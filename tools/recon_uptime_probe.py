#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Outside-in uptime probe + notifier for the Brisken expense-recon app
(backlog item 123: nobody was told when the app was down; the last outage
was surfaced by the owner, not by a monitor).

Fly's own `[[http_service.checks]]` on /healthz restarts a dead process
but tells no human. This script runs OUTSIDE the app (GitHub Actions,
`.github/workflows/expense-recon-uptime.yml`, every 10 minutes) and turns
an outage into one GitHub issue plus one mail, and a recovery into a
comment, a close and one more mail. Stdlib only; nothing under the module's
`src/` is touched.

`probe`: three checks, each retried once after --retry-delay seconds (5)
before it counts as DOWN, so a single blip never pages.

  api   GET <api>/healthz     200 within --timeout, JSON status == "ok",
                              disk.available true, disk.intake_refusing
                              false. free_pct below 15 is a WARN: reported
                              in the output, does not fail the probe.
  mx    TCP <mx>:25           a `220` banner within --timeout, then QUIT.
                              No EHLO, no RCPT, no DATA: the intake never
                              sees a message.
  spa   GET <spa>/            200 within --timeout (the Lovable-hosted
                              shell; a 200 here says nothing about the
                              API, which is why `api` exists).

Output: one line per check (OK / WARN / DOWN + detail) and a summary line.
With --json the table goes to stderr and the JSON result to stdout, so
`probe --json > probe.json` keeps the file clean. Exit 0 when every check
is OK or WARN, 1 when any check is DOWN, 2 when the probe itself broke.

`notify --result probe.json [--dry-run]`: applies the alert policy using
`gh` (GH_TOKEN) and Resend (RESEND_API_KEY, recipient BRIEFING_TO, the
morning-briefing conventions):

  DOWN, no open `recon-uptime` issue  -> create the label if absent, open
                                          ONE issue with the check table,
                                          send ONE mail
  DOWN, open issue exists             -> append one comment (no mail: it
                                          must not page every 10 minutes)
  all OK, open issue exists           -> comment "recovered at <UTC>",
                                          close it, send one recovery mail
  all OK, no issue                    -> nothing

--dry-run prints what it would do and exits 0 without calling gh or
Resend. When RESEND_API_KEY (or BRIEFING_TO) is unset the mail leg is
skipped with a log line; the issue is the floor. Exit 0 when the policy
was applied (also when the app is down: the issue is the signal), 2 when
the notifier itself failed (gh error, unreadable result, a refused mail).

Test seams, never set in production:
  RECON_UPTIME_GH_CMD      the gh command to invoke instead of `gh`
                           (a full command line, shlex-split)
  RECON_UPTIME_RESEND_URL  the endpoint POSTed to instead of Resend

Usage:
  uv run tools/recon_uptime_probe.py probe [--json] [--api URL] [--mx HOST] [--spa URL]
  uv run tools/recon_uptime_probe.py notify --result probe.json [--dry-run] [--repo OWNER/REPO]
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_API = "https://brisken-expense-recon.fly.dev"
DEFAULT_MX = "mx.expenses.brisken.com"
DEFAULT_SPA = "https://expenses.brisken.com"
MX_PORT = 25
TIMEOUT_S = 10.0
RETRY_DELAY_S = 5.0
WARN_FREE_PCT = 15.0
LABEL = "recon-uptime"
DEFAULT_REPO = "011matthias/agentic-ops1.01"
# Cloudflare (in front of the Lovable host and of api.resend.com) answers
# Python's default urllib User-Agent with 403 error 1010. A real UA passes.
PROBE_UA = "Mozilla/5.0 (compatible; agentic-ops-recon-uptime/1.0)"
RESEND_UA = "agentic-ops-recon-uptime/1.0"
RESEND_URL = "https://api.resend.com/emails"
RESEND_FROM = "onboarding@resend.dev"
SUBJECT_HOST = "expenses.brisken.com"


class CheckFailed(Exception):
    """One check did not pass; the message is the human detail."""


class NotifyError(Exception):
    """The notifier itself broke (gh, the result file, a refused mail)."""


# ------------------------------------------------------------------ probe --

def _get(url: str, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url, headers={"User-Agent": PROBE_UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(1_000_000)
    except urllib.error.HTTPError as e:
        raise CheckFailed(f"HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise CheckFailed(f"unreachable: {e.reason}") from None
    except (OSError, ValueError) as e:
        raise CheckFailed(f"unreachable: {e}") from None


def check_api(base: str, timeout: float) -> dict:
    url = base.rstrip("/") + "/healthz"
    status, body = _get(url, timeout)
    if status != 200:
        raise CheckFailed(f"HTTP {status}")
    try:
        data = json.loads(body)
    except ValueError:
        raise CheckFailed("healthz body is not JSON") from None
    if not isinstance(data, dict) or data.get("status") != "ok":
        got = data.get("status") if isinstance(data, dict) else type(data).__name__
        raise CheckFailed(f"healthz status is {got!r}, not 'ok'")
    disk = data.get("disk")
    if not isinstance(disk, dict):
        raise CheckFailed("healthz has no disk block (build older than item 122?)")
    if disk.get("available") is not True:
        raise CheckFailed("disk.available is not true: the /data volume cannot be read")
    free_pct = disk.get("free_pct")
    if disk.get("intake_refusing"):
        raise CheckFailed(
            f"disk.intake_refusing is true (free {free_pct}%): "
            "the mailbox is turning receipts away")
    server = data.get("server") if isinstance(data.get("server"), dict) else {}
    result = {
        "detail": f"200 status=ok free_pct={free_pct} uptime_s={server.get('uptime_s')}",
        "free_pct": free_pct,
    }
    if isinstance(free_pct, (int, float)) and free_pct < WARN_FREE_PCT:
        result["warn"] = (
            f"disk free {free_pct}% is below the {WARN_FREE_PCT:g}% warn floor "
            "(reported, does not page)")
    return result


def _read_line(sock: socket.socket, deadline: float) -> str:
    buf = b""
    while b"\n" not in buf and len(buf) < 512:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CheckFailed("no banner line within the timeout")
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(128)
        except socket.timeout:
            raise CheckFailed("no banner line within the timeout") from None
        if not chunk:
            raise CheckFailed("connection closed before a banner")
        buf += chunk
    return buf.split(b"\n", 1)[0].decode("utf-8", "replace").rstrip("\r")


def check_mx(host: str, port: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        raise CheckFailed(f"connect failed: {e}") from None
    with sock:
        banner = _read_line(sock, deadline)
        if not banner.startswith("220"):
            raise CheckFailed(f"banner is not 220: {banner[:80]!r}")
        try:
            sock.sendall(b"QUIT\r\n")
            _read_line(sock, time.monotonic() + 2.0)  # 221, best effort
        except (OSError, CheckFailed):
            pass
    return {"detail": banner}


def check_spa(base: str, timeout: float) -> dict:
    status, body = _get(base.rstrip("/") + "/", timeout)
    if status != 200:
        raise CheckFailed(f"HTTP {status}")
    return {"detail": f"200 ({len(body)} bytes)"}


def run_check(name: str, target: str, fn, retry_delay: float) -> dict:
    """Run one check, retrying once after `retry_delay` so a blip is not an
    outage. A WARN is a pass and is not retried."""
    attempts = 0
    last = ""
    while attempts < 2:
        attempts += 1
        try:
            r = fn()
        except CheckFailed as e:
            last = str(e)
            if attempts < 2:
                time.sleep(retry_delay)
            continue
        out = {"name": name, "target": target, "attempts": attempts}
        if r.get("warn"):
            out["state"] = "WARN"
            out["detail"] = f"{r['detail']}; {r['warn']}"
        else:
            out["state"] = "OK"
            out["detail"] = r["detail"]
        if "free_pct" in r:
            out["free_pct"] = r["free_pct"]
        return out
    return {"name": name, "target": target, "state": "DOWN",
            "detail": f"after retry: {last}", "attempts": attempts}


def render_table(checks: list[dict]) -> list[str]:
    return [f"{c['name']:<4} {c['state']:<5} {c['target']}  {c['detail']}"
            for c in checks]


def split_mx(value: str) -> tuple[str, int]:
    """`host` or `host:port`; the port defaults to 25 (an MX target can only
    be port 25, the override exists for the local stand-in in the tests)."""
    host, sep, port = value.rpartition(":")
    if sep and port.isdigit():
        return host, int(port)
    return value, MX_PORT


def cmd_probe(a: argparse.Namespace) -> int:
    mx_host, mx_port = split_mx(a.mx)
    checks = [
        run_check("api", a.api.rstrip("/") + "/healthz",
                  lambda: check_api(a.api, a.timeout), a.retry_delay),
        run_check("mx", f"{mx_host}:{mx_port}",
                  lambda: check_mx(mx_host, mx_port, a.timeout), a.retry_delay),
        run_check("spa", a.spa.rstrip("/") + "/",
                  lambda: check_spa(a.spa, a.timeout), a.retry_delay),
    ]
    down = [c["name"] for c in checks if c["state"] == "DOWN"]
    warn = [c["name"] for c in checks if c["state"] == "WARN"]
    if down:
        summary = "DOWN: " + ", ".join(down)
    elif warn:
        summary = ("all OK, with WARN on " + ", ".join(warn)
                   + " (reported, does not page)")
    else:
        summary = "all OK"
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "targets": {"api": a.api, "mx": a.mx, "spa": a.spa},
        "checks": checks,
        "down": bool(down),
        "warn": bool(warn),
        "summary": summary,
    }
    human = sys.stderr if a.json else sys.stdout
    print("\n".join(render_table(checks) + [f"summary: {summary}"]), file=human)
    if a.json:
        print(json.dumps(result, indent=2))
    return 1 if down else 0


# ----------------------------------------------------------------- notify --

def _stamp(checked_at: str | None) -> str:
    try:
        dt = datetime.fromisoformat(checked_at or "")
    except (TypeError, ValueError):
        dt = datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def md_table(result: dict) -> str:
    rows = ["| Check | State | Target | Detail |", "|---|---|---|---|"]
    for c in result.get("checks", []):
        detail = str(c.get("detail", "")).replace("|", "\\|")
        rows.append(f"| {c.get('name')} | {c.get('state')} | `{c.get('target')}` | {detail} |")
    lines = [f"Probed at {_stamp(result.get('checked_at'))}: {result.get('summary', '')}", "",
             *rows]
    run = _run_url()
    if run:
        lines += ["", f"Run: {run}"]
    return "\n".join(lines)


def text_table(result: dict) -> str:
    lines = [f"Probed at {_stamp(result.get('checked_at'))}: {result.get('summary', '')}", ""]
    lines += render_table(result.get("checks", []))
    run = _run_url()
    if run:
        lines += ["", f"Run: {run}"]
    return "\n".join(lines)


class Gh:
    """Thin `gh` wrapper; the command comes from RECON_UPTIME_GH_CMD in tests."""

    def __init__(self, repo: str) -> None:
        self.cmd = shlex.split(os.environ.get("RECON_UPTIME_GH_CMD") or "gh")
        self.repo = repo

    def run(self, *args: str, stdin: str = "") -> str:
        argv = [*self.cmd, *args]
        try:
            p = subprocess.run(argv, input=stdin, capture_output=True,
                               text=True, encoding="utf-8", timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotifyError(f"gh {' '.join(args[:2])}: {e}") from None
        if p.returncode != 0:
            raise NotifyError(
                f"gh {' '.join(args[:2])} failed ({p.returncode}): "
                f"{p.stderr.strip()[:500]}")
        return p.stdout

    def open_issues(self) -> list[dict]:
        out = self.run("issue", "list", "--repo", self.repo, "--state", "open",
                       "--label", LABEL, "--json", "number,title,url", "--limit", "10")
        try:
            issues = json.loads(out or "[]")
        except ValueError:
            raise NotifyError(f"gh issue list returned non-JSON: {out[:200]!r}") from None
        return [i for i in issues if isinstance(i, dict) and "number" in i]

    def ensure_label(self) -> bool:
        out = self.run("label", "list", "--repo", self.repo, "--search", LABEL,
                       "--json", "name")
        try:
            names = {lbl.get("name") for lbl in json.loads(out or "[]")}
        except (ValueError, AttributeError):
            names = set()
        if LABEL in names:
            return False
        self.run("label", "create", LABEL, "--repo", self.repo, "--color", "B60205",
                 "--description", "expense-recon uptime alert (tools/recon_uptime_probe.py)")
        return True

    def create_issue(self, title: str, body: str) -> str:
        return self.run("issue", "create", "--repo", self.repo, "--title", title,
                        "--label", LABEL, "--body-file", "-", stdin=body).strip()

    def comment(self, number: int, body: str) -> None:
        self.run("issue", "comment", str(number), "--repo", self.repo,
                 "--body-file", "-", stdin=body)

    def close(self, number: int) -> None:
        self.run("issue", "close", str(number), "--repo", self.repo,
                 "--reason", "completed")


def send_mail(subject: str, text: str) -> bool | None:
    """One mail through Resend. None = skipped (no key / no recipient),
    True = accepted, False = refused. Never prints the key."""
    key = os.environ.get("RESEND_API_KEY")
    to = os.environ.get("BRIEFING_TO")
    if not key:
        print("mail: RESEND_API_KEY unset, skipping (the issue is the floor)")
        return None
    if not to:
        print("mail: BRIEFING_TO unset, skipping (the issue is the floor)")
        return None
    url = os.environ.get("RECON_UPTIME_RESEND_URL") or RESEND_URL
    payload = json.dumps({"from": RESEND_FROM, "to": to,
                          "subject": subject, "text": text}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": RESEND_UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"mail: RESEND_OK {resp.read(400).decode('utf-8', 'replace')}")
            return True
    except Exception as e:  # noqa: BLE001 - the reason belongs in the run log
        detail = getattr(e, "read", lambda: b"")()
        print(f"mail: RESEND_ERR {e} {detail.decode('utf-8', 'replace')[:300] if detail else ''}")
        return False


def cmd_notify(a: argparse.Namespace) -> int:
    try:
        with open(a.result, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, ValueError) as e:
        raise NotifyError(f"cannot read probe result {a.result}: {e}") from None
    if not isinstance(result, dict) or "down" not in result:
        raise NotifyError(f"{a.result} is not a probe result (no 'down' field)")
    down = bool(result["down"])
    stamp = _stamp(result.get("checked_at"))
    repo = a.repo or os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    title = f"{SUBJECT_HOST} is down ({stamp})"
    to = os.environ.get("BRIEFING_TO") or "(BRIEFING_TO unset: no mail)"

    if a.dry_run:
        print("DRY-RUN notify: no gh call, no mail")
        print(f"  probe: {result.get('summary', '?')} at {stamp}")
        if down:
            print(f"  if no open '{LABEL}' issue in {repo}: create the label if absent, "
                  f"open issue {title!r}, send one mail to {to}")
            print("  if an open issue exists: append one comment with the table, no mail")
        else:
            print(f"  if an open '{LABEL}' issue exists in {repo}: comment "
                  f"'recovered at {stamp}', close it, send one recovery mail to {to}")
            print("  if none: nothing")
        print("  table:")
        print("\n".join("    " + line for line in text_table(result).splitlines()))
        return 0

    gh = Gh(repo)
    issues = gh.open_issues()
    if len(issues) > 1:
        print(f"note: {len(issues)} open {LABEL} issues; acting on #{issues[0]['number']}")
    mail: bool | None = None
    if down and not issues:
        created = gh.ensure_label()
        print(f"label {LABEL}: {'created' if created else 'present'}")
        url = gh.create_issue(title, md_table(result))
        print(f"issue opened: {url or '(no url returned)'}")
        mail = send_mail(f"[{LABEL}] {title}",
                         f"{title}\n\n{text_table(result)}\n\nIssue: {url}")
    elif down:
        n = issues[0]["number"]
        gh.comment(n, md_table(result))
        print(f"still down: commented on #{n} (no mail)")
    elif issues:
        n = issues[0]["number"]
        gh.comment(n, f"recovered at {stamp}\n\n{md_table(result)}")
        gh.close(n)
        print(f"recovered: commented on and closed #{n}")
        mail = send_mail(f"[{LABEL}] {SUBJECT_HOST} recovered ({stamp})",
                         f"recovered at {stamp}\n\n{text_table(result)}")
    else:
        print("all OK and no open issue: nothing to do")
    if mail is False:
        raise NotifyError("the mail leg was refused (the issue exists; see the line above)")
    return 0


# ------------------------------------------------------------------- main --

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="run the three checks")
    pr.add_argument("--api", default=DEFAULT_API, help="API base URL (healthz lives under it)")
    pr.add_argument("--mx", default=DEFAULT_MX,
                    help="MX host; `host:port` overrides port 25 (tests only)")
    pr.add_argument("--spa", default=DEFAULT_SPA, help="SPA base URL")
    pr.add_argument("--json", action="store_true",
                    help="JSON result on stdout, human table on stderr")
    pr.add_argument("--timeout", type=float, default=TIMEOUT_S,
                    help="seconds per attempt (default %(default)s)")
    pr.add_argument("--retry-delay", type=float, default=RETRY_DELAY_S,
                    help="seconds before the one retry (default %(default)s; tests lower it)")
    pr.set_defaults(fn=cmd_probe)

    nt = sub.add_parser("notify", help="apply the alert policy to a probe result")
    nt.add_argument("--result", required=True, help="path to `probe --json` output")
    nt.add_argument("--dry-run", action="store_true",
                    help="print what would happen; call neither gh nor Resend")
    nt.add_argument("--repo", default=None,
                    help="OWNER/REPO for the issue (default: $GITHUB_REPOSITORY, "
                         f"then {DEFAULT_REPO})")
    nt.set_defaults(fn=cmd_notify)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except NotifyError as e:
        print(f"notify error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - the probe's own failure is exit 2, not DOWN
        print(f"{a.cmd} error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
