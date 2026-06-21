---
project: brisken
workstream: p2-onepilot-site
group: lead-generation
spec: p2
state: active
updated: 2026-06-20
general_ref: status/p2-lead-gen-general.md
---

# Brisken / OnePilot site (p2)

The OnePilot marketing site prototype and its positioning assets. The OnePilot
*vision* itself is shared context (in `status/p2-lead-gen-general.md`); this
workstream is the concrete site build, blueprints, and review assets.

The prototype is hosted for internal review (pre-Dirk) at
brisken-onepilot-proto.fly.dev behind a name page (no access code, just share the
URL); feedback writes to JSONL on the Fly volume
(`project_brisken_onepilot_site_hosting` memory).

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Site prototype | in-progress | Spine + corrected band/SOC; internal review pre-Dirk | Incorporate review feedback | Dirk hierarchy decision | `deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html` |
| Hosting (name-gated Fly) | live | brisken-onepilot-proto.fly.dev serving | none | none | `onepilot-site/` (FastAPI) |
| Website blueprint | done | Build blueprint written | none | none | `deliverables/lead-generation/onepilot/brisken-onepilot-website-blueprint.md` |
| Revision blueprint | done | §8 repositioning landed | Apply once hierarchy decided | Dirk hierarchy decision | `deliverables/lead-generation/onepilot/brisken-onepilot-revision-blueprint.md` |
| TreasuryCentral restyle | in-progress | Restyle blueprint staged | Cut once hierarchy decided | Dirk hierarchy decision | `deliverables/lead-generation/onepilot/brisken-treasurycentral-restyle-blueprint.md` |
| Review sign-off | done | Short sign-off sheet for Dirk | Walk Dirk through | Dirk review | `deliverables/lead-generation/onepilot/brisken-onepilot-review-signoff.md` |

## Open decisions / gates

- TreasuryCentral / OnePilot hierarchy (umbrella with OnePilot as the AI layer
  inside, or peers). Gates the site re-cut. Copy is built to the nested model and
  is one-edit reversible. Do NOT re-skin the OnePilot-as-platform assets until answered.

## Pointers

- Deliverables: `deliverables/lead-generation/onepilot/`
- Positioning memo: `deliverables/brisken-onepilot-positioning-memo-dirk-2026-06-20.pdf`
- Host: `onepilot-site/README.md`
