
# TeleSum - Telegram Chat Manager

**TeleSum** is an open-source desktop application for managing and analyzing Telegram chats. Built with Python and PyQt6, it integrates with the Telegram API to fetch chats and messages, stores data locally in PostgreSQl, and uses AI for message summarization via OpenRouter API. The tool offers a clean, customizable GUI with dark/light themes, making it ideal for organizing and exploring Telegram conversations.

## Features

- **Secure Login**: Authenticate using Telegram API credentials.
- **Chat Management**: Fetch and display private chats in a tabular view.
- **Message Filtering**: Retrieve messages by:
  - Recent messages (e.g., last 10 messages)
  - Recent days (e.g., last 7 days)
  - Specific date (e.g., 10 April 2025)
- **AI Summarization**: Generate conversation summaries using OpenRouter API.
- **Search Functionality**: Search chats by ID, name, or username with cached history.
- **Local Database Storage**: Store chats and messages in a PostgreSQL database.
- **Message History Management**: View and delete saved messages.
- **Customizable GUI**: Toggle between dark and light themes with PyQt6 interface.
- **Real-Time Logging**: Monitor system activity with a dedicated Logs tab.

## Tech Stack

- **Frontend**: PyQt6 for the graphical interface.
- **Backend**: Python, `asyncio`, `qasync` for Telegram API integration.
- **Database**: PostgreSQL with SQLAlchemy for local storage.
- **AI**: OpenRouter API for message summarization.
- **Dependencies**: `python-telegram`, `pytz`, `sqlalchemy`, etc.

## Installation

### Prerequisites

- Python 3.8 or higher
- Telegram API credentials (API ID and Hash) from [my.telegram.org](https://my.telegram.org)

### Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Sina-Amare/telesam.git
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
   - Edit `config.py` to set `DATABASE_URL` and other settings:
     ```python
     ```
     Edit PostgreSQL configuration
     ```
     VERBOSE_LOGGING = True
     ```

5. **Run the Application**:
   ```bash
   python gui.py
   ```

## Usage

- **Log In**:
  - Open the app and go to the **Login** tab.
  - Enter your phone number (e.g., `+989123456789`), API ID, API Hash, and timezone.
  - Click **Connect to Telegram**.

- **Manage Chats**:
  - View chats in the **Chats** tab.
  - Select a chat to fetch messages in the **Messages** tab.

- **Fetch Messages**:
  - Choose a filter:
    - Recent messages (e.g., last 10 messages)
    - Recent days (e.g., last 7 days)
    - Specific date (e.g., 10 April 2025)
  - View messages and AI-generated summaries.

- **Search & History**:
  - Search chats in the **Search** tab.
  - Manage saved messages in the **Search History** tab.

- **Logs**:
  - Check the **Logs** tab for system activity.

## Contributing

Contributions are welcome! To contribute:

- Fork the repository.
- Create a branch:
  ```bash
  git checkout -b my-feature
  ```
- Commit changes:
  ```bash
  git commit -m "Add my feature"
  ```
- Push:
  ```bash
  git push origin my-feature
  ```
- Open a Pull Request.

Please follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.

## License

This project is licensed under the MIT License. See the [LICENSE] file.

## Contact

For questions or feedback, open an issue on [GitHub](https://github.com/Sina-Amare/telesum/issues).
