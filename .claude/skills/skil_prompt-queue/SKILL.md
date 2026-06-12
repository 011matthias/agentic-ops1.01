---
name: prompt-queue
description: Queue prompts to run after the current task. Append prompts to .claude/queue/pending.md while a chat is busy; when invoked, the agent drains the queue FIFO (one prompt at a time), records each in done.md, then stops. Use for "queue this prompt", "add to the queue", "drain the queue", "run my queued prompts", "queue mode".
---

# Prompt Queue

Line up prompts while a chat is still working on something. You append prompts to a
plain-text file from your editor (or a second terminal) at any time; this skill drains
them in order once the current task is done, then stops. No polling, no background worker.

## Files

- `.claude/queue/pending.md` — the queue. Prompts waiting to run.
- `.claude/queue/done.md` — archive of processed prompts, with timestamps and one-line outcomes.

If `pending.md` does not exist, create it with the header block at the bottom of this file
before doing anything else.

## Queue file format

Prompts are separated by a line containing exactly `---`. Everything between separators is
one prompt. HTML comments (`<!-- ... -->`, including multi-line) are stripped before
splitting, so the header never counts as a prompt even though no `---` separates it from
the first prompt.

```text
<!-- header / instructions (ignored) -->

first queued prompt
---
second queued prompt, can span
multiple lines
---
third queued prompt
```

To add one: append your text as a new segment (put a `---` line before it if the file
already ends with prompt text). To bulk-add: paste several prompts separated by `---` lines.

## Mini interface (optional)

`uv run tools/prompt-queue-ui.py` serves a miniature queue UI on `http://127.0.0.1:7077`
(auto-opens the browser; `--no-open` to suppress, `--port N` to change). It lists pending
prompts and supports add, edit, reorder, delete, and clear, plus a read-only tail of
`done.md`. The file stays the source of truth: the page polls every 2 seconds, so agent
drains and hand-edits show up live, and every mutation is hash-guarded so the UI never
clobbers a drain that happened underneath it.

To embed in VS Code: start the server (terminal, or wire a local VS Code background
task running `uv run tools/prompt-queue-ui.py --no-open`), then
Ctrl+Shift+P > "Simple Browser: Show" > paste the URL. Same page, in an editor tab.

The UI canonicalizes `pending.md` on write: the leading header comment is kept,
everything else is regenerated from the parsed prompts. Hand-written comments below
the header do not survive a UI mutation; annotate as plain text inside a block instead.

## Modes (dispatch on the argument)

- no argument, or `run` / `drain` / `go` → **Drain** (default)
- `add <text>` → append `<text>` to `pending.md` as a new block, confirm it was queued, STOP. Do not drain.
- `list` / `status` → print the pending prompts in order with their position. Do not run them.
- `clear` → show what will be discarded, move all pending blocks to `done.md` marked `cleared`, leave `pending.md` empty.

## Drain procedure (the core)

Run this only after the current in-flight task is finished. Then:

1. Read `pending.md`. Parse into ordered prompt blocks: strip HTML comments (`<!-- ... -->`, including multi-line) first, then split on `^---$` lines, trim each segment, drop empty segments. The remainder are the queued prompts in order.
2. No prompt blocks → report `Queue empty.` and stop.
3. Take the **first** block. Announce it: `Queue [k of N]: <first line of the prompt>`.
4. Execute it exactly as if the user had just typed it. Full agent capabilities; every rule and gate still applies (see Guardrails).
5. On success: remove that exact block from `pending.md`, and append it to `done.md` in this shape:

   ```text
   ## <YYYY-MM-DD HH:MM> done
   <the prompt>
   > <one-line outcome>
   ```

   The tag after the timestamp is `done` for drained prompts; the mini UI writes
   `deleted` and `cleared` for prompts removed without running. Same entry shape.

6. Re-read `pending.md` (this picks up anything appended while step 4 ran) and return to step 2.
7. When `pending.md` has no prompt blocks left, print a one-line summary (`Drained N prompts.`) and STOP. Do not schedule a wakeup; do not poll.

Re-reading every iteration is deliberate: if you keep appending while it drains, it keeps
going until the file is empty, then stops on its own.

## Guardrails

- A queued prompt is a user instruction, but queuing is **not** blanket authorization. The hard gates still fire per item: the Instantly invasive-action gate (B5), the no-auto-commit floor / ship gate (B6 — push-to-main, force push, deploy, tag/release, client subtree push), and any irreversible or outward-facing action. Pause for explicit confirmation exactly as you would for a typed prompt; do not treat "it was in the queue" as the yes.
- If a queued prompt fails, is ambiguous, or needs a decision: **stop draining**. Leave that block and all later blocks in `pending.md` (nothing is lost), surface the problem, and wait. Never skip ahead silently.
- Strict FIFO. Do not reorder.
- Remove a block from `pending.md` only after the work is actually done and recorded in `done.md`. Never delete a prompt you did not complete.

## Header block for a fresh pending.md

```text
<!--
PROMPT QUEUE - pending items (FIFO).
Add a prompt as a new block separated by a line with exactly ---.
Append anytime, including while a chat is mid-task; picked up on the next drain.
Run with /skil_prompt-queue (or say "drain the queue"). Drains once, then stops.
-->
```
