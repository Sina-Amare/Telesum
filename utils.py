# utils.py


def get_sender_name(sender, me):
    """Determine the sender's name for a message.

    Args:
        sender: Sender object from Telegram (User or None).
        me: Current user object from Telegram.

    Returns:
        str: Sender's name or identifier.
    """
    if not sender:
        return "Unknown"
    if sender.id == me.id:
        return "me"
    if sender.username:
        return f"@{sender.username}"
    return sender.first_name or "Unnamed"


def get_message_content(message):
    """Extract content from a Telegram message.

    Args:
        message: Telegram message object.

    Returns:
        str: Message content or media type placeholder.
    """
    if message.message:
        return message.message
    if message.photo:
        return "[Photo]"
    if message.video:
        return "[Video]"
    if message.document:
        return "[Document]"
    if message.sticker:
        return "[Sticker]"
    if message.gif:
        return "[GIF]"
    return "[Unsupported message type]"


def search_by_username(username, chats):
    """Search for a chat by username in the list of chats.

    Args:
        username (str): Username to search for (with or without '@').
        chats (list): List of tuples (chat_id, name, username).

    Returns:
        tuple: (chat_name, chat_id) if found, (None, None) otherwise.
    """
    username = username.lstrip('@').lower()
    for chat_id, name, chat_username in chats:
        if chat_username and chat_username.lower() == username:
            return name, chat_id
    return None, None
