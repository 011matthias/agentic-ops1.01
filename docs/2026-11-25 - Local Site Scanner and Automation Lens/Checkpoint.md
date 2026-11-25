# Checkpoint: Local Site Scanner and Automation Lens

**Date:** 2026-11-25
**Status:** Tool live on main (PRs #1782, #1807); Karlsruhe lists generated; cashflow work not started

---

## Summary

Trialled `ethanplusai/sellbird` (ex-Harvey) no-send on Karlsruhe and did not adopt it; on the owner's choice built our own prospect finder, `tools/local_site_scan.py`, with a website lens (build offer) and an automation lens (automation offer). Next session turns the two Karlsruhe lists into paid work.

---

## What Was Done This Session

### Sellbird trial (2026-11-19)
1. Ran its prospecting half on Karlsruhe in a scratch clone, email off, OSM source, 14 trades patched in: 1,031 businesses, 591 sites profiled, EUR 0.
2. Measured why it does not fit Germany: fit score is email reachability (878 of 1,031 tied at 20-25, top two picks from "& Partner" read as a title); booking detector US-only (10-21 of 50 sampled "no booking" flags wrong); unreachable sites leave no record; its summary said "14 of 14 queries" when 7 failed; OSM missing `website` tag read as no website (Beauty Lounge, Wesch have sites).

### local_site_scan.py (PR #1782, 2026-11-19)
1. OSM list (one Overpass query, three mirrors, backoff, partial/empty answers are errors) + per-site check: DNS gone behind a control lookup, HTTP errors, invalid certificate, parked/placeholder/spam, mobile-readiness, footer year, JSON-LD, German booking vendors, Impressum owner. No email addresses collected.
2. Live Karlsruhe: 923 businesses, 67 dead or broken (28 domains gone), 62 weak; demos landed as expected (Aras server_error, Dr. Wo ssl_broken, Lenk/Uslu/Helmle weak).

### Automation lens (PR #1807, 2026-11-25)
1. `--lens automation`: admin-heavy trades (9 new OSM tags, each counted live) ranked by phone-only booking, fax, printable PDF forms, office-role job ads, callback, WhatsApp/Forms intake, software in use (HERO highest).
2. Guards from the first live run: job-ad context for roles, Arzt/Zahnarzt/Physio out of the default, OSM brand-tagged chains labelled apart, duplicates merged by website.
3. Overpass fixes for the whole tool: the tool's own user agent, one empty answer = server failure.
4. Live Karlsruhe: 522 businesses, 10 strong fit, 90 some signals, 63 chains; top 100 = Kfz 21, Fahrschule 20, Steuerberater 14, Kanzlei 12, Tierarzt 8, Hausverwaltung 8, Versicherung 7.

---

## Key Decisions Made

### Build our own scanner, not Sellbird
- **Choice:** Owner picked "Build our own scanner" (AskUserQuestion, 2026-11-19).
- **Rationale:** Sellbird's ranking and signals are US/email-shaped; the useful residue (OSM list + site check) is small to own.

### Patient trades out of the automation default
- **Choice:** Arzt, Zahnarzt, Physio only via `--trades` in the automation lens.
- **Rationale:** Their intake is Art. 9 / § 203 StGB data; the uwi voice-line verdict keeps them website-only. They filled 44 of 56 strong fits in the first run.

---

## What Did NOT Work (and why)

- **Sellbird as a demo-target feeder:** fit score measures email reachability, not website need; demos ranked 147-984 of 1,031, none in its top 100.
- **Browser or curl user agent to overpass-api.de:** 406 Not Acceptable since at least 2026-11-25; a tool-named agent gets 200.
- **kumi.systems for area queries:** answered 200 with zero for every tag (plumber 0 vs overpass-api.de 12); radius queries on the same server were correct.
- **Office-role match without job-ad context:** 132 of 576 sites flagged "hiring" from team pages naming an MFA; with context 33 of 286.
- **Pattern `medizinischefachangestellt`:** the title is two words, so "Medizinische Fachangestellte" never matched; caught by the new team-page test.
- **regress_check on `if lens == "automation":`:** matched twice and was refused; mutated the unique `automation_signals` call instead.
- **Background run redirected into `.scratch/` of a fresh worktree:** the folder did not exist, the run failed before starting.
- **Tax-advisor live check of the timeout retry:** sat 13+ min in Overpass backoff on pre-retry code; stopped, the retry is covered by a test seen red.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/local_site_scan.py` | Created, extended | Prospect finder, two lenses |
| `tools/tests/test_local_site_scan.py` | Created | 41 network-free tests |
| `tools/INDEX.md` | Edited | Tool row |
| `workspace/projects/upwork-independence/status/uwi-general.md` | Edited | Prospect-finder pointer |
| memory `project_upwork_independence_two_routes.md` | Edited | Sellbird verdict, scanner, Overpass gotchas |

---

## Current Status

Both PRs merged (da837a78, 66c959a0). Lists (gitignored, owner names): `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-sitescan\.scratch\local-site-scan\karlsruhe-2026-11-19.csv` (website) and `karlsruhe-automation-2026-11-25.csv` (automation). upwork-independence: no infrastructure.yaml, no comms log. No prospect has been contacted from these lists.

---

## Next Steps

1. Turn the lists into paid work: pick 10 (5 website, 5 automation), hand-verify each, build demos and first letters for owner review (continuation prompt below).
2. Owner decision D3: automation package prices (u9 status; anchors care EUR200, licence EUR600, tiers 650/1,850).

---

## Context for Next Session

### Files to Read First
- `workspace/projects/upwork-independence/context/monetization-strategy.md`
- `workspace/projects/upwork-independence/status/uwi-general.md`
- `workspace/projects/upwork-independence/context/icp.md`
- `tools/local_site_scan.py` (module docstring)

### Open Questions
- Automation entry offer and price (D3).
- Who prints and posts letters, and per-letter cost approval (postal is approved per item).

### Working Notes
- No Karlsruhe trade site shows HERO; the u9 channel cannot be fed from this scan.
- "Kanzlei Wangler" carries an OSM brand tag and lands in the chain bucket; data quirk, not a tool bug.
- Owner names: 203 of 482 working sites (website lens); spot-checks matched the Impressum, including outdated map names (Esswein practice now OrthoDocs).

### Reference Materials
- PR #1782, PR #1807
- `workspace/projects/local-web/prospects/` (demo workflow), `workspace/projects/local-web/GESPRAECHSLEITFADEN.md`

---

## How to Continue

Paste the continuation prompt below into a new Claude Code chat.

````markdown
/comd_resume upwork-independence

Goal of this session: turn the new local prospect lists into paid work, on the shortest path to first invoices, inside the committed uwi strategy. Nothing is sent, printed or posted without my explicit per-action yes.

## Where it stands (2026-11-25)
- `tools/local_site_scan.py` is on main (PR #1782 website lens, PR #1807 automation lens). It lists a town's businesses from OpenStreetMap and reads each website.
  - `--lens website` (default): dead, broken and weak sites, for the EUR1,225 build + EUR200/mo care offer. Karlsruhe 2026-11-19: 923 businesses, 67 dead or broken (28 domains gone), 62 weak.
  - `--lens automation`: admin-heavy trades ranked by manual back-office signals (phone-only booking, fax, printable PDF forms, office job ads, callback requests, WhatsApp/Forms intake, software in use). Karlsruhe 2026-11-25: 522 businesses, 10 strong fit, 90 some signals, 63 chains set apart. Top 100: Kfz 21, Fahrschule 20, Steuerberater 14, Kanzlei 12, Tierarzt 8, Hausverwaltung 8, Versicherung 7.
  - Arzt, Zahnarzt and Physio are deliberately out of the automation default (patient data, Art. 9 / § 203 StGB); they stay website-only.
  - No Karlsruhe trade website shows HERO, so the u9 HERO channel cannot be fed from this scan.
- The lists are gitignored (they hold owner names): `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-sitescan\.scratch\local-site-scan\karlsruhe-2026-11-19.csv` (website) and `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-sitescan\.scratch\local-site-scan\karlsruhe-automation-2026-11-25.csv` (automation). If they are gone, regenerate with `uv run tools/local_site_scan.py --area Karlsruhe` and `--lens automation`; the free map servers throttle, and a run can wait about 30 minutes before it stops with an error.
- Demo-first is the active channel. Cold email is retired (UWG §7). Postal and print are approved per item. Demo workflow: Lovable one-pagers with sourced facts in `workspace/projects/local-web/prospects/`; conversation guide `workspace/projects/local-web/GESPRAECHSLEITFADEN.md`.

## What to do
1. Read first: `workspace/projects/upwork-independence/context/monetization-strategy.md`, `workspace/projects/upwork-independence/status/uwi-general.md` (decisions and hours ledger), `workspace/projects/upwork-independence/context/icp.md`, and the memories `feedback_prospect_letters_and_pdfs.md`, `feedback_client_comms_tone.md`, `project_upwork_independence_two_routes.md`.
2. State the current position against the strategy's revenue floor, sourced from the repo; TBD where there is no source.
3. Recommend ONE plan for the shortest path to first invoices from these two lists, with a weekly cadence that fits the hours budget in uwi-general. Cover: the first 10 businesses (5 website, 5 automation) and why each; what each gets (website: a demo one-pager; automation: one concrete mini-demo built on what their own site shows, for example their PDF form turned into an online form that files itself); the entry offer and price (website terms are decided; automation package prices are open owner decision D3, so put your recommendation and its consequence to me with AskUserQuestion); the channel (a postal letter with the demo link, per feedback_prospect_letters_and_pdfs: no prices in the first letter, name the gap, show the demo, ask for a meeting); and how outcomes get logged.
4. Hand-verify each of the 10 before any work on it: still trading, owner name from the Impressum, and the signals true on the live site today. The lists are clues, not proof.
5. After my go: build the first demos and letter drafts for my review.

## How to work
- Use your own worktree off origin/main (`git worktree add -b uwi/<name> ../agentic-ops1-<name> origin/main`); sibling sessions are live on main.
- Project files only under `workspace/projects/upwork-independence/` and `workspace/projects/local-web/`. Prospect data with personal names stays gitignored (`.scratch/` or a `context/` folder); the repo is public.
- Every fact in a letter or demo comes from the business's own site (B4); TBD beats a guess.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume upwork-independence`; where it stands (what shipped this session with PR numbers, what is in flight and why, what waits on the owner); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any other paste-ready prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty, do not write another prompt: say the loop is done and list what shipped and what waits on the owner.
````

---

## Strategic Feedback

### What Worked Well This Session
- Defining expected outcomes before each live run (Aras server_error, Dr. Wo ssl_broken, Wesch no website) made the runs checkable, and reading the first automation output critically caught three ranking errors before they shipped.

### Suggestions
- Add a `--top N` export of the strongest rows with a fixed column set for letter work, so the next session does not re-filter the CSV by hand.

### System Health
- The session-header skip recurred (fourth row since 2026-11-09); the documented fix has not held and the Stop-event header check stays unbuilt. Autonomy: 0 corrections; 2 owner decisions via AskUserQuestion.
