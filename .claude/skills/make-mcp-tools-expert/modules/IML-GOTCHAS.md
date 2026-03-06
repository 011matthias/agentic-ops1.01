# Make.com IML Gotchas & Workarounds

Critical IML (Integromat Markup Language) limitations discovered through production debugging. These are NOT documented in Make.com's official docs.

---

## IML Numeric Key Limitation (CRITICAL)

`{{moduleId.numericKey}}` is parsed as a **decimal number**, NOT a field reference.

- `{{2.3}}` → `"2.3"` (decimal), NOT "module 2, field 3"
- `{{2.11}}` → `"2.11"` (decimal)
- Affects ALL Google Sheets read modules (`filterRows`, `getSheetContent`) which output 0-indexed numeric keys

**Workaround:** Use `getCell` module which outputs a NAMED `value` field → `{{moduleId.value}}` works. Chain multiple `getCell` modules after `filterRows` to read individual fields.

---

## IML Function Arguments: Numeric Literals (CRITICAL)

`toString(moduleId)` where moduleId is numeric treats the argument as a **literal number**, NOT a module reference.

- `{{toString(2)}}` → `"2"` (literal string of number 2)
- `{{toString(10)}}` → `"10"` (same — multi-digit doesn't help)
- Affects ANY IML function call with a bare numeric module ID argument

**Workaround:** Use dot-notation field access: `{{10.value}}` resolves to module 10's `value` field correctly. For webhook responses returning module data, use pipe-separated `key={{moduleId.field}}` references instead of `toString(moduleId)`.

---

## filterRows Operator Reference

| Operator | Status | Notes |
|----------|--------|-------|
| `text:equal` | Works | Standard text comparison |
| `text:notEqual` | BROKEN | Silent filter failure (no match, no error) |
| `number:greaterorequal` | Works | Numeric comparison |
| `date:before` | BREAKS OUTPUT | Corrupts `__ROW_NUMBER__` in results |

**`date:before` causes filterRows to return results with EMPTY `__ROW_NUMBER__`**, breaking all downstream `getCell` references. The operator is syntactically accepted (`isinvalid: false`) but corrupts runtime output.

---

## Date Comparison Workaround

Since `date:before` breaks filterRows, use IML string comparison in **router filters**:

```
{{if(14.value < formatDate(now; "YYYY-MM-DDTHH:mm:ssZ"); "due"; "notdue")}}
```

Then compare with `text:equal` `"due"`. ISO 8601 strings sort lexicographically correctly as long as timezone offsets are consistent.

---

## Function Reference

- `parseNumber(value; ".")` — NOT `toNumber()` (doesn't exist in Make IML)
- `first(map(array; "valueField"; "keyField"; "keyMatch"))` — search array by key, return value
- `ifempty(value; "default")` — fallback for empty/null
- `formatDate(now; "YYYY-MM-DDTHH:mm:ssZ")` — date formatting
- `addHours(now; 24)` — date arithmetic

---

## getCell Dynamic Cell References

- `C{{2.__ROW_NUMBER__}}` → `"C2"` (literal prefix outside IML expression — correct)
- `{{"C" & 2.__ROW_NUMBER__}}` → `"2"` (string concatenation loses the prefix — broken)

---

## google-email:sendAnEmail — Field Name (CRITICAL)

Must use **version 4**. Version 4 does **NOT** accept `html` as a mapper field — it is silently ignored. The correct approach:

```json
"mapper": {
  "to": "{{...}}",
  "subject": "{{...}}",
  "bodyType": "rawHtml",
  "content": "{{...html body expression...}}",
  "fromName": "{{...}}"
}
```

**What happens with `html`:** The Gmail module accepts the field but silently ignores it. The email IS sent (no error) but the body is empty — blank MIME boundaries in the raw MIME output:
```
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: 7bit

--boundary--
```

**Diagnosis path:** Use `datastore:GetRecord`, `replace()` chains, and `util:SetVariable2` outputs to confirm upstream data is correct before suspecting the Gmail module itself. The issue manifests as empty body despite all upstream IML expressions resolving correctly.

**Root cause:** Discovered via `app-module_get` — `bodyType` (select: `rawHtml`|`collection`) with nested `content` field is the v4 spec. Always run `app-module_get` on Gmail module before building mappers.

---

## updateRow with Header Names

Use `"mode": "select"` + `"useColumnHeaders": true` + `"includesHeaders": true` to reference columns by header name in the `values` object instead of numeric indices. More resilient to column reordering.

---

## CustomWebHook Data Access Paths

The path depends on `udt` (user data type) from `hooks_get(hookId)`:

| `udt` value | Path | Example |
|-------------|------|---------|
| `null` | `1.data.*` or `1.*` | `1.data.fields` for Tally |
| Set (learned) | `1.body.*` | `1.body.data.fields` for Tally |

**Always run `hooks_get(hookId)` and check `udt` before building mappers.**

---

## Module Name Casing Matters

`datastore:AddRecord` (capital A), NOT `datastore:addRecord`. Similarly `datastore:GetRecord`. Incorrect casing causes silent failures.

---

## `datastore:GetRecord` — `returnWrapped` is REQUIRED

The module spec declares `returnWrapped` as `required: true, default: false`. When deploying blueprints via API, required params with defaults are **NOT auto-filled**. Always explicitly set `"returnWrapped": false` in the mapper:

```json
{"id": 50, "module": "datastore:GetRecord", "version": 1,
  "parameters": {"datastore": 98606},
  "mapper": {"key": "main", "returnWrapped": false}}
```

Without it → `BundleValidationError` on every downstream module. **General rule:** Always check `app-module_get` for `required: true` params in `expect[]` and set them explicitly, even if they have defaults.

---

## `util:SetVariable2` — `scope: "roundtrip"` is REQUIRED

Same gotcha as `returnWrapped`. Output accessed as `{{moduleId.variableName}}` (e.g., `{{52.lead_score}}`). Use for compute-once-reference-everywhere patterns.

---

## `http:ActionSendData` for External APIs

Use when no native Make.com connection exists. Key mapper fields: `url`, `method`, `headers` (array of `{name, value}`), `bodyType: "raw"`, `contentType: "application/json"`, `data` (JSON string with IML expressions), `parseResponse: true`. Output: `data` (auto-parsed JSON), `statusCode`. Parameters: `handleErrors: true`, `useNewZLibDeCompress: true`.

---

## OpenAI App Name in Make.com

The app name is `openai-gpt-3` (v1), NOT `openai` or `openai-gpt-4`. Use `apps_recommend` to discover correct names. No connections can be created via API for built-in apps — fall back to HTTP module.

---

## Make.com Parsed JSON Array Indexing

Use `[1]` not `[0]` for first element (1-based). E.g., `70.data.choices[1].message.content` for OpenAI response.

---

## Pre-Router Enrichment Pattern

Place shared enrichment modules (API calls, data store lookups, variable computations) **before** the router so all routes can access the output. One call serves all routes — cheaper and simpler than duplicating the module in each route.

---

## Graceful API Degradation (Resume + ifempty)

For non-critical API calls (AI personalization, analytics, etc.):
1. Set `"handleErrors": true` in module parameters
2. Add `builtin:Resume` as `onerror` handler on the API module
3. Use `ifempty(moduleId.outputField; "fallback")` in all downstream references

If the API call fails, Resume allows the scenario to continue, and `ifempty()` provides the fallback value. The API enrichment is additive, never blocking.

**Warning:** A scenario with `builtin:Resume` will show status:1 even if those modules failed. Don't trust status alone — always verify outcomes.
