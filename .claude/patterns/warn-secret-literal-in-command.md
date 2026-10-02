---
name: warn-secret-literal-in-command
enabled: true
event: bash
action: warn
message: A literal API key, or a key carried in a URL (?key=), is in this command. The command lands in the transcript, and an error page can echo the URL into a saved file (2026-09-27: a Google 404 page wrote the Gemini key into %TEMP%/vx.json). Read the key from the gitignored .env into a variable and send it in a header (x-goog-api-key / Authorization) or on stdin.
source: 2026-09-28 skipped-gate (Gemini key inlined in a printf and sent as ?key= in curl URLs)
created: 2026-09-29
pattern: '(?:AIza[0-9A-Za-z_\-]{30,}|\bAQ\.[0-9A-Za-z_\-]{30,}|\bsk-(?:proj-)?[0-9A-Za-z_\-]{20,}|[?&]key=(?:\$|[^&\s"'']{8,}))'
---
Explain what went wrong, when, and what to do instead.
