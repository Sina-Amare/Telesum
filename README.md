# TeleSam

**TeleSam** is an open-source desktop application for managing and analyzing Telegram chats. Built with Python and PyQt6, it integrates with the Telegram API to fetch chats and messages, stores data locally in SQLite, and uses AI for message summarization via OpenRouter API. The tool offers a clean, customizable GUI with dark/light themes, making it ideal for organizing and exploring Telegram conversations.

## Features

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

## Tech Stack

- **Frontend**: PyQt6 for the graphical interface.
- **Backend**: Python, `asyncio`, `qasync` for Telegram API integration.
- **Database**: SQLite with SQLAlchemy for local storage.
- **AI**: OpenRouter API for message summarization.
- **Dependencies**: `python-telegram`, `pytz`, `sqlalchemy`, etc.

## Installation

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