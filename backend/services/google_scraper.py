"""
Google AI Overviews / AI Mode — stub for the hosted (Vercel) version.

Playwright-based scraping is not available in serverless environments.
Users who want Google scraping should run the tool locally.
"""

_UNAVAILABLE = {
    "available": False,
    "raw_response": "",
    "brand_mentions": {},
    "cited_urls": {},
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "error": (
        "Google AI scraping is not supported in the hosted version. "
        "Run the tool locally (start.bat) to use Google AI Overview / AI Mode."
    ),
}


def query(prompt: str, brands: list[dict], mode: str) -> dict:  # noqa: ARG001
    """Return a graceful 'unavailable' result for both google_aio and google_aim."""
    return _UNAVAILABLE.copy()


# Keep the old function names for backward-compat with any direct callers
def query_ai_overview(prompt: str, brands: list[dict]) -> dict:
    return query(prompt, brands, "overview")


def query_ai_mode(prompt: str, brands: list[dict]) -> dict:
    return query(prompt, brands, "ai_mode")
