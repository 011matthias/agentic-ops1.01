# Checkpoint: Meji Piece 3 mejixmas Domain Setup

**Date:** 2026-06-01
**Status:** End-to-end shipped. 3-4 week warmup clock running on both sending mailboxes.

---

## Summary

End-to-end shipped the Piece 3 cold-sending domain `mejixmas.com` for Meji Media. DNS pushed via Porkbun API across three B5-gated phases (verification TXT, parking-to-Google-MX swap, SPF+DKIM+DMARC); 2 sending mailboxes created in Workspace (count trimmed from 3 to 2 mid-build); Instantly OAuth verified at backend; DKIM signing empirically confirmed via Port25 verifier (both mailboxes pass on SPF + iprev + DKIM); URL-forward redirect `mejixmas.com -> mejimedia.com` shipped; warmup toggled ON for both. Workspace's DKIM backend flipped active within ~60 min of the Confirm click rather than the worst-case 48 hr.

---

## What Was Done This Session

### DNS (Porkbun, agent-driven via API)
1. Phase 2: pushed `google-site-verification=2LDJ-khKBi-qjsa9sloRrM3-9xPcNCJgiZBrisINWNs` TXT at root, TTL 600 (record id 551905064)
2. Phase 4: deleted parking ALIAS root + wildcard CNAME + 2 Porkbun `fwd*.porkbun.com` MX records; added Google MX `smtp.google.com` priority 1 TTL 600 (record id 551908985)
3. Phase 7: deleted Porkbun SPF; added Google SPF (`v=spf1 include:_spf.google.com ~all`, id 551913879); added 2048-bit DKIM TXT at `google._domainkey` (id 551913883, 411 chars, parsed clean as RSA public key); added DMARC at `_dmarc` (`p=none; rua=mailto:postmaster@mejimedia.com; pct=100; adkim=r; aspf=r`, id 551913888)
4. Optional 301 redirect: URL-forward record (id 29094154) `mejixmas.com` + `*.mejixmas.com` -> `https://mejimedia.com`, permanent, includePath=yes; SSL provisioning on bare-domain expected ~15 min post-add

### Workspace (Matthias-driven in admin.google.com)
1. Phase 1: added `mejixmas.com` as Secondary Domain on the mejimedia.com Workspace
2. Phase 3: domain verified via the Porkbun TXT push from Phase 2
3. Phase 5: created 2 Workspace users `gurmej@mejixmas.com` and `gurmej.p@mejixmas.com` (trimmed from 3 mid-build per challenge — see Key Decisions)
4. Phase 6: generated 2048-bit DKIM key for `mejixmas.com`
5. Phase 8: clicked Confirm; DKIM authentication started; backend flipped active within ~60 min (verified empirically via Port25 verifier auto-reply)

### Instantly (Matthias-driven in UI)
1. Phase 9: OAuth flow for both mailboxes in incognito tabs; both landed green first attempt on the back of the org-wide Instantly trust set 2026-05-30 (no per-domain trust step needed — that "You only need to do this once per domain" instruction is generic copy from before Instantly handled org-wide trust)
2. Phase 10: warmup toggled ON per mailbox in Warmup tab; backend confirms `warmup_status=1` on both

### File updates
1. `workspace/clients/meji-media/context/pilot-routing.md` — Piece 3 row updated with the 2 mailbox names, `last_verified: 2026-06-01`, Hard Rule #3 made specific to mejixmas.com
2. `workspace/clients/meji-media/context/piece3-mejixmas-setup-plan.md` — target_state updated for 2-mailbox count, Phase 10 description corrected (warmup not auto, requires manual toggle), Phase 8 empirical-verification note added
3. Draft created then deleted: `drafts/reply-to-gurmej-2026-06-01-mejixmas-mailbox-count.md` (cost-trim note for Matthias to send to Gurmej about the 3-to-2 trim; Matthias opted not to send)

### Verification (all DoH-based, not Windows nslookup)
1. Phase 2: TXT propagation confirmed via Cloudflare + Google DoH
2. Phase 4: MX propagation confirmed via Cloudflare + Google DoH (Windows nslookup returned SOA-only false-negative; DoH was the canonical source)
3. Phase 7: SPF, DKIM (length, ends-with check), DMARC all confirmed via Cloudflare + Google DoH on first attempt
4. Phase 7 again post-URL-forward: re-verified all auth records still resolve under the re-added wildcard CNAME (RFC override: explicit records win over wildcard CNAME)
5. Phase 9: Instantly `/api/v2/accounts` GET filtered to `mejixmas` confirms `status=1, provider_code=2` on both
6. Phase 8: Port25 verifier auto-reply landed in each mailbox showing SPF=pass + iprev=pass + DKIM=pass with `d=mejixmas.com s=google` (definitive empirical proof Workspace is signing)
7. Phase 10: Instantly accounts GET confirms `warmup_status=1, timestamp_updated` advanced ~12 min after toggle

---

## Key Decisions Made

### Mailbox count trimmed 3 -> 2
- **Choice:** Create only `gurmej@mejixmas.com` and `gurmej.p@mejixmas.com`. Skip `gurmej.pawar@mejixmas.com`.
- **Rationale:** Initial 3-mailbox plan was pattern-matched from mejimedia.co (Piece 1) and mejievent.com (Piece 2), not driven by Piece 3 volume math. Piece 3 audience is the smallest of the three pieces (3 venue cities only, not UK-wide). Apollo-filtered cohort is 500-2000 contacts. At Instantly's 30-50/day post-warmup pace, 2 mailboxes clear it in ~2 months with 1-mailbox deliverability hedge. Saves 1 ongoing Workspace seat. Adding a 3rd later is ~5 min if volume demands.
- **Surfaced by:** Matthias asking "why three mailboxes again? is that necessary?"

### Cost-trim note to Gurmej dropped
- **Choice:** Don't send a proactive note to Gurmej about the 3-to-2 mailbox seat trim.
- **Rationale:** Matthias's call. Gurmej's 2026-05-31 "ok with the domains" was for 3 seats; we're delivering 2; the proactive transparency note would surface the trim. Matthias chose not to send.
- **Draft trace:** `drafts/reply-to-gurmej-2026-06-01-mejixmas-mailbox-count.md` was written then deleted per direction.

### MX modern single-record over legacy 5-record
- **Choice:** Push `mejixmas.com MX 3600 1 smtp.google.com` (single record) instead of legacy ASPMX.L.GOOGLE.COM + ALT1..4.
- **Rationale:** What Workspace's Activate Gmail panel showed Matthias was the modern single-record form. We followed what Workspace asked for rather than guessing. Backed by Google's 2023 MX consolidation for new tenants.

### Phase 8 empirically verified via Port25 instead of waiting 48 hr UI window
- **Choice:** Trigger a test send from each mailbox to `check-auth@verifier.port25.com` and read the auto-reply headers in Gmail.
- **Rationale:** Workspace's UI shows a "may take up to 48 hours" message after DKIM activation. The DNS layer is verified clean via DoH; the only unknown is whether Workspace's backend has flipped to active. Test send + Port25 reply gives definitive header-level proof in ~30 seconds. Both mailboxes returned `DKIM: pass`. Backend flipped within ~60 min, not 48 hr.

### Instantly OAuth via skip-per-domain-trust path
- **Choice:** Click Login directly on Instantly's "Connect Your Google Account" screen instead of re-doing the per-domain Configure-new-app trust step.
- **Rationale:** The Client-ID Instantly showed (`536726988839-pt93oro4685dtb1emb0pp2vjgjol5mls...`) matches the one we org-wide trusted on 2026-05-30. The org-wide trust covers all 8 secondary domains on the Workspace, including the newly-added mejixmas.com. Instantly's per-domain instructions are generic UI copy from before they handled org-wide trust. Result: both mailboxes OAuth'd first attempt.

### URL forward to mejimedia.com over A-record-to-static-page
- **Choice:** Porkbun URL forwarding feature, 301 permanent, root + wildcard.
- **Rationale:** Zero DNS work, brand-adjacent trust signal, immediate. Cold prospects who check the sender domain land on the main Meji site instead of "site can't be reached."

### DMARC at p=none for first 30 days
- **Choice:** Monitor mode with aggregate reports to `postmaster@mejimedia.com`.
- **Rationale:** Standard for a fresh cold-sending domain. Lenient during warmup to avoid blocking warmup mail. Tighten to `p=quarantine` after 30 days of clean traffic.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/pilot-routing.md` | Modified | Lock in mejixmas.com Piece 3 mailboxes; bump last_verified to 2026-06-01; specialize Hard Rule #3 |
| `workspace/clients/meji-media/context/piece3-mejixmas-setup-plan.md` | Modified | Update target_state for 2-mailbox count; correct Phase 10 description (warmup not auto); add Phase 8 empirical-verification note |
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-2026-06-01-mejixmas-mailbox-count.md` | Created then deleted | Cost-trim note drafted, deleted per Matthias direction |
| Porkbun DNS zone mejixmas.com | Live changes (12 record adds/deletes net) | Phases 2/4/7 + URL forward |
| Google Workspace (mejimedia.com tenant) | Live changes | mejixmas.com added as Secondary Domain, Gmail activated, DKIM generated + activated, 2 new users created |
| Instantly accounts | Live changes | 2 mailboxes OAuth'd, warmup toggled ON |

---

## Current Status

`mejixmas.com` cold-sending infrastructure is end-to-end shipped:

- DNS layer: SPF + DKIM (signing verified) + DMARC (p=none) + MX (Google) all live and DoH-verified
- 2 mailboxes (`gurmej@mejixmas.com`, `gurmej.p@mejixmas.com`) connected to Instantly via Google OAuth (`status=1, provider_code=2`)
- Warmup active on both (`warmup_status=1`); 3-4 week ramp clock now running
- 301 redirect live (URL-forward id 29094154); bare-domain SSL provisioning in next ~15 min from end-of-session
- DKIM signing empirically verified via Port25 (both mailboxes `pass`)

No client-facing comms required — Matthias chose not to send the cost-trim note. Gurmej's 2026-05-31 greenlight (`Yes the Managing director thing is fine` + `And ok with the domains`) is the most recent inbound; comms-log staleness = 1 day.

---

## Next Steps

1. **Wait 3-4 weeks for warmup to ramp** before any live Piece 3 cold send. No agent action required during the ramp; Instantly handles it.
2. **During the warmup window, draft the Piece 3 Christmas cold sequence copy** for Gurmej review. Per pilot-routing.md, audience = 3 venue cities only (Birmingham/Leicester/Wolverhampton); ICP per 2026-05-22 + 2026-05-31 locks (PA/EA/Office Mgr/HR on 51-500 emp tier; MD/CEO on 11-50 emp tier).
3. **Source the Piece 3 audience via Apollo** during warmup (saved search + sample preview to Gurmej before pulling full list).
4. **At day-30 post-warmup, tighten DMARC to `p=quarantine`** if aggregate reports show no auth failures.
5. **Bare-domain HTTPS sanity check** in next session — confirm Porkbun's Let's Encrypt cert provisioned for `https://mejixmas.com` (cosmetic, not blocking).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/pilot-routing.md` — canonical Piece routing; mejixmas.com now locked in
- `workspace/clients/meji-media/context/piece3-mejixmas-setup-plan.md` — full setup runbook, now fully executed
- `workspace/clients/meji-media/context/comms-log.md` — most recent comms (2026-05-31 16:24 BST Gurmej greenlight is the open state)
- `workspace/clients/meji-media/context/.env` — credentials inventory (Apollo + Porkbun + Workspace temp Super Admin + Instantly API key)

### Open Questions
None for the Piece 3 infrastructure. All blocking asks resolved.

### Working Notes

**Porkbun's `uixie.porkbun.com` is dual-purpose.** The root ALIAS + wildcard CNAME pointing at `uixie.porkbun.com` both (a) serve the Porkbun parking page when no URL forward is configured AND (b) back the URL-forwarding redirector when one IS configured. Deleting them in Phase 4 thinking they were just "parking" was correct for email purposes (MX takes precedence) but caused them to be silently re-added by Porkbun when the URL-forward record was created. The runbook's Phase 4 description called these records "parking" without flagging the URL-forward dependency. Updated in piece3-mejixmas-setup-plan.md.

**Instantly's warmup is NOT auto-on for freshly-connected mailboxes.** Earlier in the session I stated "Instantly auto-starts warmup at ~30/day" which was wrong. The actual default is `warmup_status=0, daily_limit=null` until manually toggled in the Warmup tab. Corrected the runbook Phase 10 description.

**Windows `nslookup` returned SOA-only false-negative on MX query after Phase 4.** When Porkbun's authoritative NS was queried directly, nslookup still returned only the SOA. DoH (Cloudflare + Google) returned the correct MX. Use DoH for all DNS verification in this codebase; Windows nslookup is unreliable on Porkbun zones for some query types.

**Both Phase 4 and Phase 7 had Unicode encoding crashes on first attempt.** The arrow character `→` (->) printed via Python on Windows cp1252 console crashed with `UnicodeEncodeError`. Fix: `sys.stdout.reconfigure(encoding='utf-8')` at top of every script that does DNS-verification print output, OR use ASCII-safe `->` literal instead of `→`. Both scripts in this session adopted both fixes.

**Port25's verifier (`check-auth@verifier.port25.com`) is the canonical free DKIM-sign verification path.** Sends an auto-reply within ~30s with a Summary of Results block showing SPF/iprev/DKIM/(DMARC). The reply lands in the sending mailbox's inbox. Worth captured as a fixture pattern for future cold-domain setups.

### Reference Materials

- Porkbun API docs: https://porkbun.com/api/json/v3/documentation
- Google Workspace DKIM key generation: admin.google.com -> Apps -> Google Workspace -> Gmail -> Authenticate email
- Port25 verifier: https://www.port25.com/authentication-checker/
- Cloudflare DoH JSON endpoint: https://cloudflare-dns.com/dns-query (accept: application/dns-json)
- Google DoH JSON endpoint: https://dns.google/resolve
- mejixmas.com expires 2027-05-27 (per .env note)
- Porkbun record IDs (in case rollback needed): MX 551908985, SPF 551913879, DKIM 551913883, DMARC 551913888, URL-forward 29094154

---

## How to Continue

If picking up Piece 3 work in a future session: read `pilot-routing.md` first, then `piece3-mejixmas-setup-plan.md`. The infrastructure is shipped; next priority is sequence copy + audience sourcing during the warmup window. Don't re-execute any of the DNS pushes (they're complete); re-verify state via `/api/v2/accounts` GET on the Instantly side and Cloudflare DoH on the DNS side before assuming anything.

If `warmup_status` regressed to 0 on either mailbox at re-check, that's a re-toggle in Instantly UI, no DNS work needed.

---

## Strategic Feedback

### What Worked Well This Session

- **The B4 paste-don't-transcribe call on the DKIM key was load-bearing.** Refusing to transcribe ~408 chars of base64 from a screenshot and demanding a clipboard paste prevented an entire class of "DKIM never validates because one character flipped" debug spiral. The structural test: parse the published TXT as a DER-encoded RSA public key via `cryptography` after it landed. Both checks passed on first push. Pattern worth reusing for any cryptographic-blob handoff.
- **DoH-first DNS verification beat Windows nslookup twice this session** (Phase 4 MX false-negative, Phase 7 propagation check). Worth making the project-default verification path for any DNS push.
- **Port25 verifier reply landed in each mailbox in ~30 seconds and gave a definitive Phase 8 verdict** instead of waiting the worst-case 48 hr UI window. Workspace's backend was empirically active within ~60 min of the Confirm click.
- **Matthias's "why three mailboxes" challenge** mid-build was the right tactical override. Pattern-matching 3 from the other domains was a soft assumption; the city-bound Piece 3 audience size made 2 the right cap with room to scale. Saved an ongoing seat without a comms cycle.

### Suggestions

- **A reusable DNS-verification helper script** at `tools/dns-verify.py` would compress the post-push DoH-check pattern (Cloudflare + Google JSON endpoints, all record types, ASCII-safe output, parse + length check on DKIM specifically) from "write a fresh script every time" to one CLI call. Worth ~30 min to build before the next cold-domain setup.
- **A `Port25-verify` fixture** documented in `context/test-fixtures.md` (or its meji-equivalent) for future cold-domain setups, with the exact email format and the parse pattern for the Summary of Results block.

### System Health

- The B1 stop-hook fired twice in this session catching deferral patterns ("Want me to draft..." and "Two questions: (a) want me to set this up..."). Hook is working as intended — both catches were corrections-at-stop-time, not pre-emission. The hook's "post-hoc" architecture is good enough but the friction register has a `missed-memory-recall` entry from 2026-05-26 calling out the same "move enforcement from after to before" architectural gap. Two B1 catches in one session is on the elevated end; worth surfacing in the next `/system-dev` round whether a pre-emission deferral linter would pay for itself.
- The `validate-pilot-routing.py` hook stayed quiet this session (no draft cross-wires). Good signal that the canonical-file-plus-hook layer is doing its job after the 2026-05-30 cross-wire incident.

### Autonomy Score
4 human interventions this session:
1. Stop-hook B1 catch on the cost-trim closer
2. Stop-hook B1 catch on the 301-redirect framing
3. Matthias's "why three mailboxes" course-correction (not a misalignment so much as a load-bearing veto on an over-default; counted as intervention because I would have shipped 3 without it)
4. Matthias's "leave the cost trim out" direction

Not elevated — multi-phase build sessions with infrastructure decisions naturally invite more user input than pure tactical work.
