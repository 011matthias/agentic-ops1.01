#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Cold-seat, read-only browser read-back of what a page actually RENDERS.

    uv run --with playwright tools/spa-readback.py URL --expect TEXT [--absent TEXT]
        [--click TEXT] [--wait-text TEXT] [--expect-url SUBSTR]
        [--login-label LABEL --login-secret-env VAR [--login-button NAME] [--env-file PATH]]
        [--local-storage KEY=VALUE] [--api-pattern /api/] [--allow-write SUBSTR]
        [--replay-api] [--max-api-seconds 45] [--require-api]
        [--timeout 60] [--settle-ms 1500] [--case-sensitive] [--screenshot PATH] [--json]

Run it with `uv run --with playwright ...` in the FOREGROUND: that spelling is
what deploy-consumer-gate.py recognizes as a browser read-back, so a deploy
marker closes on a drive that genuinely observed the page.

Why it exists. A fetch of an SPA returns the shell, so `curl` / WebFetch / a
`/healthz` 200 prove the half that was not broken (rule_behaviors,
consumer-drive sub-clause; 2026-08-24 "pooled" rendered as "Arriving"). The
browser wrappers proved unreliable here: Playwright MCP is bound to the
owner's Edge on :9222 (a warm, signed-in seat, and it hangs when a sibling
holds it) and `agent-browser open` hung on SPAs four times between 2026-09-17
and 2026-10-07. Python Playwright on the installed Chrome held every time
(feedback_agent_browser_named_sessions). The recon drives also needed the same
four guards rebuilt by hand each session (feedback_recon_drive_replay_payloads),
which is the drive helper that memory asked for.

What one run does, in order:
  1. Launches the installed Chrome headless in a FRESH context: no cookies, no
     storage, no session. That is the recipient's seat (cold-drive sub-clause).
  2. Seeds localStorage keys before any script runs (--local-storage), e.g.
     the recon first-visit hint `erc-fb-hint-seen=1`. Never deletes DOM nodes.
  3. Guards writes: every non-GET/HEAD/OPTIONS request whose URL contains
     --api-pattern is ABORTED unless it matches an --allow-write substring.
     Login options allow "/login" automatically. Aborted calls are reported.
  4. Optionally replays API GETs (--replay-api): the first response per URL is
     cached and every later identical GET is fulfilled from the copy, so a
     drive reads each heavy payload once. A single API response slower than
     --max-api-seconds trips the load brake and fails the run.
  5. Navigates, logs in if asked (press_sequentially, because fill() leaves
     React's state empty and the button disabled), clicks the named elements
     (scrolled into view first), waits for --wait-text.
  6. Reads the rendered state back: final URL, title, document.body.innerText,
     console errors, a screenshot. Then asserts every --expect is present,
     every --absent fallback ("Arriving", "Unknown", "--") is absent, the final
     URL contains --expect-url, and (with --require-api) that the page actually
     reached the backend.

Exit codes: 0 PASS, 1 FAIL (the page did not render what was claimed, or the
probe could not see it; the reasons say which), 2 environment error (browser
or secret unavailable: nothing was observed, so no claim either way).

A FAIL tagged `drive-blind` means the instrument saw nothing usable (an empty
body, the login wall still up, no API traffic): that is a statement about the
probe, never a finding that the change failed to land. Prove an instrument by
running it against a state you know first (rule_behaviors, instrument-validity
sub-clause): the same command against the pre-change build should FAIL.

Read-only by construction: the only writes it allows are the login POST and
whatever --allow-write names, and it writes one screenshot under the gitignored
.scratch/spa-readback/ unless --screenshot points elsewhere.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
# Below this many characters of rendered text the page is treated as not
# rendered (a shell, a spinner, a blank error boundary).
MIN_RENDERED_CHARS = 40


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Pure logic (unit-tested without a browser)
# ---------------------------------------------------------------------------

def is_write_method(method: str) -> bool:
    return (method or "").upper() not in SAFE_METHODS


def is_api_url(url: str, pattern: str) -> bool:
    return bool(pattern) and pattern in (url or "")


def write_allowed(url: str, allow: list[str]) -> bool:
    return any(a and a in (url or "") for a in allow)


def check_text(body: str, expect: list[str], absent: list[str],
               case_sensitive: bool = False) -> tuple[dict, list[str]]:
    """Presence of each --expect and absence of each --absent in the body."""
    hay = body if case_sensitive else (body or "").lower()

    def has(s: str) -> bool:
        return (s if case_sensitive else s.lower()) in hay

    results = {"expect": {s: has(s) for s in expect},
               "absent": {s: has(s) for s in absent}}
    reasons = [f"[missing-content] expected text not rendered: {s!r}"
               for s, ok in results["expect"].items() if not ok]
    reasons += [f"[fallback-rendered] fallback text present: {s!r}"
                for s, seen in results["absent"].items() if seen]
    return results, reasons


_MSYS_MANGLED = re.compile(r"^[A-Za-z]:[\\/].*\bGit[\\/]", re.IGNORECASE)


def msys_mangled(values: list[str]) -> list[str]:
    """Arguments Git Bash rewrote from `/api/` into `C:/Program Files/Git/api/`.

    The first live recon drive (2026-11-11) passed `--api-pattern /api/` from
    Git Bash; MSYS turned it into a Windows path, the pattern matched nothing,
    and the write guard and replay silently covered no request while the page
    logged in and rendered. Refuse such an argument instead of driving blind.
    """
    return [v for v in values if v and _MSYS_MANGLED.match(v)]


def parse_kv(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"ERROR: --local-storage expects KEY=VALUE, got {item!r}")
        k, _, v = item.partition("=")
        out[k] = v
    return out


def load_secret(env_name: str, env_file: str | None) -> str | None:
    """A secret from the environment or a KEY=VALUE file. Never printed."""
    if os.environ.get(env_name):
        return os.environ[env_name]
    if env_file and Path(env_file).is_file():
        for line in Path(env_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == env_name:
                return v.strip().strip('"').strip("'")
    return None


def blind_reasons(report: dict, require_api: bool) -> list[str]:
    """Reasons the probe could not see, kept apart from content findings so a
    blind drive is never reported as 'the change did not land'."""
    out = []
    if report.get("rendered_chars", 0) < MIN_RENDERED_CHARS:
        out.append(f"[drive-blind] page rendered {report.get('rendered_chars', 0)} "
                   "characters of text (shell, spinner or blank error boundary)")
    if report.get("login") and report["login"].get("wall_still_up"):
        out.append("[drive-blind] login form is still on screen after the login step")
    if report.get("api", {}).get("routed_total", 1) == 0:
        out.append("[drive-blind] the route guard intercepted no request at all, so the "
                   "write guard and replay were not in effect for this drive")
    if require_api and report.get("api", {}).get("requests", 0) == 0:
        out.append("[drive-blind] no request matched --api-pattern: the page never "
                   "reached the backend (wrong host pattern, or only the shell loaded)")
    return out


def verdict(report: dict, require_api: bool) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = report.get("document_status")
    if status is not None and status >= 400:
        reasons.append(f"[http] main document returned {status}")
    reasons += blind_reasons(report, require_api)
    reasons += report.get("text_reasons", [])
    for t in report.get("wait_text_missing", []):
        reasons.append(f"[missing-content] --wait-text never appeared: {t!r}")
    for c in report.get("click_missing", []):
        reasons.append(f"[click-target-missing] no element with text {c!r}")
    exp_url = report.get("expect_url")
    if exp_url and exp_url not in (report.get("final_url") or ""):
        reasons.append(f"[landing] final URL {report.get('final_url')!r} does not "
                       f"contain {exp_url!r} (the recipient did not land on it)")
    if report.get("api", {}).get("brake_tripped"):
        reasons.append(f"[load-brake] an API response took "
                       f"{report['api']['slowest_s']}s; drive stopped to spare the backend")
    return ("PASS" if not reasons else "FAIL"), reasons


# ---------------------------------------------------------------------------
# Browser drive
# ---------------------------------------------------------------------------

def _launch(p, headless: bool):
    for path in CHROME_PATHS:
        if Path(path).is_file():
            return p.chromium.launch(executable_path=path, headless=headless)
    try:
        return p.chromium.launch(channel="chrome", headless=headless)
    except Exception:
        return p.chromium.launch(headless=headless)


def drive(args) -> dict:
    try:
        from playwright.sync_api import TimeoutError as PWTimeout
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"env_error": "playwright not importable; run with `uv run --with playwright`"}

    mangled = msys_mangled([args.api_pattern, args.expect_url or "", *args.allow_write])
    if mangled:
        return {"env_error": f"argument rewritten by Git Bash path conversion: {mangled[0]!r}. "
                             "Prefix the command with MSYS_NO_PATHCONV=1 (or omit "
                             "--api-pattern; its default is /api/)."}

    secret = None
    if args.login_label:
        if not args.login_secret_env:
            return {"env_error": "--login-label needs --login-secret-env"}
        secret = load_secret(args.login_secret_env, args.env_file)
        if not secret:
            return {"env_error": f"secret {args.login_secret_env} not found in env or --env-file"}

    allow = list(args.allow_write) + (["/login"] if args.login_label else [])
    seeds = parse_kv(args.local_storage)
    timeout_ms = int(args.timeout * 1000)
    api = {"routed_total": 0, "requests": 0, "fulfilled_from_cache": 0, "aborted_writes": [],
           "allowed_writes": [], "slowest_s": 0.0, "brake_tripped": False}
    cache: dict[str, dict] = {}
    console_errors: list[str] = []
    report: dict = {"url": args.url, "expect_url": args.expect_url,
                    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}

    with sync_playwright() as p:
        try:
            browser = _launch(p, headless=not args.headed)
        except Exception as e:
            return {"env_error": f"browser launch failed: {e}"}
        # Cold seat: no storage, no cookies. Service workers are blocked because
        # Playwright's routing does not see a request a service worker answers,
        # which would let a write slip past the guard unseen.
        context = browser.new_context(service_workers="block")
        for k, v in seeds.items():
            context.add_init_script(
                f"try{{localStorage.setItem({json.dumps(k)},{json.dumps(v)})}}catch(e){{}}")

        def on_route(route):
            req = route.request
            url, method = req.url, req.method
            api["routed_total"] += 1
            if not is_api_url(url, args.api_pattern):
                return route.continue_()
            api["requests"] += 1
            if is_write_method(method):
                if write_allowed(url, allow):
                    api["allowed_writes"].append(f"{method} {url}")
                    return route.continue_()
                api["aborted_writes"].append(f"{method} {url}")
                return route.abort()
            if method != "GET" or not args.replay_api:
                return route.continue_()
            if url in cache:
                api["fulfilled_from_cache"] += 1
                c = cache[url]
                return route.fulfill(status=c["status"], headers=c["headers"], body=c["body"])
            t0 = time.monotonic()
            resp = route.fetch()
            took = round(time.monotonic() - t0, 2)
            api["slowest_s"] = max(api["slowest_s"], took)
            if took > args.max_api_seconds:
                api["brake_tripped"] = True
            body = resp.body()
            cache[url] = {"status": resp.status, "headers": resp.headers, "body": body}
            return route.fulfill(status=resp.status, headers=resp.headers, body=body)

        context.route("**/*", on_route)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.on("console", lambda m: console_errors.append(m.text[:200]) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {str(e)[:200]}"))
        seen: list[str] = []
        page.on("request", lambda r: seen.append(f"{r.method} {r.url.split('?')[0]}"))

        try:
            resp = page.goto(args.url, wait_until="domcontentloaded", timeout=timeout_ms)
            report["document_status"] = resp.status if resp else None
            page.wait_for_timeout(args.settle_ms)

            if args.login_label:
                login = {"attempted": True}
                field = page.get_by_label(args.login_label).first
                field.wait_for(timeout=timeout_ms)
                field.press_sequentially(secret, delay=20)
                page.get_by_role("button", name=args.login_button).first.click()
                try:
                    field.wait_for(state="detached", timeout=timeout_ms)
                except PWTimeout:
                    pass
                page.wait_for_timeout(args.settle_ms)
                login["wall_still_up"] = page.get_by_label(args.login_label).count() > 0
                report["login"] = login
                if args.after_login_url:
                    page.goto(args.after_login_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(args.settle_ms)

            missing_clicks = []
            for text in args.click:
                if api["brake_tripped"]:
                    break
                target = page.get_by_text(text, exact=False).first
                try:
                    target.wait_for(timeout=timeout_ms)
                    target.scroll_into_view_if_needed()
                    target.click()
                    page.wait_for_timeout(args.settle_ms)
                except PWTimeout:
                    missing_clicks.append(text)
            report["click_missing"] = missing_clicks

            waits_missing = []
            for text in args.wait_text:
                try:
                    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout_ms)
                except PWTimeout:
                    waits_missing.append(text)
            report["wait_text_missing"] = waits_missing
            page.wait_for_timeout(args.settle_ms)

            body = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
            report["final_url"] = page.url
            report["title"] = page.title()
            report["rendered_chars"] = len(body.strip())
            report["text"], report["text_reasons"] = check_text(
                body, args.expect, args.absent, args.case_sensitive)
            if args.dump_text:
                report["body_excerpt"] = body[:4000]

            shot = Path(args.screenshot) if args.screenshot else (
                repo_root() / ".scratch" / "spa-readback" /
                f"{urlparse(args.url).hostname or 'page'}-{datetime.datetime.now():%Y%m%d-%H%M%S}.png")
            shot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shot), full_page=True)
            report["screenshot"] = str(shot)
        except PWTimeout as e:
            report["drive_error"] = f"timeout: {str(e).splitlines()[0][:200]}"
            report.setdefault("rendered_chars", 0)
        finally:
            report["api"] = api
            report["requests_seen"] = len(seen)
            report["api_requests_seen"] = [s for s in seen if is_api_url(s, args.api_pattern)][:40]
            if args.dump_requests:
                report["requests_sample"] = seen[:80]
            report["console_errors"] = console_errors[:10]
            context.close()
            browser.close()
    return report


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--expect", action="append", default=[], help="text that must render (repeatable)")
    ap.add_argument("--absent", action="append", default=[], help="fallback text that must NOT render (repeatable)")
    ap.add_argument("--click", action="append", default=[], help="click the first element with this text, in order")
    ap.add_argument("--wait-text", action="append", default=[], help="wait until this text appears")
    ap.add_argument("--expect-url", default=None, help="final URL must contain this (landing check)")
    ap.add_argument("--login-label", default=None, help="accessible label of the login input")
    ap.add_argument("--login-secret-env", default=None, help="env var (or --env-file key) holding the login secret")
    ap.add_argument("--login-button", default="Log in", help="accessible name of the submit button")
    ap.add_argument("--after-login-url", default=None, help="navigate here after logging in")
    ap.add_argument("--env-file", default=None, help="KEY=VALUE file to read the login secret from")
    ap.add_argument("--local-storage", action="append", default=[], help="KEY=VALUE seeded before page scripts run")
    ap.add_argument("--api-pattern", default="/api/", help="URL substring that marks backend calls")
    ap.add_argument("--allow-write", action="append", default=[], help="URL substring a write may pass to")
    ap.add_argument("--replay-api", action="store_true", help="fetch each API GET once, replay later copies")
    ap.add_argument("--max-api-seconds", type=float, default=45.0, help="load brake per API response")
    ap.add_argument("--require-api", action="store_true", help="FAIL as drive-blind when no API call was seen")
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds per wait")
    ap.add_argument("--settle-ms", type=int, default=1500, help="pause after each step")
    ap.add_argument("--case-sensitive", action="store_true")
    ap.add_argument("--screenshot", default=None)
    ap.add_argument("--dump-text", action="store_true", help="include the first 4000 chars of rendered text")
    ap.add_argument("--dump-requests", action="store_true",
                    help="include every request the page made (method + URL, no query); use it "
                         "to find the right --api-pattern when the guard sees nothing")
    ap.add_argument("--headed", action="store_true", help="show the browser (debugging only)")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = drive(args)
    if "env_error" in report:
        out = {"verdict": "ENV-ERROR", "reasons": [report["env_error"]], "url": args.url}
        print(json.dumps(out, indent=2) if args.json else f"ENV-ERROR {args.url}\n  {report['env_error']}")
        return 2
    v, reasons = verdict(report, args.require_api)
    if report.get("drive_error"):
        reasons.append(f"[drive-blind] {report['drive_error']}")
        v = "FAIL"
    report["verdict"], report["reasons"] = v, reasons
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        api = report["api"]
        print(f"{v} {args.url}")
        print(f"  final URL: {report.get('final_url')}  status: {report.get('document_status')}  "
              f"rendered chars: {report.get('rendered_chars')}")
        for s, ok in (report.get("text") or {}).get("expect", {}).items():
            print(f"  expect {'PRESENT' if ok else 'MISSING'}: {s!r}")
        for s, seen in (report.get("text") or {}).get("absent", {}).items():
            print(f"  absent {'VIOLATED' if seen else 'ok'}: {s!r}")
        print(f"  api: {api['requests']} request(s), {api['fulfilled_from_cache']} replayed, "
              f"{len(api['aborted_writes'])} write(s) aborted, slowest {api['slowest_s']}s")
        for w in api["aborted_writes"]:
            print(f"    aborted: {w}")
        if report.get("console_errors"):
            print(f"  console errors: {len(report['console_errors'])} (first: {report['console_errors'][0]!r})")
        if report.get("screenshot"):
            print(f"  screenshot: {report['screenshot']}")
        for r in reasons:
            print(f"  {r}")
    return 0 if v == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
