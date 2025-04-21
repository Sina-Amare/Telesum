from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QComboBox, QTextEdit, QListWidget, QInputDialog,
                             QMessageBox, QLabel, QProgressBar, QFrame, QGridLayout, QDialog, QTableWidget,
                             QTableWidgetItem, QStyle, QStyleFactory)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
import asyncio
import sys
import qasync
from telegram_client import TelegramManager
from database import (setup_database, save_chats, load_chats, save_search_history, load_search_history,
                      delete_search_history_entry, delete_all_search_history, delete_messages,
                      save_last_update_timestamp, load_last_update_timestamp, load_messages,
                      save_user_settings, load_user_settings, load_all_users, load_users_with_search_history, load_chats_with_messages)
from utils import search_by_username
from ai_processor import summarize_text
from config import VERBOSE_LOGGING
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

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))

    logger.handlers = []  # Clear any existing handlers
    logger.addHandler(queue_handler)
    logger.addHandler(stream_handler)


# Updated FetchMessagesDialog init_ui to increase output box size
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
        self.setMinimumSize(600, 400)  # Increased dialog size
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        filter_frame = QFrame()
        filter_frame.setMinimumHeight(150)
        filter_layout = QGridLayout()
        filter_layout.setSpacing(20)

        filter_label = QLabel("Message Filter:")
        filter_label.setMinimumWidth(200)
        filter_label.setMinimumHeight(50)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Recent messages (e.g., last 10 messages)",
            "Messages from recent days (e.g., last 7 days)",
            "Messages from a specific date (e.g., 10 March 2025)"
        ])
        self.filter_combo.currentIndexChanged.connect(
            self.update_placeholder_text)
        self.filter_combo.setMinimumWidth(400)
        self.filter_combo.setMinimumHeight(50)

        self.value_input = QLineEdit()
        self.value_input.setMinimumWidth(400)
        self.value_input.setMinimumHeight(50)
        self.update_placeholder_text()

        self.fetch_button = QPushButton("📥 Fetch Messages")
        self.fetch_button.clicked.connect(self.fetch_messages)
        self.fetch_button.setMinimumHeight(50)

        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setMinimumHeight(50)

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

    def update_placeholder_text(self):
        filter_index = self.filter_combo.currentIndex()
        if filter_index == 0:
            self.value_input.setPlaceholderText(
                "e.g., 10 for last 10 messages")
        elif filter_index == 1:
            self.value_input.setPlaceholderText("e.g., 7 for last 7 days")
        else:
            self.value_input.setPlaceholderText("e.g., 10 March 2025")

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
        self.setMinimumSize(1000, 700)
        self.is_dark_mode = True
        self.init_ui()
        self.apply_stylesheet()

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

        self.telegram = None
        self.user_phone = None
        self.user_timezone = None
        self.chats = []
        self.is_fetching = False
        self.fetch_task = None
        self.current_chat_id = None
        self.current_chat_name = None

    def apply_stylesheet(self):
        if self.is_dark_mode:
            stylesheet = """
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1B263B, stop:1 #2F0F5E
                );
                color: #E0E0E0;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QTabWidget::pane {
                background-color: #1B263B;
                border: none;
            }
            QTabBar::tab {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2F0F5E, stop:1 #1B263B
                );
                color: #E0E0E0;
                padding: 14px 28px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13pt;
                font-weight: 600;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #1B263B
                );
                border-bottom: 4px solid #9B59B6;
                color: #FFFFFF;
            }
            QTabBar::tab:!selected {
                background: #2F0F5E;
            }
            QTabBar::tab:hover {
                background: #3A1A6E;
            }
            QFrame {
                background-color: #2A2A4A;
                border: 1px solid #404040;
                border-radius: 12px;
                padding: 20px;
                margin: 10px;
            }
            QLabel {
                color: #E0E0E0;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13pt;
                font-weight: 500;
                padding: 8px;
                min-width: 150px;
                min-height: 40px;
                text-align: left;
            }
            QLineEdit {
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: 1px solid #505050;
                border-radius: 10px;
                padding: 12px 18px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                min-width: 350px;
                min-height: 40px;
                text-align: left;
            }
            QLineEdit:focus {
                border: 2px solid #9B59B6;
                background-color: #40406A;
            }
            QLineEdit:disabled {
                background-color: #2A2A4A;
                color: #B0BEC5;
            }
            QComboBox {
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: 1px solid #505050;
                border-radius: 10px;
                padding: 12px 18px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                min-width: 350px;
                min-height: 40px;
            }
            QComboBox:hover {
                background-color: #40406A;
                border: 1px solid #606080;
            }
            QComboBox::drop-down {
                width: 30px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 12px;
                height: 12px;
                margin-right: 10px;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #E0E0E0;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A5A;
                color: #E0E0E0;
                selection-background-color: #9B59B6;
                selection-color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 12px;
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #40406A;
                color: #E0E0E0;
            }
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #6A1B9A
                );
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                font-weight: 600;
                transition: background-color 0.2s;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #AB69C6, stop:1 #7A2BAA
                );
            }
            QPushButton:pressed {
                background: #6A1B9A;
            }
            QPushButton[delete="true"] {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E74C3C, stop:1 #C0392B
                );
            }
            QPushButton[delete="true"]:hover {
                background: #F75C4C;
            }
            QPushButton[delete="true"]:pressed {
                background: #B0291B;
            }
            QTextEdit {
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: 1px solid #505050;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14pt;
            }
            QListWidget {
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: 1px solid #505050;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QListWidget::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #40406A;
            }
            QTableWidget {
                background-color: #3A3A5A;
                color: #E0E0E0;
                border: 1px solid #505050;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QTableWidget::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QTableWidget::item:hover {
                background-color: #40406A;
            }
            QHeaderView::section {
                background-color: #3A3A5A;
                color: #B0BEC5;
                padding: 6px;
                border: 1px solid #505050;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 10px;
                background-color: #3A3A5A;
                text-align: center;
                color: #E0E0E0;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #6A1B9A
                );
                border-radius: 10px;
            }
            QStatusBar {
                background: #2F0F5E;
                color: #B0BEC5;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
                padding: 8px;
            }
            """
        else:
            stylesheet = """
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E0E0E0, stop:1 #FFFFFF
                );
                color: #212121;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QTabWidget::pane {
                background-color: #FFFFFF;
                border: none;
            }
            QTabBar::tab {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D0D0D0, stop:1 #E0E0E0
                );
                color: #616161;
                padding: 14px 28px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13pt;
                font-weight: 600;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: #F5F5F5;
                border-bottom: 4px solid #9B59B6;
                color: #212121;
            }
            QTabBar::tab:!selected {
                background: #D0D0D0;
            }
            QTabBar::tab:hover {
                background: #E5E5E5;
            }
            QFrame {
                background-color: #F5F5F5;
                border: 1px solid #B0BEC5;
                border-radius: 12px;
                padding: 20px;
                margin: 10px;
            }
            QLabel {
                color: #212121;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13pt;
                font-weight: 500;
                padding: 8px;
                min-width: 150px;
                min-height: 40px;
                text-align: left;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                padding: 12px 18px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                min-width: 350px;
                min-height: 40px;
                text-align: left;
            }
            QLineEdit:focus {
                border: 2px solid #9B59B6;
                background-color: #FAFAFA;
            }
            QLineEdit:disabled {
                background-color: #E0E0E0;
                color: #616161;
            }
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                padding: 12px 18px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                min-width: 350px;
                min-height: 40px;
            }
            QComboBox:hover {
                background-color: #FAFAFA;
                border: 1px solid #9E9E9E;
            }
            QComboBox::drop-down {
                width: 30px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 12px;
                height: 12px;
                margin-right: 10px;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #212121;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #212121;
                selection-background-color: #9B59B6;
                selection-color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0px;
                margin: 0px;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                padding: 12px;
                background-color: #FFFFFF;
                color: #212121;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #FAFAFA;
                color: #212121;
            }
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #6A1B9A
                );
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                font-weight: 600;
                transition: background-color 0.2s;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #AB69C6, stop:1 #7A2BAA
                );
            }
            QPushButton:pressed {
                background: #6A1B9A;
            }
            QPushButton[delete="true"] {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E74C3C, stop:1 #C0392B
                );
            }
            QPushButton[delete="true"]:hover {
                background: #F75C4C;
            }
            QPushButton[delete="true"]:pressed {
                background: #B0291B;
            }
            QTextEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14pt;
            }
            QListWidget {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QListWidget::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #FAFAFA;
            }
            QTableWidget {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QTableWidget::item:selected {
                background-color: #9B59B6;
                color: #FFFFFF;
            }
            QTableWidget::item:hover {
                background-color: #FAFAFA;
            }
            QHeaderView::section {
                background-color: #E0E0E0;
                color: #616161;
                padding: 6px;
                border: 1px solid #B0BEC5;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
            }
            QProgressBar {
                border: 1px solid #B0BEC5;
                border-radius: 10px;
                background-color: #FFFFFF;
                text-align: center;
                color: #212121;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B59B6, stop:1 #6A1B9A
                );
                border-radius: 10px;
            }
            QStatusBar {
                background: #E0E0E0;
                color: #616161;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11pt;
                padding: 8px;
            }
            """
        self.setStyleSheet(stylesheet)
        FetchMessagesDialog.setStyleSheet(self, stylesheet)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_stylesheet()
        self.theme_toggle_button.setText(
            "🌙 Dark Mode" if not self.is_dark_mode else "☀️ Light Mode")

    # Updated setup_login_tab method to improve layout and styling

    def setup_login_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(50)

        # Theme Toggle Button
        self.theme_toggle_button = QPushButton("🌙 Dark Mode")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        self.theme_toggle_button.setMinimumHeight(50)
        layout.addWidget(self.theme_toggle_button,
                         alignment=Qt.AlignmentFlag.AlignRight)

        # Account Selection Section
        account_frame = QFrame()
        account_frame.setMinimumHeight(100)
        account_layout = QHBoxLayout()
        account_layout.setSpacing(30)
        account_label = QLabel("Select Account:")
        account_label.setMinimumWidth(200)
        account_label.setMinimumHeight(50)
        self.account_combo = QComboBox()
        self.account_combo.addItem("New Account")
        self.account_combo.currentIndexChanged.connect(
            self.on_account_selected)
        self.account_combo.setMinimumWidth(400)
        self.account_combo.setMinimumHeight(50)
        account_layout.addWidget(account_label)
        account_layout.addWidget(self.account_combo)
        account_frame.setLayout(account_layout)
        layout.addWidget(account_frame)

        # Phone Number Section
        phone_frame = QFrame()
        phone_frame.setMinimumHeight(100)
        phone_layout = QHBoxLayout()
        phone_layout.setSpacing(30)
        phone_label = QLabel("Phone Number:")
        phone_label.setMinimumWidth(200)
        phone_label.setMinimumHeight(50)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g., +989123456789")
        self.phone_input.setMinimumWidth(400)
        self.phone_input.setMinimumHeight(50)
        phone_layout.addWidget(phone_label)
        phone_layout.addWidget(self.phone_input)
        phone_frame.setLayout(phone_layout)
        layout.addWidget(phone_frame)

        # API Credentials Section
        api_frame = QFrame()
        api_frame.setMinimumHeight(150)
        api_layout = QGridLayout()
        api_layout.setSpacing(30)

        api_id_label = QLabel("API ID:")
        api_id_label.setMinimumWidth(200)
        api_id_label.setMinimumHeight(50)
        self.api_id_input = QLineEdit()
        self.api_id_input.setPlaceholderText("Enter your Telegram API ID")
        self.api_id_input.setMinimumWidth(400)
        self.api_id_input.setMinimumHeight(50)

        api_hash_label = QLabel("API Hash:")
        api_hash_label.setMinimumWidth(200)
        api_hash_label.setMinimumHeight(50)
        self.api_hash_input = QLineEdit()
        self.api_hash_input.setPlaceholderText("Enter your Telegram API Hash")
        self.api_hash_input.setMinimumWidth(400)
        self.api_hash_input.setMinimumHeight(50)

        api_layout.addWidget(api_id_label, 0, 0)
        api_layout.addWidget(self.api_id_input, 0, 1)
        api_layout.addWidget(api_hash_label, 1, 0)
        api_layout.addWidget(self.api_hash_input, 1, 1)
        api_frame.setLayout(api_layout)
        layout.addWidget(api_frame)

        # Timezone Section
        tz_frame = QFrame()
        tz_frame.setMinimumHeight(100)
        tz_layout = QHBoxLayout()
        tz_layout.setSpacing(30)
        tz_label = QLabel("Timezone:")
        tz_label.setMinimumWidth(200)
        tz_label.setMinimumHeight(50)
        self.tz_combo = QComboBox()
        self.tz_combo.addItems([
            "Iran (UTC+3:30)",
            "United States (UTC-5:00, Eastern Time)",
            "United Kingdom (UTC+0:00)",
            "Other (UTC)"
        ])
        self.tz_combo.setMinimumWidth(400)
        self.tz_combo.setMinimumHeight(50)
        tz_layout.addWidget(tz_label)
        tz_layout.addWidget(self.tz_combo)
        tz_frame.setLayout(tz_layout)
        layout.addWidget(tz_frame)

        # Connect Button
        self.connect_button = QPushButton("🔒 Connect to Telegram")
        self.connect_button.clicked.connect(self.connect_telegram)
        self.connect_button.setMinimumHeight(60)
        self.connect_button.setMinimumWidth(300)
        layout.addWidget(self.connect_button,
                         alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Label
        self.login_status = QLabel(
            "Enter your phone number, API credentials, and timezone to connect.")
        self.login_status.setStyleSheet(
            "font-size: 12pt; color: #B0BEC5; font-family: 'Segoe UI', 'Arial', sans-serif;")
        layout.addWidget(self.login_status,
                         alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        self.login_tab.setLayout(layout)

        # Load existing accounts
        self.load_accounts()

    def setup_chats_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        self.chats_list = QListWidget()
        layout.addWidget(self.chats_list)

        self.chats_tab.setLayout(layout)

    def setup_messages_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Chat Selection Section
        chats_frame = QFrame()
        chats_layout = QHBoxLayout()
        chats_layout.setSpacing(20)
        chats_label = QLabel("Select Chat:")
        self.messages_chat_combo = QComboBox()
        self.messages_chat_combo.setMinimumWidth(350)
        self.messages_chat_combo.setMinimumHeight(40)
        chats_layout.addWidget(chats_label)
        chats_layout.addWidget(self.messages_chat_combo)
        chats_frame.setLayout(chats_layout)
        layout.addWidget(chats_frame)

        # Buttons Section
        button_layout = QHBoxLayout()
        fetch_button = QPushButton("📥 Fetch Messages for Selected Chat")
        fetch_button.clicked.connect(self.fetch_chat_messages)
        button_layout.addWidget(fetch_button)

        self.cancel_button = QPushButton("❌ Cancel Fetching")
        self.cancel_button.clicked.connect(self.cancel_fetching)
        self.cancel_button.setVisible(False)
        self.cancel_button.setProperty("delete", True)
        button_layout.addWidget(
            self.cancel_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.copy_summary_button = QPushButton("📋 Copy Summary")
        self.copy_summary_button.clicked.connect(self.copy_summary)
        self.copy_summary_button.setVisible(False)
        button_layout.addWidget(self.copy_summary_button)

        layout.addLayout(button_layout)

        self.messages_display = QTextEdit()
        self.messages_display.setReadOnly(True)
        self.messages_display.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.messages_display)

        self.messages_progress = QProgressBar()
        self.messages_progress.setVisible(False)
        self.messages_progress.setRange(0, 100)
        self.messages_progress.setValue(0)
        layout.addWidget(self.messages_progress)

        self.messages_status_label = QLabel("Ready to fetch messages.")
        self.messages_status_label.setStyleSheet(
            "font-size: 11pt; color: #B0BEC5; font-family: 'Segoe UI';")
        layout.addWidget(self.messages_status_label)

        self.messages_tab.setLayout(layout)

    def setup_search_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Input Section
        search_input_frame = QFrame()
        search_input_layout = QHBoxLayout()
        search_input_layout.setSpacing(20)
        search_label = QLabel("Search Chat (ID or Name):")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., Chat ID or Name")
        self.search_input.setMinimumWidth(350)
        self.search_input.setMinimumHeight(40)
        search_button = QPushButton("🔍 Search")
        search_button.clicked.connect(self.search_chat)
        search_input_layout.addWidget(search_label)
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(search_button)
        search_input_frame.setLayout(search_input_layout)
        layout.addWidget(search_input_frame)

        # Output Section
        search_output_frame = QFrame()
        search_output_layout = QVBoxLayout()

        search_output_label = QLabel("Search Results:")
        search_output_layout.addWidget(search_output_label)

        self.search_results_table = QTableWidget()
        self.search_results_table.setColumnCount(3)
        self.search_results_table.setHorizontalHeaderLabels(
            ["Chat ID", "Name", "Username"])
        self.search_results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.search_results_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self.search_results_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.search_results_table.setColumnWidth(0, 100)
        self.search_results_table.setColumnWidth(1, 200)
        search_output_layout.addWidget(self.search_results_table)

        fetch_messages_button = QPushButton("📥 Fetch Messages")
        fetch_messages_button.clicked.connect(self.fetch_from_search_result)
        search_output_layout.addWidget(fetch_messages_button)

        search_output_frame.setLayout(search_output_layout)
        layout.addWidget(search_output_frame)

        self.search_tab.setLayout(layout)

    # Updated setup_search_history_tab to increase history_messages_display size

    def setup_search_history_tab(self):
        self.history_layout = QVBoxLayout()
        self.history_layout.setContentsMargins(40, 40, 40, 40)
        self.history_layout.setSpacing(30)

        # User Selection Section
        user_frame = QFrame()
        user_layout = QHBoxLayout()
        user_layout.setSpacing(20)
        user_label = QLabel("Select User:")
        self.user_combo = QComboBox()
        self.user_combo.addItem("Select a user...")
        self.user_combo.currentIndexChanged.connect(
            self.load_user_search_history)
        self.user_combo.setMinimumWidth(350)
        self.user_combo.setMinimumHeight(40)
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_combo)
        user_frame.setLayout(user_layout)
        self.history_layout.addWidget(user_frame)

        self.history_list = QListWidget()
        self.history_layout.addWidget(self.history_list)

        button_layout = QHBoxLayout()
        view_button = QPushButton("📜 View Messages")
        view_button.clicked.connect(self.view_history_messages)
        button_layout.addWidget(view_button)
        self.history_layout.addLayout(button_layout)

        self.messages_frame = QFrame()
        self.messages_frame.setVisible(False)
        messages_layout = QVBoxLayout()

        self.history_messages_display = QTextEdit()
        self.history_messages_display.setReadOnly(True)
        self.history_messages_display.setFont(QFont("Segoe UI", 14))
        self.history_messages_display.setMinimumHeight(400)  # Increased size
        self.history_messages_display.setMinimumWidth(600)
        messages_layout.addWidget(self.history_messages_display)

        manage_buttons_layout = QHBoxLayout()
        delete_recent_button = QPushButton("🗑️ Delete Recent Messages")
        delete_recent_button.clicked.connect(self.delete_recent_messages)
        delete_recent_button.setProperty("delete", True)
        manage_buttons_layout.addWidget(delete_recent_button)

        delete_date_button = QPushButton("🗓️ Delete Messages from Date")
        delete_date_button.clicked.connect(self.delete_messages_from_date)
        delete_date_button.setProperty("delete", True)
        manage_buttons_layout.addWidget(delete_date_button)

        delete_all_button = QPushButton("🗑️ Delete All Messages")
        delete_all_button.clicked.connect(self.delete_all_messages)
        delete_all_button.setProperty("delete", True)
        manage_buttons_layout.addWidget(delete_all_button)

        back_button = QPushButton("⬅️ Back to List")
        back_button.clicked.connect(self.back_to_history_list)
        manage_buttons_layout.addWidget(back_button)

        messages_layout.addLayout(manage_buttons_layout)
        self.messages_frame.setLayout(messages_layout)
        self.history_layout.addWidget(self.messages_frame)

        self.history_status_label = QLabel(
            "Select a user to view their search history.")
        self.history_status_label.setStyleSheet(
            "font-size: 11pt; color: #B0BEC5; font-family: 'Segoe UI';")
        self.history_layout.addWidget(self.history_status_label)

        self.search_history_tab.setLayout(self.history_layout)

        # Load users with search history
        self.load_users_with_search_history()

    def setup_refresh_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        refresh_button = QPushButton("🔄 Refresh Chat List")
        refresh_button.clicked.connect(self.refresh_chats)
        layout.addWidget(refresh_button)

        self.refresh_status = QLabel("Click to refresh the chat list.")
        self.refresh_status.setStyleSheet(
            "font-size: 11pt; color: #B0BEC5; font-family: 'Segoe UI';")
        layout.addWidget(self.refresh_status)

        layout.addStretch()
        self.refresh_tab.setLayout(layout)

    def setup_logs_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)

        refresh_logs_button = QPushButton("🔄 Refresh Logs")
        refresh_logs_button.clicked.connect(self.update_logs)
        layout.addWidget(refresh_logs_button)

        self.logs_tab.setLayout(layout)

        setup_logging(self.logs_text)

    def load_accounts(self):
        users = load_all_users()
        self.account_combo.clear()
        self.account_combo.addItem("New Account")
        for user_phone in users:
            self.account_combo.addItem(user_phone)

    def on_account_selected(self):
        selected_account = self.account_combo.currentText()
        if selected_account == "New Account":
            self.phone_input.clear()
            self.api_id_input.clear()
            self.api_hash_input.clear()
            self.api_id_input.setEnabled(True)
            self.api_hash_input.setEnabled(True)
        else:
            self.phone_input.setText(selected_account)
            credentials = load_user_settings(selected_account)
            if credentials:
                api_id, api_hash = credentials
                self.api_id_input.setText(str(api_id))
                self.api_hash_input.setText(api_hash)
                self.api_id_input.setEnabled(False)
                self.api_hash_input.setEnabled(False)
            else:
                self.api_id_input.clear()
                self.api_hash_input.clear()
                self.api_id_input.setEnabled(True)
                self.api_hash_input.setEnabled(True)

    def load_users_with_search_history(self):
        users = load_users_with_search_history()
        self.user_combo.clear()
        self.user_combo.addItem("Select a user...")
        for user_phone in users:
            self.user_combo.addItem(user_phone)

    def load_user_search_history(self):
        selected_user = self.user_combo.currentText()
        if selected_user == "Select a user...":
            self.history_list.clear()
            self.history_status_label.setText(
                "Select a user to view their search history.")
            return

        self.history_list.clear()
        chats = load_chats_with_messages(selected_user)
        if not chats:
            self.history_list.addItem(
                "No chats with saved messages found for this user.")
            self.history_status_label.setText(
                "No chats with saved messages found for this user.")
            return

        for chat_id, chat_name, username in chats:
            display_text = f"{chat_name} (ID: {chat_id})"
            if username:
                display_text += f" (@{username})"
            self.history_list.addItem(display_text)
        self.history_status_label.setText(
            f"Showing chats with messages for {selected_user}")

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

        api_id_text = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        if not api_id_text or not api_hash:
            QMessageBox.warning(self, "Input Error",
                                "API ID and API Hash cannot be empty.")
            return

        try:
            api_id = int(api_id_text)
        except ValueError:
            QMessageBox.warning(self, "Input Error",
                                "API ID must be a valid integer.")
            return

        if self.account_combo.currentText() == "New Account":
            try:
                save_user_settings(self.user_phone, api_id, api_hash)
                logger.info(f"Saved API credentials for {self.user_phone}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save API credentials: {e}")
                return
            self.load_accounts()
            self.account_combo.setCurrentText(self.user_phone)

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
                credentials = load_user_settings(self.user_phone)
                if not credentials:
                    raise ValueError(
                        f"No API credentials found for {self.user_phone}")
                api_id, api_hash = credentials
                self.telegram = TelegramManager(
                    self.user_phone, api_id, api_hash, self)
                await self.telegram.connect()
                user = await self.telegram.login(self.user_phone)
                logger.info(f"Logged in as: {user.first_name} ({user.phone})")
                save_user_settings(self.user_phone, api_id, api_hash)
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
            self.load_users_with_search_history()
            self.load_accounts()
            self.account_combo.setCurrentText(self.user_phone)
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

            await self.update_progress(90)
            self.messages_status_label.setText(
                "Messages fetched, analyzing with AI...")

            result = ""
            if messages:
                logger.info(
                    f"Processing {len(messages)} messages for display...")
                for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                    local_time = timestamp.astimezone(self.user_timezone)
                    result += f"{i}. {sender}: {msg}\n   (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})\n\n"
                logger.info("Summarizing messages...")
                summary = await summarize_text(messages)
                result += "=== Summary ===\n" + summary + "\n"

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
        self.load_users_with_search_history()

        fetch_dialog = FetchMessagesDialog(
            self.telegram, chat_id, chat_name, self.user_timezone, self.user_phone, self)
        if fetch_dialog.exec():
            filter_type, filter_value = fetch_dialog.result
            self.is_fetching = True
            self.messages_progress.setVisible(True)
            self.messages_progress.setValue(0)
            self.cancel_button.setVisible(True)
            self.copy_summary_button.setVisible(False)
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
            self.copy_summary_button.setVisible(False)
            self.messages_progress.setVisible(False)
            self.messages_display.setText("Fetching cancelled by user.")
            self.messages_status_label.setText("Fetching cancelled.")

    def copy_summary(self):
        text = self.messages_display.toPlainText()
        summary_start = text.find("=== Summary ===")
        if summary_start != -1:
            summary_text = text[summary_start + len("=== Summary ===\n"):]
            clipboard = QApplication.clipboard()
            clipboard.setText(summary_text)
            QMessageBox.information(
                self, "Success", "Summary copied to clipboard!")

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
                    self.copy_summary_button.setVisible(False)
                else:
                    self.messages_status_label.setText(
                        "Messages fetched successfully.")
                    self.copy_summary_button.setVisible(True)
            else:
                self.messages_display.setText("No messages found.")
                self.messages_status_label.setText("No messages found.")
                self.copy_summary_button.setVisible(False)
        except Exception as e:
            self.messages_status_label.setText("Error fetching messages.")
            self.copy_summary_button.setVisible(False)
            logger.error(f"Error displaying messages in tab: {e}")
            QMessageBox.critical(
                self, "Error", f"Error fetching messages: {e}")

    def search_chat(self):
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Input Error",
                                "Search term cannot be empty.")
            return

        self.search_results_table.setRowCount(0)

        async def search_coro():
            try:
                matching_chats = await self.telegram.search_chat_by_id_or_name(search_term)
                return matching_chats
            except Exception as e:
                logger.error(f"Error searching chats: {e}")
                return []

        task = asyncio.ensure_future(search_coro())
        task.add_done_callback(self.display_search_results)

    def display_search_results(self, task):
        try:
            matching_chats = task.result()
            self.search_results_table.setRowCount(len(matching_chats))
            for row, (chat_id, name, username) in enumerate(matching_chats):
                self.search_results_table.setItem(
                    row, 0, QTableWidgetItem(str(chat_id)))
                self.search_results_table.setItem(
                    row, 1, QTableWidgetItem(name))
                self.search_results_table.setItem(
                    row, 2, QTableWidgetItem(username if username else ""))
            if not matching_chats:
                self.search_results_table.setRowCount(1)
                self.search_results_table.setItem(
                    0, 0, QTableWidgetItem("No chats found."))
        except Exception as e:
            logger.error(f"Error displaying search results: {e}")
            self.search_results_table.setRowCount(1)
            self.search_results_table.setItem(
                0, 0, QTableWidgetItem("Error searching chats."))

    def fetch_from_search_result(self):
        selected_row = self.search_results_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error",
                                "Please select a chat from the search results.")
            return

        chat_id_item = self.search_results_table.item(selected_row, 0)
        if not chat_id_item or "No chats found" in chat_id_item.text() or "Error" in chat_id_item.text():
            QMessageBox.warning(self, "Selection Error",
                                "Invalid chat selected.")
            return

        chat_id = int(chat_id_item.text())
        chat_name = self.search_results_table.item(selected_row, 1).text()
        username = self.search_results_table.item(selected_row, 2).text()

        found = False
        for i, chat in enumerate(self.chats):
            if chat[0] == chat_id:
                found = True
                break
        if not found:
            self.chats.append((chat_id, chat_name, username))

        self.messages_chat_combo.clear()
        for chat_id_, chat_name_, username_ in self.chats:
            item_text = f"{chat_name_} (ID: {chat_id_})"
            if username_:
                item_text += f" (@{username_})"
            self.messages_chat_combo.addItem(item_text)

        self.messages_chat_combo.setCurrentText(
            f"{chat_name} (ID: {chat_id})" + (f" (@{username})" if username else ""))

        search_term = username if username else chat_name
        save_search_history(search_term, self.user_phone)
        self.load_users_with_search_history()

        self.tabs.setCurrentWidget(self.messages_tab)
        self.fetch_chat_messages()

    def view_history_messages(self):
        selected_item = self.history_list.currentItem()
        if not selected_item or "No chats" in selected_item.text():
            QMessageBox.warning(self, "Selection Error",
                                "Please select a chat with saved messages.")
            return

        item_text = selected_item.text()
        parts = item_text.split("(ID: ")
        chat_name = parts[0].strip()
        chat_id_part = parts[1].split(")")[0]
        chat_id = int(chat_id_part)

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
            self, "Confirm Deletion", f"Are you sure you want to delete the last {count} messages for {self.current_chat_name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
            self.load_users_with_search_history()

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
            self, "Confirm Deletion", f"Are you sure you want to delete messages from {date} for {self.current_chat_name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
            self.load_users_with_search_history()

    def delete_all_messages(self):
        if not self.current_chat_id:
            QMessageBox.warning(self, "Selection Error", "No chat selected.")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion", f"Are you sure you want to delete all messages for {self.current_chat_name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
            self.load_users_with_search_history()

    def back_to_history_list(self):
        self.messages_frame.setVisible(False)
        self.history_list.setVisible(True)
        self.history_status_label.setText(
            "Select a user to view their search history.")
        self.load_user_search_history()

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
    app.setStyle(QStyleFactory.create('Fusion'))
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    try:
        window = MainWindow(loop)
        window.show()
        with loop:
            loop.run_forever()
    except Exception as e:
        logger.error(f"Error in run_gui: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    run_gui()
