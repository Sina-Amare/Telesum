# TeleSum

**TeleSum** is an open-source tool designed to summarize and analyze Telegram chats using AI. It leverages the Telegram API to fetch private chats and the Gemini API for natural language processing tasks such as conversation summarization, sentiment analysis, music extraction, and message suggestion. This tool is built with Python and aims to provide an intuitive and user-friendly experience for analyzing Telegram conversations.

## Features

- **Fetch Private Chats**: Retrieve a list of private chats from your Telegram account.
- **Message Filtering**: Filter messages by:
  - Recent messages (e.g., last 10 messages)
  - Recent days (e.g., last 7 days)
  - Specific date (e.g., 10 December 2024)
- **Local Database Storage**: Store chats and messages in a local SQLite database for faster access.
- **Search History Management**: Keep track of searched usernames and manage search history.
- **CLI Interface**: Currently features a command-line interface (CLI) for interacting with the tool.
- **Planned Features** (coming soon):
  - AI-powered conversation summarization using Gemini API.
  - Sentiment analysis to detect the tone of conversations (positive, negative, neutral).
  - Extraction of music names and links from chats.
  - Suggestion of the next message to continue the conversation.
  - A graphical user interface (GUI) using PyQt6.

## Tech Stack

- **Backend**: Python, [Telethon](https://github.com/LonamiWebs/Telethon) for Telegram API integration.
- **Database**: SQLite for local storage.
- **NLP (Planned)**: Gemini API for summarization, sentiment analysis, and more.
- **GUI (Planned)**: PyQt6 for a user-friendly graphical interface.
- **Build Tool (Planned)**: PyInstaller to create standalone `.exe` files.

## Installation

### Prerequisites
- Python 3.8 or higher
- A Telegram account with API credentials (API ID and API Hash)
- (Optional) Gemini API Key for NLP features (coming soon)
