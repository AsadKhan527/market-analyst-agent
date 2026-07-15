"""No live web-search API is used (Brave requires a card; DuckDuckGo's scrape-friendly
endpoint actively blocks bots; Gemini's grounding tool needs billing-enabled Cloud
access this account doesn't have). Instead, the agent researches from URLs supplied in
the client config (see sample_configs/) plus a small set of predictable review-site URL
guesses built from the competitor's name — no search API, no key, no card, $0."""
from __future__ import annotations
import re

REVIEW_SITE_TEMPLATES = [
    "https://www.g2.com/products/{slug}/reviews",
    "https://www.trustpilot.com/review/{domain_guess}",
    "https://www.capterra.com/p/search/?q={name_encoded}",
]


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def guess_review_urls(competitor_name: str) -> list[str]:
    """Predictable-pattern URL guesses for common review sites. These are guesses, not
    search results — the agent's fetch_page tool already handles a failed/404 fetch
    gracefully, so a wrong guess just means less evidence for that source, not a crash."""
    slug = _slugify(competitor_name)
    return [
        f"https://www.g2.com/products/{slug}/reviews",
        f"https://www.capterra.com/p/search/?q={slug}",
    ]
