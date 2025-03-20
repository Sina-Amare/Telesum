# utils.py
def search_by_username(username, chats):
    username = username.lstrip('@').lower()
    for chat_id, chat_name, chat_username in chats:
        if chat_username and chat_username.lower() == username:
            return chat_name, chat_id
    return None, None
