import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QLineEdit, QComboBox


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Personal Dashboard")
        self.setGeometry(200, 100, 900, 600)
        # پس‌زمینه روشن برای رنگ‌های جذاب‌تر
        self.setStyleSheet("background-color: #ecf0f1;")

        # Creating the stacked widget to switch between different sections
        self.stacked_widget = QStackedWidget()

        # Create the different sections
        self.create_chat_section()
        self.create_ai_tools_section()

        # Add sections to stacked widget
        self.stacked_widget.addWidget(self.chat_section)
        self.stacked_widget.addWidget(self.ai_tools_section)

        # Main layout
        layout = QVBoxLayout()
        self.navigation_layout = self.create_navigation_buttons()
        layout.addLayout(self.navigation_layout)
        layout.addWidget(self.stacked_widget)

        self.setLayout(layout)

    def create_navigation_buttons(self):
        # Navigation buttons for switching between sections
        nav_layout = QHBoxLayout()

        self.chat_button = QPushButton("Chats")
        self.chat_button.clicked.connect(self.show_chat_section)
        self.chat_button.setStyleSheet("""
            background-color: #3498db; 
            color: white; 
            padding: 15px; 
            border-radius: 5px; 
            font-size: 18px;
        """)

        self.ai_tools_button = QPushButton("AI Tools")
        self.ai_tools_button.clicked.connect(self.show_ai_tools_section)
        self.ai_tools_button.setStyleSheet("""
            background-color: #e74c3c; 
            color: white; 
            padding: 15px; 
            border-radius: 5px; 
            font-size: 18px;
        """)

        nav_layout.addWidget(self.chat_button)
        nav_layout.addWidget(self.ai_tools_button)

        return nav_layout

    def create_chat_section(self):
        self.chat_section = QWidget()

        # Chat section header
        chat_header = QLabel("Chats & Messages")
        chat_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chat_header.setStyleSheet(
            "font-size: 24px; color: #34495e; font-weight: bold; padding: 10px;")

        # Creating a list of chats (Groups, Channels, Bots)
        self.chat_list = QListWidget()
        self.chat_list.addItem("Group Chat 1")
        self.chat_list.addItem("Channel 1")
        self.chat_list.addItem("Bot 1")
        self.chat_list.setStyleSheet("""
            background-color: #fff; 
            color: #34495e; 
            padding: 10px;
            border-radius: 5px;
            font-size: 16px;
        """)

        # Chat display area (can be expanded)
        self.chat_display = QLabel("Chat Messages will be shown here.")
        self.chat_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chat_display.setStyleSheet("""
            background-color: #f4f6f9; 
            color: #34495e; 
            padding: 20px;
            border-radius: 5px;
            font-size: 18px;
        """)

        # Layout for chat section
        chat_layout = QVBoxLayout()
        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self.chat_list)
        chat_layout.addWidget(self.chat_display)

        self.chat_section.setLayout(chat_layout)

    def create_ai_tools_section(self):
        self.ai_tools_section = QWidget()

        # AI tools section header
        ai_header = QLabel("AI Tools: Summarize & Analyze")
        ai_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_header.setStyleSheet(
            "font-size: 24px; color: #34495e; font-weight: bold; padding: 10px;")

        # Text input for selecting chat or entering text to analyze
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(
            "Enter chat text to analyze or summarize...")
        self.text_input.setStyleSheet("""
            padding: 10px; 
            font-size: 16px; 
            border-radius: 5px; 
            border: 1px solid #3498db;
            background-color: #ecf0f1;
        """)

        # ComboBox for selecting AI tool
        self.ai_tool_selector = QComboBox()
        self.ai_tool_selector.addItem("Summarize Chat")
        self.ai_tool_selector.addItem("Sentiment Analysis")
        self.ai_tool_selector.addItem("Extract Key Information")
        self.ai_tool_selector.setStyleSheet("""
            font-size: 16px;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
            border: 1px solid #3498db;
        """)

        # Button to process the selected AI tool
        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self.process_ai_tool)
        self.process_button.setStyleSheet("""
            background-color: #2ecc71; 
            color: white; 
            padding: 12px; 
            border-radius: 5px;
            font-size: 18px;
        """)

        # Layout for AI tools section
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(ai_header)
        ai_layout.addWidget(self.text_input)
        ai_layout.addWidget(self.ai_tool_selector)
        ai_layout.addWidget(self.process_button)

        self.ai_tools_section.setLayout(ai_layout)

    def show_chat_section(self):
        self.stacked_widget.setCurrentWidget(self.chat_section)

    def show_ai_tools_section(self):
        self.stacked_widget.setCurrentWidget(self.ai_tools_section)

    def process_ai_tool(self):
        # Simple placeholder function for AI tool processing
        selected_tool = self.ai_tool_selector.currentText()
        input_text = self.text_input.text()

        if selected_tool == "Summarize Chat":
            self.ai_tools_section.findChild(QLabel).setText(
                f"Summarized Text: {input_text[:50]}...")  # Simulate summarization
        elif selected_tool == "Sentiment Analysis":
            self.ai_tools_section.findChild(QLabel).setText(
                "Sentiment: Positive")  # Simulate sentiment analysis
        elif selected_tool == "Extract Key Information":
            self.ai_tools_section.findChild(QLabel).setText(
                "Extracted Info: Key data found.")  # Simulate info extraction


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardPage()
    window.show()
    sys.exit(app.exec())
