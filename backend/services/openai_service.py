import re
from openai import AsyncOpenAI
from services.sentiment import analyze


async def query(prompt: str, brands: list[dict], api_key: str) -> dict:
    client = AsyncOpenAI(api_key=api_key)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
        return _parse(text, brands)
    except Exception as e:
        return {"available": False, "error": str(e), "raw_response": "", "brand_mentions": {}, "cited_urls": {}, "sentiment": "neutral", "sentiment_score": 0.0}


def _parse(text: str, brands: list[dict]) -> dict:
    mentions = {}
    cited = {}
    for b in brands:
        name = b["name"]
        url = b["url"].rstrip("/").lower()
        domain = re.sub(r"^https?://(www\.)?", "", url)
        count = len(re.findall(re.escape(name), text, re.IGNORECASE))
        mentions[name] = count
        urls_found = re.findall(r'https?://[^\s\)\]"\']+', text)
        cited[name] = [u for u in urls_found if domain in u.lower()]
    s = analyze(text)
    return {
        "available": True,
        "raw_response": text,
        "brand_mentions": mentions,
        "cited_urls": cited,
        "sentiment": s["label"],
        "sentiment_score": s["score"],
    }
