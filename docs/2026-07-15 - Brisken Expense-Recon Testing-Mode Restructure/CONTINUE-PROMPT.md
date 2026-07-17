Continue the Brisken expense-reconciliation build. First feature: add the
double-click-to-give-feedback function we have in the other apps and the
website prototype, so Chris (and any reviewer) can leave anchored feedback
from inside the live tool.

## Where things are
- The app is LIVE at brisken-expense-recon.fly.dev (deployed 2026-07-15) and
  is a role-split testing-mode intake app: users upload + review published
  runs; operators run the pipeline + publish. FastAPI + Jinja, base.html
  shell, `/data` volume, HMAC-cookie auth with a `role` (user/operator).
- Code target is `origin/main`. p1 finance work ships from a WORKTREE OFF
  MAIN, not the shared clone (which is 91 commits behind on a lead-desk
  branch). Reuse the existing worktree if present, else:
  `git worktree add ../agentic-ops1-recon -b client/brisken/expense-recon-feedback origin/main`
  (or branch off the just-merged testing-mode work; check `git worktree list`
  and `gh pr view 228` first — if #228 merged, branch off fresh main).
- Module: `workspace/clients/brisken/automations/expense-reconciliation/`.
- Tests: `uv run --with 'pytest>=8.0' pytest` from the module dir (503 green
  as of the last session). Regression gate: `uv run expense-recon calibrate
  --config examples/run.example.json` (exit 0).
- Read `memory/project_brisken_expense_recon_chris_process.md` for the full
  built state, and the session checkpoint in this same folder.

## The reference implementation (mirror this, don't reinvent)
Two files already implement the exact widget:

1. **Client side** (the dblclick UX):
   `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html`
   - `document.addEventListener('dblclick', ...)` (~line 1509): double-click
     anywhere drops an anchored feedback popover at that spot, capturing what
     the reviewer clicked on (nearest heading/section/element text) + page +
     position.
   - A floating `.feedback-fab` button (bottom corner, ~line 1378) for a
     general (centered) note.
   - `#fbPop` popover (~line 1399) + a one-time explainer hint `#fbHintOverlay`
     (~line 1425), shown once via localStorage.
   - `POST /feedback` (~line 1540) with the note + anchor + reviewer.
   - CSS ~lines 483-540.

2. **Server side** (same FastAPI stack as the recon app):
   `workspace/clients/brisken/onepilot-site/app.py`
   - `POST /feedback` (~line 228): append one JSON line to
     `feedback.jsonl` on the `/data` volume, attributing to the reviewer.
   - `GET /feedback-log` (~line 321): a simple HTML table view, newest first.
   - `GET /feedback.jsonl` (~line 342): raw NDJSON download.
   - The reviewer name is injected into the page server-side.

The One Assessment portal ships the same widget on every logged-in page,
parity-guarded by a `test_feedback_widget_parity.py` test; keep the recon
version consistent with that family.

## What to build (in the recon app)
- A shared feedback widget in `web/templates/base.html` (so it rides on every
  logged-in page: home, workbench, help) OR a `{% include %}` partial the
  pages pull in. Double-click -> anchored popover; a floating Feedback FAB;
  the one-time hint. Match the Brisken tokens/theme already in tokens.css
  (no new palette). No em-dashes, no emoji (deliverable rules).
- The reviewer = the logged-in role/session. The recon app has no per-user
  name today (one shared user code), so attribute by role ("user"/"operator")
  plus the current page/run id; if you want a name, reuse the session or add
  an optional name field, your call, keep it minimal.
- `POST /feedback` route in `web/app.py`: append to `feedback.jsonl` on the
  data root (`app.state.data_root`), capturing note + page path + anchor
  text + reviewer + timestamp (use `_now_iso()`). Never fail the page on a
  write error.
- `GET /feedback-log` (operator-gated) + `GET /feedback.jsonl` (operator-gated)
  so the dev can read what Chris left. Add both to `auth.path_requires_operator`.
- Tie it into the dev-side notifier: extend `tools/brisken-recon-notify.py`
  to also poll new feedback (or add feedback to `/api/operator/state`) and
  mail matthias on a new note. Optional this pass; at minimum leave a clear
  seam.
- Tests: a `test_web_feedback.py` covering the POST append + the operator
  gate on the log views + the widget rendering on a logged-in page.

## Ship
Verify (suite + calibrate + a TestClient behavioral check that a POST lands
in feedback.jsonl and the log view is operator-gated), then commit/push/PR
per the B6 ship rule. Deploy is Band-3: only `fly deploy` on an explicit
order. If you do deploy, live-verify the widget renders + a POST persists on
the origin.

## Still-open follow-ups from last session (not this task, but adjacent)
- `EXPENSE_RECON_NOTIFY_USER` (Chris's email) is unset -> the "ready" ping is
  dev-copy-only until the owner supplies it.
- `/data/cards.json` is unauthored -> the upload form shows a plain card-name
  text box until the owner supplies the real card list (label/entity/account
  id each).
