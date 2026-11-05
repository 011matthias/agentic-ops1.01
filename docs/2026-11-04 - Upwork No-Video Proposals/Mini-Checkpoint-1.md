# Mini-Checkpoint: Upwork No-Video Proposals

**Date:** 2026-11-04
**Status:** First proposal written; reusable case-study attachment shipped (PR #1727, merged c0a38f89)
**Type:** mini

---

## Summary
Started no-video, mass-production proposal mode on the "Outbound Product Manager: Roadmap, Outreach Systems & AI Agents" posting (German AI-outbound startup, client avg $12.13/hr). Wrote the cover letter in chat and built a reusable two-page outbound case study PDF to attach to outbound and lead-gen jobs.

## What Was Done
- Letter format for no-video mode: opening block at most 225 chars (the client's collapsed preview; this one 218), then a short body carrying the proof the video used to carry, then "How I'd start", organization line, Karlsruhe / German line, sign-off "Matthias". Delivered in chat only.
- Default proof set, all anonymized: Meji = "UK events company", Brisken lead desk = "treasury-software company", WW = "German heat-pump installer". Owner rejected the Brisken expense-recon app as a second Brisken entry.
- `workspace/projects/platform/upwork-agency/assets/outbound-case-study.{html,pdf}`: v1 one page (#1725), v2 two pages (#1727). v2 = three program tiles + five cases, five charts. Every figure traced to Meji `status/enquiry-automation.md`, `context/weekly-summaries/2026-10-30.json`, `docs/2026-07-07 - Meji Media Ops/Checkpoint.md`, Brisken `status/p2-outreach-engine.md` rows 47-48, lead-desk `web/review.py` (booked = contact with a calendar 'booked' event).

## What Did NOT Work (and why)
- **One-page case study on two small samples:** owner: "this really is not enough data". It had n=11 and n=62 and no after-the-fix outcome; the status files held the volume (773, 446, 127/40/20) all along.
- **"12 had written back" lifted from the memory/status row 48:** row 47's breakdown is 2 new replies + 5 earlier relationships + 5 out-of-office. Shipped in v1 and the letter before the breakdown was read; corrected in v2 and a replacement letter line given.
- **"12 domains held out" (approved draft wording):** the comms log counts leads (12 of 145 in October; 63 Mimecast-or-no-MX of 366 in November).
- **`grep --no-ignore`:** GNU grep has no such flag; blocked by `block-grep-no-ignore`. Use `rg --no-ignore` for gitignored `context/`.

## Current Status
PR #1727 merged; origin/main holds the two-page PDF. Primary checkout NOT pulled (a sibling session was live on main). The worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-case-study` (branch merged) still holds the PDF the owner has open to attach. If the letter was already pasted, its Brisken sentence still counts the 5 OOO replies.

Corrected Brisken proof paragraph (use this one):
"I built their lead desk, one pipeline replacing nine scattered sources (sheet copies, send logs, booth notes, Sales Navigator, Outlook drafts), with each contact's stage computed from an event log and a daily mailbox scan. An audit showed why that matters: of 62 contacts checked against the mailboxes, 12 had written to us (7 people, 5 out-of-office replies) and the log held 2 of them. Measured properly, the conference follow-up stands at 127 people reached, 40 in conversation and 20 with a meeting booked."

## Next Steps
1. Next job screenshot: same letter format, pick from the proof set; attach `outbound-case-study.pdf` on outbound / lead-gen jobs.
2. After the PDF is attached: `git worktree remove` the case-study worktree and pull the primary when no sibling is live.
3. `PROPOSAL-TEMPLATES.md` Template 0 assumes a walkthrough link; add the no-video variant (opening at most 225 + body) so the next session does not re-derive it.

## Files to Read First
- `.claude/skills/skil_upwork-proposals/modules/PROPOSAL-TEMPLATES.md`
- `workspace/projects/platform/upwork-agency/assets/outbound-case-study.html`
- `workspace/clients/meji-media/status/enquiry-automation.md`, `workspace/clients/brisken/status/p2-outreach-engine.md` (rows 47-48)
