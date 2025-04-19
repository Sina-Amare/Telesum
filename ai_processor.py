import requests
from config import OPENROUTER_API_KEY


def summarize_text(messages):
    """
    Summarizes and analyzes a list of messages using DeepSeek via OpenRouter API.

    Args:
        messages (list): A list of message texts to summarize and analyze.

    Returns:
        str: An analytical and concise summary of the messages or an error message if the request fails.
    """
    if not messages:
        return "هیچ پیامی برای خلاصه‌سازی وجود ندارد."

    # Combine messages into a single text block
    combined_text = "\n".join(messages)
    prompt = (
        "پیام‌ها را به فارسی خلاصه کن و تحلیل دقیقی از آن‌ها ارائه بده. "
        "خلاصه باید به صورت یک پاراگراف خبری و تحلیلی باشد که نکات اصلی، عبارات کلیدی، روابط بین پیام‌ها، و احساسات مطرح‌شده را به‌طور جامع پوشش دهد. "
        "لطفاً دقت کن که جمله‌ها به‌طور کامل به پایان برسند و خلاصه به‌صورت یک متن یکپارچه و بدون بریدگی یا قطع ناگهانی ارائه شود:\n\n"
        f"{combined_text}\n\n"
        "خلاصه:"
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
        "max_tokens": 500,
        "temperature": 0.6,
    }

    try:
        # Send request to OpenRouter API
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise error for unsuccessful requests

        # Extract and clean the summary
        summary = response.json()["choices"][0]["message"]["content"].strip()

        # Ensure the summary is a single complete paragraph ending with proper punctuation.
        if not summary.endswith('.'):
            summary += "."
        return summary

    except requests.exceptions.RequestException as e:
        return "API error: Unable to summarize messages."
    except KeyError:
        return "API response parsing error."
    except Exception:
        return "An unexpected error occurred during summarization."


# Optional test function
if __name__ == "__main__":
    test_messages = [
        "سلام، امروز چطوری؟",
        "خوبم، مرسی! تو چطور؟",
        "عالیم، فقط دارم استراحت می‌کنم. برنامه‌ای داری؟",
        "چیز خاصی نه، شاید بعداً یه فیلم ببینم."
    ]
    summary = summarize_text(test_messages)
    print("Summary:", summary)
