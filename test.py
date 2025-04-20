import logging
from database import setup_database

# Setup basic logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    setup_database()
