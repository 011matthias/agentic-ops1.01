---
description: Generate a system digest (overview, changelog, or client report) and deliver via terminal, file, or email. Use for system awareness, client updates, or progress reports.
argument-hint: [--overview|--changes|--client NAME] [--since DATE] [--client-facing] [--email ADDRESS] [--file] [--html]
---

# System Digest

Generate a structured digest of the Agentic Ops system and deliver it.

## Process

1. **Parse arguments:**
   - Mode: `--overview` (default), `--changes`, or `--client NAME`
   - Template: `--client-facing` for non-technical audience (default: internal/technical)
   - Delivery: `--email ADDRESS`, `--file`, `--html` (default: print to terminal)
   - Date filter: `--since YYYY-MM-DD` (for `--changes` mode, default: 7 days ago)

2. **Load the `system-digest` skill** — it contains the scan logic and templates.

3. **Execute the skill's scan + generate flow:**
   - Scan live system state (rules, skills, agents, commands, client status)
   - Apply the appropriate template (internal or client-facing)
   - Render output (markdown or HTML)

4. **Deliver:**
   - Terminal (default): print markdown output
   - `--file`: save to `docs/digests/YYYY-MM-DD-{mode}.md`
   - `--html`: save styled HTML to `docs/digests/YYYY-MM-DD-{mode}.html`
   - `--email ADDRESS`: run `uv run scripts/send-digest-email.py` to send via Resend API

## Examples

```bash
# Full system overview (internal, terminal)
/system-digest --overview

# What changed this week (internal, terminal)
/system-digest --changes

# What changed since a specific date
/system-digest --changes --since 2026-02-25

# Client report for Meji Media (client-facing, emailed)
/system-digest --client meji-media --client-facing --email client@example.com

# System overview saved as HTML file
/system-digest --overview --html

# Client report saved to file
/system-digest --client herbox-sweden --file
```

## Output

- Terminal: markdown printed directly
- File: `docs/digests/YYYY-MM-DD-{mode}.md` or `.html`
- Email: sent via Resend API (requires `RESEND_API_KEY` env var)
