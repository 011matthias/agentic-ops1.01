# App/Frontend Spec Sections

Use these section templates when `type: app` — replacing the automation-oriented sections.

---

## Frontmatter Template

```yaml
---
id: app{N}
name: {App Name}
type: app
stage: spec
needs_fixes: false
version: 1.0.0
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
orchestrator: none
systems:
  - {backend-api}
  - {auth-system}
owner: owner@client.com
last_changes: []
next_steps: []
stage_history:
  - stage: spec
    date: {YYYY-MM-DD}
---
```

---

## Goal Section

```markdown
## Goal

**Problem:** {What manual process or gap this UI addresses}

**Solution:** {What the app provides — who uses it, what they can do}

**Business Value:**
- {Benefit 1}
- {Benefit 2}
```

---

## Tech Stack Section

```markdown
## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Frontend | {React / Jinja2 / Next.js / ...} | {Why} |
| Styling | {Tailwind / CSS / Bootstrap} | {Why} |
| Auth | {Existing cookie session / OAuth / None} | {Why} |
| Data source | {FastAPI / n8n / Postgres / Airtable} | {Why} |
| Hosting | {Railway / Vercel / Netlify} | {Why} |
```

---

## Pages & Routes Section

```markdown
## Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | {Dashboard / Home} | {What it shows} |
| `/{resource}` | {Resource List} | {What it shows} |
| `/{resource}/{id}` | {Resource Detail} | {What it shows} |
```

---

## User Flows Section (Mermaid)

```markdown
## User Flows

```mermaid
flowchart TD
    A[User lands on /{page}] --> B{Authenticated?}
    B -->|No| C[Redirect to /login]
    B -->|Yes| D[Load {data}]
    D --> E[Display {UI component}]
    E -->|User clicks {action}| F[API call: POST /{endpoint}]
    F -->|Success| G[Update UI]
    F -->|Error| H[Show error message]
```
```

---

## UI Components Section

```markdown
## UI Components

### {Component Name}
- **Location:** `{page/route}`
- **Shows:** {what data is displayed}
- **Actions:** {buttons/interactions available}
- **Data source:** `{API endpoint or data field}`

### {Component Name 2}
...
```

---

## API Integration Section

```markdown
## API Integration

| Action | Method | Endpoint | Auth | Description |
|--------|--------|----------|------|-------------|
| Load data | GET | `/{resource}` | {cookie/key} | {What it fetches} |
| Submit | POST | `/{resource}` | {cookie/key} | {What it creates/updates} |
| Delete | DELETE | `/{resource}/{id}` | {cookie/key} | {What it removes} |
```

---

## Testing Section

```markdown
## Testing

### Manual QA Steps

1. Navigate to `/{route}` — verify {expected state}
2. Perform {action} — verify {expected result}
3. Test error case: {scenario} — verify {error message shown}
4. Test auth: log out, try to access `/{route}` — verify redirect to login

### Acceptance Criteria

- [ ] {Feature 1} works end-to-end
- [ ] Error states are handled gracefully
- [ ] Auth is enforced on all protected routes
- [ ] Existing pages still work (regression)
```

---

## Implementation Notes Section

```markdown
## Implementation Notes

**Code Location:**
- Frontend: `{path to templates or components}`
- Backend routes: `{path to router}`

**Dependencies:**
- `{package}` — {why}

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `{VAR}` | {What it's for} |
```
