import sqlite3
from datetime import datetime, timedelta
import pytz
import os
from config import MAX_MESSAGES_PER_CHAT


DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "database.db")


def setup_database():
    """Set up the SQLite database and create necessary tables."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    timestamp TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    sender TEXT,
                    text TEXT,
                    timestamp TEXT,
                    UNIQUE(chat_id, message_id)
                )''')

    c.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in c.fetchall()]
    if 'message_id' not in columns:
        c.execute("ALTER TABLE messages ADD COLUMN message_id INTEGER")
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS unique_message ON messages (chat_id, message_id)")

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")


def save_chats(chats):
    """Save a list of chats to the SQLite database.

    Args:
        chats (list): List of tuples (chat_id, name, username) to save.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM chats")
    for chat_id, name, username in chats:
        c.execute("INSERT OR REPLACE INTO chats (id, name, username) VALUES (?, ?, ?)",
                  (chat_id, name, username))
    conn.commit()
    conn.close()


def load_chats():
    """Load all chats from the SQLite database.

    Returns:
        list: List of tuples (id, name, username).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, username FROM chats")
    chats = c.fetchall()
    conn.close()
    return chats


def save_search_history(username):
    """Save a username to the search history.

    Args:
        username (str): Username to save.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO search_history (username, timestamp) VALUES (?, ?)",
              (username, timestamp))
    conn.commit()
    conn.close()


def load_search_history():
    """Load the search history from the database.

    Returns:
        list: List of tuples (id, username, timestamp).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, timestamp FROM search_history ORDER BY timestamp DESC")
    history = c.fetchall()
    conn.close()
    print(f"Total search history entries: {len(history)}")
    return history


def delete_search_history_entry(entry_id):
    """Delete a specific search history entry.

    Args:
        entry_id (int): ID of the entry to delete.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def delete_all_search_history():
    """Delete all search history entries."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history")
    conn.commit()
    conn.close()


def save_messages(chat_id, messages):
    """Save messages to the database for a specific chat.

    Args:
        chat_id (int): ID of the chat.
        messages (list): List of tuples (sender, text, timestamp, message_id).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for sender, text, timestamp, message_id in messages:
        c.execute("INSERT OR IGNORE INTO messages (message_id, chat_id, sender, text, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (message_id, chat_id, sender, text, timestamp.isoformat()))

    c.execute("""
        DELETE FROM messages 
        WHERE chat_id = ? AND id NOT IN (
            SELECT id FROM messages 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        )
    """, (chat_id, chat_id, MAX_MESSAGES_PER_CHAT))

    conn.commit()
    conn.close()


def load_messages(chat_id, filter_type, filter_value):
    """Load messages from the database based on a filter.

    Args:
        chat_id (int): ID of the chat.
        filter_type (str): Type of filter ('recent_messages', 'recent_days', 'specific_date').
        filter_value: Value for the filter (int for recent, str for date).

    Returns:
        list: List of tuples (sender, text, timestamp, message_id).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if filter_type == "recent_messages":
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
                  (chat_id, filter_value))
    elif filter_type == "recent_days":
        min_date = (datetime.now() - timedelta(days=filter_value)).isoformat()
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? AND timestamp >= ? ORDER BY timestamp DESC",
                  (chat_id, min_date))
    elif filter_type == "specific_date":
        specific_date = datetime.strptime(filter_value, "%d %B %Y")
        min_date = specific_date.replace(
            hour=0, minute=0, second=0, microsecond=0).isoformat()
        max_date = (specific_date + timedelta(days=1) -
                    timedelta(seconds=1)).isoformat()
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp DESC",
                  (chat_id, min_date, max_date))

    messages = [(sender, text, datetime.fromisoformat(timestamp), message_id)
                for sender, text, timestamp, message_id in c.fetchall()]
    conn.close()
    print(
        f"Total messages loaded from database for chat {chat_id}: {len(messages)}")
    return [(sender, text, msg_time.replace(tzinfo=pytz.UTC) if msg_time.tzinfo is None else msg_time, message_id)
            for sender, text, msg_time, message_id in messages]
