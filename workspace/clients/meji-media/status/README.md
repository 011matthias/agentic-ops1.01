# Status

Per-workstream status-of-elements files for Meji Media (tracked, NOT in the
gitignored `context/`). One file per discrete workstream. Convention:
`.claude/rules/rule_project_status.md` + `skil_project-status`.

Public-repo rule: these files hold POINTERS and method state only. Campaign
IDs, mailboxes, metrics, contact names, and money figures stay in the
gitignored `context/`.

Loaded by `/comd_resume`, updated at `/comd_checkpoint`. Check / scaffold:

```bash
uv run tools/project_status.py --client meji-media --check
uv run tools/project_status.py --client meji-media --scaffold {slug}
```

Owed (not yet scaffolded): status files for the live campaign pieces and the
multi-inbox build; today only `ops-radar.md` exists (created 2026-07-20 with
the opportunity-radar method).
