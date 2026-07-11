# Status

Per-workstream status-of-elements files for Brisken (tracked, NOT in the
gitignored `context/`). One file per discrete workstream; one
`p2-lead-gen-general.md` holding the lead-generation group's shared context (the
OnePilot vision, the marketing plan) so it is stated once rather than copied into
each workstream file.

Loaded by `/comd_resume`, updated at `/comd_checkpoint`. Convention:
`.claude/rules/rule_project_status.md` + `skil_project-status`.

Check / scaffold:

```bash
uv run tools/project_status.py --client brisken --check
uv run tools/project_status.py --client brisken --scaffold {slug} --group {group} --spec {id}
```

Cross-project active/paused index + swap history stays in
`../PROJECT-BOUNDARIES.md`; these files are the level of detail beneath it.
