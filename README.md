<<<<<<< HEAD
# TeleSum

**TeleSum** is an open-source tool designed to summarize and analyze Telegram chats using AI. It leverages the Telegram API to fetch private chats and the Gemini API for natural language processing tasks such as conversation summarization, sentiment analysis, music extraction, and message suggestion. This tool is built with Python and aims to provide an intuitive and user-friendly experience for analyzing Telegram conversations.
=======
<<<<<<< HEAD
# TeleSam

**TeleSam** is an open-source desktop application for managing and analyzing Telegram chats. Built with Python and PyQt6, it integrates with the Telegram API to fetch chats and messages, stores data locally in SQLite, and uses AI for message summarization via OpenRouter API. The tool offers a clean, customizable GUI with dark/light themes, making it ideal for organizing and exploring Telegram conversations.
=======
TeleSam - Telegram Chat Manager

TeleSam is a lightweight desktop application for managing Telegram chats. Built with Python and PyQt6, it allows you to fetch, store, search, and analyze Telegram conversations with a clean, user-friendly interface. The app supports AI-powered message summarization, local data storage, and customizable themes.
Features
>>>>>>> 5513185ddc347f539651655cf7ef42c4e036d43c
>>>>>>> c762e55cafc70bf3c0704d01659d5ef8047ae2d9

## Features

<<<<<<< HEAD
- **Fetch Private Chats**: Retrieve a list of private chats from your Telegram account.
- **Message Filtering**: Filter messages by:
  - Recent messages (e.g., last 10 messages)
  - Recent days (e.g., last 7 days)
  - Specific date (e.g., 10 December 2024)
- **Local Database Storage**: Store chats and messages in a local SQLite database for faster access.
- **Search History Management**: Keep track of searched usernames and manage search history.
- **CLI Interface**: Currently features a command-line interface (CLI) for interacting with the tool.
- **Planned Features** (coming soon):
  - AI-powered conversation summarization using Gemini API.
  - Sentiment analysis to detect the tone of conversations (positive, negative, neutral).
  - Extraction of music names and links from chats.
  - Suggestion of the next message to continue the conversation.
  - A graphical user interface (GUI) using PyQt6.
=======
<<<<<<< HEAD
- **Secure Login**: Authenticate using Telegram API credentials.
- **Chat Management**: Fetch and display private chats in a tabular view.
- **Message Filtering**: Retrieve messages by:
  - Recent messages (e.g., last 10 messages)
  - Recent days (e.g., last 7 days)
  - Specific date (e.g., 10 April 2025)
- **AI Summarization**: Generate conversation summaries using OpenRouter API.
- **Search Functionality**: Search chats by ID, name, or username with cached history.
- **Local Database Storage**: Store chats and messages in a SQLite database.
- **Message History Management**: View and delete saved messages.
- **Customizable GUI**: Toggle between dark and light themes with PyQt6 interface.
- **Real-Time Logging**: Monitor system activity with a dedicated Logs tab.
=======
Tech Stack
>>>>>>> 5513185ddc347f539651655cf7ef42c4e036d43c
>>>>>>> c762e55cafc70bf3c0704d01659d5ef8047ae2d9

## Tech Stack

<<<<<<< HEAD
- **Backend**: Python, [Telethon](https://github.com/LonamiWebs/Telethon) for Telegram API integration.
- **Database**: SQLite for local storage.
- **NLP (Planned)**: Gemini API for summarization, sentiment analysis, and more.
- **GUI (Planned)**: PyQt6 for a user-friendly graphical interface.
- **Build Tool (Planned)**: PyInstaller to create standalone `.exe` files.
=======
<<<<<<< HEAD
- **Frontend**: PyQt6 for the graphical interface.
- **Backend**: Python, `asyncio`, `qasync` for Telegram API integration.
- **Database**: SQLite with SQLAlchemy for local storage.
- **AI**: OpenRouter API for message summarization.
- **Dependencies**: `python-telegram`, `pytz`, `sqlalchemy`, etc.
=======
Installation
Prerequisites
>>>>>>> 5513185ddc347f539651655cf7ef42c4e036d43c
>>>>>>> c762e55cafc70bf3c0704d01659d5ef8047ae2d9

## Installation

<<<<<<< HEAD
### Prerequisites
- Python 3.8 or higher
- A Telegram account with API credentials (API ID and API Hash)
- (Optional) Gemini API Key for NLP features (coming soon)
=======
<<<<<<< HEAD
### Prerequisites

- Python 3.8 or higher
- Telegram API credentials (API ID and Hash) from my.telegram.org

### Steps

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/telesam.git
   cd telesam
   ```

2. **Set Up Virtual Environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure**:

   - Copy `config.example.py` to `config.py`:

     ```bash
     cp config.example.py config.py
     ```

   - Edit `config.py`:

     ```python
     DATABASE_URL = "sqlite:///telesam.db"
     VERBOSE_LOGGING = True
     ```

5. **Run the Application**:

   ```bash
   python gui.py
   ```

## Usage

- **Log In**: Enter phone number, API ID, API Hash, and timezone in the **Login** tab.
- **View Chats**: Browse chats in the **Chats** tab and select one to fetch messages.
- **Fetch Messages**: Filter messages in the **Messages** tab (recent, by date, etc.) and view AI summaries.
- **Search Chats**: Use the **Search** tab to find chats and manage history in **Search History**.
- **Monitor Logs**: Check system activity in the **Logs** tab.

## Contributing

Contributions are welcome! To contribute:

- Fork the repository.
- Create a branch: `git checkout -b my-feature`.
- Commit changes: `git commit -m "Add my feature"`.
- Push: `git push origin my-feature`.
- Open a Pull Request.

Please follow PEP 8 for Python code.

## License

This project is licensed under the MIT License. See the LICENSE file.

## Contact

For feedback or issues, open an issue on GitHub.
=======
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
>>>>>>> 5513185ddc347f539651655cf7ef42c4e036d43c
>>>>>>> c762e55cafc70bf3c0704d01659d5ef8047ae2d9
