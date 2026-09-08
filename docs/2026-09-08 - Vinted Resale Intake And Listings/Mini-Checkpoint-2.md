# Mini-Checkpoint: Vinted Resale Intake And Listings

**Date:** 2026-09-08
**Status:** Delivered; iCloud upload still draining
**Type:** mini

---

## Summary

Filed 31 resale items (100 photos, 152 MB) out of the owner's iCloud mailbox into
`iCloudDrive\Vinted` as numbered per-item folders, diagnosed and fixed an 11-day
iCloud Drive sync outage found in the process, then read every photo and wrote a
paste-ready Vinted listing (DE + EN) into each folder.

## What Was Done

- **Intake.** Items arrive from `matneumann07@gmail.com`, NOT the iCloud address, so
  an IMAP `FROM neumath4` search returns zero and looks like nothing exists. 31 mails,
  INBOX seq 2602-2632, subject = item name, body always "Sent from my iPhone".
- **Filing.** `NN - Item Name` folders, photos renamed `01_IMG_4914.jpeg` so attach
  order (= cover shot first) survives sorting. Verified 100/100 on sha256, byte length
  and JPEG decodability; 0 duplicates, 0 strays.
- **Sync outage (the real find).** iCloud Drive had thrown `kAOSErrorInvalidCredentials`
  6,397 times since Fri 2026-08-28 08:26, 0.7s after daemon launch. Nothing synced for
  11 days; 362 items / 237 MB stuck across Vinted, UnpauseAI, Personal, Studium.
  Surfaced the sign-in window; after auth the daemon wedged again (0.00s CPU over 20s,
  no log or db write for 12 min, no TCP to Apple) on broken parent-chain records.
  Stop + relaunch of the three daemons cleared it; backlog drained 362 → 240.
- **Listings.** Read all 100 photos and wrote `LISTING.txt` per folder: copy-ready title,
  attributes block, description in German (Vinted DE) and English.

## Current Status

31 folders + `_INDEX.md` + 31 `LISTING.txt` on disk and verified. iCloud upload still
running on its own; Vinted uploads LAST because the queue is `item_rank` ordered and it
is the newest content. Watcher deliberately stopped at owner request.

Items worth more than their email subject suggested: 01 is a Balenciaga Track sz 45
(subject said "Black shoes"), 13/14 Gallery Dept., 28 Corteiz, 06 Levi's SilverTab
W31 L30, 05 an Outlander Western pearl-snap XL.

Two errors caught that would have cost returns: item 12's label reads `G` +
`PRODUTO NACIONAL` (Brazilian sizing, G ~ L, not S); item 30 is sage/grey-green, not
beige as the subject said.

Items 03 (Fenix HM70R headlamp) and 04 (six devices: 2x Surface + Type Covers, Lenovo
P2a42, TI-30XS) are not Vinted categories; routed to eBay Kleinanzeigen with a
factory-reset + `Sur15` inventory-sticker warning written into the listing.

## Next Steps

1. Pricing: 31 items unpriced. Needs sold-comp research, especially the Balenciaga,
   Gallery Dept. and Corteiz pieces.
2. 16 items have no legible size in-photo (2, 7, 8, 9, 10, 14, 19, 20, 21, 22, 23, 24,
   25, 26, 27, 31) and 8 no legible brand (7, 9, 11, 12, 21, 23, 24, 27); each
   `LISTING.txt` says where to look. Item 19 (Lacoste) needs numeric-size conversion.
3. Confirm the iCloud backlog reaches 0 and Vinted shows 134/134; re-run
   `.scratch/vinted/progress.py`.
4. Split item 04 into one eBay Kleinanzeigen listing per device, with fresh per-device photos.

## Files to Read First

- `C:\Users\neuma_p1qrsic\iCloudDrive\Vinted\_INDEX.md` (the item roster)
- `~/.claude/projects/.../memory/project_vinted_resale_intake.md` (intake shape, the
  wrong-sender trap, script inventory)
- `.scratch/vinted/` — `extract.py`, `verify.py`, `make_index.py`, `make_listings.py`,
  `progress.py`, `syncdiag.py`, `restart_icloud.ps1`
