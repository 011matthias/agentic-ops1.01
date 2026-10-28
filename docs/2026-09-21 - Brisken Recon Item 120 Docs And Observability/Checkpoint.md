# Checkpoint: Brisken Recon Item 120 Docs And Observability

**Date:** 2026-09-21
**Status:** Docs-and-observability half of backlog item 120 shipped and merged; the hosting-org move and the restore rehearsal stay with the owner

---

## Summary

Backlog item 120 asked for five things inside the module so a stand-in could
deploy, verify and explain the expense-recon tool without the author. All five
shipped as PRs #1156 to #1160 plus #1163 and #1168, and the headline one is
proven live: `/healthz` now reports the commit the running image was built
from. Three claims in the session brief turned out to be wrong when checked,
and two of my own verification probes returned confident empties that were
blind instruments, both caught by running a known-present control first.

---

## What Was Done This Session

### Build identity on `/healthz` (PR #1156, Fly v195)

1. `server.commit` is baked into the image by a Dockerfile `ARG GIT_COMMIT`;
   `server.image` is `FLY_IMAGE_REF`, which Fly sets from the image the
   machine actually booted. Both live in `machine.snapshot()`, so every
   surface stamping it reports the same string.
2. Staleness is structurally impossible rather than unlikely: a version FILE
   drifts because the claim and the code are two things that can move apart,
   and a baked layer cannot drift from the image it is a layer of. The only
   remaining failure is absence, which reports `""`.
3. Proven end to end: deployed `640be61b`, `/healthz` returned
   `640be61b6264b8cdd01c96d631a5ccac2d68aee6`.
4. Red proof by hand, restored byte-identical after each: unwiring `commit()`
   took two route-level tests red, unwiring `image()` took a third.

### The four documentation pieces

1. `docs/operating.md` (#1158): read live state, audit a publish, the labels,
   the notifier, and the deploy command with the stamp. Only the remainder
   `docs/if-it-is-down.md` did not already carry; it cross-references rather
   than restating.
2. `docs/screen-field-map.md` (#1157): a wrong on-screen value to the function
   that produced it, in four steps, keyed on names rather than line numbers.
3. README cut from 559 lines to 119 (#1159).
4. The doc reconciliation closed as superseded (#1160): ANNEALING E4 struck,
   SPEC-GAP-REGISTER shortlist item 1 struck, and a header on the v2 spec
   saying it is the design for a different product.
5. Backlog item 120 (#1163) and the p1 status roll-up (#1168) record what
   shipped, what stays open, and whose call each open piece is.

### Verification that went beyond the suite

1. Drove the real consumer of the changed payload: `tools/recon_uptime_probe.py`
   against the live app returned api/mx/spa all OK, exit 0.
2. Established the SPA reads `/healthz` nowhere (0 references across all five
   bundles), so its drive is the did-the-deploy-break-the-screen check rather
   than an assertion about the new field.
3. Drove the SPA cold in a headless Chrome, logged in through the real input
   and button, and read back all 7 months with real receipt counts, matching
   the API's count exactly and with no fallback strings.

---

## Key Decisions Made

### Build identity arrives as a build arg, not a file or a fly.toml entry

- **Choice:** Dockerfile `ARG GIT_COMMIT` baked to `ENV`, plus `FLY_IMAGE_REF`
  read at runtime.
- **Rationale:** the item's bar was that it must not silently go stale. A
  `fly.toml` `[build.args]` entry or a `VERSION` file is exactly the thing
  somebody forgets to edit. A value baked into the image travels inside the
  artifact, and `image` names that artifact, so the two cannot disagree.

### Nothing else added to `/healthz`

- **Choice:** commit and image only.
- **Rationale:** it is Fly's health-check target on a 5s timeout, so every
  field must be a pure env read that cannot throw or block. A DB count or
  queue depth would touch SQLite on the same volume `/healthz` exists to
  report on filling up, turning a probe into a restart loop precisely when it
  is needed.

### The doc reconciliation is closed, not done

- **Choice:** strike E4 and register item 1, put a header on the spec, do not
  rewrite it.
- **Rationale:** the v2 spec is not a stale description of this program, it is
  the design for a different one (multi-tenant SaaS on Firebase, Anthropic
  Claude, mobile capture), descoped 2026-05-27. Rewriting 66 KB of it to match
  a tool several hundred commits past it would create a second document
  claiming to describe the build, which is the failure E4 records.

### The commit column on `client_errors` was left open rather than half-done

- **Choice:** document the gap in the test and the docstring; do not migrate.
- **Rationale:** it is a schema migration on the live database holding Criss's
  months, and item 120 asks only for the endpoint. Scope belongs to the owner.

---

## What Did NOT Work (and why)

- **A `just deploy` recipe wrapping the build arg:** written, then cut. `just`
  is not installed on this machine, so the recipe could not be run even once,
  and an unrun command in an emergency runbook is the exact failure the work
  is meant to remove. The raw command went into `docs/operating.md` instead,
  with its clean-tree guard differential-probed.
- **The field map's first scoped-search helper:** `awk -v fn="^def $1\\("`
  consumed the escape, leaving an unbalanced paren, so awk aborted. Worse, its
  failure printed nothing, which is indistinguishable from a correct empty
  result. Rewritten to literal `index()` matching.
- **The final README-pointer verification:** `MSYS_NO_PATHCONV=1 git -C /c/...`
  broke the `-C` path, so `git cat-file -e` reported all ten pointer files
  MISSING when every one exists. The negative was an artifact of a blind
  instrument.
- **Playwright MCP on :9222:** timed out; a sibling session holds the user's
  Edge.
- **`agent-browser --session i120 --executable-path <chrome> open`:** never
  returned, backgrounded, after 180s. This is the documented 2026-09-17 remedy
  for exactly this situation and it did not hold.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/machine.py` | Modified | `commit()`, `image()`, both in `snapshot()` |
| `.../expense-reconciliation/Dockerfile` | Modified | `ARG GIT_COMMIT` to `ENV EXPENSE_RECON_COMMIT` |
| `.../expense-reconciliation/tests/test_client_error_probe.py` | Modified | 5 route-level tests; key-set contract widened |
| `.../expense-reconciliation/docs/operating.md` | Created | Deploy, roll back, live state, publish audit, labels, notifier |
| `.../expense-reconciliation/docs/screen-field-map.md` | Created | Wrong on-screen value to the function that made it |
| `.../expense-reconciliation/README.md` | Rewritten | 559 lines to 119, cut to what is true |
| `.../expense-reconciliation/ANNEALING.md` | Modified | E4 closed as superseded, original kept in a details block |
| `.../expense-reconciliation/SPEC-GAP-REGISTER.md` | Modified | Shortlist item 1 closed |
| `.../specs/1-spec/p1-expense-reconciliation-functional-spec.md` | Modified | Header: this is the original design, not what runs |
| `.../brisken/status/p1-improvement-backlog.md` | Modified | Item 120 records the shipped half |
| `.../brisken/status/p1-expense-reconciliation.md` | Modified | Element row extended; stale live-UI address fixed |
| `memory/feedback_agent_browser_named_sessions.md` | Modified | The raw-CDP path that works when both wrappers hang |

---

## Current Status

All eight PRs merged (#1156 to #1160, #1163, #1168). Fly v195 is live carrying
`640be61b`, which is still the last commit touching `src/`; everything merged
after it is documentation, so no redeploy is pending. Live health at last
read: status ok, disk 78.8% free, intake not refusing.

brisken platform: unknown plan, ops/mo not assessed. `infrastructure.yaml` has
no assessment date for this client, so a feasibility assessment is outstanding.

Two `status/` files are stale and belong to p2, not this session's scope:
`p2-product-decks.md` (60d) and `p2-targeting.md` (61d). Deliberately not
touched, because bumping them without doing the work would invent progress.

---

## Next Steps

1. Turn on the SharePoint backup: `EXPENSE_RECON_BACKUP` is still absent from
   the nine deployed secrets, so the only copies of Brisken's data are the live
   volume and Fly's 5-day snapshots, both inside the developer's personal
   account. Owner-gated (it restarts the live app and starts writing to their
   tenant), so prepare the readiness evidence read-only first, then put the
   decision with a recommendation.
2. Stop the notifier running from a checkout 283 commits behind `origin/main`.
   Do not add a `git pull` to the scheduled task: that clone is the shared
   working tree several sessions use.
3. Add a `commit` column to `client_errors` so a historical failure ties to a
   build. Live-DB migration; existing rows must read empty, never back-filled.
4. Run `/ops-audit brisken` or record a platform assessment, since
   `infrastructure.yaml` has neither plan nor ops figures for this client.
5. Log the Brisken comms conversations of the last 13 days.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/if-it-is-down.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 120, and 121 for the notifier)

### Open Questions

- Does the owner want the SharePoint backup switched on now, given the restore
  has never been rehearsed? Switching it on and rehearsing a restore are
  separate decisions and the first does not depend on the second.
- Is the narrow notifier fix worth shipping when item 121 proposes moving the
  notifier into the app entirely?

### Working Notes

- **The API is not behind Cloudflare.** `brisken-expense-recon.fly.dev` answers
  200 to plain `urllib` with no UA, probed three ways.
  `expenses.brisken.com` IS behind Cloudflare and 403s without a browser UA.
  The session brief attached the caveat to the wrong host.
- **`service.py` is 15,408 lines**, and item 120's evidence block quotes line
  counts as if they were offsets: `build_view` is at 3219 (1162 lines), not
  952. `build_expense_view` :7208, `build_expense_report` :8298,
  `rematch_month` :12874.
- **There is no publish log.** `published_by` / `published_at` /
  `published_override` are current state; unpublish clears all three and
  publishing writes no decision-history entry. And no month has ever been
  published: `published_runs` was empty across all 7.
- **Live state 2026-09-20:** 7 months, 0 published, 0 processing, 36 re-match
  events, 72 feedback notes.
- **`--extra web` is not optional** when running the module suite: without it
  the web tests `importorskip` and SKIP while the run still reports success.
  Suite is 2714 passed, 2 skipped.
- **`test_drop_speed_item_148.py::test_parallel_beats_the_serial_wall_clock`
  is a wall-clock flake** (asserts < 0.7s, saw 1.25s on a loaded runner). It
  was the only red check on the README PR, which touches no code; it passed on
  rerun.
- The working browser path when both wrappers hang is in
  `feedback_agent_browser_named_sessions`: own headless Chrome on :9333, raw
  CDP, `suppress_origin=True` on the websocket.

### Reference Materials

- `https://brisken-expense-recon.fly.dev/healthz` (no auth, no UA needed)
- PRs #1156, #1157, #1158, #1159, #1160, #1163, #1168

---

## How to Continue

The three open items each have a shape and a gate. Task 3 above (the
`client_errors` column) is pure code and needs no permission. Task 2 is a local
scheduled-task change whose only real risk is disturbing the shared clone.
Task 1 is owner-gated and the preparation is entirely read-only, so do all of
it, then ask once with a recommendation.

---

## Strategic Feedback

### What Worked Well This Session

- Checking the brief before building against it. Three of its claims were
  wrong, and two of them (the `service.py` offsets, the Cloudflare host) would
  have been copied into a stand-in's documentation as fact.
- Running the documentation's own commands verbatim out of the finished
  markdown. That is what caught the broken search helper, which the unit tests
  could never have seen because it lives in prose.
- Probing `FLY_IMAGE_REF` on the live machine before designing around it,
  rather than assuming what Fly injects.

### Suggestions

- The two blind-instrument near-misses this session both had the same
  signature: a probe returning empty, where empty was also what a broken probe
  returns. A cheap structural fix is a convention rather than a hook: any
  command whose ABSENCE of output is the evidence gets a known-present control
  in the same call. I wrote that convention into `screen-field-map.md` for its
  own helper; it generalizes.

### System Health

- Autonomy: 0 corrective human interventions. The two "continue" messages were
  nudges after I ended turns, not corrections.
- Gates: B1:0 B2:6 B3:1 skipped:0.
- The friction register is 318 KB and the archiver can only move 3 rows,
  because the remainder is unresolved. The file is growing faster than
  resolution, which will eventually make the regression check at checkpoint
  time unreliable.
