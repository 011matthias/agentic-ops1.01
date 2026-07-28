# Cold-email infrastructure: ready-to-purchase checklist (u1)

Purpose: a later "go" starts the 3-4 week warm-up clock the same day.
Everything below is decided and priced so purchase day is execution, not
research. PURCHASE GATE (owner decision 2026-07-22): nothing here is
bought without its own explicit owner approval, line by line.

Prices were fetched from the vendor's live page (2026-07-22, verification
+ Apollo re-checked 2026-07-28) in the currency the vendor displayed. No
FX conversion applied.

**2026-07-28 update (the finding that gates everything):** the local vault
holds NO UnpauseAI-owned rails. Its `porkbun` (`gurmejsp`), `apollo`
(`gurmej@mejimedia.com`), and `workspace-super-admin` (`matthias@mejimedia.com`,
"temp Super Admin") entries all resolve to **Meji client accounts**, and the
only Instantly entry is the client's (`Instantly Gurmej`). UnpauseAI's
acquisition engine must not be built on a client's Porkbun / Workspace /
Instantly / Apollo: it co-mingles billing on the client's cards, puts
UnpauseAI's cold-sending reputation on the client's infrastructure (a real
deliverability risk to Meji), and defeats the point of an independence
program. So every line below is bought on an **UnpauseAI-owned** account the
owner provisions (§12), never a client account. Owner chose this path
2026-07-28.

## 1. Registrar: Porkbun (recommendation)

| Item | Value | Source |
|---|---|---|
| .com registration | $11.08/yr (fees included) | porkbun.com/products/domains, 2026-07-22 |
| .com renewal | $11.08/yr (as shown on the same page) | same |
| Alternative | Cloudflare Registrar, "at-cost" claim, no figure shown on page | cloudflare.com/products/registrar |

Why Porkbun: existing DNS tooling and API familiarity, and the API now
covers the whole flow. Porkbun's API supports programmatic registration
(`POST /domain/create/{domain}`, `agreeToTerms=yes`, `cost` in US cents
matching the availability quote, `Idempotency-Key` header for safe retry) on
a **verified account with sufficient prepaid balance**. So once an
UnpauseAI-owned Porkbun account exists, is funded (>= ~$34), and has API
access enabled, I register all three by API and run the DNS runbook with no
UI clicks. Cloudflare's at-cost pricing is marginally cheaper but adds a
nameserver-migration constraint for no material saving at 3 domains.

## 2. Domain candidates (availability RDAP-checked 2026-07-28)

unpauseai.com NEVER cold-sends; the root domain stays clean. Confirmed
2026-07-28: unpauseai.com's own mail runs on Zoho (`mx.zoho.eu`,
`v=spf1 include:zohomail.eu`), which is a second reason to keep the cold
senders off Zoho (see §3).

| Priority | Domain | Status (RDAP 2026-07-28) |
|---|---|---|
| Buy 1 | tryunpauseai.com | Available |
| Buy 2 | unpause-ai.com | Available |
| Buy 3 | unpauseautomation.com | Available |
| Spare | unpauseops.com | Available |
| Spare | unpauseai.net | Available |
| Off-list | getunpauseai.com | TAKEN (registered 2026-01-31 by a third party) |

Availability changes without notice; re-check on purchase day. Each sending
domain gets a 301 redirect to unpauseai.com (Porkbun URL forwarding) so a
recipient who types the domain lands somewhere real.

## 3. Mailbox plan: Google Workspace, separate tenant (DECIDED 2026-07-28)

| Item | Value | Source |
|---|---|---|
| Business Starter | EUR 6.80/user/mo (flexible monthly; EUR 3.40 first 3 months promo) | workspace.google.com/pricing, 2026-07-22 |
| Annual-commit discount | "Save 16% with 1 year commitment" (page wording) | same |
| Alternative: M365 Business Basic | $7.00/user/mo, annual subscription | microsoft.com compare page, 2026-07-22 |

Decision closed: **Google Workspace, in a NEW tenant dedicated to the cold
senders, on monthly flex.** Not Zoho. Two reasons, both load-bearing:

- Zoho Mail's usage policy forbids bulk/cold outreach outright (shared IPs;
  auto-suspension on cold-send patterns). Its own usage-policy page and
  multiple deliverability writeups say the same.
- unpauseai.com's clean mail is already on Zoho. Even if Zoho allowed it, a
  cold-send suspension would land on the same provider as UnpauseAI's real
  mail. Keeping the cold senders on a different provider from the clean root
  is the same blast-radius logic as "unpauseai.com never cold-sends".

Plan: **2 mailboxes per domain**. Standard = 3 domains x 2 = 6 mailboxes =
EUR 40.80/mo (EUR 20.40/mo during the 3-month promo). Minimal = 2 domains x
2 = 4 mailboxes = EUR 27.20/mo. Sender display name: **Matthias Neumann**
(task-confirmed 2026-07-28). Take monthly flex, not the annual commit, until
the channel proves itself.

## 4. ESP: Instantly (recommendation: Growth, monthly)

| Tier | Price | Caps | Source |
|---|---|---|---|
| Growth | $47/mo | 1,000 uploaded contacts, 5,000 emails/mo, unlimited email accounts, warm-up included | instantly.ai/pricing, 2026-07-22 |
| Hypergrowth | $97/mo | 25,000 contacts, 100,000 emails/mo | same |
| Light Speed | $358/mo | 100,000 contacts, 500,000 emails/mo | same |

No UnpauseAI-owned Instantly account exists (the vault's only Instantly is
the client's). A new signup is required (§12). Annual billing = 10% off;
start on Growth monthly. The 1,000-contact cap binds only once list building
outgrows the first campaigns; upgrade to Hypergrowth is a same-day switch.

## 5. List building: Apollo Basic (DECIDED 2026-07-28 — free tier is dead)

| Tier | Price | Credits | Source |
|---|---|---|---|
| Free | $0 | ~100 email + ~10 export credits/mo; **25 records per bulk export** | Apollo help + pricing writeups, 2026-07-28 |
| Basic | $49/seat/mo billed annually | 30,000 credits/yr | apollo.io/pricing, 2026-07-22 |
| Professional | $79/seat/mo billed annually | 48,000 credits/yr | same |
| Organization | $119/seat/mo billed annually (min 3 seats) | 72,000 credits/yr | same |

Closed: Apollo's late-2025 changes gutted the free tier to ~100 email
credits/mo and a **25-record-per-export cap** [Meet Suplex, Scrupp]. The
export capability list-building depends on is gated, so "start Free" fails.
The list line needs a **paid seat or a different source.**

Commitment flag: Basic is billed **annually** ($49/seat/mo = ~$588 up front)
for a pool the ICP models as small (cold ~50; segment bands 150/95/30). Two
lighter options to weigh before committing a year:
- Check Apollo's monthly-billed Basic rate (not shown on the annual page,
  TBD); a one-time list build may need only one month.
- If u3 (LinkedIn/Sales Nav) and future channels share the Apollo seat as
  the common enrichment engine, the annual seat amortizes and is fine.

Must be an **UnpauseAI-owned** Apollo account, not the client's. The meji
Apollo filter-spec pattern is reusable once the credential exists; the exact
u1 filter is in `u1-list-and-sequences.md`.

## 6. Verification: MillionVerifier (DECIDED 2026-07-28)

| Verifier | Pay-as-you-go | 10k cost | Source |
|---|---|---|---|
| MillionVerifier | ~$3.70/1,000 at the 10k tier; ~$0.00055/email at scale | ~$37 | Puzzle Inbox, Prospeo, 2026-07-28 |
| NeverBounce | ~$0.008/email (<10k), ~$0.004-0.005 at scale | ~$80 | Cleanlist, Puzzle Inbox, 2026-07-28 |

Closed: **MillionVerifier**, ~half NeverBounce's cost at low volume and far
cheaper at scale, same accuracy class. Buy a 10k credit pack when the list
volume is known. The MX pre-filter (drop Mimecast-gatewayed domains before
verification; `reference_cold_email_gateway_bounces`) runs first and shrinks
the paid volume regardless of vendor.

## 7. DNS-auth runbook (per sending domain, Google Workspace)

Order matters: the tenant + domain must exist before DKIM can be generated,
and mailboxes should exist before turning DKIM authentication on. All records
are published on Porkbun; the tenant-specific values (DKIM key, Instantly
CNAME target) come from the respective admin screens, so confirm against
those, not against this doc.

1. **Add domain to the GWS tenant** (secondary domain), verify ownership via
   the TXT `google-site-verification=...` record Google gives you (publish on
   Porkbun, root).
2. **MX** (Google's current single-record setup): `1 smtp.google.com`.
   Legacy 5-record set (`ASPMX.L.GOOGLE.COM` @1, `ALT1/ALT2` @5,
   `ALT3/ALT4` @10) still works; use whichever the admin-console setup screen
   shows for the tenant. One provider's MX only, never mixed.
3. **SPF** (TXT, root): `v=spf1 include:_spf.google.com ~all`. Exactly one
   SPF record per domain, never two.
4. **Create the 2 mailboxes** for this domain (users in the GWS admin
   console), sender display name **Matthias Neumann**.
5. **DKIM**: Admin console -> Apps -> Google Workspace -> Gmail ->
   Authenticate email -> generate a **2048-bit** key -> publish the TXT it
   gives you at host `google._domainkey` (Porkbun) -> then "Start
   authentication" (turn it ON) in the console.
6. **DMARC** (TXT at `_dmarc`): `v=DMARC1; p=none; rua=mailto:dmarc@{domain}`
   during warm-up; tighten to `p=quarantine` after the first clean month.
7. **Instantly custom tracking domain**: CNAME per Instantly's setup screen
   (host + target it specifies), one per domain, so click-tracking links are
   on-brand and not Instantly's shared host.
8. **Root 301 redirect**: Porkbun URL forwarding -> https://unpauseai.com.
9. **Verify everything** (dig/nslookup + Google Admin Toolbox "Check MX")
   before connecting anything to Instantly. Expected: MX resolves to Google,
   one SPF, DKIM TXT present + auth ON, DMARC present, tracking CNAME
   resolves, 301 returns unpauseai.com.

## 8. Day-1-after-provisioning sequence (same-day warm-up start)

Once the owner has provisioned the accounts (§12), this is my execution path:

1. Re-check domain availability (RDAP); register the 3 domains (Porkbun API).
2. Add the 3 domains to the new GWS tenant; create the 6 mailboxes.
3. Run the DNS runbook (§7) for all 3 domains; verify.
4. Connect all 6 mailboxes to Instantly; enable warm-up the same day. Warm-up
   ramp: low single digits per day rising toward normal over 3-4 weeks
   (`project_brisken_outreach_domains`: no real sends before the clock
   completes).
5. Calendar markers at day 21 and day 28: earliest first-send window.
6. During warm-up (parallel, no sends): build the Apollo list per the filter
   spec, run the MX pre-filter, verify the remainder (MillionVerifier), load
   sequences. Instantly delay semantics: the gap belongs on the EARLIER step
   (`reference_instantly_sequence_delay_semantics`).
7. Any first real send is a separate B5-gated decision (scope-of-effects +
   readiness audit per `rule_instantly_invasive`); warm-up completion does
   not authorize sending.

## 9. Cost roll-up (as-displayed currencies, standard config)

| Line | Cost |
|---|---|
| Domains (3 x .com, Porkbun) | $33.24/yr one-line |
| Mailboxes (6 x GWS Starter, monthly flex) | EUR 40.80/mo (EUR 20.40 first 3 months) |
| ESP (Instantly Growth, monthly) | $47/mo |
| List (Apollo Basic, annual) | $49/seat/mo (~$588/yr up front) |
| Verification (MillionVerifier) | ~$37/10k, as needed |

**Model-feedback flag:** the leadgen-portfolio scorer assumes EUR 40/mo fixed
cold-email infra. The real recurring stack is ~EUR 40.80 + $47 (Instantly) +
$49 (Apollo) monthly before verification, i.e. roughly 3x the modeled fixed
cost (minimal config drops mailboxes to EUR 27.20; Apollo/Instantly are fixed
regardless of mailbox count). When the channel goes live, this belongs in the
same re-pin conversation as the pool validations (u4 pattern).

## 10. Purchase-approval checklist (each line needs its own owner yes)

- [x] **APPROVED** Domains: tryunpauseai.com, unpause-ai.com, unpauseautomation.com ($33.24/yr) — owner 2026-07-22
- [x] **APPROVED + provider CLOSED** Mailboxes: 6 x GWS Starter, new separate tenant (not Zoho) — owner 2026-07-22, provider decided 2026-07-28
- [x] **APPROVED** Instantly Growth ($47/mo) — owner 2026-07-22
- [ ] **Apollo Basic** ($49/mo annual, or one monthly seat) — approve the paid seat; free tier ruled out 2026-07-28
- [ ] **MillionVerifier** 10k credit pack (~$37) — approve at list-volume time

**Execution status: nothing purchased.** The blocker is NOT vault-read access
(reads work); it is that UnpauseAI owns none of the accounts. Each line needs
an UnpauseAI-owned account the owner provisions (§12) with a payment method
and, for Google/Instantly, signup + phone/2FA the agent cannot perform.

## 11. Decisions closed 2026-07-28

- Mailbox provider: **Google Workspace, new separate tenant** (Zoho ruled out
  on AUP + blast-radius; see §3).
- Verification: **MillionVerifier** (§6).
- Apollo: **free tier ruled out** (25-record export cap); needs a paid seat
  (§5).
- Sender display name: **Matthias Neumann** (§3).
- Account ownership: everything on **UnpauseAI-owned** accounts (§12).

## 12. Owner provisioning steps (the card / signup / 2FA only you can do)

Do these once; I execute everything downstream. Store each new credential in
the vault under an explicit UnpauseAI-scoped name (suffix `-unpauseai`) so it
is never confused with a client account again.

1. **Porkbun (UnpauseAI):** create or designate a Porkbun account that is
   yours, not the client's; add a card / fund balance >= ~$34; enable API
   access and generate the API key + secret. Save as vault `porkbun-unpauseai`.
   -> I register the 3 domains by API and run DNS.
2. **Google Workspace (new tenant):** start a new Workspace signup with one
   sending domain as the primary (e.g. tryunpauseai.com); add a card;
   complete phone verification; set the super-admin. Save as vault
   `gws-unpauseai`. -> I add the other 2 domains, create the 6 mailboxes,
   generate DKIM.
3. **Instantly (new subscription):** sign up at instantly.ai; subscribe
   Growth ($47/mo); generate an API key. Save as vault `instantly-unpauseai`.
   -> I connect all 6 mailboxes and enable warm-up.
4. **Apollo (Basic seat):** sign up; subscribe Basic (check the monthly-billed
   rate first if a one-time list is all we need); generate an API key. Save as
   vault `apollo-unpauseai`. -> I build the list per the filter spec.
5. **MillionVerifier:** create an account; buy a 10k credit pack when list
   volume is known; generate an API key. Save as vault
   `millionverifier-unpauseai`. -> I verify the post-MX-filter remainder.

Fastest path to start the warm-up clock: items 1-3 unblock domains +
mailboxes + Instantly (the clock starts when mailboxes connect with warm-up
on). Items 4-5 are warm-up-parallel and can follow within the 3-4 week window.
