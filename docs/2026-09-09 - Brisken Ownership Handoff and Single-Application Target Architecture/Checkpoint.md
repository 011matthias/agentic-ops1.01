# Checkpoint: Brisken Ownership Handoff and Single-Application Target Architecture

**Date:** 2026-09-09
**Status:** Two recommendation docs merged to main; nothing sent to Dirk; no infrastructure touched

---

## Summary

Enumerated the entire Brisken web estate live and found every property, including
brisken.com itself, hosted and billed under personal accounts, then answered the
owner's follow-on requirement (one application for website and tools) with a
12-agent workflow whose two decisive findings both contradicted the intuitive
plan: port 25 eliminates every edge host, and path-prefix mounting is empirically
broken on the pinned Starlette.

---

## What Was Done This Session

### Ownership enumeration (verified live, not inferred)
1. Vercel: personal account `matthias-5647` / neumath4@icloud.com, single team
   `matthias-neumanns-projects` (`team_MNNYUo2DofKqKUISX0X01rre`), holding
   `brisken-onepilot` (brisken.com + www + onepilot), `resources-site`, and
   `brisken-rome-hub`, alongside our own `unpauseai-web`. Per-project transfer
   only; a team handover is not available.
2. Fly: `flyctl orgs list` returns exactly one org, `personal`. Both stateful
   apps carry client data on 1GB volumes (`recon_data`, `lead_desk_data`).
3. Neon is a Vercel-managed storage integration on the personal team (18
   `DATABASE_*` vars incl. `DATABASE_NEON_PROJECT_ID`), so it does NOT ride
   along with a Vercel project transfer. It is a migration, not a transfer.
4. GitHub `011matthias`, no orgs. SPA repo + Lovable seat both personal.
5. What Brisken already owns, which changes the risk profile: brisken.com
   registered at GoDaddy since 2009 (our GoDaddy key 401s against it, so the
   registrar account is theirs), the Entra Graph app in their tenant, Dirk's
   OpenAI key. No lock-out is permanent; they can always repoint DNS.

### Reconstructability gap (the sharper finding)
6. The deploy sources for brisken.com and resources live inside the private
   monorepo, which does not transfer. The source bound to rome2026 sits in
   gitignored `.scratch/brisken-rome-hub/`, on one laptop. "They can rebuild
   from git" assumed a git they do not have.

### Single-application strategy (12-agent workflow, 12/12 clean, 2.58M tokens)
7. Four ground agents read the running systems; four independent architectures
   (Azure-native, Fly-minimal, product-shaped, contrarian); three adversarial
   judges; one synthesis.
8. Recommendation: consolidate into the existing `brisken-expense-recon` Fly app
   behind a Host-header router, SPA same-origin, one magic-link sign-in, six
   phases plus a conditional seventh.

### Deliverables
9. `OWNERSHIP-HANDOFF.md` (PR #704), extended with single-platform consolidation
   as the target end state (PR #705).
10. `TARGET-ARCHITECTURE.md` (PR #754).
11. Two client-email drafts authored and held; nothing sent, no mailbox draft
    created.

---

## Key Decisions Made

### Port 25 decides the host, before preference
- **Choice:** Container host only. Vercel, Netlify, Cloudflare Pages/Workers and
  Azure Container Apps are eliminated outright.
- **Rationale:** Receipts arrive over an `aiosmtpd` listener inside the same
  uvicorn process, Fly raw TCP pass-through on 25, dedicated IPv4, rDNS, and the
  `expenses.brisken.com` MX. An MX target can only point at port 25 and a shared
  or anycast IP cannot carry it. Direction follows: the 11.4 MB website comes
  INTO the container, never the engine out to the edge.

### Merge INTO brisken-expense-recon, not into a new app
- **Choice:** Keep the app object; it is invisible once `tools.brisken.com`
  resolves to it.
- **Rationale:** That object owns the IPv4, MX, PTR and cert. Merging into it
  makes the mail cutover risk zero rather than managed, and deletes the dual-MX
  work three of the four designs only needed because they chose to move apps.

### Host-header dispatch, never path prefixes
- **Choice:** Dispatch whole ASGI applications by hostname; unknown hosts deny.
- **Rationale:** On the pinned Starlette 1.3.1, `Mount` does not propagate
  lifespan, so the SMTP listener and the lead desk's capture loops would silently
  never start while `/healthz` returned an unconditional ok and every page still
  served. `Mount` also leaves the prefix in `request.url.path`, and both engines
  gate on exact-match `OPEN_PATHS`, so a mounted app locks out its own login.
  Three of four candidate designs used prefix mounts.

### Azure deferred, not rejected
- **Choice:** Not the plan of record until Brisken names an owner. One-question
  test: who restores this from backup, by name, within a week of asking.
- **Rationale:** Disqualified by two of three judges on an unqueryable
  dependency. The Graph credential 403s on `/users`, `/users/{upn}` and
  `/applications`, so Criss's licensed sign-in-capable account cannot be
  confirmed; at three seats that is a third of the user base potentially locked
  out of her own month-close. Base rate on that IT function: a one-line Exchange
  Application Access Policy requested 2026-07-14, still unconfirmed.

### Transfer before consolidate
- **Choice:** Ownership moves on the current stack first (days), consolidation
  second (weeks).
- **Rationale:** A bad consolidation then fails onto infrastructure Brisken
  already controls. Also leverage: handing over accounts while the code is still
  only in our repo gives up control without giving them capability.

### Emails do not announce the departure
- **Choice:** Pose ownership and consolidation on their own merits.
- **Rationale:** Dirk has never been told anything about the timeline (comms-log
  scan confirms). Announcing it makes him reply to the exit rather than the
  question, and the infrastructure conversation should land first.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/OWNERSHIP-HANDOFF.md` | created (#704), extended (#705) | Who owns what, per-platform transfer runbook, single-platform target |
| `workspace/clients/brisken/TARGET-ARCHITECTURE.md` | created (#754) | The one-application recommendation, six phases, rejected options, live defects |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | updated | Consolidation target pointer |
| `workspace/clients/brisken/status/p2-onepilot-site.md` | updated | Fly review sites slated for retirement in P1 |

---

## Current Status

Both docs merged and verified on `main`. No infrastructure changed, no accounts
moved, no email sent, no mailbox draft created. Brisken ops status: platform
section reports unknown plan and no assessment date, which is pre-existing.

The estate is exactly as it was at session start. What changed is that it is now
enumerated, and the decision is framed.

---

## Next Steps

1. Decide the end state (transfer + retained seat, clean exit, or de-risk only).
   Every downstream choice keys on it, including the platform.
2. Split the three site sources into standalone repos. Needed in all three
   scenarios, no Dirk involvement, closes the reconstructability gap.
3. Send or revise the ownership email once (1) is settled.
4. Triage the seven live defects in `TARGET-ARCHITECTURE.md` §8 independently of
   the strategy. The OnePilot `inquiries.jsonl` read must happen BEFORE those
   volumes are destroyed.
5. Refresh six stale p2 status files (48 to 80 days): `p2-lead-gen-general`,
   `p2-outreach`, `p2-product-decks`, `p2-rome`, `p2-targeting`, and
   `p2-onepilot-site` beyond the pointer added here.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/TARGET-ARCHITECTURE.md`
- `workspace/clients/brisken/OWNERSHIP-HANDOFF.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- End state: retained seat vs clean exit vs de-risk only. Blocks the platform
  choice and whether secrets rotate against our own access at cutover.
- Does Brisken IT have a named owner? Flips Azure from deferred to the point.
- Is the old Wix site still accepting form submissions? The only two genuine
  inbound enquiries Brisken has ever had came through it.

### Working Notes
- **The workflow output is worth keeping.** Full per-agent returns at
  `.../subagents/workflows/wf_d839513b-24f/journal.jsonl`; the merged result is
  ~440 KB. The synthesis is condensed into `TARGET-ARCHITECTURE.md`, but the
  ground agents' route-level detail on the recon app (71 routes, 3 SQLite DBs,
  12 + 5 tables, process-global locks) is not, and would cost real tokens to
  re-derive.
- **Correctness-at-one-instance is already true today,** not a consequence of the
  plan: the mail day budget, `MAX_INFLIGHT_ROUTES`, the trip-batch slot set, the
  batch write lock and the Graph send counter are Python globals under
  `threading.Lock`. The plan makes the singleton written policy rather than a
  Fly accident.
- **Scale-to-zero is currently the scheduler.** Four boot sweeps (stale-job
  reconcile, interrupted-ingest requeue, ten-year AO §147 retention deletion,
  pooled-mail claim) fire only because a restart is near-daily. Setting
  `min_machines_running = 1` without converting them first stops all four with
  no error and no log line. They must ship in the same change.
- **Failed approach:** `vercel projects ls` and `vercel teams ls` both dead, the
  CLI token is stale and the OAuth device flow cannot run in a non-interactive
  session. The working path is the REST API with `VERCEL_BRISKEN_TOKEN` from the
  gitignored client `.env`; that answered account identity, team list, project
  list, per-project domains and env-var names in four calls.
- **GoDaddy API returns 401 for brisken.com.** Not a broken key on our side in
  the useful sense: it is positive evidence the registrar account is Brisken's.
  RDAP is the free route to registrar and dates.
- Fly org move for volume-backed apps stays UNVERIFIED. P1 of the plan probes it
  for free on `brisken-onepilot-proto` before P5 depends on the answer.

### Reference Materials
- PRs: #704 (runbook), #705 (single-platform target), #754 (architecture)
- Workflow run: `wf_d839513b-24f`, script persisted under the session's
  `workflows/scripts/`
- `reference_vercel_platform_team_scope`, `reference_lovable_merge_is_not_live`,
  `feedback_reviews_in_plain_language`

---

## How to Continue

Read `TARGET-ARCHITECTURE.md` §10 for the four questions, then settle the end
state. Nothing else should start before that: the platform, the email framing,
and whether we keep a seat all key on it. Step 2 in Next Steps is the exception
and can run in parallel, since it is required in every scenario.

---

## Strategic Feedback

### What Worked Well This Session
- Enumerating live before recommending changed the answer twice. The GoDaddy 401
  turned a lock-out story into a fire-drill story; the `.vercel` project bindings
  turned a team handover into three per-project transfers.
- The 12-agent workflow earned its cost. The Starlette lifespan finding
  invalidated the approach three of four designs used and that I would have
  written myself. A single-pass answer would have shipped a plan that deploys
  green and silently stops taking receipts.
- Adversarial judging killed the design I was drawn to. Azure read as obviously
  correct for a Microsoft company until two judges independently found the same
  unqueryable dependency.

### Suggestions
- The owner had to ask "can you explain this properly" after a technically dense
  answer, which `feedback_reviews_in_plain_language` predicts exactly. That
  memory fires on plan reviews; it did not fire here because the turn read as an
  analysis summary rather than a review. Widening its trigger to "any answer the
  owner is expected to decide on" would have caught it. Consider promoting it to
  a rule with that trigger, since it has now missed twice.

### System Health
- Two guards fired on documented patterns that already have four register rows
  between them (heredoc size, cd-guard). They caught everything before damage, so
  the structural layer is working, but four tool calls were still lost to
  patterns the register has recorded since August.
- The branch-isolation gate is advisory and fires AFTER the write. In a shared
  tree with two live sibling sessions, the session-start hook had already
  recommended a worktree and the write happened on `main` anyway.
- **A sibling session overwrote the shared checkpoint payload mid-run.** The
  checkpoint skill documents one fixed path, `.scratch/checkpoint-payload.json`,
  in a clone that routinely runs concurrent sessions. A parallel session wrote
  its Vinted payload there between my write and my `finalize` call, so the run
  appended that session's INDEX row, session entry and four friction rows into
  my docs worktree. Caught immediately because `finalize` echoes the topic back,
  and it echoed the wrong one. Recovery: archive the diff, discard the throwaway
  worktree rather than git-restore anything, re-run with a topic-scoped payload
  filename, and copy the sibling's payload back to the shared path so their own
  checkpoint still finds it. The structural fix is to scope that filename by
  topic or session id; as written, two checkpoints in the same window silently
  consume each other.
- Autonomy: 3 human interventions (AskUserQuestion answered outside the options,
  a redirect toward strategy, and the plain-language correction).
