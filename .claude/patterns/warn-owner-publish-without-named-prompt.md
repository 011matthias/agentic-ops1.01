---
name: warn-owner-publish-without-named-prompt
enabled: true
event: stop
action: warn
message: You are handing the owner a Lovable publish/paste without naming the docs/lovable-*-prompt.md it comes from. Name the file; if none exists, writing it is yours, not the owner's (verify with a grep of docs/ and the live bundle first).
source: 2026-09-24 agent-deferred (Phase 1 SPA prompt never written; four checkpoints said the deploy waits on the owner publishing it)
created: 2026-09-24
conditions:
  - field: final_text
    operator: regex_match
    pattern: '(?is)\b(publish|paste)\w*\b[^.\n]{0,80}\b(lovable|bundle|screen update|SPA)\b'
  - field: final_text_raw
    operator: not_regex_match
    pattern: '(?i)lovable-[a-z0-9-]+-prompt\.md'
---
Explain what went wrong, when, and what to do instead.
