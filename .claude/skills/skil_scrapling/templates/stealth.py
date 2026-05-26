# /// script
# requires-python = ">=3.11"
# dependencies = ["scrapling[fetchers]", "pydantic"]
# ///
"""Stealth Scrapling fetch — for pages with anti-bot protection.

One-time setup before first run:
    scrapling install

Run: uv run stealth.py <url>
"""
from __future__ import annotations

import json
import os
import sys

from pydantic import BaseModel
from scrapling.fetchers import StealthyFetcher


class Item(BaseModel):
    title: str
    url: str | None = None


def scrape(url: str) -> list[Item]:
    page = StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        solve_cloudflare=True,
        block_resources=True,
        proxy=os.environ.get("SCRAPING_PROXY") or None,
        timeout=60,
    )
    if page.status_code != 200:
        raise RuntimeError(f"HTTP {page.status_code} for {url}")

    out: list[Item] = []
    for el in page.css(".item"):
        title = el.css("h2::text").get()
        if not title:
            continue
        out.append(Item(title=title.strip(), url=el.css("a::attr(href)").get()))
    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/"
    print(json.dumps([i.model_dump() for i in scrape(target)], indent=2))
