# u1 list filter + cold-email sequences (warm-up-parallel build)

Two build artifacts prepped during warm-up, both account-agnostic (no live
account needed to draft them). Execution waits on the UnpauseAI-owned Apollo
+ Instantly accounts (see `cold-email-purchase-checklist.md` §12).

Structural constraint on everything below: **UK + US targets only, Germany
excluded** (UWG §7, not optional). The filter enforces it by whitelisting
countries, not by blacklisting DE.

## Part A - Apollo list filter (exact query)

Derived from `icp.md` (the Route-2 persona). Set these in Apollo People
search; export, then MX-prefilter, then verify.

| Field | Value |
|---|---|
| Person titles | Founder, Co-Founder, Owner, CEO, Managing Director, Director |
| Seniority | Owner, Founder, C-Suite (exclude IC / VP-of-large-org noise) |
| Company headcount | 1-10, 11-20, 21-50 (ICP: ~5-50, plus solo founders at the micro end) |
| Country (whitelist) | United Kingdom, United States. Nothing else. |
| Technologies (any of) | Make.com, n8n, Zapier, HubSpot Operations Hub, GoHighLevel, Instantly, Apollo |
| Email status | Verified (Apollo's own status; we re-verify externally regardless) |

Notes:
- **The technographic markers are the discriminator, not industry.** The won
  set spans events, treasury, HVAC/renewables, construction, agencies; the
  common factor is an owner running a revenue process on low-code, which the
  Make/n8n/Zapier/GHL signal captures better than any single industry. Leave
  industry open unless the pool is too large, then narrow to the won verticals.
- Apollo technographic coverage is partial; a lead using Make/n8n may not be
  tagged. Treat the tech filter as precision-over-recall: it gives a cleaner,
  smaller, higher-intent list, which suits a small cold pool and Instantly's
  1,000-contact Growth cap.
- **Export reality (2026-07-28):** Apollo's free tier caps bulk export at 25
  records; it cannot build this list. A Basic seat is required (checklist §5).

## Part B - Pre-verification hygiene (before paying to verify)

1. **MX pre-filter (free, runs first).** Resolve each domain's MX; drop any
   fronted by Mimecast (`*.mimecast.com`). Mimecast rejects cold at the
   gateway and a verifier will not catch it, so paying to verify those is
   wasted (`reference_cold_email_gateway_bounces`). This shrinks the paid
   volume.
2. **Verify the remainder** with MillionVerifier (checklist §6); keep only
   `ok`. Drop catch-all/unknown for the first warm campaigns.
3. **Dedup** against any other live UnpauseAI sending list (none yet; will
   matter once u3 runs).

## Part C - Sequence library (v1 drafts, not for send)

4-touch sequence. Sender: **Matthias Neumann**, UnpauseAI. Plain text, one
link max, one ask per email. These are DRAFTS: any outcome/metric claim is
bracketed and needs a verified, owner-approved case before it goes near a
send (B4). First real send is B5-gated regardless.

**Cadence + Instantly delay semantics.** Emails at day 0 / 3 / 7 / 12
(increasing gaps). In Instantly the wait lives on the EARLIER step
(`reference_instantly_sequence_delay_semantics`): Step 1 delay = 3, Step 2
delay = 4, Step 3 delay = 5, Step 4 is last (its delay never fires a send).
Never set a step's delay to 0 while it has a next step; delay 0 double-sends.

**Merge variables** (source per lead):
- `{{firstName}}` - Apollo
- `{{stackTool}}` - the detected automation tool (Make / n8n / Zapier / GHL); pick the one Apollo tagged
- `{{personalizedLine}}` - a level-2+ research line tied to the problem (a real observation about their site/stack/hiring), added per lead, never a generic "saw your profile". If no genuine line exists, the lead is under-researched; hold it rather than ship a thin opener.

---

### Step 1 (day 0) - the one-head-deep problem

Subject: `{{stackTool}} handoff`

> Hi {{firstName}},
>
> {{personalizedLine}}. Setups like that usually live in one person's head, so when they leave or get swamped the flow breaks quietly and a lead or two goes missing before anyone notices.
>
> We take those over: rebuild it, run it, and own it end to end so it isn't one head deep. Most of our work is fixing someone's half-finished {{stackTool}} build, not starting from scratch.
>
> Worth a look at how yours is holding up?
>
> Matthias

### Step 2 (day 3) - the handoff leak / speed-to-lead

Subject: `leads slipping`

> Hi {{firstName}},
>
> One follow-on thought: the place these setups leak most is the handoff, where a lead comes in on one tool and has to land in another, and the gap is where it stalls or goes cold.
>
> We close that gap and make it fast, so a new lead gets an answer in minutes instead of the next time someone opens the sheet.
>
> Is speed-to-lead something you're watching, or is it fine as is?
>
> Matthias

### Step 3 (day 7) - rescue proof (anonymized)

Subject: `quick one`

> Hi {{firstName}},
>
> One example in case it helps: a team we work with had a large outbound operation producing almost nothing usable. The tools were fine; the routing and enrichment around them were the bottleneck. We took the pipeline over and rebuilt that layer [insert one verified, owner-approved outcome metric here before send].
>
> Different setup to yours, same shape: the tool works, the plumbing around it doesn't.
>
> Want me to flag where yours might be leaking?
>
> Matthias

### Step 4 (day 12) - breakup

Subject: `closing the loop`

> Hi {{firstName}},
>
> I'll leave it here so I'm not cluttering your inbox. If the {{stackTool}} side ever gets flaky or too manual, we're the people who take it over and run it, and we're EU-based so there's a solid overlap with your day.
>
> If now isn't the time, no problem, I'll assume it's handled. Have a good rest of the week.
>
> Matthias

---

**Compliance footer (Instantly-managed, required on every step):**
- One-click unsubscribe (Instantly's list-unsubscribe + footer link).
- Real sender identity + a valid postal address for CAN-SPAM (US recipients):
  supply UnpauseAI's registered address; do not fabricate one.
- Single content link only: `unpauseai.com` in the signature. No images, no
  tracking pixels beyond Instantly's per-domain tracking CNAME.

**Refinement hooks (before first send):**
- Positioning/offer ties to u5 (scope-to-deliverables) and the u2 author/entity
  decision; revisit the copy once those land.
- Replace the Step 3 bracket with a real, approved case + metric, or cut the
  metric and keep the problem-shape framing.
