---
project: brisken
workstream: p2-product-decks
group: lead-generation
spec: p2
state: dormant
updated: 2026-09-24
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Product decks (p2)

The OnePilot / TreasuryCentral deck estate and the engine that builds it
(`automations/lead-generation/deckgen/native/`, standard in `deckgen/DESIGN.md`).
Build history and provenance live in `deliverables/product-decks-redesign/CHANGELOG.md`,
`deliverables/tc-overview-redesign/` and git; this file is current state only.

**Dormant since 2026-07-27.** Read off SharePoint on 2026-09-24 (Graph, app-only,
`MARKETING/.../OnePilot - Cloud Solutions Presentations/2026_PPTX`): nothing we
uploaded has been touched since 07-27; `Brisken Product Assets` is unchanged since
07-14, so none of the NEW product decks was ever swapped in; and Dirk has taken the
Overview into his own hands (details in the table). Picking this back up starts with
asking Dirk which Overview is canonical now, not with another build.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Overview (TreasuryCentral Solutions) | owner-held | Dirk's own line since late July: `Dirk - Brisken - TreasuryCentral Solutions Overview 2026-07-27.pptx` (Asset Testing/TreasuryCentral Solutions, 07-29), then `...Overview-Classic_2026.pptx` (08-27) and `...Overview GOLDEN COPY.pptx` (08-31) at the `2026_PPTX` root. He moved `...Overview 2026.pptx` to Archive 08-01 and marked our 07-21 NEW deck and the PROPOSAL pair "(Outdated)" | Ask Dirk whether GOLDEN COPY is the canonical Overview the product decks should now match | Dirk | SharePoint `2026_PPTX/` root |
| Market Data Hub NEW (13 sl) | stalled | In Asset Testing since 07-23, untouched; Product Assets still holds `Market Data Hub 2026-07` (07-09) | Dirk per-deck pick, re-based on the GOLDEN COPY if he wants the family to match | Dirk | `Asset Testing/NEW - Brisken - Market Data Hub 2026-07-23.*` |
| MDH Commodities NEW (10 sl) | stalled | Same; Product Assets holds `Market Data Hub Commodities 2026` (07-09) | Same | Dirk | same folder |
| Smart Trading NEW (11 sl) | stalled | Same; Product Assets holds `Smart Trading 2026` (07-11) | Same | Dirk | same folder |
| Digital Co-Worker NEW (14 sl) | stalled | Same (pptx re-uploaded 07-24); Product Assets holds `Digital Co-Worker 2026-07` (Dirk, 07-14) | Same | Dirk | same folder |
| 07-27 logo-wall rebuilds | unshipped | All five rebuilt with per-prospect transparent logo sets as `NEW - ... 2026-07-27`, never uploaded (owner-gated); Tradeweb/ICD logo unsourced | Only worth uploading once the Overview question is settled | Dirk + owner | `deckgen/native/logosets.py`; memory `project_brisken_product_decks_restructured` |
| MN- / PROPOSAL leftovers | stale | 8 `MN - ... 2026-08 PROPOSAL` files (07-21) + `MN - ... Overview 2026-07-21` still in Asset Testing | Tidy with Dirk's word when the folder is next touched | Dirk | `Asset Testing/` |
| Prospect decks (Sanofi, Zalando) | as-shipped | `Client Deliverables/Sanofi` (Dirk edited pptx 07-19), `/Zalando` (07-11); old pipeline | Rebuild on the new standard only if a prospect needs one | none | `2026_PPTX/Client Deliverables/` |
| Build system (native v3) | done | Overview regression 121/121 parts identical; DS token parity gate (07-29); CI `deckgen-native-tests.yml` | None until the deck work restarts | none | `deckgen/native/`, `deckgen/DESIGN.md` |

## Open with Dirk

1. Which Overview is canonical now (GOLDEN COPY?), and should the four product decks follow it.
2. Per-deck pick and swap into Product Assets (runbook in `deckgen/README.md`, never executed).
3. Asset Testing tidy (MN-/PROPOSAL/Outdated files).
4. Carried from July: BTP wording opt-in; ring graphic needs his source art;
   success-story expansion waits on his consultant-interview mechanism.
