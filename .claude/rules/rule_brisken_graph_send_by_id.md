# Brisken Graph Email-Send Safety (send-by-ID)

**Hard constraint (owner directive 2026-07-27).** Every email send in
Brisken's live Microsoft 365 tenant via Graph sends **only explicitly
enumerated messages, by id** (or a per-recipient `POST /sendMail` with an
explicitly enumerated recipient). Never a folder-level send, never a
broad-filter send, never "send all drafts." Before any send fires, the
content AND the recipients are double-checked for **situational
correctness**. "WE SEND ONLY BY ID. WE DO NOT RISK SENDING EMAILS OUT THAT
WE SHOULDN'T ACCIDENTALLY. WE DOUBLE CHECK THE CONTENT AND THE RECIPIENTS
FOR SITUATIONAL CORRECTNESS BEFORE SENDING."

This rule governs HOW a Brisken Graph send is executed safely. It sits beside
[[rule_brisken_graph_first]] (which mailbox/credential path is sanctioned) and
the invasive-action gate ([[feedback_no_invasive_action_without_ask]],
[[rule_instantly_invasive]] B5, which governs WHETHER a send is authorized at
all). All three apply to every send; this one is about not firing the wrong
message at the wrong person.

## 1. Send only by id (never folder-level, never broad-filter)

- The send target is an **explicit list of message ids you selected and
  verified**, iterated one at a time (`POST /users/{mbx}/messages/{id}/send`),
  or a per-recipient `POST /users/{mbx}/sendMail` whose recipient you set
  explicitly. Nothing else.
- **Never** send by "everything in the Drafts folder", by a subject/`$search`
  filter alone, or by any query that could sweep a message you did not intend.
  A shared mailbox's Drafts folder legitimately contains **other, unrelated
  drafts**. On 2026-07-27 the pre-send audit found 21 unrelated drafts in
  Dirk's Drafts folder (two of them addressed to SAP contacts) sitting
  alongside the 19 GA-wave drafts; a folder-level or loose-filter send would
  have fired all of them. That is the failure this rule exists to prevent.
- Selection is a **positive allowlist match**: a draft joins the send set only
  if its sole recipient is in the intended-recipient allowlist AND its subject
  is in the intended-subject set AND it is still an unsent draft. Match, do not
  guess.

## 2. Hard guards, refuse by default

The sender code asserts, and aborts the whole batch if any fails:

- **Count assertion.** `len(send_set) == expected_count` exactly. One too many
  or one too few aborts with no send. (GA wave: assert exactly 19.)
- **Recipient allowlist.** Every recipient in the send set is in the intended
  allowlist. Any address not explicitly intended aborts.
- **Exclusion refusal.** Refuse any recipient on a held / exclusion list even
  if it slipped in: held segments (e.g. SAP), opt-outs / `STOP` / suppression,
  and anyone already in an active thread (mailbox-truth dedup,
  [[feedback_brisken_outreach_truth_is_mailbox]]). A domain check (`@sap.com`)
  and the specific held addresses are hard-coded refusals, not warnings.
- **Mailbox allowlist.** Operate only on the sanctioned mailbox per
  [[rule_brisken_graph_first]] (`dirk.neumann@` / `matthias.silva@`), asserted
  in code before the call.

Guards are **deny-by-default**: the safe outcome of any uncertainty is "send
nothing", never "send anyway".

## 3. Double-check content + recipients for situational correctness

Situational correctness is judgment the guards cannot encode. Before firing,
confirm by eye:

- **Recipients** are the right people for THIS message: correct addresses (use
  the human-readable address over a cryptic alias when both exist), no
  wrong-role targets (an event planner is not a treasury contact), no
  competitors/partners a segment rule excludes, no duplicates, deduped against
  prior contact via the mailbox.
- **Content fits THIS audience**: the copy is right for who receives it (a
  buyer pitch is wrong for partners/SAP; the market-data note vs the plainer
  note was a per-segment call). Correct links, correct sender identity, correct
  BCC (Zoho dropbox on prospect/customer mail; none on internal), and **no
  leftover template tokens** (`{First}`, `{Firm}`).
- **Validate message #1 before any batch**: fetch the first created draft and
  confirm recipient, BCC, subject, body/link, `isDraft=true`, before creating
  or sending the rest ([[rule_brisken_graph_first]] already requires this for
  drafts; it applies to sends too).

## 4. Preview, then verify behavior

- **Dry-run** the resolved send set (print each recipient + subject) and read
  it before passing the go flag. The dry run is the last human-legible check.
- **After sending, verify behavior, not the accept code.** A `202` from
  `/send` only means "accepted". Confirm each message **left Drafts and landed
  in Sent Items** (`isDraft=false`), and that the count in Sent Items matches
  the intended count. State the verified result. (B2, [[rule_behaviors]].)

## Enforcement

Agent discipline at decision time, on every Brisken Graph send. The reference
implementation is the guarded sender pattern used for the GA wave
(`.scratch/ga_send_wave.py`): collect candidates, positive-allowlist match,
assert exact count, refuse SAP/held/non-allowlisted, dry-run, then send by id
with `--go`, then verify Drafts→Sent. Reuse that shape; do not hand-roll a
looser one. A folder-level or unguarded send, or a send without the
content/recipient double-check, is a `graph-send-safety` friction event even if
nothing goes wrong that time; log at `/comd_checkpoint`.

A structural backstop (a preflight that refuses a Graph `/send` loop lacking a
count-assert + recipient-allowlist) is the recurrence-kill if this ever repeats;
until then it is agent-enforced here.

## Why

2026-07-27 Rome GA wave. 19 approved drafts were staged in Dirk's Outlook for
send. The pre-send readiness audit found the Drafts folder actually held 40
drafts: our 19 plus 21 unrelated drafts of Dirk's own, two of them to SAP
contacts the wave explicitly excludes. Sending "the drafts" as a folder would
have fired all 40, mailing SAP people the wave was built to keep off and
Dirk's private unfinished drafts. The guarded send-by-id path (match exactly
19, refuse everything else) sent precisely the intended 19 and left the other
21 untouched, verified after the fact (0 left in Drafts, 19/19 in Sent Items).
The owner made the lesson a standing rule: send only by id, never risk an
accidental send, double-check content and recipients for situational
correctness first.

Related: [[rule_brisken_graph_first]] (sanctioned Graph path + mailbox
allowlist), [[feedback_no_invasive_action_without_ask]] +
[[rule_instantly_invasive]] (invasive-send authorization gate),
[[feedback_brisken_outreach_truth_is_mailbox]] (mailbox-truth dedup),
[[rule_behaviors]] (B2 verify-behavior).
