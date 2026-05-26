# Checkpoint: Brisken Expense Recon Call Outcomes

**Date:** 2026-05-20
**Status:** Active. Spec revision is the next deliverable; blocked on obtaining the original functional document (2026-05-14).

---

## Summary

Prepped Dirk for the 2026-05-20 expense-reconciliation call (brief + talking notes), then captured the full call as a primary-source transcript and extracted the decisions into a structured outcomes file. The call materially changed direction: stack reversed (Azure rejected, Firebase candidate), scope nuance restored (expenses-priority not whole-bookkeeping MVP), new hard requirements added (multi-entity RBAC, mandatory MVP receipt scanning), and the very next deliverable per Dirk is a revised functional spec.

---

## What Was Done This Session

### Call prep (pre-call)
1. `/resume brisken` — full-context load (no fast-path entry); reconstructed state from `PROJECT-BOUNDARIES.md` (active = expense reconciliation; lead nurturing paused, ledger authoritative), the 18-decision sheet, the paused lead-nurturing materials.
2. Wrote `2026-05-20-dirk-call-brief.md` — call-prep one-pager: triaged the 18 decisions into "discussion-needed" (5), "needs Dirk/accountant input" (5), "safe to default" (8). Surfaced the headline-goal question as the single load-bearing gating decision.
3. Wrote `2026-05-20-dirk-call-talking-notes.md` — human-to-human phrasing for each question + a why-this-stack section. Used during the call; user later trimmed two questions (gating-goal and splits/multi-receipt) — those were answered live.

### Call capture (post-call)
4. Saved verbatim Part 1 transcript to `reference/2026-05-20-call-transcript.md` (primary source, like the 2026-04-10 transcript).
5. Appended verbatim Part 2 (continuation recording, ~37:37) to the same transcript.
6. Wrote `context/2026-05-20-call-outcomes.md` — decisions extracted with timestamps (Part 1) and Part 2 additions section. Each item traces to the transcript; Dirk's guesses are flagged.

---

## Key Decisions Made

### Multi-tenant from day one
- **Choice:** Build as multi-tenant. Tenant ID and data separation hardened at the start.
- **Rationale:** Dirk confirmed productizing is a goal (not first priority); login/auth needed regardless; the incremental cost of multi-tenancy now is small vs the rebuild cost later.

### Stack direction reversed: Firebase/GCP candidate, Azure out, AWS-as-provider declined
- **Choice:** Investigate Firebase/Google Cloud for the whole platform (DB, runtime, AI gateway). Azure Document Intelligence rejected; Azure Blob rejected (single secure-cheap store instead, files in the same DB as structured data). AWS Bedrock declined as the provider.
- **Rationale:** Dirk's reasons: Brisken may exit Microsoft, Microsoft complexity, cost, product-independence from Brisken's tenant. Firebase recommendation comes via Giuliano (Brisken's "one pilot V3" on Firebase): out-of-box logging/audit, cheap elastic pricing, ~80% small customers on free tier. Risk flagged: Firebase gets messy beyond simple apps, especially audit-heavy accounting — research must settle this before the spec locks the stack.

### Claude confirmed with conditions
- **Choice:** Use Anthropic Claude for judgment. Use the existing Brisken Claude subscription (Pro-level guarantees no-training-on-data); app must surface a built-in user-consent prompt for sensitive data.
- **Rationale:** Dirk OK with the data path, but the no-train guarantee is non-negotiable and a new account would be redundant. Per-customer data-center selection deferred; EU-for-all acceptable now.

### Scope nuance restored (correction to earlier read)
- **Choice:** MVP priority is expenses/reconciliation. The Zoho-replacement / full-bookkeeping vision stands as direction, not as MVP.
- **Rationale:** Dirk explicit: "a different priority that we put now on expenses rather than the whole of bookkeeping." Requirement was born from Dirk's exercise with Chris (the finance manager / only finance person / key user) about her painful reconciliation process.

### Next deliverable = functional-spec revision (Dirk directive)
- **Choice:** Revise Dirk's 2026-05-14 functional document based on the call, before any Firebase research.
- **Rationale:** Dirk explicit. Research items flow from the revised spec, not before it. He also challenged whether the original spec was read line-by-line; standing instruction is genuine source comprehension, not AI-skim.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/drafts/2026-05-20-dirk-call-brief.md` | Created | Pre-call triage: 18 decisions sorted into discuss/collect/default; gating-goal question framed |
| `workspace/clients/brisken/context/drafts/2026-05-20-dirk-call-talking-notes.md` | Created (user later trimmed) | Human-phrasing companion to the brief; used live in the call |
| `workspace/clients/brisken/reference/2026-05-20-call-transcript.md` | Created + appended Part 2 | Verbatim primary source; preserved for future reference, like the 2026-04-10 transcript |
| `workspace/clients/brisken/context/2026-05-20-call-outcomes.md` | Created + appended Part 2 additions | Structured decision extraction; every item traces to a transcript timestamp; Dirk's guesses flagged |

---

## Current Status

Active. Pre-call materials served their purpose and are now superseded by the call outcomes file. The 18-decision sheet and the prepared talking notes should not be sent to Dirk as-is.

**Next deliverable:** revised functional spec, per Dirk's directive.

**Blocker on that deliverable:** the original 2026-05-14 functional document is not in `workspace/clients/brisken/` and is required input.

**Platform feasibility:** `infrastructure.yaml` lists `tier: unknown` with "Platform build scope" as a blocker. The blocker is partially resolved by the call (build direction is clearer), but the spec revision is the right vehicle to retire it, not an infra.yaml edit now.

---

## Next Steps

1. **Obtain the original functional document** (Dirk's 2026-05-14 source). Add to `workspace/clients/brisken/reference/`. Without it, the spec revision can't start.
2. **Read the functional document line by line** before drafting the revision. Per Dirk's directive; AI-skim is explicitly insufficient.
3. **Revise the functional spec** based on the call outcomes file. Output goes in `specs/1-spec/p1-*` per `PROJECT-BOUNDARIES.md` ID namespace.
4. **Brief / sync with Chris** (Brisken finance manager / key user / Zoho admin). Dirk to brief her first, then a joint call. She holds Zoho Books and Zoho Expense admin access and all historic reconciliation data.
5. **Task-list: Brisken Claude subscription access** — get API access to the existing Brisken Pro subscription; do not create a new account.
6. **Research items (after the spec revision):**
   - Firebase suitability for audit-heavy accounting (Matthias's flagged concern vs Giuliano's experience).
   - Anthropic direct API region selection / EU user creation. Price diff: AWS Bedrock vs direct.
   - Whether Firebase AI hub is hosted-Anthropic-with-region-choice or just an orchestrator using your own API key.
   - Mobile receipt scanning approach: Lovable-built mini-app vs Zoho Expense API fallback.
7. **Confirm legal retention period** with Brisken's accountant (Dirk's guess ~7 years US; unconfirmed).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/PROJECT-BOUNDARIES.md` — binding scope ledger
- `workspace/clients/brisken/context/2026-05-20-call-outcomes.md` — single source of truth for current state
- `workspace/clients/brisken/reference/2026-05-20-call-transcript.md` — primary transcript (full, both parts)
- `workspace/clients/brisken/reference/expense-reconciliation-open-decisions.md` — superseded in parts; cross-reference only

### Open Questions
- Where is the original 2026-05-14 functional document, and can it be added to `reference/`? (Hard blocker on the next deliverable.)
- Does the bookkeeping-replacement vision belong inside the MVP-priority spec or in a separate longer-horizon doc? Dirk's narrowing suggests separate, but he also said to "think about it from the beginning."
- Stack: Firebase for the whole platform, or Firebase + something for the audit/relational parts? Resolvable with the research items above.

### Working Notes
- The pre-call stack recommendation (FastAPI + Postgres + Azure + Claude) was anchored on the 18-decision sheet's team recommendations. The call reversed key parts. Lesson surfaced in Strategic Feedback below.
- The user trimmed two questions from the talking notes during the call (gating-goal and splits/multi-receipt). Both got answered. Not a friction event — that's the notes doing their job.
- Two PreToolUse Reference Anchor hooks fired (on Write outcomes + Edit outcomes Part 2). Both writes anchored faithfully to the transcript with timestamps; no fabricated values.
- "FastAPI" was described inaccurately in the call as a parser and conflated with an open-source parser tool ("one parser"). Dirk asked for a proper explanation. The revised spec must cleanly separate OCR/receipt-reading vs deterministic matching engine vs LLM judgment layer vs the web framework — and Matthias should be able to explain it on the next call.

### Reference Materials
- 2026-04-10 lead-nurturing call transcript (paused project; same client; do not cross-edit)
- `expense-reconciliation-open-decisions.md` — pre-call 18-decision sheet (partially superseded)
- Giuliano's "one pilot V3" Firebase build is the closest reference point Dirk has for the recommended stack

---

## How to Continue

`/resume brisken`. The 2026-05-20 context YAML now carries a brisken entry, so resume will take the fast path and land on the outcomes file. First substantive step: ask the user for the original functional document (the only B1-legitimate ask here — file genuinely not in repo, verified twice). Once present, read it line by line, then revise into `specs/1-spec/p1-*`.

---

## Strategic Feedback

### What Worked Well This Session
- The drip of directives (`load brisken` → `make notes` → `save transcript` → `save more` → `checkpoint`) worked cleanly because each step's output anchored the next. No re-discovery needed between steps.
- `PROJECT-BOUNDARIES.md` did its job: the ledger prevented accidental work in the paused lead-nurturing project despite the rich materials present in the folder. The "read the ledger, do not infer from file presence" rule held up.
- Splitting primary source (`reference/`) from structured extraction (`context/`) matched the established pattern from the 2026-04-10 transcript and made the outcomes file usable independently.

### Suggestions
- The pre-call brief and talking notes inherited the 18-decision sheet's team-recommendation column as-given, including the stack pick (Azure + Claude). The call reversed it because of client-ecosystem signals (Microsoft-exit risk, Giuliano's Firebase experience) that were not in the brief's reasoning chain. For future client-call prep, add a "client's tech ecosystem signals" anchor pass before any stack recommendation lands in the prep doc. The decision sheet's defaults are not a substitute for client-specific anchoring.

### System Health
- `PROJECT-BOUNDARIES.md` was authoritative at the start of session, but the call outcomes have made parts of the boundaries' "active project" description and the 18-decision sheet's recommendations stale. There is no system trigger that flags "boundary/scope docs may need refresh after a major client conversation." They decay silently. Worth considering whether `/comd_comms` or a post-call hook should surface a "scope-docs-may-be-stale" prompt when a transcript is saved to `reference/`.
- `infrastructure.yaml` for brisken still carries pre-call blockers (Upwork-contract, build-scope-to-confirm-on-call) that the call partially retires. Leaving these as-is for now because the spec revision is the right vehicle to retire them, but this is a small instance of the same boundary-staleness pattern.

**Autonomy score:** 0 — fully autonomous session. No corrections, no user-performed tasks I could have done, no diagnostic spirals.
