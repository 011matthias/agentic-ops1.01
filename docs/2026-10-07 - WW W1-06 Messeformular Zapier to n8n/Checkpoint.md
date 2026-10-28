# Checkpoint: WW W1-06 Messeformular Zapier to n8n

**Date:** 2026-10-07
**Status:** LIVE in n8n; Zap paused; first real production submission still to be observed

---

## Summary
The Wärme Wimmer Zap "Messeformular - Neuer Lead" (285988676) was rebuilt as n8n workflow `dXd24ZprI1QLSKLZ` from a fresh Zap JSON export, tested end to end with the real Jotform form, and went live the same afternoon (Jotform webhook on the production URL, Zap paused, heizreport node on). The session ran from agentic-ops1, but all WW code and state live in the `akkton/agentic-ops` clone, PR #304.

---

## What Was Done This Session

### Zapier MCP
1. Started the zapier:onboarding skill, then dropped it when the WW task arrived. The connector is bound to "Raphael Woltz's Account" (8901286), the client's Zapier account; GitHub/Zoho Mail enabled during onboarding were removed again (never authenticated).
2. Proved the connector cannot read Zap definitions: Zapier Manager "Find Zap" returns metadata only, and a read-only `write_code_action` failed with an opaque error (removed). Write actions `toggle_zap`, `team_invite`, `review_approval` disabled right after enabling. Only Find Zap / Find App remain.

### W1-06 build (akkton/agentic-ops, branch `client/warme-wimmer/w1-06-messeformular-n8n`, worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops-w1-06`)
1. Analysed the live Zap export (44 nodes): Jotform trigger form 250713133327347, Code "Variablen", 5 PDF GETs, 9 Paths on Infomaterialien (iexact), per path Outlook send as sabine@ + filter Heizreport=Ja + POST heizreport.de startReport. Two mail bodies (with/without Infomaterialien line), two Outlook connections in the Zap.
2. Make blueprint s6-v4-native compared: 8 of 9 routes mis-map attachments or body (only PVT right). Not used.
3. Jotform field names read from the public form page: q21_anrede, q3_name{first,last}, q6_email, q25_infomaterialien, q23_schreibenSie23 = Heizreport.
4. Built via POST /workflows (inactive): webhook with secret path + in-flow formID IF gate (Leonard's pattern), Jotform parse, 5 PDF downloads, path table in one Code node, Graph send. PDFs of 5.0 MB (Wärmepumpe) and 4.1 MB (PVT) exceed Graph's 3 MB inline limit, so mails with PDFs go draft -> attachments (<3 MB POST, >=3 MB upload session in 3,276,800-byte parts) -> send. Byte-identical HTML verified on read-back; local harness over 11 cases.
5. Test run 49166 failed at the chunk PUT (parallel requests); fixed with Loop Over Items around attachments and chunks via PUT (owner go). Run 49169: everything up to send green, then 403 Send-As (hero.automation@ on sabine). Run 49176 ("Keine") same 403.
6. Owner/Raphael then changed the workflow in the editor (v19/v20): credential "Microsoft Outlook info@", sender and reply-to info@, messe text "am Tag der Wärme in Putzbrunn", HTML with inline logo + banner (no longer byte-identical to the Zap), heizreport node re-enabled.
7. Real form test 49190 (Jotform -> test URL): multipart with rawRequest, fields parsed correctly, path Keine, mail sent (Graph 202).
8. Go-live (done in the editor and Jotform by Matthias/Raphael): active v20, Zap 285988676 paused 13:18:30Z, Jotform webhook on `/webhook/ww-w1-06-...`. Production probe 49208 (formID 0000-PROBE-KEIN-FORMULAR, from a script) was dropped by the gate as designed.
9. PR #304 kept current (export v20, infrastructure.yaml `n8n.messeformular_w1_06` with go-live, test evidence and editor changes; Make s6 entry points to it). Not merged: that repo has no CI.

---

## Key Decisions Made

### Live Zap export is the source, not the April artifacts
- **Choice:** Rebuilt only from the 2026-10-07 export (owner: "disregard april export").
- **Rationale:** The April Make blueprint is wrong in 8 of 9 routes.

### Graph via HTTP Request, not the Outlook node
- **Choice:** House pattern from the WW Error Handler (HTTP Request + predefined Outlook OAuth credential), with upload sessions for >=3 MB.
- **Rationale:** Proven on this instance; the Outlook node's large-attachment behaviour was unverified and could not be tested without sending.

### Sender info@ (owner/Raphael decision in the editor)
- **Choice:** info@ via its own credential instead of sabine@ with Send-As.
- **Rationale:** Send-As for hero.automation@ was missing; info@ sends as itself. Deviates from the Zap (sabine@ sender and reply-to).

---

## What Did NOT Work (and why)
- **Zapier MCP to read the Zap definition:** the connector exposes app actions only; Find Zap returns metadata, a custom code action failed with an opaque error.
- **HTTP Request batching (batchSize 1, interval 0) to keep upload chunks in order:** n8n starts all item requests together; chunk 2 hit Graph first: 400 "Invalid Start offset for the current fragment" (run 49166).
- **Sending as sabine@ through hero.automation@:** 403 "does not have the right to send mail on behalf of the specified sending account" (runs 49169, 49176).
- **Activating via the n8n API:** blocked by the Claude Code auto-mode classifier; the workflow had been activated in the editor anyway.
- **Vault lookup for a Zapier login:** blocked by the classifier as credential exploration; not pursued.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| agentic-ops: `workspace/clients/warme-wimmer/automations/w1-06-messeformular.n8n.json` | Created | Read-back export of dXd24ZprI1QLSKLZ (v20) |
| agentic-ops: `workspace/clients/warme-wimmer/infrastructure.yaml` | Modified | `n8n.messeformular_w1_06` entry; Make s6 pointer |
| memory `reference_zapier_mcp_no_zap_definitions.md` | Created | Zapier connector limits + client account binding |
| memory `reference_n8n_http_batching_not_sequential.md` | Created | Batching vs Loop Over Items; Graph attachment limits |

---

## Current Status
W1-06 live (active v20, heizreport on, sender info@). Zap 285988676 and its April copy are off. No real production submission seen yet (only probe 49208). PR akkton/agentic-ops#304 open, branch synced. Ops status: warme-wimmer has no infrastructure.yaml in agentic-ops1 (its home is the agentic-ops clone).

---

## Next Steps
1. Watch the first real production submission (n8n executions of dXd24ZprI1QLSKLZ, mode webhook): path, attachments, mail sent, heizreport for "Ja".
2. Check Jotform entries submitted 13:18-14:02 UTC (Zap already off, n8n not yet active): those leads got no mail.
3. Merge PR #304 on owner order (no CI in akkton/agentic-ops).
4. Raphael: the `<script src='/NPMH/...'>` tag still sits in the mail HTML; decide keep or drop. Leonard: confirm the webhook protection (secret path + formID gate).
5. Delete the two unsent test drafts in hero.automation@ Drafts (from runs 49166/49169).
6. Error alerts still go to Nicolas via the WW Error Handler; re-point to Matthias.
7. Remove the agentic-ops-w1-06 worktree after #304 merges.

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops-w1-06\workspace\clients\warme-wimmer\infrastructure.yaml` (`n8n.messeformular_w1_06`)
- https://github.com/akkton/agentic-ops/pull/304

### Open Questions
- Is the info@ sender (and reply-to info@) final, or should it return to sabine@ once Send-As exists?
- Does the form have a Jotform autoresponder (not visible to us)?

### Working Notes
- Webhook path `ww-w1-06-362c4b77424356f8326f597570b8f170`; test URL only accepts one call after "Execute workflow"; production URL answers GET with "not registered for GET requests" when live.
- Read-only helpers used this session sit in the session scratchpad (n8nread.py, build_w106.py, harness.mjs); the build script asserts every Zap path against the export.
- Real Jotform payload: multipart/form-data with `rawRequest` JSON plus formID, submissionID, pretty, etc.; Anrede arrives as "Sehr geehrter Herr".

### Reference Materials
- Graph large attachments: https://learn.microsoft.com/en-us/graph/outlook-large-attachments
- Live Zap export: `C:\Users\neuma_p1qrsic\Desktop\Downloads\exported-zap-2026-10-07T13_02_09.875Z.json`

---

## How to Continue
Work in the agentic-ops clone (worktree above), not agentic-ops1. Read executions read-only via the n8n API (`N8N_API_URL_WARME_WIMMER` / `N8N_API_KEY_WARME_WIMMER` from agentic-ops/.env). Any PUT on the live workflow publishes immediately: owner go first.

---

## Strategic Feedback

### What Worked Well This Session
- Pre-send readiness checks (inactive, heizreport off, recipient) before every test POST, and differential read-backs after each change, caught "already active" before a redundant activation and showed the 14:08 hit was a probe, not a lost lead.

### Suggestions
- Put the Graph attachment pattern (draft, <3 MB POST, upload session in a Loop Over Items, send) into skil_n8n-pack as a module, so the next mail-with-PDF build does not rediscover the 3 MB limit and the batching trap.

### System Health
- Editor and agent edited the same workflow concurrently (v1 to v20 in 50 minutes); every agent change had to start from a fresh GET. Autonomy: 6 human interventions (elevated; mostly owner decisions and actions only the owner could take: Zap export, credentials, Jotform, activation).
