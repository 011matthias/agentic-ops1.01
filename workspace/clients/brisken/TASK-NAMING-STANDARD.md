# Brisken Task Naming Standard (client-specific)

**Binding for this client.** Every task entry created on Brisken's Microsoft
Planner (plan **MARKETING PLAN**, `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, bucket
**Lead Generation**, `gyfptEwAwUiJLXfd6aMrYWUABZRr`) abides by the naming
system below. The title alone must tell the reader **who** the task touches,
**which channel**, and **what motion**; the description then says **where the
copy / assets / lead filter live**, so a task can be picked up and executed
without hunting. Access + tooling: memory `reference_brisken_microsoft_planner`
(token capture via CDP Edge, `planner.py` create/retitle/assign/discover).

Reason for this rule: on 2026-07-09 two near-duplicate titles ("Send Rome
booth follow-up outreach" vs "Send Rome booth network follow-up outreach")
plus tier tags that conflicted with the segmentation doc caused exactly the
confusion this standard exists to remove.

## 1. Two title families

Classify the task first, then pick the grammar.

- **Campaign / sequence task** — outreach to a defined CONTACT SEGMENT within
  a named campaign (Rome, and any future event/campaign). Use the structured
  grammar in §2.
- **Standalone task** — one discrete piece of work (a deck, a website, a
  listing, a decision). Use imperative `action + specific object` (§4).

## 2. Campaign grammar (rigid)

```
{Campaign} {tier} {segment}: {channel} {motion}
```

- **{Campaign}**: short proper name. Currently only `Rome`.
- **{tier}**: one of `H5`, `T1`, `T2`, `T3`, canonical per §3. Always present.
  Never `Tier 1 hottest-5`: H5 is not a subdivision of T1, they are disjoint
  groups of people.
- **{segment}**: the slug from §3 (`hottest-five`, `booth follow-up`,
  `warm-engaged`, `cold leads`). Mandatory even though the tier implies it;
  the slug is the belt-and-suspenders against tier drift.
- **{channel}**: exactly one of `email`, `LinkedIn + Sales Nav`, `CRM`, `web`.
  Never blend channels in one task.
- **{motion}**: `outreach`, `email outreach (Dirk sends)`, `email follow-ups`,
  `consent email`, `list-build`, and so on.

**One task = one tier x one channel.** Split, never blend. Every tier runs both
email and LinkedIn, so every tier is at least two tasks.

Current Rome set (the reference implementation), eight outreach tasks:

| Tier | email | LinkedIn |
|---|---|---|
| H5 hottest-five | `Rome H5 hottest-five: email outreach (Dirk sends)` | `Rome H5 hottest-five: LinkedIn + Sales Nav` |
| T1 booth follow-up | `Rome T1 booth follow-up: email outreach` (DONE 2026-07-08) | `Rome T1 booth follow-up: LinkedIn + Sales Nav` |
| T2 warm-engaged | `Rome T2 warm-engaged: email outreach` | `Rome T2 warm-engaged: LinkedIn + Sales Nav` |
| T3 cold leads | `Rome T3 cold leads: email outreach` | `Rome T3 cold leads: LinkedIn + Sales Nav` |

Plus one legal touch that belongs to no tier:
`Rome booth/token-network: GDPR consent email`. It is the only task allowed to
say "booth/token-network", because that group cuts across H5, T1, T2 and T3.

Rome infrastructure tasks (not outreach) stay as standalone titles: update the
SharePoint contact list, upload contacts to the CRM after all tiers are
contacted, deploy the post-event asset hub.

## 3. Rome tier canon (title slug to executable segment)

The authority is the `Tier` column of the master sheet
(`context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx`).
It is a computed, mutually exclusive partition over every row; the build script
and its rules live in `output/leadgen-task-4/` on branch `leadgen/task-4`.
Never re-derive a tier from `fob_encoded` or a company-name match.

| Tier | segment slug | Who (`Tier` column) | N | Copy / assets |
|---|---|---|---|---|
| H5 | `hottest-five` | The 11 To:/Cc: addresses of the six notes in the Dirk send pack. VW, JTI, Roche, Adidas, LSEG. Dirk sends each personally. | 11 | `deliverables/lead-generation/rome-2026/dirk-send-pack/` |
| T1 | `booth follow-up` | The 19 emailed from Dirk's Outlook on 2026-07-08 (`post_event_outreach`). | 19 | `context/drafts/rome-booth-network-touch.md` |
| T2 | `warm-engaged` | Carries a real personal note from Dirk, reachable. 13 of the 23 are partners / SIs and 4 are SAP staff; filter `lead_type = prospect` for the 8 buyers. | 23 | master sheet; three spines (MDH / AI-OnePilot / connectivity) |
| T3 | `cold leads` | Reachable, no personal note. `t3_branch` selects the copy: `attended` (29) or `no_show` (1). | 30 | `post-event-sequences.md` |

**H5 and T1 are disjoint**, asserted by the build. H5 is "Dirk writes these
himself"; T1 is "already sent from Dirk's Outlook".

Non-tier rows carry an explicit label in the same column and are never
sequenced: `ANON` (89, TA Cook withheld the PII, not contactable), `STOP` (69),
`GA` (40, Dirk's hold), `OWN_TEAM` (4), `UNREACHABLE` (1), `DEFERRED` (1),
`ORGANISER` (1), `DUPLICATE` (1), `TEST` (1).

The `booth_network_send` column (74 rows) drives the GDPR consent email. It is
orthogonal to the tier: an H5, T1, T2 or T3 person can also be on it.

Sales Nav list for all tiers: `TA Cook Rome 26`.

## 4. Standalone grammar

```
{action verb} {specific object}
```

Imperative, sentence case, specific object, no filler. Examples already on the
board: `Publish the AEO answer-engine Q&A site and research report`,
`Build the non-Rome Sales Navigator lists and saved searches`,
`Support the live Accenture (Ashok) MDH referral`. An optional leading area
tag is allowed when it aids scanning: `OnePilot`, `AEO`, `SalesNav`, `SAP`,
`Product`, `CRM`, `Web`, `Partner`.

## 5. Hard rules (every task)

- **Front-load the identifier.** Campaign: `Campaign Tier N segment` comes
  first. Standalone: the verb + object come first.
- **Length.** Title <= ~90 chars. Checklist item titles <= 100 chars (Planner
  hard limit; over-length makes the whole details PATCH 400 and silently drops
  the description).
- **No em-dash** (`—`, `&mdash;`, ` -- `). Use `:`, `+`, `/`, or plain words.
- **One Tier × one channel per task.** Split, do not blend.
- **Description is executable.** Every outreach task's description names the
  contact segment (the master-sheet filter) and where the copy / assets live.
- **Assignment.** Lead Generation tasks auto-assign to **Matthias Silva
  (Brisken)**, AAD id `8890599f-99a2-4a5a-9a73-4d9f867b751d`.

## 6. When adding or editing tasks

1. Pull live board first (`planner.py discover`) and diff titles against what
   was created; Dirk may have renamed tasks. Preserve his tier NUMBERS; only
   correct wording that fights the canon in §3.
2. Name per §2 / §4; assign per §5.
3. If a title cannot be made unambiguous inside the grammar, the segmentation
   is unclear, not the title. Fix the segmentation (or ask), then name.
