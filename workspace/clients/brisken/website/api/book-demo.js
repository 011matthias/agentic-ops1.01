// Book-a-demo capture: rate-limit -> validate -> spam-check -> persist (Neon) -> notify.
// Node serverless function. Persist FIRST, notify after, so a webhook failure never
// loses a lead. Uses an INSERT-only DB role when LEADS_DATABASE_URL is set (the table
// is provisioned by migrations/0001_create_leads.sql, not by this function).

import { neon } from '@neondatabase/serverless';

// Prefer a least-privilege (INSERT-only) role if provisioned; fall back to the
// integration's DATABASE_URL otherwise.
const sql = neon(process.env.LEADS_DATABASE_URL || process.env.DATABASE_URL);

const MIN_FILL_MS = 3000;        // submissions faster than this are almost always bots
const MAX_BODY = 16384;          // reject oversized raw bodies early
const RL_WINDOW_MS = 60000;      // rate-limit window
const RL_MAX = 5;                // max submits per IP per window (per warm instance)
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Best-effort in-memory per-IP limiter. Caps bursts against a warm instance for free;
// for a hard global limit across instances, front this with Vercel WAF or a KV store.
const hits = new Map();
function rateLimited(ip) {
  const now = Date.now();
  const arr = (hits.get(ip) || []).filter((t) => now - t < RL_WINDOW_MS);
  if (arr.length >= RL_MAX) { hits.set(ip, arr); return true; }
  arr.push(now);
  hits.set(ip, arr);
  if (hits.size > 5000) hits.clear(); // crude memory guard
  return false;
}

async function notify(lead) {
  const url = process.env.NOTIFY_WEBHOOK_URL;
  if (!url) return; // notifications optional until the webhook is configured
  const text = [
    'New TreasuryCentral demo request',
    `Name: ${lead.name}`,
    `Email: ${lead.email}`,
    `Company: ${lead.company || '-'}`,
    `Availability: ${lead.preferred_date || '-'}`,
    `Source: ${lead.source_page || '-'}`,
    `Time: ${new Date().toISOString()}`,
  ].join('\n');
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  } catch (err) {
    console.error('book-demo notify failed:', err);
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ ok: false, error: 'method_not_allowed' });
    return;
  }

  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  if (rateLimited(ip)) {
    res.status(429).json({ ok: false, error: 'rate_limited' });
    return;
  }

  const ct = String(req.headers['content-type'] || '');
  if (!ct.includes('application/json')) {
    res.status(415).json({ ok: false, error: 'unsupported_media_type' });
    return;
  }

  try {
    let body = req.body;
    if (typeof body === 'string') {
      if (body.length > MAX_BODY) {
        res.status(413).json({ ok: false, error: 'too_large' });
        return;
      }
      try { body = JSON.parse(body || '{}'); }
      catch { res.status(400).json({ ok: false, error: 'invalid' }); return; }
    }
    if (!body || typeof body !== 'object') {
      res.status(400).json({ ok: false, error: 'invalid' });
      return;
    }

    // Spam 1: honeypot. Accept silently (bot thinks it worked), persist nothing.
    if (body.company_website) {
      res.status(200).json({ ok: true });
      return;
    }

    // Spam 2: time-to-fill.
    const elapsed = Number(body.elapsed_ms || 0);
    if (!elapsed || elapsed < MIN_FILL_MS) {
      res.status(400).json({ ok: false, error: 'too_fast' });
      return;
    }

    const name = String(body.name || '').trim().slice(0, 200);
    const email = String(body.email || '').trim().slice(0, 200);
    const company = String(body.company || '').trim().slice(0, 200);
    const preferredDate = String(body.preferred_date || '').trim().slice(0, 300);
    const consent =
      body.consent === true || body.consent === 'true' || body.consent === 'on';

    if (!name || !email || !EMAIL_RE.test(email) || !consent) {
      res.status(400).json({ ok: false, error: 'invalid' });
      return;
    }

    const sourcePage = String(body.source_page || '').slice(0, 300);

    // Persist FIRST. Parameterized via the tagged template (user input is bound).
    const rows = await sql`
      insert into leads (name, email, company, preferred_date, consent, source_page)
      values (${name}, ${email}, ${company || null}, ${preferredDate || null},
              ${consent}, ${sourcePage || null})
      returning id`;

    await notify({ name, email, company, preferred_date: preferredDate, source_page: sourcePage });

    res.status(200).json({ ok: true, id: rows[0] && rows[0].id });
  } catch (err) {
    console.error('book-demo error:', err);
    res.status(500).json({ ok: false, error: 'server_error' });
  }
}
