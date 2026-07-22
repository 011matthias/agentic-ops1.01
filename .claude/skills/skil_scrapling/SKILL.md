---
name: scrapling
description: Adaptive web scraping with the Scrapling Python library. Use when building automations that need to extract data from websites — HTML pages, dynamic JS-rendered pages, or anti-bot-protected pages (Cloudflare Turnstile, fingerprint checks). Covers fetcher selection (HTTP vs stealth vs browser), CSS/XPath parsing, async/session patterns, and the Spider framework for full crawls. Pick this skill over raw httpx+BeautifulSoup when the target page may render with JS, sit behind anti-bot protection, or change structure over time.
---

# Scrapling

Adaptive web scraping framework. Source: https://github.com/D4Vinci/Scrapling

Scrapling unifies four scraping modes under one API: fast HTTP, anti-bot stealth, full browser automation, and a Spider framework. It tracks element location across page changes (the "adaptive" part) and exposes CSS, XPath, BeautifulSoup-style, and text-search selectors on the same response object.

## When to use this skill

Use Scrapling when an automation needs to pull data from a website. Pick the fetcher by what blocks you on the target:

| Target page | Fetcher | Reason |
|-------------|---------|--------|
| Static HTML, no protection | `Fetcher` | Fastest; plain HTTP. |
| Returns 403 / captcha / Cloudflare | `StealthyFetcher` | TLS fingerprint impersonation, Turnstile bypass, DNS-over-HTTPS. |
| Data only appears after JS runs | `DynamicFetcher` | Headless browser; waits for selectors. |
| Need to crawl many URLs concurrently with pause/resume | `Spider` | Spider framework with session coordination. |

Default to `Fetcher`. Escalate to `StealthyFetcher` if you see anti-bot responses. Escalate to `DynamicFetcher` only if the data is JS-rendered (confirm by viewing page source vs rendered DOM). `Spider` is for crawls with >1 page following links.

## Install

```bash
uv add scrapling                  # core
uv add "scrapling[fetchers]"      # + browsers + stealth deps
scrapling install                 # one-time: download Chromium/Firefox
```

For PEP 723 inline-dep scripts, declare `# /// script` with `scrapling` (or `scrapling[fetchers]`) and run via `uv run path/to/script.py`.

## Quick start — pick a template

Copy a template from `templates/` and adapt:

| Template | Use when |
|----------|----------|
| [basic.py](templates/basic.py) | Simple HTTP GET, parse HTML, extract fields. |
| [stealth.py](templates/stealth.py) | Page returns 403, Cloudflare, or fingerprint check. |
| [dynamic.py](templates/dynamic.py) | Data requires JS execution to appear. |
| [spider.py](templates/spider.py) | Crawl multiple pages following links. |

## Core API

### Fetcher (HTTP)

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://example.com/")
titles = page.css(".product h2::text").getall()
prices = page.css(".product .price::text").getall()
```

`Fetcher.get` / `.post` / `.put` / `.delete` all return a `Response` with parsing methods attached. Accepts `headers`, `cookies`, `proxy`, `timeout`, `impersonate="chrome"` (TLS fingerprint).

### StealthyFetcher (anti-bot)

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    "https://target.com/",
    headless=True,
    network_idle=True,
    solve_cloudflare=True,
)
```

`solve_cloudflare=True` handles Turnstile/Interstitial. Pair with `proxy=` for IP rotation. Use `block_resources=True` to skip images/fonts when you only need HTML.

### DynamicFetcher (browser)

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    "https://app.example.com/dashboard",
    headless=True,
    wait_selector=".data-loaded",
    wait_selector_state="visible",
)
```

`wait_selector` is the right knob to wait for hydration — do NOT sleep. `page_action=` accepts a callable for click/scroll/login flows before extraction.

### Async + sessions

```python
import asyncio
from scrapling.fetchers import AsyncStealthySession

async def run(urls):
    async with AsyncStealthySession(max_pages=3) as session:
        tasks = [session.fetch(u) for u in urls]
        return await asyncio.gather(*tasks)

asyncio.run(run(["https://a.com", "https://b.com"]))
```

Sessions persist cookies + auth across `.fetch()` calls. `max_pages` caps concurrent browser tabs. Always use `async with` — never leak sessions.

### Spider

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    async def parse(self, response: Response):
        for quote in response.css(".quote"):
            yield {
                "text": quote.css(".text::text").get(),
                "author": quote.css(".author::text").get(),
            }
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

Run a spider with the spider runner — see `templates/spider.py` for the full pattern including output piping and pause/resume.

## Parsing — selectors on every Response

All four selector styles work on the same `Response` (and on each child element):

```python
page.css(".item .title::text").get()         # CSS, first match
page.css(".item .title::text").getall()      # CSS, all matches
page.xpath("//div[@class='item']/text()").get()
page.find("div", class_="item")              # BeautifulSoup-style
page.find_by_text("Add to cart", tag="button")
page.css(".price").re(r"\$([\d.]+)")         # CSS + regex extract
```

Element traversal: `.parent`, `.next_sibling`, `.children`. Adaptive recovery: `.find_similar()` locates the equivalent element after a layout change.

## Patterns for agentic-ops automations

**Returning structured data to a workflow:** parse into a Pydantic model and dump to JSON. The orchestrator (n8n / Make / Trigger.dev) receives JSON via webhook or stdout.

```python
from pydantic import BaseModel
from scrapling.fetchers import Fetcher

class Product(BaseModel):
    name: str
    price: float
    url: str

def scrape(category_url: str) -> list[Product]:
    page = Fetcher.get(category_url)
    items = []
    for card in page.css(".product-card"):
        items.append(Product(
            name=card.css("h2::text").get().strip(),
            price=float(card.css(".price::text").re_first(r"[\d.]+")),
            url=card.css("a::attr(href)").get(),
        ))
    return items
```

**Test fixtures:** save real responses to `workspace/clients/{client}/context/test-fixtures/` as `.html` files; tests load the HTML directly via `scrapling.parser.Adaptor(html_string)` instead of hitting the live site. Persistent, namespaced fixtures per [rule_behaviors.md](../../rules/rule_behaviors.md).

**Anti-bot escalation log:** record which fetcher worked for which target in `context/scrape-targets.md`. Don't re-derive the right fetcher on every revisit.

## Anti-patterns

- **Don't `time.sleep()`** to wait for JS — use `wait_selector` with `DynamicFetcher`. Sleeps flake and slow tests.
- **Don't use `DynamicFetcher` when `Fetcher` works.** It's 10-50x slower. View page source (not rendered DOM) — if the data is there, plain HTTP is enough.
- **Don't catch and retry blindly on 403.** Switch to `StealthyFetcher`. Retrying the same fingerprint will keep failing.
- **Don't hardcode CSS selectors deep into ad-hoc strings.** Define them as module-level constants so adapting to a site change is one edit.
- **Don't scrape robots-disallowed paths or violate ToS.** Check `/robots.txt` and the site's terms before deploying.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `403` / Cloudflare page returned | Bot detection | Use `StealthyFetcher` with `solve_cloudflare=True`. |
| Empty `getall()` but page has content in browser | JS-rendered | Use `DynamicFetcher` with `wait_selector`. |
| `Browser not found` on first run | Browsers not downloaded | Run `scrapling install`. |
| Hangs / slow on heavy pages | Loading images/fonts | `block_resources=True` on stealth/dynamic fetchers. |
| Element selector breaks after redesign | Layout changed | Use `.find_similar()` or migrate to a more stable anchor (data attributes > class names). |

## Reference

- README: https://github.com/D4Vinci/Scrapling
- PyPI: https://pypi.org/project/scrapling/
