# Continue-Prompt: One Assessment (nach RG-Kalibrierung + Adjudikation)

Paste everything below the line into a fresh chat.

---

We are continuing the One Assessment treasury-assessment tool (workspace/clients/Jochen Projekt/automations/treasury-assessment/, a FastAPI inline-HTML app + a Python pipeline package, deployed to Fly as one-assessment-demo, live at one-assessment-demo.fly.dev). The whole Jochen Projekt tree is gitignored (ripgrep needs --no-ignore; nothing to commit or PR). The only path to production is `flyctl deploy --ha=false` from site-host/, and every deploy waits for my explicit "deploy". Tests: `uv run --directory <treasury-assessment> --extra dev pytest -q` (currently 135/135).

Read first: docs/2026-07-16 - One Assessment RG Calibration + Adjudication/Checkpoint.md, PIPELINE-NOTES.md §T + §U, DESIGN.md (Stage-2 calibration + §15 build-state table), REIFEGRAD-ADJUDIKATION.md.

Where we are. All three of Jochen's data sources (Fragebogen, Unterlagen, Workshop) flow into scoring with separate anti-fabrication haystacks and honest origin labels. The RG-calibration thrust ran its full course today and CLOSED with a pre-registered kill:

- Mined anchors v1 were built (anchors.py, data/anchors-v1.json) but showed NO lift on the rebuilt projection eval (38 vs 36 of 141) and are now DISABLED BY DEFAULT (owner decision). Diagnosis: the three golden raters disagree at the gering/mittel boundary (kappa -0.06/0.10/0.22; STAEDTLER inverts CITTI's tool convention) — cross-client absolute exemplars cannot converge.
- Rubric v2 (Prozessreife, versioned via configure_calibration, calibration_version stamped everywhere) is the default text, but the pre-registered fresh-scorer A/B (arm A2 rubric-v1 vs arm C rubric-v2, each scored by an uncontaminated subagent) showed the rubric text moves ~nothing: identical toplines 43/141, 51% exact-on-scored, harsh cell 29 in BOTH arms. Kill bar (>=18) fired: prompt-side calibration is EXHAUSTED. Do not resume prompt-tuning.
- The residual gap decomposes into (a) workshop knowledge the questionnaire never carried (Fragebogen "Systeme: keine" vs golden "Litreca Treasury, Excel") — validates the 3-source methodology, defines the coverage thrust — and (b) a rating convention inconsistent even inside the CITTI golden ("E-Mail Verkehr"=mittel vs definierte IDOC-Pruefprozesse=gering). The convention half waits on REIFEGRAD-ADJUDIKATION.md (drafted, German, 6 Faelle + Wissensluecken-Frage + 25/50/75/100-Skala) — I decide if/how it reaches Jochen; his rulings become rubric v3 verbatim + the fold-back seed.
- New structural pieces that stay: question-echo fail-closed guard (a source_quote living only in a probe QUESTION region -> n/a + review), honest metric triple in projection stats (rg_exact_scored_pct / coverage_pct / quote_question_echo — never judge by raw rg_exact again), projection eval harness `cli project` (transports --mock / --export-prompts + --responses / --real which stays owner-gated), stage1_extract._section_for header fix.
- Owner decisions in force: anchors default-OFF; "adapt it to Claude — once we finish testing we can set it up with OpenAI gpt-4o" (Claude = reference scorer of the testing phase; offline fresh-scorer arms are THE instrument; no gpt-4o runs); adjudication sheet drafted.

House rules unchanged: no invasive live action without explicit per-action yes; anti-fabrication is structural (own field + own haystack + source_origin per source, never merge; NextDecade stays byte-identical when a source is absent); no client data into git; dates passed in are never invented; zero em-dashes client-facing; every new capability gets a DoD in DESIGN §15 before build; run `cli verify` before shipping any scoring change (`--update` only after a legitimate golden/contract change — the Mock gate is prompt-blind and needed no update today).

Methodology rules added today (binding):
- Eval arms are scored by FRESH subagents only (context = that arm's PROMPTS.md, nothing else); the main loop is gold-label-contaminated and must never score an arm itself.
- Treatments (anchor sets, rubric texts) stay DORMANT until an instrument measures them; pre-register pass/kill bars before any measurement; report the honest triple, not rg_exact alone.
- Frozen arms for comparison live in out/2026-07-16-proj-{A,B,A2,C}/; the stable Claude baseline is 51% exact-on-scored at ~60% coverage.

Your task: drive the tool down its roadmap. For anything that changes pipeline logic, scoring, or a client-facing surface, go into plan mode first, design it, wait for my go, then build + verify (pytest + `cli verify` + a mock CLI E2E + a NextDecade byte-regression where render changes) and stop at the deploy gate.

Recommended next thrust (pick one, or I reprioritize):
- **Coverage/evidence** (the larger accuracy lever, independent of adjudication): 78% of the 141-row eval's abstentions sit in 4 whole-Funktion evidence deserts (IHB, Commodity, Treasury Investment, WCM). The designed fixes are the follow-up-loop controller ("enough, or another round?" — DESIGN PLANNED, generates targeted follow-up questions per deficient area) and/or auto-generated probing questions for workshop prep. NEVER fix coverage by prompt-loosening (mints ~0.49 unflagged-wrong per converted row — the gpt-4o pathology, measured).
- **First real document-bearing submission** through the full offline loop (inbox --pull -> extract + curate -> assess --export-prompts -> fresh-scorer -> responses -> render -> publish gate) to shake out extract/curation ergonomics (only mock-tested).
- **Editable As-Is workbench** (Dirk's open item 3, DESIGN §PLANNED) — biggest open product feature.
- **Operator review triage queue** (review.json + accept/correct panel) — on-ramp to fold-back once adjudication lands.

Blocked/parked (do NOT build): anchors-v2 mining, contrastive exemplar pairs, abstention-conversion prompting, gpt-4o setup — all gated on Jochen's adjudication answers or the post-testing phase.

Owner decisions still open (no code): the adjudication sheet delivery + Jochen's rulings; Quick-Satz curation; benefit voice; product naming ("1Assessment" per Dirk's Protokoll edits); Nagarro as first use case.

Start by confirming the next thrust (or telling me to pick), then plan it.
