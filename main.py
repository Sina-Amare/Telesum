from gui import run_gui
import asyncio
from config import API_ID, API_HASH
from telegram_client import TelegramManager
from database import (
    setup_database, save_chats, load_chats, save_search_history, load_search_history,
    delete_search_history_entry, delete_all_search_history, delete_messages,
    save_last_update_timestamp, load_last_update_timestamp
)
from utils import search_by_username
from ai_processor import summarize_text
from datetime import datetime
import pytz
import logging

# Set up logging
logger = logging.getLogger(__name__)


async def main(phone):
    """Run the main program loop for Telegram chat management."""
    setup_database()
    telegram = TelegramManager("session_name", API_ID, API_HASH)
    user_phone = phone

    print("\nSelect your timezone:")
    print("1. Iran (UTC+3:30)")
    print("2. United States (UTC-5:00, Eastern Time)")
    print("3. United Kingdom (UTC+0:00)")
    print("4. Other (UTC)")
    while True:
        country_choice = input("Enter choice (1-4): ")
        if country_choice in ["1", "2", "3", "4"]:
            break
        logger.warning(
            "Invalid choice. Please select a number between 1 and 4.")

    if country_choice == "1":
        user_timezone = pytz.timezone("Asia/Tehran")
    elif country_choice == "2":
        user_timezone = pytz.timezone("America/New_York")
    elif country_choice == "3":
        user_timezone = pytz.timezone("Europe/London")
    else:
        user_timezone = pytz.UTC

    logger.info(f"Timezone set to: {user_timezone}")

    try:
        await telegram.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Telegram: {e}")
        return

    try:
        user = await telegram.login(phone)
        logger.info(f"Logged in as: {user.first_name} ({user.phone})")
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return

    while True:
        print("=== Main Menu ===")
        print("1. List private chats")
        print("2. Search by username")
        print("3. View search history")
        print("4. Manage search history")
        print("5. Refresh chat list")
        print("6. Exit")
        while True:
            choice = input("Enter choice (1-6): ")
            if choice in ["1", "2", "3", "4", "5", "6"]:
                break
            logger.warning(
                "Invalid choice. Please select a number between 1 and 6.")

        if choice in ["1", "2"]:
            last_update = load_last_update_timestamp(user_phone)
            new_chats = await telegram.fetch_new_chats(last_update)
            if new_chats:
                save_chats(load_chats(user_phone) + new_chats, user_phone)
                save_last_update_timestamp(user_phone)
                logger.info(
                    f"Added {len(new_chats)} new chats to the database.")

            chats = load_chats(user_phone)
            if not chats:
                logger.info("No chats found in database. Refreshing...")
                chats = await telegram.fetch_chats()
                save_chats(chats, user_phone)
                save_last_update_timestamp(user_phone)

            if choice == "1":
                if chats:
                    logger.info("Your private chats:")
                    for i, (chat_id, chat_name, _) in enumerate(chats, 1):
                        logger.info(f"{i}. {chat_name} (ID: {chat_id})")
                    while True:
                        choice = input("Select a chat number (e.g., 1): ")
                        try:
                            choice = int(choice) - 1
                            if 0 <= choice < len(chats):
                                break
                            logger.warning(
                                f"Please select a number between 1 and {len(chats)}.")
                        except ValueError:
                            logger.warning(
                                "Invalid input. Please enter a number.")
                    chat_name, chat_id, username = chats[choice][1], chats[choice][0], chats[choice][2]
                    logger.info(f"Selected chat: {chat_name} (ID: {chat_id})")
                    search_term = username if username else chat_name
                    save_search_history(search_term, user_phone)
                    await process_chat_messages(telegram, chat_id, chat_name, user_timezone, user_phone)
                else:
                    logger.info("No private chats available.")

            elif choice == "2":
                while True:
                    username = input("Enter username (e.g., @username): ")
                    if username.strip():
                        break
                    logger.warning("Username cannot be empty.")
                chat_name, chat_id = search_by_username(username, chats)
                if chat_id:
                    logger.info(f"Found chat: {chat_name} (ID: {chat_id})")
                    save_search_history(username, user_phone)
                    await process_chat_messages(telegram, chat_id, chat_name, user_timezone, user_phone)
                else:
                    logger.info(f"No private chat found for {username}.")

        elif choice == "3":
            history = load_search_history(user_phone)
            if history:
                logger.info("Search History:")
                for i, (entry_id, username, timestamp) in enumerate(history, 1):
                    logger.info(f"{i}. {username} (Searched at: {timestamp})")
                while True:
                    choice = input("Select a username number (e.g., 1): ")
                    try:
                        choice = int(choice) - 1
                        if 0 <= choice < len(history):
                            break
                        logger.warning(
                            f"Please select a number between 1 and {len(history)}.")
                    except ValueError:
                        logger.warning("Invalid input. Please enter a number.")
                username = history[choice][1]
                chats = load_chats(user_phone)
                chat_name, chat_id = search_by_username(username, chats)
                if chat_id:
                    logger.info(f"Found chat: {chat_name} (ID: {chat_id})")
                    await process_chat_messages(telegram, chat_id, chat_name, user_timezone, user_phone)
                else:
                    logger.info(f"No private chat found for {username}.")
            else:
                logger.info("No search history available.")

        elif choice == "4":
            print("=== Manage Search History ===")
            print("1. Delete a specific search entry")
            print("2. Delete all search history")
            print("3. Delete messages for a chat")
            print("4. Back to main menu")
            while True:
                sub_choice = input("Enter choice (1-4): ")
                if sub_choice in ["1", "2", "3", "4"]:
                    break
                logger.warning(
                    "Invalid choice. Please select a number between 1 and 4.")

            if sub_choice == "1":
                history = load_search_history(user_phone)
                if history:
                    logger.info("Search History:")
                    for i, (entry_id, username, timestamp) in enumerate(history, 1):
                        logger.info(
                            f"{i}. {username} (Searched at: {timestamp})")
                    while True:
                        choice = input(
                            "Select a search entry to delete (e.g., 1): ")
                        try:
                            choice = int(choice) - 1
                            if 0 <= choice < len(history):
                                break
                            logger.warning(
                                f"Please select a number between 1 and {len(history)}.")
                        except ValueError:
                            logger.warning(
                                "Invalid input. Please enter a number.")
                    entry_id = history[choice][0]
                    delete_search_history_entry(entry_id)
                    logger.info(
                        f"Search entry for {history[choice][1]} deleted successfully.")
                else:
                    logger.info("No search history to delete.")

            elif sub_choice == "2":
                history = load_search_history(user_phone)
                if history:
                    print(
                        "Are you sure you want to delete all search history? This action cannot be undone.")
                    confirmation = input("Confirm (yes/no): ").lower()
                    if confirmation == "yes":
                        delete_all_search_history(user_phone)
                        logger.info("All search history deleted successfully.")
                    else:
                        logger.info("Deletion canceled.")
                else:
                    logger.info("No search history to delete.")

            elif sub_choice == "3":
                history = load_search_history(user_phone)
                if history:
                    logger.info("Search History:")
                    for i, (entry_id, username, timestamp) in enumerate(history, 1):
                        logger.info(
                            f"{i}. {username} (Searched at: {timestamp})")
                    while True:
                        choice = input(
                            "Select a chat to delete messages (e.g., 1): ")
                        try:
                            choice = int(choice) - 1
                            if 0 <= choice < len(history):
                                break
                            logger.warning(
                                f"Please select a number between 1 and {len(history)}.")
                        except ValueError:
                            logger.warning(
                                "Invalid input. Please enter a number.")
                    username = history[choice][1]
                    chats = load_chats(user_phone)
                    chat_name, chat_id = search_by_username(username, chats)
                    if chat_id:
                        logger.info(
                            f"Selected chat: {chat_name} (ID: {chat_id})")
                        print("Delete Messages:")
                        print("1. Delete a specific number of recent messages")
                        print("2. Delete messages from a specific date")
                        print("3. Delete all messages")
                        print("4. Cancel")
                        while True:
                            delete_choice = input("Enter choice (1-4): ")
                            if delete_choice in ["1", "2", "3", "4"]:
                                break
                            logger.warning(
                                "Invalid choice. Please select a number between 1 and 4.")

                        if delete_choice == "1":
                            while True:
                                try:
                                    count = int(
                                        input("Enter number of recent messages to delete (e.g., 10): "))
                                    if count > 0:
                                        break
                                    logger.warning(
                                        "Please enter a positive number.")
                                except ValueError:
                                    logger.warning(
                                        "Invalid input. Please enter a number.")
                            confirmation = input(
                                f"Confirm deletion of the last {count} messages for {chat_name}? (yes/no): ").lower()
                            if confirmation == "yes":
                                deleted_count = delete_messages(
                                    chat_id, user_phone, num_messages=count)
                                if deleted_count > 0:
                                    logger.info(
                                        f"Deleted {deleted_count} recent messages for {chat_name}.")
                                else:
                                    logger.info(
                                        f"No recent messages found for {chat_name}.")
                            else:
                                logger.info("Deletion canceled.")

                        elif delete_choice == "2":
                            while True:
                                date_str = input(
                                    "Enter date to delete messages from (e.g., 10 March 2025): ")
                                try:
                                    datetime.strptime(date_str, "%d %B %Y")
                                    break
                                except ValueError:
                                    logger.warning(
                                        "Invalid date format. Use 'DD Month YYYY' (e.g., '10 March 2025').")
                            confirmation = input(
                                f"Confirm deletion of messages from {date_str} for {chat_name}? (yes/no): ").lower()
                            if confirmation == "yes":
                                deleted_count = delete_messages(
                                    chat_id, user_phone, specific_date=date_str, user_timezone=user_timezone)
                                if deleted_count > 0:
                                    logger.info(
                                        f"Deleted {deleted_count} messages from {date_str} for {chat_name}.")
                                else:
                                    logger.info(
                                        f"No messages found from {date_str} for {chat_name}.")
                            else:
                                logger.info("Deletion canceled.")

                        elif delete_choice == "3":
                            confirmation = input(
                                f"Confirm deletion of all messages for {chat_name}? (yes/no): ").lower()
                            if confirmation == "yes":
                                deleted_count = delete_messages(
                                    chat_id, user_phone)
                                if deleted_count > 0:
                                    logger.info(
                                        f"Deleted {deleted_count} messages for {chat_name}.")
                                else:
                                    logger.info(
                                        f"No messages found for {chat_name}.")
                            else:
                                logger.info("Deletion canceled.")

                        elif delete_choice == "4":
                            logger.info("Deletion canceled.")
                    else:
                        logger.info(f"No chat found for username {username}.")
                else:
                    logger.info("No search history to select from.")

            elif sub_choice == "4":
                continue

        elif choice == "5":
            logger.info("Refreshing chat list...")
            chats = await telegram.fetch_chats()
            save_chats(chats, user_phone)
            save_last_update_timestamp(user_phone)
            logger.info("Chat list refreshed successfully.")

        elif choice == "6":
            break

    await telegram.disconnect()


async def process_chat_messages(telegram, chat_id, chat_name, user_timezone, user_phone):
    """Process and display messages for a given chat, including a summary."""
    filter_type, filter_value = await get_message_filter(telegram)
    if filter_type:
        if filter_type == "recent_messages":
            logger.info(f"Fetching recent messages for {chat_name}...")
            telegram_messages = await telegram.get_messages(chat_id, filter_type, filter_value, user_timezone, user_phone)
            if telegram_messages is None:
                return
            logger.info("Loading messages from database...")
            messages, _, _ = load_messages(
                chat_id, filter_type, filter_value, user_phone)
        else:
            logger.info(f"Checking database for messages in {chat_name}...")
            messages, full_day_covered, _ = load_messages(
                chat_id, filter_type, filter_value, user_phone)
            if not messages or (filter_type == "specific_date" and not full_day_covered):
                if not messages:
                    logger.info(
                        "No messages found in database. Fetching from Telegram...")
                else:
                    logger.info(
                        "Incomplete messages for this date. Fetching from Telegram...")
                telegram_messages = await telegram.get_messages(chat_id, filter_type, filter_value, user_timezone, user_phone)
                if telegram_messages is None:
                    return
                if telegram_messages:
                    messages = list({msg[3]: msg for msg in (
                        messages + telegram_messages)}.values())
                    messages.sort(key=lambda x: x[2], reverse=True)
                else:
                    logger.info("No messages fetched from Telegram.")

        if messages:
            logger.info("=== Messages ===")
            for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                local_time = timestamp.astimezone(user_timezone)
                logger.info(
                    f"{i}. {sender}: {msg} (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})")

            message_texts = [msg for _, msg, _, _ in messages]
            logger.info("=== Summary ===")
            summary = summarize_text(message_texts)
            logger.info(f"{summary.strip()}")
        else:
            if filter_type == "recent_messages":
                logger.info(
                    f"No messages found in the last {filter_value} messages.")
            elif filter_type == "recent_days":
                logger.info(
                    f"No messages found in the last {filter_value} days.")
            elif filter_type == "specific_date":
                logger.info(f"No messages found on {filter_value}.")


async def get_message_filter(telegram):
    """Get the message filter type and value from user input."""
    print("Select message filter:")
    print("1. Recent messages (e.g., last 10 messages)")
    print("2. Messages from recent days (e.g., last 7 days)")
    print("3. Messages from a specific date (e.g., 10 March 2025)")
    while True:
        choice = input("Enter choice (1-3): ")
        if choice in ["1", "2", "3"]:
            break
        logger.warning(
            "Invalid choice. Please select a number between 1 and 3.")

    if choice == "1":
        while True:
            try:
                limit = int(
                    input("Enter number of recent messages to fetch (e.g., 10): "))
                if limit > 0:
                    return "recent_messages", limit
                logger.warning("Please enter a positive number.")
            except ValueError:
                logger.warning("Invalid input. Please enter a number.")
    elif choice == "2":
        while True:
            try:
                days = int(input("Enter number of recent days (e.g., 7): "))
                if days > 0:
                    return "recent_days", days
                logger.warning("Please enter a positive number.")
            except ValueError:
                logger.warning("Invalid input. Please enter a number.")
    elif choice == "3":
        while True:
            date = input("Enter date (e.g., 10 March 2025): ")
            specific_date = telegram._parse_date(date)
            if specific_date:
                return "specific_date", date

if __name__ == '__main__':
    run_gui()
