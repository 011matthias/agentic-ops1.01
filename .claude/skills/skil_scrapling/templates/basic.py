# /// script
# requires-python = ">=3.11"
# dependencies = ["scrapling", "pydantic"]
# ///
"""Basic Scrapling fetch — static HTML, no anti-bot.

Run: uv run basic.py <url>
"""
from __future__ import annotations

import json
import sys

from pydantic import BaseModel
from scrapling.fetchers import Fetcher


class Item(BaseModel):
    title: str
    url: str | None = None


SELECTORS = {
    "items": ".item",
    "title": "h2::text",
    "link": "a::attr(href)",
}


def scrape(url: str) -> list[Item]:
    page = Fetcher.get(url, timeout=20, impersonate="chrome")
    if page.status_code != 200:
        raise RuntimeError(f"HTTP {page.status_code} for {url}")

    out: list[Item] = []
    for el in page.css(SELECTORS["items"]):
        title = el.css(SELECTORS["title"]).get()
        if not title:
            continue
        out.append(Item(title=title.strip(), url=el.css(SELECTORS["link"]).get()))
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
    print(json.dumps([i.model_dump() for i in scrape(target)], indent=2))
