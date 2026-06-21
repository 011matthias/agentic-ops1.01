-- Book-a-demo lead store (Neon Postgres). Keep the Neon project in an EU region.
-- Run once in the Neon SQL Editor. The function also runs the equivalent
-- CREATE TABLE IF NOT EXISTS on cold start; for a hardened setup, run this once
-- and point DATABASE_URL at an INSERT-only role (then the function's DDL is a no-op).

create table if not exists leads (
  id             bigserial   primary key,
  created_at     timestamptz not null default now(),
  name           text        not null,
  email          text        not null,
  company        text,
  preferred_date text,                 -- free-form availability, kept as text
  consent        boolean     not null,
  source_page    text
);
