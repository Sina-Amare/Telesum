from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QComboBox, QTextEdit, QListWidget, QInputDialog,
                             QMessageBox, QLabel, QProgressBar, QFrame, QGridLayout, QDialog)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import asyncio
import sys
import qasync
from telegram_client import TelegramManager
from database import (setup_database, save_chats, load_chats, save_search_history, load_search_history,
                      delete_search_history_entry, delete_all_search_history, delete_messages, save_last_update_timestamp, load_last_update_timestamp, load_messages)
from utils import search_by_username
from ai_processor import summarize_text
from config import API_ID, API_HASH, VERBOSE_LOGGING
from datetime import datetime
import pytz
import logging
import logging.handlers
import queue
import concurrent.futures

# Set up professional logging with QueueHandler
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if VERBOSE_LOGGING else logging.INFO)

# Custom logging handler to display logs in QTextEdit using a Queue


class QueueTextEditHandler(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.queue = queue.Queue()
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        self.worker = LogWorker(self.queue, self.text_edit)
        self.worker.start()

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)


class LogWorker(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, queue, text_edit):
        super().__init__()
        self.queue = queue
        self.text_edit = text_edit
        self.update_signal.connect(self.append_log)
        self.running = True

    def run(self):
        while self.running:
            try:
                msg = self.queue.get(timeout=1)
                self.update_signal.emit(msg)
                self.queue.task_done()
            except queue.Empty:
                continue

    def append_log(self, msg):
        self.text_edit.append(msg)
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum())

    def stop(self):
        self.running = False
        self.wait()


# Configure logging to use QueueHandler
queue_handler = None


def setup_logging(text_edit):
    global queue_handler
    queue_handler = QueueTextEditHandler(text_edit)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))
    logger.handlers = []  # Clear any existing handlers
    logger.addHandler(queue_handler)


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
        filter_label.setStyleSheet("font-weight: bold; color: #333333;")
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
        self.fetch_button.setStyleSheet(
            "background-color: #4CAF50; color: white;")

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("background-color: #F44336; color: white;")

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


class MainWindow(QMainWindow):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.setWindowTitle("TeleSam - Telegram Chat Manager")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #F5F5F5;")
        self.telegram = None
        self.user_phone = None
        self.user_timezone = None
        self.chats = []
        self.is_fetching = False
        self.fetch_task = None
        self.current_chat_id = None
        self.current_chat_name = None
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
        phone_label.setStyleSheet("font-weight: bold; color: #333333;")
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
        tz_label.setStyleSheet("font-weight: bold; color: #333333;")
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
        self.connect_button.setStyleSheet(
            "background-color: #4CAF50; color: white;")
        layout.addWidget(self.connect_button)

        self.login_status = QLabel(
            "Enter your phone number and timezone to connect.")
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
        chats_label.setStyleSheet("font-weight: bold; color: #333333;")
        self.messages_chat_combo = QComboBox()
        self.messages_chat_combo.setMinimumWidth(300)
        chats_layout.addWidget(chats_label)
        chats_layout.addWidget(self.messages_chat_combo)
        chats_frame.setLayout(chats_layout)
        layout.addWidget(chats_frame)

        button_layout = QHBoxLayout()
        fetch_button = QPushButton("Fetch Messages for Selected Chat")
        fetch_button.clicked.connect(self.fetch_chat_messages)
        fetch_button.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(fetch_button)

        self.cancel_button = QPushButton("Cancel Fetching")
        self.cancel_button.clicked.connect(self.cancel_fetching)
        self.cancel_button.setVisible(False)
        self.cancel_button.setStyleSheet(
            "background-color: #F44336; color: white;")
        button_layout.addWidget(
            self.cancel_button, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(button_layout)

        self.messages_display = QTextEdit()
        self.messages_display.setReadOnly(True)
        self.messages_display.setFont(QFont("Arial", 10))
        layout.addWidget(self.messages_display)

        self.messages_progress = QProgressBar()
        self.messages_progress.setVisible(False)
        self.messages_progress.setRange(0, 100)
        self.messages_progress.setValue(0)
        self.messages_progress.setStyleSheet(
            "QProgressBar { border: 1px solid grey; border-radius: 5px; } QProgressBar::chunk { background-color: #4CAF50; }")
        layout.addWidget(self.messages_progress)

        self.messages_status_label = QLabel("Ready to fetch messages.")
        layout.addWidget(self.messages_status_label)

        self.messages_tab.setLayout(layout)

    def setup_search_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        search_layout = QHBoxLayout()
        search_label = QLabel("Username:")
        search_label.setStyleSheet("font-weight: bold; color: #333333;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., @username")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_username)
        search_button.setStyleSheet("background-color: #4CAF50; color: white;")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_frame.setLayout(search_layout)
        layout.addWidget(search_frame)

        self.search_results_list = QListWidget()
        self.search_results_list.itemClicked.connect(
            self.on_search_result_clicked)
        layout.addWidget(self.search_results_list)

        self.search_tab.setLayout(layout)

    def setup_search_history_tab(self):
        self.history_layout = QVBoxLayout()
        self.history_layout.setContentsMargins(20, 20, 20, 20)
        self.history_layout.setSpacing(15)

        self.history_list = QListWidget()
        self.history_layout.addWidget(self.history_list)

        button_layout = QHBoxLayout()
        view_button = QPushButton("View Messages")
        view_button.clicked.connect(self.view_history_messages)
        view_button.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(view_button)
        self.history_layout.addLayout(button_layout)

        self.messages_frame = QFrame()
        self.messages_frame.setVisible(False)
        messages_layout = QVBoxLayout()

        self.history_messages_display = QTextEdit()
        self.history_messages_display.setReadOnly(True)
        self.history_messages_display.setFont(QFont("Arial", 10))
        messages_layout.addWidget(self.history_messages_display)

        manage_buttons_layout = QHBoxLayout()
        delete_recent_button = QPushButton("Delete Recent Messages")
        delete_recent_button.clicked.connect(self.delete_recent_messages)
        delete_recent_button.setStyleSheet(
            "background-color: #F44336; color: white;")
        manage_buttons_layout.addWidget(delete_recent_button)

        delete_date_button = QPushButton("Delete Messages from Date")
        delete_date_button.clicked.connect(self.delete_messages_from_date)
        delete_date_button.setStyleSheet(
            "background-color: #F44336; color: white;")
        manage_buttons_layout.addWidget(delete_date_button)

        delete_all_button = QPushButton("Delete All Messages")
        delete_all_button.clicked.connect(self.delete_all_messages)
        delete_all_button.setStyleSheet(
            "background-color: #F44336; color: white;")
        manage_buttons_layout.addWidget(delete_all_button)

        back_button = QPushButton("Back to List")
        back_button.clicked.connect(self.back_to_history_list)
        back_button.setStyleSheet("background-color: #2196F3; color: white;")
        manage_buttons_layout.addWidget(back_button)

        messages_layout.addLayout(manage_buttons_layout)
        self.messages_frame.setLayout(messages_layout)
        self.history_layout.addWidget(self.messages_frame)

        self.history_status_label = QLabel(
            "Select a chat to view saved messages.")
        self.history_layout.addWidget(self.history_status_label)

        self.search_history_tab.setLayout(self.history_layout)

    def setup_refresh_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        refresh_button = QPushButton("Refresh Chat List")
        refresh_button.clicked.connect(self.refresh_chats)
        refresh_button.setStyleSheet(
            "background-color: #4CAF50; color: white;")
        layout.addWidget(refresh_button)

        self.refresh_status = QLabel("Click to refresh the chat list.")
        layout.addWidget(self.refresh_status)

        layout.addStretch()
        self.refresh_tab.setLayout(layout)

    def setup_logs_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        refresh_logs_button = QPushButton("Refresh Logs")
        refresh_logs_button.clicked.connect(self.update_logs)
        refresh_logs_button.setStyleSheet(
            "background-color: #4CAF50; color: white;")
        layout.addWidget(refresh_logs_button)

        self.logs_tab.setLayout(layout)

        setup_logging(self.logs_text)

    def update_logs(self):
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum())

    def update_search_history(self):
        self.history_list.clear()
        chats = load_chats(self.user_phone)
        if not chats:
            self.history_list.addItem("No chats found.")
            return

        found = False
        for chat_id, chat_name, username in chats:
            messages, _, _ = load_messages(
                chat_id, "recent_messages", 1, self.user_phone)
            if messages:
                found = True
                display_text = f"{chat_name} (ID: {chat_id})"
                if username:
                    display_text += f" (@{username})"
                self.history_list.addItem(display_text)
                logger.info(f"Added {chat_name} to Search History list")

        if not found:
            self.history_list.addItem("No chats with saved messages found.")
            self.history_status_label.setText(
                "No chats with saved messages found.")

    def connect_telegram(self):
        self.user_phone = self.phone_input.text().strip()
        if not (self.user_phone.startswith("+") and self.user_phone[1:].isdigit()):
            QMessageBox.warning(
                self, "Input Error", "Invalid phone number. Use the format +989123456789")
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
            QMessageBox.critical(self, "Error", f"Connection error: {e}")

    def fetch_initial_chats(self):
        logger.info("Fetching initial chat list after login...")
        self.statusBar().showMessage("Fetching chats...")

        async def fetch_coro():
            try:
                chats_from_telegram = await self.telegram.fetch_chats()
                if chats_from_telegram:
                    save_chats(chats_from_telegram, self.user_phone)
                    save_last_update_timestamp(self.user_phone)
                    logger.info(
                        "Initial chat list fetched successfully from Telegram.")

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
        self.statusBar().showMessage("Updating chats...")

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

            batch_size = 20
            self.chat_batch = chats
            self.current_batch_index = 0

            def load_next_batch():
                start = self.current_batch_index
                end = min(start + batch_size, len(self.chat_batch))
                for i in range(start, end):
                    chat_id, chat_name, username = self.chat_batch[i]
                    item_text = f"{chat_name} (ID: {chat_id})"
                    if username:
                        item_text += f" (@{username})"
                    self.chats_list.addItem(item_text)
                    self.messages_chat_combo.addItem(item_text)
                self.current_batch_index = end

                self.statusBar().showMessage(
                    f"Loaded {self.current_batch_index} of {len(self.chat_batch)} chats")

                if self.current_batch_index < len(self.chat_batch):
                    QTimer.singleShot(50, load_next_batch)
                else:
                    self.statusBar().showMessage(
                        f"Loaded {len(self.chat_batch)} chats")
                    logger.info(
                        f"Displayed {len(self.chat_batch)} chats in the GUI.")

            load_next_batch()

        except Exception as e:
            self.statusBar().showMessage("An error occurred")
            QMessageBox.critical(self, "Error", f"Error loading chats: {e}")

    async def update_progress(self, progress):
        def set_progress():
            self.messages_progress.setValue(int(progress))
            QApplication.processEvents()
        await asyncio.get_event_loop().run_in_executor(None, set_progress)

    async def fetch_coro(self, chat_id, chat_name, filter_type, filter_value):
        logger.info(
            f"Starting fetch_coro for chat: {chat_name} (ID: {chat_id})")
        try:
            logger.info("Fetching messages from Telegram...")
            messages = await self.telegram.get_messages(
                chat_id, filter_type, filter_value, self.user_timezone, self.user_phone,
                progress_callback=self.update_progress
            )
            logger.info(
                f"get_messages returned {len(messages) if messages else 0} messages.")

            if messages is None:
                logger.warning("get_messages returned None.")
                return "No messages found."

            await self.update_progress(90)  # After fetching, set to 90%
            self.messages_status_label.setText(
                "Messages fetched, analyzing with AI...")

            result = ""
            if messages:
                logger.info(
                    f"Processing {len(messages)} messages for display...")
                for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                    local_time = timestamp.astimezone(self.user_timezone)
                    result += f"{i}. {sender}: {msg}\n   (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
                message_texts = [msg for _, msg, _, _ in messages]
                logger.info("Summarizing messages...")
                summary = await summarize_text(message_texts)
                result += "=== Summary ===\n" + summary + "\n"

                # Update progress to 100% after summarization
                await self.update_progress(100)
            else:
                result = "No messages found."
                logger.info("No messages found after processing.")
                await self.update_progress(100)

            return result
        except asyncio.CancelledError:
            logger.info(f"Message fetching for {chat_name} was cancelled.")
            return "Message fetching cancelled by user."
        except Exception as e:
            logger.error(f"Error in fetch_coro: {e}")
            raise

    def fetch_chat_messages(self):
        if self.is_fetching:
            QMessageBox.warning(self, "Operation in Progress",
                                "A fetch operation is already in progress. Please wait or cancel it.")
            return

        selected_index = self.messages_chat_combo.currentIndex()
        if selected_index < 0 or not self.chats:
            QMessageBox.warning(self, "Selection Error",
                                "Please select a chat.")
            return

        chat = self.chats[selected_index]
        chat_id = chat[0]
        chat_name = chat[1]
        username = chat[2]

        search_term = username if username else chat_name
        save_search_history(search_term, self.user_phone)
        self.update_search_history()

        fetch_dialog = FetchMessagesDialog(
            self.telegram, chat_id, chat_name, self.user_timezone, self.user_phone, self)
        if fetch_dialog.exec():
            filter_type, filter_value = fetch_dialog.result
            self.is_fetching = True
            self.messages_progress.setVisible(True)
            self.messages_progress.setValue(0)
            self.cancel_button.setVisible(True)
            self.messages_display.clear()
            self.messages_status_label.setText("Fetching messages...")

            if filter_type == "recent_messages":
                logger.info(f"Fetching recent messages for {chat_name}...")
            elif filter_type == "recent_days":
                logger.info(
                    f"Fetching messages in {chat_name} for the last {filter_value} days...")
            elif filter_type == "specific_date":
                logger.info(
                    f"Fetching messages in {chat_name} on {filter_value}...")

            self.fetch_task = asyncio.ensure_future(self.fetch_coro(
                chat_id, chat_name, filter_type, filter_value))
            self.fetch_task.add_done_callback(self.display_messages_in_tab)

    def cancel_fetching(self):
        if self.is_fetching and self.fetch_task:
            self.fetch_task.cancel()
            self.is_fetching = False
            self.cancel_button.setVisible(False)
            self.messages_progress.setVisible(False)
            self.messages_display.setText("Fetching cancelled by user.")
            self.messages_status_label.setText("Fetching cancelled.")

    def display_messages_in_tab(self, task):
        self.is_fetching = False
        self.cancel_button.setVisible(False)
        self.messages_progress.setVisible(False)
        try:
            result = task.result()
            if result:
                self.messages_display.setText(result)
                if "cancelled" in result.lower():
                    self.messages_status_label.setText("Fetching cancelled.")
                else:
                    self.messages_status_label.setText(
                        "Messages fetched successfully.")
            else:
                self.messages_display.setText("No messages found.")
                self.messages_status_label.setText("No messages found.")
        except Exception as e:
            self.messages_status_label.setText("Error fetching messages.")
            logger.error(f"Error displaying messages in tab: {e}")
            QMessageBox.critical(
                self, "Error", f"Error fetching messages: {e}")

    def search_username(self):
        username = self.search_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Input Error",
                                "Username cannot be empty.")
            return

        self.search_results_list.clear()
        chat_name, chat_id = search_by_username(username, self.chats)
        if chat_id:
            display_text = f"{chat_name} (ID: {chat_id})"
            self.search_results_list.addItem(display_text)
            logger.info(
                f"Found chat for username {username}: {chat_name} (ID: {chat_id})")
        else:
            self.search_results_list.addItem("No chat found.")
            logger.info(f"No chat found for username {username}")

    def on_search_result_clicked(self, item):
        if "No chat found" in item.text():
            return

        chat_name = item.text().split(" (ID:")[0]
        chat_id = int(item.text().split("(ID: ")[1].split(")")[0])
        username = None
        for chat in self.chats:
            if chat[0] == chat_id:
                username = chat[2]
                break

        if username:
            search_term = username
        else:
            search_term = chat_name

        save_search_history(search_term, self.user_phone)
        self.update_search_history()

        self.current_chat_id = chat_id
        self.current_chat_name = chat_name
        self.tabs.setCurrentWidget(self.messages_tab)
        self.messages_chat_combo.setCurrentText(item.text())
        self.fetch_chat_messages()

    def view_history_messages(self):
        selected_item = self.history_list.currentItem()
        if not selected_item or "No chats" in selected_item.text():
            QMessageBox.warning(self, "Selection Error",
                                "Please select a chat with saved messages.")
            return

        chat_id = int(selected_item.text().split("(ID: ")[1].split(")")[0])
        chat_name = selected_item.text().split(" (ID:")[0]

        self.current_chat_id = chat_id
        self.current_chat_name = chat_name

        messages, _, _ = load_messages(
            chat_id, "recent_messages", 100, self.user_phone, self.user_timezone)
        if messages:
            result = ""
            for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                local_time = timestamp.astimezone(self.user_timezone)
                result += f"{i}. {sender}: {msg}\n   (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
            self.history_messages_display.setText(result)
            self.history_status_label.setText(
                f"Showing messages for {chat_name}")
        else:
            self.history_messages_display.setText("No messages found.")
            self.history_status_label.setText("No messages found.")

        self.history_list.setVisible(False)
        self.messages_frame.setVisible(True)

    def delete_recent_messages(self):
        if not self.current_chat_id:
            QMessageBox.warning(self, "Selection Error", "No chat selected.")
            return

        count, ok = QInputDialog.getInt(
            self, "Delete Recent Messages", "Enter number of recent messages to delete (e.g., 10):", 10, 1)
        if not ok:
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the last {count} messages for {self.current_chat_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = delete_messages(
                self.current_chat_id, self.user_phone, num_messages=count)
            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} recent messages for {self.current_chat_name}")
                QMessageBox.information(
                    self, "Success", f"Deleted {deleted_count} recent messages.")
            else:
                logger.info(
                    f"No recent messages found for {self.current_chat_name}")
                QMessageBox.information(
                    self, "Info", "No recent messages found.")
            self.view_history_messages()
            self.update_search_history()

    def delete_messages_from_date(self):
        if not self.current_chat_id:
            QMessageBox.warning(self, "Selection Error", "No chat selected.")
            return

        date, ok = QInputDialog.getText(
            self, "Delete Messages from Date", "Enter date to delete messages from (e.g., 10 March 2025):")
        if not ok:
            return

        try:
            datetime.strptime(date, "%d %B %Y")
        except ValueError:
            QMessageBox.warning(
                self, "Input Error", "Invalid date format. Use 'DD Month YYYY' (e.g., '10 March 2025').")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete messages from {date} for {self.current_chat_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = delete_messages(
                self.current_chat_id, self.user_phone, specific_date=date, user_timezone=self.user_timezone)
            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} messages from {date} for {self.current_chat_name}")
                QMessageBox.information(
                    self, "Success", f"Deleted {deleted_count} messages from {date}.")
            else:
                logger.info(
                    f"No messages found from {date} for {self.current_chat_name}")
                QMessageBox.information(
                    self, "Info", f"No messages found from {date}.")
            self.view_history_messages()
            self.update_search_history()

    def delete_all_messages(self):
        if not self.current_chat_id:
            QMessageBox.warning(self, "Selection Error", "No chat selected.")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete all messages for {self.current_chat_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = delete_messages(
                self.current_chat_id, self.user_phone)
            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} messages for {self.current_chat_name}")
                QMessageBox.information(
                    self, "Success", f"Deleted {deleted_count} messages.")
            else:
                logger.info(f"No messages found for {self.current_chat_name}")
                QMessageBox.information(self, "Info", "No messages found.")
            self.view_history_messages()
            self.update_search_history()

    def back_to_history_list(self):
        self.messages_frame.setVisible(False)
        self.history_list.setVisible(True)
        self.history_status_label.setText(
            "Select a chat to view saved messages.")
        self.update_search_history()

    def refresh_chats(self):
        self.refresh_status.setText("Refreshing chat list...")
        self.statusBar().showMessage("Refreshing chats...")
        self.update_chats()

    def closeEvent(self, event):
        if self.telegram:
            asyncio.ensure_future(self.telegram.disconnect())
        if queue_handler and queue_handler.worker:
            queue_handler.worker.stop()
        event.accept()


def run_gui():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow(loop)
    window.show()
    with loop:
        sys.exit(loop.run_forever())
