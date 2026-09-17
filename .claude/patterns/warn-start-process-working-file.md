---
name: warn-start-process-working-file
enabled: true
event: bash
action: warn
message: Start-Process on a .md or .html file hands it to Word, which locks it or wrecks the page.
source: 2026-06-12 slow-path (was memory-only, feedback_open_files_directly)
created: 2026-09-17
pattern: '(?i)\bStart-Process\b(?![^;|\n]*\b(msedge|chrome|firefox|code)\b)[^;|\n]*\.(md|html?)\b'
---
On this machine Word owns both `.md` and `.html`. On 2026-06-12 a bare `Start-Process` on a working spec took an exclusive lock that blocked the agent's own edits for about 40 minutes, and the same day an HTML deck opened in Word as skeleton text.

- Markdown the user should see while you may still edit it: `code <file>` (no lock).
- HTML: `Start-Process msedge -ArgumentList "file:///c:/path/file.html"`.
