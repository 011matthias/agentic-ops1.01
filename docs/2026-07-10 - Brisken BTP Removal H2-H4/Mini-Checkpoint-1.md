# Mini-Checkpoint: Brisken BTP Removal H2-H4 (closure)

**Date:** 2026-07-10
**Status:** COMPLETE. All three held actions closed and origin-verified; Planner task at 100%.
**Type:** mini

---

## Summary
H2 delivered and verified after the full checkpoint was written: the owner applied the Lovable prompt to project `43ba7ecd-d250-48d5-9c6f-b34ea82f3be4` (rome2026.brisken.com) and the clean onepager PDF was re-hosted on resources.brisken.com. Every surface flagged by the 2026-07-09 BTP audit is now clean.

## What Was Done
- Deployed the clean onepager PDF to resources.brisken.com with Matthias's Vercel token (the CLI's akkton login cannot reach his team); verified from origin: 200, 145,421 B, gate exit 0 on served bytes.
- Handed the owner a two-change Lovable prompt (delete the SAP BTP creds span; repoint the onepager link to the resources URL and delete the stale local PDF). Owner published it.
- Origin-verified the publish (background watcher + independent re-check): page 0 hits for both banned patterns, creds strip correct, old `/brisken-rome-2026-onepager.pdf` now 404, new link serves the clean file.
- Marked Planner task `mJrjdoY1yUKp0gNxDld7LWUAAL_e` "Exclude BTP from all demos" to 100% via etag-guarded PATCH; readback verified (re-confirmed at user request before this checkpoint).
- Closure logged in comms-log.md; full checkpoint's Status/Current Status updated (commit 311e94e).

## Current Status
BTP removal is 100% complete across repo, resources.brisken.com, rome2026.brisken.com, SharePoint 2026_VIDEO, and brisken-onepilot-proto.fly.dev. Collateral PDFs now live on resources.brisken.com, so future updates are a direct redeploy; Lovable is out of the loop for file assets.

## Next Steps
1. USER: merge PR #207 (CI green): `bash tools/gh-merge.sh 207`.
2. USER: vault the Vercel token (`uv run ~/vault.py add "Vercel Matthias"`; it appeared in chat, rotate at 30-day expiry).
3. Plan the proto migration to a brisken.com home, then take brisken-onepilot-proto down (owner directive 2026-07-10).
4. Resolve PR #201's conflict with main so CI can run on this branch.

## Files to Read First
- `docs/2026-07-10 - Brisken BTP Removal H2-H4/Checkpoint.md` (full session record, updated with the closure)
- `tools/fixtures/demo-banned-terms.json` (the directive + exemptions)
