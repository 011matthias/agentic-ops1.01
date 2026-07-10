# Checkpoint: Brisken OnePilot Map Polish + Hours Log

**Date:** 2026-06-18
**Status:** Prototype shipped live to the gated Fly host; lead-gen hours logged through 2026-06-18.

---

## Summary
Iterated the Brisken OnePilot marketing-site prototype (the `#map` section and hero CTA) through four reviewer-driven changes, deployed the full accumulated stack to `brisken-onepilot-proto.fly.dev`, and logged the website-redesign arc into the Lead Generation hours sheet.

---

## What Was Done This Session
### Prototype (`#map` + hero)
1. **Why-now node** — folded the standalone S/4HANA "Why now" section into the map as a 7th node: a dashed question-mark pill centered below the branch row, opening the same blurred grow-from-node popup as the other nodes. Wired as tier 7 (TIERS + label + locator chip); old section removed so the id stays unique.
2. **Uniform branch nodes** — the four OnePilot branches (MDH, Smart Trading, Remittance Gate, SAP) fixed to one size (190x98).
3. **Rounder buttons** — `.btn` radius 2px -> pill.
4. **No dividers below the map** — removed the top-border on every section under `#map` (`#demo`/`#proof`/`#faq`/`#feedback`) plus the internal report/qa-list lines there.
5. **Comparison table into the popup** — moved "OnePilot vs the usual paths" out of #answers and into the Why-now panel.
6. **Removed the always-on bottom-right pill**; the **hero "Book a demo" now carries down on scroll** (fixed clone fades in, scales to 1.06, docked above the Feedback FAB; hides at top; reduced-motion drops the scale; print hides it).

### Deploy
7. Synced the deliverable into `onepilot-site/site/index.html` and `flyctl deploy`-ed (user-authorized). Verified the live origin by passing the name gate (server-signed cookie) and confirming new markers present (`float-demo`, `data-tier="why-now"`) and old pill gone, brand title flipped to TreasuryCentral.

### Hours
8. Logged the full redesign arc (`7c7cf17..HEAD`, 13 commits) into the **Lead Generation** sheet of `workspace/hours-tracker.xlsx` as 3 rows (6.0h / EUR 84), in the free early-morning slot, then sorted the table chronologically.

---

## Key Decisions Made
### Carried-down hero CTA implemented as a clone, not a moved element
- **Choice:** keep the hero button in flow; add a fixed clone that reveals on scroll past it (IntersectionObserver).
- **Rationale:** zero layout shift in the hero, smooth fade/scale, and the reviewer's dblclick ignore-list already covers `<a>`. Moving the real element would reflow the hero and fight the lock between in-flow and fixed.

### Hours logged at detailed granularity, early-morning slot
- **Choice:** 3 rows (~6h) for the arc, at 02:00-08:00 where the commits actually landed (user picked "detailed" over consolidated/skip).
- **Rationale:** 2026-06-18 was already logged ~12.5h (r19-r24, the lead-gen engine + Rome track), and the early hours were free; surfaced the day-total because it is billing data.

### Wrote to the live Excel via COM, did not force-close it
- **Choice:** append via `ListObjects.ListRows.Add` on the open workbook (BindToMoniker), not openpyxl.
- **Rationale:** the file was open and concurrently edited (rows 21-24 had just appeared); a plain openpyxl save would have clobbered them. COM appends merge with the live session and auto-propagate the Hours/Earnings formulas.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` | Modified | Why-now node, uniform nodes, pill buttons, no dividers, table-into-popup, carried-down CTA (commits 2676afc, d6866f3, a619dcb) |
| `workspace/clients/brisken/onepilot-site/site/index.html` | Synced (gitignored) | Deploy artifact for Fly |
| `workspace/hours-tracker.xlsx` (`Lead Generation`) | Modified via COM | 3 rows for the redesign arc; table A7:H27; sorted |

---

## Current Status
- Live: `https://brisken-onepilot-proto.fly.dev` serves the latest build (verified through the name gate). Pre-Dirk internal review host.
- Branch `client/brisken/lead-gen-onepilot` is pushed through a619dcb (PRs not opened by design; the gated Fly deploy is the real publish).
- Hours: Lead Generation sheet total 44.75h / EUR 626.50, all billable, control check ties.
- Platform (`infrastructure.yaml`): brisken `tier: unknown` — custom SaaS (OnePilot), not a workflow-engine op count, so no ops audit applies.

---

## Next Steps
1. Hand the live prototype URL to Dirk for review (the double-click feedback host captures notes server-side).
2. Apply remaining Dirk prototype notes when inputs arrive: booking link (#4), research-paper URL (#5), more SharePoint logos (#6).
3. Fix `tools/sync-hours.py` — it is stale (expects a single `Log` sheet; the tracker is now per-engagement sheets `Timesheet` + `Lead Generation`), so the git-driven auto-logger crashes.
4. Lead-gen engine remains gated on Dirk's go-live sheet decisions + the who-drives-seat call (unchanged from earlier sessions today).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` — the live prototype
- `workspace/clients/brisken/onepilot-site/sync-site.py` + `fly.toml` — deploy path
- `workspace/hours-tracker.xlsx` (`Lead Generation` sheet) — hours state
- `~/.claude/.../memory/reference_repo_tooling_gotchas.md` — flyctl token gotcha (see below)

### Open Questions
- None blocking. Dirk notes #4/#5/#6 await client inputs.

### Working Notes
- **flyctl token:** `flyctl` does not auto-load its token in this Git-Bash shell ("no access token available") even with a valid token in `~/.fly/config.yml`. Pass it explicitly: `export FLY_API_TOKEN="$(grep 'access_token:' ~/.fly/config.yml | sed -E 's/.*access_token:[[:space:]]*//' | tr -d '"'"'"' ')"` then `flyctl deploy`. Documented in `reference_repo_tooling_gotchas.md` (2026-06-17) — I rederived it (friction below).
- **Hours tracker is often open in Excel.** Writing via openpyxl fails with PermissionError when it is. Use COM (`BindToMoniker(path)` -> `ListObjects("LeadGenLog").ListRows.Add()`), which works on the live workbook, auto-extends the table, and propagates calculated-column formulas. Setting a long string via `.Value2 = $var` threw `InvalidCastException` in PowerShell COM; assigning a literal string worked. The sheet rebuild split it into `Timesheet` (expense-recon) + `Lead Generation`, each its own `HoursLog`/`LeadGenLog` table with structured-ref overview totals.
- **Near-miss caught:** the first openpyxl save would have overwritten live rows 21-24; the OS lock blocked it, and a re-read (triggered by a table-ref discrepancy A7:H24 vs the A7:H20 seen earlier) surfaced the concurrent edit before any damage.

### Reference Materials
- Live host: https://brisken-onepilot-proto.fly.dev
- Commits: 2676afc, d6866f3, a619dcb on `client/brisken/lead-gen-onepilot`

---

## How to Continue
The prototype is live and current. Next real action is Dirk's review (URL handoff) and applying his outstanding notes as inputs arrive. For any further deploy, use the FLY_API_TOKEN export above. For hours, write via COM while the tracker may be open.

---

## Strategic Feedback

### What Worked Well This Session
- Tight directive loop on the prototype: each reviewer request was restated, built, Playwright-verified (geometry + behavior + annotation contract), and shown back before the next. No rework.
- The hours-logging pause was the right call: re-reading on the table-ref discrepancy caught a live concurrent edit that would otherwise have been overwritten.

### Suggestions
- The hours tracker is now actively edited by hand and by concurrent sessions while open in Excel. A small `tools/log-hours.py` that appends via COM (the pattern used here) would remove the openpyxl-vs-lock hazard and replace the broken `sync-hours.py`.

### System Health
- `tools/sync-hours.py` is dead against the current tracker schema (per-engagement sheets). The "canonical automation" for hours no longer runs; logging is manual. Worth either fixing or formally retiring.
- Autonomy score: 2 human interventions this session (both agent/hook self-caught: one missed-memory-recall, one B1 deferral; zero user redirects). The user's one input (hours granularity) was a legitimate billing decision, not a correction.
