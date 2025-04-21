import asyncio
import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User
from utils import get_sender_name, get_message_content
from database import save_messages, load_messages
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, VERBOSE_LOGGING
from PyQt6.QtWidgets import QInputDialog
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Base directory for session file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)


class TelegramManager:
    """Manages Telegram client operations such as connection, login, and message fetching."""

    def __init__(self, user_phone, api_id, api_hash, parent=None):
        """Initialize the Telegram client with a session name based on the user phone."""
        session_name = user_phone.replace("+", "").replace(" ", "")
        session_path = os.path.join(SESSION_DIR, f"session_{session_name}")
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.me = None  # To store current user info
        self.parent = parent  # Reference to parent widget for GUI dialogs
        self.updates_enabled = True  # Track update state

    async def connect(self):
        """Establish a connection to Telegram servers."""
        try:
            await self.client.connect()
            logger.info("Connected to Telegram servers")
        except Exception as e:
            logger.error(f"Error connecting to Telegram: {e}")
            raise

    async def login(self, phone):
        """Log in to Telegram using the provided phone number."""
        try:
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(phone)
                if self.parent:
                    code, ok = QInputDialog.getText(
                        self.parent, "Telegram Login", "Enter the code sent to your Telegram:")
                    if not ok or not code:
                        raise ValueError("Login cancelled or no code provided")
                else:
                    code = input("Enter the code sent to your Telegram: ")
                await self.client.sign_in(phone, code)
            self.me = await self.client.get_me()
            logger.info("Logged in and session saved")
            return self.me
        except Exception as e:
            logger.error(f"Error logging into Telegram: {e}")
            raise

    async def toggle_updates(self, enable=True):
        """Enable or disable background updates."""
        if enable and not self.updates_enabled:
            self.updates_enabled = True
            logger.info("Background updates enabled.")
        elif not enable and self.updates_enabled:
            self.updates_enabled = False
            logger.info("Background updates disabled.")

    async def fetch_chats(self):
        """Retrieve private chats from Telegram with adaptive rate limiting."""
        logger.info("Loading chat list")
        chats = []
        try:
            await self.toggle_updates(False)
            async for dialog in self.client.iter_dialogs():
                if VERBOSE_LOGGING:
                    logger.debug(
                        f"Processing dialog: {dialog.name}, is_user={dialog.is_user}, entity_type={type(dialog.entity)}")
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    chats.append(
                        (dialog.id, dialog.name, dialog.entity.username))
                    if VERBOSE_LOGGING:
                        logger.debug(
                            f"Added chat: {dialog.name} (ID: {dialog.id})")
            logger.info(f"Retrieved {len(chats)} private chats from Telegram")
            return chats
        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"FloodWaitError: Waiting for {wait_time} seconds.")
            await asyncio.sleep(wait_time)
            return await self.fetch_chats()
        except Exception as e:
            logger.error(f"Error loading chats: {e}")
            return []
        finally:
            await self.toggle_updates(True)

    async def search_chat_by_id_or_name(self, search_term):
        """Search for chats by ID, name, or username (case-insensitive). Returns a list of matching (chat_id, name, username)."""
        logger.info(f"Searching for chat with term: {search_term}")
        chats = []
        try:
            await self.toggle_updates(False)
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    chat_id = str(dialog.id)
                    chat_name = dialog.name.lower()
                    username = dialog.entity.username.lower() if dialog.entity.username else ""
                    search_term_lower = search_term.lower()

                    if search_term_lower.startswith('@'):
                        search_term_clean = search_term_lower[1:]
                        if search_term_clean and search_term_clean == username:
                            chats.append(
                                (dialog.id, dialog.name, dialog.entity.username))
                            if VERBOSE_LOGGING:
                                logger.debug(
                                    f"Found matching chat by username: {dialog.name} (ID: {dialog.id}, Username: {dialog.entity.username})")
                    else:
                        if search_term_lower == chat_id or search_term_lower in chat_name:
                            chats.append(
                                (dialog.id, dialog.name, dialog.entity.username))
                            if VERBOSE_LOGGING:
                                logger.debug(
                                    f"Found matching chat by ID or name: {dialog.name} (ID: {dialog.id})")

            logger.info(
                f"Found {len(chats)} chats matching search term: {search_term}")
            return chats
        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"FloodWaitError: Waiting for {wait_time} seconds.")
            await asyncio.sleep(wait_time)
            return await self.search_chat_by_id_or_name(search_term)
        except Exception as e:
            logger.error(f"Error searching chats: {e}")
            return []
        finally:
            await self.toggle_updates(True)

    async def fetch_new_chats(self, last_update_timestamp=None):
        """Retrieve only new or updated private chats since the last update."""
        logger.info("Checking for new or updated chats")
        new_chats = []
        try:
            await self.toggle_updates(False)
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
                        if VERBOSE_LOGGING:
                            logger.debug(
                                f"Added new chat: {dialog.name} (ID: {dialog.id})")
            if new_chats:
                logger.info(f"Found {len(new_chats)} new or updated chats")
            else:
                logger.info("No new or updated chats found")
            return new_chats
        except FloodWaitError as e:
            wait_time = e.seconds
            logger.warning(f"FloodWaitError: Waiting for {wait_time} seconds.")
            await asyncio.sleep(wait_time)
            return await self.fetch_new_chats(last_update_timestamp)
        except Exception as e:
            logger.error(f"Error checking new chats: {e}")
            return []
        finally:
            await self.toggle_updates(True)

    async def safe_iter_messages(self, chat_id, limit=None, offset_id=0, offset_date=None, reverse=False):
        """Safely iterate over messages with adaptive rate limiting."""
        while True:
            try:
                async for msg in self.client.iter_messages(chat_id, limit=limit, offset_id=offset_id, offset_date=offset_date, reverse=reverse):
                    if msg.date:
                        if msg.date.tzinfo is None:
                            logger.debug(
                                f"Naive msg.date detected for message ID {msg.id}, making aware")
                            msg.date = msg.date.replace(tzinfo=pytz.UTC)
                        yield msg
                    else:
                        logger.warning(
                            f"Message ID {msg.id} has no date, skipping")
                        continue
                break
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"Rate limit hit, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Error in safe_iter_messages: {e}")
                raise

    async def get_messages(self, chat_id, filter_type, filter_value, user_timezone, user_phone, progress_callback=None):
        """Fetch messages from a chat based on the specified filter and user timezone."""
        db_messages, full_day_covered, latest_timestamp = load_messages(
            chat_id, filter_type, filter_value, user_phone, user_timezone)
        messages = []
        total_fetched = 0

        try:
            await self.toggle_updates(False)
            batch_size = 50

            if filter_type == "recent_messages":
                messages_to_fetch = filter_value
                offset_id = 0

                while total_fetched < messages_to_fetch:
                    batch = []
                    limit = min(batch_size, messages_to_fetch - total_fetched)
                    async for message in self.safe_iter_messages(chat_id, limit=limit, offset_id=offset_id):
                        sender = await message.get_sender()
                        sender_name = get_sender_name(sender, self.me)
                        message_content = get_message_content(message)
                        message_date = message.date
                        batch.append(
                            (sender_name, message_content, message_date, message.id))
                    if not batch:
                        break
                    messages.extend(batch)
                    total_fetched += len(batch)
                    if batch:
                        offset_id = batch[-1][3]
                    if progress_callback:
                        progress = (total_fetched /
                                    messages_to_fetch) * 90  # Limit to 90%
                        progress = min(progress, 90)
                        await progress_callback(progress)

            elif filter_type == "specific_date":
                specific_date = datetime.strptime(filter_value, '%d %B %Y')
                local_start = user_timezone.localize(
                    specific_date.replace(hour=0, minute=0, second=0))
                local_end = local_start.replace(hour=23, minute=59, second=59)
                min_date = local_start.astimezone(pytz.UTC)
                max_date = local_end.astimezone(pytz.UTC)

                if full_day_covered:
                    return db_messages

                offset_id = 0
                while True:
                    batch = []
                    async for message in self.safe_iter_messages(chat_id, limit=batch_size, offset_id=offset_id):
                        message_date = message.date
                        if message_date < min_date:
                            break
                        if min_date <= message_date <= max_date:
                            sender = await message.get_sender()
                            sender_name = get_sender_name(sender, self.me)
                            message_content = get_message_content(message)
                            batch.append(
                                (sender_name, message_content, message_date, message.id))
                        offset_id = message.id
                    if not batch:
                        break
                    messages.extend(batch)
                    total_fetched += len(batch)
                    if progress_callback:
                        progress = min(total_fetched * 1.8, 90)  # Limit to 90%
                        await progress_callback(progress)

            elif filter_type == "recent_days":
                min_date = datetime.now(user_timezone) - \
                    timedelta(days=filter_value)
                min_date = min_date.astimezone(pytz.UTC)
                offset_id = 0
                while True:
                    batch = []
                    async for message in self.safe_iter_messages(chat_id, limit=batch_size, offset_id=offset_id):
                        message_date = message.date
                        if message_date < min_date:
                            break
                        sender = await message.get_sender()
                        sender_name = get_sender_name(sender, self.me)
                        message_content = get_message_content(message)
                        batch.append(
                            (sender_name, message_content, message_date, message.id))
                        offset_id = message.id
                    if not batch:
                        break
                    messages.extend(batch)
                    total_fetched += len(batch)
                    if progress_callback:
                        progress = min(total_fetched * 1.8, 90)  # Limit to 90%
                        await progress_callback(progress)

            combined_messages = db_messages + messages
            combined_messages = list(
                {msg[3]: msg for msg in combined_messages}.values())
            combined_messages.sort(key=lambda x: x[2], reverse=True)

            if filter_type == "recent_messages":
                messages = combined_messages[:filter_value]
            elif filter_type == "recent_days":
                messages = [
                    msg for msg in combined_messages if msg[2] >= min_date]
            else:
                messages = [
                    msg for msg in combined_messages if min_date <= msg[2] <= max_date]

            if messages:
                engine = create_engine(DATABASE_URL)
                Session = sessionmaker(bind=engine)
                db_session = Session()
                try:
                    save_messages(db_session, chat_id, user_phone, messages)
                    db_session.commit()
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Error saving messages to database: {e}")
                finally:
                    db_session.close()

            return messages

        except Exception as e:
            logger.error(f"Error fetching messages from Telegram: {e}")
            return []
        finally:
            await self.toggle_updates(True)

    def _parse_date(self, date_str):
        """Parse a date string into a datetime object."""
        try:
            return self._make_aware_datetime(datetime.strptime(date_str, "%d %B %Y"))
        except ValueError:
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
            logger.info("Disconnected from Telegram")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
