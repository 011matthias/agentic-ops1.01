# Template Placeholder Checker

Validates that email template placeholders (`##name##`, `##topic##`, etc.) are resolved by every scenario that uses the template.

## Procedure

### Step 1: Extract Templates

Fetch email templates from the data store:

```
1. Identify the email templates data store (from infrastructure.yaml or client context)
2. data-store-records_list(dataStoreId) → get all template records
3. For each record, extract the template body (usually an HTML string)
4. Extract all placeholders matching pattern: ##[a-zA-Z_]+##
```

Build a map: `{template_key: [placeholder1, placeholder2, ...]}`

### Step 2: Map Scenarios to Templates

For each scenario that sends emails:

```
1. Find email-sending modules in the blueprint:
   - google-email:sendAnEmail / google-email:ActionSendEmail
   - HTTP module with email API endpoint
2. Trace where the email body comes from:
   - Direct in mapper? → Extract placeholders from the mapper value
   - From data store GetRecord? → Note which template record is fetched
   - From SetVariable? → Trace the variable to its source
3. Map: {scenario_id: [template_key(s) it uses]}
```

### Step 3: Trace Placeholder Resolution

For each scenario × template combination:

```
For each placeholder (e.g., ##name##):
  1. Find the IML expression that replaces it
     - Usually in a replace() or SetVariable that builds the email body
     - Pattern: replace(template; "##name##"; {{N.field}})
  2. Trace {{N.field}} — does module N exist and is it reachable?
  3. Will {{N.field}} have a value at runtime?
     - If N is a getCell module → yes (if the cell has data)
     - If N is a webhook module → yes (if the field is in the payload)
     - If N is an API call → maybe (depends on API response)
```

### Step 4: Cross-Scenario Comparison

If multiple scenarios (A1, A3) use the same template:

```
For each template:
  For each placeholder:
    - Does A1 resolve it? How?
    - Does A3 resolve it? How?
    - Are they using the same field source?
```

**Key finding pattern:** Template has `##organisation##` but A3 doesn't read the organisation column from the sheet (A1 does because it has direct access to the webhook payload).

### Step 5: Check for Graceful Degradation

For placeholders that might not resolve (e.g., AI-generated content):

```
Does the replace() use ifempty() or a fallback?
  - Good: replace(body; "##ai_opening##"; ifempty(70.choices[1].message.content; ""))
  - Bad: replace(body; "##ai_opening##"; 70.choices[1].message.content)
    → If module 70 fails, the placeholder stays as literal "##ai_opening##" in the email
```

## Output

```markdown
## Template Placeholder Checker Report

**Templates Data Store:** {name} (ID: {id})
**Templates Checked:** {count}
**Scenarios Checked:** {list}

### Template: {template_key}
**Placeholders:** ##name##, ##topic##, ##organisation##, ##signature##, ##ai_opening##

| Placeholder | A1 Resolution | A3 Resolution | Status |
|-------------|--------------|--------------|--------|
| ##name## | {{1.name}} (webhook) | {{10.value}} (getCell col A) | OK |
| ##topic## | {{1.discussion_topic}} | {{11.value}} (getCell col B) | OK |
| ##organisation## | {{1.organisation}} | NOT RESOLVED | ERROR |
| ##signature## | {{52.email_signature_html}} | {{52.email_signature_html}} | OK |
| ##ai_opening## | ifempty({{70...}}; "") | ifempty({{70...}}; "") | OK (graceful) |

### Findings
| Severity | Template | Placeholder | Scenario | Issue |
|----------|----------|-------------|----------|-------|
| ERROR | welcome_email | ##organisation## | A3 | Not resolved — A3 doesn't read org column. Add getCell or remove from A3 template. |
| WARN | followup_step2 | ##ai_opening## | A3 | Resolved but no ifempty() fallback. If AI fails, raw placeholder appears in email. |
```

## Auto-Fix Options

For unresolved placeholders:

1. **Add the missing data source** — If the field exists in the sheet, add a getCell module to read it
2. **Remove the placeholder from the template** — If the field isn't available in this scenario's context
3. **Create a scenario-specific template variant** — If different scenarios need different placeholders
4. **Add conditional wrapping** — `{{if(text:isnotempty(N.field); "##placeholder##"; "")}}` to hide the entire section when data isn't available

Recommendation: Option 2 or 4 is usually simplest. Option 1 adds modules (more ops, more cost). Option 3 adds template maintenance burden.
