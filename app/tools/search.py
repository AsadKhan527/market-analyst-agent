"""Brave Search API wrapper — free tier, no card required."""
from __future__ import annotations
import os
import requests

SEARCH_TOOL_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for a query. Returns titles, URLs, and snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    },
}


def web_search(query: str, count: int = 8) -> list[dict]:
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"},
        params={"q": query, "count": count},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("web", {}).get("results", [])
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("description", "")}
        for r in results
    ]
