# Cold-email infrastructure: ready-to-purchase checklist (u1)

Purpose: a later "go" starts the 3-4 week warm-up clock the same day.
Everything below is decided and priced so purchase day is execution, not
research. PURCHASE GATE (owner decision 2026-07-22): nothing here is
bought without its own explicit owner approval, line by line.

Every price was fetched from the vendor's live page on 2026-07-22 and is
quoted in the currency the vendor displayed. No FX conversion applied.
Two lines could not be verified (bot-walled pages) and read TBD.

## 1. Registrar: Porkbun (recommendation)

| Item | Value | Source |
|---|---|---|
| .com registration | $11.08/yr (fees included) | porkbun.com/products/domains, 2026-07-22 |
| .com renewal | $11.08/yr (as shown on the same page) | same |
| Alternative | Cloudflare Registrar, "at-cost" claim, no figure shown on page | cloudflare.com/products/registrar |

Why Porkbun: the operational precedent is already here (Brisken's
53-domain farm runs on it; existing DNS tooling and API familiarity),
and the API supports the DNS runbook below without a new vendor
relationship. Cloudflare's at-cost pricing is likely marginally cheaper
but adds a nameserver migration constraint for no material saving at
3 domains.

## 2. Domain candidates (availability RDAP-checked 2026-07-22)

unpauseai.com NEVER cold-sends; the root domain stays clean.

| Priority | Domain | Status |
|---|---|---|
| Buy 1 | tryunpauseai.com | Available |
| Buy 2 | unpause-ai.com | Available |
| Buy 3 | unpauseautomation.com | Available |
| Spare | unpauseops.com | Available |
| Spare | unpauseai.net | Available |
| Off-list | getunpauseai.com | TAKEN (registered 2026-01-31 by a third party) |

Availability changes without notice; re-check on purchase day. Each
sending domain gets a 301 redirect to unpauseai.com (Porkbun URL
forwarding) so a recipient who types the domain lands somewhere real.

## 3. Mailbox plan: Google Workspace (recommendation)

| Item | Value | Source |
|---|---|---|
| Business Starter | EUR 6.80/user/mo (flexible monthly; EUR 3.40 first 3 months promo) | workspace.google.com/pricing, 2026-07-22 |
| Annual-commit discount | "Save 16% with 1 year commitment" (page wording) | same |
| Alternative: M365 Business Basic | $7.00/user/mo, annual subscription | microsoft.com compare page, 2026-07-22 |

Plan: **2 mailboxes per domain**. Standard config = 3 domains x 2 =
6 mailboxes = EUR 40.80/mo (EUR 20.40/mo during the 3-month promo).
Minimal config = 2 domains x 2 = 4 mailboxes = EUR 27.20/mo. Sender
display names are an owner decision at purchase (ties to the u2
author/entity decision). Why Google over M365: warm-up tooling
compatibility and the existing client-farm precedent; take the monthly
flex, not the annual commit, until the channel proves itself.

## 4. ESP: Instantly (recommendation: Growth, monthly)

| Tier | Price | Caps | Source |
|---|---|---|---|
| Growth | $47/mo | 1,000 uploaded contacts, 5,000 emails/mo, unlimited email accounts, warm-up included | instantly.ai/pricing, 2026-07-22 |
| Hypergrowth | $97/mo | 25,000 contacts, 100,000 emails/mo | same |
| Light Speed | $358/mo | 100,000 contacts, 500,000 emails/mo | same |

Annual billing = 10% off (page wording). Start on Growth monthly: the
ICP's cold pool is small and the 1,000-contact cap binds only once list
building outgrows the first campaigns; upgrade to Hypergrowth is a
same-day switch when it does.

## 5. List building: Apollo (recommendation: start Free)

| Tier | Price | Credits | Source |
|---|---|---|---|
| Free | $0 | 900 credits | apollo.io/pricing (JS-rendered; read via browser), 2026-07-22 |
| Basic | $49/seat/mo billed annually | 30,000 credits/yr | same |
| Professional | $79/seat/mo billed annually | 48,000 credits/yr | same |
| Organization | $119/seat/mo billed annually (min 3 seats) | 72,000 credits/yr | same |

Note: the page shows annual-billed rates; the monthly-billed rate was
not displayed and is TBD. Start Free: the u1 filter spec (UK+US,
owner/founder/MD, 5-50 employees, Make/n8n/Zapier/GHL technographics,
DE excluded) targets a small pool, and 900 credits cover the first list.
The meji Apollo filter-spec pattern is reusable once a credential exists.

## 6. Verification: NeverBounce (price TBD)

NeverBounce is the house precedent, but its pricing page returned 403 /
a press-and-hold bot wall on 2026-07-22 (direct fetch and browser both
blocked; ZeroBounce's pricing page was walled the same way). Per B4:
**price TBD; verify on purchase day before buying credits.**

Cost-shaping fact that does not depend on the vendor quote: the MX
pre-filter (drop Mimecast-gatewayed domains before verification; see
`reference_cold_email_gateway_bounces`) runs first and shrinks the paid
verification volume.

## 7. DNS-auth runbook (per sending domain)

Order matters: mailboxes must exist before DKIM can be generated.

1. Add the domain to Google Workspace (secondary domain), verify via
   TXT record on Porkbun.
2. MX: Google's current MX set (Workspace admin shows the exact hosts).
3. SPF: `v=spf1 include:_spf.google.com ~all` (TXT, root). One SPF
   record per domain, never two.
4. DKIM: Workspace Admin -> Apps -> Gmail -> Authenticate email ->
   generate 2048-bit key -> publish TXT at `google._domainkey` -> turn
   authentication ON in admin.
5. DMARC: TXT at `_dmarc`: `v=DMARC1; p=none; rua=mailto:dmarc@{domain}`
   during warm-up; tighten to `p=quarantine` after the first clean month.
6. Custom tracking domain for Instantly: CNAME per Instantly's setup
   screen, one per domain.
7. Root redirect: Porkbun URL forward 301 -> unpauseai.com.
8. Verify all records (dig/nslookup + Google Admin Toolbox checkup)
   before connecting anything to Instantly.

## 8. Day-1-after-go sequence (same-day warm-up start)

1. Re-check domain availability; register the 3 domains (Porkbun).
2. Create/extend the Google Workspace tenant; add domains; create the
   6 mailboxes.
3. Run the DNS runbook (section 7) for all 3 domains.
4. Connect all mailboxes to Instantly; enable warm-up the same day.
   Warm-up ramp: start low single digits per day, rising toward
   normal sending over 3-4 weeks (`project_brisken_outreach_domains`
   precedent: no real sends before the clock completes).
5. Calendar marker at day 21 and day 28: earliest first real send
   window opens.
6. During warm-up (parallel, no sends): build the Apollo list per the
   u1 filter spec, run the MX pre-filter, verify the remainder, draft
   sequences. Instantly delay semantics: the gap belongs on the EARLIER
   step (`reference_instantly_sequence_delay_semantics`).
7. Any first real send is a separate B5-gated decision (scope-of-effects
   + readiness audit per `rule_instantly_invasive`); warm-up completion
   does not authorize sending.

## 9. Cost roll-up (as-displayed currencies, standard config)

| Line | Cost |
|---|---|
| Domains (3 x .com, Porkbun) | $33.24/yr one-line |
| Mailboxes (6 x GWS Starter, monthly flex) | EUR 40.80/mo (EUR 20.40 first 3 months) |
| ESP (Instantly Growth, monthly) | $47/mo |
| List (Apollo Free) | $0 (upgrade path $49/seat/mo annual-billed) |
| Verification (NeverBounce) | TBD |

**Model-feedback flag:** the leadgen-portfolio scorer assumes EUR 40/mo
fixed cold-email infra. The real ready-to-buy stack is roughly EUR 40.80
+ $47 monthly before verification, i.e. about double the modeled fixed
cost at standard config (minimal config: EUR 27.20 + $47). When the
channel goes live, this belongs in the same re-pin conversation as the
pool validations (u4 pattern).

## 10. Purchase-approval checklist (each line needs its own owner yes)

- [ ] Domains: tryunpauseai.com, unpause-ai.com, unpauseautomation.com ($33.24/yr)
- [ ] Google Workspace: 6 x Business Starter monthly (EUR 40.80/mo)
- [ ] Instantly Growth ($47/mo)
- [ ] Apollo (start Free, $0; upgrade needs its own approval)
- [ ] NeverBounce credits (TBD; quote on purchase day)
