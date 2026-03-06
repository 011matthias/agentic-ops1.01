import { execSync } from 'child_process';
import { db } from '../db/index.js';
import { cards, projects } from '../db/schema.js';

function notify(title: string, message: string) {
  const safe = message.replace(/"/g, "'");
  try {
    execSync(`osascript -e 'display notification "${safe}" with title "${title}"'`, { stdio: 'ignore' });
  } catch {
    console.log(`[NOTIFY] ${title}: ${message}`);
  }
}

export function runDeadlineScanner() {
  const now = Date.now();
  const in24h = now + 24 * 60 * 60 * 1000;

  const allCards = db.select().from(cards).all();
  const allProjects = db.select().from(projects).all();
  const projectNames = Object.fromEntries(allProjects.map(p => [p.id, p.name]));

  let sent = 0;

  for (const card of allCards) {
    let attrs: { key: string; value: string }[] = [];
    try { attrs = JSON.parse(card.attributes); } catch { continue; }

    const deadlineAttr = attrs.find(a => a.key === 'Deadline');
    if (!deadlineAttr) continue;

    const deadlineMs = new Date(deadlineAttr.value).getTime();
    if (isNaN(deadlineMs)) continue;

    const projectName = projectNames[card.projectId] ?? 'Unknown';

    if (deadlineMs < now) {
      notify('OmniBoard — Overdue', `[OVERDUE] ${card.title} (${projectName})`);
      sent++;
    } else if (deadlineMs < in24h) {
      const hoursLeft = Math.round((deadlineMs - now) / 3_600_000);
      notify('OmniBoard — Due Soon', `Due in ${hoursLeft}h: ${card.title} (${projectName})`);
      sent++;
    }
  }

  if (sent > 0) {
    console.log(`[deadline-scanner] ${sent} notification(s) sent`);
  }
}
