# Checkpoint: Brisken Rome T3 Wave Sent

**Date:** 2026-07-21
**Status:** Complete — all 24 T3 touch-1 emails SENT from Dirk's mailbox

---

## Summary
Loaded and then sent the rebuilt Rome T3 touch-1 wave: 24 individualized follow-up emails from dirk.neumann@brisken.com via Microsoft Graph, each with the TreasuryCentral pptx attached, the resources.brisken.com/treasurycentral.html skim-link in the body, and the Zoho CRM dropbox BCC. 24/24 sent, 0 failed, all reconciled in Sent Items.

---

## What Was Done This Session
### Send prep
1. Located the attachment: `C:\Users\...\Desktop\Downloads\Brisken - TreasuryCentral Solutions Overview 2026-07-21.pptx` (0.45 MB — small enough to inline in a Graph message, no upload session).
2. Resolved the send mechanism from the layout email Dirk approved ("ready to go from your Outlook" / "I'll load touch 1 from your Outlook"): load as drafts in Dirk's box, sent one-to-one from his mailbox — not a cold-domain blast.
3. Built `.scratch/t3_load_drafts.py` (idempotent draft loader; parses the 24 rendered emails from the rebuilt wave, attaches the pptx, keeps the link, bakes the Zoho BCC, validates draft #1 before batching).

### Draft load + verify
4. Loaded 24 drafts into dirk.neumann@brisken.com Drafts; validation draft #1 passed all checks (recipient / subject / skim-link / pptx / BCC / is-draft / mailbox allowlist).
5. `.scratch/t3_verify_drafts.py` — B2 batch verify: 24/24 present with attachment + link + BCC + still-draft; deep spot-check on 3 (2 booth variants + last A1) confirmed rendering.

### Send
6. Built `.scratch/t3_send.py`: sends the already-verified drafts by id (so exactly what was verified goes out), interleaved by domain + paced ~15s so same-company recipients (Adidas x4, Aramco x3, Hydro/Vodafone/Mobily/Roche x2) never hit a gateway together.
7. Readiness PASS (24/24 found, all draft+attach+bcc), then sent: **24/24 sent, 0 failed**, all 24 reconciled in Sent Items (21:34–21:40Z).

---

## Key Decisions Made
### Load-as-drafts then send-via-Graph, not a direct blast
- **Choice:** Load 24 drafts into Dirk's box first (reversible), verify, then send the verified drafts by id from Dirk's mailbox.
- **Rationale:** Matches the deliverability design Dirk approved (one-to-one from his real mailbox); sending the verified drafts guarantees the sent mail === the verified mail (attachment + BCC + link intact).

### Pace + interleave the sends (operator judgment, autonomous)
- **Choice:** ~15s gap, round-robin by domain, rather than a 3-second burst of 24.
- **Rationale:** Adidas (4) and Aramco (3) would otherwise see near-simultaneous cold mail at one gateway. Interleaving spread each company's recipients minutes apart. Applied without asking — it serves the user's actual goal (delivered, not spam-foldered).

### Zoho BCC kept per house convention
- **Choice:** Baked the Zoho dropbox BCC into all 24 (flagged to user, offered to strip).
- **Rationale:** The standing Dirk-loader convention (reference_dirk_outlook_com_drafts) files each send into CRM. User proceeded ("send") after it was flagged.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.scratch/t3_load_drafts.py` | Created | Idempotent draft loader (parse wave → 24 drafts, pptx + link + BCC, validate #1) |
| `.scratch/t3_verify_drafts.py` | Created | B2 batch verify of the 24 drafts |
| `.scratch/t3_send.py` | Created | Paced + interleaved sender (sends verified drafts by id) |
| `workspace/clients/brisken/context/lead-generation/rome-t3-wave-rebuilt.md` | Modified | Operational record flipped to SENT 2026-07-21 + next-step note |

---

## Current Status
Rome T3 touch-1 is fully out: 24/24 sent from dirk.neumann@brisken.com, 0 failed, all in Sent Items, all filed to Zoho via BCC. The TreasuryCentral resources page (resources.brisken.com/treasurycentral.html, 3-pillar story) is live and linked in every email. Nothing pending on the send itself.

---

## Next Steps
1. **Watch for replies** — scan both Brisken mailboxes (Graph, all folders) for T3 responses; strip OOO, real replies only.
2. **Touch-2 to non-responders** ~12 days out (~2026-08-02): short one-pager bump, then stop (no third email). `.scratch/t3_send.py` is adaptable.
3. **Rotate the Vercel token** pasted in the prior transcript (user action).
4. Update `status/p2-rome.md` "Post-event follow-up" element to reflect T3 sent (done this checkpoint).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/context/lead-generation/rome-t3-wave-rebuilt.md` (the wave copy + SENT record)
- `.scratch/t3_send.py` / `.scratch/t3_load_drafts.py` (the send tooling, adaptable for touch-2)
- `workspace/clients/brisken/status/p2-rome.md`

### Open Questions
- None blocking. Touch-2 copy is drafted in the layout Dirk approved; confirm timing/list (non-responders only) nearer the date.

### Working Notes
- Graph app-only send works cleanly from dirk.neumann@brisken.com (Mail.Send granted). Sending an existing draft by id (`POST /messages/{id}/send`) is naturally idempotent per run — a sent draft leaves the Drafts folder, so a re-run can't double-send.
- Attachment inline (base64 in the create payload) is fine under ~3 MB; the pptx is 0.45 MB.
- Interleave-by-domain + 15s gap put same-company sends 2–6 min apart (verified in Sent Items timestamps).

### Reference Materials
- Live page: https://resources.brisken.com/treasurycentral.html
- rule_brisken_graph_first (Graph-only for M365, HARD mailbox allowlist)
- memory: reference_dirk_outlook_com_drafts (Zoho BCC convention), project_brisken_rome_tier3_is_drafts

---

## How to Continue
The wave is sent; the next active task is reply-watching and, ~Aug 2, touch-2 to non-responders. Re-run a both-mailbox Graph reply scan whenever the user wants a read on engagement.

---

## Strategic Feedback

### What Worked Well This Session
- Terse, high-trust authorization ("greenlight to send" → "send") let the invasive gate run cleanly: scope-of-effects + readiness + execute, no round-trips. The pre-loaded, pre-approved copy meant the send was mechanical.

### Suggestions
- For touch-2, decide up front whether the Zoho BCC should apply to a bump email (it will double-file the thread). One-line call now saves a flag later.

### System Health
- The invasive-send flow is now well-tooled but entirely in `.scratch/` (load → verify → paced-send). If Brisken outreach sends recur, this trio is a candidate to promote into a real `tools/brisken-graph-send.py` with the allowlist + pace + BCC + readiness baked in, rather than re-deriving per wave.
- Autonomy score: 1 human intervention this session (one B1 closing-offer caught by the stop-b1-gate hook, then acted).
