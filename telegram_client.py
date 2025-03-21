from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User
import asyncio
import os
from datetime import datetime, timedelta
import pytz
from utils import get_sender_name, get_message_content


class TelegramManager:
    def __init__(self, session_name, api_id, api_hash):
        """Initialize the Telegram client.

        Args:
            session_name (str): Name of the session file.
            api_id (str): Telegram API ID.
            api_hash (str): Telegram API hash.
        """
        session_path = os.path.join("data", session_name)
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.me = None  # To store current user info

    async def connect(self):
        """Connect to Telegram servers."""
        try:
            await self.client.connect()
            print("Connected to Telegram servers.")
        except Exception as e:
            print(f"Error connecting to Telegram: {e}")
            raise

    async def login(self, phone):
        """Log in to Telegram with the provided phone number.

        Args:
            phone (str): Phone number to log in with.

        Returns:
            User: Logged-in user object.
        """
        try:
            if not await self.client.is_user_authorized():
                print("First-time login required.")
                await self.client.start(phone=phone)
                print("Successfully logged in and session saved!")
            else:
                print("Already logged in using saved session.")
            self.me = await self.client.get_me()  # Store user info
            return self.me
        except Exception as e:
            print(f"Error logging into Telegram: {e}")
            raise

    async def fetch_chats(self):
        """Fetch all private chats from Telegram.

        Returns:
            list: List of tuples (chat_id, name, username).
        """
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

    async def safe_iter_messages(self, chat_id, limit=None, offset_id=0):
        """Safely iterate over messages with adaptive rate limiting.

        Args:
            chat_id (int): Chat ID to fetch messages from.
            limit (int, optional): Maximum number of messages to fetch.
            offset_id (int, optional): Offset ID to start from.

        Yields:
            Message: Telegram message object.
        """
        while True:
            try:
                async for msg in self.client.iter_messages(chat_id, limit=limit, offset_id=offset_id):
                    yield msg
                break
            except FloodWaitError as e:
                print(f"Rate limit hit! Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)

    async def get_messages(self, chat_id, filter_type, filter_value):
        """Fetch messages from a chat based on the filter type.

        Args:
            chat_id (int): Chat ID to fetch messages from.
            filter_type (str): Type of filter ('recent_messages', 'recent_days', 'specific_date').
            filter_value: Value for the filter (int for recent, str for date).

        Returns:
            list: List of tuples (sender_name, message_content, date, message_id).
        """
        print(f"\nLoading messages from chat ID: {chat_id}...")
        messages = []
        retry_count = 0
        max_retries = 3
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
                specific_date = self._parse_date(filter_value)
                if not specific_date:
                    return None
                if specific_date > self._make_aware_datetime(datetime.now()):
                    print("You cannot fetch messages from a future date!")
                    return None
                min_date = self._make_aware_datetime(
                    specific_date.replace(hour=0, minute=0, second=0, microsecond=0))
                max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
                message_count = 0
                async for message in self.safe_iter_messages(chat_id, limit=5000):
                    message_count += 1
                    print(
                        f"Processing message {message_count}, date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}")
                    if min_date <= message.date <= max_date:
                        sender = await message.get_sender()
                        sender_name = get_sender_name(sender, self.me)
                        message_content = get_message_content(message)
                        messages.append(
                            (sender_name, message_content, message.date, message.id))
                    if message.date < min_date:
                        break
                    await asyncio.sleep(0.5)
                print(f"Total messages processed: {message_count}")

        except Exception as e:
            print(
                f"Error fetching messages: Could not connect to Telegram, please try again. (Details: {e})")
            return None
        return messages

    def _parse_date(self, date_str):
        """Parse a date string into a datetime object.

        Args:
            date_str (str): Date string in format 'DD Month YYYY'.

        Returns:
            datetime: Parsed datetime object or None if invalid.
        """
        try:
            return self._make_aware_datetime(datetime.strptime(date_str, "%d %B %Y"))
        except ValueError:
            print(
                "Invalid date format! Please use 'DD Month YYYY' (e.g., '10 March 2025')")
            return None

    def _make_aware_datetime(self, dt):
        """Convert date to offset-aware with UTC timezone.

        Args:
            dt (datetime): Datetime object to convert.

        Returns:
            datetime: Offset-aware datetime with UTC timezone.
        """
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
