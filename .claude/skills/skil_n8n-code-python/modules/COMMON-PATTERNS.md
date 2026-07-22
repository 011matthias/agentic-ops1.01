# Common Patterns - Python Code Node

**Use JavaScript for 95% of use cases.** Python in n8n has **NO external libraries**.

Only use Python when you have complex Python-specific logic, need stdlib features (re, statistics, datetime), or strongly prefer Python syntax.

---

## Pattern Reference

The same 10 patterns from `.claude/skills/skil_n8n-code-javascript/modules/COMMON-PATTERNS.md` apply. Translate using the syntax map below.

---

## Python ↔ JavaScript Syntax Map

| Concept | Python | JavaScript |
|---------|--------|------------|
| All items | `_input.all()` | `$input.all()` |
| First item | `_input.first()` | `$input.first()` |
| Current item | `_input.item` | `$input.item` |
| Webhook body | `_json["body"]` | `$json.body` |
| Safe access | `d.get("key", default)` | `d.key \|\| default` |
| Filter | `[x for x in items if x["active"]]` | `items.filter(x => x.active)` |
| Sort | `items.sort(key=lambda x: x["score"], reverse=True)` | `items.sort((a, b) => b.score - a.score)` |
| Return format | `return [{"json": {...}}]` | `return [{json: {...}}]` |

---

## Python-Only Best Practices

1. **Always use `.get()` with defaults** — `user.get("name", "Unknown")` not `user["name"]`
2. **Check empty lists** — `if items:` before `items[0]`
3. **Use list comprehensions** — `[item for item in items if item["json"].get("active")]`
4. **Return format** — `[{"json": {...}}]` (array of objects with `"json"` key)
5. **stdlib only** — `json`, `datetime`, `re`, `statistics`, `collections` — no pip packages

---

## See Also

- [COMMON-PATTERNS.md (JavaScript)](../../skil_n8n-code-javascript/modules/COMMON-PATTERNS.md) — Full pattern implementations
- [DATA-ACCESS.md](DATA-ACCESS.md) — Data access patterns
- [STANDARD-LIBRARY.md](STANDARD-LIBRARY.md) — Available modules
- [ERROR-PATTERNS.md](ERROR-PATTERNS.md) — Common mistakes
