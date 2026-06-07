# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6"]
# ///
"""AI-visibility probe: on-site AEO audit + AI-engine citation tracking.

Two independent halves:

  1. audit_site()       -- fetches robots.txt / llms.txt / pricing / sitemap /
                           homepage and grades the on-site AEO surface. Needs no
                           API keys; runs anywhere.
  2. probe_citations()  -- asks AI engines the target queries and records whether
                           the domain appears in the cited sources. Needs an engine
                           key (PERPLEXITY_API_KEY preferred; OPENAI_API_KEY for the
                           web-search engine). Skips cleanly when no key is set.

Run monthly per target; diff the JSON to track movement. This is the dogfood for
the AI-visibility service: the audit is the deliverable, the citation probe is the
proof.

Usage:
  uv run ai_visibility_probe.py --target targets/unpauseai.yaml --out reports/
  uv run ai_visibility_probe.py --target targets/unpauseai.yaml --audit-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.robotparser
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import httpx
import yaml

UA = "Mozilla/5.0 (compatible; UnpauseAI-AIVisibilityProbe/1.0; +https://unpauseai.com)"
TIMEOUT = httpx.Timeout(20.0)

# Search-and-cite crawlers. Blocking any of these means that engine cannot cite you.
AI_CRAWLERS = [
    "GPTBot",          # OpenAI / ChatGPT
    "ChatGPT-User",    # ChatGPT browse
    "PerplexityBot",   # Perplexity
    "ClaudeBot",       # Anthropic / Claude
    "anthropic-ai",    # Anthropic (legacy)
    "Google-Extended", # Gemini + AI Overviews training
    "Bingbot",         # Copilot via Bing
]


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN | INFO
    detail: str


@dataclass
class AuditResult:
    domain: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str) -> None:
        self.checks.append(Check(name, status, detail))

    def score(self) -> tuple[int, int]:
        graded = [c for c in self.checks if c.status in ("PASS", "FAIL", "WARN")]
        passed = sum(1 for c in graded if c.status == "PASS")
        return passed, len(graded)


def _get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        return client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:  # network / DNS / timeout
        print(f"  ! {url} -> {exc}", file=sys.stderr)
        return None


def audit_site(domain: str) -> AuditResult:
    base = f"https://{domain}"
    res = AuditResult(domain=domain)
    with httpx.Client(headers={"User-Agent": UA}, timeout=TIMEOUT) as client:
        # --- robots.txt + AI crawler access ---
        robots = _get(client, f"{base}/robots.txt")
        if robots is None or robots.status_code != 200:
            res.add("robots.txt", "WARN", "no robots.txt (all crawlers allowed by default)")
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(robots.text.splitlines())
            blocked = [bot for bot in AI_CRAWLERS if not rp.can_fetch(bot, f"{base}/")]
            if blocked:
                res.add("ai-crawler-access", "FAIL",
                        f"root blocked for: {', '.join(blocked)} -- those engines cannot cite you")
            else:
                res.add("ai-crawler-access", "PASS", "all AI crawlers may fetch the site root")
            if "sitemap" in robots.text.lower():
                res.add("robots-sitemap-ref", "PASS", "robots.txt references a sitemap")
            else:
                res.add("robots-sitemap-ref", "WARN", "robots.txt does not reference a sitemap")

        # --- sitemap.xml ---
        sitemap = _get(client, f"{base}/sitemap.xml")
        if sitemap is not None and sitemap.status_code == 200 and "<urlset" in sitemap.text:
            n = sitemap.text.count("<loc>")
            res.add("sitemap.xml", "PASS", f"present, {n} URLs")
        else:
            res.add("sitemap.xml", "FAIL", "absent -- engines have no crawl map")

        # --- llms.txt ---
        llms = _get(client, f"{base}/llms.txt")
        if llms is not None and llms.status_code == 200 and llms.text.strip():
            res.add("llms.txt", "PASS", f"present ({len(llms.text)} bytes)")
        else:
            res.add("llms.txt", "WARN", "absent -- no AI-context file (helps non-Google engines)")

        # --- pricing.md / pricing.txt ---
        for path in ("/pricing.md", "/pricing.txt"):
            pr = _get(client, f"{base}{path}")
            if pr is not None and pr.status_code == 200 and pr.text.strip():
                res.add("machine-readable-pricing", "PASS", f"{path} present")
                break
        else:
            res.add("machine-readable-pricing", "WARN",
                    "no /pricing.md|txt -- buying agents can't parse pricing")

        # --- homepage structure ---
        home = _get(client, base)
        if home is None or home.status_code != 200:
            res.add("homepage", "FAIL", f"homepage not reachable ({home.status_code if home else 'no response'})")
        else:
            html = home.text
            ld = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                            html, re.DOTALL | re.IGNORECASE)
            if ld:
                types: list[str] = []
                for block in ld:
                    types += re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
                res.add("structured-data", "PASS",
                        f"{len(ld)} JSON-LD block(s): {', '.join(sorted(set(types))) or 'untyped'}")
            else:
                res.add("structured-data", "FAIL",
                        "no JSON-LD -- no Organization/FAQ/Article schema for entity recognition")

            if re.search(r'<meta[^>]+name=["\']description["\']', html, re.IGNORECASE):
                res.add("meta-description", "PASS", "present")
            else:
                res.add("meta-description", "WARN", "no meta description in homepage head")

            if re.search(r'(last updated|updated on|aria-label=["\'][^"\']*updated)', html, re.IGNORECASE):
                res.add("freshness-signal", "PASS", "a last-updated signal is present")
            else:
                res.add("freshness-signal", "WARN",
                        "no visible last-updated date (engines weight recency)")
    return res


# --------------------------------------------------------------------------- #
# citation probe
# --------------------------------------------------------------------------- #
@dataclass
class ProbeRow:
    engine: str
    query: str
    cited: bool
    sources: list[str] = field(default_factory=list)
    note: str = ""


def _domain_in(domain: str, url: str) -> bool:
    return domain.lower().lstrip("www.") in url.lower()


def probe_perplexity(queries: list[str], domain: str) -> list[ProbeRow]:
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        return [ProbeRow("perplexity", "*", False, note="PERPLEXITY_API_KEY not set -- skipped")]
    rows: list[ProbeRow] = []
    with httpx.Client(timeout=httpx.Timeout(60.0),
                      headers={"Authorization": f"Bearer {key}"}) as client:
        for q in queries:
            try:
                r = client.post("https://api.perplexity.ai/chat/completions", json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": q}],
                })
                r.raise_for_status()
                data = r.json()
                cites = data.get("citations") or data.get("search_results") or []
                urls = [c if isinstance(c, str) else c.get("url", "") for c in cites]
                rows.append(ProbeRow("perplexity", q,
                                     any(_domain_in(domain, u) for u in urls), urls))
            except httpx.HTTPError as exc:
                rows.append(ProbeRow("perplexity", q, False, note=f"error: {exc}"))
    return rows


def probe_openai(queries: list[str], domain: str) -> list[ProbeRow]:
    key = os.environ.get("AI_VISIBILITY_OPENAI_KEY")  # dedicated key, NOT a client's
    if not key:
        return [ProbeRow("openai-search", "*", False,
                         note="AI_VISIBILITY_OPENAI_KEY not set -- skipped (do not reuse a client key)")]
    rows: list[ProbeRow] = []
    with httpx.Client(timeout=httpx.Timeout(90.0),
                      headers={"Authorization": f"Bearer {key}"}) as client:
        for q in queries:
            try:
                r = client.post("https://api.openai.com/v1/responses", json={
                    "model": "gpt-4o",
                    "tools": [{"type": "web_search_preview"}],
                    "input": q,
                })
                r.raise_for_status()
                blob = json.dumps(r.json())
                urls = re.findall(r'https?://[^\s"\\]+', blob)
                rows.append(ProbeRow("openai-search", q,
                                     any(_domain_in(domain, u) for u in urls),
                                     sorted(set(u for u in urls if _domain_in(domain, u)))))
            except httpx.HTTPError as exc:
                rows.append(ProbeRow("openai-search", q, False, note=f"error: {exc}"))
    return rows


def probe_citations(queries: list[str], domain: str, engines: list[str]) -> list[ProbeRow]:
    rows: list[ProbeRow] = []
    if "perplexity" in engines:
        rows += probe_perplexity(queries, domain)
    if "openai" in engines:
        rows += probe_openai(queries, domain)
    return rows


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
_ICON = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO"}


def render_report(audit: AuditResult, probe: list[ProbeRow], cfg: dict[str, Any], date: str) -> str:
    passed, total = audit.score()
    brand = cfg.get("brand", audit.domain)
    out = [f"# AI-visibility baseline: {brand} ({audit.domain})", ""]
    out.append(f"Run date: {date}  ")
    out.append(f"On-site AEO score: {passed}/{total} graded checks passed")
    out.append("")
    out.append("## On-site audit")
    out.append("")
    out.append("| Check | Status | Detail |")
    out.append("|---|---|---|")
    for c in audit.checks:
        out.append(f"| {c.name} | {_ICON.get(c.status, c.status)} | {c.detail} |")
    out.append("")
    out.append("## Citation probe")
    out.append("")
    live = [r for r in probe if r.query != "*"]
    if not live:
        out.append("No live engine key set. Citation probe skipped; activate by setting "
                   "`PERPLEXITY_API_KEY` (cleanest, returns source URLs) or "
                   "`AI_VISIBILITY_OPENAI_KEY`.")
        for r in probe:
            out.append(f"- {r.engine}: {r.note}")
    else:
        out.append("| Engine | Query | Cited? | Domain sources |")
        out.append("|---|---|---|---|")
        for r in live:
            mark = "YES" if r.cited else "no"
            src = ", ".join(s for s in r.sources if _domain_in(audit.domain, s)) or "-"
            out.append(f"| {r.engine} | {r.query} | {mark} | {src} |")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="AI-visibility probe (AEO audit + citation tracking)")
    ap.add_argument("--target", required=True, help="YAML target config")
    ap.add_argument("--out", help="output directory for the markdown + json report")
    ap.add_argument("--date", default="", help="run date YYYY-MM-DD (stamped into the report)")
    ap.add_argument("--audit-only", action="store_true", help="skip the citation probe")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.target).read_text(encoding="utf-8"))
    domain = cfg["domain"]
    queries = cfg.get("queries", [])
    engines = cfg.get("engines", ["perplexity"])
    date = args.date or "undated"

    print(f"Auditing {domain} ...", file=sys.stderr)
    audit = audit_site(domain)
    probe: list[ProbeRow] = []
    if not args.audit_only:
        print(f"Probing {len(queries)} queries across {engines} ...", file=sys.stderr)
        probe = probe_citations(queries, domain, engines)

    report = render_report(audit, probe, cfg, date)
    if args.out:
        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        slug = cfg.get("brand", domain).lower().replace(" ", "-")
        (outdir / f"baseline-{slug}-{date}.md").write_text(report, encoding="utf-8")
        (outdir / f"baseline-{slug}-{date}.json").write_text(
            json.dumps({"audit": asdict(audit), "probe": [asdict(r) for r in probe]},
                       indent=2), encoding="utf-8")
        print(f"Wrote report to {outdir}/baseline-{slug}-{date}.md", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
