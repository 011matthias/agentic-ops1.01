Continue the Brisken 2026_PPTX SharePoint deck-library reorg. Read the checkpoint first: `docs/2026-07-16 - Brisken 2026_PPTX Deck Library Reorg/Checkpoint.md` — it has the full manifest, duplicate-pair verdicts, and scope-of-effects.

State: the manifest is built and owner-amended (added an empty `Asset Testing` folder). **Nothing has moved yet** — this is an invasive live-SharePoint write, gated on an explicit owner yes.

1. Re-list the live `2026_PPTX` library (CDP Edge :9222 + SP REST — reuse `.scratch/deckgen/_sp_inventory.py`, re-run it fresh since Dirk edits these decks directly and this session may be hours old) and diff against `.scratch/deckgen/_inventory_2026-07-16.json` to confirm nothing drifted since the manifest was built. If it drifted, re-resolve only the changed files against the same duplicate-pair logic (modified date + bytes + version count) before touching anything else.
2. Re-present the manifest from the checkpoint's Working Notes section and get the owner's explicit yes (a plain "yes" = execute as-is; otherwise take the named changes).
3. On yes, execute via SharePoint `MoveTo`/`rename` REST calls (not download-reupload, so version history survives) for all 32 relocated files into the 8-folder structure. Recycle the emptied `Client Collateral WIP` folder (restorable, don't delete permanently).
4. Re-list everything post-move; confirm the before→after tree matches exactly (right file counts per folder, root left with 0 loose files).
5. Refresh `workspace/clients/brisken/deliverables/lead-generation/rome-2026/decks/README.md` and `call-collateral/README.md` — update SharePoint path references to match the new folder structure (content mirrors don't move, only the path text in these two READMEs).
6. Draft (do NOT send) a 5-line notification-style mail brief to Dirk on the new folder map, per `feedback_dirk_email_notification_style` memory (lead line what+where, bullets, <~120 words, one soft ask, clickable links). Show the draft; do not send.
7. Confirm the Sanofi deck's new path (`Client Deliverables/Sanofi/`) is correct in that brief — the Sanofi call is Friday 2026-07-17 16:00 and that deck is the one file with a real deadline riding on this landing correctly.

Open question to flag to the owner if not yet answered: does Dirk still work from the merged `Digital Co-Worker & Trade Automation 2026-07.pptx`, or is it fully superseded by the standalone `with UCs` rework? The manifest currently routes it to Archive.
