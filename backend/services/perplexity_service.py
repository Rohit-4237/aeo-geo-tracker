"""Perplexity AI service — synchronous, Vercel-compatible."""
import re

import httpx

from services.sentiment import analyze

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


def query(prompt: str, brands: list[dict], api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
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
        "max_tokens": 1024,
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(PERPLEXITY_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"] or ""
            citations = data.get("citations", [])
            return _parse(text, brands, citations)
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


def _parse(text: str, brands: list[dict], api_citations: list[str] | None = None) -> dict:
    mentions = {}
    cited = {}
    all_urls = list(api_citations or []) + re.findall(r'https?://[^\s\)\]"\']+', text)
    for b in brands:
        name = b["name"]
        domain = re.sub(r"^https?://(www\.)?", "", b["url"].rstrip("/").lower())
        mentions[name] = len(re.findall(re.escape(name), text, re.IGNORECASE))
        cited[name] = list(set(u for u in all_urls if domain in u.lower()))
    s = analyze(text)
    return {
        "available": True,
        "raw_response": text,
        "brand_mentions": mentions,
        "cited_urls": cited,
        "sentiment": s["label"],
        "sentiment_score": s["score"],
    }
