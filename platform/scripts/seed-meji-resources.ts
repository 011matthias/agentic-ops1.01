/**
 * Seed Meji Media documentation resources into the portal.
 *
 * Usage: cd platform && npx tsx scripts/seed-meji-resources.ts
 *
 * Requires DATABASE_URL in .env.local
 */
import dotenv from "dotenv"
dotenv.config({ path: ".env.local" })
import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import { eq } from "drizzle-orm"
import * as schema from "../src/lib/schema"

const sql = neon(process.env.DATABASE_URL!)
const db = drizzle(sql, { schema })

const RESOURCES = [
  {
    title: "Automation Hub",
    description: "Overview of all automations, status dashboard, and quick links.",
    type: "html_page" as const,
    url: "/docs/meji-media/",
    category: "documentation" as const,
    sortOrder: 0,
  },
  {
    title: "System Overview",
    description: "Architecture diagram showing how all 4 automations connect.",
    type: "html_page" as const,
    url: "/docs/meji-media/system-overview",
    category: "documentation" as const,
    sortOrder: 1,
  },
  {
    title: "Complete Guide",
    description: "Everything you need to know about your automation system.",
    type: "html_page" as const,
    url: "/docs/meji-media/guide",
    category: "guides" as const,
    sortOrder: 0,
  },
  {
    title: "A/B Testing",
    description: "How to split-test email templates for better reply rates.",
    type: "html_page" as const,
    url: "/docs/meji-media/ab-testing",
    category: "guides" as const,
    sortOrder: 1,
  },
  {
    title: "Lead Scoring",
    description: "How enquiries are scored and prioritized automatically.",
    type: "html_page" as const,
    url: "/docs/meji-media/lead-scoring",
    category: "guides" as const,
    sortOrder: 2,
  },
]

async function main() {
  // Find target client (pass client name as arg, or defaults to first available)
  const targetName = process.argv[2]?.toLowerCase()
  const allClients = await db.query.clients.findMany()

  if (allClients.length === 0) {
    console.error("No clients found in database.")
    process.exit(1)
  }

  const meji = targetName
    ? allClients.find((c) => c.companyName.toLowerCase().includes(targetName))
    : allClients[0]

  if (!meji) {
    console.log("Available clients:", allClients.map((c) => `${c.id}: ${c.companyName}`))
    console.error(`No client matching "${targetName}" found.`)
    process.exit(1)
  }

  console.log(`Target client: ${meji.companyName} (${meji.id})`)

  // Check for existing resources
  const existing = await db.query.clientResources.findMany({
    where: eq(schema.clientResources.clientId, meji.id),
  })

  if (existing.length > 0) {
    console.log(`Client already has ${existing.length} resources:`)
    existing.forEach((r) => console.log(`  - ${r.title} (${r.published ? "published" : "draft"})`))
    console.log("Skipping seed to avoid duplicates. Delete existing resources first if you want to re-seed.")
    process.exit(0)
  }

  // Insert resources
  for (const resource of RESOURCES) {
    const [created] = await db
      .insert(schema.clientResources)
      .values({
        clientId: meji.id,
        ...resource,
        published: true,
      })
      .returning()

    console.log(`Created: ${created.title} (${created.id})`)
  }

  console.log(`\nDone. ${RESOURCES.length} resources seeded for ${meji.companyName}.`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
