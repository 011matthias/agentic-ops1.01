# /// script
# requires-python = ">=3.11"
# dependencies = ["scrapling[fetchers]"]
# ///
"""Spider Scrapling crawl — multi-page with link following.

Run: uv run spider.py
"""
from __future__ import annotations

import asyncio
import json

from scrapling.spiders import Response, Spider


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    custom_settings = {
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 0.5,
    }

    async def parse(self, response: Response):
        for quote in response.css(".quote"):
            yield {
                "text": quote.css(".text::text").get(),
                "author": quote.css(".author::text").get(),
                "tags": quote.css(".tag::text").getall(),
            }
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)


async def main() -> None:
    results: list[dict] = []
    async for item in QuotesSpider().run():
        results.append(item)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
