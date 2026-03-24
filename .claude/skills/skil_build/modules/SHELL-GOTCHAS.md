# Shell Gotchas

Known shell pitfalls that have caused production failures. Reference before running shell commands in deploy/config workflows.

## Trailing Newline Corruption

**Problem:** `echo "value" | command` appends a trailing newline. Tools like `vercel env add` store it literally, corrupting the value.
**Fix:** Use `printf '%s' "value" | command` or tool-specific flags (e.g., `vercel env add VAR --value "val"`).

## Windows/Unix Line Endings

**Problem:** Files on Windows have `\r\n`. Piped to Unix tools or deployed to Linux, the `\r` causes silent failures.
**Fix:** Use `tr -d '\r'` in pipe chains for Windows-originated content.

## Heredoc Quoting

**Problem:** Unquoted heredocs (`<<EOF`) expand variables. Quoted (`<<'EOF'`) do not.
**Fix:** Always use `<<'EOF'` when content contains `$`, backticks, or should be literal.

## Python Encoding on Windows

**Problem:** Python defaults to cp1252 on Windows. UTF-8 content silently corrupts.
**Fix:** Always use `encoding='utf-8'` on all `open()` calls. (Also in MEMORY.md.)
