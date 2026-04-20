"""
Google AI Overviews & AI Mode scraper using Playwright.
These endpoints have no public API — scraping is best-effort.
Returns available=False with a clear reason when blocked.
"""
import re
import asyncio
from services.sentiment import analyze

UNAVAILABLE = {
    "available": False,
    "raw_response": "",
    "brand_mentions": {},
    "cited_urls": {},
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "error": "Google AI scraping unavailable — Playwright not installed or Google blocked the request.",
}


async def query_ai_overview(prompt: str, brands: list[dict]) -> dict:
    return await _scrape(prompt, brands, mode="overview")


async def query_ai_mode(prompt: str, brands: list[dict]) -> dict:
    return await _scrape(prompt, brands, mode="ai_mode")


async def _scrape(prompt: str, brands: list[dict], mode: str) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {**UNAVAILABLE, "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    search_url = f"https://www.google.com/search?q={_encode(prompt)}&hl=en"
    if mode == "ai_mode":
        search_url += "&udm=50"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await context.new_page()
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Try to extract AI Overview block
            text = ""
            selectors = [
                "[data-attrid='wa:/description']",
                ".ILfuVd",
                "[jsname='yEVEwb']",
                ".wDYxhc",
                "div[data-ved] .hgKElc",
            ]
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        text = await el.inner_text()
                        if text.strip():
                            break
                except Exception:
                    continue

            if not text.strip():
                await browser.close()
                return {**UNAVAILABLE, "error": "Google AI block not found — may not be triggered for this query or layout changed."}

            # Extract citation links
            cited_links = []
            try:
                link_els = await page.query_selector_all(".ILfuVd a, .hgKElc a, [data-attrid] a")
                for el in link_els:
                    href = await el.get_attribute("href")
                    if href and href.startswith("http"):
                        cited_links.append(href)
            except Exception:
                pass

            await browser.close()
            return _parse(text, brands, cited_links)

    except Exception as e:
        return {**UNAVAILABLE, "error": f"Scraping error: {str(e)}"}


def _encode(text: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(text)


def _parse(text: str, brands: list[dict], page_links: list[str] = None) -> dict:
    mentions = {}
    cited = {}
    all_urls = list(page_links or []) + re.findall(r'https?://[^\s\)\]"\']+', text)
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
