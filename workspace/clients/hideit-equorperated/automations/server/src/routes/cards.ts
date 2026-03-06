import { Hono } from 'hono';
import { db } from '../db/index.js';
import { cards } from '../db/schema.js';
import { eq, and } from 'drizzle-orm';
import { randomUUID } from 'crypto';

export const cardsRouter = new Hono();

cardsRouter.get('/', (c) => {
  const projectId = c.req.query('projectId');
  const rows = projectId
    ? db.select().from(cards).where(eq(cards.projectId, projectId)).all()
    : db.select().from(cards).all();
  return c.json(rows.map(deserialize));
});

cardsRouter.post('/', async (c) => {
  const body = await c.req.json<{ id?: string; projectId: string; columnId: string; title: string }>();
  if (!body.title?.trim()) return c.json({ error: 'title required' }, 400);
  if (!body.projectId)     return c.json({ error: 'projectId required' }, 400);
  if (!body.columnId)      return c.json({ error: 'columnId required' }, 400);

  // Position: max position in column + 1024
  const existing = db.select({ position: cards.position })
    .from(cards)
    .where(and(eq(cards.projectId, body.projectId), eq(cards.columnId, body.columnId)))
    .all();
  const maxPos = existing.reduce((m, r) => Math.max(m, r.position), 0);

  const now = new Date().toISOString();
  const row = {
    id:          body.id ?? `card_${randomUUID().replace(/-/g, '').slice(0, 10)}`,
    projectId:   body.projectId,
    columnId:    body.columnId,
    title:       body.title.trim(),
    description: '',
    position:    maxPos + 1024,
    tags:        '[]',
    attributes:  '[]',
    createdAt:   now,
    updatedAt:   now,
  };
  db.insert(cards).values(row).run();
  return c.json(deserialize(row), 201);
});

cardsRouter.patch('/:id', async (c) => {
  const id = c.req.param('id');
  const body = await c.req.json<Record<string, unknown>>();
  const existing = db.select().from(cards).where(eq(cards.id, id)).get();
  if (!existing) return c.json({ error: 'not found' }, 404);

  const patch: Partial<typeof existing> = { updatedAt: new Date().toISOString() };
  if (typeof body.title === 'string')       patch.title       = body.title;
  if (typeof body.description === 'string') patch.description = body.description;
  if (typeof body.columnId === 'string')    patch.columnId    = body.columnId;
  if (typeof body.position === 'number')    patch.position    = body.position;
  if (Array.isArray(body.tags))             patch.tags        = JSON.stringify(body.tags);
  if (Array.isArray(body.attributes))       patch.attributes  = JSON.stringify(body.attributes);

  db.update(cards).set(patch).where(eq(cards.id, id)).run();

  // Renormalize positions if gap too small
  if (typeof body.position === 'number') {
    await maybeRenormalize(existing.projectId, existing.columnId);
  }

  const updated = db.select().from(cards).where(eq(cards.id, id)).get()!;
  return c.json(deserialize(updated));
});

cardsRouter.delete('/:id', (c) => {
  const id = c.req.param('id');
  db.delete(cards).where(eq(cards.id, id)).run();
  return new Response(null, { status: 204 });
});

async function maybeRenormalize(projectId: string, columnId: string) {
  const colCards = db.select()
    .from(cards)
    .where(and(eq(cards.projectId, projectId), eq(cards.columnId, columnId)))
    .all()
    .sort((a, b) => a.position - b.position);

  if (colCards.length < 2) return;
  const minGap = Math.min(...colCards.slice(1).map((c, i) => c.position - colCards[i].position));
  if (minGap >= 0.001) return;

  // Renormalize: assign 1024, 2048, 3072, ...
  colCards.forEach((card, i) => {
    db.update(cards)
      .set({ position: (i + 1) * 1024 })
      .where(eq(cards.id, card.id))
      .run();
  });
}

function deserialize(row: typeof cards.$inferSelect) {
  return {
    ...row,
    tags:       JSON.parse(row.tags),
    attributes: JSON.parse(row.attributes),
  };
}
