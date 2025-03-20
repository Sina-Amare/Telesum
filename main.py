import asyncio
from config import API_ID, API_HASH
from telegram_client import TelegramManager
from database import setup_database, save_chats, load_chats, save_search_history, load_search_history, save_messages, load_messages, delete_search_history_entry, delete_all_search_history
from utils import search_by_username
from datetime import datetime


async def main(phone):
    setup_database()
    telegram = TelegramManager("session_name", API_ID, API_HASH)
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
        print("1. Search by username (e.g., @username)")
        print("2. List all private chats")
        print("3. Search history")
        print("4. Refresh chat list")
        print("5. Exit")
        print("6. Manage search history")
        while True:
            choice = input("Enter your choice (1-6): ")
            if choice in ["1", "2", "3", "4", "5", "6"]:
                break
            print("Invalid choice! Please enter a number between 1 and 6 (e.g., 1)")

        if choice == "1":
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
                filter_type, filter_value = await get_message_filter(telegram)
                if filter_type:
                    messages = load_messages(
                        chat_id, filter_type, filter_value)
                    if not messages:
                        print(
                            "No messages found in database, fetching from Telegram...")
                        messages = await telegram.get_messages(chat_id, filter_type, filter_value)
                        if messages is not None:
                            try:
                                save_messages(chat_id, messages)
                            except Exception as e:
                                print(
                                    f"Error saving messages to database: {e}")
                    else:
                        print("Messages loaded from database.")
                    if messages:
                        save_search_history(username)
                        print("\nMessages:")
                        for i, (sender, msg, timestamp, _) in enumerate(messages, 1):
                            print(
                                f"{i}. {sender}: {msg} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                    else:
                        if filter_type == "recent_messages":
                            print(
                                f"\nNo messages found in the last {filter_value} messages!")
                        elif filter_type == "recent_days":
                            print(
                                f"\nNo messages found in the last {filter_value} days!")
                        elif filter_type == "specific_date":
                            print(f"\nNo messages found on {filter_value}!")
            else:
                print(f"\nNo private chat found with {username}!")

        elif choice == "2":
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
                filter_type, filter_value = await get_message_filter(telegram)
                if filter_type:
                    messages = load_messages(
                        chat_id, filter_type, filter_value)
                    if not messages:
                        print(
                            "No messages found in database, fetching from Telegram...")
                        messages = await telegram.get_messages(chat_id, filter_type, filter_value)
                        if messages is not None:
                            try:
                                save_messages(chat_id, messages)
                            except Exception as e:
                                print(
                                    f"Error saving messages to database: {e}")
                    else:
                        print("Messages loaded from database.")
                    if messages:
                        print("\nMessages:")
                        for i, (sender, msg, timestamp, _) in enumerate(messages, 1):
                            print(
                                f"{i}. {sender}: {msg} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                    else:
                        if filter_type == "recent_messages":
                            print(
                                f"\nNo messages found in the last {filter_value} messages!")
                        elif filter_type == "recent_days":
                            print(
                                f"\nNo messages found in the last {filter_value} days!")
                        elif filter_type == "specific_date":
                            print(f"\nNo messages found on {filter_value}!")
            else:
                print("No private chats found!")

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
                    filter_type, filter_value = await get_message_filter(telegram)
                    if filter_type:
                        messages = load_messages(
                            chat_id, filter_type, filter_value)
                        if not messages:
                            print(
                                "No messages found in database, fetching from Telegram...")
                            messages = await telegram.get_messages(chat_id, filter_type, filter_value)
                            if messages is not None:
                                try:
                                    save_messages(chat_id, messages)
                                except Exception as e:
                                    print(
                                        f"Error saving messages to database: {e}")
                        else:
                            print("Messages loaded from database.")
                        if messages:
                            print("\nMessages:")
                            for i, (sender, msg, timestamp, _) in enumerate(messages, 1):
                                print(
                                    f"{i}. {sender}: {msg} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
                        else:
                            if filter_type == "recent_messages":
                                print(
                                    f"\nNo messages found in the last {filter_value} messages!")
                            elif filter_type == "recent_days":
                                print(
                                    f"\nNo messages found in the last {filter_value} days!")
                            elif filter_type == "specific_date":
                                print(
                                    f"\nNo messages found on {filter_value}!")
                else:
                    print(f"\nNo private chat found with {username}!")
            else:
                print("No search history yet!")

        elif choice == "4":
            print("Refreshing chat list...")
            chats = await telegram.fetch_chats()
            save_chats(chats)
            print("Chat list refreshed successfully!")

        elif choice == "5":
            break

        elif choice == "6":
            print("\nManage Search History:")
            print("1. Delete a specific search entry")
            print("2. Delete all search history")
            print("3. Back to main menu")
            while True:
                sub_choice = input("Enter your choice (1-3): ")
                if sub_choice in ["1", "2", "3"]:
                    break
                print("Invalid choice! Please enter a number between 1 and 3 (e.g., 1)")

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
                continue

    await telegram.disconnect()


async def get_message_filter(telegram):
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
            # If the date is invalid, it will prompt again

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
