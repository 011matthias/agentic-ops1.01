import { Hono } from 'hono';
import { db } from '../db/index.js';
import { cards, projects } from '../db/schema.js';

export const insightsRouter = new Hono();

const OLLAMA_URL = 'http://localhost:11434';
const DEFAULT_MODEL = 'llama3.2'; // `ollama pull llama3.2` to use

const SYSTEM_PROMPT = `You are a productivity assistant analyzing a Kanban board.
Return ONLY valid JSON:
{"insights":["..."],"suggested_next":["task title","..."],"risk_flags":["..."],"summary":"one sentence"}
- insights: 3-5 bullet points
- suggested_next: top 3 task titles to work on now
- risk_flags: tasks at risk (overdue, stale, etc.)
- summary: one sentence. Return nothing else — only the JSON object.`;

async function callOllama(prompt: string, model: string): Promise<string> {
  const res = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      stream: false,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user',   content: prompt },
      ],
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!res.ok) throw new Error(`Ollama ${res.status}`);
  const data = await res.json() as { message?: { content?: string } };
  return data.message?.content ?? '';
}

insightsRouter.post('/', async (c) => {
  const body = await c.req.json<{ projectId?: string; focus?: string; model?: string }>().catch(() => ({}));
  const focus = body.focus ?? 'priorities';
  const model = body.model ?? DEFAULT_MODEL;

  // Check Ollama is running
  try {
    await fetch(`${OLLAMA_URL}/api/tags`, { signal: AbortSignal.timeout(2_000) });
  } catch {
    return c.json({
      available: false,
      message: 'Ollama is not running. Start it with: ollama serve',
      install:  'https://ollama.com',
    }, 503);
  }

  // Build board summary
  const allProjects = db.select().from(projects).all();
  const allCards    = db.select().from(cards).all();

  const filteredProjects = body.projectId
    ? allProjects.filter(p => p.id === body.projectId)
    : allProjects;
  const filteredCards = body.projectId
    ? allCards.filter(c => c.projectId === body.projectId)
    : allCards;
  const projectNames = Object.fromEntries(filteredProjects.map(p => [p.id, p.name]));

  const now = Date.now();
  const lines: string[] = [];

  for (const proj of filteredProjects) {
    const pc = filteredCards.filter(c => c.projectId === proj.id);
    const counts = { backlog: 0, todo: 0, 'in-progress': 0, completed: 0 } as Record<string, number>;
    for (const c of pc) counts[c.columnId] = (counts[c.columnId] ?? 0) + 1;
    lines.push(`Project: ${proj.name} (${counts['backlog']} backlog, ${counts['todo']} todo, ${counts['in-progress']} in-progress, ${counts['completed']} completed)`);

    for (const card of pc.sort((a, b) => a.position - b.position)) {
      let attrs: { key: string; value: string }[] = [];
      try { attrs = JSON.parse(card.attributes); } catch {}
      const meta = attrs.map(a => `${a.key}: ${a.value}`).join(', ');
      lines.push(`  [${card.columnId}] ${card.title}${meta ? ` [${meta}]` : ''}`);
    }
  }

  const overdue = filteredCards.filter(c => {
    let attrs: { key: string; value: string }[] = [];
    try { attrs = JSON.parse(c.attributes); } catch { return false; }
    const d = attrs.find(a => a.key === 'Deadline');
    return d && new Date(d.value).getTime() < now;
  });

  if (overdue.length > 0) {
    lines.push(`\nOVERDUE (${overdue.length}):`);
    for (const c of overdue) lines.push(`  ${c.title} (${projectNames[c.projectId] ?? '?'})`);
  }

  const focusMap: Record<string, string> = {
    'priorities':   'Rank tasks by urgency and importance. Highlight overdue items.',
    'blockers':     'Identify tasks that appear blocked or are blocking others.',
    'next-actions': 'Suggest the top 3 concrete actions to move impactful tasks forward.',
  };

  const boardSummary = lines.join('\n');
  if (!boardSummary.trim()) {
    return c.json({ insights: ['Board is empty.'], suggested_next: [], risk_flags: [], summary: 'No tasks yet.' });
  }

  const prompt = `${focusMap[focus] ?? focusMap['priorities']}\n\nBoard state:\n${boardSummary}`;

  try {
    const raw = await callOllama(prompt, model);
    const match = raw.match(/\{[\s\S]*\}/);
    const result = match ? JSON.parse(match[0]) : { insights: [raw], suggested_next: [], risk_flags: [], summary: '' };
    return c.json({ available: true, focus, model, ...result });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return c.json({ available: true, error: msg, message: `AI call failed: ${msg}` }, 500);
  }
});

// GET — check if Ollama is available + list pulled models
insightsRouter.get('/status', async (c) => {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`, { signal: AbortSignal.timeout(2_000) });
    const data = await res.json() as { models?: { name: string }[] };
    return c.json({ available: true, models: data.models?.map(m => m.name) ?? [] });
  } catch {
    return c.json({ available: false, install: 'https://ollama.com', recommended_model: DEFAULT_MODEL });
  }
});
