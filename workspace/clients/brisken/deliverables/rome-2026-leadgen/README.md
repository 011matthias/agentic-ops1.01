# Rome 2026 lead-gen: parallel-session output (July 2026)

What six parallel lead-gen sessions produced for the Rome / TA Cook 2026
push, salvaged 2026-08-25 from the `leadgen/task-*` branches, which were
the only place most of it existed.

| Folder | What it holds |
|---|---|
| `leadgen-task-2` | Zalando: TreasuryCentral deck (.pptx), call brief, demo flow, collateral pack |
| `leadgen-task-3` | Sanofi: deck (.pptx), BTP one-pager, collateral pack (3 PDFs), call-prep brief |
| `leadgen-task-4` | Contact-master audit: designation scheme, board-rename proposal, open questions for Dirk |
| `leadgen-task-5` | Tier-2 roster (.csv), segmentation, LinkedIn / Sales Navigator runbooks |
| `leadgen-task-6` | Calvin forwardable clip: brief, production runbook, rendered masters (v3) |
| `leadgen-task-7` | Tier-3 roster (.csv), resolved profiles, the same runbooks for T3 |

## Provenance, and two things to know before using it

These were written to `output/` at the repo root, which is not a home the
file-placement standard recognizes, so they never merged; only task-6 had
partly reached main. This folder is the consolidation: the whole set now
sits in one sanctioned place and the stray root `output/` is gone.

**task-6 here is NEWER than what main carried.** Main held the 2026-07-11
version (PR #207); this is the 2026-07-14 "Calvin clip v3" (10s intro
overview card, 100s silent masters) built to Dirk's direction that day.

**The rosters are a July snapshot, not live contact state.** The Rome
master contact sheet in SharePoint (`30_Events/TA Cook 2026`) is the
source of truth for who was contacted and what their tier is; these CSVs
record what each session resolved at the time. Read them as a record of
that work, and never as the current list.

Not salvaged, deliberately: sixteen other files that these branches also
carried but main had since DELETED on purpose (the Jinja review UI,
superseded by the Lovable SPA at v31; `zoho/client.py`, from the
2026-08-22 cut-every-tie-to-Zoho directive; the meji corporate-sample
page removed in PR #192; and the smart-trading deck retired by the TC
story alignment). Restoring those would have undone live decisions.
