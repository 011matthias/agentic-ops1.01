# Cover Letter: Instantly Deliverability + AI-Native Data Operations (p032)

Matthias here. I've run Instantly for a UK events company since May. In July its NeverBounce-valid list bounced 8.6%; 10 of 11 bounces sat behind Mimecast. With an MX check at load, November's 184 first emails bounced zero.

Two files attached: a two-page case study with the numbers behind the examples below, and a two-page plan for your pilot (the week-one audit, the research pipeline for the four weekly ICP lists, the weekly report).

1) Deliverability and campaign management
- When I took over that account, two of its five campaigns were auto-paused for bounces, and the three mailboxes on its Christmas campaign sat on a domain that didn't exist in DNS, so Instantly had pulled them from its warmup pool. Sending now runs on warmed Google Workspace mailboxes, one domain per stream; the 773-person Christmas re-engagement bounced 0.6%.
- Verifiers fail in both directions. On the past-customer list NeverBounce marked 42% "unknown", yet all 335 of those we could check had already received our campaigns, and 47 had replied: Hotmail, iCloud and NHS servers refusing the probe. Dropping them would have cut 41% of the wave for nothing.
- Microsoft 365: for a treasury-software company I audited 53 purchased sending domains through the registrar's API. None had MX records or mailboxes and only 3 had SPF and DKIM, so the conference follow-up ran from an established M365 mailbox instead. It stands at 127 people reached, 40 in conversation and 20 meetings booked.

2) AI-native data operations
- On the events client Apollo supplied the contacts; the cuts and checks on top were mine: London headcount bands, industry cuts, a 1,183-domain past-customer exclusion, verification, the MX check, dedupe across the workspace.
- In a receipt pipeline I built for a finance team, Gemini reads every receipt, the model proposes the matching charge and category, and a person confirms before anything reaches the books. Measuring the model against the bookkeeper's own postings decided which parts it could own.
- For your four ICPs a week I'd build the research in n8n: each company's site and search results go to Claude or GPT with your brief, and the model returns JSON with a fit score, the reasons, and a source URL for every claim. No source, or a score under the line, and the company goes to a review tab instead of the list. Before a list loads I hand-check 20 rows against the sources.

3) How I'd start
Week 1: audit every sending domain (SPF, DKIM, DMARC, MX) and every mailbox (warmup, limits, bounces and replies per sender), run seed-inbox placement on Gmail, Outlook and Microsoft 365 business, and send a findings list with the fixes in order. The research workflow gets built on your first ICP briefs, so week one's campaigns ship on it. Weeks 2 to 4 run four lists a week through it, each launched after a read-only check against the Instantly API: senders, limits, the delay on every step, merge fields, dedupe against every live campaign. The weekly report counts human replies apart from automatic ones: in the November wave all 12 replies were out-of-office notices.

The $800 pilot and the weekly milestones work for me as posted. I work within UnpauseAI, an EU-based automation consultancy, and do this work myself. I'm in Karlsruhe, Germany, nine hours ahead of Los Angeles, so lists and checks are ready by your morning.

How many sending domains and mailboxes are in the account today, and how are they split between Google Workspace and Microsoft 365?

Matthias
