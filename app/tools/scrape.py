"""Page fetcher with graceful degradation: try a plain HTTP GET first (fast, free),
fall back to Playwright for JS-rendered pages. Buyers care about getting a report,
not about which tool failed, so every failure path returns a usable (possibly partial) result."""
from bs4 import BeautifulSoup
import requests

FETCH_TOOL_SCHEMA = {
    "name": "fetch_page",
    "description": "Fetch and extract the main readable text content of a webpage by URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch"},
        },
        "required": ["url"],
    },
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketAnalystBot/1.0)"}
MAX_CHARS = 8000


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:MAX_CHARS]


def fetch_page(url: str) -> dict:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=12)
        resp.raise_for_status()
        text = _extract_text(resp.text)
        if len(text) > 200:
            return {"url": url, "text": text, "status": "ok"}
    except Exception:
        pass

    # Fallback: JS-rendered page needs a real browser
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            html = page.content()
            browser.close()
        return {"url": url, "text": _extract_text(html), "status": "ok_via_browser"}
    except Exception as e:
        return {"url": url, "text": "", "status": f"failed: {e}"}
