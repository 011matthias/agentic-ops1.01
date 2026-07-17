/**
 * Seed Meji Media as the first real portal client.
 *
 * Creates: user -> client -> project ("meji-media") -> resources (5 docs) -> milestones (3)
 *
 * Usage: cd platform && npx tsx scripts/seed-meji-client.ts
 *
 * Requires DATABASE_URL in .env.local
 *
 * Safe to re-run: checks for existing records before creating.
 */
import dotenv from "dotenv"
dotenv.config({ path: ".env.local" })
import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import { eq } from "drizzle-orm"
import * as schema from "../src/lib/schema"

const sql = neon(process.env.DATABASE_URL!)
const db = drizzle(sql, { schema })

const CLIENT_EMAIL = "enquire@christmasofficeparty.co.uk"
const COMPANY_NAME = "Meji Media"
const PROJECT_NAME = "meji-media" // Must match registry.ts projectSlug

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

const MILESTONES = [
  {
    title: "A1 - Enquiry Follow-Up Sequence",
    description: "Automated email sequence triggered by new enquiries",
    status: "done" as const,
  },
  {
    title: "A2 - Reply Detection & Stop",
    description: "Detect client replies and stop follow-up sequence",
    status: "in-progress" as const,
  },
  {
    title: "A3 - Scheduled Follow-Up Steps",
    description: "Timed follow-up actions after initial sequence",
    status: "in-progress" as const,
  },
]

async function main() {
  console.log("=== Seeding Meji Media as portal client ===\n")

  // 1. User
  let userId: string
  const [existingUser] = await db
    .select()
    .from(schema.users)
    .where(eq(schema.users.email, CLIENT_EMAIL))
    .limit(1)

  if (existingUser) {
    userId = existingUser.id
    console.log(`User exists: ${existingUser.email} (${userId})`)
    if (existingUser.role !== "client") {
      await db
        .update(schema.users)
        .set({ role: "client", emailVerified: new Date() })
        .where(eq(schema.users.id, userId))
      console.log(`  Updated role to "client"`)
    }
  } else {
    const [newUser] = await db
      .insert(schema.users)
      .values({
        email: CLIENT_EMAIL,
        name: COMPANY_NAME,
        role: "client",
        emailVerified: new Date(),
      })
      .returning()
    userId = newUser.id
    console.log(`Created user: ${CLIENT_EMAIL} (${userId})`)
  }

  // 2. Client
  let clientId: string
  const [existingClient] = await db
    .select()
    .from(schema.clients)
    .where(eq(schema.clients.userId, userId))
    .limit(1)

  if (existingClient) {
    clientId = existingClient.id
    console.log(`Client exists: ${existingClient.companyName} (${clientId})`)
  } else {
    const [newClient] = await db
      .insert(schema.clients)
      .values({
        userId,
        companyName: COMPANY_NAME,
        status: "active",
      })
      .returning()
    clientId = newClient.id
    console.log(`Created client: ${COMPANY_NAME} (${clientId})`)
  }

  // 3. Project (name MUST be "meji-media" to match module registry)
  let projectId: string
  const existingProject = await db.query.projects.findFirst({
    where: eq(schema.projects.name, PROJECT_NAME),
  })

  if (existingProject) {
    projectId = existingProject.id
    console.log(`Project exists: ${existingProject.name} (${projectId})`)
  } else {
    const [newProject] = await db
      .insert(schema.projects)
      .values({
        clientId,
        name: PROJECT_NAME,
        description: "Enquiry follow-up automation system for Christmas party venue bookings",
        orchestrator: "make",
        status: "active",
        startDate: new Date("2026-02-15"),
      })
      .returning()
    projectId = newProject.id
    console.log(`Created project: ${PROJECT_NAME} (${projectId})`)
  }

  // 4. Resources
  const existingResources = await db.query.clientResources.findMany({
    where: eq(schema.clientResources.clientId, clientId),
  })

  if (existingResources.length > 0) {
    console.log(`Resources exist: ${existingResources.length} already seeded`)
  } else {
    for (const resource of RESOURCES) {
      const [created] = await db
        .insert(schema.clientResources)
        .values({
          clientId,
          projectId,
          ...resource,
          published: true,
        })
        .returning()
      console.log(`  Resource: ${created.title}`)
    }
    console.log(`Created ${RESOURCES.length} resources`)
  }

  // 5. Milestones
  const existingMilestones = await db.query.milestones.findMany({
    where: eq(schema.milestones.projectId, projectId),
  })

  if (existingMilestones.length > 0) {
    console.log(`Milestones exist: ${existingMilestones.length} already seeded`)
  } else {
    for (const milestone of MILESTONES) {
      const [created] = await db
        .insert(schema.milestones)
        .values({
          projectId,
          title: milestone.title,
          description: milestone.description,
          status: milestone.status,
          completedAt: milestone.status === "done" ? new Date("2026-03-19") : undefined,
        })
        .returning()
      console.log(`  Milestone: ${created.title} [${milestone.status}]`)
    }
    console.log(`Created ${MILESTONES.length} milestones`)
  }

  console.log("\n=== Done ===")
  console.log(`Client: ${COMPANY_NAME} (${clientId})`)
  console.log(`Project: ${PROJECT_NAME} (${projectId})`)
  console.log(`Resources: ${RESOURCES.length}`)
  console.log(`Milestones: ${MILESTONES.length}`)
  console.log(`\nWebhook endpoint ready: POST /api/modules/meji-enquiry-followup`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
