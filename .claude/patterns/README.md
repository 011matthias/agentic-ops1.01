# Pattern rules

Declarative structural controls: one markdown file per rule, read at runtime by
`.claude/hooks/pattern-rules-gate.py`. Not auto-loaded into context (that is
why they live here and not under `.claude/rules/`).

Promote a regex-shaped lesson here instead of writing a new hook: it is the
"1b" rung of the self-annealing ladder in `rule_behaviors.md`.

```
uv run tools/pattern_rules.py new warn-foo --event bash --pattern '\bfoo\b' --message "..." --source "2026-09-17 slow-path"
uv run tools/pattern_rules.py lint          # CI runs this
uv run tools/pattern_rules.py list
uv run tools/pattern_rules.py test --event stop --text "8 queued edits will apply when the file unlocks"
```

Format reference: the docstring of `.claude/hooks/_pattern_rules.py`. Record the
promotion in the friction register as Fix `pattern-rule:<name>`.
