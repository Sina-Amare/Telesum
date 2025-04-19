from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User
import asyncio
import os
from datetime import datetime, timedelta
import pytz
from utils import get_sender_name, get_message_content
from database import save_messages, load_messages
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, VERBOSE_LOGGING
import logging

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base directory for session file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)


class TelegramManager:
    """Manages Telegram client operations such as connection, login, and message fetching."""

    def __init__(self, session_name, api_id, api_hash):
        """Initialize the Telegram client."""
        session_path = os.path.join(SESSION_DIR, f"{session_name}.session")
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.me = None  # To store current user info

    async def connect(self):
        """Establish a connection to Telegram servers."""
        try:
            await self.client.connect()
            print("Connected to Telegram servers.")
            logger.info("Connected to Telegram servers")
        except Exception as e:
            print(f"Error connecting to Telegram: {e}")
            logger.error(f"Error connecting to Telegram: {e}")
            raise

    async def login(self, phone):
        """Log in to Telegram using the provided phone number."""
        try:
            if not await self.client.is_user_authorized():
                print("First-time login required.")
                await self.client.start(phone=phone)
                print("Successfully logged in and session saved!")
                logger.info("Successfully logged in and session saved")
            else:
                print("Already logged in using saved session.")
                logger.info("Already logged in using saved session")
            self.me = await self.client.get_me()
            return self.me
        except Exception as e:
            print(f"Error logging into Telegram: {e}")
            logger.error(f"Error logging into Telegram: {e}")
            raise

    async def fetch_chats(self):
        """Retrieve all private chats from Telegram."""
        print("Loading chat list...")
        logger.info("Loading chat list")
        chats = []
        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    chats.append(
                        (dialog.id, dialog.name, dialog.entity.username))
                    await asyncio.sleep(0.5)  # Delay to respect API limits
            logger.info(f"Retrieved {len(chats)} private chats")
            return chats
        except Exception as e:
            print(f"Error loading chats: {e}")
            logger.error(f"Error loading chats: {e}")
            return []

    async def fetch_new_chats(self, last_update_timestamp=None):
        """Retrieve only new or updated private chats since the last update."""
        print("Checking for new or updated chats...")
        logger.info("Checking for new or updated chats")
        new_chats = []
        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    dialog_date = dialog.date
                    if dialog_date.tzinfo is None:
                        dialog_date = dialog_date.replace(tzinfo=pytz.UTC)
                    if last_update_timestamp and last_update_timestamp.tzinfo is None:
                        last_update_timestamp = last_update_timestamp.replace(
                            tzinfo=pytz.UTC)
                    if last_update_timestamp is None or dialog_date > last_update_timestamp:
                        new_chats.append(
                            (dialog.id, dialog.name, dialog.entity.username))
                    await asyncio.sleep(0.5)  # Delay to respect API limits
            if new_chats:
                print("New or updated chats found:")
                for chat_id, name, username in new_chats:
                    username_str = f" (@{username})" if username else ""
                    print(f"- {name}{username_str} (ID: {chat_id})")
                logger.info(f"Found {len(new_chats)} new or updated chats")
            else:
                print("No new or updated chats found.")
                logger.info("No new or updated chats found")
            print(f"Total new or updated chats: {len(new_chats)}")
            return new_chats
        except Exception as e:
            print(f"Error checking new chats: {e}")
            logger.error(f"Error checking new chats: {e}")
            return []

    async def safe_iter_messages(self, chat_id, limit=None, offset_id=0, offset_date=None):
        """Safely iterate over messages with adaptive rate limiting."""
        while True:
            try:
                async for msg in self.client.iter_messages(chat_id, limit=limit, offset_id=offset_id, offset_date=offset_date):
                    if msg.date:
                        if msg.date.tzinfo is None:
                            logger.debug(
                                f"Naive msg.date detected for message ID {msg.id}, making aware")
                            msg.date = msg.date.replace(tzinfo=pytz.UTC)
                    else:
                        logger.warning(
                            f"Message ID {msg.id} has no date, skipping")
                        continue
                    yield msg
                break
            except FloodWaitError as e:
                print(f"Rate limit hit! Waiting {e.seconds} seconds...")
                logger.warning(f"Rate limit hit, waiting {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Error in safe_iter_messages: {e}")
                raise

    async def get_messages(self, chat_id, filter_type, filter_value, user_timezone, user_phone):
        """Fetch messages from a chat based on the specified filter and user timezone."""
        # Check database for existing messages
        db_messages, full_day_covered, _ = load_messages(
            chat_id, filter_type, filter_value, user_phone)
        messages = []
        messages_to_fetch = filter_value

        if filter_type == "recent_messages" and db_messages:
            db_message_count = len(db_messages)
            if db_message_count >= filter_value:
                logger.info(
                    f"Found {db_message_count} messages in database for chat ID {chat_id}, no Telegram fetch needed")
                return db_messages[:filter_value]
            messages_to_fetch = filter_value - db_message_count
            print(
                f"Found {db_message_count} messages in database, fetching {messages_to_fetch} more from Telegram...")
            logger.info(
                f"Found {db_message_count} messages in database, fetching {messages_to_fetch} more for chat ID {chat_id}")
        elif filter_type == "specific_date" and db_messages and full_day_covered:
            logger.info(
                f"Database has complete messages for {filter_value} for chat ID {chat_id}")
            return db_messages
        else:
            print(f"Fetching messages from Telegram for chat ID {chat_id}...")
            logger.info(
                f"Fetching messages from Telegram for chat ID {chat_id}")

        try:
            if filter_type == "recent_messages":
                # Use the smallest message_id from db_messages as offset_id
                offset_id = 0
                if db_messages:
                    offset_id = min(msg[3] for msg in db_messages)
                    logger.debug(
                        f"Using offset_id {offset_id} for chat ID {chat_id}")

                async for message in self.safe_iter_messages(chat_id, limit=messages_to_fetch, offset_id=offset_id):
                    sender = await message.get_sender()
                    sender_name = get_sender_name(sender, self.me)
                    message_content = get_message_content(message)
                    message_date = message.date
                    messages.append(
                        (sender_name, message_content, message_date, message.id))
                    logger.debug(
                        f"Fetched message ID {message.id} for chat ID {chat_id}")
                    await asyncio.sleep(0.5)

            elif filter_type == "recent_days":
                min_date = self._make_aware_datetime(
                    datetime.now() - timedelta(days=filter_value))
                message_count = 0
                last_id = 0
                oldest_date = None
                while True:
                    batch = []
                    last_message_date = None
                    async for message in self.safe_iter_messages(chat_id, limit=5000, offset_id=last_id):
                        message_count += 1
                        last_message_date = message.date
                        if not oldest_date or (last_message_date and last_message_date < oldest_date):
                            oldest_date = last_message_date
                        if last_message_date and last_message_date >= min_date:
                            sender = await message.get_sender()
                            sender_name = get_sender_name(sender, self.me)
                            message_content = get_message_content(message)
                            batch.append(
                                (sender_name, message_content, last_message_date, message.id))
                            logger.debug(
                                f"Fetched message ID {message.id} for chat ID {chat_id}")
                        last_id = message.id
                        await asyncio.sleep(0.5)
                    if batch:
                        messages.extend(batch)
                    if last_message_date and last_message_date < min_date:
                        break
                    if not batch:
                        break

            elif filter_type == "specific_date":
                specific_date = datetime.strptime(filter_value, '%d %B %Y')
                local_start = user_timezone.localize(
                    specific_date.replace(hour=0, minute=0, second=0))
                local_end = local_start.replace(hour=23, minute=59, second=59)
                min_date = local_start.astimezone(pytz.UTC)
                max_date = local_end.astimezone(pytz.UTC)

                message_count = 0
                last_id = 0
                while True:
                    batch = []
                    async for message in self.safe_iter_messages(chat_id, limit=100, offset_id=last_id):
                        message_count += 1
                        message_date = message.date
                        if message_date and message_date < min_date:
                            break
                        if message_date and min_date <= message_date <= max_date:
                            sender = await message.get_sender()
                            sender_name = get_sender_name(sender, self.me)
                            message_content = get_message_content(message)
                            batch.append(
                                (sender_name, message_content, message_date, message.id))
                            logger.debug(
                                f"Fetched message ID {message.id} for chat ID {chat_id}")
                        last_id = message.id
                        await asyncio.sleep(0.5)
                    if batch:
                        messages.extend(batch)
                    if not batch or message_count >= 1000:
                        break

        except Exception as e:
            print(f"Error fetching messages from Telegram: {e}")
            logger.error(f"Error fetching messages from Telegram: {e}")
            return None

        # Ensure all timestamps are timezone-aware before combining
        combined_messages = []
        for msg in db_messages + messages:
            sender, text, timestamp, msg_id = msg
            if timestamp.tzinfo is None:
                logger.warning(
                    f"Naive timestamp in message ID {msg_id}, making aware")
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            combined_messages.append((sender, text, timestamp, msg_id))

        # Combine database and Telegram messages, removing duplicates
        if combined_messages:
            messages = list(
                {msg[3]: msg for msg in combined_messages}.values())
            messages.sort(key=lambda x: x[2], reverse=True)
            # Save fetched messages to database
            engine = create_engine(DATABASE_URL)
            Session = sessionmaker(bind=engine)
            db_session = Session()
            try:
                save_messages(db_session, chat_id, user_phone, messages)
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                print(f"Error saving messages to database: {e}")
                logger.error(f"Error saving messages to database: {e}")
                return messages
            finally:
                db_session.close()

        if not messages:
            print(f"No new messages found for chat ID {chat_id}")
            logger.info(f"No new messages found for chat ID {chat_id}")

        logger.info(
            f"Returning {len(messages)} messages for chat ID {chat_id}")
        return messages

    def _parse_date(self, date_str):
        """Parse a date string into a datetime object."""
        try:
            return self._make_aware_datetime(datetime.strptime(date_str, "%d %B %Y"))
        except ValueError:
            print(
                "Invalid date format! Please use 'DD Month YYYY' (e.g., '10 March 2025')")
            logger.error(f"Invalid date format: {date_str}")
            return None

    def _make_aware_datetime(self, dt):
        """Convert a naive datetime to an offset-aware one with UTC timezone."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.UTC)
        return dt

    async def disconnect(self):
        """Disconnect from Telegram servers."""
        try:
            await self.client.disconnect()
            print("Disconnected from Telegram.")
            logger.info("Disconnected from Telegram")
        except Exception as e:
            print(f"Error disconnecting: {e}")
            logger.error(f"Error disconnecting: {e}")
