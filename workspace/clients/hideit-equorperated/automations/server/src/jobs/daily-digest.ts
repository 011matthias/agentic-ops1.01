import { execSync } from 'child_process';
import { appendFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { db } from '../db/index.js';
import { cards } from '../db/schema.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DIGEST_FILE = join(__dirname, '../../../digest.jsonl');

function notify(title: string, message: string) {
  const safe = message.replace(/"/g, "'");
  try {
    execSync(`osascript -e 'display notification "${safe}" with title "${title}"'`, { stdio: 'ignore' });
  } catch {
    console.log(`[NOTIFY] ${title}: ${message}`);
  }
}

export function runDailyDigest() {
  const now = new Date();
  const yesterdayStart = new Date(now);
  yesterdayStart.setDate(yesterdayStart.getDate() - 1);
  yesterdayStart.setHours(0, 0, 0, 0);
  const yesterdayEnd = new Date(yesterdayStart);
  yesterdayEnd.setDate(yesterdayEnd.getDate() + 1);

  const allCards = db.select().from(cards).all();

  const completedYesterday = allCards.filter(c => {
    if (c.columnId !== 'completed') return false;
    const updated = new Date(c.updatedAt).getTime();
    return updated >= yesterdayStart.getTime() && updated < yesterdayEnd.getTime();
  }).length;

  const inProgress = allCards.filter(c => c.columnId === 'in-progress').length;
  const todo       = allCards.filter(c => c.columnId === 'todo').length;
  const overdue    = allCards.filter(c => {
    let attrs: { key: string; value: string }[] = [];
    try { attrs = JSON.parse(c.attributes); } catch { return false; }
    const d = attrs.find(a => a.key === 'Deadline');
    return d && new Date(d.value).getTime() < Date.now();
  }).length;

  const messageParts = [`Yesterday: ${completedYesterday} completed.`, `Today: ${inProgress} in progress, ${todo} todo`];
  if (overdue > 0) messageParts.push(`${overdue} overdue`);
  const message = messageParts.join(' ') + '.';

  notify('OmniBoard — Good morning!', message);

  const entry = {
    date:                 now.toISOString().slice(0, 10),
    completed_yesterday:  completedYesterday,
    in_progress:          inProgress,
    todo,
    overdue,
    ts:                   now.toISOString(),
  };
  try {
    appendFileSync(DIGEST_FILE, JSON.stringify(entry) + '\n');
  } catch {
    console.warn('[daily-digest] Could not write digest.jsonl');
  }

  console.log(`[daily-digest] ${message}`);
}
