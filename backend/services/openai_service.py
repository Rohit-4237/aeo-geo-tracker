"""OpenAI ChatGPT service — synchronous, Vercel-compatible."""
import re

from openai import OpenAI

from services.sentiment import analyze


def query(prompt: str, brands: list[dict], api_key: str) -> dict:
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant specialising in the Indian market. "
                        "Answer every question strictly from an Indian perspective — "
                        "focus on Indian consumers, Indian brands and competitors, "
                        "pricing in Indian Rupees (INR), regulations under Indian law, "
                        "and regional availability across India. If asked to compare or "
                        "recommend products/services, only consider options available "
                        "and relevant in India."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
        return _parse(text, brands)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "raw_response": "",
            "brand_mentions": {},
            "cited_urls": {},
            "sentiment": "neutral",
            "sentiment_score": 0.0,
        }


def _parse(text: str, brands: list[dict]) -> dict:
    mentions = {}
    cited = {}
    for b in brands:
        name = b["name"]
        domain = re.sub(r"^https?://(www\.)?", "", b["url"].rstrip("/").lower())
        mentions[name] = len(re.findall(re.escape(name), text, re.IGNORECASE))
        urls = re.findall(r'https?://[^\s\)\]"\']+', text)
        cited[name] = [u for u in urls if domain in u.lower()]
    s = analyze(text)
    return {
        "available": True,
        "raw_response": text,
        "brand_mentions": mentions,
        "cited_urls": cited,
        "sentiment": s["label"],
        "sentiment_score": s["score"],
    }
