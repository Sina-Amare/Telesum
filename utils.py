# utils.py
def search_by_username(username, chats):
    """Search for a chat by username in the chat list.

    Args:
        username (str): Username to search for (with or without '@').
        chats (list): List of tuples (chat_id, chat_name, chat_username).

    Returns:
        tuple: (chat_name, chat_id) if found, (None, None) otherwise.
    """
    username = username.lstrip('@').lower()
    for chat_id, chat_name, chat_username in chats:
        if chat_username and chat_username.lower() == username:
            return chat_name, chat_id
    return None, None


def get_sender_name(sender, me):
    """Get the display name of a message sender.

    Args:
        sender: Telegram sender object or None.
        me: Current user object from TelegramManager.

    Returns:
        str: Formatted sender name.
    """
    if not sender:
        return "Unknown"
    if sender.id == me.id:
        return f"{me.username}(me)" if me.username else "me"
    return f"@{sender.username}" if sender.username else sender.first_name


def get_message_content(message):
    """Determine message type and return appropriate content.

    Args:
        message: Telegram message object.

    Returns:
        str: Message content or type descriptor.
    """
    if message.text:
        return message.text
    elif message.photo:
        return "[Photo]"
    elif message.gif:
        return "[GIF]"
    elif message.video:
        return "[Video]"
    elif message.audio:
        return "[Audio]"
    elif message.voice:
        return "[Voice Message]"
    elif message.sticker:
        return "[Sticker]"
    elif message.document:
        return "[Document]"
    else:
        return "[Unknown message type]"
