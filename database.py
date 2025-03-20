import sqlite3
from datetime import datetime, timedelta
import pytz
import os

DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "database.db")


def setup_database():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Create tables if they don't exist
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

    # Check if message_id column exists, if not, add it
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM chats")
    for chat_id, name, username in chats:
        c.execute("INSERT OR REPLACE INTO chats (id, name, username) VALUES (?, ?, ?)",
                  (chat_id, name, username))
    conn.commit()
    conn.close()


def load_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, username FROM chats")
    chats = c.fetchall()
    conn.close()
    return chats


def save_search_history(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO search_history (username, timestamp) VALUES (?, ?)",
              (username, timestamp))
    conn.commit()
    conn.close()


def load_search_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, timestamp FROM search_history ORDER BY timestamp DESC")
    history = c.fetchall()
    conn.close()
    print(f"Total search history entries: {len(history)}")
    return history


def delete_search_history_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def delete_all_search_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history")
    conn.commit()
    conn.close()


def save_messages(chat_id, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for sender, text, timestamp, message_id in messages:  # Now expecting message_id in the tuple
        c.execute("INSERT OR IGNORE INTO messages (message_id, chat_id, sender, text, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (message_id, chat_id, sender, text, timestamp.isoformat()))

    # Remove messages older than the most recent 1000 for this chat
    c.execute("""
        DELETE FROM messages 
        WHERE chat_id = ? AND id NOT IN (
            SELECT id FROM messages 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1000
        )
    """, (chat_id, chat_id))

    conn.commit()
    conn.close()


def load_messages(chat_id, filter_type, filter_value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT sender, text, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp DESC",
              (chat_id,))
    all_messages = [(sender, text, datetime.fromisoformat(timestamp))
                    for sender, text, timestamp in c.fetchall()]
    conn.close()

    print(
        f"Total messages loaded from database for chat {chat_id}: {len(all_messages)}")

    all_messages = [(sender, text, msg_time.replace(tzinfo=pytz.UTC) if msg_time.tzinfo is None else msg_time)
                    for sender, text, msg_time in all_messages]

    if filter_type == "recent_messages":
        if len(all_messages) >= filter_value:
            return all_messages[:filter_value]
        else:
            print(
                f"Not enough messages in database (have {len(all_messages)}, need {filter_value})")
            return None  # This triggers fetching from Telegram
    elif filter_type == "recent_days":
        min_date = (datetime.now() - timedelta(days=filter_value)
                    ).replace(tzinfo=pytz.UTC)
        filtered_messages = [msg for msg in all_messages if msg[2] >= min_date]
        return filtered_messages
    elif filter_type == "specific_date":
        specific_date = datetime.strptime(filter_value, "%d %B %Y")
        min_date = specific_date.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
        max_date = (min_date + timedelta(days=1) -
                    timedelta(seconds=1)).replace(tzinfo=pytz.UTC)
        filtered_messages = [
            msg for msg in all_messages if min_date <= msg[2] <= max_date]
        return filtered_messages
