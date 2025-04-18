import sqlite3
from datetime import datetime, timedelta
import pytz
import os
from config import MAX_MESSAGES_PER_CHAT

# Base directory for database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DB_DIR, "database.db")


def setup_database():
    """Initialize the SQLite database and create necessary tables with user_phone column."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Create chats table
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER,
                    name TEXT NOT NULL,
                    username TEXT,
                    user_phone TEXT NOT NULL,
                    PRIMARY KEY (id, user_phone))''')

    # Create search_history table
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_phone TEXT NOT NULL)''')

    # Create messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    sender TEXT,
                    text TEXT,
                    timestamp TEXT,
                    user_phone TEXT NOT NULL,
                    UNIQUE(chat_id, message_id, user_phone)
                )''')

    # Create last_update table for tracking last chat update timestamp
    c.execute('''CREATE TABLE IF NOT EXISTS last_update (
                    user_phone TEXT PRIMARY KEY,
                    last_update_timestamp TEXT NOT NULL)''')

    # Add message_id column if not exists
    c.execute("PRAGMA table_info(messages)")
    columns = [col[1] for col in c.fetchall()]
    if 'message_id' not in columns:
        c.execute("ALTER TABLE messages ADD COLUMN message_id INTEGER")
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS unique_message ON messages (chat_id, message_id, user_phone)")

    # Add user_phone column if not exists
    if 'user_phone' not in columns:
        c.execute(
            "ALTER TABLE messages ADD COLUMN user_phone TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")


def save_chats(chats, user_phone):
    """Save or update a list of chats to the SQLite database for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Load existing chats to avoid duplicates
    existing_chats = {chat_id: (name, username)
                      for chat_id, name, username in load_chats(user_phone)}

    new_or_updated = 0
    for chat_id, name, username in chats:
        # Save only new or changed chats
        if chat_id not in existing_chats or existing_chats[chat_id] != (name, username):
            c.execute("INSERT OR REPLACE INTO chats (id, name, username, user_phone) VALUES (?, ?, ?, ?)",
                      (chat_id, name, username, user_phone))
            new_or_updated += 1
    conn.commit()
    conn.close()
    print(f"Saved or updated {new_or_updated} chats for user {user_phone}.")


def load_chats(user_phone):
    """Load all chats from the SQLite database for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, name, username FROM chats WHERE user_phone = ?", (user_phone,))
    chats = c.fetchall()
    conn.close()
    return chats


def save_search_history(username, user_phone):
    """Save a username to the search history for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO search_history (username, timestamp, user_phone) VALUES (?, ?, ?)",
              (username, timestamp, user_phone))
    conn.commit()
    conn.close()


def load_search_history(user_phone):
    """Load the search history from the database for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, timestamp FROM search_history WHERE user_phone = ? ORDER BY timestamp DESC",
              (user_phone,))
    history = c.fetchall()
    conn.close()
    print(f"Total search history entries for {user_phone}: {len(history)}")
    return history


def delete_search_history_entry(entry_id):
    """Delete a specific search history entry by ID."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def delete_all_search_history(user_phone):
    """Delete all entries from the search history for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM search_history WHERE user_phone = ?", (user_phone,))
    conn.commit()
    conn.close()


def save_messages(chat_id, messages, user_phone):
    """Save messages to the database for a specific chat and user, avoiding duplicates."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_messages_count = 0

    for sender, text, timestamp, message_id in messages:
        # Try to insert message; duplicates are ignored due to UNIQUE constraint
        try:
            c.execute("INSERT INTO messages (message_id, chat_id, sender, text, timestamp, user_phone) VALUES (?, ?, ?, ?, ?, ?)",
                      (message_id, chat_id, sender, text, timestamp.isoformat(), user_phone))
            new_messages_count += 1
        except sqlite3.IntegrityError:
            continue

    # Remove excess messages beyond MAX_MESSAGES_PER_CHAT
    c.execute("""
        DELETE FROM messages 
        WHERE chat_id = ? AND user_phone = ? AND id NOT IN (
            SELECT id FROM messages 
            WHERE chat_id = ? AND user_phone = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        )
    """, (chat_id, user_phone, chat_id, user_phone, MAX_MESSAGES_PER_CHAT))

    conn.commit()
    conn.close()

    if new_messages_count > 0:
        print(
            f"Saved {new_messages_count} new messages to database for chat ID {chat_id} and user {user_phone}.")
    else:
        print(
            f"No new messages saved for chat ID {chat_id} and user {user_phone} (all were duplicates).")


def load_messages(chat_id, filter_type, filter_value, user_phone):
    """Load messages from the database based on a filter for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if filter_type == "recent_messages":
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? AND user_phone = ? ORDER BY timestamp DESC LIMIT ?",
                  (chat_id, user_phone, filter_value))
    elif filter_type == "recent_days":
        min_date = (datetime.now() - timedelta(days=filter_value)).isoformat()
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? AND user_phone = ? AND timestamp >= ? ORDER BY timestamp DESC",
                  (chat_id, user_phone, min_date))
    elif filter_type == "specific_date":
        specific_date = datetime.strptime(filter_value, "%d %B %Y")
        min_date = specific_date.replace(
            hour=0, minute=0, second=0, microsecond=0).isoformat()
        max_date = (specific_date + timedelta(days=1) -
                    timedelta(seconds=1)).isoformat()
        c.execute("SELECT sender, text, timestamp, message_id FROM messages WHERE chat_id = ? AND user_phone = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp DESC",
                  (chat_id, user_phone, min_date, max_date))

    messages = [(sender, text, datetime.fromisoformat(timestamp), message_id)
                for sender, text, timestamp, message_id in c.fetchall()]
    conn.close()

    if messages:
        print(
            f"Messages found in database for chat ID {chat_id} and user {user_phone}: {len(messages)} total.")
    else:
        print(
            f"No messages found in database for chat ID {chat_id} and user {user_phone} with the given filter.")

    # Convert timestamps to UTC-aware
    messages = [(sender, text, msg_time.replace(tzinfo=pytz.UTC) if msg_time.tzinfo is None else msg_time, message_id)
                for sender, text, msg_time, message_id in messages]

    # Check if full day is covered for specific_date filter
    if filter_type == "specific_date" and messages:
        earliest_timestamp = min(msg[2] for msg in messages)
        latest_timestamp = max(msg[2] for msg in messages)
        full_day_covered = (earliest_timestamp <= specific_date.replace(hour=0, minute=0, second=0, tzinfo=pytz.UTC) and
                            latest_timestamp >= specific_date.replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC))
        return messages, full_day_covered, latest_timestamp

    return messages, False, None


def delete_messages_by_chat_id(chat_id, user_phone):
    """Delete all messages for a specific chat ID and user from the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE chat_id = ? AND user_phone = ?",
              (chat_id, user_phone))
    conn.commit()
    conn.close()
    print(
        f"All messages for chat ID {chat_id} and user {user_phone} deleted from database.")


def save_last_update_timestamp(user_phone):
    """Save the timestamp of the last chat update for a specific user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Store timestamp in UTC
    timestamp = datetime.now(pytz.UTC).isoformat()
    c.execute("INSERT OR REPLACE INTO last_update (user_phone, last_update_timestamp) VALUES (?, ?)",
              (user_phone, timestamp))
    conn.commit()
    conn.close()


def load_last_update_timestamp(user_phone):
    """Load the timestamp of the last chat update for a specific user as a UTC-aware datetime."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT last_update_timestamp FROM last_update WHERE user_phone = ?",
              (user_phone,))
    result = c.fetchone()
    conn.close()
    if result:
        # Parse timestamp and ensure it's UTC-aware
        dt = datetime.fromisoformat(result[0])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt
    return None
