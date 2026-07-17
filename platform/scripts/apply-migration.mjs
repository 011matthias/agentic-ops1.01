#!/usr/bin/env node
// Apply a single Drizzle migration file from ./drizzle to Neon.
//
// Usage:
//   cd platform
//   node --env-file=.env.local scripts/apply-migration.mjs 0006_doc_comments.sql
//
// Why this exists: this repo's prior migrations 0001..0005 were applied via
// `drizzle-kit push` (schema-diff sync). Push has too wide a blast radius for
// a one-table addition — it would apply any schema.ts drift across all tables.
// This runner is surgical: read one .sql file, execute it inside a transaction
// against Neon, verify, exit. Idempotent SQL (CREATE IF NOT EXISTS, FK in
// DO $$ EXCEPTION END $$) means it's safe to re-run.
//
// Connection: prefers DATABASE_URL_UNPOOLED (direct endpoint, required for DDL
// in plpgsql DO blocks), falls back to DATABASE_URL.

import { Pool } from "@neondatabase/serverless"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, resolve } from "node:path"

const __dirname = dirname(fileURLToPath(import.meta.url))
const MIGRATIONS_DIR = resolve(__dirname, "..", "drizzle")

async function main() {
  const arg = process.argv[2]
  if (!arg) {
    console.error("Usage: node scripts/apply-migration.mjs <migration-filename>")
    process.exit(2)
  }
  const path = resolve(MIGRATIONS_DIR, arg)
  let sql
  try {
    sql = readFileSync(path, "utf8")
  } catch (e) {
    console.error(`Cannot read migration file ${path}: ${e.message}`)
    process.exit(2)
  }

  const connStr = process.env.DATABASE_URL_UNPOOLED || process.env.DATABASE_URL
  if (!connStr) {
    console.error("Neither DATABASE_URL_UNPOOLED nor DATABASE_URL is set.")
    process.exit(2)
  }

  console.log(`Applying drizzle/${arg} to Neon...`)
  const pool = new Pool({ connectionString: connStr })
  const client = await pool.connect()
  try {
    await client.query("BEGIN")
    await client.query(sql)
    await client.query("COMMIT")
    console.log("  Migration applied.")
  } catch (e) {
    await client.query("ROLLBACK").catch(() => {})
    console.error(`  FAILED: ${e.message}`)
    client.release()
    await pool.end()
    process.exit(1)
  }

  // Verification — best-effort, only tries the table from this specific migration if present.
  try {
    if (arg.includes("doc_comments")) {
      const exists = await client.query("SELECT to_regclass('doc_comments') AS rel")
      console.log(`  to_regclass('doc_comments') = ${exists.rows[0].rel}`)
      const idx = await client.query(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'doc_comments' ORDER BY indexname"
      )
      console.log(`  indexes: ${idx.rows.map((r) => r.indexname).join(", ") || "(none)"}`)
    }
  } catch (e) {
    console.warn(`  verification query warning: ${e.message}`)
  } finally {
    client.release()
    await pool.end()
  }
  console.log("Done.")
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
