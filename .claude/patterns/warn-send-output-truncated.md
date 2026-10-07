---
name: warn-send-output-truncated
enabled: true
event: bash
action: warn
message: Irreversibler Send durch tail/head gefiltert: die SMTP-Bestaetigung ist der einzige Beleg. Ungefiltert lesen, oder den Sendebeleg zuletzt drucken.
source: 2026-09-24 verification-theater
created: 2026-09-24
pattern: '(?i)\b(?!test_)\w*(send(?!er)|smtp|publish)\w*\.py\b[^|]*\|\s*(tail|head)\b'
---
Explain what went wrong, when, and what to do instead.
