#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.26.0",
#     "beautifulsoup4>=4.12.0",
#     "markdownify>=0.11.0",
#     "lxml>=5.0.0",
#     "playwright>=1.40.0",
# ]
# ///
"""
Fetch API documentation using sitemap-first approach.

Usage:
    uv run fetch_docs.py --url "https://developer.fortnox.se" --service fortnox
    uv run fetch_docs.py --sitemap "https://api.example.com/sitemap.xml" --service example
    uv run fetch_docs.py --url "https://docs.example.com" --service example --filter "/api/"
    uv run fetch_docs.py --url "https://docs.example.com" --service example --playwright
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md


# =============================================================================
# HTTP Client
# =============================================================================

def get_client() -> httpx.Client:
    """Create configured HTTP client."""
    return httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )


def fetch_url(client: httpx.Client, url: str) -> str | None:
    """Fetch URL content."""
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}")
        return None


# =============================================================================
# Sitemap Discovery & Parsing
# =============================================================================

def discover_sitemap(client: httpx.Client, base_url: str) -> str | None:
    """Try to find sitemap URL from robots.txt or common locations."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap/sitemap.xml",
        f"{base}/docs/sitemap.xml",
        f"{base}/api/sitemap.xml",
    ]

    # Try robots.txt first
    robots_url = f"{base}/robots.txt"
    try:
        response = client.get(robots_url)
        if response.status_code == 200:
            for line in response.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    print(f"Found sitemap in robots.txt: {sitemap_url}")
                    return sitemap_url
    except Exception:
        pass

    # Try common locations
    for sitemap_url in sitemap_urls:
        try:
            response = client.head(sitemap_url)
            if response.status_code == 200:
                print(f"Found sitemap at: {sitemap_url}")
                return sitemap_url
        except Exception:
            continue

    return None


def parse_sitemap(client: httpx.Client, sitemap_url: str) -> list[str]:
    """Parse sitemap and return list of URLs."""
    urls = []

    content = fetch_url(client, sitemap_url)
    if not content:
        return urls

    try:
        root = ElementTree.fromstring(content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Check if it's a sitemap index
        sitemaps = root.findall(".//sm:sitemap/sm:loc", ns)
        if sitemaps:
            print(f"Found sitemap index with {len(sitemaps)} sitemaps")
            for sitemap in sitemaps:
                child_urls = parse_sitemap(client, sitemap.text)
                urls.extend(child_urls)
        else:
            locs = root.findall(".//sm:url/sm:loc", ns)
            urls = [loc.text for loc in locs if loc.text]
            print(f"Found {len(urls)} URLs in sitemap")

    except ElementTree.ParseError:
        soup = BeautifulSoup(content, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("http"):
                urls.append(href)

    return urls


def filter_urls(urls: list[str], filter_pattern: str | None, base_url: str) -> list[str]:
    """Filter URLs to only include relevant documentation pages."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    filtered = []
    for url in urls:
        parsed = urlparse(url)

        if parsed.netloc != base_domain:
            continue

        skip_patterns = [
            r'/blog/', r'/news/', r'/press/', r'/careers/',
            r'/about/', r'/contact/', r'/privacy/', r'/terms/',
            r'/login/', r'/signup/', r'/account/',
            r'\.(pdf|zip|png|jpg|jpeg|gif|svg|css|js)$',
        ]
        if any(re.search(p, url, re.I) for p in skip_patterns):
            continue

        if filter_pattern and filter_pattern not in url:
            continue

        filtered.append(url)

    return filtered


# =============================================================================
# Content Extraction
# =============================================================================

def html_to_markdown(html: str, url: str) -> str:
    """Convert HTML to clean markdown."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(class_=re.compile(r"content|docs|documentation|api-doc", re.I)) or
        soup.find("div", class_=re.compile(r"markdown|content|docs", re.I)) or
        soup.body or
        soup
    )

    title = soup.find("title")
    title_text = title.get_text().strip() if title else urlparse(url).path

    markdown = md(str(main_content), heading_style="ATX", bullets="-")
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = f"# {title_text}\n\nSource: {url}\n\n---\n\n{markdown.strip()}"

    return markdown


def is_content_empty(markdown: str) -> bool:
    """Check if extracted markdown has meaningful content (not a JS-rendered shell)."""
    stripped = re.sub(r'(Source:.*|^#.*|^---$|\s)', '', markdown, flags=re.MULTILINE)
    return len(stripped) < 150


def url_to_filename(url: str, base_url: str) -> str:
    """Convert URL to safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return "index"

    filename = path.replace("/", "_")
    filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
    filename = filename[:100]

    return filename or "page"


def save_pages(all_content: list[str], service: str, output_dir: Path, service_dir: Path) -> None:
    """Save combined documentation file."""
    if all_content:
        combined_path = output_dir / service / "full-documentation.md"
        combined_path.write_text("\n\n---\n\n".join(all_content))
        print(f"\nSaved combined docs: {combined_path}")


# =============================================================================
# Crawlers
# =============================================================================

def crawl_with_httpx(client: httpx.Client, urls: list[str], service: str, output_dir: Path) -> None:
    """Crawl URLs using httpx (for static/SSR sites)."""
    service_dir = output_dir / service / "pages"
    service_dir.mkdir(parents=True, exist_ok=True)

    all_content = []
    js_detected = False

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Fetching: {url}")

        html = fetch_url(client, url)
        if not html:
            continue

        markdown = html_to_markdown(html, url)

        if is_content_empty(markdown):
            if not js_detected:
                js_detected = True
                print(f"\n  ⚠ JS-rendered site detected — content is empty.")
                print(f"  Re-run with --playwright for proper rendering:\n")
                print(f"    uv run fetch_docs.py --url <URL> --service {service} --playwright\n")
            continue

        all_content.append(markdown)

        filename = url_to_filename(url, urls[0])
        filepath = service_dir / f"{filename}.md"
        filepath.write_text(markdown)
        print(f"  Saved: {filepath.name}")

        time.sleep(0.3)

    save_pages(all_content, service, output_dir, service_dir)


async def crawl_with_playwright(urls: list[str], service: str, output_dir: Path) -> None:
    """Crawl JS-rendered pages using Playwright (single browser instance, no rate limits)."""
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

    service_dir = output_dir / service / "pages"
    service_dir.mkdir(parents=True, exist_ok=True)

    all_content = []

    async with async_playwright() as p:
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        try:
            browser = await p.chromium.launch(headless=True, args=launch_args)
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "chromium" in str(e).lower():
                print("Playwright browser not installed. Installing chromium...")
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
                    check=True
                )
                browser = await p.chromium.launch(headless=True, args=launch_args)
            else:
                raise

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            # Mask automation signals
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        # Override navigator.webdriver to avoid bot detection
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Rendering: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # Wait a bit extra for dynamic content
                await page.wait_for_timeout(500)
                html = await page.content()
            except PlaywrightTimeoutError:
                # On timeout, still try to get whatever content rendered
                try:
                    html = await page.content()
                except Exception:
                    print(f"  Failed (timeout)")
                    continue
            except Exception as e:
                print(f"  Failed: {e}")
                continue

            markdown = html_to_markdown(html, url)

            if is_content_empty(markdown):
                print(f"  Skipping (no content)")
                continue

            all_content.append(markdown)

            filename = url_to_filename(url, urls[0])
            filepath = service_dir / f"{filename}.md"
            filepath.write_text(markdown)
            print(f"  Saved: {filepath.name}")

        await browser.close()

    save_pages(all_content, service, output_dir, service_dir)


async def crawl_with_crawl4ai(urls: list[str], service: str, output_dir: Path) -> None:
    """Crawl URLs using Crawl4AI for JavaScript-heavy sites."""
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        print("Crawl4AI not installed. Run: uv pip install crawl4ai")
        sys.exit(1)

    service_dir = output_dir / service / "pages"
    service_dir.mkdir(parents=True, exist_ok=True)

    all_content = []

    async with AsyncWebCrawler(verbose=False) as crawler:
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Crawling: {url}")
            result = await crawler.arun(url=url)

            if result.success and result.markdown:
                filename = url_to_filename(url, urls[0])
                filepath = service_dir / f"{filename}.md"
                content = f"# {url}\n\n{result.markdown}"
                filepath.write_text(content)
                all_content.append(content)
                print(f"  Saved: {filepath.name}")
            else:
                print(f"  Failed: {result.error_message}")

            await asyncio.sleep(0.5)

    save_pages(all_content, service, output_dir, service_dir)


# =============================================================================
# Postman Collection Converter
# =============================================================================

def postman_request_to_markdown(item: dict) -> str:
    """Convert a single Postman request item to markdown."""
    req = item.get("request", {})
    if not isinstance(req, dict):
        return ""

    name = item.get("name", "Unnamed")
    method = req.get("method", "GET")
    url = req.get("url", "")
    if isinstance(url, dict):
        url = url.get("raw", "")
    # Clean up token/variable placeholders for readability
    url = re.sub(r'\?token=\{\{.*?\}\}', '', url)
    url = re.sub(r'&token=\{\{.*?\}\}', '', url)

    description = req.get("description", "")
    headers = req.get("header", [])
    body = req.get("body", {})

    lines = [f"### {method} {name}", ""]

    lines.append(f"**`{method} {url}`**")
    lines.append("")

    if description:
        lines.append(description.strip())
        lines.append("")

    # Headers (skip Content-Type boilerplate)
    non_trivial_headers = [h for h in headers if h.get("key") not in ("Content-Type",)]
    if non_trivial_headers:
        lines.append("**Headers:**")
        for h in non_trivial_headers:
            lines.append(f"- `{h['key']}: {h.get('value', '')}`")
        lines.append("")

    # Request body
    if body and body.get("mode") == "raw" and body.get("raw"):
        raw = body["raw"].strip()
        if raw:
            lines.append("**Request Body:**")
            lines.append("```json")
            lines.append(raw)
            lines.append("```")
            lines.append("")

    # Response examples (first one only)
    responses = item.get("response", [])
    if responses:
        resp = responses[0]
        status = resp.get("code", "")
        resp_body = resp.get("body", "")
        if resp_body and resp_body.strip():
            try:
                # Pretty-print JSON
                parsed = json.loads(resp_body)
                resp_body = json.dumps(parsed, indent=2)
            except Exception:
                pass
            lines.append(f"**Response ({status}):**")
            lines.append("```json")
            lines.append(resp_body.strip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def postman_to_markdown(collection: dict) -> tuple[str, dict[str, str]]:
    """
    Convert a Postman collection to markdown.
    Returns (full_doc, {folder_name: folder_markdown}).
    """
    import json as _json

    info = collection.get("info", {})
    name = info.get("name", "API Documentation")
    description_html = info.get("description", "")

    # Convert HTML description to markdown
    overview_md = md(description_html, heading_style="ATX", bullets="-") if description_html else ""
    overview_md = re.sub(r'\n{3,}', '\n\n', overview_md)

    all_sections = []
    folder_docs = {}

    # Overview section
    if overview_md.strip():
        overview_section = f"# {name}\n\n{overview_md.strip()}"
        all_sections.append(overview_section)
        folder_docs["_overview"] = overview_section

    # Process each folder
    for folder in collection.get("item", []):
        folder_name = folder.get("name", "Unnamed")
        folder_description = folder.get("description", "")
        items = folder.get("item", [])

        section_lines = [f"## {folder_name}", ""]
        if folder_description:
            # Convert HTML descriptions to markdown
            if "<" in folder_description:
                folder_description = md(folder_description, heading_style="ATX", bullets="-")
                folder_description = re.sub(r'\n{3,}', '\n\n', folder_description)
            section_lines.append(folder_description.strip())
            section_lines.append("")

        for item in items:
            # Handle nested folders (depth 2)
            if item.get("item"):
                sub_name = item.get("name", "")
                section_lines.append(f"### {sub_name}")
                section_lines.append("")
                for sub_item in item["item"]:
                    req_md = postman_request_to_markdown(sub_item)
                    if req_md:
                        # Shift heading level for nested
                        req_md = req_md.replace("### ", "#### ", 1)
                        section_lines.append(req_md)
            else:
                req_md = postman_request_to_markdown(item)
                if req_md:
                    section_lines.append(req_md)

        section = "\n".join(section_lines)
        all_sections.append(section)
        folder_docs[folder_name] = section

    full_doc = "\n\n---\n\n".join(all_sections)
    return full_doc, folder_docs


def fetch_postman_collection(collection_url: str, service: str, output_dir: Path) -> None:
    """Fetch and convert a Postman collection to markdown docs."""
    import json as _json

    print(f"Fetching Postman collection: {collection_url}")
    try:
        response = httpx.get(collection_url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        collection = response.json()
    except Exception as e:
        print(f"ERROR: Failed to fetch collection: {e}")
        sys.exit(1)

    info = collection.get("info", {})
    total_folders = len(collection.get("item", []))
    total_requests = sum(
        len([x for x in f.get("item", []) if x.get("request") or x.get("item")])
        for f in collection.get("item", [])
    )
    print(f"Collection: {info.get('name', '?')} — {total_folders} folders, ~{total_requests} requests")
    print("-" * 50)

    full_doc, folder_docs = postman_to_markdown(collection)

    # Save output
    service_dir = output_dir / service / "pages"
    service_dir.mkdir(parents=True, exist_ok=True)

    for folder_name, content in folder_docs.items():
        filename = re.sub(r'[^a-zA-Z0-9_-]', '_', folder_name.lower())[:80]
        filepath = service_dir / f"{filename}.md"
        filepath.write_text(content)
        print(f"  Saved: {filepath.name}")

    combined_path = output_dir / service / "full-documentation.md"
    combined_path.write_text(full_doc)
    print(f"\nSaved combined docs: {combined_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fetch API documentation via sitemap or Postman collection")
    parser.add_argument("--url", help="Base URL (will discover sitemap)")
    parser.add_argument("--sitemap", help="Direct sitemap URL")
    parser.add_argument("--postman-collection", help="Postman collection JSON URL (for Postman-published docs)")
    parser.add_argument("--service", required=True, help="Service name (e.g., fortnox)")
    parser.add_argument("--output", default="api-docs", help="Output directory")
    parser.add_argument("--filter", help="Filter URLs containing this pattern (e.g., /api/)")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright for JS-rendered sites (recommended for SPAs)")
    parser.add_argument("--crawl4ai", action="store_true", help="Use Crawl4AI for JS-heavy sites")
    parser.add_argument("--limit", type=int, default=50, help="Max pages to fetch (default: 50)")

    args = parser.parse_args()

    output_dir = Path(args.output)

    print(f"Service: {args.service}")
    print(f"Output: {output_dir / args.service}")

    # Postman collection mode — completely different flow
    if args.postman_collection:
        print(f"Mode: Postman Collection")
        print("-" * 50)
        fetch_postman_collection(args.postman_collection, args.service, output_dir)
        print("-" * 50)
        print("Done! Next steps:")
        print(f"1. Review docs in {output_dir / args.service}/")
        print("2. Run api-boilerplate skill to generate client code")
        return

    if not args.url and not args.sitemap:
        print("ERROR: Must provide --url, --sitemap, or --postman-collection")
        sys.exit(1)

    if args.playwright:
        print(f"Mode: Playwright (headless browser)")
    elif args.crawl4ai:
        print(f"Mode: Crawl4AI")
    else:
        print(f"Mode: httpx (static/SSR — use --playwright for JS-rendered sites)")
    print("-" * 50)

    with get_client() as client:
        # Get sitemap URL
        sitemap_url = args.sitemap
        if not sitemap_url and args.url:
            print(f"Discovering sitemap for {args.url}...")
            sitemap_url = discover_sitemap(client, args.url)

        if not sitemap_url:
            print("No sitemap found. Fetching single page...")
            urls = [args.url]
        else:
            print(f"Parsing sitemap: {sitemap_url}")
            urls = parse_sitemap(client, sitemap_url)

        # Filter URLs
        if args.filter or args.url:
            base = args.url or urlparse(sitemap_url).scheme + "://" + urlparse(sitemap_url).netloc
            urls = filter_urls(urls, args.filter, base)

        print(f"Found {len(urls)} documentation URLs")

        if len(urls) > args.limit:
            print(f"Limiting to {args.limit} pages (use --limit to change)")
            urls = urls[:args.limit]

        if not urls:
            print("No URLs to fetch!")
            sys.exit(1)

        print("-" * 50)

        # Crawl
        if args.playwright:
            asyncio.run(crawl_with_playwright(urls, args.service, output_dir))
        elif args.crawl4ai:
            asyncio.run(crawl_with_crawl4ai(urls, args.service, output_dir))
        else:
            crawl_with_httpx(client, urls, args.service, output_dir)

    print("-" * 50)
    print("Done! Next steps:")
    print(f"1. Review docs in {output_dir / args.service}/")
    print("2. Run api-boilerplate skill to generate client code")


if __name__ == "__main__":
    main()
