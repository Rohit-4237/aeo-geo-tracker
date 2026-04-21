"""Gemini REST API service — synchronous, Vercel-compatible."""
import re

import httpx

from services.sentiment import analyze

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/gemini-2.0-flash-lite:generateContent"
)


def query(prompt: str, brands: list[dict], api_key: str) -> dict:
    url = f"{GEMINI_URL}?key={api_key}"
    payload = {
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are an AI assistant specialising in the Indian market. "
                    "Answer every question strictly from an Indian perspective — "
                    "focus on Indian consumers, Indian brands and competitors, "
                    "pricing in Indian Rupees (INR), regulations under Indian law, "
                    "and regional availability across India. If asked to compare or "
                    "recommend products/services, only consider options available "
                    "and relevant in India."
                )
            }]
        },
        "contents": [{"parts": [{"text": prompt}]}],
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                err = resp.json()
                msg = err.get("error", {}).get("message", resp.text)
                return _unavailable(f"Gemini API error {resp.status_code}: {msg}")
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return _parse(text, brands)
    except Exception as exc:
        return _unavailable(str(exc))


def _unavailable(error: str) -> dict:
    return {
        "available": False,
        "error": error,
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
        urls = re.findall(r'https?://[^\s\)\]"\'<>]+', text)
        cited[name] = list(set(u for u in urls if domain in u.lower()))
    s = analyze(text)
    return {
        "available": True,
        "raw_response": text,
        "brand_mentions": mentions,
        "cited_urls": cited,
        "sentiment": s["label"],
        "sentiment_score": s["score"],
    }
