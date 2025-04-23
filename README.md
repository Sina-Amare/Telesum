<<<<<<< HEAD
# TeleSam

**TeleSam** is an open-source desktop application for managing and analyzing Telegram chats. Built with Python and PyQt6, it integrates with the Telegram API to fetch chats and messages, stores data locally in SQLite, and uses AI for message summarization via OpenRouter API. The tool offers a clean, customizable GUI with dark/light themes, making it ideal for organizing and exploring Telegram conversations.
=======
TeleSam - Telegram Chat Manager

TeleSam is a lightweight desktop application for managing Telegram chats. Built with Python and PyQt6, it allows you to fetch, store, search, and analyze Telegram conversations with a clean, user-friendly interface. The app supports AI-powered message summarization, local data storage, and customizable themes.
Features
>>>>>>> 5513185ddc347f539651655cf7ef42c4e036d43c

Telegram Integration: Securely log in with Telegram API credentials.
Chat Management: View and refresh chats in a tabular format.
Message Retrieval: Fetch messages by recent count, date range, or specific date.
AI Summarization: Generate summaries of chats using OpenRouter API.
Search: Find chats by ID, name, or username with cached history.
Message History: Store and delete messages in a local SQLite database.
Customizable UI: Switch between dark and light themes.
Logging: View real-time system logs for debugging.

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

Frontend: PyQt6
Backend: Python, asyncio, qasync
Database: SQLAlchemy, SQLite
AI: OpenRouter API
Dependencies: python-telegram, pytz, etc.

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

Python 3.8+
Telegram API credentials (API ID and Hash) from my.telegram.org.

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
