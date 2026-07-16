# Continue-Prompt: One Assessment roadmap (paste into a fresh chat)

---

We are continuing the **One Assessment** treasury-assessment tool
(`workspace/clients/Jochen Projekt/automations/treasury-assessment/`,
FastAPI inline-HTML app + a Python pipeline package, deployed to Fly as
`one-assessment-demo`, live at `one-assessment-demo.fly.dev`). The whole
`Jochen Projekt` tree is **gitignored** (ripgrep needs `--no-ignore`; nothing
to commit or PR). The only path to production is `flyctl deploy --ha=false`
from `site-host/`, and **every deploy waits for my explicit "deploy"**. The
registry, feedback log, resolutions, showcases and per-submission data live on
the persistent `/data` volume and survive deploys. `render.py` changes reach
the demo only via re-render + showcase republish (a separate volume write, also
gated).

**Read first:**
`docs/2026-07-15 - One Assessment Workshop Channel + Feedback Resolution/Checkpoint.md`
(current state), `DESIGN.md` §8–§15 (the roadmap + build-state table),
`PIPELINE-NOTES.md` §N/§O/§P, `FEEDBACK-REGISTER.md`.

**Where we are.** The three data sources Jochen requires are: (1) the
Fragebogen, (2) the client's uploaded documents, (3) what we compile with the
client in workshops. Source 1 is live. Source 3 (workshop) shipped this round
as a full channel (`oa-workshop/v1`: `cli workshop --template/--push`, merges
into scoring with a separate traceability haystack, honest "aus dem Workshop"
evidence origin, renders in the `#pipe-workshop` stage). **Source 2
(documents) is the gap: uploads are stored raw but never influence the
assessment.** All 6 reviewer feedback items are resolved and marked in-app.

**Your task: drive the tool down its roadmap.** Below is the map grouped by
theme, each item with its definition-of-done from DESIGN.md §15. Pick up the
recommended next thrust unless I redirect. For anything that changes pipeline
logic, scoring, or a client-facing surface, **go into plan mode first** (this
is a large, correctness-sensitive tool), design it, and wait for my go before
building. Then build + verify (pytest + mock E2E + a NextDecade byte-regression
where render changes) and stop at the deploy gate.

## Recommended next thrust: close source 2 (the document channel)

`cli extract --inbox inbox/<id>` → `evidence/` (a `00-facts` file + per-area
verbatim quote files with anchors kept under the probe budget + a
`manifest.json` provenance chain sha256 → extractor → quote), then those
per-area evidence quotes feed the SAME two-source-haystack model the workshop
channel now uses (a third `source_origin = "dokument"`), so a document-sourced
Reifegrad is quotable and honestly labelled "aus den Unterlagen". Doctrine is
already decided (DESIGN §8a "Upload extraction strategy [DECIDED 2026-07-14]"):
markdown/selected-verbatim-quotes operator-side, NO generic file→md flattening,
dispatched typed extractors generalizing `NextDecade/build_intake_md.py` →
tabular schema-summary fallback → LLM-assisted prose/PDF fallback with operator
review. Rationale: this completes "all three sources actually flow into the
assessment", which is Jochen's explicit directive, and it reuses the exact
pattern we just validated for workshops (separate field, separate haystack,
origin label, render sheet). Highest coherence, lowest new-design risk.

## The rest of the map (pick any; I may reprioritize)

**A. Assessment accuracy (biggest trust lever, needs golden data).**
- Mined Reifegrad anchors: per-family (As-Is → golden RG) few-shot exemplars in
  `score_area`. DoD: projection rg_exact rises above the 38% baseline.
- Reifegrad-conditional Stage 3: maturity-banded library index. DoD: a `hoch`
  cell never gets the "manual/fragmented" gap.
- Input-coverage abstention signals: replace the dead 0.6 floor. DoD: flag
  recall well above the ~11% baseline at ≥90% precision.
- Metrics release gate: `cli verify --assert` + committed expected CITTI
  metrics. DoD: a regressing edit exits non-zero.
- German register gate (OPEN): native-register + boilerplate-dedup pass before a
  real client reads a generated As-Is/gap/benefit.

**B. Collection completeness (the "get the whole As-Is efficiently" loop).**
- Multi-channel guided collection: chat / voice / dictation into the same
  structure, pre-classified.
- Document checklist + tracker: predefined wanted docs, per-item have-it /
  won't-give-it.
- Follow-up loop controller: "have I got enough, or run another round" over the
  specific deficient topics; metric is efficiency, not volume.
- Auto-generated probing questions: mostly delivered via `cli workshop
  --template`; generalize it to a standing per-area gap checklist.

**C. Operator workflow + the learning loop (what makes it a managed service).**
- Editable As-Is workbench (open half of Dirk's feedback item 3): show the
  ENTIRE collected As-Is, edit values/comments in place, add/remove documents,
  add ad-hoc topics/info OUTSIDE the fixed TCF spine. Ties to regenerate.
- Operator review triage queue: `review.json` + accept/correct panel. DoD:
  operator clears in-Klärung flags without reading raw JSON.
- Corrections store + versioned anchors: append-only JSONL → `anchors-vN.json`,
  `anchor_set_version` stamped; extend to Priorität.
- Assessment versioning + state stamp: ENTWURF → Experte-geprüft →
  Kunde-bestätigt, with a visible diff.
- Fold-back consumer: ingests the corrections JSONL → tightened anchors +
  questions (the actual learning loop; consumes B/C above).

**D. Client-facing depth.**
- Client verification playback: play the first As-Is (and the workshop memo)
  back to the client to confirm/change. This is the client half of the workshop
  channel we just built; Jochen's memo-check step.
- Gap-to-action (OPEN): from a named gap → its closing action (activities,
  effort, roadmap), even before the implementing automation exists.
- Full tier: detailed questionnaire, more follow-ups, complete As-Is, then a
  binding estimate. Depth still comes from the workshops.
- PDF one-pager leave-behind; Deck (.pptx) + TCF (.xlsx) generation (PARTIAL,
  demonstrated 2026-07-13); Benefit-voice detail renderer (PARTIAL, voice gate
  pending).

**E. Productization / multi-client.**
- Per-client registry + workspace: `clients/<slug>/` + `assessments.json`; kills
  the CITTI/NextDecade-hardcoded names.
- White-label branding block: a render-context branding object (§18).
- Per-client deploy targets + registry.
- Neutral sender domain: notification mail currently sends as
  `matthias.silva@brisken.com` (dev phase).
- Scope beyond two areas: Quick is verified only on Cash & Liquidity +
  Zahlungsverkehr; extend taxonomy coverage.

## Owner decisions still open (no code, my calls)
Product ownership (Brisken product vs Jochen's product vs carve-out);
reifegrad_pct band mapping + the reachable "100" level; benefit voice;
question-bank curation; Nagarro as first use case.

## House rules (carry these)
- No invasive live action (deploy, showcase republish, registry writes, sends,
  volume writes) without my explicit per-action yes.
- Anti-fabrication is structural, not advisory: a scored cell needs a verbatim
  quote that traces (≥18-char run) to a client source; never merge sources into
  one haystack. New sources get their own field + haystack + `source_origin`
  label, never claimed for a run that lacks them (NextDecade demo must stay
  byte-identical when a source is absent).
- No client data into git (tree is gitignored; keep it that way).
- Feedback widget is parity-guarded (`tests/test_feedback_widget_parity.py`) —
  re-sync `templates.py` if you touch it in `render.py`.
- Dates are passed in, never invented (B4). Zero em-dashes in client-facing
  output.
- Every new capability gets a one-line DoD in DESIGN.md §15 before it's built,
  and updates PIPELINE-NOTES on completion.

Start by confirming the next thrust (or telling me to pick), then plan it.
