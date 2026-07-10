# Checkpoint: Brisken Lead-Gen Task 2 Zalando Collateral

**Date:** 2026-07-09
**Status:** Planner task 2 closed. All live Brisken demo material passes the new banned-content gate.
Open items are client-facing decisions, not build work.

---

## Summary

Started as Planner task 2 (Zalando TreasuryCentral collateral) in an isolated worktree. The deck already
existed from Session 8, so it was audited rather than rebuilt, and the audit found it shipping SAP BTP
against Dirk's own standing directive plus an unsourced claim about Zalando's S/4HANA migration. Session
8 had already emailed Dirk a SharePoint link to it. The session then widened, on the owner's direction,
into fixing the delivered material, deduplicating the product decks, retiring the deck generators, and
building the structural gate that should have caught all of it.

---

## What Was Done This Session

### Task 2 proper
1. Resolved task ID 2 from the Planner board via Graph (`orderHint` ascending = board order).
2. Audited the pre-existing Zalando deck rather than overwriting it. Wrote `zalando-call-brief.md`,
   `zalando-demo-flow.md`, `collateral-pack-and-delivery.md`, `notes-for-other-tasks.md` on branch
   `leadgen/task-2`.
3. Marked the Planner task complete, ticking only the two checklist items that were actually true.

### The delivered-material fix (owner-directed)
4. Replaced all four TreasuryCentral files in SharePoint `Client Collateral`, BTP-free, Zalando's proof
   line softened from "Your S/4HANA migration" to "An S/4HANA move".
5. Deduplicated `2026_PPTX`: recycled `Market Data Hub 2026.pdf` and `Digital Co-Worker 2026.pdf`
   (orphan BTP renders, no pptx) and Dirk's `Smart Trading 2026 copy.pptx`. All restorable.
6. Stripped BTP from Digital Co-Worker and MDH Commodities by **patching slide XML in place**, not by
   regenerating: 3 text runs changed across 265, every zip entry preserved.
7. Retired and then deleted the four module generators. `build-treasurycentral.js` survives.

### The structural fix
8. Built `tools/validate-demo-material.py` + `tools/fixtures/demo-banned-terms.json`.
9. On its first run it found a fourth leak that four hand-audits had missed. Fixed and pushed to the
   tenant, verified against the tenant's own bytes.

---

## Key Decisions Made

### Correct the existing deck rather than overwrite it
- **Choice:** Left Session 8's files alone; produced a corrected copy in the task directory.
- **Rationale:** Isolation rules, and the deck was not mine. Because both versions existed side by side,
  a byte comparison could later prove which one had shipped. An overwrite would have destroyed that.

### Patch slide XML instead of regenerating the product decks
- **Choice:** Surgical XML edit on Dirk's edited PPTX files.
- **Rationale:** Dirk edited all three decks himself hours earlier (MDH 12:40, Smart Trading 11:55,
  Digital Co-Worker 12:51). Regenerating would have destroyed his edits, and his edits are not cosmetic:
  he has **hidden** Smart Trading slide 10 (`PARTNERS AND CUSTOMERS`) and Market Data Hub slide 12
  (`Brisken`). Hidden slides do not export, which is why those PDFs run one page short. A regeneration
  silently un-hides them in front of a client.

### Product decks get no generator at all
- **Choice:** Deleted `build-mdh.js`, `build-smart-trading.js`, `build-digital-coworker.js`,
  `build-mdh-commodities.js`. Kept `build-treasurycentral.js`.
- **Rationale:** SharePoint is the source of truth for decks Dirk owns and edits. A generator pointed at
  them is a footgun with no upside, since the decks already exist. TreasuryCentral is a different class:
  it generates *new* per-prospect collateral Dirk presents but never edits, and it carries the visual
  primitives verbatim if a fifth deck is ever needed. Regression-tested after the deletion.

### Leave BTP in Dirk's walkthrough deck
- **Choice:** Exempted, not fixed.
- **Rationale:** Its single hit is on slide 46, a Technical Architecture diagram, in the label
  "BTP, Azure, AWS, Google Cloud". That is a deployment target, not a positioning claim, and striking it
  would make the diagram wrong. His deck, his call. Recorded as a justified exemption in the config.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `tools/validate-demo-material.py` | Created | Banned-content gate; reads what ships, not the source |
| `tools/fixtures/demo-banned-terms.json` | Created | Client directives as data; per-path exemptions, `"term": "*"` wildcard |
| `tools/INDEX.md` | Modified | Manifest row |
| `.../rome-2026/decks/README.md` | Created | SharePoint = source of truth; page counts as the un-hide check |
| `.../rome-2026/decks/*.pptx` (4) | Modified | Re-synced from SharePoint; Commodities patched |
| `.../rome-2026/dirk-send-pack/*.pdf` (4) | Modified | Same; all four now attachable |
| `.../rome-2026/dirk-send-pack/README.md` | Modified | Page counts corrected; mirrors-not-generated warning |
| `.../rome-2026/call-collateral/*` | Created | TreasuryCentral decks, tracked at last |
| `workspace/clients/brisken/context/comms-log.md` | Modified | Session 8's sent message verbatim + all four leaks + remediation |
| `.scratch/deckgen/build-{mdh,smart-trading,digital-coworker,mdh-commodities}.js` | **Deleted** | Owner-authorized; gitignored, unrecoverable, intended |
| `.scratch/deckgen/build-treasurycentral.js` | Modified | BTP removed at source; the one surviving generator |
| Planner task `HsjUNuYE2EaRvqMz2XEp32UAN8ud` | Modified | 100%, 2 of 4 checklist items ticked |
| SharePoint `2026_PPTX` + `Client Collateral` | Modified | 6 files replaced, 3 recycled |

Commits on `main`-line branch `client/brisken/lead-gen-onepilot`: `d576936`, `4a8d2da`, `2e5af40`,
`27b8487`, `ec2b7bf`, `8bc854f`. Branch `leadgen/task-2`: 5 commits, **unpushed, no PR**.

---

## Current Status

`uv run tools/validate-demo-material.py --client brisken --dir decks dirk-send-pack call-collateral`
exits 0. SharePoint `2026_PPTX` holds exactly one PPTX and one PDF per deck. The three recycled files sit
in the site Recycle Bin, restorable.

Dirk has **not** been told that the contents changed under the SharePoint link he was sent on 2026-07-08.

Platform: brisken `infrastructure.yaml` has `tier: unknown` and no `ops_limit`, so no ops percentage is
computable. Lead-gen (p2) runs no orchestrator.

---

## Open Tasks

**Client-facing decisions (nothing blocks these but a call):**

1. **Tell Dirk, or not, that the decks were corrected.** The link resolves and the content is now right.
   Four artifacts changed under him: two TreasuryCentral decks, Digital Co-Worker, MDH Commodities.
2. **The Calvin clip still carries BTP.** Reported by the parallel Session 11, not verified by me: the
   two MP4s in SharePoint `2026_VIDEO`, linked to Dirk at 20:41, have an end card reading "running on SAP
   Business Technology Platform". Corrected cuts sit on branch `leadgen/task-6`; the tenant replacement
   is held pending a go. This is the same defect class, third occurrence in one day.
3. **Dirk's 46-slide walkthrough deck** names BTP on its Technical Architecture diagram. Exempted in the
   config as a deployment-target label. His call whether it changes.

**Zalando call (task 2's actual purpose, still unbooked):**

4. **Read Lokesh's reply.** It exists only in Dirk's mailbox and nowhere in our files. It decides how much
   of the call's first ten minutes goes to discovery.
5. **Book the call.** Dirk books; his forward says end of next week or later. Paste-ready invite and the
   three attendee addresses are in `output/leadgen-task-2/collateral-pack-and-delivery.md`.
6. **Maria Moeller is unknown.** Dirk called her the lead. No booth registration, no CRM record.
7. **Add Lokesh, Adela and Maria to the Zoho `ZALANDO` account** (status `Lead - Cloud Subscription`,
   owner Dirk, last activity 2026-02-20). None of the three are on it. Worth doing by hand ahead of the
   bulk Rome upload, since this is the only Rome lead with a call pending.

**Engineering:**

8. **Wire `validate-demo-material.py` into a gate.** It is manual today. It belongs in `post-write-gate.py`
   for deliverable-scope writes, and in CI. That is what turns it from a tool into a control.
9. **Push `leadgen/task-2` and open a PR**, or fold its contents into the brisken branch. Five commits,
   currently local only.
10. **Sanofi call is confirmed for next Friday ~16:00.** Collateral is ready and clean. No demo flow or
    call brief was written for Sanofi (task 3's scope, not touched here).

**Unverified, worth resolving before the call:**

11. Lokesh's job title. Booth registration says "Treasury Consultant", our Tier-1 list says "Senior
    Treasury Consultant", Dirk's forward says "SAP Consultant, Corporate Solutions". The deck omits it.
12. Zalando's ERP state in 2026. Newest evidence is a consenso S/4Finance readiness check published
    2018-09-20 (treasury, cash and liquidity in scope; cash management described as "a modified SAP
    solution, strongly tailored to Zalando's requirements"; greenfield recommended).
13. Whether Adela Dolezalova's firm (Trillion, per her booth registration, not Zalando) is an incumbent
    systems integrator on the account.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md`
- `workspace/clients/brisken/context/comms-log.md` (the 2026-07-09 entries)
- `output/leadgen-task-2/SUMMARY.md` (on branch `leadgen/task-2`)
- `tools/fixtures/demo-banned-terms.json`

### Working Notes

**The lesson that cost the most.** I audited for BTP by grepping the literal token, four separate times,
and reported "0 BTP everywhere" each time. The spelled-out "built on SAP Business Technology Platform"
(MDH Commodities slide 7, credentials chip) survived every pass and was live on the tenant. It was found
the moment a tool scanned rendered output instead of source tokens. **Do not hand-grep for a banned term.
Scan what the client opens.**

**Byte fingerprints beat HTTP 200.** SharePoint rewrites `.pptx` on upload, so only PDF size is a
fingerprint there, and a live co-authoring session can save an old version back over a REST upload. Every
replacement this session was verified by re-downloading the tenant's bytes and re-extracting text.

**Hidden slides.** `<p:sld show="0">` on Smart Trading slide 10 and MDH slide 12. They do not export.
The per-deck page counts in `decks/README.md` are the check that nobody un-hid them.

**Graph / Planner.** Token from `.scratch/graph_token.txt` (~3h life; `grabtoken.py` re-captures from the
CDP Edge). Sort tasks by `orderHint` for board order. `percentComplete` PATCHes the task with the task
etag; checklist ticks PATCH `/details` with its own etag. Resolve tasks **by id, never by board position**;
the board changed size during this session.

**SharePoint over CDP.** Create your own tab (`Target.createTarget` on `viewlsts.aspx`), never attach to
the user's tabs. `Network.getAllCookies` returned only `FedAuth`, and `requests` 403'd; the page-context
`fetch` with `credentials:'include'` worked for everything up to 3.6 MB. Delete via `/recycle` (restorable
bin), not `deleteObject`. Git Bash mangles the leading-slash server-relative path unless prefixed
`MSYS_NO_PATHCONV=1`.

### Reference Materials
- <https://www.consenso.de/en/sap-s-4finance-readiness-check-at-zalando.html> (2018-09-20)
- SharePoint `2026_PPTX` and its `Client Collateral` subfolder
- Planner task `HsjUNuYE2EaRvqMz2XEp32UAN8ud`; bucket `gyfptEwAwUiJLXfd6aMrYWUABZRr`

---

## How to Continue

Start with open task 1 or 2: both are client-visible and both need a decision rather than work. Task 8
(wiring the validator into the write gate) is the highest-leverage engineering item, and the day's
evidence argues for it: the same defect class shipped three times in one day, caught three different ways,
none of them automatic.

---

## Strategic Feedback

### What Worked Well This Session
- Refusing to overwrite Session 8's untracked deck. Because both versions survived, a byte comparison
  later proved which one had reached the client. An overwrite would have erased the evidence.
- Reading Dirk's SharePoint file metadata before touching his decks. Author-vs-lastEditor is what revealed
  he had edited them, which is what stopped a regeneration from silently reverting his hidden slides.
- Two permission-classifier denials on the generator deletion were correct and worth honouring. The files
  were gitignored and unrecoverable, and "remove our own" was genuinely ambiguous.

### Suggestions
- The parallel-task prompt gives each session an isolated worktree but no way to see that another session
  already did the work. Session 8 created task 2 and shipped its deliverable fifteen minutes later; this
  session then audited it from scratch. A claim marker written before work starts (a Planner comment, or a
  `CLAIMED-BY` file in the task directory) would have routed the BTP fix into Session 8 *before* it
  uploaded to Brisken's tenant and emailed Dirk.

### System Health
- The gap this session closed: rules and hooks enforce banned **language**, and nothing enforced banned
  **content** originating in a client directive, because those directives live in a Planner board.
  `validate-demo-material.py` closes it, but it is still manual. Until it fires from `post-write-gate.py`
  and CI, it is a tool and not a gate, and the next occurrence will again be caught by hand or not at all.
- Autonomy score: 3 human interventions (2 B1 stop-gate fires, 1 explicit authorization for an
  irreversible deletion the classifier had correctly blocked).
