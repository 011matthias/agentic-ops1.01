# Reference notes: Mizoreww/awesome-claude-code-config

Reference-only. Nothing from this repo is vendored into agentic-ops (owner
decision 2026-06-06: "reference only"). This file records what is worth
borrowing and what we already do better, so the next person does not re-evaluate
the whole repo.

Source: https://github.com/Mizoreww/awesome-claude-code-config (236 stars as of
2026-06-06). It is a "production-ready Claude Code config": multi-language
coding rules, 24 plugins across 9 marketplaces, a gradient statusline, and a
self-improvement loop that remembers corrections across sessions.

## What we already have that is equal or stronger

- **Self-improvement loop.** Their loop writes a flat `lessons.md`
  (date / context / mistake / rule). Ours is the three-layer self-annealing
  system in `rule_behaviors.md` plus `docs/friction-register.md` with typed
  events, gate attribution (B1-B6), and a regression check. Do not downgrade to
  a flat lessons file.
- **Adversarial review.** Their `adversarial-review` skill is a single worked
  example. We have `agnt_done-verifier`, `agnt_intent-reviewer`,
  `agnt_comms-critic`, plus the Workflow adversarial-verify pattern. Stronger.
- **Multi-language coding rules** (Python / TS / Go). We carry our own rules
  scoped to the actual stack. No need to import a generic set.

## Genuinely worth borrowing (candidates, not yet done)

1. **The `lessons.md` capture FORMAT as a fast-path.** Their one-liner
   (date / context / mistake / rule) is a lower-friction capture than a full
   friction-register row. Worth considering as the EOD-capture agent's quick
   intake before promotion into the register. Optional; the register is the
   system of record.
2. **Gradient statusline** (`hooks/statusline.sh`). Pure cosmetics. Only if the
   owner wants a richer status bar; not load-bearing.
3. **Two-level interactive install selector** (`install.ps1` / `install.sh`).
   Nice UX pattern for our own `tools/wire-hooks.py` if we ever ship a
   first-run setup, low priority.

## Verdict

No vendor. The one idea worth keeping in view is the lightweight lessons-capture
format for the EOD-capture agent. Everything else is already covered by our
rules, agents, and friction register. Revisit only if the owner wants the
statusline.
