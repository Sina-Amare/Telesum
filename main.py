# main.py
import asyncio
from config import API_ID, API_HASH
from telegram_client import TelegramManager
from database import (
    setup_database, save_chats, load_chats, save_search_history, load_search_history,
    save_messages, load_messages, delete_search_history_entry, delete_all_search_history,
    delete_messages_by_chat_id
)
from utils import search_by_username
from ai_processor import summarize_text
from datetime import datetime
import pytz


async def main(phone):
    """Run the main program loop for Telegram chat management.

    Args:
        phone (str): User's phone number for Telegram login.
    """
    setup_database()
    telegram = TelegramManager("session_name", API_ID, API_HASH)

    # Prompt user to select timezone based on country
    print("Please select your country for timezone settings:")
    print("1. Iran (UTC+3:30)")
    print("2. United States (UTC-5:00, Eastern Time)")
    print("3. United Kingdom (UTC+0:00)")
    print("4. Other (UTC)")
    while True:
        country_choice = input("Enter your choice (1-4): ")
        if country_choice in ["1", "2", "3", "4"]:
            break
        print("Invalid choice! Please enter a number between 1 and 4.")

    if country_choice == "1":
        user_timezone = pytz.timezone("Asia/Tehran")
    elif country_choice == "2":
        user_timezone = pytz.timezone("America/New_York")
    elif country_choice == "3":
        user_timezone = pytz.timezone("Europe/London")
    else:
        user_timezone = pytz.UTC

    print(f"Timezone set to: {user_timezone}")

    try:
        await telegram.connect()
    except Exception as e:
        print(f"Error connecting to Telegram: {e}")
        return

    try:
        user = await telegram.login(phone)
        print(f"Successfully logged in as: {user.first_name} ({user.phone})")
    except Exception as e:
        print(f"Error logging in: {e}")
        return

    while True:
        print("\nOptions:")
        print("1. List all private chats")
        print("2. Search by username (e.g., @username)")
        print("3. Search history")
        print("4. Manage search history")
        print("5. Refresh chat list")
        print("6. Exit")
        while True:
            choice = input("Enter your choice (1-6): ")
            if choice in ["1", "2", "3", "4", "5", "6"]:
                break
            print("Invalid choice! Please enter a number between 1 and 6 (e.g., 1)")

        if choice == "1":
            chats = load_chats()
            if not chats:
                print("No chats in database, refreshing...")
                chats = await telegram.fetch_chats()
                save_chats(chats)
            if chats:
                print("\nYour private chats (real people only):")
                for i, (chat_id, chat_name, _) in enumerate(chats, 1):
                    print(f"{i}. {chat_name} (ID: {chat_id})")
                while True:
                    choice = input(
                        "\nEnter the number of the chat you want to process (e.g., 1): ")
                    try:
                        choice = int(choice) - 1
                        if 0 <= choice < len(chats):
                            break
                        print(
                            f"Invalid choice! Please enter a number between 1 and {len(chats)} (e.g., 1)")
                    except ValueError:
                        print("Invalid input! Please enter a valid number (e.g., 1)")
                chat_name, chat_id = chats[choice][1], chats[choice][0]
                print(f"\nSelected chat: {chat_name} (ID: {chat_id})")
                await process_chat_messages(telegram, chat_id, chat_name, user_timezone)
            else:
                print("No private chats found!")

        elif choice == "2":
            while True:
                username = input("Enter the username (e.g., @username): ")
                if username.strip():
                    break
                print(
                    "Username cannot be empty! Please enter a valid username (e.g., @username)")
            chats = load_chats()
            if not chats:
                print("No chats in database, refreshing...")
                chats = await telegram.fetch_chats()
                save_chats(chats)
            chat_name, chat_id = search_by_username(username, chats)
            if chat_id:
                print(f"\nFound chat: {chat_name} (ID: {chat_id})")
                await process_chat_messages(telegram, chat_id, chat_name, user_timezone)
                save_search_history(username)
            else:
                print(f"\nNo private chat found with {username}!")

        elif choice == "3":
            history = load_search_history()
            if history:
                print("\nSearch history:")
                for i, (entry_id, username, timestamp) in enumerate(history, 1):
                    print(f"{i}. {username} (Searched at: {timestamp})")
                while True:
                    choice = input(
                        "\nEnter the number of the username to process (e.g., 1): ")
                    try:
                        choice = int(choice) - 1
                        if 0 <= choice < len(history):
                            break
                        print(
                            f"Invalid choice! Please enter a number between 1 and {len(history)} (e.g., 1)")
                    except ValueError:
                        print("Invalid input! Please enter a valid number (e.g., 1)")
                username = history[choice][1]
                chats = load_chats()
                chat_name, chat_id = search_by_username(username, chats)
                if chat_id:
                    print(f"\nFound chat: {chat_name} (ID: {chat_id})")
                    await process_chat_messages(telegram, chat_id, chat_name, user_timezone)
                else:
                    print(f"\nNo private chat found with {username}!")
            else:
                print("No search history yet!")

        elif choice == "4":
            print("\nManage Search History:")
            print("1. Delete a specific search entry")
            print("2. Delete all search history")
            print("3. Delete messages for a chat from database")
            print("4. Back to main menu")
            while True:
                sub_choice = input("Enter your choice (1-4): ")
                if sub_choice in ["1", "2", "3", "4"]:
                    break
                print("Invalid choice! Please enter a number between 1 and 4 (e.g., 1)")

            if sub_choice == "1":
                history = load_search_history()
                if history:
                    print("\nSearch history:")
                    for i, (entry_id, username, timestamp) in enumerate(history, 1):
                        print(f"{i}. {username} (Searched at: {timestamp})")
                    while True:
                        choice = input(
                            "\nEnter the number of the search entry to delete (e.g., 1): ")
                        try:
                            choice = int(choice) - 1
                            if 0 <= choice < len(history):
                                break
                            print(
                                f"Invalid choice! Please enter a number between 1 and {len(history)} (e.g., 1)")
                        except ValueError:
                            print(
                                "Invalid input! Please enter a valid number (e.g., 1)")
                    entry_id = history[choice][0]
                    delete_search_history_entry(entry_id)
                    print(
                        f"Search entry for {history[choice][1]} deleted successfully!")
                else:
                    print("No search history to delete!")

            elif sub_choice == "2":
                history = load_search_history()
                if history:
                    print(
                        "\nAre you sure you want to delete all search history? This action cannot be undone.")
                    confirmation = input(
                        "Enter 'yes' to confirm, 'no' to cancel: ").lower()
                    if confirmation == "yes":
                        delete_all_search_history()
                        print("All search history deleted successfully!")
                    else:
                        print("Deletion canceled.")
                else:
                    print("No search history to delete!")

            elif sub_choice == "3":
                history = load_search_history()
                if history:
                    print("\nSearch history:")
                    for i, (entry_id, username, timestamp) in enumerate(history, 1):
                        print(f"{i}. {username} (Searched at: {timestamp})")
                    while True:
                        choice = input(
                            "\nEnter the number of the chat to delete its messages (e.g., 1): ")
                        try:
                            choice = int(choice) - 1
                            if 0 <= choice < len(history):
                                break
                            print(
                                f"Invalid choice! Please enter a number between 1 and {len(history)} (e.g., 1)")
                        except ValueError:
                            print(
                                "Invalid input! Please enter a valid number (e.g., 1)")
                    username = history[choice][1]
                    chats = load_chats()
                    chat_name, chat_id = search_by_username(username, chats)
                    if chat_id:
                        print(f"\nFound chat: {chat_name} (ID: {chat_id})")
                        confirmation = input(
                            f"Are you sure you want to delete all messages for {chat_name} (ID: {chat_id})? (yes/no): ").lower()
                        if confirmation == "yes":
                            delete_messages_by_chat_id(chat_id)
                            print(
                                f"Messages for {chat_name} deleted successfully!")
                        else:
                            print("Deletion canceled.")
                    else:
                        print(f"No chat found with username {username}!")
                else:
                    print("No search history to select from!")

            elif sub_choice == "4":
                continue

        elif choice == "5":
            print("Refreshing chat list...")
            chats = await telegram.fetch_chats()
            save_chats(chats)
            print("Chat list refreshed successfully!")

        elif choice == "6":
            break

    await telegram.disconnect()


async def process_chat_messages(telegram, chat_id, chat_name, user_timezone):
    """Process and display messages for a given chat, including a summary.

    Args:
        telegram (TelegramManager): Telegram client instance.
        chat_id (int): ID of the chat to process.
        chat_name (str): Name of the chat.
        user_timezone (pytz.timezone): User-selected timezone.
    """
    filter_type, filter_value = await get_message_filter(telegram)
    if filter_type:
        if filter_type == "recent_messages":
            # Always fetch recent messages from Telegram first
            print("Fetching recent messages from Telegram...")
            telegram_messages = await telegram.get_messages(chat_id, filter_type, filter_value, user_timezone)
            if telegram_messages:
                try:
                    save_messages(chat_id, telegram_messages)
                    print(
                        f"Saved {len(telegram_messages)} new messages to database.")
                except Exception as e:
                    print(f"Error saving messages to database: {e}")
            # Load the requested number of messages from database
            print("Loading messages from database...")
            messages, _, _ = load_messages(chat_id, filter_type, filter_value)
        else:
            # For other filters (recent_days, specific_date), use existing logic
            print("Loading messages from database...")
            messages, full_day_covered, _ = load_messages(
                chat_id, filter_type, filter_value)
            if not messages or (filter_type == "specific_date" and not full_day_covered):
                if not messages:
                    print("No messages found in database, fetching from Telegram...")
                else:
                    print(
                        "Not all messages for this date are in the database, fetching from Telegram...")
                telegram_messages = await telegram.get_messages(chat_id, filter_type, filter_value, user_timezone)
                if telegram_messages:
                    # Combine database and Telegram messages, deduplicate by message_id
                    messages = list({msg[3]: msg for msg in (
                        messages + telegram_messages)}.values())
                    # Sort by timestamp
                    messages.sort(key=lambda x: x[2], reverse=True)
                    try:
                        save_messages(chat_id, telegram_messages)
                        print(
                            f"Saved {len(telegram_messages)} new messages to database.")
                    except Exception as e:
                        print(f"Error saving messages to database: {e}")
                else:
                    print("No messages fetched from Telegram.")
            else:
                print(f"Loaded {len(messages)} messages from database.")

        if messages:
            print("\nMessages:")
            for i, (sender, msg, timestamp, message_id) in enumerate(messages, 1):
                local_time = timestamp.astimezone(user_timezone)
                print(
                    f"{i}. {sender}: {msg} (ID: {message_id}, {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')})")

            # Summarize message content
            message_texts = [msg for _, msg, _, _ in messages]
            print("\nSummary:")
            summary = summarize_text(message_texts)
            print(summary)
        else:
            if filter_type == "recent_messages":
                print(
                    f"\nNo messages found in the last {filter_value} messages!")
            elif filter_type == "recent_days":
                print(f"\nNo messages found in the last {filter_value} days!")
            elif filter_type == "specific_date":
                print(f"\nNo messages found on {filter_value}!")


async def get_message_filter(telegram):
    """Get the message filter type and value from user input.

    Args:
        telegram (TelegramManager): Telegram client instance.

    Returns:
        tuple: (filter_type, filter_value) or (None, None) if invalid.
    """
    print("\nHow would you like to fetch messages?")
    print("1. Recent messages (e.g., last 10 messages)")
    print("2. Messages from recent days (e.g., last 7 days)")
    print("3. Messages from a specific date (e.g., 10 March 2025)")
    while True:
        choice = input("Enter your choice (1-3): ")
        if choice in ["1", "2", "3"]:
            break
        print("Invalid choice! Please enter a number between 1 and 3 (e.g., 1)")

    if choice == "1":
        while True:
            try:
                limit = int(
                    input("Enter the number of recent messages to fetch (e.g., 10): "))
                if limit > 0:
                    return "recent_messages", limit
                print("Please enter a positive number (e.g., 10)")
            except ValueError:
                print("Invalid input! Please enter a valid number (e.g., 10)")
    elif choice == "2":
        while True:
            try:
                days = int(
                    input("Enter the number of recent days (e.g., 7): "))
                if days > 0:
                    return "recent_days", days
                print("Please enter a positive number (e.g., 7)")
            except ValueError:
                print("Invalid input! Please enter a valid number (e.g., 7)")
    elif choice == "3":
        while True:
            date = input("Enter the date (e.g., 10 March 2025): ")
            specific_date = telegram._parse_date(date)
            if specific_date:
                return "specific_date", date
            # Invalid date will prompt again


if __name__ == '__main__':
    while True:
        phone = input("Please enter your phone number (e.g., +989123456789): ")
        if phone.strip() and phone.startswith("+") and phone[1:].isdigit():
            break
        print(
            "Invalid phone number! Please enter a valid phone number (e.g., +989123456789)")
    try:
        asyncio.run(main(phone))
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
