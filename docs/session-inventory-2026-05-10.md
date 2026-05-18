# Session Inventory: Instantly Audit, Meji Media

**Date:** 2026-05-10
**Session scope:** Instantly workspace audit for Gurmej Pawar across Meji Media, Banter Experiences, and MejiAI. Capture window 8 to 10 May 2026.

Reference document. Tables grouped by category. Every row carries a Source column with one of:

- **Screenshot** — visible in a screenshot the user pasted in chat
- **Correction** — stated directly by the user as a correction or clarification
- **Derived** — analytical conclusion over screenshots or corrections

Where a row blends sources, all are listed. Where a row can't be cleanly traced, it's flagged with `?` and routed to Section 13.

---

## 1. Client and project context

Pulled from the handoff-package.md at session start.

| Item | Detail | Source |
|---|---|---|
| Audit origin | Requested in `handoff-package.md` §9 step 11 and §10 (Days 5-14 and Days 15-30 of the Meji handover) | Screenshot |
| Three growth segments raised by Gurmej on 2026-04-22 call | (1) Instantly outbound revival across Christmas DB warm, cold outreach revival, hen/stag DB; (2) Lead-scoring + monitoring dashboard for Instantly campaigns; (3) Corporate-side automation | Screenshot |
| Two Upwork threads | Thread 1 "Automated Follow-Up System Development" (Gurmej, Jess, Anuj). Thread 2 "General outreach project" (1:1 with Gurmej). Instantly work belongs in Thread 2 | Screenshot |
| Instantly login | `gurmej@mejimedia.com` / `<ASK-NICOLAS-OFFLINE>` | Screenshot |
| Gurmej's "10 to 11 warmed domains" framing | Stated on 2026-04-27 in Thread 2 | Screenshot |
| Banter ownership | Established mid-session: Banter Experiences is a Gurmej-owned business, not separate | Screenshot + Derived |
| Gurmej-owned outbound businesses | Meji Media (events), MejiAI (automation services to trades), Banter Experiences (stag/hen/corporate weekends) | Derived |
| Upwork-side stakeholders | Gurmej (owner, decision-maker), Jess Harrar (operations), Anuj (developer/DNS) | Screenshot |

---

## 2. Campaign metrics from the dashboard

From the top-level Campaigns view.

| Campaign | Status | Sent | Click | Replies | Reply rate | Opps | Source |
|---|---|---|---|---|---|---|---|
| Event Mgmt Companies / Chatbots / Vayne | Paused | 1,924 | 0 | 37 | 3.5% | 2 | Screenshot |
| MejiAI / Construction, HVAC, Plumbers, Electricians | Bounces (auto-paused) | 216 | 0 | 7 | 3.9% | 0 | Screenshot |
| Meji Media / Corporate Events / Big Companies in UK | Bounces (auto-paused) | 1,968 | 0 | 21 | 2.0% | 0 | Screenshot |
| Meji Media – Christmas Bookers | Active 99% | 1,923 | 0 | 42 | 4.3% | 4 | Screenshot |
| Banter reactivation – Booked | Completed | 8,588 | 0 | 48 | 1.1% | 8 | Screenshot |
| **Totals** | | **14,619** | **0** | **155** | | **14** | Derived (sum) |

Workspace-level:

| Item | Value | Source |
|---|---|---|
| Lead-credit balance ("Get Leads" pool) | 1,000 | Screenshot |
| Click tracking | Disabled across every campaign (all show 0 clicks) | Derived |

---

## 3. Per-campaign analytics drill-down

From each campaign's Analytics tab. Fields not visible in the Campaigns list.

### 3a. MejiAI

| Field | Value | Source |
|---|---|---|
| Last send activity | Single send-spike mid-Nov 2025 (around 13 to 18 Nov), flatline since | Screenshot |
| Progress | 18% | Screenshot |
| Sequence started | Blank/dash on Analytics header | Screenshot |
| Open rate | Disabled | Screenshot |
| Click rate | Disabled | Screenshot |
| Opportunities | 0 (0 / $0) | Screenshot |
| Conversions | 0 (0 / $0) | Screenshot |
| Step 1 total | 180 sent, 0 opened, 7 replied (3.89%), 0 clicked, 0 opps | Screenshot |
| Step 1 variant A | 60 sent, 2 replies (3.3%) | Screenshot |
| Step 1 variant B | 60 sent, 4 replies (6.7%) | Screenshot |
| Step 1 variant C | 60 sent, 1 reply (1.7%) | Screenshot |
| Step 2 (single variant A) | 36 sent, 0 opens, 0 replies | Screenshot |

### 3b. Corporate Events

| Field | Value | Source |
|---|---|---|
| Last send activity | Spikes 9 Nov to 15 Dec 2025, then two further spikes mid-Jan 2026, flatline since | Screenshot |
| Progress | 69% | Screenshot |
| Sequence started | 1,058 unique leads | Screenshot |
| Open rate | Disabled | Screenshot |
| Click rate | Disabled | Screenshot |
| Opportunities | 0 (0 / $0) | Screenshot |
| Conversions | 0 (0 / $0) | Screenshot |
| Analytics date filter | "Last 6 months" | Screenshot |
| Step 1 total | 1,058 sent, 0 opened, 11 replied (1.04%), 0 clicked, 0 opps | Screenshot |
| Step 1 variant A | 353 sent, 5 replies (1.4%) | Screenshot |
| Step 1 variant B | 353 sent, 4 replies (1.1%) | Screenshot |
| Step 1 variant C | 352 sent, 2 replies (0.6%) | Screenshot |
| Step 2 (single variant A) | 910 sent, 0 opens, 9 replies (0.99%), 0 opps | Screenshot |

### 3c. Christmas Bookers

| Field | Value | Source |
|---|---|---|
| Status | Active 99% | Screenshot |
| Step structure | Step 1 only (no automated Step 2) | Correction |
| Step 1 subject variants configured | 4 (A active, B/C/D inactive) | Screenshot |
| Variant A (active) | "{firstName}, quick win for you" | Screenshot |
| Variant B (inactive) | "Quick win on events for you, {firstName}" | Screenshot |
| Variant C (inactive) | "remember the dancers, {firstName}?" | Screenshot |
| Variant D (inactive) | "You've grown, {firstName}!" | Screenshot |
| Step 1 "Send next message in" setting | 2 days (unused since no Step 2 exists) | Screenshot |
| Sender mailboxes attached | `gurmej.pawar@mejimedia.co`, `gurmej@mejimedia.co` (visible in reply From: fields) | Screenshot + Derived |

---

## 4. Diagnose API output

Both bounce-paused campaigns returned identical JSON.

| Campaign | Status returned | Diagnostics | Source |
|---|---|---|---|
| MejiAI | `campaign_bounce_protect` ("Campaign has been paused due to bounce protection. This happens when too many emails have bounced. You can disable this feature from the campaign settings.") | `null` | Screenshot |
| Corporate Events | Same status, same message | `null` | Screenshot |

Other fields on both exports: `issue_started_at: null`, `last_healthy_send_at: null`, `ai_summary: null`.

---

## 5a. Sender infrastructure — per-mailbox

From the Email Accounts page across the two screenshots provided.

| Mailbox | Sent today | Warmup volume | Health % | Indicator | Source |
|---|---|---|---|---|---|
| `gurmej.p@mejiai.com` | 0 of 30 | 62 | 100 | Green flame | Screenshot |
| `gurmej.p@mejievent.com` | 0 of 30 | 64 | 98 | Green flame | Screenshot |
| `gurmej.p@mejimedia.co` | 0 of 30 | 0 | 100 | Red flame | Screenshot |
| `gurmej.pawar@mejiai.com` | 0 of 30 | 61 | 100 | Green flame | Screenshot |
| `gurmej.pawar@mejievent.com` | 0 of 30 | 63 | 100 | Green flame | Screenshot |
| `gurmej.pawar@mejimedia.co` | 0 of 30 | 0 | 0 | Red flame | Screenshot |
| `gurmej@mejiai.com` | 0 of 30 | 62 | 100 | Green flame | Screenshot |
| `gurmej@mejievent.com` | 0 of 30 | 61 | 100 | Green flame | Screenshot |
| `gurmej@mejimedia.co` | 0 of 30 | 0 | 100 | Red flame | Screenshot |
| `jessica.h@banterexp.com` | 0 of 30 | 65 | 100 | Green flame | Screenshot |
| `jessica.harrar@banterexp.com` | 0 of 30 | 69 | 100 | Green flame | Screenshot |
| `jessica@banterexp.com` | 0 of 30 | 70 | 100 | Green flame | Screenshot |

| Item | Value | Source |
|---|---|---|
| Mailbox rows visible across both screenshots | 12 | Screenshot |
| User-stated authoritative total | 11 (6 + 5) | Correction |
| Discrepancy | One mailbox row in the source data is not in the user's count. Most likely explanation: `gurmej.pawar@mejimedia.co` (0% health) excluded as effectively dead. Not resolved in session. Surfaced again in Section 13 | Derived |

## 5b. Sender infrastructure — per-domain

Aggregated from 5a.

| Domain | Mailbox aliases | Persona | Warmup state | Visible use in workspace | Source |
|---|---|---|---|---|---|
| `mejimedia.co` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (parent brand) | Off across all three (mature production) | Christmas Bookers, Corporate Events | Screenshot + Derived |
| `mejiai.com` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (sub-brand) | On | MejiAI; potentially Banter cross-rotation (see Section 13) | Screenshot + Derived |
| `mejievent.com` | gurmej, gurmej.p, gurmej.pawar | Gurmej Pawar (sub-brand) | On | Mixed; appears in Corporate Events reply chains | Screenshot |
| `banterexp.com` | jessica, jessica.h, jessica.harrar | Jessica Harrar | On | Banter reactivation campaign | Screenshot |

---

## 6. Bounce composition

Recipient-level detail for the two bounce-paused campaigns.

### 6a. MejiAI bounced leads (12 visible)

All show "Email Security Gateway: None".

| Recipient | Title | Provider | Source |
|---|---|---|---|
| peter@ecologic-sips.co.uk | Founder | Microsoft | Screenshot |
| michaelg@rcd-yorkshire.co.uk | Contract Manager | Other | Screenshot |
| jeremy@smeconcepts.co.uk | Chief Executive Officer | Google | Screenshot |
| jamie@taylorsolar.co.uk | Director & Co-Founder | Microsoft | Screenshot |
| dave_simms@narboroughwindowsconservatories.co.uk | Business Owner | Microsoft | Screenshot |
| debbi@torrancegroup.co.uk | Company Owner | Microsoft | Screenshot |
| andrew.coombe@quantumquote.co.uk | Founder / Director | Not Found | Screenshot |
| dave.w@midlandsflooring.co.uk | Managing Director | Microsoft | Screenshot |
| wspence.mice@pmgroup-global.com | Construction Manager | Microsoft | Screenshot |
| matthew_booth@nwflooringsolutions.co.uk | Co-Owner | Microsoft | Screenshot |
| andy_wynjones@xpressiveinteriors.co.uk | Director Owner | Other | Screenshot |
| doherty@foundationsolutionshv.com | Supervisor | Microsoft | Screenshot |

| Stat | Value | Source |
|---|---|---|
| MejiAI bounce count (visible) | 12 | Screenshot |
| MejiAI Step 1 sent | 180 | Screenshot |
| MejiAI bounce rate | 6.7% (12 / 180) | Derived |

### 6b. Corporate Events bounced leads (12 of 19 visible)

| Recipient | Title | Provider | Gateway | Source |
|---|---|---|---|---|
| e.j.robinson.1@bham.ac.uk | Operations Coordinator / PA | Other | Proofpoint | Screenshot |
| d.coleman@bham.ac.uk | CEO, University of Birmingham | Other | Proofpoint | Screenshot |
| l.h.neale@bham.ac.uk | PA / Administrative Officer | Other | Proofpoint | Screenshot |
| james@taxbuddi.co.uk | Chief Executive Officer | Google | None | Screenshot |
| ababirye@misr.mak.ac.ug | PA (listed as Univ of Nottingham; actually Makerere, Uganda) | Other | None | Screenshot |
| s.vincent@bham.ac.uk | PA to Director of Development | Other | Proofpoint | Screenshot |
| blackburn@nfumutual.co.uk | PA | Microsoft | None | Screenshot |
| lian.styring@mfgsolicitors.com | PA, mfg Solicitors LLP | Other | Mimecast | Screenshot |
| a.partleton@bham.ac.uk | PA | Other | Proofpoint | Screenshot |
| liz.rowe@communitytransport.org | Deputy Chief Executive Officer | Other | None | Screenshot |
| a.m.farley@bham.ac.uk | Office Manager / PA | Other | Proofpoint | Screenshot |
| liz.stokes@apc-overnight.com | Human Resources Director | Microsoft | None | Screenshot |

| Stat | Value | Source |
|---|---|---|
| Corporate Events bounce counter | 19 total | Screenshot |
| Corporate Events contacted (denominator) | 622 | Screenshot |
| Corporate Events bounce rate | 3.1% (19 / 622) | Derived |
| `bham.ac.uk` concentration | 6 of 12 visible bounces (50%) | Derived |

---

## 7. Inbox replies surfaced

22 reply rows across the four campaigns inspected, plus 1 cross-categorization.

### 7a. MejiAI inbox (7 of 7 replies)

| Recipient | Type | Note | Source |
|---|---|---|---|
| Mark Avent (aventinteriors.co.uk) | OOO auto-reply | Until 15 Dec | Screenshot |
| Jay Fairgrieve (i-d-h.co.uk) | OOO auto-reply | Until 1 Dec | Screenshot |
| Tracey Glew (ferfa.org.uk) | OOO auto-reply | Until 24 Nov | Screenshot |
| Dean (aloftservices.co.uk) | OOO auto-reply | Until 28 Nov, with redirect contacts | Screenshot |
| Piers Gilbert (gilberthomes.co.uk) | OOO auto-reply | Return 24 Nov | Screenshot |
| Matt Kenney (kenney-cd.co.uk) | Real reply | "No thanks I'm not a plumber" (runs Kenney Consulting & Design) | Screenshot |
| Mark Stinton (unitedmep.co.uk) | OOO auto-reply | Until 24 Nov | Screenshot |

### 7b. Corporate Events inbox (sample, ~15% of ~20 total replies)

| Recipient | Type | Note | Source |
|---|---|---|---|
| Jane Burns (rainbows.co.uk) | Real reply | "No thanks" | Screenshot |
| Jason Emerson (covwarkpt.nhs.uk) | OOO auto-reply | NHS, until 2 Feb 2026 | Screenshot |
| James Salisbury (westleygroup.co.uk) | OOO auto-reply | Return 26 Jan 2026 | Screenshot |
| Tyler Doak (tylerjdoak@gmail.com) | Cross-categorization | Actually a Banter reply (sent from `jessica@banterexp.com`); appeared in this batch | Screenshot + Derived |

User noted "there were more but too many to paste all". Remaining ~16-17 replies not in this session's view.

### 7c. Christmas Bookers inbox (5 visible)

| Recipient | Tag | Note | Source |
|---|---|---|---|
| Jayne Nixon (jayne@sssfashions.co.uk), Director, SSS Fashions Ltd, Leicester | Interested | Sent 613KB document, "Please review it when you get a chance" | Screenshot |
| Suralita (alitte42@gmail.com) | Interested | TV/music production, "Las Vegas Theme" project. Gurmej manually followed up 13 Jan 2026; silent since | Screenshot |
| Tracey Hatfield (traceyhatfield@icloud.com) | None | Hard remove: "Please take my details off your mailing list" | Screenshot |
| Tom Sabin (tom.sabin@nhs.net), Finance Administrator, Black Country ICB | None | Polite "not at this time"; NHS external-sender warning visible | Screenshot |
| Simon Seal (sisports@icloud.com), Director, Si Sports Limited | None | "Hi Mel not for me this time sorry" (addressed Mel, not Gurmej) | Screenshot |

### 7d. Banter inbox (6 visible)

| Recipient | Type | Note | Source |
|---|---|---|---|
| Andy Judge (andy.directbathrooms@gmail.com) | Real opportunity | 20-person Budapest stag, asking for prices | Screenshot |
| Tyler Doak (tylerjdoak@gmail.com) | Defunct | "EMAIL NO LONGER IN USE" | Screenshot |
| Jude Thompson (jude.thompson@cscm.co.uk) | Sarcastic, brand-experience flag | CC'd `gurmej@mejimedia.com`; sent to colleague Craig Upton | Screenshot |
| Joshua Benson (joshjbenson@gmail.com) | Hard remove | "remove me from your list" | Screenshot |
| Lee Robinson (lee.robinson@metaeagle.co.uk) | OOO auto-reply, cross-domain anomaly | Sent from `gurmej.pawar@mejiai.com` despite Banter-style subject "any fooling around lately, Lee?" | Screenshot + Derived |
| Chris Rice (coppin1983@gmail.com) | Hard "Not interested" | Reply within 1.5h of follow-up | Screenshot |

---

## 8. Live pipeline items

Pulled from the inboxes during the audit. **Excluded from the client deliverable at user request** (`Leave the unworked leads in the mailbox out`). Retained here for reference.

| Name | Status | Type | Latest action visible | Source |
|---|---|---|---|---|
| Suralita | Interested, TV/music production | Real warm pipeline, "Las Vegas Theme" project | Gurmej manually followed up 13 Jan 2026; no response since | Screenshot |
| Jayne Nixon (SSS Fashions Ltd, Leicester) | Interested | Document sent (613KB brief) | Not visibly answered in thread | Screenshot |
| Andy Judge | Real opportunity | 20-person Budapest stag, pricing-stage | Replied 28 Jan 2026 asking for prices | Screenshot |
| Jude Thompson | Brand-experience flag | Past Banter customer, sarcastic reply | CC'd `gurmej@mejimedia.com` referencing "Russian guides...friends bars...extra commission. PMSLOL" | Screenshot |

---

## 9. Outreach copy and subject variants

Verbatim from email threads in the inbox.

### 9a. Step 1 / pitch bodies

| Campaign | Block | Content | Source |
|---|---|---|---|
| MejiAI | Step 1 body (visible in Matt Kenney reply chain) | "Hi [Name], I work with a trades company out in the UK(plumbing-specific). Not sure if you guys do plumbing, but wanted to run this by you. We set up an automated lead-capture system and have increased inbound leads by roughly 80%. The system instantly replies to enquiries, follows up until contact is made, and keeps everything moving while the lads are out on site. Pretty confident I could get you similar results, enough that I'll set the whole system up for you at no extra cost, and only if it brings you new business will I ask for a deal. Would this be of use to you? If yes, I'd be happy to give you a ring. Cheers, Gurmej." | Screenshot |
| Christmas Bookers | Step 1 body (Sequences view + reply chains) | "Hey {firstName}, Know your team had a blast at the last Christmas party, hence why I'm reaching out. People usually know us for the Christmas side of things (moonlight & mistletoe), but we handle events all year round; from team-building days and conferences to gala dinners. Recently helped a corporate group organise a full weekend; sourced their accommodation, set up go-karting, a private dinner, nightlife access, and delivered it all in one easy itinerary. If you're already planning something for {shortenedcompanyname}, happy to run some ideas by you. Would you be up for that? If yes, let me know and I can give you a ring. Cheers, Gurmej. p.s. for reference, google 'meji media'. Sent from my iPhone" | Screenshot |
| Christmas Bookers | Manual follow-up body (visible in Tracey Hatfield, Simon Seal threads) | "Hey [Name], just checking in again. Would this be of use to you? TLDR: Didn't get the chance to reconnect with you sooner since the last moonlight & mistletoe. Recently worked with Adidas & Polestar on a variety of events lately, from 10 people team building days to >350 gala dinners and celebrations. Thought I'd let you know, since I deeply enjoyed working with you and I do a variety of other events outside of Christmas. If this isn't the right fit, no worries, just wanted to put it in front of you. Cheers, Gurmej, Meji Media" | Screenshot |
| Banter | Pitch body (Step 1 + follow-up, visible in Andy Judge, Joshua Benson, Chris Rice threads) | "Hey [Name], just checking in again. Would there be any interest in this? TLDR: Recently worked with a handful of groups organising everything from stag & hen weekends to corporate hangouts. Took care of everything; curated hotel options, transfers, activity days to cocktail workshops, bottomless brunches, nightclub access, flexible accommodation, etc. Since you've booked with us before, wanted to see if you had anything planned lately. 15% reduced rate + booker rate is halved. If this isn't the right fit, no worries, just wanted to put it in front of you. Let me know. Cheers, Jessica, Banter Experiences" | Screenshot |

### 9b. Subject-line patterns

| Campaign | Observed patterns | Source |
|---|---|---|
| MejiAI | "Referral for you, [Name]" / "quick win for you, [Name]" / "sending you this, [Name]" | Screenshot |
| Corporate Events | "[Name], planning something?" / "quick win on events for you, [Name]" | Screenshot |
| Christmas Bookers | A: "{firstName}, quick win for you" (active); B: "Quick win on events for you, {firstName}"; C: "remember the dancers, {firstName}?"; D: "You've grown, {firstName}!" | Screenshot |
| Banter | "Quick win on events, [Name]" / "[Name], quick win for the weekend" / "any fooling around lately, [Name]?" | Screenshot |

---

## 10. Operational patterns observed

| Pattern | Evidence | Source |
|---|---|---|
| Single-touch + manual personal follow-up | Christmas Bookers Sequences view shows Step 1 only (user confirmed "No Step 2"); inbox threads show Gurmej manually following up | Screenshot + Correction |
| 2-day Step 1 to follow-up cadence | Chris Rice Banter thread: 7 Jan Step 1 → 9 Jan follow-up. Christmas Bookers Sequences config "Send next message in 2 Days" | Screenshot |
| Thread continuity within rotation | Chris Rice received Step 1 and manual follow-up from the same `jessica.h@` alias, not a different jessica address | Screenshot + Derived |
| Three-mailbox-per-domain rotation | Every domain has exactly 3 mailbox aliases (gurmej, gurmej.p, gurmej.pawar on Meji-side; jessica, jessica.h, jessica.harrar on Banter) | Screenshot |
| Persona separation by brand | Meji-side domains all use the Gurmej persona; `banterexp.com` uses the Jessica Harrar persona | Screenshot |
| Tracking globally disabled | All campaigns show "Open rate: Disabled" and "Click rate: Disabled" in Analytics; dashboard shows 0 clicks across every campaign | Screenshot |

---

## 11. User confirmations and corrections

Direct statements from the user that established or overrode something.

| Statement | Effect | Source |
|---|---|---|
| "i count 11" with "6+5" visual breakdown | Mailbox total = 11. Overrode my partial-visibility "9 visible" count from earlier in session | Correction |
| "Christmas Bookers: No Step 2" | The campaign is single-touch automated. Follow-ups are manual, by hand, not Instantly | Correction |
| "I dont have DNS on each domain" | DNS access on Meji-owned domains is not available during the audit. Postmaster verification is unreachable | Correction |
| "there were more but too many to paste all" (Corporate Events inbox) | Reply sample for Corporate Events is roughly 15% of the total ~20 replies | Correction |
| "Leave the unworked leads in the mailbox out" | Suralita, Jayne, Andy, Jude removed from the client deliverable | Correction |
| "your language needs to be more human" + "still too much text" | Voice and length feedback driving deliverable iterations | Correction |

---

## 12. Derived findings

Analytical conclusions over screenshots and corrections, each flagged with the evidence chain and a confidence note.

| Finding | Evidence chain | Confidence | Source |
|---|---|---|---|
| MejiAI bounce rate = 6.7% | 12 bounces (counter) / 180 Step 1 sent | High (direct ratio) | Derived |
| Corporate Events bounce rate = 3.1% | 19 bounces (counter) / 622 contacted | High (direct ratio) | Derived |
| Christmas Bookers reply-to-opportunity = 9.5% | 4 opps / 42 replies | High | Derived |
| Banter reply-to-opportunity = 16.7% | 8 opps / 48 replies | High | Derived |
| Realistic daily send capacity ≈ 250/day | 11 mailboxes × 30/day nominal, minus mejimedia.co warmup-off and general warmup overhead | Medium (assumption-dependent) | Derived |
| Monthly capacity ≈ 7,500 emails | 250/day × 30 | Medium | Derived |
| `mejimedia.co` is the production sender for Christmas Bookers, not broken | The exact addresses appear in From: fields on Suralita, Tracey, Tom Sabin, Simon Seal threads. Red flame = warmup-off-mature | High | Screenshot + Derived |
| TLD split observed: `.com` is the login mailbox; `.co` is the visible sender for the campaigns reviewed | Login per handoff is `.com`; senders in inbox screenshots are all `.co`. Whether `.com` is also used as a sender elsewhere is not established | Medium (sender side proven; non-use of `.com` not proven) | Screenshot + Derived |
| Banter ownership = Gurmej Pawar | Jude Thompson CC'd `gurmej@mejimedia.com` and named Gurmej directly in the reply text | High | Screenshot + Derived |
| Banter audience = past stag/hen/corporate weekend bookers | Pitch copy: "Since you've booked with us before". Andy Judge inquiry matches | High | Screenshot + Derived |
| MejiAI failure cause = list rot + off-vertical | All 12 visible bounces show "Gateway: None"; bounced leads include solar/SIPs/generic-consulting verticals on a "plumbing/HVAC" brief; Matt Kenney's "I'm not a plumber" reply confirms | High | Screenshot + Derived |
| Corporate Events failure cause = gateway rejection on public-sector lists | 6 of 12 visible bounces are bham.ac.uk on Proofpoint; reply set includes NHS Finance Administrator; Mimecast on legal firms | High | Screenshot + Derived |
| Banter playbook ≡ Christmas Bookers playbook structurally | Identical Step 1 + manual follow-up format, identical TLDR follow-up format, same 2-day cadence | High | Screenshot + Derived |
| Banter has a conversion lever Christmas Bookers does not | Banter pitch includes "15% reduced rate + booker rate is halved"; Christmas Bookers pitch has no equivalent | High | Screenshot |
| Sender reputation looks intact on signals available in-session | Instantly internal health 98-100% on working mailboxes; no spam-complaint trips visible; bounce trips trace to recipient-side, not sender-side | Medium (no Postmaster verification) | Derived |
| The Diagnose API alone can't surface per-domain bounce attribution | Both JSON exports returned `diagnostics: null` and only the top-level paused-for-bounces status | High | Screenshot |

---

## 13. Audit gaps and limitations

Things flagged in-session as not cleanly knowable, plus discrepancies surfaced during the verification pass on this inventory.

| Gap | Reason | Source |
|---|---|---|
| Google Postmaster Tools data per domain | No DNS access on Meji-owned domains during the audit | Correction |
| Microsoft SNDS | Recipient-side opt-in tool, not generally claimable for arbitrary domains | Derived |
| Per-domain bounce attribution from Instantly | Diagnose API returned no breakdown for either bounce-paused campaign | Screenshot |
| Full Corporate Events reply set | User pasted approximately 15% of the ~20 replies. The remaining ~16-17 are not in this session's view | Correction |
| Vayne campaign drill-down | Not opened in the session beyond dashboard-level metrics (1,924 sent, 2 opps, paused) | Derived (gap by omission) |
| Mailbox count: 11 vs 12 discrepancy | 12 distinct rows visible across the two Email Accounts screenshots; user-stated authoritative count is 11. Most likely explanation: `gurmej.pawar@mejimedia.co` (0% health) excluded from the user's count as effectively dead. Not resolved in session | Screenshot + Correction + Derived |
| Per-mailbox campaign attribution in Email Accounts view | View shows health but no per-campaign send mapping | Screenshot |
| Lead-source pipeline for any campaign | Not visible from Instantly UI; would need the previous contractor's lead-sourcing tool. Apollo/Lusha/scrape source unknown | Derived |
| Cross-domain rotation anomaly | Lee Robinson OOO came back to `gurmej.pawar@mejiai.com` despite a Banter-style subject "any fooling around lately, Lee?". Either Banter rotated through MejiAI mailboxes, or there's a separate uncategorized MejiAI campaign on a different angle. Not resolved | Screenshot + Derived |
| Corporate Events reply count discrepancy | Step Analytics: 11 (Step 1) + 9 (Step 2) = 20 replies. Dashboard counter shows 21. Off by 1, surfaced during the consistency pass on this inventory. Could be a Step 3 reply, a manual reply not counted at step level, or a counter lag. Unresolved | Screenshot + Derived |
| Stag pricing context (£250-£500/head) | I cited this as industry-standard during the analysis. This is external context I introduced, not from the Instantly data. `?` | ? Inserted by me without explicit data source |
| Instantly auto-pause bounce threshold ("typically ≥3% to 5%") | I cited this threshold value during analysis. The actual threshold is configurable per workspace and not visible in any screenshot. `?` | ? Inserted by me as general-industry context |
| Cold-outbound reply-rate benchmark (2 to 5%) | Cited during analysis as the typical range. External-industry context, not from the Instantly data. `?` | ? Inserted by me as general-industry context |
| "Universities and NHS reject cold outbound as policy" | Inferred from the bounce composition (Proofpoint clustering on bham.ac.uk) and reply composition (NHS Finance Admin polite-no). The "as policy" framing is interpretive; not directly verified per recipient | Derived (interpretive layer) |
| Microsoft 365 NHS warning attribution | Tom Sabin's reply showed a sender-identification warning. Attributing this specifically to Microsoft 365's external-sender mechanism is reasonable inference, not directly confirmed | Screenshot + Derived |
| "Hi Mel" anomaly | Simon Seal addressed his reply to Mel, not Gurmej. Two possibilities: previous Meji contact, or a previous sender persona changed to Gurmej. Unresolved in session | Screenshot + Derived |
| Whether NHS / public-sector recipients were intentional or scrape noise | Implied list-quality issue; no explicit confirmation from the user or contractor | Derived |

---

## 14. Deliverable iteration history

The client-facing deliverable (`workspace/clients/meji-media/deliverables/instantly-audit.pdf`) went through 5 versions in this session.

| Version | Trigger | Output state | Source |
|---|---|---|---|
| v1 | Initial request: "generate a pdf for the audit they asked for" | ~10 sections, ~3,500 words, 6 pages, decision-support framed | Screenshot (file write) |
| v2 | User: "do it structured, with a plan and everything" + "keep the content compact" + output validator caught 9 em-dash-substitute hits | Plan/TOC added upfront, em-dash substitutes replaced with commas/colons, trimmed to roughly 2,000 words, 5 pages | Correction + Screenshot (hook output) |
| v3 | User: "i need it to sound more human and be formated more like the content on our website" | Voice rewritten anchored on `unpauseai.com/docs/meji-media/scaling` style. PDF generator palette updated to slate body + blue accents, blockquote rendered as callout card. 6 pages | Correction |
| v4 | User: "still too much text. I need quick statements, founded in facts" | Compressed to 3 pages. Headlines section added; tables-only otherwise. Verbatim quotes preserved | Correction |
| v5 (final) | User: "Leave the unworked leads in the mailbox out. also your language needs to be more human" | Live pipeline section removed entirely. Section intros and bullets rewritten in conversational prose. 3 pages | Correction |

Final files:

| File | Path | Source |
|---|---|---|
| Markdown source | `workspace/clients/meji-media/deliverables/instantly-audit.md` | Screenshot (file write) |
| PDF output | `workspace/clients/meji-media/deliverables/instantly-audit.pdf` | Screenshot (file write) |

---

## 15. Tool development: `tools/md-to-pdf.py`

Built this session to convert the audit markdown to PDF, after hitting three friction points en route.

### 15a. Tool description

| Field | Value | Source |
|---|---|---|
| Path | `tools/md-to-pdf.py` | Screenshot (file write) |
| Purpose | Convert markdown deliverables to print-styled A4 PDF. Auto-detects Unicode TTF. Renders headings, paragraphs, lists, tables, code, hr, blockquote as callout card | Screenshot |
| Dependencies (final) | `fpdf2>=2.7,<3`, `markdown-it-py>=3.0` | Screenshot |
| Registered in | `tools/INDEX.md` one-liner row | Screenshot (file write) |
| Style palette | Slate body (#0f172a), blue-600 accent (#2563eb), slate-100 code background, blue-50 callout tint. Matches `docs.unpauseai.com` | Screenshot |

### 15b. Friction events during the build

| Friction | Resolution | Source |
|---|---|---|
| `xhtml2pdf>=0.2.17` pulls `python-bidi>=0.6` which needs a Rust toolchain to compile on Windows; `maturin pep517 build-wheel` failed under `uv` | Pinned attempted to `xhtml2pdf<0.2.14` | Screenshot (build error) |
| Pinned `xhtml2pdf 0.2.13` triggered an API incompatibility with reportlab 4.x (`ShowBoundaryValue` import missing) | Switched toolchain entirely to `fpdf2` | Screenshot (import error) |
| Built-in Helvetica in fpdf2 is Latin-1 only; crashed on `•` bullet (U+2022) | Added Unicode TTF auto-detection (Arial on Windows, DejaVu on Linux, Arial on macOS) with graceful fall-back to built-in | Screenshot (FPDFUnicodeEncodingException) |
| `self.font_family` attribute on my AuditPDF subclass collided with FPDF parent attribute; `set_font("Arial", ...)` silently fell through to Courier | Renamed instance attribute to `self.body_family`; minimal repro test confirmed this was the issue | Screenshot + Derived |

---

## 16. Open questions in the final client deliverable

| Question | Source |
|---|---|
| Is Banter in scope? Revive actively, run quietly, or park? | Screenshot (deliverable content) |
| Is MejiAI in scope? Rebuild, park, or sunset? | Screenshot |
| DNS access on Meji-owned domains so reputation can be verified properly via Postmaster? | Screenshot |
| Consolidate outbound onto `mejimedia.co` long-term, or keep the multi-brand split? | Screenshot |

---

*Session inventory · Instantly audit · Meji Media · 2026-05-10*
