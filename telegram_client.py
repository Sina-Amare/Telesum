from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User
import asyncio
import os
from datetime import datetime, timedelta
import pytz
from utils import get_sender_name, get_message_content
from database import save_messages

# Base directory for session file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class TelegramManager:
    """Manages Telegram client operations such as connection, login, and message fetching."""

    def __init__(self, session_name, api_id, api_hash):
        """Initialize the Telegram client."""
        session_path = os.path.join(BASE_DIR, "data", session_name)
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.me = None  # To store current user info

    async def connect(self):
        """Establish a connection to Telegram servers."""
        try:
            await self.client.connect()
            print("Connected to Telegram servers.")
        except Exception as e:
            print(f"Error connecting to Telegram: {e}")
            raise

    async def login(self, phone):
        """Log in to Telegram using the provided phone number."""
        try:
            if not await self.client.is_user_authorized():
                print("First-time login required.")
                await self.client.start(phone=phone)
                print("Successfully logged in and session saved!")
            else:
                print("Already logged in using saved session.")
            self.me = await self.client.get_me()
            return self.me
        except Exception as e:
            print(f"Error logging into Telegram: {e}")
            raise

    async def fetch_chats(self):
        """Retrieve all private chats from Telegram."""
        print("Loading chat list...")
        chats = []
        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    chats.append(
                        (dialog.id, dialog.name, dialog.entity.username))
                    await asyncio.sleep(0.5)  # Delay to respect API limits
            return chats
        except Exception as e:
            print(f"Error loading chats: {e}")
            return []

    async def fetch_new_chats(self, last_update_timestamp=None):
        """Retrieve only new or updated private chats since the last update."""
        print("Checking for new or updated chats...")
        new_chats = []
        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and isinstance(dialog.entity, User) and not dialog.entity.bot:
                    # Ensure dialog.date is UTC-aware
                    dialog_date = dialog.date if dialog.date.tzinfo else dialog.date.replace(
                        tzinfo=pytz.UTC)
                    # Include chats if no last_update_timestamp or if updated after it
                    if last_update_timestamp is None or dialog_date > last_update_timestamp:
                        new_chats.append(
                            (dialog.id, dialog.name, dialog.entity.username))
                    await asyncio.sleep(0.5)  # Delay to respect API limits
            if new_chats:
                print("New or updated chats found:")
                for chat_id, name, username in new_chats:
                    username_str = f" (@{username})" if username else ""
                    print(f"- {name}{username_str} (ID: {chat_id})")
            else:
                print("No new or updated chats found.")
            print(f"Total new or updated chats: {len(new_chats)}")
            return new_chats
        except Exception as e:
            print(f"Error checking new chats: {e}")
            return []

    async def safe_iter_messages(self, chat_id, limit=None, offset_id=0, offset_date=None):
        """Safely iterate over messages with adaptive rate limiting."""
        while True:
            try:
                async for msg in self.client.iter_messages(chat_id, limit=limit, offset_id=offset_id, offset_date=offset_date):
                    yield msg
                break
            except FloodWaitError as e:
                print(f"Rate limit hit! Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)

    async def get_messages(self, chat_id, filter_type, filter_value, user_timezone, user_phone):
        """Fetch messages from a chat based on the specified filter and user timezone."""
        print(
            f"\nLoading messages from chat ID: {chat_id} for user {user_phone}...")
        messages = []
        try:
            if filter_type == "recent_messages":
                async for message in self.safe_iter_messages(chat_id, limit=filter_value):
                    sender = await message.get_sender()
                    sender_name = get_sender_name(sender, self.me)
                    message_content = get_message_content(message)
                    messages.append(
                        (sender_name, message_content, message.date, message.id))
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
                        if not oldest_date or message.date < oldest_date:
                            oldest_date = message.date
                        print(
                            f"Processing message {message_count}, date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}")
                        if message.date >= min_date:
                            sender = await message.get_sender()
                            sender_name = get_sender_name(sender, self.me)
                            message_content = get_message_content(message)
                            batch.append(
                                (sender_name, message_content, message.date, message.id))
                        last_id = message.id
                        await asyncio.sleep(0.5)
                    if batch:
                        messages.extend(batch)
                    if last_message_date and last_message_date < min_date:
                        break
                    if not batch:
                        break
                print(f"Total messages processed: {message_count}")
                if oldest_date:
                    print(
                        f"Oldest message date: {oldest_date.strftime('%Y-%m-%d %H:%M:%S')}")

            elif filter_type == "specific_date":
                specific_date = datetime.strptime(filter_value, '%d %B %Y')
                local_start = user_timezone.localize(
                    specific_date.replace(hour=0, minute=0, second=0))
                local_end = local_start.replace(hour=23, minute=59, second=59)
                min_date = local_start.astimezone(pytz.UTC)
                max_date = local_end.astimezone(pytz.UTC)

                print(
                    f"Fetching messages from {min_date} to {max_date} (UTC)...")
                message_count = 0
                last_id = 0
                while True:
                    batch = []
                    async for message in self.safe_iter_messages(chat_id, limit=100, offset_id=last_id):
                        message_count += 1
                        msg_date_str = message.date.strftime(
                            '%Y-%m-%d %H:%M:%S')
                        print(
                            f"Fetched message {message_count}, date: {msg_date_str}")
                        if message.date < min_date:
                            print(
                                f"Stopping: Message date {msg_date_str} is before {min_date}")
                            break
                        if min_date <= message.date <= max_date:
                            sender = await message.get_sender()
                            sender_name = get_sender_name(sender, self.me)
                            message_content = get_message_content(message)
                            batch.append(
                                (sender_name, message_content, message.date, message.id))
                        last_id = message.id
                        await asyncio.sleep(0.5)
                    if batch:
                        messages.extend(batch)
                    if not batch or message_count >= 1000:
                        break
                print(f"Total messages fetched from Telegram: {message_count}")
                print(f"Messages within date range: {len(messages)}")

        except Exception as e:
            print(
                f"Error fetching messages: Could not connect to Telegram, please try again. (Details: {e})")
            return None

        # Save fetched messages to database
        if messages:
            try:
                save_messages(chat_id, messages, user_phone)
                print(
                    f"Saved {len(messages)} new messages to database with timestamps for user {user_phone}.")
            except Exception as e:
                print(f"Error saving messages to database: {e}")

        return messages

    def _parse_date(self, date_str):
        """Parse a date string into a datetime object."""
        try:
            return self._make_aware_datetime(datetime.strptime(date_str, "%d %B %Y"))
        except ValueError:
            print(
                "Invalid date format! Please use 'DD Month YYYY' (e.g., '10 March 2025')")
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
        except Exception as e:
            print(f"Error disconnecting: {e}")
