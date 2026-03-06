# MAKE-BUILD -- Make.com Implementation Workflow

Scenarios are built via Make.com MCP tools (programmatic blueprint deployment) or the Make.com web UI (fallback). MCP tools enable blueprint generation and deployment from specs.

---

## The Core Principle

**Blueprints are code.** Claude generates Make.com blueprint JSON from the spec, then deploys it via MCP tools. Connection IDs and webhook URLs are instance-specific and must be configured per-client.

---

## Step 1: Architecture Planning

Invoke the **`make-scenario-patterns`** skill to choose the right pattern.

1. **Identify the trigger type:**
   - **Instant trigger** (webhook) -- scenario runs immediately when event is received
   - **Scheduled trigger** -- scenario runs on interval (minutes/hours/days)
   - **Polling trigger** (Watch module) -- Make.com checks for new data periodically

2. **Map the spec flow to Make.com modules:**
   - Each spec step maps to one or more Make.com modules
   - Check `make-scenario-patterns` for the module selection guide (native app vs HTTP)
   - Note where Routers (branching), Iterators (array processing), or Aggregators (combining) are needed

3. **Plan error handling:**
   - All write/HTTP modules need error handler routes
   - Break (fatal/5xx) vs Resume (non-fatal/404) vs Ignore (harmless)
   - Retry pattern: Break with `maxRetries` and `interval`

---

## Step 2: Review Spec Completeness

Before building, verify the spec includes:

- [ ] All source/target systems identified
- [ ] Trigger type and schedule defined
- [ ] Data field mappings documented (source field --> target field)
- [ ] Error handling approach specified
- [ ] Connections (auth) requirements listed
- [ ] Acceptance criteria defined

If any are missing, update the spec first using `/spec-updater`.

---

## Step 3: Connection Verification

Invoke the **`make-mcp-tools-expert`** skill.

Use MCP tools to verify connections exist in the client's Make.com org:

1. List available connections for the client's team
2. Note connection IDs needed for each service in the blueprint
3. If connections are missing, instruct the client to create them in the Make.com UI
4. Connection IDs are instance-specific -- record them for blueprint generation

---

## Step 4: Generate Blueprint JSON

### Option A: Start from a Make.com Export (Recommended for handover scenarios)

If this scenario will be delivered as a handover blueprint (the client will import it via Make.com UI), start from an exported blueprint rather than generating from scratch:

1. Export a similar existing scenario from the client's Make.com org: `scenarios_get(scenarioId)` returns API format
2. For UI-import format: use Make.com UI three-dots menu > "Export Blueprint" -- this includes `scheduling`, `interface`, `metadata.designer.orphans`, and `metadata.scenario.dataloss` that API-built blueprints omit
3. Use the exported JSON as your starting template, replacing modules as needed
4. All handover-required metadata fields will be present from the start

This prevents the IMPORT_FORMAT_ERROR (IF-1) class of failures where an API-valid blueprint fails UI import due to missing metadata fields.

### Option B: Generate from spec (API-deploy-only scenarios)

Using the spec and the **`make-mcp-tools-expert` > BLUEPRINT-FORMAT.md** reference:

1. Build the blueprint JSON following the standard format
2. Populate `flow` array with modules matching the spec's flow diagram
3. Set `mapper` objects with data field mappings from the spec
4. Add `filter` objects on Router routes for conditional logic
5. Attach `onerror` handlers on write/HTTP modules
6. Configure `metadata` (instant, sequential, maxErrors)
7. Reference connection IDs from Step 3

> **If using Option B and the scenario may later become a handover:** Run `blueprint-reconciler` > HANDOVER-FORMAT-CHECKER immediately after generating the blueprint, before the missing UI-import fields are forgotten.

**Save blueprint to:** `workspace/clients/{client}/automations/blueprints/{id}-{name}.json`

---

## Step 5: Deploy via MCP

Use Make.com MCP tools to deploy the scenario:

1. Create scenario from blueprint (requires team ID)
2. Verify scenario was created (get scenario details)
3. Note the scenario URL and ID for documentation
4. If webhook trigger: copy the generated webhook URL to the source system

**Fallback:** If MCP deployment fails, provide the blueprint JSON for manual import in the Make.com UI (Scenarios → Import Blueprint).

---

## Step 5.5: Source Schema Verification

**Before testing, verify the source system's payload format matches the blueprint's mapper.**

If the scenario has an external trigger (webhook from a form, API, or third-party system):

1. **Check known providers:** Consult `webhook-inspector` skill → KNOWN-PROVIDERS.md
   - Tally: nested `data.fields[]` array — requires `first(map(...))` accessor
   - Typeform: nested `form_response.answers[]` — requires field ID matching
   - Stripe: nested `data.object` — requires deep path references
2. **If provider not listed:** Use `webhook-inspector` skill → CAPTURE-PATTERN.md to capture a real payload
3. **Compare source format against mapper expressions:**
   - Does the source send flat fields or nested structures?
   - Do field names match the `1.body.*` references in the blueprint?
   - Are there arrays that need `map()` / `first()` to extract values?
4. **If structural mismatch:** Update mapper expressions BEFORE testing
   - This prevents false positives where the scenario "succeeds" but data is empty/wrong

**This step prevents the most common integration bug:** building mappers with assumed field names, testing with clean JSON, then discovering the real source sends a completely different structure.

---

## Step 6: Test

### Pre-Test: Check Fixture Registry
Before testing, check `workspace/clients/{client}/context/test-fixtures.md` for existing observability and control fixtures (Sheet Readers, Cell Writers, etc.). Use these instead of creating disposable utilities. See `.claude/rules/behaviors.md` for outcome verification and test fixture conventions.

### Run Once
1. Ensure scheduling is **OFF** (toggle in bottom-left)
2. Click **"Run once"** in the editor
3. Inspect each module's input/output bubbles (click the bubble above each module)
4. Verify data mappings produce expected output
5. Confirm items created/updated correctly in target systems

### Incremental Testing
1. Test trigger module alone first
2. Add modules one at a time, testing after each addition
3. Test error handlers by deliberately providing invalid data

### Idempotency
1. Run once (creates items)
2. Run once again with the same data
3. Verify no duplicate items created in target systems

---

## Step 7: Activate

### Pre-activation checklist:
- [ ] All modules tested and producing correct output
- [ ] Error handlers attached to critical modules
- [ ] Scenario named following convention (`{ID} - {Description}`)
- [ ] Connections use production credentials (not test/sandbox)
- [ ] Scheduling set to correct interval
- [ ] Sequential processing configured if needed

### Activate:
1. Toggle scheduling **ON** (bottom-left switch)
2. Monitor first 2-3 scheduled executions in the history tab
3. Verify results in target systems after each execution

---

## Step 8: Document

Update the following after activation:

1. **`workspace/clients/{client}/automations/README.md`** -- Add scenario link and status
2. **`workspace/clients/{client}/infrastructure.yaml`** -- Ensure Make.com entry exists
3. **Spec frontmatter** -- Set `stage: live` when confirmed working
4. **Export final blueprint** -- Save to `workspace/clients/{client}/automations/blueprints/{id}-{name}.json`

---

## Fallback: Manual UI Build

If MCP tools are unavailable (no API token, free plan, etc.), build directly in Make.com:

1. **Create Scenario** -- New scenario in the correct org/team, name as `{ID} - {Description}`
2. **Add Trigger** -- Webhook (note URL), Schedule (set interval), or Watch (configure polling)
3. **Add Modules** -- Working left-to-right through the spec flow diagram, configure connections and mappings
4. **Add Error Handlers** -- Right-click critical modules, attach Break/Resume/Ignore routes
5. **Configure Settings** -- Max cycles, sequential processing, data confidentiality
6. **Test & Activate** -- Follow Steps 6-8 above

Reference: `.claude/rules/make/project-setup.md` for detailed UI building guidelines.

---

## Common Gotchas

| Problem | Fix |
|---------|-----|
| Mapping shows empty | Check module execution order -- source must run before consumer |
| Iterator produces no output | Verify array mapping points to actual array, not single object |
| Webhook not receiving data | Check webhook URL is registered in source system |
| Rate limit errors (429) | Add Sleep module between iterator items (200-500ms) |
| Scenario stops on error | Change from Break to Resume for non-fatal errors |
| Connection expired | Reconnect in Make.com Connections page, retest |
| Blueprint import fails | Verify connection IDs are valid for the target org |
| Wrong data types | Use `toString()`, `toNumber()`, `parseDate()` in mappings |
