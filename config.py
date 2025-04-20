import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API key (if used for text processing or summarization)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenRouter API key (if used for additional AI services)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Maximum number of messages to store per chat in the database
MAX_MESSAGES_PER_CHAT = int(os.getenv("MAX_MESSAGES_PER_CHAT", 5000))

# PostgreSQL connection string
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = f"postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/telesum"

# Set to True for detailed terminal output, False for concise output
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "True").lower() == "true"

# Encryption key for Fernet (ensure it's a bytes object)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if ENCRYPTION_KEY is None:
    raise ValueError("ENCRYPTION_KEY not found in .env file")
# Convert the key from string to bytes
ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
