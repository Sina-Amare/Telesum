import aiohttp  # Replace requests with aiohttp for async HTTP requests
from config import OPENROUTER_API_KEY


async def summarize_text(messages):
    """
    Summarizes and analyzes a list of messages using DeepSeek via OpenRouter API asynchronously.

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
        # Use aiohttp for asynchronous HTTP request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response.raise_for_status()  # Raise error for unsuccessful requests
                data = await response.json()

        # Extract and clean the summary
        summary = data["choices"][0]["message"]["content"].strip()

        # Ensure the summary is a single complete paragraph ending with proper punctuation
        if not summary.endswith('.'):
            summary += "."
        return summary

    except aiohttp.ClientError as e:
        return f"API error: Unable to summarize messages due to {str(e)}."
    except KeyError:
        return "API response parsing error."
    except Exception as e:
        return f"An unexpected error occurred during summarization: {str(e)}."

# Optional test function (for CLI testing, not used in GUI)
if __name__ == "__main__":
    import asyncio
    test_messages = [
        "سلام، امروز چطوری؟",
        "خوبم، مرسی! تو چطور؟",
        "عالیم، فقط دارم استراحت می‌کنم. برنامه‌ای داری؟",
        "چیز خاصی نه، شاید بعداً یه فیلم ببینم."
    ]

    async def test():
        summary = await summarize_text(test_messages)
        print("Summary:", summary)
    asyncio.run(test())
