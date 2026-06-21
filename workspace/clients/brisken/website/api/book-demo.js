// Book-a-demo capture: validate -> spam-check -> persist to Neon Postgres -> notify.
// Node serverless function (not Edge: plain Node handler; the Neon HTTP driver runs
// here fine). Persist FIRST, notify after, so a webhook failure never loses a lead.
//
// Hardening note: this is an unauthenticated public insert endpoint. Honeypot +
// time-to-fill are first-line bot filters only; before heavy promotion add a real
// per-IP rate limit (Vercel WAF / Upstash KV) or a Turnstile/hCaptcha token.

import { neon } from '@neondatabase/serverless';

const sql = neon(process.env.DATABASE_URL);

const MIN_FILL_MS = 3000; // submissions faster than this are almost always bots
const MAX_BODY = 16384; // reject oversized raw bodies early (defense in depth)
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Ensure the table exists once per warm instance (idempotent; canonical schema
// also lives in migrations/0001_create_leads.sql). For a hardened setup, run the
// migration once and point DATABASE_URL at an INSERT-only role, then this is a no-op.
let tableReady = false;
async function ensureTable() {
  if (tableReady) return;
  await sql`create table if not exists leads (
    id             bigserial   primary key,
    created_at     timestamptz not null default now(),
    name           text        not null,
    email          text        not null,
    company        text,
    preferred_date text,
    consent        boolean     not null,
    source_page    text
  )`;
  tableReady = true;
}

// Single swap point for the alert channel. Teams/Slack incoming webhooks both
// accept a JSON body with a "text" field. Swap to an email API here if wanted.
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

  // Only accept JSON, and bound the raw body before parsing.
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
      try {
        body = JSON.parse(body || '{}');
      } catch {
        res.status(400).json({ ok: false, error: 'invalid' });
        return;
      }
    }
    if (!body || typeof body !== 'object') {
      res.status(400).json({ ok: false, error: 'invalid' });
      return;
    }

    // Spam 1: honeypot. A real user never fills this hidden field; if it is set,
    // accept silently so the bot believes it succeeded, but persist nothing.
    if (body.company_website) {
      res.status(200).json({ ok: true });
      return;
    }

    // Spam 2: time-to-fill. Reject implausibly fast submits.
    const elapsed = Number(body.elapsed_ms || 0);
    if (!elapsed || elapsed < MIN_FILL_MS) {
      res.status(400).json({ ok: false, error: 'too_fast' });
      return;
    }

    // Validate.
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

    // Persist FIRST (durable record). Parameterized via the tagged template, so
    // user input is bound, never interpolated.
    await ensureTable();
    const rows = await sql`
      insert into leads (name, email, company, preferred_date, consent, source_page)
      values (${name}, ${email}, ${company || null}, ${preferredDate || null},
              ${consent}, ${sourcePage || null})
      returning id`;

    // Notify only after the insert succeeded.
    await notify({ name, email, company, preferred_date: preferredDate, source_page: sourcePage });

    res.status(200).json({ ok: true, id: rows[0] && rows[0].id });
  } catch (err) {
    console.error('book-demo error:', err);
    res.status(500).json({ ok: false, error: 'server_error' });
  }
}
