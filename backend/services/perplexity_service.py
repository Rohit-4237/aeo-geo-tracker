import re
import httpx
from services.sentiment import analyze

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


async def query(prompt: str, brands: list[dict], api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3-sonar-small-32k-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(PERPLEXITY_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"] or ""
            citations = data.get("citations", [])
            return _parse(text, brands, citations)
    except Exception as e:
        return {"available": False, "error": str(e), "raw_response": "", "brand_mentions": {}, "cited_urls": {}, "sentiment": "neutral", "sentiment_score": 0.0}


def _parse(text: str, brands: list[dict], api_citations: list[str] = None) -> dict:
    mentions = {}
    cited = {}
    all_urls = list(api_citations or []) + re.findall(r'https?://[^\s\)\]"\']+', text)
    for b in brands:
        name = b["name"]
        url = b["url"].rstrip("/").lower()
        domain = re.sub(r"^https?://(www\.)?", "", url)
        count = len(re.findall(re.escape(name), text, re.IGNORECASE))
        mentions[name] = count
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
