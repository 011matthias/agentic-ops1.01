# Checkpoint: Brisken brisken.com Launch

**Date:** 2026-06-21
**Status:** Live on Vercel. brisken.com + www serve TreasuryCentral; onepilot.brisken.com serves the platform page. Book-a-demo live (Neon + ntfy). Two user-side DB steps outstanding.

---

## Summary
Replaced the live Wix corporate site at brisken.com (apex + www) with the TreasuryCentral page on the owner's personal Vercel account, added onepilot.brisken.com for the platform page, shipped an accessible book-a-demo (Neon Postgres + ntfy alert), rebuilt the mobile platform-map as a tiered infographic, and set the real Brisken cube as the favicon.

---

## What Was Done This Session

### DNS cutover (GoDaddy API, Wix -> Vercel)
1. Stored the GoDaddy DNS API key in the gitignored `workspace/clients/brisken/context/.env` (Meji-Porkbun pattern).
2. Non-destructive first: added `onepilot` CNAME -> `cname.vercel-dns.com` + three `_vercel` TXT ownership records (onepilot, apex, www). Wix untouched.
3. Verified all three domains on Vercel via the API (`POST /v9/projects/{id}/domains/{domain}/verify`) after the TXT propagated.
4. Cutover (irreversible, user-greenlit): apex `@` A `185.230.63.107` -> `76.76.21.21`; `www` CNAME `pointing.wixdns.net` -> `cname.vercel-dns.com`. Email (M365 MX), Zoho, `events.brisken.com`, all other records untouched.

### Site routing + book-a-demo
1. Renamed `index.html` -> `treasury.html` and added host-based clean-URL rewrites so apex serves TreasuryCentral and `onepilot.brisken.com` serves the platform page. Fixes the latent "rewrite never fired" bug (Vercel serves static files before rewrites, so a root `index.html` shadowed the host rewrite). Clean-URL destinations (`/treasury`, `/onepilot`), not `.html` (cleanUrls makes `.html` unroutable in a rewrite).
2. Book-a-demo serverless fn (`api/book-demo.js`): rate-limit -> spam-check (honeypot + time-to-fill) -> Neon insert (parameterized) -> notify. Persists first, notifies after.
3. Notifier: ntfy.sh topic (no account/secret needed), PII-minimal payload (company + preferred date only; name/email stay in Postgres). `NOTIFY_WEBHOOK_URL` set in Vercel.

### Mobile + branding
1. Rebuilt the platform-map mobile fallback as a tiered infographic: OnePilot (platform) -> TreasuryCentral (edition) -> 2x2 app grid -> Why now, with connectors. Tap-to-open popup intact. Verified at 390px in light + dark via Playwright; no horizontal overflow.
2. Favicon: cropped the real cube from the actual brisken logo PNG, composed on a white rounded tile, shipped as `/favicon.png` referenced by all pages (replaces the hand-drawn SVG approximation).

---

## Key Decisions Made

### Personal Vercel account, not akkton
- **Choice:** Host on `matthias-neumanns-projects` (project `brisken-onepilot`, `prj_Avie4cXev9Axx4WfKNAJfob3FEap`).
- **Rationale:** Owner directive; the akkton agency account was the wrong home.

### ntfy.sh for lead alerts
- **Choice:** ntfy public topic instead of Teams/Slack webhook or email.
- **Rationale:** Owner said "write your own webhook" (no Teams/Slack setup, no secret-harvesting). ntfy needs no account; PII kept out of the public topic. Swappable later via the one env var (JSON path for Slack/Teams already coded).

### INSERT-only DB role (handed to user)
- **Choice:** Function prefers `LEADS_DATABASE_URL` (a least-privilege `leads_writer` role) over the integration's `DATABASE_URL`.
- **Rationale:** Limits blast radius if the connection string leaks. Role creation is a privileged DB op the safety layer correctly blocks from automation, so it's turnkey SQL for the user.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/website/treasury.html | Renamed from index.html + mobile CSS + favicon link | Apex TreasuryCentral page; mobile map infographic |
| workspace/clients/brisken/website/onepilot.html | Modified | Favicon link; served at onepilot.brisken.com |
| workspace/clients/brisken/website/demo.html | Modified | Favicon link; /demo fallback form |
| workspace/clients/brisken/website/api/book-demo.js | Modified | ntfy notifier (PII-minimal) + rate limit |
| workspace/clients/brisken/website/vercel.json | Modified | Host-based clean-URL rewrites |
| workspace/clients/brisken/website/favicon.png | Created | Real Brisken cube favicon |
| workspace/clients/brisken/context/.env | Created (gitignored) | GoDaddy DNS API key |

---

## Current Status
Live and verified: `brisken.com` + `www.brisken.com` -> TreasuryCentral; `onepilot.brisken.com` -> platform page; `/favicon.png` 200; book-a-demo end-to-end tested (Neon insert id:3/id:4 + ntfy push). Commits `6ec80ab` (routing + webhook + mobile) and `bb92393` (favicon) pushed to `client/brisken/lead-gen-onepilot`. NOT merged to main (branch carries unrelated WIP; site is live via direct `vercel deploy --prod`, independent of main).

---

## Next Steps
1. **User:** run the `alter role leads_writer ...` Neon SQL (grants INSERT + SELECT(id) + sequence usage; also `delete from leads where email like '%brisken-demo.invalid%'` to clear test rows id:3/id:4).
2. **User:** set `LEADS_DATABASE_URL` in Vercel to the `leads_writer` pooled connection string, redeploy to move the form onto the locked-down role.
3. **User:** confirm Neon project region is `aws eu-central-1` (Frankfurt) for lead-PII residency.
4. **Security:** rotate the Vercel token (`vcp_...`) after launch and revoke the unused `vck_...` API key, both pasted in chat.
5. Decide whether/when to PR `client/brisken/lead-gen-onepilot` into main (isolated website commits are clean to cherry-pick).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/website/api/book-demo.js (function + notify logic)
- workspace/clients/brisken/website/vercel.json (host rewrites)
- workspace/clients/brisken/context/.env (GoDaddy key; gitignored)

### Open Questions
- Move lead alerts off ntfy public topic to a private channel (email/Slack) eventually?
- When does the feature branch merge to main?

### Working Notes
- **Apex cutover cert behavior (important):** a Vercel apex via A-record CANNOT pre-issue its TLS cert; HTTP-01 needs the domain already pointing at Vercel. Only CNAME subdomains (onepilot) pre-issue. The flip itself triggers issuance, with a brief HTTPS window. Do not promise "confirm cert before flip" for an apex.
- **Authoritative apex IP = 76.76.21.21** for this project (from `GET /v6/domains/brisken.com/config` -> `recommendedIPv4`). A stale captured `216.198.79.1` cost a wasted readiness watcher; always read the config at flip time.
- **www cache:** old `www` TTL was 3600s, so stale Wix views persist up to ~60 min after the flip. Wix sets NO service worker (it stubs `serviceWorker.register`), and Vercel HTML is `max-age=0, must-revalidate`, so visitors self-heal within the old TTL with zero action.
- **CSS gotcha:** when overriding an absolutely-positioned element to `position: relative` on mobile, reset `left/top` to auto, else the desktop `left: var(--nx)` (=50%) shifts it. Also override desktop `max-width` for full-width grid spanners.
- Vercel CLI auth via inline `VERCEL_TOKEN=...`; deploys with `vercel deploy --prod --cwd workspace/clients/brisken/website --scope matthias-neumanns-projects`.

### Reference Materials
- Vercel project: brisken-onepilot (prj_Avie4cXev9Axx4WfKNAJfob3FEap), scope matthias-neumanns-projects
- ntfy topic: https://ntfy.sh/brisken-demo-160f5f52c2d0e27a295a166e
- GoDaddy DNS API base: https://api.godaddy.com/v1/domains/brisken.com/records

---

## How to Continue
The site is live. The remaining work is user-side DB hardening (steps 1-3 above) and the security rotation (step 4). To change site content, edit under `workspace/clients/brisken/website/` and `vercel deploy --prod` with the personal scope; verify the deployed origin, not localhost.

---

## Strategic Feedback

### What Worked Well This Session
- Splitting the DNS change into non-destructive-first (onepilot + TXT) then the gated apex flip kept Wix up until the irreversible step, and pre-verifying domains made the flip near-instant.
- Visual verification via Playwright at a real mobile viewport caught two layout bugs (max-width, left:50%) before they reached the user.

### Suggestions
- For domain cutovers, capturing the registrar key in `context/.env` once (done) lets future DNS edits run end-to-end without re-asking.

### System Health
- Autonomy score: 3 human interventions this session (cutover-delay redirect, B1 commit-deferral hook, repeated www-cache explanations). Not elevated.
- No `platform` ops section for brisken in infrastructure.yaml; the new Vercel host is outside the Make/n8n ops-audit model, so the lightweight ops line does not apply here.
- Candidate: a `feedback_vercel_apex_cutover` memory for the apex-cert-cannot-pre-issue lesson (currently only in this checkpoint's working notes).
