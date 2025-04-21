from telethon.tl.types import User, Chat, Channel


def search_by_username(username, chats):
    """Search for a chat by username in the list of chats."""
    username = username.strip().lstrip('@').lower()
    for chat_id, chat_name, chat_username in chats:
        if chat_username and chat_username.lower() == username:
            return chat_name, chat_id
        # Also check if the username matches the chat name (for cases where username is not set)
        if chat_name.lower() == username:
            return chat_name, chat_id
    return None, None


def get_sender_name(sender, me):
    """Extract the sender's name from the sender object."""
    if not sender:
        return "Unknown"
    if isinstance(sender, User):
        if sender.id == me.id:
            return "You"
        return sender.first_name or sender.username or "Unknown User"
    elif isinstance(sender, (Chat, Channel)):
        return sender.title or "Unknown Group"
    return "Unknown"


def get_message_content(message):
    """Extract the content of a message in a human-readable format."""
    if not message:
        return None

    # Check for message attributes safely using hasattr
    if hasattr(message, 'text') and message.text:
        return message.text
    if hasattr(message, 'photo') and message.photo:
        return "[Photo]"
    if hasattr(message, 'video') and message.video:
        return "[Video]"
    if hasattr(message, 'document') and message.document:
        return "[Document]"
    if hasattr(message, 'sticker') and message.sticker:
        return "[Sticker]"
    if hasattr(message, 'audio') and message.audio:
        return "[Audio]"
    if hasattr(message, 'voice') and message.voice:
        return "[Voice]"
    if hasattr(message, 'location') and message.location:
        return "[Location]"
    if hasattr(message, 'contact') and message.contact:
        return "[Contact]"
    if hasattr(message, 'poll') and message.poll:
        return "[Poll]"
    if hasattr(message, 'dice') and message.dice:
        return "[Dice]"
    if hasattr(message, 'action') and message.action:
        return f"[Action: {str(message.action)}]"
    if hasattr(message, 'fwd_from') and message.fwd_from:
        return "[Forwarded Message]"
    if hasattr(message, 'via_bot') and message.via_bot:
        return "[Bot Message]"

    # Fallback for messages with no recognizable content
    return "[Unknown Content]"
