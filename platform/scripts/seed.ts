/**
 * Database seed script for local development.
 *
 * Usage:
 *   cd platform && npx tsx scripts/seed.ts
 *
 * Requires DATABASE_URL in environment (copy from .env.local or Vercel dashboard).
 * Safe to re-run — uses upsert (no duplicate errors).
 */

import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import { eq } from "drizzle-orm"
import * as schema from "../src/lib/schema"

const { users, clients } = schema

async function main() {
  const dbUrl = process.env.DATABASE_URL
  if (!dbUrl) {
    console.error("ERROR: DATABASE_URL not set. Copy from .env.local or Vercel dashboard.")
    process.exit(1)
  }

  const sql = neon(dbUrl)
  const db = drizzle(sql, { schema })

  console.log("Seeding database...")

  // Admin user (UnpausAI team)
  const adminEmail = "dev@unpauseai.com"
  const existingAdmin = await db.query.users.findFirst({
    where: eq(users.email, adminEmail),
  })

  let adminId: string
  if (existingAdmin) {
    adminId = existingAdmin.id
    console.log(`  [skip] Admin user already exists: ${adminEmail}`)
  } else {
    const [admin] = await db
      .insert(users)
      .values({ name: "Dev Admin", email: adminEmail, role: "admin" })
      .returning()
    adminId = admin.id
    console.log(`  [+] Created admin user: ${adminEmail}`)
  }

  // Test client user
  const clientEmail = "test@client.com"
  const existingClient = await db.query.users.findFirst({
    where: eq(users.email, clientEmail),
  })

  let clientUserId: string
  if (existingClient) {
    clientUserId = existingClient.id
    console.log(`  [skip] Client user already exists: ${clientEmail}`)
  } else {
    const [clientUser] = await db
      .insert(users)
      .values({ name: "Test Client", email: clientEmail, role: "client" })
      .returning()
    clientUserId = clientUser.id
    console.log(`  [+] Created client user: ${clientEmail}`)
  }

  // Client record for test client
  const existingClientRecord = await db.query.clients.findFirst({
    where: eq(clients.userId, clientUserId),
  })

  if (existingClientRecord) {
    console.log(`  [skip] Client record already exists for ${clientEmail}`)
  } else {
    await db.insert(clients).values({
      userId: clientUserId,
      companyName: "Test Company Ltd",
      status: "active",
    })
    console.log(`  [+] Created client record: Test Company Ltd`)
  }

  // Test prospect user (pending approval)
  const prospectEmail = "prospect@test.com"
  const existingProspect = await db.query.users.findFirst({
    where: eq(users.email, prospectEmail),
  })

  if (existingProspect) {
    console.log(`  [skip] Prospect user already exists: ${prospectEmail}`)
  } else {
    await db
      .insert(users)
      .values({ name: "Test Prospect", email: prospectEmail, role: "prospect" })
    console.log(`  [+] Created prospect user: ${prospectEmail}`)
  }

  console.log("\nSeed complete.")
  console.log(`  Admin:    ${adminEmail}     (role: admin)`)
  console.log(`  Client:   ${clientEmail}    (role: client)`)
  console.log(`  Prospect: ${prospectEmail}  (role: prospect)`)
  console.log("\nTo sign in: use /login with magic link or OAuth.")
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
