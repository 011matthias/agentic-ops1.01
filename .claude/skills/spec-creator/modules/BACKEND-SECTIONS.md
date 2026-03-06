# Backend/Service Spec Sections

Use these section templates when `type: backend` — for backend APIs, database migrations, infrastructure services, and integrations.

---

## Frontmatter Template

```yaml
---
id: be{N}
name: {Service Name}
type: backend
stage: spec
needs_fixes: false
version: 1.0.0
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
orchestrator: none
systems:
  - {database}
  - {external-api}
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

**Problem:** {What gap this backend service addresses}

**Solution:** {What it provides — endpoints, data processing, integrations}

**Business Value:**
- {Benefit 1}
- {Benefit 2}
```

---

## Architecture Section

```markdown
## Architecture

```mermaid
flowchart TD
    A[{Client / Caller}] -->|{method} /{endpoint}| B[{Service Name}]
    B --> C{Auth check}
    C -->|Unauthorized| D[401 response]
    C -->|Authorized| E[{Business logic}]
    E --> F[{Database / External API}]
    F --> G[Return {response}]
```

**Tech Stack:**
| Component | Technology | Reason |
|-----------|-----------|--------|
| Runtime | {Python / Node.js} | {Why} |
| Framework | {FastAPI / Express / ...} | {Why} |
| Database | {Postgres / SQLite / ...} | {Why} |
| Auth | {API key / JWT / cookie} | {Why} |
| Hosting | {Railway / Fly.io / ...} | {Why} |
```

---

## API Endpoints Section

```markdown
## API Endpoints

### `{METHOD} /{path}`

**Auth:** `{X-API-Key header / cookie / none}`

**Request:**
```json
{
  "field": "value"
}
```

**Response (200):**
```json
{
  "status": "ok",
  "data": {}
}
```

**Error Responses:**
| Status | Reason |
|--------|--------|
| 400 | Invalid request body |
| 401 | Missing or invalid auth |
| 404 | Resource not found |
| 500 | Internal server error |
```

---

## Database Schema Section

```markdown
## Database Schema

### `{table_name}` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID PK | Unique identifier |
| `{field}` | {VARCHAR/INT/JSON/...} | {Purpose} |
| `created_at` | TIMESTAMPTZ | Row creation time |
| `updated_at` | TIMESTAMPTZ | Last modification |
```

---

## Edge Cases & Error Handling

```markdown
## Edge Cases & Error Handling

| Scenario | Handling | Recovery |
|----------|----------|----------|
| {External API timeout} | Retry 3x with backoff | Return 503 if all fail |
| {Duplicate record} | Return 409 with existing ID | Client deduplicates |
| {Invalid payload} | Validate on entry, return 400 | Client fixes and retries |
| {Auth failure} | Return 401 | Client refreshes token |
```

---

## Testing Section

```markdown
## Testing

### Unit Tests

- Test {function} with valid input → returns {expected}
- Test {function} with invalid input → raises {error}

### Integration Tests

1. POST `/{endpoint}` with valid payload → 200, data stored
2. POST `/{endpoint}` with invalid auth → 401
3. GET `/{endpoint}` → returns correct data
4. Test duplicate handling → 409 or idempotent response

### Acceptance Criteria

- [ ] All endpoints return correct status codes
- [ ] Auth is enforced on all protected routes
- [ ] DB schema applies cleanly via migration
- [ ] Error responses include useful messages
```

---

## Implementation Notes Section

```markdown
## Implementation Notes

**Code Location:**
- Router: `{path to router file}`
- Models: `{path to models file}`
- Service logic: `{path to service file}`

**Dependencies:**
- `{package}` — {why}

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `INTERNAL_API_KEY` | Auth for internal callers |
| `{OTHER_VAR}` | {What it's for} |

**Migration:**
```bash
# Apply schema changes
uv run alembic upgrade head
```
```
