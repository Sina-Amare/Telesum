from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import User
import asyncio
import os
from datetime import datetime, timedelta
import pytz


class TelegramManager:
    def __init__(self, session_name, api_id, api_hash):
        session_path = os.path.join("data", session_name)
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.me = None  # To store current user info

    async def connect(self):
        try:
            await self.client.connect()
            print("Connected to Telegram servers.")
        except Exception as e:
            print(f"Error connecting to Telegram: {e}")
            raise

    async def login(self, phone):
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

    async def get_messages(self, chat_id, filter_type, filter_value):
        print(f"\nLoading messages from chat ID: {chat_id}...")
        messages = []
        retry_count = 0
        max_retries = 3
        try:
            if filter_type == "recent_messages":
                async for message in self.client.iter_messages(chat_id, limit=filter_value):
                    sender = await message.get_sender()
                    sender_name = self._get_sender_name(sender)
                    message_content = self._get_message_content(message)
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
                    try:
                        async for message in self.client.iter_messages(chat_id, limit=5000, offset_id=last_id):
                            message_count += 1
                            last_message_date = message.date
                            if not oldest_date or message.date < oldest_date:
                                oldest_date = message.date
                            print(
                                f"Processing message {message_count}, date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}")
                            if message.date >= min_date:
                                sender = await message.get_sender()
                                sender_name = self._get_sender_name(sender)
                                message_content = self._get_message_content(
                                    message)
                                batch.append(
                                    (sender_name, message_content, message.date, message.id))
                            last_id = message.id
                            await asyncio.sleep(0.5)
                    except FloodWaitError as e:
                        print(
                            f"Telegram rate limit hit! Please wait for {e.seconds} seconds...")
                        await asyncio.sleep(e.seconds)
                        continue
                    except Exception as e:
                        print(f"Error loading messages: {e}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            print("Maximum retries reached, stopping.")
                            break
                        await asyncio.sleep(5)
                        continue

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
                try:
                    async for message in self.client.iter_messages(chat_id, limit=5000):
                        message_count += 1
                        print(
                            f"Processing message {message_count}, date: {message.date.strftime('%Y-%m-%d %H:%M:%S')}")
                        if min_date <= message.date <= max_date:
                            sender = await message.get_sender()
                            sender_name = self._get_sender_name(sender)
                            message_content = self._get_message_content(
                                message)
                            messages.append(
                                (sender_name, message_content, message.date, message.id))
                        if message.date < min_date:
                            break
                        await asyncio.sleep(0.5)
                except FloodWaitError as e:
                    print(
                        f"Telegram rate limit hit! Please wait for {e.seconds} seconds...")
                    await asyncio.sleep(e.seconds)
                    return await self.get_messages(chat_id, filter_type, filter_value)
                except Exception as e:
                    print(f"Error loading messages: {e}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        print("Maximum retries reached, stopping.")
                        return messages
                    await asyncio.sleep(5)
                    return await self.get_messages(chat_id, filter_type, filter_value)
                print(f"Total messages processed: {message_count}")

        except Exception as e:
            print(
                f"Error fetching messages: Could not connect to Telegram, please try again. (Details: {e})")
            return None
        return messages

    def _get_sender_name(self, sender):
        if not sender:
            return "Unknown"
        if sender.id == self.me.id:
            return f"{self.me.username}(me)" if self.me.username else "me"
        return f"@{sender.username}" if sender.username else sender.first_name

    def _get_message_content(self, message):
        """Determine message type and return appropriate content"""
        if message.text:
            return message.text
        elif message.photo:
            return "[Photo]"
        elif message.gif:
            return "[GIF]"
        elif message.video:
            return "[Video]"
        elif message.audio:
            return "[Audio]"
        elif message.voice:
            return "[Voice Message]"
        elif message.sticker:
            return "[Sticker]"
        elif message.document:
            return "[Document]"
        else:
            return "[Unknown message type]"

    def _parse_date(self, date_str):
        try:
            return self._make_aware_datetime(datetime.strptime(date_str, "%d %B %Y"))
        except ValueError:
            print(
                "Invalid date format! Please use 'DD Month YYYY' (e.g., '10 March 2025')")
            return None

    def _make_aware_datetime(self, dt):
        """Convert date to offset-aware with UTC timezone"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.UTC)
        return dt

    async def disconnect(self):
        try:
            await self.client.disconnect()
            print("Disconnected from Telegram.")
        except Exception as e:
            print(f"Error disconnecting: {e}")
