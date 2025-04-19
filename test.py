from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Message
from config import DATABASE_URL
import pytz
import logging

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_timestamps():
    """Check and fix naive timestamps in the messages table."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        messages = session.query(Message).all()
        naive_count = 0
        for msg in messages:
            if msg.timestamp and msg.timestamp.tzinfo is None:
                naive_count += 1
                logger.warning(
                    f"Fixing naive timestamp for message ID {msg.message_id}")
                msg.timestamp = msg.timestamp.replace(tzinfo=pytz.UTC)
        session.commit()
        print(
            f"Checked {len(messages)} messages, fixed {naive_count} naive timestamps.")
        logger.info(
            f"Checked {len(messages)} messages, fixed {naive_count} naive timestamps")
    except Exception as e:
        session.rollback()
        print(f"Error fixing timestamps: {e}")
        logger.error(f"Error fixing timestamps: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    fix_timestamps()
