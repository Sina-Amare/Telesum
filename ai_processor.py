import requests
from config import OPENROUTER_API_KEY


def summarize_text(messages):
    """
    Summarizes a list of messages using DeepSeek via OpenRouter API.

    Args:
        messages (list): A list of message texts to summarize.

    Returns:
        str: A concise summary of the messages or an error message if the request fails.
    """
    if not messages:
        return "No messages to summarize."

    # Combine messages into a single text block
    combined_text = "\n".join(messages)
    prompt = (
        "به صورت منطقی پیام هارو خلاصه کن. "
        "عبارات کلیدی و در نظر بگیر و جمع بندی ساختار یافته ای بده:\n\n"
        f"{combined_text}\n\n"
        "Summary:"
    )

    # OpenRouter API URL
    url = "https://openrouter.ai/api/v1/chat/completions"

    # Request headers
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # API payload
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.5,
    }

    try:
        # Send request to OpenRouter API
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise error for unsuccessful requests

        # Extract and clean the summary
        summary = response.json()["choices"][0]["message"]["content"].strip()

        # Remove redundant "Summary:" prefix if present
        return summary[len("Summary:"):].strip() if summary.startswith("Summary:") else summary

    except requests.exceptions.RequestException as e:
        return "API error: Unable to summarize messages."
    except KeyError:
        return "API response parsing error."
    except Exception:
        return "An unexpected error occurred during summarization."


# Optional test function
if __name__ == "__main__":
    test_messages = [
        "Hey, how are you today?",
        "I'm good, thanks! What about you?",
        "I'm great, just relaxing. Any plans?",
        "Not much, maybe I'll watch a movie later."
    ]
    summary = summarize_text(test_messages)
    print("Summary:", summary)
