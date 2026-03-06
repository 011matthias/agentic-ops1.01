import { serve } from '@hono/node-server';
import { serveStatic } from '@hono/node-server/serve-static';
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import cron from 'node-cron';
import { projectsRouter } from './routes/projects.js';
import { cardsRouter } from './routes/cards.js';
import { boardStateRouter } from './routes/board-state.js';
import { insightsRouter } from './routes/insights.js';
import { runDeadlineScanner } from './jobs/deadline-scanner.js';
import { runDailyDigest } from './jobs/daily-digest.js';

const app = new Hono();

app.use('*', cors({
  origin: ['http://localhost:5173', 'http://127.0.0.1:5173'],
  allowMethods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type'],
}));

// API routes
app.route('/api/projects',   projectsRouter);
app.route('/api/cards',      cardsRouter);
app.route('/api/board-state', boardStateRouter);
app.route('/api/insights',   insightsRouter);

app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }));

// Serve built React app in production (when app/dist/ exists)
app.use('/*', serveStatic({ root: '../app/dist' }));
app.get('/*', serveStatic({ path: '../app/dist/index.html' }));

// Cron jobs (run in-process, no external service needed)
// Deadline scanner — every hour at :00
cron.schedule('0 * * * *', () => {
  console.log('[cron] Running deadline scanner...');
  try { runDeadlineScanner(); } catch (e) { console.error('[cron] Deadline scanner failed:', e); }
});

// Daily digest — 8:00 AM
cron.schedule('0 8 * * *', () => {
  console.log('[cron] Running daily digest...');
  try { runDailyDigest(); } catch (e) { console.error('[cron] Daily digest failed:', e); }
});

const PORT = Number(process.env.PORT ?? 3001);
serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`\nOmniBoard running at http://localhost:${PORT}`);
  console.log('  API   → /api/projects  /api/cards  /api/board-state');
  console.log('  AI    → /api/insights  (requires: ollama serve)');
  console.log('  Crons → deadline scanner hourly · digest at 8am\n');
});
