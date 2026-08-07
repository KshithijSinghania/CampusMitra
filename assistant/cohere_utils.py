import time
import cohere
from django.conf import settings


def chat_with_retry(messages, temperature=0, max_retries=3):
    co = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

    for attempt in range(max_retries):
        try:
            return co.chat(
                model="command-a-03-2025",
                messages=messages,
                temperature=temperature,
            )
        except Exception as e:
            if "429" in str(e) or "TooManyRequestsError" in type(e).__name__:
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
            raise