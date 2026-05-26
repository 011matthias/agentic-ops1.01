# /// script
# requires-python = ">=3.11"
# dependencies = ["scrapling[fetchers]", "pydantic"]
# ///
"""Dynamic Scrapling fetch — for JS-rendered pages (full browser).

Use this only when the data is NOT in raw page source. Confirm by viewing
view-source: in the browser before reaching for this fetcher.

One-time setup before first run:
    scrapling install

Run: uv run dynamic.py <url>
"""
from __future__ import annotations

import json
import sys

from pydantic import BaseModel
from scrapling.fetchers import DynamicFetcher


class Item(BaseModel):
    title: str
    url: str | None = None


def scrape(url: str) -> list[Item]:
    page = DynamicFetcher.fetch(
        url,
        headless=True,
        wait_selector=".item",
        wait_selector_state="visible",
        network_idle=True,
        block_resources=True,
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
