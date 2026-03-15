import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import * as schema from "./schema"

// Provide a placeholder URL at build time so neon() doesn't throw.
// At runtime on Vercel, DATABASE_URL is set and the real connection is used.
// Actual queries will fail at runtime if DATABASE_URL is missing — which is
// the correct behavior (explicit error at query time, not at build time).
const sql = neon(process.env.DATABASE_URL ?? "postgresql://user:password@localhost/placeholder")

export const db = drizzle(sql, { schema })
