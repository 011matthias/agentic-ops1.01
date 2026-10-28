---
name: warn-hand-prompt-as-text
enabled: true
event: stop
action: warn
message: Naming a Lovable prompt file is not handing it over. Paste the prompt body into the reply inside a FOUR-backtick fence and say which tool it goes into (MEMORY.md feedback_prompts_are_pasteable_text + feedback_label_prompt_target). A path makes the user go fetch it.
source: 2026-09-24 missed-memory-recall
created: 2026-09-24
conditions:
  - field: final_text
    operator: regex_match
    pattern: '(?i)lovable-[a-z0-9-]+-prompt\.md'
  - field: final_text_raw
    operator: not_regex_match
    pattern: '`{4}'
---
Explain what went wrong, when, and what to do instead.

Fires only when a prompt file is named AND the reply carries no four-backtick
fence. Naming the file next to the pasted body is exactly what the sibling rule
`warn-owner-publish-without-named-prompt` asks for, so the file-name-only
version made the two rules contradict each other on a correct reply
(2026-10-05, three pasted Lovable prompts with their file paths).
