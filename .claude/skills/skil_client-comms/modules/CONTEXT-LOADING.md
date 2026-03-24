# Context Loading

Which files to read and what to extract, organized by priority.

## Always Load (Every Message)

### 1. `workspace/clients/{client}/context/comms-profile.md`

Extract:
- `platform` — determines formatting rules
- `contacts` — names, roles, tone, technical level
- `style_overrides` — formality, sign-off, first person, max length, imperfection density

If this file doesn't exist, run the profile setup flow before drafting.

### 2. Latest Checkpoint

Find the most recent checkpoint for this client:
```
docs/*{client}*/Checkpoint.md
```
Sort by date prefix in folder name. Read the most recent.

Extract:
- **Current Status** section — what's done, what's in progress
- **Next Steps** section — what's planned
- **Open Questions** section — unresolved items
- **Blockers** — what's waiting on the client

### 3. Comms Log (`workspace/clients/{client}/context/comms-log.md`)

If it exists, extract:
- **Last 3-5 entries** — recent conversation thread for continuity
- **All unresolved open items** — items from `Open items:` fields not resolved by later entries
- **Recent decisions** (last 2 weeks) — for reference in messages
- **Last contact date + direction** — who spoke last and when

This feeds into:
- **Conversation continuity:** Reference what was said before. Don't repeat questions already answered.
- **Temporal opener rules:** Time since last contact determines greeting style (see STYLE-RULES.md).
- **Open item awareness:** Know what's still pending when drafting.

If no comms-log exists, proceed without it. Offer to create one after the draft is approved.

### 4. Temporal Context

Note the current date/time and calculate:
- **Time since last contact** (from comms-log `last_contact` or checkpoint date):
  - Same day → no greeting, jump straight in
  - Next morning → "Good morning" / "Morning"
  - 2-3 days → brief context re-establishment
  - Week+ → warmer re-establishment
- **Who spoke last** — are we replying to them, or initiating?
- **Day of week / time of day** — affects opener tone (Monday morning vs Friday afternoon)

## Load by Message Type

### Status Updates, Blocker Notifications

Also read:
- **All spec files** in `workspace/clients/{client}/specs/` (all stage folders). Extract frontmatter only: `id`, `name`, `stage`, `needs_fixes`, `next_steps`.
- **`infrastructure.yaml`** — extract `ship: true/false` flags, scenario status (active/inactive), connection notes.

### Info Requests

Also read:
- **`context/process-notes.md`** — extract key contacts, who owns what, current blockers.

### Deliverable Handover

Also read:
- **`docs/client/overview.md`** — the client-facing narrative. Can be referenced or quoted.
- **`handover/README.md`** — what's included, prerequisites, setup steps.
- **`infrastructure.yaml`** — `ship: true` items only. These are what the client receives.

### Technical-to-Dev

Also read:
- **`context/infrastructure-ids.md`** — scenario IDs, webhook URLs, connection IDs, data store IDs.
- **Relevant spec file** — the specific automation being discussed. Full content, not just frontmatter.

### Scope Discussion, Proposal

Also read:
- **`context/process-notes.md`** — contract type, rate, original brief, architecture decisions.
- **All spec frontmatter** — to understand existing scope.

### Invoice Context

Also read:
- **Multiple checkpoints** from the billing period — scan `docs/` for all checkpoints within the date range.
- **Spec frontmatter** — stage changes indicate shipped work.

### Meeting Recap

Also read:
- **`context/process-notes.md`** — for existing decisions and architecture context.
- **Latest checkpoint** — for pre-meeting state (to diff against post-meeting).

### Follow-Up

Minimal context. Just:
- **comms-profile.md** — tone and contact info
- **The original message context** — what was asked and when

---

## Extraction Principles

1. **Don't dump raw content.** Extract specific facts relevant to the message.
2. **Prefer frontmatter over full content** for specs unless discussing a specific automation.
3. **Always check the `ship: false` flag** — never mention ship:false items to clients.
4. **Latest checkpoint is the single best source** for "where are things right now."
5. **Process notes are the single best source** for "who is this person and what do they care about."
