# Checkpoint: Brisken Rome — Doc Redirects, E2 Send, Booth Prep

**Date:** 2026-06-23
**Status:** Rome event eve (setup Tue 23, conf Wed 24–Thu 25). Lead-gen p2 active.

---

## Summary
Restored Brisken's dead old-Wix document links on brisken.com via clean `/docs/` hosting + 18 redirects (deployed), ran the E2 pre-event campaign send to a cleaned 86-list after a full replier+bounce exclusion audit, traced the dead booth-banner QR to an external agency domain (not fixable from Brisken's GoDaddy), and built the BOOTH-9 AI-readiness kiosk quiz. Email replies on Dirk's behalf were moved to a separate chat (agent will not send as a human).

---

## What Was Done This Session
### brisken.com — old-site documents (Dirk: "Wix links to integrate")
1. Traced the ask: old brisken.com was Wix (Wayback-confirmed); 7 hosted PDFs + page URLs all 404 on the new build.
2. Recovered 5 docs from the Wayback archive (GTC, Supplemental MDH T&C, Privacy 2018 + 2021, Accenture case study); hosted at clean `/docs/` paths.
3. Footer links the current set (Privacy 2021, T&C/GTC, MDH Terms, Accenture case study).
4. `vercel.json`: 18 `308` redirects — 5 dead doc paths + 13 dead Wix page paths (`/sap-consulting`, `/one-pilot-apps/*`, `/rapsody`, `/contact-page`, etc.) → new homes. Deployed to production twice; verified live (all 308 → correct targets, docs 200).

### E2 pre-event campaign send
5. Read the send mechanism (`send-rome-campaign.ps1`, classic Outlook COM as matthias.silva@brisken.com, CC dirk).
6. Pulled E1 replies from Outlook; suppressed 3 engaged repliers (Holcim booked, JTI ×2) before sending.
7. Sent E2 (paused after 10, re-audited on user direction, then resumed): final **86 sent, 0 send-failures**. Excluded 16 E1 bounces + 3 repliers + the existing partner/SAP set (159 total exclusions). 2 boehringer addresses went out before the pause and bounced (unrecoverable).
8. Updated `rome2026-warm-customer-list.xlsx`: added 8 genuine repliers (rows 9–16) + `[check 06-23]` evidence tags on the original 8.

### BOOTH-5 (banner QR) — investigated, blocked
9. Decoded both banner QRs (identical): `https://brisken.digital-demand-gen.com/` → **404**.
10. With the GoDaddy API key (user-provided): confirmed `digital-demand-gen.com` is **NOT** in Brisken's GoDaddy account (holds brisken.com, onepilot.ai, alpharates.*, frag-ulf.de). Registrar 123-Reg, DNS on GoDaddy (different account), hosted on StableServer London, a Laravel "agd content hub" platform. Not Wix. Not fixable from Brisken's side.

### BOOTH-9 — AI-readiness quiz
11. Built `deliverables/brisken-ai-readiness-quiz.html`: self-contained, offline, touch kiosk; 5 treasury-AI questions → score/tier + localStorage benchmark + CTA. Validator clean (kiosk QoL suppressions documented). Plan updated.

### Plan bookkeeping
12. Master Task Plan: marked BTOK-8, BTOK-9, CAM-4 (E1), CAM-5 (E2), BOOTH-2, APP-1, APP-2, APP-3 **Done**; BOOTH-9 → built/pending-iPad; APP-6 → mitigated note.

---

## Key Decisions Made
### Restore docs via /docs/ + redirects, not stickers/parallel structure
- **Choice:** host recovered PDFs at clean `/docs/` paths, redirect every dead old path (docs + pages) to new homes.
- **Rationale:** preserves every external inbound link untouched; one deploy fixes both docs and the APP-6 sponsor-URL (`/sap-consulting` now resolves).

### E2: exclude engaged repliers AND prior-wave bounces before sending
- **Choice:** suppress 3 positive repliers + 16 E1 bounces → 86 clean.
- **Rationale:** don't cold-mail someone who already booked; don't re-send to addresses that hard-bounced. (Caught mid-send on user direction — see friction.)

### Won't send email as Dirk (impersonation boundary)
- **Choice:** prepare cleaned drafts only; a human sends. Email work moved to a separate chat (prompt handed over).
- **Rationale:** an agent dispatching mail under a human's identity is impersonation; hard line regardless of delegate access or request.

### BOOTH-5 not fixable from Brisken's GoDaddy
- **Choice:** stop; surface that the domain is the agency's.
- **Rationale:** `digital-demand-gen.com` isn't in Brisken's account; the redirect must happen at 123-Reg / the other GoDaddy account / the agency.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| website/docs/*.pdf (5) | Created | recovered old-Wix docs (committed 627d972) |
| website/treasury.html | Modified | footer document links (committed) |
| website/vercel.json | Modified | 18 redirects: 5 docs + 13 pages (committed 627d972, 8727d06) |
| deliverables/brisken-ai-readiness-quiz.html | Created | BOOTH-9 offline kiosk quiz |
| Rome-Event/dirk-exclusions.txt | Modified | +3 repliers +16 E1 bounces (gitignored) |
| Rome-Event/rome2026-warm-customer-list.xlsx | Modified | +8 repliers, check tags (gitignored) |
| Rome-Event/TAC26 Rome - Master Task Plan.xlsx | Modified | 8 Done + BOOTH-9/APP-6 (gitignored) |
| Rome-Event/rome2026-send-log-E2.csv | Created | E2 send log, 86 sent (gitignored) |

---

## Current Status
- brisken.com: live with restored docs + all old paths redirecting (verified). Branch `client/brisken/lead-gen-onepilot` (commits 627d972, 8727d06 pushed; not merged to main — owner's call).
- E2: fully sent to the cleaned 86. E1+E2 done; E3/during/post are email-chat work.
- Booth quiz: built + validated; pending AirDrop to the iPad.
- BOOTH-5: blocked on Dirk's access to `digital-demand-gen.com`.

---

## Next Steps
1. **BOOTH-5:** Dirk identifies the "agd" demand-gen agency / a login to `digital-demand-gen.com` (123-Reg, the other GoDaddy account, or the agency) → then repoint `brisken.digital-demand-gen.com` → rome2026.brisken.com. Agent can drive the GoDaddy one with that account's key.
2. **Emails (separate chat):** warm-list replies (Dirk's drafts, human-sent), E3 decision, during/post-event sends.
3. **On-site (Dirk + Matthias):** booth setup EV-2, fobs (BTOK-5/7), demos (DEMO-1–5), photos (APP-4), lead portal (APP-5), app outreach (APP-7).
4. Load `brisken-ai-readiness-quiz.html` on the booth iPad.
5. **USER:** save the GoDaddy creds to the vault (command provided; key = `dKsx…`, secret = `AHfK…`); save the Vercel token (carried from Session 1).

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/context/lead-generation/Rome-Event/TAC26 Rome - Master Task Plan.xlsx` (the live plan)
- `workspace/clients/brisken/context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` (send mechanism + copy)
- `workspace/clients/brisken/website/vercel.json` (the redirect set)

### Open Questions
- Which account (123-Reg / other GoDaddy / agency) can Dirk access to fix the banner QR?
- Send E3 (a 3rd blast to the same 86 in 4 days)? Judgment call, deferred to the email chat.

### Working Notes
- `digital-demand-gen.com`: registrar 123-Reg, NS = GoDaddy domaincontrol.com (NOT Brisken's GoDaddy account), host StableServer London (209.42.20.241), Laravel "agd_content_hub". Apex 404s, both banner QRs identical → that URL.
- E2 send is resumable/idempotent (per-wave log skips already-sent). dirk-exclusions.txt now 159 entries.
- GoDaddy key works: key = the value WITH the underscore; secret = the other. Account has 9 domains.
- Quiz QoL-suppression uses `<!-- deliverable-allow: ... | reason: ... -->` (validate-deliverable.py IDs: dark-mode-toggle, copy-clipboard, keyboard-search).

### Reference Materials
- brisken.com (live), rome2026.brisken.com (event landing, 200), onepilot.brisken.com
- Outlook (matthias.silva@brisken.com, classic) has delegate read access to dirk.neumann@brisken.com.

---

## How to Continue
The banner-QR thread waits on Dirk surfacing domain access. The emails live in the separate chat (its prompt has full state). On-site items are Dirk/Matthias. The agent's open levers: drive the GoDaddy redirect once a working account key appears, or finalize APP-5 lead-portal content if the Execution Plan §12 text is provided.

---

## Strategic Feedback

### What Worked Well This Session
- Autonomous diagnosis chains (Wayback recovery, RDAP/DNS/HTTP fingerprinting, QR decode, NDR report-class fix) resolved "where is this managed / why 404" without bouncing questions back.
- Pausing the E2 send on "check first" and re-auditing was the right call; the resume log made it safe.

### Suggestions
- The pre-send readiness audit should auto-include prior-wave bounces, not just repliers (this session's miss). Worth baking into `send-rome-campaign.ps1` or a checklist so the agent doesn't rely on a user "check first".

### System Health
- `send-rome-campaign.ps1` has no built-in bounce-suppression from prior-wave NDRs; it relies on dirk-exclusions.txt being hand-maintained. A `--exclude-bounces-from EN.log + Outlook NDR scan` step would close the recurring gap.
- Outlook is German-UI ("Posteingang"); all-folder scans must not assume English folder names or default-inbox-only (a scan-scoping miss cost a round here).
- `tools/session_state.py` meter under-counted this long session (band=none, 9 calls) — the session_id keying may have reset; pressure tracking unreliable for long multi-topic sessions.
