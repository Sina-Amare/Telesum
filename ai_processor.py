import aiohttp  # Replace requests with aiohttp for async HTTP requests
from config import OPENROUTER_API_KEY
from datetime import datetime
import pytz


async def summarize_text(messages_data):
    """
    Summarizes and analyzes a list of messages with metadata using DeepSeek via OpenRouter API asynchronously.

    Args:
        messages_data (list): A list of tuples (sender, text, timestamp, message_id) to summarize and analyze.

    Returns:
        str: A structured summary with general analysis, sentiment analysis, and events, or an error message if the request fails.
    """
    if not messages_data:
        return "No messages available for summarization."

    # Extract and format message data
    messages = []
    senders = set()
    timestamps = []
    for sender, text, timestamp, message_id in messages_data:
        if text:  # Only include messages with actual text
            # Ensure timestamp is timezone-aware
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            messages.append(f"{sender}: {text}")
            senders.add(sender)
            timestamps.append(timestamp)

    if not messages:
        return "No text messages found for summarization."

    # Combine messages into a single text block
    combined_text = "\n".join(messages)

    # Calculate some statistics for the summary
    num_messages = len(messages)
    num_senders = len(senders)
    if timestamps:
        min_time = min(timestamps).astimezone(pytz.UTC)
        max_time = max(timestamps).astimezone(pytz.UTC)
        duration_minutes = int((max_time - min_time).total_seconds() / 60)
    else:
        duration_minutes = 0

    # Design the prompt
    prompt = (
        "شما یک تحلیل‌گر حرفه‌ای چت هستید و تخصص شما تحلیل دقیق مکالمات به زبان فارسی است. لطفاً پیام‌های زیر را تحلیل کنید و یک گزارش جامع و حرفه‌ای به زبان فارسی ارائه دهید. "
        "در زبان فارسی، لحن و زمینه مکالمه اهمیت زیادی دارد. برای مثال، عباراتی مثل 'دهنتو گاییدم' یا 'احمق' در مکالمات دوستانه و شوخی‌آمیز معمولاً توهین محسوب نمی‌شوند و صرفاً بخشی از لحن طنزآمیز هستند. "
        "بنابراین، هنگام تحلیل احساسات و لحن، حتماً زمینه مکالمه و روابط بین کاربران را در نظر بگیرید و از قضاوت اشتباه درباره عبارات پرهیز کنید.\n\n"
        "تحلیل شما باید شامل سه بخش زیر باشد:\n"
        "1. **خلاصه کلی:** یک پاراگراف تحلیلی (حداکثر ۵۰۰ توکن) که موضوعات اصلی، لحن کلی، نکات کلیدی، و روابط بین پیام‌ها را پوشش دهد. "
        "اطمینان حاصل کنید که پاراگراف با یک جمله کامل به پایان برسد و متن ناقص نباشد. لحن و زمینه مکالمه را به دقت تحلیل کنید.\n"
        "2. **تحلیل احساسات:** ابتدا یک جمله بنویسید که احساسات غالب مکالمه (مثلاً خوشحالی، ناراحتی، دعوا، رمانتیک) و تغییرات احساسی را توصیف کند. "
        "برای هر حالت احساسی از یک استیکر مرتبط استفاده کنید (مثلاً 😊 برای خوشحالی، 😢 برای ناراحتی، 😡 برای دعوا، ❤️ برای رمانتیک). "
        "اگر مکالمه خنثی بود و هیچ احساس خاصی نداشت، آن را مشخص کنید (مثلاً 'مکالمه خنثی بود 😐'). "
        "سپس در چند خط توضیح دهید که کدام جملات یا کلمات باعث این برداشت شدند و چرا این احساسات شناسایی شدند. حتماً به زمینه و لحن توجه کنید.\n"
        "3. **رویدادها:** برنامه‌ریزی‌ها یا کارهایی که کاربران در مکالمه به آن اشاره کرده‌اند یا انجام داده‌اند را به صورت یک لیست (bullet points) مشخص کنید. "
        "اگر زمان یا مکان مشخصی ذکر شده، آن را هم بنویسید. اگر اطلاعاتی وجود ندارد، فقط فعالیت را ذکر کنید. "
        "رویدادها را بر اساس اهمیت مرتب کنید: ابتدا برنامه‌ریزی‌های قطعی (مثلاً 'تصمیم گرفتند') و سپس پیشنهادها (مثلاً 'پیشنهاد داد').\n\n"
        "پیام‌ها:\n"
        f"{combined_text}\n\n"
        "تحلیل:"
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
        "max_tokens": 1000,  # Increased to accommodate all sections
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

        # Add statistical info and adjust section titles to English
        stats_line = f"This conversation includes {num_messages} messages between {num_senders} people over {duration_minutes} minutes."
        if summary.startswith("**خلاصه کلی:**"):
            sections = summary.split("\n\n")
            for i, section in enumerate(sections):
                if section.startswith("**خلاصه کلی:**"):
                    general_summary = section[len("**خلاصه کلی:**"):].strip()
                    if not general_summary.endswith('.'):
                        general_summary += "."
                    general_summary += f" {stats_line}"
                    sections[i] = f"**General Summary:**\n{general_summary}"
                elif section.startswith("**تحلیل احساسات:**"):
                    sections[i] = section.replace(
                        "**تحلیل احساسات:**", "**Sentiment Analysis:**")
                elif section.startswith("**رویدادها:**"):
                    sections[i] = section.replace(
                        "**رویدادها:**", "**Events:**")
            summary = "\n\n".join(sections)
        else:
            summary = f"**General Summary:**\n{stats_line}\n\n{summary}"

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
    test_messages_data = [
        ("علی", "سلام، امروز چطوری؟", datetime.now(pytz.UTC), 1),
        ("مریم", "خوبم، مرسی! تو چطور؟", datetime.now(pytz.UTC), 2),
        ("علی", "عالیم، فقط دارم استراحت می‌کنم. برنامه‌ای داری؟",
         datetime.now(pytz.UTC), 3),
        ("مریم", "چیز خاصی نه، شاید بعداً یه فیلم ببینم.", datetime.now(pytz.UTC), 4),
    ]

    async def test():
        summary = await summarize_text(test_messages_data)
        print("Summary:", summary)
    asyncio.run(test())
