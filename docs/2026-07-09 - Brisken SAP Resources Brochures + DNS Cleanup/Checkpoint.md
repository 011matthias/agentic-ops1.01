# Checkpoint: Brisken SAP Resources Brochures + DNS Cleanup

**Date:** 2026-07-09
**Status:** COMPLETE for the DNS tail. Changes (2 of 3) live + verified + documented; change record + restore snapshot uploaded to SharePoint + verified; Dirk notified by email (sent + verified as Matthias). Only onepilot.ai apex decision + SAP concise-vs-richer choice remain.

---

## Summary
Built 6 on-brand SAP Resources brochure one-pagers and hosted them live on a new `resources.brisken.com` subdomain (Vercel); mapped Brisken's full 22-domain / DNS / redirect landscape across GoDaddy + Namecheap; and executed 2 of 3 Dirk-approved DNS cleanups (redirect normalization + dead-record removal) with a full restore baseline, deferring the third (onepilot.ai) as a live customer domain.

---

## What Was Done This Session

### SAP Resources brochures + hosting
1. Produced 6 dark-cockpit one-pagers (Market Data Hub, Brisken Smart Trading, Remittance Advice Gate, Bank Fee Portal, TreasuryCentral, OnePilot). Single A4 page each, ~260-277 KB, zero em-dashes, PDF text scanned clean of banned words. Masters in `deliverables/lead-generation/sap-assets/*-onepager.pdf`; render source `.scratch/brisken-sap-assets/gen_onepagers.py`.
2. Hosted them live at **`resources.brisken.com`** on a dedicated, isolated Vercel project `resources-site` (`prj_9EDCYbR0tJV7dwe8aC6HxbQYpuH9`, team matthias-neumanns-projects), NOT the live-site project. Deploy dir `workspace/clients/brisken/resources-site/` (clean-named PDFs + branded `index.html`). Verified: all 6 serve HTTP 200 `application/pdf` over HTTPS; domain verified + configured on Vercel.
3. Updated deliverable `sap-surfaces-repositioning.md` §1 to the real live tab (10/10 cards, not the stale 4) with the final rebalance plan + paste-ready copy + live links.
4. Compared the 4 existing brisken.io brochures vs ours: ours win on current brand, correct naming (retires TraderPlus/SAP TPI), grammar, no slop; the old flyers carry more capability depth. Card 03 (SAP's own 12-page Blueprint) kept untouched.

### Domain / DNS overview + cleanup
5. Discovered both registrar APIs now work (creds in `context/registrar-api.env`). Mapped 22 domains: GoDaddy 9 (brisken.com, onepilot.ai, frag-ulf.de, alpharates.*), Namecheap 13 (brisken.io + 10 brisken.* variants + verve.works + opentickers.com). Built full live DNS + HTTP-redirect map.
6. Emailed Dirk the 3 recommended fixes (from Matthias.Silva@brisken.com, comms-critic passed, sent + verified 02:38). Dirk approved 02:40 with the condition "record and document so we can restore".
7. Captured a full read-only restore baseline (`snapshot-2026-07-09T024600.json`), then applied via API:
   - **10 brisken.* domains -> permanent 301 to https://brisken.com** (was mostly the brisken.io placeholder; brisken.in loop fixed). Email/verification records preserved; **brisken.co Outlook MX + DKIM + SPF verified intact** post-change.
   - **Deleted 3 dead GoDaddy records** (events, www.events -> Wix 404; sap-ai-brief-orig). Zone 86 -> 83.
   - Each verified live (`http 301 -> brisken.com`; deleted records confirmed absent).
8. Wrote the restore-capable change record (`brisken-dns-change-record-2026-07-09.md` + PDF, 6 pages).

### Record to SharePoint + Dirk notification (continuation session)
9. **Root-caused the SharePoint "block":** it was never a SharePoint problem. Git Bash's MSYS path conversion rewrote the leading-slash argument `/sites/MARKETING/...` into `C:/Program Files/Git/sites/MARKETING/...` before it reached the API, producing the 400 `URL is not web relative`. `General` has the plain SRU `/sites/MARKETING/Shared Documents/General`; the Teams-channel hypothesis was wrong. Fix: run the tool with `MSYS_NO_PATHCONV=1`.
10. **Uploaded both artifacts to SharePoint** `Marketing > Documents > 20_Assets > DOMAIN DNS REGISTRY` (a purpose-built folder that already held "COmpare TXT records for ZOHO.xlsx"): `brisken-dns-change-record-2026-07-09.pdf` + `brisken-dns-restore-baseline-snapshot-2026-07-09.json`. Verified via Files API: both present, byte-lengths match local exactly (135843 / 25559).
11. **Notified Dirk by email** (reply in thread "Brisken domains: three fixes worth making"): 2 of 3 done + verified, onepilot.ai held for his destination decision, exact SharePoint location + filenames given. Drafted -> agnt_comms-critic returned OK (Register A, zero em-dashes) -> sent via Outlook COM from Matthias's store. Verified in Sent (Sent=True, 03:31), SenderName "Matthias Silva (Brisken)", sender CN contains 8890599F (Matthias, not Dirk).

---

## Key Decisions Made

### Snapshot-before-change caught a near-miss on onepilot.ai
- **Choice:** Deferred the onepilot.ai fix instead of applying it.
- **Rationale:** The pre-change snapshot revealed onepilot.ai is a LIVE PRODUCTION domain with real customer app environments on AWS (brisken-prod, evonik-prod/qa, lge-prod/qa, nestle-qa, rwz-prod, bat-prod, `*.app` wildcard). Only the apex is Parked. Touching it needs a narrow apex-only scope + destination decision. Snapshot-first is why this was caught before any change.

### Isolated Vercel project for the brochures
- **Choice:** New `resources-site` project, not the live brisken.com project.
- **Rationale:** Avoids redeploying the live site from a dirty working tree (`reference_vercel_force_deploy_uses_cwd_tree`); zero blast radius on brisken.com.

### 301 target = https://brisken.com, preserving email on the redirect domains
- **Choice:** Namecheap `setHosts` rebuilt each domain's full record set, dropping only the old URL/parkingpage-www records and adding clean `@`+`www` URL301, keeping every MX/DKIM/SPF/TXT.
- **Rationale:** `setHosts` is all-or-nothing; a dry-run confirmed brisken.co's email survived before applying.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/deliverables/lead-generation/sap-assets/*-onepager.pdf | Created (x6) | Brochure one-pagers |
| workspace/clients/brisken/resources-site/ (index.html + 6 PDFs) | Created | Vercel deploy source for resources.brisken.com |
| workspace/clients/brisken/deliverables/lead-generation/sap-surfaces-repositioning.md | Modified | Real 10-card tab + final plan + live links |
| workspace/clients/brisken/context/registrar-api.env | Created | Working GoDaddy + Namecheap API creds (gitignored) |
| workspace/clients/brisken/context/dns-changes/ (snapshot, changelog, record .md + .pdf) | Created | Restore baseline + documented change record |
| .scratch/sp_upload.py | Modified | Folders/Files listers return exact ServerRelativeUrl; upload path now URL-encodes folder+name; added `files` verify command |
| SharePoint: 20_Assets/DOMAIN DNS REGISTRY/ (record PDF + restore snapshot JSON) | Uploaded | Client-accessible change record + restore baseline |
| ~/.claude/.../memory/reference_repo_tooling_gotchas.md | Updated | Git Bash MSYS mangles leading-slash args; use MSYS_NO_PATHCONV=1 |
| ~/.claude/.../memory/project_brisken_resources_subdomain_and_dns.md | Created/Updated | resources.brisken.com + GoDaddy API-now-works |

---

## Current Status
Both approved DNS changes are **live and verified**; restore baseline + human-readable record are written, PDF-rendered, **uploaded to SharePoint (20_Assets/DOMAIN DNS REGISTRY) and verified**. **Dirk has been notified by email** (reply in the domain-fixes thread, sent + verified as Matthias). onepilot.ai untouched, awaiting his destination decision. The "record -> SharePoint -> notify Dirk -> checkpoint" tail is DONE.

---

## Next Steps
1. **onepilot.ai:** await Dirk's reply on the apex destination (redirect to the OnePilot page on brisken.com, or serve OnePilot on onepilot.ai with a valid cert), then apply the narrow apex-only fix. Snapshot of its current state is in `snapshot-2026-07-09T024600.json` under `godaddy.onepilot.ai`.
2. **SAP Resources:** confirm concise vs richer (2-page) for MDH + BST, then Dirk pastes cards.
3. **comms-log:** the domain-fixes thread + this notification email are not yet in `comms-log.md` (a parallel session owns that file this session). Log the verbatim thread when that session yields the file.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/context/dns-changes/brisken-dns-change-record-2026-07-09.md (+ .pdf)
- workspace/clients/brisken/context/dns-changes/snapshot-2026-07-09T024600.json (restore baseline)
- workspace/clients/brisken/deliverables/lead-generation/sap-surfaces-repositioning.md (§1)
- .scratch/sp_upload.py, .scratch/brisken_apply_dns.py, .scratch/brisken_dns_snapshot.py

### Open Questions
- onepilot.ai apex: redirect to onepilot.brisken.com, or serve the OnePilot page with a Vercel cert? (live customer domain — apex-only)
- SAP Resources: concise one-pagers or richer 2-page datasheets for MDH + BST?

### Working Notes
- **SharePoint upload block — RESOLVED (root cause: Git Bash, not SharePoint).** The 400 `URL is not web relative` was Git Bash MSYS path conversion rewriting the leading-slash argument `/sites/MARKETING/...` into `C:/Program Files/Git/sites/MARKETING/...` before it ever reached the API. The diagnostic that exposed it: the tool echoed back `folder: "C:/Program Files/Git/sites/MARKETING/Shared Documents"`. Prior-session hypotheses (Teams-channel folder SRU, `GetFolderByServerRelativePath`) were red herrings. **Fix: prefix the Bash call with `MSYS_NO_PATHCONV=1`** (or run via the PowerShell tool). With that, `General` resolves at its plain SRU and any folder is writable. `sp_upload.py` now has `folders` / `files` / `upload` commands; `files` verifies an upload by listing name+length. Tool runs raw CDP against the open MARKETING tab; `connect_over_cdp` HANGS, raw CDP is the path.
- **SharePoint home for DNS records:** `Marketing > Documents > 20_Assets > DOMAIN DNS REGISTRY` (server-relative `/sites/MARKETING/Shared Documents/20_Assets/DOMAIN DNS REGISTRY`). Purpose-built; already held a Zoho TXT-compare workbook.
- **Registrar APIs work:** `context/registrar-api.env`. GoDaddy `PATCH .../records` to append (never bulk-PUT). Namecheap `setHosts` is all-or-nothing per domain (preserve email).
- **Restore:** exact before-values are in the record + snapshot JSON.

### Reference Materials
- resources.brisken.com (live); Vercel project resources-site
- SharePoint site: https://brisken.sharepoint.com/sites/MARKETING (Shared Documents; folders incl. General, 20_Assets, 90_Marketing Agents - Data)

---

## How to Continue
The DNS tail is closed. Next real work is Dirk's onepilot.ai apex decision (then apply the narrow apex-only fix) and the SAP concise-vs-richer choice for MDH + BST. When the parallel session releases `comms-log.md`, log the domain-fixes thread + the notification email verbatim. Registrar APIs, Vercel token, Outlook COM, and the SharePoint uploader (with `MSYS_NO_PATHCONV=1`) are all working.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the full error body (not just the status) instantly exposed the real cause: the tool echoed `folder: "C:/Program Files/Git/sites/..."`, so B3 (read the full error, question my own environment) turned a 3-iteration prior-session block into a 2-step fix.
- Snapshot-before-mutate + dry-run-before-apply (prior session) caught the onepilot.ai live-customer-domain risk. The pattern to keep for all infra mutations.
- Belt-and-suspenders identity control on the outbound send: default-store owner check + explicit `SendUsingAccount` + post-send sender-CN verify, so COM property flakiness could not send as the wrong person.

### Suggestions
- Any Bash-tool call passing a server-relative path or other leading-slash argument on Windows must set `MSYS_NO_PATHCONV=1`, or Git Bash silently rewrites it. Now captured in `reference_repo_tooling_gotchas`.

### System Health
- Autonomy score: 0 — fully autonomous session (user input was "continue").
- The prior-session SharePoint "block" was environment path-mangling, not a capability gap; the fix is a documented gotcha, not new tooling. The reusable `snapshot/apply/record/upload` pattern is proven end to end and could be promoted from `.scratch/` to a committed `tools/` brisken-DNS helper if DNS work recurs.
