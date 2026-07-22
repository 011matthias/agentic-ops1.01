# Checkpoint: Brisken Nestle StratiFy Contact Intelligence

**Date:** 2026-07-22
**Status:** Delivered. Two mails sent to Dirk; three decisions open on his side.

> **PII NOTE.** This checkpoint is in a TRACKED path. The underlying work is a
> third-party contact list, and by owner instruction it lives ONLY in the
> gitignored `workspace/clients/brisken/context/`. No individual on that list is
> named here, in the session log, or in the friction register. Read the pointers
> in "Files to Read First" for the actual names.

---

## Summary

Mined the Nestle "STRatiFI Hypercare Support Model" distribution list that Dirk
forwarded on 2026-07-21, into a tiered 214-person target list for a LinkedIn
upsell of TreasuryCentral / OnePilot. Cross-referencing it against Brisken's own
Zoho CRM and event workbooks turned a cold list into a warm one, and surfaced a
data-quality problem on the top-ranked contact. Both findings were mailed to
Dirk, the second with an Excel attachment.

---

## What Was Done This Session

### Extraction
1. Pulled Dirk's 2026-07-21 13:31 "Nestle Intelligence" mail app-only via Graph
   from `matthias.silva@brisken.com` (read-only; mailbox hard-allowlisted per
   `rule_brisken_graph_first`).
2. Parsed the two nested recipient blocks (an 18 Jun forward carrying display
   names only, and the 17 Jun original carrying names + SMTP) into 214 unique
   people, deduped across blocks.
3. Deliberately did NOT reconstruct the 51 missing addresses from Nestle's
   visible `First.Last@{cc}.nestle.com` pattern. They are flagged
   `address_in_source=False` and stay blank.

### Enrichment (the part that changed the answer)
4. Cross-matched all 214 against the Zoho CRM cache: 12 already known.
5. Scanned all 88 client workbooks under `context/` with openpyxl (xlsx are
   invisible to grep, per `feedback_ripgrep_skips_gitignored_context`). Found
   four people on the list who have already met Brisken at TA Cook events, with
   real titles and seniority on file.
6. Established from Zoho that the account is `Active - Cloud Subscription`, i.e.
   a genuine existing customer under the `Account_Status` rule in
   `project_brisken_zoho_crm`, so the brief is an upsell, not a prospect pitch.

### Delivery
7. Tiered the list A1/A3/A2/B/D/C/E/X by strength of evidence, with a per-row
   `basis` (the fact) and `confidence` (grading the role inference only).
8. Wrote the analysis brief + CSV into the gitignored client context.
9. Built a 3-tab Excel deliverable (Shortlist 57 / All 214 / How to read).
10. Sent two mails to Dirk via Graph, each behind a scripted pre-send readiness
    check with a Sent-Items readback (`isDraft=false`) as the proof of send.

### Data-quality finding
11. The top-ranked contact is filed under a different surname in Zoho and in
    every TA Cook list than in Nestle's own address book, joined on one email.
    Traced the wrong surname to the TA Cook delegate registration data itself
    (not a Brisken merge), alongside other inconsistencies in the same rows.
12. Verified via Graph that no outreach ever used the wrong surname, and that the
    contact is on a live Brisken project thread rather than being a cold name.

---

## Key Decisions Made

### Fact vs inference carried per row, not asserted globally
- **Choice:** every row carries a `basis` naming the evidence and a `confidence`
  grading only the role inference. No job title was invented; the five titles in
  the output all trace to Brisken's own records via a `list_source` column.
- **Rationale:** B4. Only 11 of 214 state a department anywhere in the source. A
  tier label that hardens into assumed seniority is the failure mode here.

### PII stays in the gitignored context, including out of this checkpoint
- **Choice:** CSV, brief, xlsx and drafts all under
  `workspace/clients/brisken/context/`; no names in `docs/`, `status/`, or memory.
- **Rationale:** explicit owner instruction. Verified with `git check-ignore` on
  every artifact and a `git grep` sweep of tracked paths.

### Excel attachment, reversing an earlier call
- **Choice:** attached the full list to Dirk. My first draft deliberately carried
  no attachment and no bulk name list.
- **Rationale:** owner override. Dirk is the data's own recipient and the account
  owner; the containment rule targets tracked paths and public deliverables, not
  an internal mail to the person who sent the source.

### LinkedIn enrichment left as the owner's decision
- **Choice:** did not run the 27 lookups; wrote it up as an open decision.
- **Rationale:** Sales Navigator profile views are visible to the person viewed.
  27 lookups on named staff at a live account mid-delivery is a judgement about
  how Brisken shows up at the customer, not a mechanical step.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/context/lead-generation/nestle-stratifi-contacts.csv` | Created | 214 rows x 23 cols, tiered, per-row basis + source (**gitignored**) |
| `workspace/clients/brisken/context/lead-generation/nestle-stratifi-analysis.md` | Created | The brief: tiers, gaps, open decisions (**gitignored**) |
| `workspace/clients/brisken/context/lead-generation/Nestle-StratiFy-contacts-260722.xlsx` | Created | 3-tab deliverable sent to Dirk (**gitignored**) |
| `workspace/clients/brisken/context/drafts/nestle-stratifi-findings-to-dirk.md` | Created | Draft 1 + per-claim source table (**gitignored**) |
| `workspace/clients/brisken/context/drafts/dorta-name-disparity-to-dirk.md` | Created | Draft 2 + per-claim source table (**gitignored**) |
| `workspace/clients/brisken/context/comms-log.md` | Modified | Both sends logged verbatim with open items (**gitignored**) |
| `workspace/clients/brisken/status/p2-targeting.md` | Modified | New element row + `updated:` bump (tracked; no names) |

---

## Current Status

Both mails are sent and confirmed in Sent Items. The list is built, tiered and in
Dirk's hands as an Excel workbook. Nothing further is actionable by me without a
decision from him.

No `platform` section applies (this was a research and comms session, no
orchestrator work). No Make.com reconciliation needed.

---

## Next Steps

1. **Wait on Dirk's LinkedIn go/no-go** for enriching the top 27 (A1+A3+A2). This
   is the step that converts tiers A2 and B from a location prior into a real map.
2. **Zoho name correction** on the top contact. LIMITATION: the connection is
   READ-scope (`ZohoCRM.modules.contacts.READ, accounts.READ`), so it needs
   someone with write rights, or a scope upgrade on the Self Client.
3. **Capture the top contact's real title** via the live project thread, which
   also resolves the doubt about the registration record.
4. **Log this session's hours** to the Lead Generation tab. LIMITATION: I could
   not source a defensible session start (`session_state.py` reported `calls=1`,
   so the meter did not track this session), and inventing a start time on a
   billing value is exactly what B4 forbids. Needs the owner to supply the window.
5. **Two Brisken status files are 31 days stale**, flagged by
   `project_status.py --check`: `p2-lead-gen-general.md` and `p2-outreach.md`.
   Neither was touched by this session's work, so I did not edit them; writing
   progress I have not verified into a status file is the exact failure mode the
   convention exists to prevent. They need a session that actually worked those
   workstreams, or deletion if the work is dead.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/lead-generation/nestle-stratifi-analysis.md`
- `workspace/clients/brisken/context/lead-generation/nestle-stratifi-contacts.csv`
- `workspace/clients/brisken/context/comms-log.md` (last two entries)
- `workspace/clients/brisken/status/p2-targeting.md`

### Open Questions
- Who owns the "Treasury Sustain Team" and the Vevey "Center Cash Mngt,
  Application" group? Both are named in the source invite but neither resolves to
  individuals from it. These are the sharpest TreasuryCentral fit on the list.
- Does the top contact's registration record describe one person or two? The
  treasury title that makes him the #1 target sits on rows with a contradictory
  billing address, a placeholder phone, and an attendee type that flips between
  customer and partner across sheets.

### Working Notes
- **The enrichment step is what made this valuable.** The email alone yields a
  location-ranked guess. Cross-referencing Brisken's own event workbooks is what
  produced real titles and the four warm contacts. Do that first next time.
- **xlsx are invisible to ripgrep.** 88 workbooks under `context/` returned zero
  plaintext hits for "nestl" while actually containing the decisive evidence.
  Always scan with openpyxl before concluding absence.
- **Two parse bugs, both self-caught, both worth remembering.** (a) Locating the
  recipient blocks by fixed line number silently dropped a 46-person Cc block;
  switched to regex-located blocks. (b) A city containing its own comma
  ("AU-Rhodes, Sydney") parsed "Sydney" as an org unit, inventing 3 phantom
  departments and inflating a count I had already written into the brief.
- **A readiness check can produce a false negative on hard-wrapped HTML.** The
  second send aborted because a phrase I was asserting straddled a newline in the
  source. Flatten whitespace before substring-checking a body. The gate failing
  closed was correct behaviour; the bug was mine.
- **Do NOT substitute a targeted `$search` for `brisken-outreach-truth.py`.** The
  tool exceeded the 120s foreground timeout on a single-contact question, so I
  answered via a narrow Graph `$search` instead. When the backgrounded run later
  completed it returned strictly more: it surfaced an inbound reply my query had
  structurally excluded (I filtered `to == [contact]` for 1:1 outreach, which
  drops all inbound), and it showed one send filed in a custom folder
  (`TA Cook 2026 Rome - Outreach`) rather than Sent Items, which is the precise
  false-negative case `feedback_brisken_outreach_truth_is_mailbox` exists to
  prevent. The faster path answered the question I asked and would have silently
  missed "has he replied". Run the real tool in the background and wait for it.
- **Read the tool's REPLIED flag, not just its verdict.** It marks any non-OOO
  inbound as a reply. For the top-ranked contact the inbound was on the live
  project thread, not a response to either Rome outreach mail. He did not answer
  the Rome campaign; relevant context for the LinkedIn decision.

### Reference Materials
- `rule_brisken_graph_first` (Graph-only for Brisken M365; mailbox allowlist)
- `feedback_brisken_outreach_truth_is_mailbox` (a real send is `isDraft eq false`)
- `project_brisken_zoho_crm` (`Account_Status`, not `Account_Type`)
- `feedback_dirk_email_notification_style` (the voice both mails were written in)

---

## How to Continue

Read the analysis brief, then check whether Dirk has replied on the LinkedIn
question. If he greenlights it, enrich the 27 names in tiers A1/A3/A2, rewrite
the `list_role` column from real titles, and re-run the tiering. If he has not
replied, there is nothing to push: the remaining work is all gated on him.

---

## Strategic Feedback

### What Worked Well This Session
- The two-step "draft, inspect, then send" loop on both mails caught real issues
  before they reached Dirk. The attachment reversal and the "explain the LinkedIn
  ask" request both improved the output materially.
- Terse directive input ("use Dirk's StratiFy", "hand him excel attachment",
  "Send.") was efficient and unambiguous. No interpretation needed.

### Suggestions
- The hours tracker cannot be filled autonomously because nothing records session
  start. If `session_state.py` stamped a session-start timestamp, hours logging
  would become a mechanical step instead of a question back to you.

### System Health
- **`stop-b1-gate` fired three times; once correctly, twice on quoted content.**
  The correct fire caught a real deferral that, once acted on, changed the
  headline finding. The two false positives both matched deferral phrasing
  *inside an email body being shown for inspection*. The gate cannot currently
  distinguish my own closing words from quoted draft content, which trains
  desensitisation to a hook that is otherwise earning its keep.
- **The register shows `agent-deferred` as a persistent recurring class** across
  at least six sessions this week, with the note "the hook keeps holding, the
  disposition does not improve". This session repeats it. The hook is a
  backstop, not a fix; the underlying disposition to offer bounded autonomous
  work instead of doing it has not changed.
- Autonomy score: 3 human interventions this session.
