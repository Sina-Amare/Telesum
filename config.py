# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
# Convert to int for Telethon compatibility
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Gemini API key (if used for text processing or summarization)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenRouter API key (if used for additional AI services)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Maximum number of messages to store per chat in the database
MAX_MESSAGES_PER_CHAT = 5000
