# Continuation prompt — One Assessment app

Paste this into a fresh session (after `/resume jochen-projekt`).

---

We are continuing on the **One Assessment** treasury-assessment portal
(`workspace/clients/Jochen Projekt/automations/treasury-assessment/`, FastAPI
inline-HTML app, deployed to Fly as `one-assessment-demo`, live at
one-assessment-demo.fly.dev). This whole client tree is gitignored; the only
path to production is `flyctl deploy --ha=false` from `site-host/`, and every
deploy waits for my explicit "deploy". The registry, feedback log and showcases
live on the persistent `/data` volume and survive deploys. Read
`docs/2026-07-15 - One Assessment Feedback Widget + Portal Access/Checkpoint.md`
for the current state.

**Start with the feedback we have received.** The portal now carries the
feedback widget on every logged-in page, and there are already 7 items in the
log. First pull the current feedback fresh (don't trust this list, it may have
grown): reviewer path is `POST /welcome {name, next:/feedback-log}` then
`GET /feedback.jsonl`, or `flyctl ssh console` + `cat /data/feedback.jsonl`.
Then triage every item into: already-done / quick-fix / needs-owner-decision,
and show me that triage as a short table before building anything.

Known items as of the checkpoint (verify against the live pull):

1. **Dirk, 2026-07-14** — the Pipeline "Eingabe" link jumps back to the
   Auswertung page instead of going to Eingabe. This may already be fixed in a
   prior render.py pass; open the live NextDecade demo and check the actual
   behavior before touching anything. If fixed, mark it done, don't re-fix.
2. **Dirk** — "where do I fill the gaps?" The Lücke/Empfehlung section reads as
   passive. Make it clear what the client is supposed to DO with the gaps.
3. **Dirk** — make the as-is data collection more detailed: surface all data
   collected, the entire as-is input structure, on the Eingabe/Light-Fragebogen
   view.
4. **Dirk** — the Ist-Aufnahme (per-function) section needs to be regenerable
   when the input changes, because a changed input changes the Reifegrad.
5. **Jochen Stiebe, 2026-07-15** — add a further step after Step 1 Eingabe: a
   "Workshop" step, in the "Wie diese Auswertung entsteht" process flow.
6. **Jochen Stiebe** — the Gap/Empfehlung area needs a "Kapitel 4.
   Voraussetzungen" chapter; the content is in the Component Framework (ask me
   for that source if you don't have it).

For each item: confirm the exact surface it lands on, propose the change in
plain German as a short user-view walkthrough (per the reviews-in-plain-language
rule), and wait for my go on anything that changes wording, structure, or the
pipeline logic. Feedback items 5 and 6 are content/structure decisions, not
mechanical fixes; treat them as owner decisions, don't invent the content.

**After the feedback**, the remaining open work in priority order:
- Resolve Jannik's login: his exact code works live; he's mistyping it. Either
  relay a copy-paste-safe code, or on my yes mint a fresh code from an
  unambiguous alphabet (no `I l 1 O 0`, no leading lowercase).
- Add `Cache-Control: no-store` to the portal/intake HTML responses (root cause
  of the "immer noch nicht da" stale view).
- Pending Jochen build items: question-bank curation, `reifegrad_pct`,
  Benefit-Voice.
- Deferred a11y: intake `<label for>` association; darken the Produktweg green
  pill for AA contrast.

Constraints that always apply here: no invasive action in the live system
(registry writes, sends, deploys) without my explicit per-action yes; zero
em-dashes in anything client-facing; ground every claim/number in a queried
source; and the widget is parity-guarded (`tests/test_feedback_widget_parity.py`)
so if you change it in render.py you must re-sync templates.py.
