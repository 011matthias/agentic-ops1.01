-- Book-a-demo lead store (Neon Postgres).
-- Run once in the Neon SQL Editor, or let the function ensure it on first call
-- (api/book-demo.js runs the equivalent CREATE TABLE IF NOT EXISTS on cold start).

create table if not exists leads (
  id             bigserial   primary key,
  created_at     timestamptz not null default now(),
  name           text        not null,
  email          text        not null,
  company        text,
  preferred_date text,                 -- free-form availability, kept as text
  consent        boolean     not null,
  source_page    text,
  user_agent     text
);
