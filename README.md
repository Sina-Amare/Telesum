TeleSam - Telegram Chat Manager

TeleSam is a lightweight desktop application for managing Telegram chats. Built with Python and PyQt6, it allows you to fetch, store, search, and analyze Telegram conversations with a clean, user-friendly interface. The app supports AI-powered message summarization, local data storage, and customizable themes.
Features

Telegram Integration: Securely log in with Telegram API credentials.
Chat Management: View and refresh chats in a tabular format.
Message Retrieval: Fetch messages by recent count, date range, or specific date.
AI Summarization: Generate summaries of chats using OpenRouter API.
Search: Find chats by ID, name, or username with cached history.
Message History: Store and delete messages in a local SQLite database.
Customizable UI: Switch between dark and light themes.
Logging: View real-time system logs for debugging.

Tech Stack

Frontend: PyQt6
Backend: Python, asyncio, qasync
Database: SQLAlchemy, SQLite
AI: OpenRouter API
Dependencies: python-telegram, pytz, etc.

Installation
Prerequisites

Python 3.8+
Telegram API credentials (API ID and Hash) from my.telegram.org.

Steps

Clone the Repository:
git clone https://github.com/yourusername/telesam.git
cd telesam


Set Up Virtual Environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt


Configure:

Copy config.example.py to config.py:cp config.example.py config.py


Edit config.py to set DATABASE_URL and other settings:DATABASE_URL = "sqlite:///telesam.db"
VERBOSE_LOGGING = True




Run:
python gui.py



Usage

Log In:

Open the app and go to the Login tab.
Enter your phone number (e.g., +989123456789), API ID, API Hash, and timezone.
Click Connect to Telegram.


Manage Chats:

View chats in the Chats tab.
Select a chat to fetch messages in the Messages tab.


Fetch Messages:

Choose a filter (e.g., last 10 messages or a specific date).
View messages and AI-generated summaries.


Search & History:

Search chats in the Search tab.
Manage saved messages in the Search History tab.


Logs:

Check the Logs tab for system activity.



Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a branch: git checkout -b my-feature.
Commit changes: git commit -m "Add my feature".
Push: git push origin my-feature.
Open a Pull Request.

Please follow PEP 8 for Python code.
License
This project is licensed under the MIT License. See the LICENSE file.
Contact
For questions or feedback, open an issue on GitHub.
