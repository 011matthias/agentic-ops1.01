# Checkpoint: Brisken September Month End And Invoice

**Date:** 2026-10-02
**Status:** September closed and billed; invoice 01-01111 and the grand total sheet delivered to Dirk and Criss

---

## Summary

September's hours were completed to month end (192.00h in the book), invoice 01-01111 was built from the August template with its figures read out of the workbook, and both documents went to Dirk and Criss in one mail, verified on the sent copy. Two detours cost most of the session: I built a grand total sheet that already existed, and the owner had to point out that every hours workbook opened on the wrong tab.

---

## What Was Done This Session

### Hours completed through month end
1. Logged Sep 21-27's remainder (23.01h: Friday the 25th at 16.34h across five blocks, Sunday the 27th at 6.67h; Saturday has zero commits and stayed a zero day), then Sep 28-29 (8.67h). The book closes at 192.00h.
2. Built the Sep 21-27 weekly sheet (62.83h), the heaviest week in the set, and sent it to Dirk. Verified from Sent Items: attachment present, `isDraft=false`, nothing left in Drafts.
3. The widened estimating basis is now standing rather than something the owner has to ask for each time; recorded in `feedback_hours_tracker_format` after the third request.

### The invoice
4. Invoice **01-01111**, Aug 24 to Sep 27, 183.33h at EUR 14 = **EUR 2,566.67**. The number was read off the three prior sources (01-01108 June, 01-01109 July, 01-01110 August) rather than inferred, and no 01-0111x existed anywhere in the finance archive.
5. The generator reads hours from each table's Start/End and computes amounts from exact minutes, so no figure on the invoice was typed by hand. Verified by extracting the PDF's own text: every figure present, no surviving August token.
6. Owner dropped the Sep 28 week from the invoice late in the session. That also removed the budget problem: billed September-dated hours land at 159.33h, inside the 160h cap, so the overflow rule never had to fire. The 8.67h stays in the sheet on its true dates and carries to 01-01112, stated on the invoice face.

### Default tab, and the hole behind it
7. All eleven hours workbooks opened on OneAssessment or Lead Generation. Fixed to the expense-recon tab, resolved by TABLE name (`HoursLog`) because June's is titled "Timesheet". Verified by opening each in Excel and reading the active sheet back: 12 of 12.
8. Patched both builders (`build-brisken-week-sheet.py`, `roll-hours-month.py`) so the next weekly build and the October rollover cannot regress. Proved it by regenerating `sep14-20` through the patched tool.

### The send
9. One mail to Dirk and Criss with both attachments. Before sending, recalculated and saved the workbook through Excel to bake the formula cache, because openpyxl stores formulas with no cached values and that is exactly how a sheet reached Dirk showing zero hours on 2026-08-24. Confirmed with a cached-values-only read: zero dated rows without an Hours value.

---

## Key Decisions Made

### The Sep 28-29 overage stays on its true dates
- **Choice:** logged 8.67h on 28 and 29 September rather than moving the over-160 portion onto Aug 27 and Aug 30 as the overflow rule directs.
- **Rationale:** the rule acquired a cost it did not have when it was set. The Aug 24-30 weekly sheet went to Dirk on 21 September showing 24.00h, and re-dating into that week would put a delivered sheet at odds with the grand total. Dropping the week from the invoice then made the question moot.

### The grand total sheet is the month workbook, not a new artifact
- **Choice:** reverted a standalone cycle-summary workbook and a Month Summary tab; the month workbook itself is the grand total sheet.
- **Rationale:** owner correction, twice. See What Did NOT Work.

---

## What Did NOT Work (and why)

- **Concluding no grand total sheet existed.** I scanned tab names across `workspace/hours-tracker/**` and reported that nothing rolled the weeks up. The sheet existed: it is the month workbook, and the August copy in `Documents/.../timesheets-submitted/` carries a `Month Summary` front tab whose last row literally reads "Aug 24 to 31, follows with the next sheet". My scan never left the repo and I never asked. Two artifacts were built on that false premise and both were deleted.
- **A standalone cycle-summary workbook plus a tool to generate it.** Correct diagnosis of a real gap (nothing spanned the month boundary), wrong conclusion, because the gap was already solved elsewhere. Deleted along with its `INDEX.md` row and the branch and worktree started for it.
- **A `Month Summary` tab bolted onto the September book.** Second attempt, also wrong: the owner wanted the grand total kept as its own file, not a summary layered onto the working book. Removed.
- **The exact-minutes footnote on the first invoice render.** It printed `(174,42 h)`, the rounded figure, contradicting its own sentence; August's cited the true `15,9833 h`. Caught before sending and corrected to 4 decimals.
- **A script run from the Windows Temp root.** A sibling session left a `types.py` there, which shadows the stdlib for anything whose `sys.path[0]` is that directory, so `import subprocess` died inside `functools`. Moved to this session's own scratchpad rather than deleting another session's file.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/hours-tracker/hours-tracker-2026-09-september.xlsx` | edit | Sep 21-29 rows, 31.68h; formula cache baked before send |
| `workspace/hours-tracker/weekly/hours-tracker-2026-09-week-sep21-27.xlsx` | create | the week sent to Dirk |
| all 11 hours workbooks | edit | default tab set to expense recon |
| `tools/build-brisken-week-sheet.py` | edit | sets the default tab on build |
| `tools/roll-hours-month.py` | edit | sets the default tab on rollover |
| `Finance/Brisken-Direct/invoice-sources/InvoiceMatthiasBrisken-261002.html` | create | invoice 01-01111 source |
| `Finance/Brisken-Direct/invoices/InvoiceMatthiasBrisken-261002.pdf` | create | the delivered invoice |
| `memory/feedback_hours_tracker_format.md` | edit | widened estimating basis as standing |
| `.scratch/build-september-invoice.py`, `.scratch/send-month-end.py` | create | generator and guarded sender |

---

## Current Status

September book: 192.00h (Expense Reconciliation 174.42h, Lead Generation 17.58h), of which 24.00h is the carried Aug 24-30 week and 168.00h is September-dated.

Billed on 01-01111: 183.33h / EUR 2,566.67, period Aug 24 to Sep 27. Delivered 2026-10-02T07:08:55Z to Dirk and Criss with both attachments, `isDraft=false`, Drafts clean.

Carrying to 01-01112: the week of Sep 28, 8.67h, already in the sheet on its true dates.

Ops status: `platform: unknown plan, ~?/? ops/mo. Last assessed: ?`.

---

## Next Steps

1. October's rollover: `uv run tools/roll-hours-month.py --month 2026-10`. Check `--status` on September before rolling, since the logger reaches only the latest book afterwards.
2. The Sep 28 week is the first entry of the next cycle; 01-01112 starts there.
3. `p2-lovable-rebuild` and `p2-onepilot-site` status files are 22 days stale; bring current from a p2 session rather than guessing from p1.
4. Record a Brisken ops feasibility assessment; `infrastructure.yaml` carries no plan or volume figures.

---

## Context for Next Session

### Files to Read First
- memory `feedback_hours_tracker_format.md` (structure, rollover, the widened basis) and `project_brisken_hours_budget_160.md` (the cap and the real-hours-only boundary)
- `.scratch/build-september-invoice.py` (the invoice generator; change NUMBER, ISSUED, CUTOFF, PERIOD)

### Open Questions
- Does the 160h budget renew for October, and does it still mean September-dated hours only now that a carried week sits in the book?
- The rate. September billed 183.33h at EUR 14. The owner's own recorded rate for personal work is USD 36-50/hr, and the EUR 600/mo licence proposal has been held to 01-10 since before this session.

### Working Notes
- Invoice numbering is strictly sequential from 01-01108 (June). Next is **01-01112**.
- The invoice's own convention: hours shown to 2dp, amounts computed from exact minutes, and the footnote cites the first line whose exact value is not already clean at 2dp.
- Weekly sheet totals as delivered: Aug 24-30 24.00, Aug 31-Sep 6 8.00, Sep 7-13 30.17, Sep 14-20 58.33, Sep 21-27 62.83.
- The month book's by-week block now carries SIX Monday slots (Aug 24 through Sep 28), the sixth added so the carried August week still foots. October's rollover will re-anchor to October's Mondays.
- Chrome renders the invoice PDF; Edge headless fails silently on this machine.

### Reference Materials
- `tools/log-brisken-hours.py`, `tools/build-brisken-week-sheet.py`, `tools/roll-hours-month.py`
- `~/Documents/UnpauseAI-Backup/UnpauseAI/Finance/Brisken-Direct/` (invoices, invoice-sources, timesheets-submitted)

---

## How to Continue

October runs the same loop: log against the commit record on the widened basis, build each closed week's sheet on the Monday after, and close the month with a grand total plus the next sequential invoice. Nothing is pending on September.

---

## Strategic Feedback

### What Worked Well This Session
- Recalling the 2026-08-24 zero-hours incident before attaching the workbook. The formula cache was genuinely empty, so without that memory the same broken sheet would have gone to Criss and Dirk a second time. The cached-values-only read is a cheap check worth keeping as the pre-send step for any xlsx.
- Reading figures out of the workbook rather than typing them. The invoice generator means the only way a wrong number reaches the PDF is if the sheet itself is wrong.

### Suggestions
- The default-tab defect is the shape worth generalising: every verification this project runs checks the DATA (tab totals, `ties to table`, by-week footing) and none of it checks what the recipient's first screen looks like. Several of those books had already been delivered. A deliverable check that opens the file as the recipient would, and asserts the landing tab, would have caught in August what the owner caught today.
- The grand total detour would have been avoided by one question or one `find` outside the repo. Before concluding an artifact does not exist, search where the delivered copies live, not only where the working copies live.

### System Health
- Autonomy: 6 human interventions, elevated. Four were corrections of my own wrong turns (two on the grand total sheet, one on the default tab, one on the invoice scope), which is the real signal here rather than the count.
- The friction register advisory said 363 KB with 82 resolved rows archivable, but by the time this checkpoint ran the archiver reported nothing to move: a sibling session had already taken them. Nothing to do here, and worth knowing that the advisory's numbers go stale inside a single checkpoint when siblings are live.
