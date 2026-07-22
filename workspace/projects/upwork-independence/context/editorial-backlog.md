# Editorial backlog (u2)

The corpus piece list, derived 2026-07-22 from `icp.md`'s demand
taxonomy. Titles are phrased in the buyer's problem language, never our
solution language (icp §channel-filter-derivation). Shapes follow the
ai-seo skill's citation data: comparison pieces are the most-cited AI
answer shape, then definitive guides, how-tos, and FAQ-shaped pages;
every piece leads with a direct answer and keeps key passages
extractable.

**Ranking** = buyer intent x pool relevance. Intent: how close the query
sits to hiring someone (a person searching "make.com contractor left" is
days from a purchase; "what is an LLM" is not). Pool relevance: corpus
frequency of the demand bucket (T1 cold-outreach ~17/33 asks > T2 AI-ops
> T3 rescue > T4 compliance) adjusted for one structural fact: content
is a DE-legal channel (UWG §7 fences cold email, not publishing), so T4
DACH pieces carry more weight than their corpus frequency suggests.

**Sourcing rules (hard):** the 5 live local prototypes are the only
citable proof assets. No client names, no client numbers, no invented
statistics. Practitioner guidance is phrased as method, not measurement
(B4). Zero em-dashes; `validate-platform-content.py` gates every piece.

Buckets: T1 cold-outreach/lead-gen, T2 AI-in-the-loop ops, T3 back-office
rescue, T4 compliance/DACH, R1 local-proof (Route 1, fill-only).

## Priority 1 (write first)

| # | Working title (buyer language) | Bucket | Shape | Query cluster | Intent | Pool | Status |
|---|---|---|---|---|---|---|---|
| 1 | Your Make.com contractor left: taking over an automation you did not build | T3 | How-to + checklist | make.com contractor left, take over automation | H | H | Drafted (first-posts PR) |
| 2 | Cold email getting no replies: find the real problem before sending more | T1 | Diagnostic guide + table | cold email no replies, low reply rate | H | H | Drafted (first-posts PR) |
| 3 | SPF, DKIM, DMARC for cold email: the minimum that actually passes | T1 | Technical how-to + table | spf dkim dmarc cold email setup | H | H | Drafted (first-posts PR) |
| 4 | Zapier vs Make vs n8n for a small business: an operator's decision table | T3 | Comparison | zapier vs make vs n8n | H | H | Backlog |
| 5 | How long does cold-email warm-up really take (and what skipping it costs) | T1 | FAQ + guide | email warmup how long | H | H | Backlog |
| 6 | Leads dropping between your ad form and your CRM: where handoffs silently fail | T1 | Guide | facebook lead ads not reaching crm | H | M-H | Backlog |
| 7 | Reconciliation takes days: what to automate first (and what to leave manual) | T3 | Guide | automate bank reconciliation | H | M-H | Backlog |
| 8 | How many sending domains do you need for cold outreach? | T1 | FAQ | how many domains cold email | H | M | Backlog |

## Priority 2

| # | Working title | Bucket | Shape | Query cluster | Intent | Pool | Status |
|---|---|---|---|---|---|---|---|
| 9 | Email verification is not enough: why verified lists still bounce | T1 | Explainer | verified emails still bouncing | M-H | H | Backlog |
| 10 | Speed-to-lead: automating the first five minutes after a form fill | T1 | How-to | speed to lead automation | H | M | Backlog |
| 11 | Reply handling: the half of cold outreach nobody automates | T1 | Guide | cold email reply handling | M | H | Backlog |
| 12 | Why your ESP says delivered and your prospect never saw it | T1 | Explainer | email delivered but not received | M | H | Backlog |
| 13 | Auditing an inherited n8n instance: a working checklist | T3 | Checklist | n8n audit inherited workflows | H | M | Backlog |
| 14 | Moving off Zapier without breaking everything: a migration order that works | T3 | How-to | zapier migration to make n8n | H | M | Backlog |
| 15 | CRM to accounting sync: why it breaks and how to stabilize it | T3 | Guide | crm accounting sync breaking | M | M-H | Backlog |
| 16 | Google Sheets as your data plane: when it works, when it becomes a liability | T3 | Analysis | google sheets automation limits | M | H | Backlog |
| 17 | Webhook failures: the silent killer of no-code automations | T3 | Explainer | webhook failing silently | M | M | Backlog |
| 18 | AI support triage with confidence gating: when the bot must hand off | T2 | Guide | ai support triage human handoff | M-H | M-H | Backlog |
| 19 | Human-approval gates: adding AI to workflows that cannot afford mistakes | T2 | Guide | ai automation human approval | M | M-H | Backlog |
| 20 | When an LLM call beats a rules engine (and when it does not) | T2 | Comparison | llm vs rules classification | M | M | Backlog |
| 21 | AI personalization in outreach: the line between relevant and spam-shaped | T2 | Analysis | ai personalization cold email | M | M | Backlog |
| 22 | Adding AI steps to Make.com scenarios: patterns that survive production | T2 | How-to | make.com openai module patterns | M | M | Backlog |
| 23 | Cost control for LLM-powered automations | T2 | Guide | llm api cost control automation | M | M | Backlog |
| 24 | Cold email to Germany: what UWG §7 actually allows in B2B | T4 | Explainer | cold email germany legal uwg | H | M (DACH: H) | Backlog |
| 25 | GDPR-aware automation design: data minimization in Make and n8n | T4 | Guide | gdpr automation make n8n | M | M | Backlog |
| 26 | Where your automation data lives: EU hosting options for n8n, Make, and AI APIs | T4 | Comparison | eu data residency automation tools | M | M | Backlog |
| 27 | Self-hosting n8n for data residency: what it takes to run it properly | T4 | Guide | self host n8n production | M | M | Backlog |

## Priority 3

| # | Working title | Bucket | Shape | Query cluster | Intent | Pool | Status |
|---|---|---|---|---|---|---|---|
| 28 | Why most AI automations die at the demo stage | T2 | Analysis | ai automation production failure | M | M | Backlog |
| 29 | Signs your automation stack needs stabilization, not new features | T3 | Checklist | automation keeps breaking | M | M | Backlog |
| 30 | Done-for-you automation partner vs hiring in-house: the real trade-offs | T3 | Comparison | automation consultant vs hire | M | M | Backlog |
| 31 | What a local business website actually needs in 2026 | R1 | Checklist | local business website checklist | M | L-M | Backlog (prototypes citable) |
| 32 | Lighthouse 100 on a real business site: what it takes | R1 | How-to | lighthouse 100 real website | M | L | Backlog (prototypes citable) |
| 33 | DSGVO und Automatisierung im Mittelstand (German-language piece) | T4 | Guide | dsgvo automatisierung mittelstand | M-H | DACH: H | Backlog; language + entity decision is an owner call |

## Operating notes

- 33 pieces total; at the current weekly hours the honest cadence is 1-2
  pieces/week, so this backlog covers roughly the model's ~200h fixed
  corpus build. Re-rank as probe data arrives (monthly
  `ai_visibility_probe.py` run, u2 status element).
- Statuses move Backlog -> Drafted (in PR) -> Live. Kill or merge rows
  freely; the ranking is a working order, not a contract.
- Existing live posts (make-vs-n8n, when-to-automate, automation-handoff)
  are complements; #4 deliberately widens make-vs-n8n with Zapier and the
  SMB-owner frame rather than duplicating it.
- The tier menu (650/1850/6300) stays unpublished everywhere until u6's
  scope mapping exists (owner gate 2026-07-22); no backlog piece may
  reference those numbers.
