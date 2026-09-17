---
name: block-pre-conceding-comms
enabled: true
event: file
action: block
message: Pre-conceding phrase in a client draft or comms-log; hold the line instead of discounting against yourself.
source: 2026-05-19 strategic-gap (was memory-only, feedback_negotiation_posture)
created: 2026-09-17
conditions:
  - field: file_path
    operator: regex_match
    pattern: '(?i)(/context/drafts/|(^|/)comms-log\.md$)'
  - field: new_text
    operator: regex_match
    pattern: '(?i)\b(happy to lower|fair guardrail|you(''|’| a)re right to flag|thanks for being direct)\b'
---
rule_human_communication §2 bans pre-emptive concession inside a pushback context. On 2026-05-19 a draft answered a client's billing pushback with "a fair guardrail" and "happy to lower", and the owner had to escalate twice before the reply held its position.

Rewrite in Register B (polite-firm): restate the commitment or price, do not pre-discount it, and do not thank the client for the challenge.

If the phrase is the CLIENT's verbatim words being logged, not ours, add `<!-- pattern-allow:block-pre-conceding-comms (client quote) -->` next to it. The marker stays visible in the file, so every suppression is reviewable.
