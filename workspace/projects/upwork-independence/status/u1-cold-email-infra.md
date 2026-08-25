---
project: upwork-independence
workstream: u1-cold-email-infra
group: uwi
spec:
state: active
updated: 2026-07-28
general_ref: status/uwi-general.md
---

# uwi / u1 - Cold-email sending infrastructure

Stand up UnpauseAI-owned sending infrastructure for the volume-engine channel
(0.378 of acquisition effort, UK/US only per UWG §7). UnpauseAI owns the full
knowledge/safety layer (cold-email skill, Mimecast MX pre-filter + Instantly
delay-semantics memories, B5 invasive gate) and ZERO sending infrastructure:
every working account (Instantly, Apollo, domains, mailboxes) is Meji/Brisken
client property, off-limits. 2026-07-28: purchase execution attempted; the
blocker is not vault access (reads work) but that the vault holds only CLIENT
accounts. Owner chose (2026-07-28) to provision UnpauseAI-owned accounts; all
purchase decisions are now closed and the owner-provisioning steps are written.

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| Purchase/provisioning checklist | done | Refreshed 2026-07-28: 3 open decisions closed (provider, verification, Apollo), account-ownership finding added, owner-provisioning steps (§12) + GWS-exact DNS runbook (§7) written | Owner runs §12 provisioning | none | `../context/cold-email-purchase-checklist.md` |
| Sending domains (3) | blocked | Approved 2026-07-22; RDAP re-checked 2026-07-28 (all available); Porkbun API can register but needs an UnpauseAI-owned, funded account | I register by API once `porkbun-unpauseai` exists + funded | owner provisioning (§12.1) | checklist §1-2 |
| Mailboxes + warm-up | blocked | Provider CLOSED 2026-07-28: Google Workspace, new SEPARATE tenant, not Zoho (Zoho bans cold + hosts the clean root's mail). Sender = Matthias Neumann | I add domains + create 6 mailboxes once GWS tenant exists | owner provisioning (§12.2) | checklist §3, §7 |
| Instantly workspace | blocked | Approved Growth ($47/mo); no UnpauseAI Instantly account exists (only client's) | I connect mailboxes + enable warm-up once `instantly-unpauseai` exists | owner provisioning (§12.3) | checklist §4 |
| Apollo account | decided, needs paid seat | Free tier RULED OUT 2026-07-28 (25-record export cap gutted late-2025); needs Basic ($49/mo annual, or 1 monthly seat) on an UnpauseAI account | Owner provisions Basic; I build the list | owner provisioning (§12.4) | checklist §5 |
| Verification | decided | MillionVerifier chosen 2026-07-28 (~$37/10k vs NeverBounce ~$80/10k); MX pre-filter runs first | Buy 10k pack at list-volume time | owner provisioning (§12.5) | checklist §6 |
| List filter + sequences | done | Apollo filter spec (UK+US, owner/MD, 5-50, Make/n8n/Zapier/GHL tech, DE excluded) + 4-touch sequence v1 drafts written; delay-on-earlier-step cadence encoded | Refine copy vs u5/u2; swap Step-3 metric for a verified case | none (draft) | `../context/u1-list-and-sequences.md` |
| First campaign build | not-started | Send is B5-gated (scope-of-effects + readiness audit); needs warm-up complete + verified list + approved copy | — | warm-up not started | `rule_instantly_invasive` |

## Open decisions / gates

- CLOSED 2026-07-28: mailbox provider (GWS separate tenant), verification
  (MillionVerifier), Apollo (paid Basic), sender name (Matthias Neumann),
  account ownership (all UnpauseAI-owned, never client accounts).
- PURCHASE GATE stands: each line needs its own owner yes; Apollo Basic +
  MillionVerifier still need an explicit approve.
- BLOCKER (owner action): provision the 5 UnpauseAI-owned accounts per
  checklist §12 (card + signup + phone/2FA the agent cannot do). Fastest
  clock-start = §12.1-3 (domains + mailboxes + Instantly).
- First real send: B5-gated, separate decision; warm-up completion does not
  authorize it.

## Pointers

- Purchase + provisioning runbook: `../context/cold-email-purchase-checklist.md`
- List filter + sequence drafts: `../context/u1-list-and-sequences.md`
- Deliverability knowledge: memories `reference_cold_email_gateway_bounces`
  (Mimecast MX pre-filter), `reference_instantly_sequence_delay_semantics`
  (gap on the EARLIER step), warm-up 3-4 wk (`project_brisken_outreach_domains`).
- Delivery pipeline shape: `u5-delivery-kit.md` (meji p1-p3 extraction).
- Model economics: leadgen-portfolio scorer; real fixed stack now ~3x the
  EUR 40/mo assumption (Apollo + Instantly added); re-pin when live.
