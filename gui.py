from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QComboBox, QTextEdit, QListWidget, QInputDialog,
                             QMessageBox, QLabel, QProgressBar, QFrame, QGridLayout, QDialog)
from PyQt6.QtCore import Qt, QTimer
import asyncio
import sys
import qasync
from telegram_client import TelegramManager
from database import (setup_database, save_chats, load_chats, save_search_history, load_search_history,
                      delete_search_history_entry, delete_all_search_history, delete_messages, save_last_update_timestamp, load_last_update_timestamp)
from utils import search_by_username
from ai_processor import summarize_text
from config import API_ID, API_HASH
from datetime import datetime
import pytz
import logging
import os
import time

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom logging handler to display logs in QTextEdit


class TextEditHandler(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum())


class FetchMessagesDialog(QDialog):
    def __init__(self, telegram, chat_id, chat_name, user_timezone, user_phone, parent=None):
        super().__init__(parent)
        self.telegram = telegram
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.user_timezone = user_timezone
        self.user_phone = user_phone
        self.result = None
        self.setWindowTitle(f"Fetch Messages for {chat_name}")
        self.setMinimumSize(500, 250)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        filter_frame = QFrame()
        filter_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)

        filter_label = QLabel("Message Filter:")
        filter_label.setStyleSheet("font-weight: bold; color: #D5D5D5;")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Recent messages (e.g., last 10 messages)",
            "Messages from recent days (e.g., last 7 days)",
            "Messages from a specific date (e.g., 10 March 2025)"
        ])
        self.filter_combo.setMinimumWidth(300)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., 10, 7, 10 March 2025")
        self.value_input.setMinimumWidth(200)

        self.fetch_button = QPushButton("Fetch Messages")
        self.fetch_button.clicked.connect(self.fetch_messages)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        filter_layout.addWidget(filter_label, 0, 0)
        filter_layout.addWidget(self.filter_combo, 0, 1)
        filter_layout.addWidget(self.value_input, 1, 1)
        filter_layout.addWidget(self.fetch_button, 1, 2)
        filter_frame.setLayout(filter_layout)
        layout.addWidget(filter_frame)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def fetch_messages(self):
        filter_index = self.filter_combo.currentIndex()
        filter_value = self.value_input.text().strip()

        if not filter_value:
            QMessageBox.warning(self, "Input Error",
                                "Please enter a filter value.")
            return

        filter_types = ["recent_messages", "recent_days", "specific_date"]
        filter_type = filter_types[filter_index]

        try:
            if filter_type == "recent_messages":
                filter_value = int(filter_value)
                if filter_value <= 0:
                    raise ValueError("Number of messages must be positive.")
            elif filter_type == "recent_days":
                filter_value = int(filter_value)
                if filter_value <= 0:
                    raise ValueError("Number of days must be positive.")
            elif filter_type == "specific_date":
                datetime.strptime(filter_value, "%d %B %Y")
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(
                e) if "must be positive" in str(e) else "Invalid input format.")
            return

        self.result = (filter_type, filter_value)
        self.accept()


class MessageDialog(QWidget):
    def __init__(self, telegram, chat_id, chat_name, user_timezone, user_phone, filter_type, filter_value, parent=None):
        super().__init__(parent)
        self.telegram = telegram
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.user_timezone = user_timezone
        self.user_phone = user_phone
        self.filter_type = filter_type
        self.filter_value = filter_value
        self.setWindowTitle(f"Messages for {chat_name}")
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.fetch_messages()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_label = QLabel(f"Messages for {self.chat_name}")
        header_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #D5D5D5;")
        layout.addWidget(header_label)

        self.messages_text = QTextEdit()
        self.messages_text.setReadOnly(True)
        layout.addWidget(self.messages_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    async def fetch_coro(self):  # Changed to async and renamed for clarity
        try:
            # Check database messages first
            from database import load_messages
            messages, full_day_covered, _ = load_messages(
                self.chat_id, self.filter_type, self.filter_value, self.user_phone)

            if not messages or (self.filter_type == "specific_date" and not full_day_covered):
                if not messages:
                    logger.info(
                        "No messages found in database. Fetching from Telegram...")
                else:
                    logger.info(
                        "Incomplete messages for this date. Fetching from Telegram...")

            messages = await self.telegram.get_messages(self.chat_id, self.filter_type, self.filter_value, self.user_timezone, self.user_phone)
            if messages is None:
                return None

            result = ""
            if messages:
                for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                    local_time = timestamp.astimezone(self.user_timezone)
                    result += f"{i}. {sender}: {msg}\n   (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
                message_texts = [msg for _, msg, _, _ in messages]
                summary = await summarize_text(message_texts)  # Now awaited
                result += "=== Summary ===\n" + summary + "\n"
            else:
                result = "No messages found."
                # Log no messages found
                if self.filter_type == "recent_messages":
                    logger.info(
                        f"No messages found in the last {self.filter_value} messages for {self.chat_name}.")
                elif self.filter_type == "recent_days":
                    logger.info(
                        f"No messages found in the last {self.filter_value} days for {self.chat_name}.")
                elif self.filter_type == "specific_date":
                    logger.info(
                        f"No messages found on {self.filter_value} for {self.chat_name}.")
            return result
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            raise

    def fetch_messages(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.messages_text.clear()

        # Log the start of message fetching
        if self.filter_type == "recent_messages":
            logger.info(f"Fetching recent messages for {self.chat_name}...")
        elif self.filter_type == "recent_days":
            logger.info(
                f"Checking database for messages in {self.chat_name} for the last {self.filter_value} days...")
        elif self.filter_type == "specific_date":
            logger.info(
                f"Checking database for messages in {self.chat_name} on {self.filter_value}...")

        task = asyncio.ensure_future(
            self.fetch_coro())  # Use the async coroutine
        task.add_done_callback(self.display_messages)

    def display_messages(self, task):
        self.progress_bar.setVisible(False)
        try:
            result = task.result()
            if result:
                self.messages_text.setText(result)
            else:
                self.messages_text.setText("No messages found.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to fetch messages: {e}")


class MainWindow(QMainWindow):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.setWindowTitle("TeleSum - Telegram Chat Manager")
        self.setMinimumSize(900, 600)
        self.telegram = None
        self.user_phone = None
        self.user_timezone = None
        self.chats = []
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.login_tab = QWidget()
        self.setup_login_tab()
        self.tabs.addTab(self.login_tab, "Login")

        self.chats_tab = QWidget()
        self.setup_chats_tab()
        self.tabs.addTab(self.chats_tab, "Chats")

        self.messages_tab = QWidget()
        self.setup_messages_tab()
        self.tabs.addTab(self.messages_tab, "Messages")

        self.search_tab = QWidget()
        self.setup_search_tab()
        self.tabs.addTab(self.search_tab, "Search")

        self.search_history_tab = QWidget()
        self.setup_search_history_tab()
        self.tabs.addTab(self.search_history_tab, "Search History")

        self.manage_history_tab = QWidget()
        self.setup_manage_history_tab()
        self.tabs.addTab(self.manage_history_tab, "Manage History")

        self.refresh_tab = QWidget()
        self.setup_refresh_tab()
        self.tabs.addTab(self.refresh_tab, "Refresh")

        self.logs_tab = QWidget()
        self.setup_logs_tab()
        self.tabs.addTab(self.logs_tab, "Logs")

        self.statusBar().showMessage("Ready")

    def setup_login_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        phone_frame = QFrame()
        phone_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        phone_layout = QHBoxLayout()
        phone_label = QLabel("Phone Number:")
        phone_label.setStyleSheet("font-weight: bold; color: #D5D5D5;")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g., +989123456789")
        phone_layout.addWidget(phone_label)
        phone_layout.addWidget(self.phone_input)
        phone_frame.setLayout(phone_layout)
        layout.addWidget(phone_frame)

        tz_frame = QFrame()
        tz_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        tz_layout = QHBoxLayout()
        tz_label = QLabel("Timezone:")
        tz_label.setStyleSheet("font-weight: bold; color: #D5D5D5;")
        self.tz_combo = QComboBox()
        self.tz_combo.addItems([
            "Iran (UTC+3:30)",
            "United States (UTC-5:00, Eastern Time)",
            "United Kingdom (UTC+0:00)",
            "Other (UTC)"
        ])
        tz_layout.addWidget(tz_label)
        tz_layout.addWidget(self.tz_combo)
        tz_frame.setLayout(tz_layout)
        layout.addWidget(tz_frame)

        self.connect_button = QPushButton("Connect to Telegram")
        self.connect_button.clicked.connect(self.connect_telegram)
        layout.addWidget(self.connect_button)

        self.login_status = QLabel(
            "Enter phone number and timezone to connect.")
        layout.addWidget(self.login_status)

        layout.addStretch()
        self.login_tab.setLayout(layout)

    def setup_chats_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.chats_list = QListWidget()
        layout.addWidget(self.chats_list)

        self.chats_tab.setLayout(layout)

    def setup_messages_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        chats_frame = QFrame()
        chats_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        chats_layout = QHBoxLayout()
        chats_label = QLabel("Select Chat:")
        chats_label.setStyleSheet("font-weight: bold; color: #D5D5D5;")
        self.messages_chat_combo = QComboBox()
        self.messages_chat_combo.setMinimumWidth(300)
        chats_layout.addWidget(chats_label)
        chats_layout.addWidget(self.messages_chat_combo)
        chats_frame.setLayout(chats_layout)
        layout.addWidget(chats_frame)

        fetch_button = QPushButton("Fetch Messages for Selected Chat")
        fetch_button.clicked.connect(self.fetch_chat_messages)
        layout.addWidget(fetch_button)

        self.messages_display = QTextEdit()
        self.messages_display.setReadOnly(True)
        layout.addWidget(self.messages_display)

        self.messages_progress = QProgressBar()
        self.messages_progress.setVisible(False)
        layout.addWidget(self.messages_progress)

        self.messages_tab.setLayout(layout)

    def setup_search_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        search_layout = QHBoxLayout()
        search_label = QLabel("Username:")
        search_label.setStyleSheet("font-weight: bold; color: #D5D5D5;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., @username")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_username)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_frame.setLayout(search_layout)
        layout.addWidget(search_frame)

        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        layout.addWidget(self.search_results)

        self.search_tab.setLayout(layout)

    def setup_search_history_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.history_list = QListWidget()
        layout.addWidget(self.history_list)

        button_layout = QHBoxLayout()
        view_button = QPushButton("View Messages")
        view_button.clicked.connect(self.view_history_messages)
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_history_entry)
        button_layout.addWidget(view_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)

        self.search_history_tab.setLayout(layout)

    def setup_manage_history_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        delete_specific_button = QPushButton("Delete Specific Search Entry")
        delete_specific_button.clicked.connect(self.delete_specific_history)
        layout.addWidget(delete_specific_button)

        delete_all_button = QPushButton("Delete All Search History")
        delete_all_button.clicked.connect(self.delete_all_history)
        layout.addWidget(delete_all_button)

        delete_messages_button = QPushButton("Delete Messages for a Chat")
        delete_messages_button.clicked.connect(self.delete_chat_messages)
        layout.addWidget(delete_messages_button)

        layout.addStretch()
        self.manage_history_tab.setLayout(layout)

    def setup_refresh_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        refresh_button = QPushButton("Refresh Chat List")
        refresh_button.clicked.connect(self.refresh_chats)
        layout.addWidget(refresh_button)

        self.refresh_status = QLabel("Click to refresh chat list.")
        layout.addWidget(self.refresh_status)

        layout.addStretch()
        self.refresh_tab.setLayout(layout)

    def setup_logs_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Logs display
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        # Refresh logs button
        refresh_logs_button = QPushButton("Refresh Logs")
        refresh_logs_button.clicked.connect(self.update_logs)
        layout.addWidget(refresh_logs_button)

        self.logs_tab.setLayout(layout)

        # Set up logging handler to redirect logs to QTextEdit
        handler = TextEditHandler(self.logs_text)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        # Set up a timer to auto-refresh logs
        self.logs_timer = QTimer()
        self.logs_timer.timeout.connect(self.update_logs)
        self.logs_timer.start(5000)

        # Initial log load
        self.update_logs()

    def update_logs(self):
        try:
            with open('app.log', 'r', encoding='utf-8') as log_file:
                logs = log_file.read()
            current_text = self.logs_text.toPlainText()
            if logs != current_text:
                self.logs_text.setText(logs)
                self.logs_text.verticalScrollBar().setValue(
                    self.logs_text.verticalScrollBar().maximum())
        except Exception as e:
            self.logs_text.setText(f"Error loading logs: {e}")

    def connect_telegram(self):
        self.user_phone = self.phone_input.text().strip()
        if not (self.user_phone.startswith("+") and self.user_phone[1:].isdigit()):
            QMessageBox.warning(
                self, "Input Error", "Invalid phone number. Use format: +989123456789")
            return

        tz_index = self.tz_combo.currentIndex()
        timezones = [
            pytz.timezone("Asia/Tehran"),
            pytz.timezone("America/New_York"),
            pytz.timezone("Europe/London"),
            pytz.UTC
        ]
        self.user_timezone = timezones[tz_index]

        self.statusBar().showMessage("Connecting to Telegram...")
        self.login_status.setText("Connecting...")
        self.connect_button.setEnabled(False)

        async def connect_coro():
            try:
                setup_database()
                self.telegram = TelegramManager(
                    "session_name", API_ID, API_HASH, self)
                await self.telegram.connect()
                user = await self.telegram.login(self.user_phone)
                logger.info(f"Logged in as: {user.first_name} ({user.phone})")
                return user
            except Exception as e:
                logger.error(f"Error connecting to Telegram: {e}")
                raise

        task = asyncio.ensure_future(connect_coro())
        task.add_done_callback(self.on_login_result)

    def on_login_result(self, task):
        self.connect_button.setEnabled(True)
        try:
            user = task.result()
            self.login_status.setText(
                f"Logged in as: {user.first_name} ({user.phone})")
            self.statusBar().showMessage(f"Logged in as {user.first_name}")
            self.fetch_initial_chats()
            self.update_search_history()
        except Exception as e:
            self.login_status.setText("Login failed.")
            self.statusBar().showMessage("Ready")
            QMessageBox.critical(self, "Error", f"Failed to connect: {e}")

    def fetch_initial_chats(self):
        logger.info("Fetching initial chat list after login...")

        async def fetch_coro():
            try:
                # Always try to fetch from Telegram
                chats_from_telegram = await self.telegram.fetch_chats()
                if chats_from_telegram:
                    save_chats(chats_from_telegram, self.user_phone)
                    save_last_update_timestamp(self.user_phone)
                    logger.info(
                        "Initial chat list fetched successfully from Telegram.")

                # Always load chats from the database, regardless of Telegram fetch
                chats_from_db = load_chats(self.user_phone)
                if chats_from_db:
                    logger.info(
                        f"Loaded {len(chats_from_db)} chats from database.")
                    return chats_from_db
                elif chats_from_telegram:
                    return chats_from_telegram
                else:
                    logger.info("No chats found in database or Telegram.")
                    return []
            except Exception as e:
                logger.error(f"Error fetching initial chats: {e}")
                # On error, still try to load from database
                chats_from_db = load_chats(self.user_phone)
                if chats_from_db:
                    logger.info(
                        f"Loaded {len(chats_from_db)} chats from database after error.")
                    return chats_from_db
                raise

        task = asyncio.ensure_future(fetch_coro())
        task.add_done_callback(self.display_chats)

    def update_chats(self):
        logger.info("Updating chat list...")

        async def fetch_chats_coro():
            try:
                last_update = load_last_update_timestamp(self.user_phone)
                new_chats = await self.telegram.fetch_new_chats(last_update)
                if new_chats:
                    existing_chats = load_chats(self.user_phone)
                    combined_chats = {chat[0]: chat for chat in (
                        existing_chats + new_chats)}.values()
                    save_chats(list(combined_chats), self.user_phone)
                    save_last_update_timestamp(self.user_phone)
                    logger.info(
                        f"Added {len(new_chats)} new chats to the database.")
                else:
                    logger.info("No new chats found.")
                chats = load_chats(self.user_phone)
                return chats
            except Exception as e:
                logger.error(f"Error fetching chats: {e}")
                raise

        task = asyncio.ensure_future(fetch_chats_coro())
        task.add_done_callback(self.display_chats)

    def display_chats(self, task):
        try:
            chats = task.result()
            self.chats = chats
            self.chats_list.clear()
            self.messages_chat_combo.clear()
            for chat_id, chat_name, username in chats:
                item_text = f"{chat_name} (ID: {chat_id})"
                if username:
                    item_text += f" (@{username})"
                self.chats_list.addItem(item_text)
                self.messages_chat_combo.addItem(item_text)
            self.statusBar().showMessage(f"Loaded {len(chats)} chats")
            logger.info(f"Displayed {len(chats)} chats in the GUI.")
        except Exception as e:
            self.statusBar().showMessage("Error occurred")
            QMessageBox.critical(self, "Error", f"Failed to load chats: {e}")

    async def fetch_coro(self, chat_id, chat_name, filter_type, filter_value):  # Changed to async
        try:
            # Check database messages first
            from database import load_messages
            messages, full_day_covered, _ = load_messages(
                chat_id, filter_type, filter_value, self.user_phone)

            if not messages or (filter_type == "specific_date" and not full_day_covered):
                if not messages:
                    logger.info(
                        "No messages found in database. Fetching from Telegram...")
                else:
                    logger.info(
                        "Incomplete messages for this date. Fetching from Telegram...")

            messages = await self.telegram.get_messages(chat_id, filter_type, filter_value, self.user_timezone, self.user_phone)
            if messages is None:
                return None

            result = ""
            if messages:
                for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                    local_time = timestamp.astimezone(self.user_timezone)
                    result += f"{i}. {sender}: {msg}\n   (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
                message_texts = [msg for _, msg, _, _ in messages]
                summary = await summarize_text(message_texts)  # Now awaited
                result += "=== Summary ===\n" + summary + "\n"
            else:
                result = "No messages found."
                # Log no messages found
                if filter_type == "recent_messages":
                    logger.info(
                        f"No messages found in the last {filter_value} messages for {chat_name}.")
                elif filter_type == "recent_days":
                    logger.info(
                        f"No messages found in the last {filter_value} days for {chat_name}.")
                elif filter_type == "specific_date":
                    logger.info(
                        f"No messages found on {filter_value} for {chat_name}.")
            return result
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            raise

    def fetch_chat_messages(self):
        selected_index = self.messages_chat_combo.currentIndex()
        if selected_index < 0 or not self.chats:
            QMessageBox.warning(self, "Selection Error",
                                "Please select a chat.")
            return

        chat = self.chats[selected_index]
        chat_id = chat[0]
        chat_name = chat[1]

        fetch_dialog = FetchMessagesDialog(
            self.telegram, chat_id, chat_name, self.user_timezone, self.user_phone, self)
        if fetch_dialog.exec():
            filter_type, filter_value = fetch_dialog.result
            self.messages_progress.setVisible(True)
            self.messages_progress.setRange(0, 0)
            self.messages_display.clear()

            # Log the start of message fetching
            if filter_type == "recent_messages":
                logger.info(f"Fetching recent messages for {chat_name}...")
            elif filter_type == "recent_days":
                logger.info(
                    f"Checking database for messages in {chat_name} for the last {filter_value} days...")
            elif filter_type == "specific_date":
                logger.info(
                    f"Checking database for messages in {chat_name} on {filter_value}...")

            task = asyncio.ensure_future(self.fetch_coro(
                chat_id, chat_name, filter_type, filter_value))  # Use the async coroutine
            task.add_done_callback(self.display_messages_in_tab)

    def display_messages_in_tab(self, task):
        self.messages_progress.setVisible(False)
        try:
            result = task.result()
            if result:
                self.messages_display.setText(result)
            else:
                self.messages_display.setText("No messages found.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to fetch messages: {e}")

    def search_username(self):
        username = self.search_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Input Error",
                                "Please enter a username.")
            return

        logger.info(f"Searching for username: {username}")

        async def search_coro():
            try:
                chats = load_chats(self.user_phone)
                chat_name, chat_id = search_by_username(username, chats)
                if chat_id:
                    save_search_history(username, self.user_phone)
                    logger.info(f"Found chat: {chat_name} (ID: {chat_id})")
                    return chat_name, chat_id
                else:
                    logger.info(f"No private chat found for {username}.")
                return None, None
            except Exception as e:
                logger.error(f"Error searching username: {e}")
                raise

        task = asyncio.ensure_future(search_coro())
        task.add_done_callback(self.display_search_result)

    def display_search_result(self, task):
        try:
            chat_name, chat_id = task.result()
            if chat_id:
                self.search_results.setText(
                    f"Found chat: {chat_name} (ID: {chat_id})\n")
                self.update_search_history()
                self.messages_chat_combo.setCurrentText(
                    f"{chat_name} (ID: {chat_id})")
                self.tabs.setCurrentWidget(self.messages_tab)
            else:
                self.search_results.setText(
                    f"No private chat found for {self.search_input.text()}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to search: {e}")

    def update_search_history(self):
        self.history_list.clear()
        history = load_search_history(self.user_phone)
        for _, username, timestamp in history:
            self.history_list.addItem(f"{username} (Searched at: {timestamp})")
        logger.info(f"Updated search history with {len(history)} entries.")

    def view_history_messages(self):
        selected = self.history_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Selection Error",
                                "Please select a search history entry.")
            return

        username = selected.text().split(" (Searched at:")[0]
        logger.info(f"Viewing messages for username from history: {username}")

        async def view_coro():
            try:
                chats = load_chats(self.user_phone)
                chat_name, chat_id = search_by_username(username, chats)
                if chat_id:
                    logger.info(f"Found chat: {chat_name} (ID: {chat_id})")
                else:
                    logger.info(f"No private chat found for {username}.")
                return chat_name, chat_id
            except Exception as e:
                logger.error(f"Error viewing history messages: {e}")
                raise

        task = asyncio.ensure_future(view_coro())
        task.add_done_callback(self.display_history_messages)

    def display_history_messages(self, task):
        try:
            chat_name, chat_id = task.result()
            if chat_id:
                self.messages_chat_combo.setCurrentText(
                    f"{chat_name} (ID: {chat_id})")
                self.tabs.setCurrentWidget(self.messages_tab)
            else:
                QMessageBox.warning(
                    self, "Error", f"No private chat found for the selected username.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to view messages: {e}")

    def delete_history_entry(self):
        selected = self.history_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Selection Error",
                                "Please select a search history entry.")
            return

        username = selected.text().split(" (Searched at:")[0]
        history = load_search_history(self.user_phone)
        entry_id = next(entry[0] for entry in history if entry[1] == username)

        reply = QMessageBox.question(self, "Confirm", f"Delete search entry for {username}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_search_history_entry(entry_id)
            self.update_search_history()
            logger.info(f"Search entry for {username} deleted successfully.")

    def delete_specific_history(self):
        history = load_search_history(self.user_phone)
        if not history:
            QMessageBox.information(
                self, "Info", "No search history to delete.")
            logger.info("No search history to delete.")
            return

        items = [f"{entry[1]} (Searched at: {entry[2]})" for entry in history]
        item, ok = QInputDialog.getItem(
            self, "Select Entry", "Select search entry to delete:", items, 0, False)
        if ok and item:
            username = item.split(" (Searched at:")[0]
            entry_id = next(entry[0]
                            for entry in history if entry[1] == username)
            delete_search_history_entry(entry_id)
            self.update_search_history()
            logger.info(f"Search entry for {username} deleted successfully.")

    def delete_all_history(self):
        history = load_search_history(self.user_phone)
        if not history:
            QMessageBox.information(
                self, "Info", "No search history to delete.")
            logger.info("No search history to delete.")
            return

        reply = QMessageBox.question(self, "Confirm", "Delete all search history? This action cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_all_search_history(self.user_phone)
            self.update_search_history()
            logger.info("All search history deleted successfully.")
        else:
            logger.info("Deletion of all search history canceled.")

    def delete_chat_messages(self):
        history = load_search_history(self.user_phone)
        if not history:
            QMessageBox.information(
                self, "Info", "No search history to select from.")
            logger.info(
                "No search history to select from for deleting messages.")
            return

        items = [f"{entry[1]} (Searched at: {entry[2]})" for entry in history]
        item, ok = QInputDialog.getItem(
            self, "Select Chat", "Select chat to delete messages:", items, 0, False)
        if ok and item:
            username = item.split(" (Searched at:")[0]
            chats = load_chats(self.user_phone)
            chat_name, chat_id = search_by_username(username, chats)
            if not chat_id:
                QMessageBox.warning(
                    self, "Error", f"No chat found for username {username}.")
                logger.info(f"No chat found for username {username}.")
                return

            logger.info(
                f"Selected chat for deletion: {chat_name} (ID: {chat_id})")

            options = [
                "Delete a specific number of recent messages",
                "Delete messages from a specific date",
                "Delete all messages"
            ]
            option, ok = QInputDialog.getItem(
                self, "Delete Messages", f"Select deletion option for {chat_name}:", options, 0, False)
            if ok and option:
                if option.startswith("Delete a specific number"):
                    count, ok = QInputDialog.getInt(
                        self, "Input", "Enter number of recent messages to delete:", 10, 1)
                    if ok:
                        reply = QMessageBox.question(self, "Confirm", f"Delete the last {count} messages for {chat_name}?",
                                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.Yes:
                            deleted_count = delete_messages(
                                chat_id, self.user_phone, num_messages=count)
                            QMessageBox.information(
                                self, "Result", f"Deleted {deleted_count} messages.")
                            logger.info(
                                f"Deleted {deleted_count} recent messages for {chat_name}.")
                        else:
                            logger.info(
                                f"Deletion of {count} recent messages for {chat_name} canceled.")
                elif option.startswith("Delete messages from"):
                    date, ok = QInputDialog.getText(
                        self, "Input", "Enter date (e.g., 10 March 2025):")
                    if ok:
                        try:
                            datetime.strptime(date, "%d %B %Y")
                            reply = QMessageBox.question(self, "Confirm", f"Delete messages from {date} for {chat_name}?",
                                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            if reply == QMessageBox.StandardButton.Yes:
                                deleted_count = delete_messages(
                                    chat_id, self.user_phone, specific_date=date)
                                QMessageBox.information(
                                    self, "Result", f"Deleted {deleted_count} messages.")
                                logger.info(
                                    f"Deleted {deleted_count} messages from {date} for {chat_name}.")
                            else:
                                logger.info(
                                    f"Deletion of messages from {date} for {chat_name} canceled.")
                        except ValueError:
                            QMessageBox.warning(
                                self, "Input Error", "Invalid date format. Use 'DD Month YYYY'.")
                            logger.error(
                                "Invalid date format entered for message deletion.")
                elif option.startswith("Delete all"):
                    reply = QMessageBox.question(self, "Confirm", f"Delete all messages for {chat_name}?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        deleted_count = delete_messages(
                            chat_id, self.user_phone)
                        QMessageBox.information(
                            self, "Result", f"Deleted {deleted_count} messages.")
                        logger.info(
                            f"Deleted {deleted_count} messages for {chat_name}.")
                    else:
                        logger.info(
                            f"Deletion of all messages for {chat_name} canceled.")

    def refresh_chats(self):
        self.refresh_status.setText("Refreshing chat list...")
        logger.info("Refreshing chat list...")

        async def refresh_coro():
            try:
                chats = await self.telegram.fetch_chats()
                save_chats(chats, self.user_phone)
                save_last_update_timestamp(self.user_phone)
                logger.info("Chat list refreshed successfully.")
                return chats
            except Exception as e:
                logger.error(f"Error refreshing chats: {e}")
                raise

        task = asyncio.ensure_future(refresh_coro())
        task.add_done_callback(self.on_refresh_result)

    def on_refresh_result(self, task):
        try:
            chats = task.result()
            self.refresh_status.setText("Chat list refreshed successfully.")
            self.update_chats()
        except Exception as e:
            self.refresh_status.setText("Failed to refresh chats.")
            QMessageBox.critical(
                self, "Error", f"Failed to refresh chats: {e}")

    def closeEvent(self, event):
        if self.telegram:
            async def disconnect_coro():
                try:
                    await self.telegram.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")

            task = asyncio.ensure_future(disconnect_coro())
            self.loop.run_until_complete(task)
        event.accept()


def run_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow, QWidget, QDialog { 
            background-color: #2A2A2E; 
            color: #D5D5D5; 
            font-family: 'Segoe UI', Arial, sans-serif; 
            font-size: 13px; 
        }
        QLineEdit, QComboBox, QTextEdit, QListWidget { 
            background-color: #3A3A3E; 
            color: #D5D5D5; 
            border: 1px solid #5A5A5E; 
            padding: 5px; 
            border-radius: 4px; 
        }
        QComboBox::drop-down { 
            border: none; 
        }
        QPushButton { 
            background-color: #8A00C2; 
            color: white; 
            border-radius: 4px; 
            padding: 8px; 
            font-weight: bold; 
        }
        QPushButton:hover { 
            background-color: #A855F7; 
        }
        QPushButton[delete="true"] { 
            background-color: #F44336; 
        }
        QPushButton[delete="true"]:hover { 
            background-color: #EF5350; 
        }
        QFrame { 
            background-color: #3A3A3E; 
            border: 1px solid #5A5A5E; 
            padding: 10px; 
            border-radius: 4px; 
        }
        QLabel { 
            color: #B0BEC5; 
        }
        QMessageBox { 
            background-color: #2A2A2E; 
            color: #D5D5D5; 
        }
        QTabWidget::pane { 
            border: 1px solid #5A5A5E; 
            background: #2A2A2E; 
        }
        QTabBar::tab { 
            background: #3A3A3E; 
            color: #D5D5D5; 
            padding: 8px 16px; 
            border-top-left-radius: 4px; 
            border-top-right-radius: 4px; 
        }
        QTabBar::tab:selected { 
            background: #8A00C2; 
            color: white; 
        }
        QStatusBar { 
            background-color: #3A3A3E; 
            color: #D5D5D5; 
        }
        QProgressBar { 
            border: 1px solid #5A5A5E; 
            background-color: #3A3A3E; 
            color: #D5D5D5; 
            border-radius: 4px; 
        }
        QProgressBar::chunk { 
            background-color: #8A00C2; 
            border-radius: 4px; 
        }
    """)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow(loop)
    window.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    run_gui()
