# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Miniature web interface for the prompt queue (skil_prompt-queue).

Serves a single-page UI on localhost for viewing, adding, editing,
reordering, and deleting queued prompts in .claude/queue/pending.md,
plus a read-only tail of done.md. The text file stays the source of
truth: hand-edits and agent drains appear on the next poll (2s).
Every mutation is double-guarded: an optimistic-concurrency hash on
the whole file, plus content addressing (the client sends the prompt
text it believes it is acting on; the server rejects if the slot
holds something else), so the UI can never act on the wrong prompt
after a drain shifted the list.

Writes canonicalize the file: the leading header comment is kept,
everything else is regenerated from the parsed prompt list. Hand-
written comments below the header do not survive a UI mutation;
annotate prompts as plain text inside the block instead.

Run:        uv run tools/prompt-queue-ui.py [--port 7077] [--no-open]
Standalone: opens in the default browser.
VS Code:    Ctrl+Shift+P -> "Simple Browser: Show" -> paste the printed
            URL. Optionally wire a .vscode/tasks.json background task
            running: uv run tools/prompt-queue-ui.py --no-open

Mutations require the X-PQ custom header (cross-origin requests cannot
set it without a CORS preflight, which this server never grants) and a
loopback Host header, so a malicious web page cannot drive the queue
via CSRF or DNS rebinding. Binds 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUEUE_DIR = REPO / ".claude" / "queue"
PENDING = QUEUE_DIR / "pending.md"
DONE = QUEUE_DIR / "done.md"

COMMENT = re.compile(r"<!--.*?-->", re.S)
SEP = re.compile(r"(?m)^---\s*$")
# done.md entries are anchored on the stamp shape, not bare '## ', so a
# prompt that itself contains markdown headings cannot mis-segment the tail.
DONE_ENTRY = re.compile(
    r"(?m)^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} .+"
    r"(?:\n(?!## \d{4}-\d{2}-\d{2} \d{2}:\d{2} ).*)*"
)

DEFAULT_HEADER = """<!--
PROMPT QUEUE - pending items (FIFO).
Add a prompt as a new block separated by a line with exactly ---.
Append anytime, including while a chat is mid-task; picked up on the next drain.
Run with /skil_prompt-queue (or say "drain the queue"). Drains once, then stops.
The mini UI (tools/prompt-queue-ui.py) canonicalizes this file on write:
comments below this header are dropped.
-->"""

_LOCK = threading.Lock()


# ---------- queue file model ----------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def file_hash(raw: str) -> str:
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def parse_pending(raw: str) -> list[str]:
    """Same rule as the skill: strip HTML comments, split on ---, drop empties."""
    no_comments = COMMENT.sub("", raw)
    return [s.strip() for s in SEP.split(no_comments) if s.strip()]


def leading_comment(raw: str) -> str:
    m = re.match(r"\s*(<!--.*?-->)", raw, re.S)
    return m.group(1) if m else DEFAULT_HEADER


def guard_separator_lines(prompt: str) -> str:
    """A block-edge '  ---' line loses its indent to strip(); re-indent any
    line that would otherwise serialize as a separator and split the block."""
    return "\n".join(
        (" " + line) if re.fullmatch(r"---\s*", line) else line
        for line in prompt.splitlines()
    )


def serialize_pending(header: str, prompts: list[str]) -> str:
    if not prompts:
        return header + "\n"
    body = "\n---\n".join(guard_separator_lines(p) for p in prompts)
    return header + "\n\n" + body + "\n"


def atomic_write(path: Path, text: str) -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=QUEUE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def append_done(entries: list[tuple[str, str, str]]) -> None:
    """entries: (prompt, tag, outcome). Called only AFTER pending.md wrote OK,
    so done.md never records a removal that did not happen."""
    if not entries:
        return
    base = read_text(DONE)
    if not base:
        base = ("<!-- PROMPT QUEUE - completed items. Newest at the bottom. "
                "The agent appends here as it drains pending.md. -->\n")
    chunks = [base]
    for prompt, tag, outcome in entries:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        chunks.append(f"\n## {stamp} {tag}\n{prompt}\n> {outcome}\n")
    atomic_write(DONE, "".join(chunks))


def validate_prompt_text(text: str) -> str | None:
    """Reject text that would corrupt the block format on re-parse."""
    if not text.strip():
        return "Prompt is empty."
    if any(re.fullmatch(r"---\s*", line) for line in text.splitlines()):
        return ("A line containing only --- is the block separator; "
                "rephrase that line (interior lines may be indented instead).")
    if "<!--" in text or "-->" in text:
        return "HTML comment markers are stripped by the parser; remove <!-- and -->."
    return None


# ---------- mutations (lock + file hash + content addressing) ----------

class StaleState(Exception):
    pass


def mutate(client_hash: str, fn) -> dict:
    """Read-check-modify-write under the lock.

    fn(prompts, done_entries) mutates the prompt list in place and may
    append (prompt, tag, outcome) tuples to done_entries; those are written
    to done.md only after pending.md persisted.
    """
    with _LOCK:
        raw = read_text(PENDING)
        if file_hash(raw) != client_hash:
            raise StaleState()
        prompts = parse_pending(raw)
        done_entries: list[tuple[str, str, str]] = []
        fn(prompts, done_entries)
        atomic_write(PENDING, serialize_pending(leading_comment(raw), prompts))
        append_done(done_entries)
        return state_dict()


def check_slot(prompts: list[str], idx: int, original: str) -> None:
    """Content addressing: the slot must still hold what the client saw."""
    if not 0 <= idx < len(prompts):
        raise StaleState()
    if prompts[idx] != original:
        raise StaleState()


def state_dict() -> dict:
    raw = read_text(PENDING)
    done_raw = read_text(DONE)
    return {
        "hash": file_hash(raw),
        "pending": parse_pending(raw),
        "done_tail": DONE_ENTRY.findall(done_raw)[-15:][::-1],
        "pending_path": str(PENDING),
    }


# ---------- HTTP layer ----------

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prompt Queue</title>
<style>
  :root { color-scheme: light dark;
    --bg:#f6f7f9; --card:#fff; --ink:#1a1d21; --mut:#6b7280; --line:#e2e5ea;
    --acc:#2563eb; --danger:#b91c1c; --ok:#059669; }
  @media (prefers-color-scheme: dark) { :root {
    --bg:#101216; --card:#1a1d23; --ink:#e7e9ee; --mut:#8b93a1; --line:#2a2f38;
    --acc:#5b8def; --danger:#ef6b6b; --ok:#34d399; } }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:14px/1.45 system-ui, "Segoe UI", sans-serif; }
  .wrap { max-width:580px; margin:0 auto; padding:16px 14px 40px; }
  header { display:flex; align-items:baseline; gap:10px; margin-bottom:4px; }
  h1 { font-size:16px; margin:0; }
  .count { color:var(--mut); font-size:12.5px; }
  .hint { color:var(--mut); font-size:12px; margin:0 0 14px; }
  .hint code { background:var(--card); border:1px solid var(--line);
    border-radius:4px; padding:1px 5px; font-size:11.5px; }
  .addbox { display:flex; flex-direction:column; gap:6px; margin-bottom:16px; }
  textarea { width:100%; min-height:54px; resize:vertical; background:var(--card);
    color:var(--ink); border:1px solid var(--line); border-radius:8px;
    padding:8px 10px; font:13px/1.4 ui-monospace, Consolas, monospace; }
  textarea:focus { outline:2px solid var(--acc); outline-offset:-1px; border-color:transparent; }
  .row { display:flex; gap:8px; align-items:center; }
  button { border:1px solid var(--line); background:var(--card); color:var(--ink);
    border-radius:7px; padding:5px 11px; font-size:12.5px; cursor:pointer; }
  button:hover { border-color:var(--acc); color:var(--acc); }
  button.primary { background:var(--acc); border-color:var(--acc); color:#fff; }
  button.primary:hover { filter:brightness(1.08); color:#fff; }
  button.icon { padding:4px 8px; font-size:12px; line-height:1; }
  button.danger:hover { border-color:var(--danger); color:var(--danger); }
  button:disabled { opacity:.45; cursor:default; }
  .kbd { color:var(--mut); font-size:11.5px; margin-left:auto; }
  ol.queue { list-style:none; margin:0; padding:0; display:flex;
    flex-direction:column; gap:8px; }
  ol.queue.settle { pointer-events:none; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px;
    padding:9px 11px; display:flex; gap:10px; }
  .num { color:var(--mut); font:12px ui-monospace, Consolas, monospace;
    padding-top:2px; min-width:18px; }
  .body { flex:1; min-width:0; }
  .text { white-space:pre-wrap; overflow-wrap:break-word;
    font:13px/1.45 ui-monospace, Consolas, monospace; }
  .text.clamp { display:-webkit-box; -webkit-line-clamp:3;
    -webkit-box-orient:vertical; overflow:hidden; cursor:pointer; }
  .btns { display:flex; gap:4px; align-items:flex-start; }
  .empty { color:var(--mut); text-align:center; padding:22px 0 14px; font-size:13px; }
  details { margin-top:22px; }
  summary { color:var(--mut); font-size:12.5px; cursor:pointer; user-select:none; }
  .done-entry { background:var(--card); border:1px solid var(--line); border-radius:8px;
    padding:7px 10px; margin-top:8px; font:12px/1.45 ui-monospace, Consolas, monospace;
    white-space:pre-wrap; overflow-wrap:break-word; color:var(--mut); }
  .done-entry b { color:var(--ok); font-weight:600; }
  #toast { position:fixed; left:50%; bottom:18px; transform:translateX(-50%);
    background:var(--ink); color:var(--bg); border-radius:8px; padding:7px 14px;
    font-size:12.5px; opacity:0; transition:opacity .25s; pointer-events:none; }
  #toast.show { opacity:.94; }
  .foot { margin-top:26px; color:var(--mut); font-size:11px; }
</style>
</head>
<body>
<div class="wrap">
  <header><h1>Prompt Queue</h1><span class="count" id="count"></span></header>
  <p class="hint">FIFO. Drain by typing <code>/skil_prompt-queue</code> in the Claude
  chat once it finishes its current task. This page and the file stay in sync.</p>

  <div class="addbox">
    <textarea id="add" placeholder="Queue a prompt&hellip;"></textarea>
    <div class="row">
      <button class="primary" id="addBtn">Add to queue</button>
      <span class="kbd">Ctrl+Enter</span>
    </div>
  </div>

  <ol class="queue" id="queue"></ol>
  <div class="empty" id="empty" hidden>Queue is empty.</div>

  <div class="row" style="margin-top:14px" id="clearRow" hidden>
    <button class="danger" id="clearBtn">Clear queue</button>
  </div>

  <details id="doneWrap"><summary id="doneSummary">Done</summary>
    <div id="done"></div>
  </details>

  <div class="foot" id="foot"></div>
</div>
<div id="toast"></div>

<script>
"use strict";
let state = { hash: "", pending: [], done_tail: [] };
let editing = -1;          // index currently being edited, -1 = none
let editOriginal = null;   // prompt text captured when the edit opened
let inFlight = 0;          // mutations in flight; poll results are ignored meanwhile
let toastTimer = null;
let settleTimer = null;

const $ = id => document.getElementById(id);

function toast(msg) {
  $("toast").textContent = msg;
  $("toast").classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("toast").classList.remove("show"), 2200);
}

async function api(path, body) {
  let res;
  try {
    res = await fetch(path, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json", "X-PQ": "1" } : { "X-PQ": "1" },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    toast("Server unreachable; is prompt-queue-ui.py still running?");
    return null;
  }
  if (res.status === 409) {
    const fresh = await res.json().catch(() => null);
    if (fresh) apply(fresh.state, true);
    toast("Queue changed underneath; refreshed.");
    return null;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    toast(err.error || ("Error " + res.status));
    return null;
  }
  return res.json().catch(() => null);
}

function esc(s) {
  return s.replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
}

// external=true when the new state came from a poll/409, not the user's own click
function apply(s, external) {
  if (!s) return;
  const changed = s.hash !== state.hash;
  state = s;
  if (editing !== -1) {
    // re-anchor the open edit by content; never clobber the draft text
    const at = state.pending.indexOf(editOriginal);
    if (at === -1) {
      const draft = ($("editBox") || {}).value || "";
      editing = -1; editOriginal = null;
      if (draft.trim() && draft !== editOriginal) {
        $("add").value = draft;
        toast("Edited prompt left the queue; draft moved to the add box.");
      } else {
        toast("Edited prompt left the queue; edit cancelled.");
      }
      render();
      return;
    }
    if (at !== editing) editing = at;
    $("count").textContent = countLabel();
    if (changed && external) toast("Queue changed underneath; edit re-anchored.");
    return;
  }
  if (changed) {
    render();
    if (external) {
      // brief click-shield so a committed click cannot land on a row that just moved
      const q = $("queue");
      q.classList.add("settle");
      clearTimeout(settleTimer);
      settleTimer = setTimeout(() => q.classList.remove("settle"), 350);
    }
  }
}

function countLabel() {
  const n = state.pending.length;
  return n === 0 ? "empty" : n + " pending";
}

function render() {
  $("count").textContent = countLabel();
  $("empty").hidden = state.pending.length > 0;
  $("clearRow").hidden = state.pending.length === 0;

  const q = $("queue");
  q.innerHTML = "";
  state.pending.forEach((p, i) => {
    const li = document.createElement("li");
    li.className = "card";
    if (i === editing) {
      li.innerHTML =
        '<span class="num">' + (i + 1) + "</span>" +
        '<div class="body"><textarea id="editBox"></textarea>' +
        '<div class="row" style="margin-top:6px">' +
        '<button class="primary" id="saveBtn">Save</button>' +
        '<button id="cancelBtn">Cancel</button>' +
        '<span class="kbd">Ctrl+Enter / Esc</span></div></div>';
      q.appendChild(li);
      const box = li.querySelector("#editBox");
      box.value = p;
      box.style.minHeight = "72px";
      li.querySelector("#saveBtn").onclick = () => saveEdit(box.value);
      li.querySelector("#cancelBtn").onclick = () => { editing = -1; editOriginal = null; render(); };
      box.onkeydown = e => {
        if (e.key === "Enter" && e.ctrlKey) saveEdit(box.value);
        if (e.key === "Escape") { editing = -1; editOriginal = null; render(); }
      };
      box.focus();
      return;
    }
    li.innerHTML =
      '<span class="num">' + (i + 1) + "</span>" +
      '<div class="body"><div class="text clamp">' + esc(p) + "</div></div>" +
      '<div class="btns">' +
      '<button class="icon" title="Move up">&#9650;</button>' +
      '<button class="icon" title="Move down">&#9660;</button>' +
      '<button class="icon" title="Edit">&#9998;</button>' +
      '<button class="icon danger" title="Delete">&#10005;</button></div>';
    const [up, down, edit, del] = li.querySelectorAll("button");
    up.disabled = i === 0;
    down.disabled = i === state.pending.length - 1;
    up.onclick = () => post("/api/move", { index: i, original: p, dir: -1 });
    down.onclick = () => post("/api/move", { index: i, original: p, dir: 1 });
    edit.onclick = () => { editing = i; editOriginal = p; render(); };
    del.onclick = () => post("/api/delete", { index: i, original: p });
    li.querySelector(".text").onclick = e => e.currentTarget.classList.toggle("clamp");
    q.appendChild(li);
  });

  const d = $("done");
  d.innerHTML = "";
  $("doneSummary").textContent = "Done (" + state.done_tail.length +
    (state.done_tail.length === 15 ? "+, newest first)" : ", newest first)");
  state.done_tail.forEach(e => {
    const div = document.createElement("div");
    div.className = "done-entry";
    div.innerHTML = esc(e).replace(/^## (.+)$/, "<b>$1</b>");
    d.appendChild(div);
  });
  $("foot").textContent = state.pending_path;
}

async function post(path, body) {
  inFlight++;
  try {
    const r = await api(path, { ...body, hash: state.hash });
    if (r) apply(r.state, false);
  } finally { inFlight--; }
}

async function saveEdit(text) {
  inFlight++;
  try {
    const r = await api("/api/update",
      { index: editing, original: editOriginal, text: text, hash: state.hash });
    if (r) { editing = -1; editOriginal = null; apply(r.state, false); }
  } finally { inFlight--; }
}

$("addBtn").onclick = addPrompt;
$("add").onkeydown = e => { if (e.key === "Enter" && e.ctrlKey) addPrompt(); };
async function addPrompt() {
  const text = $("add").value;
  if (!text.trim()) return;
  inFlight++;
  try {
    const r = await api("/api/add", { text: text, hash: state.hash });
    if (r) { $("add").value = ""; apply(r.state, false); toast("Queued."); }
  } finally { inFlight--; }
}

$("clearBtn").onclick = async () => {
  if (!confirm("Move all " + state.pending.length + " pending prompts to done as cleared?")) return;
  inFlight++;
  try {
    const r = await api("/api/clear", { hash: state.hash });
    if (r) { apply(r.state, false); toast("Cleared."); }
  } finally { inFlight--; }
};

async function poll() {
  if (editing !== -1 || inFlight > 0) return;
  const r = await api("/api/state");
  if (inFlight === 0) apply(r, true);
}
api("/api/state").then(s => { if (s) { state = s; render(); } });
setInterval(poll, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "PromptQueueUI/1.1"

    def log_message(self, fmt, *args):  # quiet
        pass

    # -- helpers --
    def _send(self, code: int, body: dict | str, ctype: str = "application/json") -> None:
        data = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _guard(self) -> bool:
        """Loopback Host + custom header on API calls: blocks CSRF / DNS rebinding."""
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            self._send(403, {"error": "forbidden host"})
            return False
        if self.path.startswith("/api/") and self.headers.get("X-PQ") != "1":
            self._send(403, {"error": "missing X-PQ header"})
            return False
        return True

    def _body(self) -> dict | None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 1_000_000:
                self._send(413, {"error": "too large"})
                return None
            return json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "bad JSON"})
            return None

    # -- routes --
    def do_GET(self) -> None:
        if not self._guard():
            return
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, PAGE, "text/html")
        elif self.path == "/api/state":
            self._send(200, state_dict())
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._guard():
            return
        body = self._body()
        if body is None:
            return
        client_hash = str(body.get("hash") or "")
        try:
            if self.path == "/api/add":
                text = str(body.get("text") or "").replace("\r\n", "\n").strip()
                if (err := validate_prompt_text(text)):
                    self._send(422, {"error": err})
                    return
                result = mutate(client_hash, lambda ps, dn: ps.append(text))
            elif self.path == "/api/update":
                idx = int(body.get("index", -1))
                original = str(body.get("original") or "")
                text = str(body.get("text") or "").replace("\r\n", "\n").strip()
                if (err := validate_prompt_text(text)):
                    self._send(422, {"error": err})
                    return
                def upd(ps: list[str], dn: list) -> None:
                    check_slot(ps, idx, original)
                    ps[idx] = text
                result = mutate(client_hash, upd)
            elif self.path == "/api/delete":
                idx = int(body.get("index", -1))
                original = str(body.get("original") or "")
                def rm(ps: list[str], dn: list) -> None:
                    check_slot(ps, idx, original)
                    dn.append((ps.pop(idx), "deleted", "removed via queue UI"))
                result = mutate(client_hash, rm)
            elif self.path == "/api/move":
                idx = int(body.get("index", -1))
                original = str(body.get("original") or "")
                dir_ = 1 if int(body.get("dir", 0)) > 0 else -1
                def mv(ps: list[str], dn: list) -> None:
                    check_slot(ps, idx, original)
                    j = idx + dir_
                    if not 0 <= j < len(ps):
                        raise StaleState()
                    ps[idx], ps[j] = ps[j], ps[idx]
                result = mutate(client_hash, mv)
            elif self.path == "/api/clear":
                def clear(ps: list[str], dn: list) -> None:
                    for p in ps:
                        dn.append((p, "cleared", "cleared via queue UI"))
                    ps.clear()
                result = mutate(client_hash, clear)
            else:
                self._send(404, {"error": "not found"})
                return
        except StaleState:
            self._send(409, {"error": "stale", "state": state_dict()})
            return
        except (TypeError, ValueError):
            self._send(422, {"error": "bad request", "state": state_dict()})
            return
        self._send(200, {"ok": True, "state": result})


class ExclusiveServer(ThreadingHTTPServer):
    # On Windows, SO_REUSEADDR lets a second instance bind over a live
    # listener; exclusive binding makes the second launch fail loudly
    # and fall through to the next port instead.
    allow_reuse_address = False


def bind_server(preferred: int) -> ExclusiveServer:
    for port in range(preferred, preferred + 10):
        try:
            return ExclusiveServer(("127.0.0.1", port), Handler)
        except OSError:
            continue
    print(f"ERROR: no free port in {preferred}..{preferred + 9}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Prompt queue mini UI (localhost)")
    ap.add_argument("--port", type=int, default=7077)
    ap.add_argument("--no-open", action="store_true",
                    help="don't auto-open the default browser")
    args = ap.parse_args()

    if not PENDING.exists():
        atomic_write(PENDING, DEFAULT_HEADER + "\n")

    httpd = bind_server(args.port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"Prompt Queue UI: {url}")
    print(f"Queue file:      {PENDING}")
    print('VS Code embed:   Ctrl+Shift+P -> "Simple Browser: Show" -> paste the URL')
    if not args.no_open:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
