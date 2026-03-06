import { Hono } from 'hono';
import { db } from '../db/index.js';
import { cards, projects } from '../db/schema.js';

export const boardStateRouter = new Hono();

boardStateRouter.get('/', (c) => {
  const allProjects = db.select().from(projects).all().map(p => ({
    ...p,
    columns:   JSON.parse(p.columns),
    tags:      JSON.parse(p.tags),
  }));

  const allCards = db.select().from(cards).all().map(card => ({
    ...card,
    tags:       JSON.parse(card.tags),
    attributes: JSON.parse(card.attributes),
  }));

  const now = new Date();
  const nowMs = now.getTime();
  const in24h = nowMs + 24 * 60 * 60 * 1000;

  const overdue: typeof allCards = [];
  const dueSoon: typeof allCards = [];

  for (const card of allCards) {
    const attrs: { key: string; value: string }[] = card.attributes;
    const deadlineAttr = attrs.find(a => a.key === 'Deadline');
    if (!deadlineAttr) continue;

    const deadlineMs = new Date(deadlineAttr.value).getTime();
    if (isNaN(deadlineMs)) continue;

    if (deadlineMs < nowMs) {
      overdue.push(card);
    } else if (deadlineMs < in24h) {
      dueSoon.push(card);
    }
  }

  const byColumn: Record<string, number> = {
    backlog: 0, todo: 0, 'in-progress': 0, completed: 0,
  };
  const byProject: Record<string, number> = {};

  for (const card of allCards) {
    byColumn[card.columnId] = (byColumn[card.columnId] ?? 0) + 1;
    byProject[card.projectId] = (byProject[card.projectId] ?? 0) + 1;
  }

  return c.json({
    projects: allProjects,
    cards: allCards,
    stats: {
      totalCards: allCards.length,
      byColumn,
      byProject,
      overdue,
      dueSoon,
    },
  });
});
