---
id: be1
name: OmniBoard API
type: backend
stage: build
orchestrator: hono
version: 1.0
created: 2026-03-05
updated: 2026-03-05
trigger: http
systems: [sqlite, drizzle]
last_changes: Initial spec
next_steps: Scaffold server/, install deps, implement schema → routes → test with curl
---

# OmniBoard API

Local Hono.js REST API with Drizzle ORM + SQLite. Runs at `localhost:3001`.

## Tech Stack

- Hono.js + `@hono/node-server`
- Drizzle ORM + `better-sqlite3`
- TypeScript
- Zod (validation on routes)

## Drizzle Schema (`server/src/db/schema.ts`)

```typescript
export const projects = sqliteTable('projects', {
  id:        text('id').primaryKey(),
  name:      text('name').notNull(),
  color:     text('color').notNull().default('#6366f1'),
  columns:   text('columns').notNull(),   // JSON: { id, label }[]
  tags:      text('tags').notNull(),      // JSON: { id, name, color }[]
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
});

export const cards = sqliteTable('cards', {
  id:          text('id').primaryKey(),
  projectId:   text('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),
  columnId:    text('column_id').notNull(),  // backlog | todo | in-progress | completed
  title:       text('title').notNull(),
  description: text('description').notNull().default(''),
  position:    real('position').notNull(),   // fractional indexing (1024, 2048, ...)
  tags:        text('tags').notNull(),       // JSON: { id, name, color }[]
  attributes:  text('attributes').notNull(), // JSON: { key, value }[]
  createdAt:   text('created_at').notNull(),
  updatedAt:   text('updated_at').notNull(),
});
```

## Routes

### Projects

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/projects` | — | `Project[]` |
| POST | `/api/projects` | `{ name, color }` | `Project` |
| PATCH | `/api/projects/:id` | `Partial<Project>` | `Project` |
| DELETE | `/api/projects/:id` | — | `204` |

### Cards

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/cards` | `?projectId=` (optional) | `Card[]` |
| POST | `/api/cards` | `{ projectId, columnId, title }` | `Card` |
| PATCH | `/api/cards/:id` | `Partial<Card>` | `Card` |
| DELETE | `/api/cards/:id` | — | `204` |

### Board State (for Trigger.dev tasks)

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/board-state` | — | `BoardState` |

`BoardState`:
```typescript
{
  projects: Project[];
  cards: Card[];
  stats: {
    totalCards: number;
    byColumn: Record<ColumnId, number>;
    byProject: Record<string, number>;
    overdue: Card[];     // Deadline attribute < now
    dueSoon: Card[];     // Deadline attribute < now + 24h
  };
}
```

## Position Logic (fractional indexing)

- New card at end of column: `position = lastCard.position + 1024`
- Move between cards A and B: `position = (A.position + B.position) / 2`
- When gap < 0.001: renormalize all cards in that column (multiply by 1024)

## CORS

Allow `http://localhost:5173` (Vite dev server).

## Environment

No env vars needed — SQLite file is stored at `server/omniboard.db`.

## Startup

```bash
cd server && npm install && npm run db:push && npm run dev
# Drizzle push creates tables from schema, no migrations needed in dev
```

## Acceptance Criteria

- [ ] `GET /api/projects` returns empty array on first run
- [ ] CRUD on projects persists in SQLite
- [ ] CRUD on cards persists in SQLite
- [ ] Deleting a project cascades-deletes its cards
- [ ] `GET /api/board-state` returns correct `overdue` and `dueSoon` arrays
- [ ] CORS allows requests from `localhost:5173`
