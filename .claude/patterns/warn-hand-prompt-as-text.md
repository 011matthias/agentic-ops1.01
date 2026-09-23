---
name: warn-hand-prompt-as-text
enabled: true
event: stop
action: warn
message: Naming a Lovable prompt file is not handing it over. Paste the prompt body into the reply inside a FOUR-backtick fence and say which tool it goes into (MEMORY.md feedback_prompts_are_pasteable_text + feedback_label_prompt_target). A path makes the user go fetch it.
source: 2026-09-24 missed-memory-recall
created: 2026-09-24
pattern: '(?i)docs/lovable-[a-z0-9-]+-prompt\.md|lovable-[a-z0-9-]+-prompt\.md'
---
Explain what went wrong, when, and what to do instead.
