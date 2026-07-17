# Instantly Audit Inventory

Meji Media, Banter Experiences, MejiAI
For Gurmej Pawar
2026-05-10

## 1. Project context

| Item | Detail |
|---|---|
| Audit origin | Requested by Gurmej on 2026-04-22 call; tracked in the handover package |
| Three growth segments raised on 2026-04-22 | (1) Instantly outbound revival across Christmas DB warm, cold revival, and hen/stag DB; (2) lead-scoring and monitoring dashboard for Instantly; (3) corporate-side automation |
| Two Upwork threads | Thread 1 "Automated Follow-Up System Development" (Gurmej, Jess, Anuj). Thread 2 "General outreach project" (1:1 with Gurmej). Instantly work belongs in Thread 2 |
| Instantly login | `gurmej@mejimedia.com` |
| "10 to 11 warmed domains" framing | Stated on 2026-04-27 in Thread 2 |
| Banter Experiences ownership | Established in-session: a Gurmej-owned business, not separate |
| Three outbound businesses operating | Meji Media (events), MejiAI (automation services for trades), Banter Experiences (stag/hen/corporate weekends) |
| Stakeholders on the Upwork side | Gurmej (owner, decision-maker), Jess Harrar (operations), Anuj (developer and DNS) |

## 2. Campaign metrics from the dashboard

The top-level Campaigns view.

| Campaign | Status | Sent | Click | Replies | Reply rate | Opportunities |
|---|---|---|---|---|---|---|
| Event Mgmt Companies / Chatbots / Vayne | Paused | 1,924 | 0 | 37 | 3.5% | 2 |
| MejiAI / Construction, HVAC, Plumbers, Electricians | Bounces (auto-paused) | 216 | 0 | 7 | 3.9% | 0 |
| Meji Media / Corporate Events / Big Companies in UK | Bounces (auto-paused) | 1,968 | 0 | 21 | 2.0% | 0 |
| Meji Media – Christmas Bookers | Active 99% | 1,923 | 0 | 42 | 4.3% | 4 |
| Banter reactivation – Booked | Completed | 8,588 | 0 | 48 | 1.1% | 8 |
| **Totals** | | **14,619** | **0** | **155** | | **14** |

Workspace-level:

| Item | Value |
|---|---|
| Lead-credit balance ("Get Leads" pool) | 1,000 |
| Click tracking | Disabled across every campaign (all show 0 clicks) |

## 3. Per-campaign analytics drill-down

Detailed data analytics by campaign.

### 3a. MejiAI

| Field | Value |
|---|---|
| Last send activity | Single send-spike mid-November 2025 (around 13 to 18 Nov), flatline since |
| Progress | 18% |
| Sequence started | Blank on Analytics header |
| Open rate | Disabled |
| Click rate | Disabled |
| Opportunities | 0 |
| Conversions | 0 |
| Step 1 total | 180 sent, 0 opened, 7 replied (3.89%), 0 clicked, 0 opportunities |
| Step 1 variant A | 60 sent, 2 replies (3.3%) |
| Step 1 variant B | 60 sent, 4 replies (6.7%) |
| Step 1 variant C | 60 sent, 1 reply (1.7%) |
| Step 2 (single variant A) | 36 sent, 0 opens, 0 replies |

### 3b. Corporate Events

| Field | Value |
|---|---|
| Last send activity | Spikes 9 Nov to 15 Dec 2025, then two further spikes mid-January 2026, flatline since |
| Progress | 69% |
| Sequence started | 1,058 unique leads |
| Open rate | Disabled |
| Click rate | Disabled |
| Opportunities | 0 |
| Conversions | 0 |
| Analytics date filter | "Last 6 months" |
| Step 1 total | 1,058 sent, 0 opened, 11 replied (1.04%), 0 clicked, 0 opportunities |
| Step 1 variant A | 353 sent, 5 replies (1.4%) |
| Step 1 variant B | 353 sent, 4 replies (1.1%) |
| Step 1 variant C | 352 sent, 2 replies (0.6%) |
| Step 2 (single variant A) | 910 sent, 0 opens, 9 replies (0.99%), 0 opportunities |

### 3c. Christmas Bookers

| Field | Value |
|---|---|
| Status | Active 99% |
| Step structure | Step 1 only, no automated Step 2 |
| Step 1 subject variants configured | 4 (A active, B/C/D inactive) |
| Step 1 "Send next message in" setting | 2 days (unused, since no Step 2 exists) |
| Sender mailboxes attached | `gurmej.pawar@mejimedia.co`, `gurmej@mejimedia.co` (visible in reply From: fields) |

## 4. Diagnose API output

Both bounce-paused campaigns returned identical JSON.

| Campaign | Status returned | Diagnostics object |
|---|---|---|
| MejiAI | `campaign_bounce_protect` (paused due to bounce protection) | `null` |
| Corporate Events | Same status, same message | `null` |

Other fields on both exports: `issue_started_at: null`, `last_healthy_send_at: null`, `ai_summary: null`. No per-domain breakdown returned.

## 5. Sender infrastructure

The Email Accounts page, split into per-mailbox and per-domain views.

### 5a. Per-mailbox

| Mailbox | Sent today | Warmup volume | Health % | Indicator |
|---|---|---|---|---|
| `gurmej.p@mejiai.com` | 0 of 30 | 62 | 100 | Green flame |
| `gurmej.p@mejievent.com` | 0 of 30 | 64 | 98 | Green flame |
| `gurmej.p@mejimedia.co` | 0 of 30 | 0 | 100 | Red flame |
| `gurmej.pawar@mejiai.com` | 0 of 30 | 61 | 100 | Green flame |
| `gurmej.pawar@mejievent.com` | 0 of 30 | 63 | 100 | Green flame |
| `gurmej.pawar@mejimedia.co` | 0 of 30 | 0 | 0 | Red flame |
| `gurmej@mejiai.com` | 0 of 30 | 62 | 100 | Green flame |
| `gurmej@mejievent.com` | 0 of 30 | 61 | 100 | Green flame |
| `gurmej@mejimedia.co` | 0 of 30 | 0 | 100 | Red flame |
| `jessica.h@banterexp.com` | 0 of 30 | 65 | 100 | Green flame |
| `jessica.harrar@banterexp.com` | 0 of 30 | 69 | 100 | Green flame |
| `jessica@banterexp.com` | 0 of 30 | 70 | 100 | Green flame |

| Item | Value |
|---|---|
| Mailbox rows visible across both screenshots | 12 |
| User-stated authoritative total | 11 |
| Discrepancy | One mailbox in the source data isn't in the stated count. Most likely the 0%-health `gurmej.pawar@mejimedia.co` excluded as effectively dead |

### 5b. Per-domain

| Domain | Mailbox aliases | Persona | Warmup state | Visible use |
|---|---|---|---|---|
| `mejimedia.co` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (parent brand) | Off across all three (mature production) | Christmas Bookers, Corporate Events |
| `mejiai.com` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (sub-brand) | On | MejiAI |
| `mejievent.com` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (sub-brand) | On | Mixed; appears in Corporate Events reply chains |
| `banterexp.com` | jessica, jessica.h, jessica.harrar | Jessica Harrar | On | Banter reactivation |

## 6. Bounce composition

Recipient-level detail for the two bounce-paused campaigns.

### 6a. MejiAI bounced leads (12 visible)

All show "Email Security Gateway: None".

| Recipient | Title | Provider |
|---|---|---|
| peter@ecologic-sips.co.uk | Founder | Microsoft |
| michaelg@rcd-yorkshire.co.uk | Contract Manager | Other |
| jeremy@smeconcepts.co.uk | Chief Executive Officer | Google |
| jamie@taylorsolar.co.uk | Director & Co-Founder | Microsoft |
| dave_simms@narboroughwindowsconservatories.co.uk | Business Owner | Microsoft |
| debbi@torrancegroup.co.uk | Company Owner | Microsoft |
| andrew.coombe@quantumquote.co.uk | Founder / Director | Not Found |
| dave.w@midlandsflooring.co.uk | Managing Director | Microsoft |
| wspence.mice@pmgroup-global.com | Construction Manager | Microsoft |
| matthew_booth@nwflooringsolutions.co.uk | Co-Owner | Microsoft |
| andy_wynjones@xpressiveinteriors.co.uk | Director Owner | Other |
| doherty@foundationsolutionshv.com | Supervisor | Microsoft |

| Stat | Value |
|---|---|
| MejiAI bounce count (visible) | 12 |
| MejiAI Step 1 sent | 180 |
| MejiAI bounce rate | 6.7% (12 / 180) |

### 6b. Corporate Events bounced leads (12 of 19 visible)

| Recipient | Title | Provider | Gateway |
|---|---|---|---|
| e.j.robinson.1@bham.ac.uk | Operations Coordinator / PA | Other | Proofpoint |
| d.coleman@bham.ac.uk | CEO, University of Birmingham | Other | Proofpoint |
| l.h.neale@bham.ac.uk | PA / Administrative Officer | Other | Proofpoint |
| james@taxbuddi.co.uk | Chief Executive Officer | Google | None |
| ababirye@misr.mak.ac.ug | PA (listed as Univ of Nottingham; actually Makerere, Uganda) | Other | None |
| s.vincent@bham.ac.uk | PA to Director of Development | Other | Proofpoint |
| blackburn@nfumutual.co.uk | PA | Microsoft | None |
| lian.styring@mfgsolicitors.com | PA, mfg Solicitors LLP | Other | Mimecast |
| a.partleton@bham.ac.uk | PA | Other | Proofpoint |
| liz.rowe@communitytransport.org | Deputy Chief Executive Officer | Other | None |
| a.m.farley@bham.ac.uk | Office Manager / PA | Other | Proofpoint |
| liz.stokes@apc-overnight.com | Human Resources Director | Microsoft | None |

| Stat | Value |
|---|---|
| Corporate Events bounce counter | 19 total |
| Corporate Events contacted (denominator) | 622 |
| Corporate Events bounce rate | 3.1% (19 / 622) |
| `bham.ac.uk` concentration | 6 of 12 visible bounces (50%) |

## 7. Operational patterns

Patterns visible across the campaigns reviewed.

| Pattern | Evidence |
|---|---|
| Single-touch send plus manual personal follow-up | Christmas Bookers Sequences view has Step 1 only (confirmed by Gurmej); inbox threads show Gurmej manually following up |
| 2-day cadence between Step 1 and follow-up | Chris Rice Banter thread: 7 January Step 1, 9 January follow-up. Christmas Bookers Sequences config carries the same "Send next message in 2 Days" setting |
| Thread continuity within rotation | Chris Rice received Step 1 and the manual follow-up from the same `jessica.h@` alias, not a different jessica address |
| Three mailboxes per domain | Every domain has exactly 3 mailbox aliases (gurmej, gurmej.p, gurmej.pawar on Meji-side; jessica, jessica.h, jessica.harrar on Banter) |
| Persona separation by brand | Meji-side domains all use the Gurmej persona; `banterexp.com` uses the Jessica Harrar persona |
| Tracking globally disabled | Every campaign shows "Open rate: Disabled" and "Click rate: Disabled" on Analytics; dashboard shows 0 clicks across the board |

## 8. Derived findings

Conclusions reached over the data in the previous sections, grouped by topic.

### 8a. Performance ratios

| Finding | Evidence |
|---|---|
| MejiAI carries a 6.7% bounce rate | 12 bounces from 180 Step 1 sends |
| Corporate Events carries a 3.1% bounce rate | 19 bounces against 622 contacted |
| Christmas Bookers turns 9.5% of replies into tagged opportunities | 4 opportunities from 42 replies |
| Banter turns 16.7% of replies into tagged opportunities | 8 opportunities from 48 replies |

### 8b. Capacity and infrastructure

| Finding | Evidence |
|---|---|
| Daily send capacity sits around 250 emails | 11 mailboxes at 30 a day nominal, minus mejimedia.co's warmup-off effect and general warmup overhead |
| That works out to roughly 7,500 emails a month | 250 a day across 30 days |
| `mejimedia.co` is the production sender for Christmas Bookers and isn't broken | The same addresses appear in the From: line on Christmas Bookers reply threads. The red flame means warmup is off because the mailbox is mature, not because it's broken |
| The `.com` is the login mailbox; the `.co` is what actually sends | Login per the handover is `.com`; senders in the inbox are all `.co`. Whether `.com` is ever used as a sender elsewhere isn't established |
| Sender reputation looks intact on what's visible in the workspace | Instantly health scores 98 to 100% on the working mailboxes; no spam-complaint trips; bounce trips trace to recipient-side issues, not sender-side |
| The Diagnose API doesn't show per-domain bounce breakdowns | Both JSON exports returned `diagnostics: null` plus the top-level paused-for-bounces status |

### 8c. Failure modes

| Finding | Evidence |
|---|---|
| MejiAI failed on list quality, not infrastructure | All 12 visible bounces show "Gateway: None"; the bounced leads span solar, panels, and generic consulting against a brief targeted at plumbing and HVAC; one human reply confirmed the recipient was on a wrong-vertical list |
| Corporate Events failed on audience choice, not deliverability | 6 of 12 visible bounces are `bham.ac.uk` behind Proofpoint; the reply set includes an NHS Finance Administrator; a legal firm on the list ran Mimecast |

## 9. Audit gaps

Items that couldn't be verified from the data available in this session, plus discrepancies surfaced during cross-checking.

| Gap | Reason |
|---|---|
| Google Postmaster Tools data per domain | No DNS access on Meji-owned domains during the audit |
| Microsoft SNDS | Recipient-side opt-in tool, not generally claimable for arbitrary domains |
| Per-domain bounce attribution from Instantly | Diagnose API returned no breakdown for either bounce-paused campaign |
| Vayne campaign drill-down | Not opened beyond dashboard-level metrics (1,924 sent, 2 opportunities, paused) |
| Per-mailbox campaign attribution in Email Accounts view | Health is visible, but no per-campaign send mapping |
| Lead-source pipeline for any campaign | Not visible from Instantly; would need the previous contractor's lead-sourcing tool. Apollo, Lusha, or scrape source unknown |
| Whether NHS / public-sector recipients were intentional or scrape noise on the cold lists | The bounce and reply composition implies a list-quality issue. No explicit confirmation in-session |
