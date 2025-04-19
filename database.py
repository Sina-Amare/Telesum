from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, BigInteger, text, select
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timedelta
import pytz
from config import MAX_MESSAGES_PER_CHAT, DATABASE_URL, VERBOSE_LOGGING
import logging

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

# Define database models


class Chat(Base):
    """Model for the chats table."""
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str | None] = mapped_column(String)
    user_phone: Mapped[str] = mapped_column(String, nullable=False)
    __table_args__ = (UniqueConstraint(
        "id", "user_phone", name="uq_chat_id_user_phone"),)


class SearchHistory(Base):
    """Model for the search_history table."""
    __tablename__ = "search_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_phone: Mapped[str] = mapped_column(String, nullable=False)


class Message(Base):
    """Model for the messages table."""
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    sender: Mapped[str | None] = mapped_column(String)
    text: Mapped[str | None] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    user_phone: Mapped[str] = mapped_column(String, nullable=False)
    __table_args__ = (UniqueConstraint("chat_id", "message_id",
                      "user_phone", name="uq_message_chat_id_message_id_user_phone"),)


class LastUpdate(Base):
    """Model for the last_update table."""
    __tablename__ = "last_update"
    user_phone: Mapped[str] = mapped_column(String, primary_key=True)
    last_update_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False)


def setup_database():
    """Initialize the PostgreSQL database and create necessary tables."""
    try:
        Base.metadata.create_all(engine)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        logger.error(f"Error initializing database: {e}")
        raise


def save_chats(chats, user_phone):
    """Save or update a list of chats to the database for a specific user."""
    session = Session()
    try:
        existing_chats = {chat.id: (chat.name, chat.username) for chat in session.query(
            Chat).filter_by(user_phone=user_phone).all()}
        new_or_updated = 0
        for chat_id, name, username in chats:
            if chat_id not in existing_chats or existing_chats[chat_id] != (name, username):
                session.merge(Chat(id=chat_id, name=name,
                              username=username, user_phone=user_phone))
                new_or_updated += 1
        session.commit()
        if new_or_updated > 0:
            print(f"Updated {new_or_updated} chats for user {user_phone}.")
            logger.info(
                f"Updated {new_or_updated} chats for user {user_phone}")
    except Exception as e:
        session.rollback()
        print(f"Error saving chats: {e}")
        logger.error(f"Error saving chats: {e}")
    finally:
        session.close()


def load_chats(user_phone):
    """Load all chats from the database for a specific user."""
    session = Session()
    try:
        chats = [(chat.id, chat.name, chat.username) for chat in session.query(
            Chat).filter_by(user_phone=user_phone).all()]
        logger.info(f"Loaded {len(chats)} chats for user {user_phone}")
        return chats
    except Exception as e:
        print(f"Error loading chats: {e}")
        logger.error(f"Error loading chats: {e}")
        return []
    finally:
        session.close()


def save_search_history(username, user_phone):
    """Save a username to the search history for a specific user."""
    session = Session()
    try:
        timestamp = datetime.now(pytz.UTC)
        session.add(SearchHistory(username=username,
                    timestamp=timestamp, user_phone=user_phone))
        session.commit()
        print(f"Saved search history for username: {username}")
        logger.info(f"Saved search history for username: {username}")
    except Exception as e:
        session.rollback()
        print(f"Error saving search history: {e}")
        logger.error(f"Error saving search history: {e}")
    finally:
        session.close()


def load_search_history(user_phone):
    """Load the search history from the database for a specific user."""
    session = Session()
    try:
        history = [(entry.id, entry.username, entry.timestamp.isoformat()) for entry in
                   session.query(SearchHistory).filter_by(user_phone=user_phone).order_by(SearchHistory.timestamp.desc()).all()]
        print(
            f"Found {len(history)} search history entries for user {user_phone}.")
        logger.info(
            f"Found {len(history)} search history entries for user {user_phone}")
        return history
    except Exception as e:
        print(f"Error loading search history: {e}")
        logger.error(f"Error loading search history: {e}")
        return []
    finally:
        session.close()


def delete_search_history_entry(entry_id):
    """Delete a specific search history entry by ID."""
    session = Session()
    try:
        session.query(SearchHistory).filter_by(id=entry_id).delete()
        session.commit()
        logger.info(f"Deleted search history entry ID {entry_id}")
    except Exception as e:
        session.rollback()
        print(f"Error deleting search history entry: {e}")
        logger.error(f"Error deleting search history entry: {e}")
    finally:
        session.close()


def delete_all_search_history(user_phone):
    """Delete all entries from the search history for a specific user."""
    session = Session()
    try:
        session.query(SearchHistory).filter_by(user_phone=user_phone).delete()
        session.commit()
        logger.info(f"Deleted all search history for user {user_phone}")
    except Exception as e:
        session.rollback()
        print(f"Error deleting all search history: {e}")
        logger.error(f"Error deleting all search history: {e}")
    finally:
        session.close()


def save_messages(db_session, chat_id, user_phone, messages, MAX_MESSAGES_PER_CHAT=5000):
    """Save messages to the database, skipping duplicates efficiently."""
    # Fetch existing message IDs for the chat and user
    existing_message_ids = set(
        row[0] for row in db_session.execute(
            select(Message.message_id).filter_by(
                chat_id=chat_id, user_phone=user_phone)
        ).fetchall()
    )

    new_messages_count = 0
    duplicate_count = 0
    total_messages = len(messages)

    for i, (sender, message_text, timestamp, message_id) in enumerate(messages):
        if message_id in existing_message_ids:
            duplicate_count += 1
            logger.debug(
                f"Skipped duplicate message ID {message_id} for chat ID {chat_id}")
            continue

        try:
            sender = str(sender) if sender is not None else "Unknown"
            message_text = str(
                message_text) if message_text is not None else None
            if not isinstance(message_id, (int, type(None))):
                raise ValueError(f"Invalid message_id: {message_id}")
            if not isinstance(chat_id, int):
                raise ValueError(f"Invalid chat_id: {chat_id}")
            if timestamp.tzinfo is None:
                logger.warning(
                    f"Naive timestamp detected for message ID {message_id}, making aware")
                timestamp = timestamp.replace(tzinfo=pytz.UTC)

            message = Message(
                message_id=message_id,
                chat_id=chat_id,
                sender=sender,
                text=message_text,
                timestamp=timestamp,
                user_phone=user_phone
            )
            db_session.add(message)
            db_session.flush()
            new_messages_count += 1

            if VERBOSE_LOGGING:
                print(
                    f"Added message {i+1}/{total_messages}: {sender}: {message_text} (ID: {message_id}, {timestamp})")
            logger.debug(
                f"Added message {i+1}: sender={sender}, text={message_text}, timestamp={timestamp}, message_id={message_id}")

        except IntegrityError as ie:
            db_session.rollback()
            duplicate_count += 1
            logger.warning(
                f"Duplicate message ID {message_id} for chat ID {chat_id}: {ie}")
            continue
        except Exception as e:
            db_session.rollback()
            print(f"Error adding message {i+1}: {e}")
            logger.error(f"Error adding message {i+1}: {e}")
            continue

    if new_messages_count > 0:
        try:
            db_session.commit()
            db_session.execute(text("""
                DELETE FROM messages 
                WHERE chat_id = :chat_id AND user_phone = :user_phone AND id NOT IN (
                    SELECT id FROM messages 
                    WHERE chat_id = :chat_id AND user_phone = :user_phone 
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                )
            """), {"chat_id": chat_id, "user_phone": user_phone, "limit": MAX_MESSAGES_PER_CHAT})
            db_session.commit()
            logger.info(
                f"Added {new_messages_count} new messages for chat ID {chat_id}")
        except Exception as e:
            db_session.rollback()
            logger.error(
                f"Error committing messages for chat ID {chat_id}: {e}")
            print(
                f"Failed to save {new_messages_count} messages for chat ID {chat_id}: {e}")
    else:
        logger.info(f"No new messages to save for chat ID {chat_id}")

    if duplicate_count > 0:
        logger.info(
            f"Skipped {duplicate_count} duplicate messages for chat ID {chat_id}")
    print(
        f"Processed {total_messages} messages: {new_messages_count} new, {duplicate_count} already in database")
    return new_messages_count


def load_messages(chat_id, filter_type, filter_value, user_phone):
    """Load messages from the database based on a filter for a specific user."""
    session = Session()
    try:
        query = session.query(Message).filter_by(
            chat_id=chat_id, user_phone=user_phone)

        if filter_type == "recent_messages":
            query = query.order_by(
                Message.timestamp.desc()).limit(filter_value)
        elif filter_type == "recent_days":
            min_date = datetime.now(pytz.UTC) - timedelta(days=filter_value)
            query = query.filter(Message.timestamp >= min_date).order_by(
                Message.timestamp.desc())
        elif filter_type == "specific_date":
            specific_date = datetime.strptime(filter_value, "%d %B %Y")
            specific_date = specific_date.replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)
            min_date = specific_date
            max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(Message.timestamp.between(
                min_date, max_date)).order_by(Message.timestamp.desc())

        messages = []
        for msg in query.all():
            timestamp = msg.timestamp
            if timestamp.tzinfo is None:
                logger.warning(
                    f"Naive timestamp found in database for message ID {msg.message_id}, making aware")
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            messages.append((msg.sender, msg.text, timestamp, msg.message_id))

        full_day_covered = False
        latest_timestamp = None
        if filter_type == "specific_date" and messages:
            earliest_timestamp = min(msg[2] for msg in messages)
            latest_timestamp = max(msg[2] for msg in messages)
            full_day_covered = (
                earliest_timestamp <= specific_date and
                latest_timestamp >= specific_date.replace(
                    hour=23, minute=59, second=59, tzinfo=pytz.UTC)
            )

        logger.info(
            f"Loaded {len(messages)} messages for chat ID {chat_id}, filter: {filter_type}")
        return messages, full_day_covered, latest_timestamp
    except Exception as e:
        print(f"Error loading messages: {e}")
        logger.error(f"Error loading messages: {e}")
        return [], False, None
    finally:
        session.close()


def delete_messages(chat_id, user_phone, num_messages=None, specific_date=None):
    """Delete messages for a specific chat and user from the database."""
    session = Session()
    try:
        query = session.query(Message).filter_by(
            chat_id=chat_id, user_phone=user_phone)

        if num_messages is not None:
            subquery = (
                select(Message.id)
                .where(Message.chat_id == chat_id, Message.user_phone == user_phone)
                .order_by(Message.timestamp.desc())
                .limit(num_messages)
            )
            query = query.filter(Message.id.in_(subquery))
        elif specific_date is not None:
            specific_date = datetime.strptime(specific_date, "%d %B %Y").replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC
            )
            min_date = specific_date
            max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(Message.timestamp.between(min_date, max_date))

        deleted_count = query.delete(synchronize_session=False)
        session.commit()
        print(f"Deleted {deleted_count} messages for chat ID {chat_id}")
        logger.info(f"Deleted {deleted_count} messages for chat ID {chat_id}")
        return deleted_count
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Error deleting messages: {e}")
        logger.error(f"Error deleting messages: {e}")
        return 0
    finally:
        session.close()


def save_last_update_timestamp(user_phone):
    """Save the timestamp of the last chat update for a specific user."""
    session = Session()
    try:
        timestamp = datetime.now(pytz.UTC)
        session.merge(LastUpdate(user_phone=user_phone,
                      last_update_timestamp=timestamp))
        session.commit()
        logger.info(f"Saved last update timestamp for user {user_phone}")
    except Exception as e:
        session.rollback()
        print(f"Error saving last update timestamp: {e}")
        logger.error(f"Error saving last update timestamp: {e}")
    finally:
        session.close()


def load_last_update_timestamp(user_phone):
    """Load the timestamp of the last chat update for a specific user as a UTC-aware datetime."""
    session = Session()
    try:
        entry = session.query(LastUpdate).filter_by(
            user_phone=user_phone).first()
        if entry:
            timestamp = entry.last_update_timestamp
            if timestamp.tzinfo is None:
                logger.warning(
                    f"Naive last_update_timestamp for user {user_phone}, making aware")
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            logger.info(f"Loaded last update timestamp for user {user_phone}")
            return timestamp
        return None
    except Exception as e:
        print(f"Error loading last update timestamp: {e}")
        logger.error(f"Error loading last update timestamp: {e}")
        return None
    finally:
        session.close()
