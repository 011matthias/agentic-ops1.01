import { Hono } from 'hono';
import { db } from '../db/index.js';
import { projects } from '../db/schema.js';
import { eq } from 'drizzle-orm';
import { randomUUID } from 'crypto';

export const projectsRouter = new Hono();

const DEFAULT_COLUMNS = JSON.stringify([
  { id: 'backlog',     label: 'Backlog' },
  { id: 'todo',        label: 'To-Do' },
  { id: 'in-progress', label: 'In Progress' },
  { id: 'completed',   label: 'Completed' },
]);

projectsRouter.get('/', (c) => {
  const rows = db.select().from(projects).all();
  return c.json(rows.map(deserialize));
});

projectsRouter.post('/', async (c) => {
  const body = await c.req.json<{ id?: string; name: string; color?: string }>();
  if (!body.name?.trim()) return c.json({ error: 'name required' }, 400);

  const now = new Date().toISOString();
  const row = {
    id:        body.id ?? `proj_${randomUUID().replace(/-/g, '').slice(0, 10)}`,
    name:      body.name.trim(),
    color:     body.color ?? '#6366f1',
    columns:   DEFAULT_COLUMNS,
    tags:      '[]',
    createdAt: now,
    updatedAt: now,
  };
  db.insert(projects).values(row).run();
  return c.json(deserialize(row), 201);
});

projectsRouter.patch('/:id', async (c) => {
  const id = c.req.param('id');
  const body = await c.req.json<Record<string, unknown>>();
  const existing = db.select().from(projects).where(eq(projects.id, id)).get();
  if (!existing) return c.json({ error: 'not found' }, 404);

  const patch: Partial<typeof existing> = { updatedAt: new Date().toISOString() };
  if (typeof body.name === 'string')    patch.name    = body.name;
  if (typeof body.color === 'string')   patch.color   = body.color;
  if (Array.isArray(body.columns))      patch.columns = JSON.stringify(body.columns);
  if (Array.isArray(body.tags))         patch.tags    = JSON.stringify(body.tags);

  db.update(projects).set(patch).where(eq(projects.id, id)).run();
  const updated = db.select().from(projects).where(eq(projects.id, id)).get()!;
  return c.json(deserialize(updated));
});

projectsRouter.delete('/:id', (c) => {
  const id = c.req.param('id');
  db.delete(projects).where(eq(projects.id, id)).run();
  return new Response(null, { status: 204 });
});

function deserialize(row: typeof projects.$inferSelect) {
  return {
    ...row,
    columns:   JSON.parse(row.columns),
    tags:      JSON.parse(row.tags),
  };
}
