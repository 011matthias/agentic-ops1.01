---
name: api-docs-fetcher
description: Fetch API documentation from URLs and save to api-docs folder. Uses sitemap-first approach. Use when you need to download API docs for Fortnox, Upsales, or other services to feed into api-boilerplate skill.
---

# API Docs Fetcher

Fetch API documentation using a **sitemap-first approach** and save to `workspace/api-docs/{service}/` for use with the api-boilerplate skill.

## How It Works

1. Discovers sitemap from robots.txt or common locations
2. Parses sitemap to get all documentation URLs
3. Filters to relevant pages (skips blog, marketing, etc.)
4. Fetches each page and converts to markdown
5. Saves individual pages + combined documentation

## Usage

### Basic (Auto-discover sitemap)

```bash
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  --url "https://developer.fortnox.se" \
  --service fortnox
```

### Direct sitemap URL

```bash
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  --sitemap "https://docs.example.com/sitemap.xml" \
  --service example
```

### Filter to specific section

```bash
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  --url "https://developer.fortnox.se" \
  --service fortnox \
  --filter "/api/"
```

### JavaScript-rendered sites (Playwright — recommended)

Use for SPAs, Docusaurus, Next.js docs, or any site where `httpx` returns empty content.
Playwright auto-installs Chromium on first run. Reuses a single browser for all pages (fast, no rate limits).

```bash
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  --url "https://docs.example.com" \
  --service example \
  --playwright
```

### JavaScript-heavy sites (Crawl4AI — alternative)

```bash
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  --url "https://docs.example.com" \
  --service example \
  --crawl4ai
```

## Script Options

| Option | Description |
|--------|-------------|
| `--url URL` | Base URL (will auto-discover sitemap) |
| `--sitemap URL` | Direct sitemap URL |
| `--service NAME` | Service name (e.g., fortnox) |
| `--output PATH` | Output directory (default: workspace/api-docs/) |
| `--filter PATTERN` | Only fetch URLs containing pattern |
| `--playwright` | Use Playwright headless browser (best for JS-rendered sites) |
| `--crawl4ai` | Use Crawl4AI for JS-heavy sites (alternative) |
| `--limit N` | Max pages to fetch (default: 50) |

## When to Use `--playwright`

The script auto-detects JS-rendered sites and tells you to re-run with `--playwright` when content is empty.
Common cases: Docusaurus, Next.js, React-based doc sites (like Teamleader Focus, Stripe, etc.).

## Output Structure

```
workspace/api-docs/{service}/
├── full-documentation.md  # All pages combined
└── pages/                 # Individual pages
    ├── customers.md
    ├── invoices.md
    └── orders.md
```

### Postman-published collections

For APIs documented via Postman (e.g. Upsales). Fetches the full JSON collection including
auth, pagination, filtering, rate limits, and all endpoints in one request — no browser needed.

```bash
# Use = syntax when URL contains & to avoid shell splitting
uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
  '--postman-collection=https://api.upsales.com/api/collections/4421023/RW87rVf1?segregateAuth=true&versionTag=latest' \
  '--service=upsales'
```

**How to find the collection URL:** Open DevTools on the Postman-published page → Network tab → look for a request to `/api/collections/...`.

> **Note:** Always use `--flag=value` syntax (not `--flag value`) when the value contains `&` or other shell-special characters.

## Common API Documentation Sources

| Service | URL type | Command |
|---------|----------|---------|
| Fortnox | Static HTML | `uv run ... --url https://developer.fortnox.se --service fortnox` |
| Upsales | Postman collection | `uv run ... --postman-collection "https://api.upsales.com/api/collections/4421023/RW87rVf1?segregateAuth=true&versionTag=latest" --service upsales` |
| Teamleader Focus | JS/Docusaurus | `uv run ... --url https://developer.focus.teamleader.eu/docs/api --service teamleader-focus --playwright --filter /docs/api/` |

## After Fetching

1. Review docs in `workspace/api-docs/{service}/`
2. Run **api-boilerplate** skill to generate client code
3. Generated clients appear in `workspace/templates/api-clients/{service}/`
