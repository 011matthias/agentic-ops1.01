-- Book-a-demo lead store (Neon Postgres). Keep the Neon project in an EU region.
--
-- YOU MUST RUN THIS. api/book-demo.js contains no DDL of any kind: it only
-- INSERTs. An earlier version of this header claimed the function ran the
-- equivalent CREATE TABLE IF NOT EXISTS on cold start, which was never true and
-- would leave a fresh Neon project 500ing on every submission with the reader
-- believing the step was optional. Corrected 2026-09-09 after re-reading the
-- function; it matters for the Neon migration in TARGET-ARCHITECTURE P5, where
-- a new database gets provisioned and this file is the only bootstrap.
--
-- Run once in the Neon SQL Editor, then point LEADS_DATABASE_URL at an
-- INSERT-only role (DATABASE_URL is the fallback).

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
