# utils.py
def search_by_username(username, chats):
    """Search for a chat by username in the list of chats."""
    username = username.strip().lstrip('@').lower()
    for chat_id, chat_name, chat_username in chats:
        if chat_username and chat_username.lower() == username:
            return chat_name, chat_id
    return None, None


def get_sender_name(sender, me):
    """Get a readable name for the message sender."""
    if not sender:
        return "Unknown"
    if sender.id == me.id:
        return "me"
    return sender.username or sender.first_name or "Unknown"


def get_message_content(message):
    """Extract the content of a message as a string."""
    if not message:
        return None
    if message.text:
        return message.text
    if message.photo:
        return "[Photo]"
    if message.video:
        return "[Video]"
    if message.document:
        return "[Document]"
    if message.sticker:
        return "[Sticker]"
    if message.audio:
        return "[Audio]"
    if message.voice:
        return "[Voice]"
    if message.location:
        return "[Location]"
    if message.contact:
        return "[Contact]"
    return "[Unknown Content]"
