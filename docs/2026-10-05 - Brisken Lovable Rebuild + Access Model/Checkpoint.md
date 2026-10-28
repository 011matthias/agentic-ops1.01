# Checkpoint: Brisken Lovable Rebuild + Access Model

**Date:** 2026-10-05
**Status:** Decided and shipped; execution blocked on Dirk's Lovable invite

---

## Summary

Dirk greenlit the end state: the expense reconciliation tool stays unchanged,
everything else Brisken-facing moves into Lovable, inside Brisken's own
existing Lovable workspace. The ownership/access-model strategy and the
ordered rebuild list are both decided, written, and merged; nothing can
start until Dirk invites us to that workspace.

---

## What Was Done This Session

### Ownership and access model (PR #792)
1. Ran a workflow (five live verifiers against the repo, Lovable, Fly,
   GitHub/Cloudflare and Microsoft docs; three strategies; six adversarial
   refuters; one synthesis) to design how Brisken gets centralized editing
   and admin access to every live asset.
2. Rewrote `OWNERSHIP-HANDOFF.md` sections 4-12: two Brisken shared
   mailboxes (`platform@` owns every vendor account, `tools@` is what the
   apps send as), a per-asset access table, a 17-step sequence (rehearse
   on something worthless before Criss's ledger moves), nine decisions only
   Dirk can make, and a claims table naming every UNVERIFIED fact.
3. Superseded three TARGET-ARCHITECTURE.md calls with verified reasons:
   no Cloudflare in front (CNAME setup needs the Business plan, else the
   whole zone's nameservers move and put Microsoft 365 mail in the blast
   radius), the expense SPA stays on Lovable hosting rather than co-hosting
   in the Fly container (Publish is the only ship path a Brisken editor
   has), and the `Domain=.brisken.com` cookie is reopened.
4. Corrected three things the docs had wrong: the GoDaddy API key answers
   200 with 101 records (not 401); the legal PDFs serve from
   `brisken.com/docs/`, not resources; the Exchange Application Access
   Policy is already live on Brisken's tenant.
5. Explained the access model to the owner per-app after an initial
   explanation was too abstract (see Friction).

### Dirk's greenlight and the Lovable rebuild plan (PR #798)
6. Owner directive: expense reconciliation (Fly engine + its existing
   Lovable SPA) stays unchanged; everything else is replicated, improved
   where sensible, in Lovable, inside Brisken's existing workspace (already
   serving seven brisken.com microsites: brisklet, mbc-faq, tac-2025,
   token, articles, insights, sap-ai-brief).
7. Agreed the working method with the owner: one ordered list, then one
   site at a time together, Lead Desk last.
8. Created `workspace/clients/brisken/status/p2-lovable-rebuild.md`: the
   ordered list (workspace access + two mechanic probes, onepilot,
   resources, brisken.com+www, rome2026 retirement, Lead Desk, close-out),
   seeded from LIVE probes rather than the repo (page titles/sizes, the 18
   redirect sources, the five legal PDFs with byte sizes, the two host
   rewrites, one orphan resources page).
9. Answered directly, on request, whether moving the Lead Desk to Lovable
   Cloud needs new access: no. The Entra credential already works from
   Cloud, the Application Access Policy already covers both mailboxes, the
   data is on our own Fly volume.
10. Launched a five-agent read-only inventory workflow to prep the per-site
    build briefs (repo sources, live site probe, Lovable mechanics, design
    canon, Lead Desk surface). Did not complete (see What Did NOT Work).

### Fly cleanup (not committed; handed to the owner as a prompt)
11. Audited the live Fly account (`flyctl apps list`, `volumes list`,
    `machines list`) and wrote a destroy/keep prompt distinguishing live
    Brisken apps, the (then-still-live) `brisken-onepilot-proto` rehearsal
    target, another client's live demo, and Fly's own builder.

---

## Key Decisions Made

### Scope boundary
- **Choice:** The expense reconciliation engine and its existing Lovable
  SPA are out of scope for this rebuild.
- **Rationale:** Dirk's explicit directive; it already works and already
  lives in Lovable.

### Workspace
- **Choice:** Rebuild inside Brisken's EXISTING Lovable workspace, not a
  new one.
- **Rationale:** avoids a second Lovable subscription; Brisken already
  operates one (seven microsites live there today).

### Build order
- **Choice:** onepilot -> resources -> brisken.com+www -> rome2026
  retirement -> Lead Desk -> close-out. Ordered by cost of being wrong, not
  by importance.
- **Rationale:** learn the Lovable editor on a page with no forms and no
  redirects before touching the page that carries the demo form, the 18
  legacy redirects, and the GDPR-load-bearing legal PDFs.

### Lead Desk access
- **Choice:** scope the Lovable Cloud rebuild to what Brisken actually
  uses (contacts, mailbox truth-scan history, review queue, unmatched
  queue, user admin); defer the campaign sender until Dirk arms it.
- **Rationale:** verified live that this needs NO new grants — same Entra
  credential, same Access Policy, same Fly-volume data — so the only open
  cost is rewrite effort, not access.

---

## What Did NOT Work (and why)

- **Background inventory workflow (`wf_fe91f002-7cb`, five read-only
  agents: repo sources, live site probe, Lovable mechanics verification,
  design-canon extraction, Lead Desk surface).** Launched to prep the
  per-site build briefs, but never completed: the prior session ended
  while it was running, and a later task-notification reported it
  "stopped" with no completion record. It was launched without a
  `bg_watch.py` registration (see Friction), so nothing flagged it going
  quiet. The rebuild status file was instead seeded directly from live
  curl/DNS/GoDaddy probes done by hand, which covered the load-bearing
  facts (page sizes, the 18 redirects, PDF byte sizes, the host rewrites)
  but not the deeper Lovable-mechanics and design-canon extraction the
  workflow was meant to supply. That prep work is still owed before the
  per-site build sessions begin.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/OWNERSHIP-HANDOFF.md` | Rewrote sections 4-12 | Access model: identity, per-asset table, 17-step sequence (PR #792, merged) |
| `workspace/clients/brisken/TARGET-ARCHITECTURE.md` | 3 supersession notes | Cloudflare-in-front, SPA co-hosting, the `Domain` cookie, superseded by the access model (PR #792) |
| `workspace/clients/brisken/status/p2-lovable-rebuild.md` | Created | Ordered execution list for the Lovable rebuild (PR #798, merged) |
| `C:\Users\neuma_p1qrsic\.claude\plans\rippling-discovering-kahan.md` | Rewritten (plan mode, local only) | Current approved plan: replicate everything but the expense tool in Lovable |
| `workspace/clients/brisken/status/p2-onepilot-site.md` | Cross-referenced, `updated:` bumped | Hosting row superseded by `p2-lovable-rebuild.md`; rest of the file's live content/positioning tracking kept, not deleted (shipped in this checkpoint's docs PR per `rule_branch_isolation` §1) |

---

## Current Status

brisken platform: unknown plan, ops count not applicable (custom FastAPI
build, not a workflow-engine). Comms log 7 days stale — see note below.
p2-lovable-rebuild.md and p2-onepilot-site.md were both flagged 25 days stale
by the project-status sweep; p2-lovable-rebuild.md was in fact created and
updated today. p2-onepilot-site.md is reconciled below: its hosting row only
is superseded (the Fly hosting it describes is already destroyed and its
rebuild now lives in p2-lovable-rebuild.md), but it still carries live,
un-superseded tracked state (the TC deck-story alignment pointer, the
nested-hierarchy decision, open blueprint and one-pager work) and was not
deleted.

The rebuild is **blocked on Dirk**: nothing in `p2-lovable-rebuild.md` item 0
can start until he names the Brisken Lovable workspace and sends an invite.
`rome2026` retirement is independent and can proceed whenever he is at the
GoDaddy screen. The ownership/access-model track (PR #792) is fully shipped
and waiting on a separate Dirk answer: who operates the estate post-handover.

---

## Next Steps

1. **[Dirk-gated]** Get him to name the Brisken Lovable workspace and invite
   the build identity. Nothing else in the rebuild starts without this.
2. Once invited: build the throwaway Lovable project and probe the two
   unverified mechanics — a route-loader 301, and files pushed into
   `public/` via GitHub sync served at root paths — before touching
   anything real.
3. Decide whether to relaunch the stopped inventory workflow
   (`wf_fe91f002-7cb`, resumable via `scriptPath` + `resumeFromRunId`) for
   the deeper per-site briefs, or proceed straight off live probes as was
   done for the status file.
4. Work the list in order per `p2-lovable-rebuild.md`: onepilot ->
   resources -> brisken.com+www -> rome2026 retirement -> Lead Desk ->
   close-out.
5. **[Dirk-gated, separate track]** Who operates the estate post-handover,
   by name (`OWNERSHIP-HANDOFF.md` section 10, Q1) — keys the Fly-org
   creation step.
6. ~~Reconcile `p2-onepilot-site.md` against the new `p2-lovable-rebuild.md`~~
   — done this session: cross-referenced, not deleted (it still tracks live
   content/positioning work beyond hosting).
7. Correct `OWNERSHIP-HANDOFF.md` step 5: it names `brisken-onepilot-proto`
   as the `fly apps move` rehearsal target, but that app was destroyed
   2026-09-10; a fresh throwaway app is needed instead.
8. System-dev candidate: `feedback_reviews_in_plain_language` has now
   failed to hold six times (2026-07-14, 08-24, 09-06, 09-09, 09-28, and
   today); the 09-28 fix was marked resolved and still didn't hold. Promote
   to the rule layer rather than re-editing the memory again.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-lovable-rebuild.md`
- `workspace/clients/brisken/OWNERSHIP-HANDOFF.md` sections 4-12
- `workspace/clients/brisken/TARGET-ARCHITECTURE.md` section 1b

### Open Questions
- Which Lovable account/workspace is "Brisken's existing one" — whose
  login, Pro or Business plan?
- Does a route-loader 301 actually get honored on Lovable hosting?
- Do files pushed into `public/` via GitHub sync serve at root paths after
  Publish?
- Who at Brisken owns/operates the estate post-handover, by name?
- Which mailbox receives `/demo` form submissions once rebuilt — `tools@`
  or an interim `dirk.neumann@`?

### Working Notes
- The two Vercel projects (`brisken-onepilot`, `resources-site`) and Neon
  stay alive as the rollback until each Lovable cutover has soaked seven
  days.
- `rome2026` is a retirement, not a rebuild — independent of the workspace
  invite, can happen any time Dirk is at the GoDaddy screen.
- `resources.brisken.com` has one orphan page (`smart-trading-deck.html`,
  linked by nothing on the live site) — confirm before dropping it on
  rebuild.
- `brisken.com` and `/treasury` serve the identical document via a
  `vercel.json` host rewrite — one page to rebuild, not two.
- The Accenture case-study PDF (2.3 MB) is the largest asset in the
  estate; still inside Lovable's 10 MB per-file cap.
- **Correction caught before this checkpoint shipped:** `brisken-onepilot-proto`
  and `brisken-onepilot` (the Fly apps) no longer exist — confirmed live via
  `flyctl apps list` today. `p2-onepilot-site.md` records both as destroyed
  2026-09-10, the same day the OWNERSHIP-HANDOFF.md sequence (PR #792) was
  written naming `brisken-onepilot-proto` as the rehearsal target for the
  `fly apps move` dry run. That rehearsal step now needs a freshly-created
  throwaway app instead; OWNERSHIP-HANDOFF.md step 5 is stale on this point
  and should be corrected next time that track is touched.

### Reference Materials
- PR #792 (ownership/access model), PR #798 (rebuild list) — both merged
- Workflow `wf_192e288a-7cc` (completed, access-strategy design) —
  journal at `.../subagents/workflows/wf_192e288a-7cc/journal.jsonl`
- Workflow `wf_fe91f002-7cb` (stopped, incomplete inventory) — resume via
  `Workflow({scriptPath, resumeFromRunId: "wf_fe91f002-7cb"})` if revisited
- `C:\Users\neuma_p1qrsic\.claude\plans\rippling-discovering-kahan.md`

---

## How to Continue

Wait for Dirk's Lovable invite (item 0 of `p2-lovable-rebuild.md`), or start
with `rome2026` since it does not depend on the invite. Once invited, run
the two mechanic probes before building anything else; do not skip them —
the whole redirect and asset-carryover plan leans on both being true.

---

## Strategic Feedback

### What Worked Well This Session
- Live-probe-first discipline. Before writing the rebuild status file,
  curl/DNS/GoDaddy/Vercel calls caught facts the repo alone would have
  gotten wrong: `brisken.com` and `/treasury` are one document, not two;
  one resources page is an orphan; the legal PDFs live on `brisken.com`,
  not `resources.brisken.com`.
- Answering the Lead Desk access question directly and concretely when the
  owner asked for it, instead of waiting on the slower workflow-based
  inventory — the right call was a direct yes/no with the specific
  mechanism, not a research detour.

### Suggestions
- **Promote `feedback_reviews_in_plain_language` to the rule layer.** Six
  recurrences since 2026-07-14 across different clients and content types
  (plans, data layouts, architecture explanations, access-model
  explanations); the most recent memory-only fix (2026-09-28) was marked
  resolved and failed again today. The pattern is consistent: a
  synthesized/technical answer where the owner needs a concrete
  per-item walkthrough. This is a decision-time boundary, not a recall
  problem — it belongs beside `rule_human_communication`, not in memory.
- Secondary: a `PostToolUse(Workflow)` hook that checks whether a launched
  workflow has a matching `bg_watch.py` registration in the same turn
  would close the repeat gap from the 2026-09-08 register row (same class,
  recurred today on `wf_fe91f002-7cb`).

### System Health
- Autonomy score: 2 human interventions (one clarity correction on the
  access-model explanation, one redirect away from a slower in-flight
  workflow toward a direct answer). Not elevated.
- Gates: B1:4 B2:2 B3:0 skipped:1.
