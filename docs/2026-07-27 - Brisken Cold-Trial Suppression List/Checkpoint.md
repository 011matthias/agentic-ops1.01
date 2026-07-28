# Checkpoint: Brisken Cold-Trial Suppression List

**Date:** 2026-07-27
**Status:** SENT + verified; ball in Cristian's court

---

## Summary
Built and delivered the suppression list that gates Brisken's reopened cold-email
trial (Cristian Frunze / getken). Dirk set the definition (suppress if in the CRM
or in the mailbox); 2,377 emails + 77 customer domains were sent to Cristian via
Graph and verified in Sent Items.

---

## What Was Done This Session
### Suppression list
1. Enumerated three read-only sources and confirmed reachability: live Zoho CRM,
   both-mailbox Graph scan, Rome master opt-outs.
2. Built a lean both-mailbox Graph 90d scan (inbound aggregate + Sent Items),
   reusing `brisken-outreach-truth.py` helpers; cached the active set to
   `.scratch/active_threads.json` so reruns skip the ~5 min scan.
3. First built the customer-only "Standard" cut (Matthias's pick), then REBUILT
   to Dirk's definition when his reply superseded it: every CRM Contact +
   mailbox counterparties + hard opt-outs + customer domains.
4. Verified the CSV clean: 0 dupes, 0 malformed, 0 brisken.com leak.

### Send
5. Ran the invasive-action gate before the Graph send (plain-language
   scope-of-effects + read-only readiness check). Readiness surfaced a recipient
   ambiguity (Cristian uses two addresses); resolved by reply-in-thread so the
   recipient is auto-set to the message sender (getken.ai).
6. Sent via Graph as Matthias; verified in Sent Items (isDraft=false,
   hasAttachments=true, to=cristian@getken.ai).

### State
7. Updated `p2-outreach.md`, corrected + unstaled `p2-lead-gen-general.md`
   ("cold email retired" was inaccurate after the trial), logged inbound +
   build + verbatim sent to `comms-log.md`.

---

## Key Decisions Made
### Suppression scope = Dirk's definition
- **Choice:** suppress a pool contact if in the CRM (ALL Contacts, not just
  customers) OR in the mailbox (90d), plus hard opt-outs and customer domains.
- **Rationale:** Dirk (owner) is authoritative; his rule supersedes Matthias's
  earlier customer-only "Standard" pick.

### Lean scan over the all-folders walk
- **Choice:** inbound aggregate + Sent Items, not the exhaustive per-folder
  outbound walk.
- **Rationale:** the all-folders walk ran 18+ min (killed); the lean method is
  complete enough for suppression and finishes in ~2 min.

### Send via Graph reply-in-thread
- **Choice:** `createReply` on Cristian's 2026-07-25 08:28 message (auto-addresses
  getken.ai) rather than a manual To line.
- **Rationale:** closes the wrong-address risk (Cristian replies from both
  getken.ai and ken.com.co) and keeps the thread.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/lead-generation/outreach-assets/suppression-list.csv` | create | the deliverable: 2,377 emails + 77 domains |
| `status/p2-outreach.md` | update | trial reopened, list built, SENT + verified |
| `status/p2-lead-gen-general.md` | update | correct "cold email retired"; unstale |
| `context/comms-log.md` | append | inbound + build + verbatim sent |
| `.scratch/build_suppression_lean.py` | create | rebuildable source (Graph cached) |

---

## Current Status
Suppression list SENT to cristian@getken.ai and verified in Sent Items. Ball is
in Cristian's court: dedup the 834 pool against it, confirm the count, launch.
brisken platform ops: unknown plan, no `platform` section in infrastructure.yaml
(feasibility assessment still TBD).

---

## Next Steps
1. Await Cristian's dedup + launch confirmation; log the reply and update
   `p2-outreach.md`.
2. If Brisken parks prospects as Zoho **Leads** (not Contacts): re-auth the Zoho
   app with the Leads read scope, then rebuild + resend (Leads pull currently
   401s on scope).
3. Only if the 834 overlaps Brisken's old ~2M-send lists: fold historical
   Instantly unsubscribes (no local export exists).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p2-outreach.md`
- `workspace/clients/brisken/context/comms-log.md` (tail: the Cristian thread)
- `.scratch/build_suppression_lean.py` (rebuild path)

### Open Questions
- Is there a logged Dirk sign-off for reopening the cold channel? Matthias
  committed to launch in his 2026-07-22 email; no explicit Dirk trial-approval
  is logged.
- Does Brisken keep prospects as Zoho Leads (would require the Leads scope)?

### Working Notes
- Graph active set cached at `.scratch/active_threads.json` (1258 raw
  counterparties). Zoho is pulled live each run; its token endpoint
  (`accounts.zoho.com`) intermittently timed out, so a retry wrapper was added.
- The all-folders outbound walk (`pull_outbound`) is the slow path (~18 min); it
  exists for per-contact "has X been contacted" truth, NOT bulk enumeration. For
  a suppression list, inbound aggregate + Sent Items is the right method.
- The person is **Cristian Frunze** (user said "Fuze"), two addresses:
  cristian@getken.ai (suppression thread "RE: Cristian Out of Office"),
  cristian@ken.com.co (separate "Problem" thread).
- Zoho customer signal = `Account_Status` startswith Active/Churned/Blocked
  (per `project_brisken_zoho_crm`); the cache's `type`=Customer field is NOT
  authoritative.

### Reference Materials
- Rules: `rule_brisken_graph_first`, `rule_instantly_invasive` (invasive gate),
  `rule_no_invasive_action_without_ask`
- Memory: `feedback_brisken_outreach_truth_is_mailbox`, `project_brisken_zoho_crm`

---

## How to Continue
When Cristian replies, log it and update `p2-outreach.md`. If he flags overlap
with Brisken's old lists, address the Instantly-unsubscribe gap; if he wants
Leads covered, get the Zoho Leads scope and rerun `.scratch/build_suppression_lean.py`.

---

## Strategic Feedback

### What Worked Well This Session
- The invasive-gate readiness check caught the two-address ambiguity BEFORE
  2,377 CRM/customer addresses went to the wrong recipient. The gate earned its
  keep here.
- Caching the Graph active set made the Dirk-definition rebuild near-instant
  instead of a second 5 min scan.

### Suggestions
- Promote the lean counterparty-enumeration into `brisken-outreach-truth.py` as
  an `--enumerate` mode (inbound aggregate + Sent Items) so the next suppression
  rebuild does not reinvent it in `.scratch`.

### System Health
- Autonomy: 4 human touchpoints (task inputs + the send authorization), 0
  corrections of agent error. Not elevated.
- One slow-path this session: started with the exhaustive all-folders walk
  before switching to the lean scan.
