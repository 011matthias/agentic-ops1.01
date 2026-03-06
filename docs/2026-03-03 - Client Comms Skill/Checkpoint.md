# Checkpoint: Client Comms Skill

**Date:** 2026-03-03
**Status:** Complete, ready for use

---

## Summary
Built a full `client-comms` skill and `/draft` command that drafts client messages using project context, configurable per-client tone profiles, and anti-AI style enforcement (no em-dashes, banned phrase list, mandatory contractions, deliberate imperfections). Created Meji Media as the first configured client profile.

---

## What Was Done This Session
### Planning & Design
1. Explored existing skill/command patterns and client context structure to inform architecture
2. Designed skill as Skill + Command combo per the meta-builder decision tree
3. Defined 11 message types, 7 hard style rules, configurable soft rules, and per-client profile schema
4. User chose: light imperfections by default, both auto-trigger and `/draft` command, added proposal and meeting-recap types

### Implementation
1. Created `client-comms` skill with SKILL.md entry point (6-step process)
2. Created STYLE-RULES.md with 7 hard rules, 27+ banned phrases, platform-specific formatting, post-draft validation checklist
3. Created MESSAGE-TYPES.md with 11 message types (status-update, info-request, blocker-notification, deliverable-handover, milestone, follow-up, technical-to-dev, scope-discussion, invoice-context, proposal, meeting-recap)
4. Created CONTEXT-LOADING.md with priority-ordered file loading per message type
5. Created SANITY-CHECK.md with 7 validation checks (claims vs state, names, technical accuracy, scope, blockers, leakage, tone)
6. Created profile setup prompt and comms-profile template
7. Created `/draft` command with argument parsing and examples
8. Created Meji Media comms-profile.md with all 3 contacts configured
9. Updated CLAUDE.md with new skill and command in registry

---

## Key Decisions Made
### Skill Architecture
- **Choice:** New standalone skill (not a module in an existing skill)
- **Rationale:** Client communication is genuinely distinct from automation building. Passes the "extend vs create" test — this knowledge isn't needed during Make.com building, spec creation, or testing.

### Invocation Pattern
- **Choice:** Both auto-trigger (on "draft a message", "write to client") AND explicit `/draft` command
- **Rationale:** User wants flexibility. Sometimes they'll say "draft a message to Gurmej" naturally in conversation, sometimes they'll use `/draft meji-media status-update` explicitly.

### Imperfection Density
- **Choice:** Light mode as default (1 subtle imperfection per message)
- **Rationale:** Enough to break AI patterns without looking sloppy. Configurable per-client.

### Per-Client Config Location
- **Choice:** `workspace/clients/{client}/context/comms-profile.md`
- **Rationale:** Follows existing workspace rule that client-specific knowledge stays in `context/`. YAML frontmatter for machine-readable config, markdown body for freeform notes.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/client-comms/SKILL.md` | Created | Entry point with 6-step process |
| `.claude/skills/client-comms/modules/STYLE-RULES.md` | Created | Anti-AI rules, banned phrases, validation checklist |
| `.claude/skills/client-comms/modules/MESSAGE-TYPES.md` | Created | 11 message type templates with structure and pitfalls |
| `.claude/skills/client-comms/modules/CONTEXT-LOADING.md` | Created | File loading priorities per message type |
| `.claude/skills/client-comms/modules/SANITY-CHECK.md` | Created | 7 accuracy validation checks |
| `.claude/skills/client-comms/prompts/client-profile-setup.md` | Created | Questions for new client profile setup |
| `.claude/skills/client-comms/templates/comms-profile-template.md` | Created | Template for comms-profile.md |
| `.claude/commands/draft.md` | Created | `/draft` command entry point |
| `workspace/clients/meji-media/context/comms-profile.md` | Created | Meji Media profile (3 contacts, Upwork, casual, light imperfections) |
| `CLAUDE.md` | Modified | Added client-comms to Skills, `/draft` to Commands |

---

## Current Status
- Skill is fully built and registered in CLAUDE.md
- Meji Media is the first client with a comms profile
- Auto-discovery is working (skill appears in the skill list)
- No other clients have comms profiles yet (will be created on first `/draft` use per client)

---

## Next Steps
1. **Test with a real draft** — run `/draft meji-media status-update` to validate the full flow
2. **Create comms profiles for other clients** as needed (Herbox, Peakora, Kunde Inc, Uplifted)
3. **Iterate on banned phrases** — add new patterns as they're noticed in drafts
4. **Consider adding a "message history" feature** — track what was sent to each client for continuity across sessions

---

## Context for Next Session
### Files to Read First
- `.claude/skills/client-comms/SKILL.md` — the skill entry point
- `.claude/skills/client-comms/modules/STYLE-RULES.md` — the style enforcement rules
- `workspace/clients/meji-media/context/comms-profile.md` — the first configured profile

### Open Questions
- Should message history be tracked? (e.g., a `context/comms-log.md` per client that records what was sent and when)
- Should the profile setup be triggered automatically by `/new-client`?

### Reference Materials
- Plan file: `.claude/plans/parsed-soaring-lynx.md`
- Meta-builder decision tree: `.claude/skills/meta-builder/modules/DECISION-TREE.md`

---

## How to Continue
1. Just say "draft a message to [client]" or use `/draft [client]` to test the skill
2. The skill auto-triggers when it detects message drafting intent
3. To add a new client profile, either run `/draft {client}` (will prompt for setup) or manually create `context/comms-profile.md`

---

## Strategic Feedback

### What Worked Well This Session
- The user identified a genuine workflow bottleneck (client messaging) and scoped it as a system improvement rather than a one-off task. This is exactly the self-annealing philosophy in action.

### Suggestions
- When you have a new client onboarding, consider running `/draft {client} proposal` early to force the comms profile creation. That way the profile exists before you need it mid-project.

### System Health
- The skills registry in CLAUDE.md now has a "Comms" category, which is a new domain beyond the automation-building core. This signals healthy expansion of the workspace's capabilities beyond just technical implementation. The per-client `comms-profile.md` pattern could eventually extend to track other relationship metadata (meeting notes, preferences, communication frequency).
