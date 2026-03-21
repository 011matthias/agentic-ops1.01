import {
  pgTable,
  pgEnum,
  text,
  timestamp,
  integer,
  primaryKey,
  uuid,
  boolean,
} from "drizzle-orm/pg-core"
import { relations } from "drizzle-orm"
import type { AdapterAccountType } from "next-auth/adapters"

// ── Auth.js required tables ──────────────────────────────────────────────────

export const users = pgTable("user", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),
  name: text("name"),
  email: text("email").unique(),
  emailVerified: timestamp("emailVerified", { mode: "date" }),
  image: text("image"),
  role: text("role").$type<"admin" | "client" | "prospect">().default("prospect"),
  createdAt: timestamp("createdAt", { mode: "date" }).defaultNow(),
})

export const accounts = pgTable(
  "account",
  {
    userId: text("userId")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    type: text("type").$type<AdapterAccountType>().notNull(),
    provider: text("provider").notNull(),
    providerAccountId: text("providerAccountId").notNull(),
    refresh_token: text("refresh_token"),
    access_token: text("access_token"),
    expires_at: integer("expires_at"),
    token_type: text("token_type"),
    scope: text("scope"),
    id_token: text("id_token"),
    session_state: text("session_state"),
  },
  (account) => ({
    compoundKey: primaryKey({
      columns: [account.provider, account.providerAccountId],
    }),
  })
)

export const sessions = pgTable("session", {
  sessionToken: text("sessionToken").primaryKey(),
  userId: text("userId")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  expires: timestamp("expires", { mode: "date" }).notNull(),
})

export const verificationTokens = pgTable(
  "verificationToken",
  {
    identifier: text("identifier").notNull(),
    token: text("token").notNull(),
    expires: timestamp("expires", { mode: "date" }).notNull(),
  },
  (vt) => ({
    compoundKey: primaryKey({ columns: [vt.identifier, vt.token] }),
  })
)

// ── Business tables ──────────────────────────────────────────────────────────

export const clients = pgTable("client", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),
  userId: text("userId")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  companyName: text("companyName").notNull(),
  status: text("status").$type<"active" | "inactive">().default("active"),
  createdAt: timestamp("createdAt", { mode: "date" }).defaultNow(),
})

// ── Portal tables ─────────────────────────────────────────────────────────────

export const projects = pgTable("projects", {
  id: uuid("id").defaultRandom().primaryKey(),
  clientId: text("client_id")
    .references(() => clients.id, { onDelete: "cascade" })
    .notNull(),
  name: text("name").notNull(),
  description: text("description"),
  status: text("status", { enum: ["active", "paused", "complete"] })
    .default("active")
    .notNull(),
  orchestrator: text("orchestrator", {
    enum: ["make", "n8n", "trigger-dev", "fastapi"],
  }),
  startDate: timestamp("start_date", { mode: "date" }),
  targetDate: timestamp("target_date", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const milestones = pgTable("milestones", {
  id: uuid("id").defaultRandom().primaryKey(),
  projectId: uuid("project_id")
    .references(() => projects.id, { onDelete: "cascade" })
    .notNull(),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status", { enum: ["pending", "in-progress", "done"] })
    .default("pending")
    .notNull(),
  dueDate: timestamp("due_date", { mode: "date" }),
  completedAt: timestamp("completed_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const messages = pgTable("messages", {
  id: uuid("id").defaultRandom().primaryKey(),
  clientId: text("client_id")
    .references(() => clients.id, { onDelete: "cascade" })
    .notNull(),
  authorId: text("author_id").references(() => users.id, {
    onDelete: "set null",
  }),
  authorRole: text("author_role", { enum: ["admin", "client"] }).notNull(),
  body: text("body").notNull(),
  readAt: timestamp("read_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const files = pgTable("files", {
  id: uuid("id").defaultRandom().primaryKey(),
  clientId: text("client_id")
    .references(() => clients.id, { onDelete: "cascade" })
    .notNull(),
  projectId: uuid("project_id").references(() => projects.id, {
    onDelete: "set null",
  }),
  uploadedBy: text("uploaded_by").references(() => users.id, {
    onDelete: "set null",
  }),
  filename: text("filename").notNull(),
  url: text("url").notNull(),
  sizeBytes: integer("size_bytes"),
  mimeType: text("mime_type"),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const clientResources = pgTable("client_resources", {
  id: uuid("id").defaultRandom().primaryKey(),
  clientId: text("client_id")
    .references(() => clients.id, { onDelete: "cascade" })
    .notNull(),
  projectId: uuid("project_id").references(() => projects.id, { onDelete: "set null" }),
  title: text("title").notNull(),
  description: text("description"),
  type: text("type", { enum: ["html_page", "video", "link", "file"] }).notNull(),
  url: text("url").notNull(),
  category: text("category", { enum: ["documentation", "setup", "guides", "videos"] }).notNull(),
  sortOrder: integer("sort_order").default(0).notNull(),
  published: boolean("published").default(false).notNull(),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "date" }).defaultNow().notNull(),
})

// ── Module execution tables ──────────────────────────────────────────────────

export const moduleExecutions = pgTable("module_executions", {
  id: uuid("id").defaultRandom().primaryKey(),
  projectId: uuid("project_id")
    .references(() => projects.id, { onDelete: "cascade" })
    .notNull(),
  moduleName: text("module_name").notNull(),
  status: text("status", { enum: ["success", "error", "partial"] }).notNull(),
  itemCount: integer("item_count").default(0).notNull(),
  durationMs: integer("duration_ms"),
  metadata: text("metadata"),
  executedAt: timestamp("executed_at", { mode: "date" }).notNull(),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

// ── Purchase tables ───────────────────────────────────────────────────────────

export const products = pgTable("products", {
  id: uuid("id").defaultRandom().primaryKey(),
  catalogSlug: text("catalog_slug").notNull().unique(),
  name: text("name").notNull(),
  priceUsd: integer("price_usd").notNull(), // cents, e.g. 4900 for $49
  stripePriceId: text("stripe_price_id"), // set after Stripe product created
  active: boolean("active").default(true).notNull(),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const purchases = pgTable("purchases", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: text("user_id").references(() => users.id, { onDelete: "set null" }),
  productId: uuid("product_id")
    .references(() => products.id)
    .notNull(),
  stripeSessionId: text("stripe_session_id").unique(),
  status: text("status", { enum: ["pending", "complete", "refunded"] })
    .default("pending")
    .notNull(),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

// ── Autopilot tables ─────────────────────────────────────────────────────────

export const autopilotBuildStatusEnum = pgEnum("autopilot_build_status", [
  "pending",
  "running",
  "waiting",
  "completed",
  "failed",
  "cancelled",
])

export const autopilotPhaseNameEnum = pgEnum("autopilot_phase_name", [
  "plan",
  "implement",
  "test_local",
  "test_dev",
  "document",
  "deploy",
  "verify",
  "complete",
])

export const autopilotBuilds = pgTable("autopilot_builds", {
  id: uuid("id").defaultRandom().primaryKey(),
  projectId: uuid("project_id")
    .references(() => projects.id, { onDelete: "cascade" })
    .notNull(),
  specId: text("spec_id").notNull(),
  status: autopilotBuildStatusEnum("status").default("pending").notNull(),
  directive: text("directive").notNull(),
  currentPhase: autopilotPhaseNameEnum("current_phase"),
  triggerRunId: text("trigger_run_id"),
  error: text("error"),
  startedAt: timestamp("started_at", { mode: "date" }),
  completedAt: timestamp("completed_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { mode: "date" }).defaultNow().notNull(),
})

export const autopilotPhases = pgTable("autopilot_phases", {
  id: uuid("id").defaultRandom().primaryKey(),
  buildId: uuid("build_id")
    .references(() => autopilotBuilds.id, { onDelete: "cascade" })
    .notNull(),
  name: autopilotPhaseNameEnum("name").notNull(),
  status: text("status", {
    enum: ["pending", "running", "waiting", "passed", "failed", "skipped"],
  })
    .default("pending")
    .notNull(),
  output: text("output"),
  error: text("error"),
  startedAt: timestamp("started_at", { mode: "date" }),
  completedAt: timestamp("completed_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const autopilotApprovals = pgTable("autopilot_approvals", {
  id: uuid("id").defaultRandom().primaryKey(),
  buildId: uuid("build_id")
    .references(() => autopilotBuilds.id, { onDelete: "cascade" })
    .notNull(),
  phase: autopilotPhaseNameEnum("phase").notNull(),
  status: text("status", {
    enum: ["pending", "approved", "rejected", "timed_out"],
  })
    .default("pending")
    .notNull(),
  waitpointTokenId: text("waitpoint_token_id"),
  reviewerId: text("reviewer_id").references(() => users.id, {
    onDelete: "set null",
  }),
  comments: text("comments"),
  resolvedAt: timestamp("resolved_at", { mode: "date" }),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

export const autopilotLogs = pgTable("autopilot_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  buildId: uuid("build_id")
    .references(() => autopilotBuilds.id, { onDelete: "cascade" })
    .notNull(),
  phase: autopilotPhaseNameEnum("phase"),
  level: text("level", { enum: ["info", "warn", "error"] })
    .default("info")
    .notNull(),
  message: text("message").notNull(),
  metadata: text("metadata"),
  createdAt: timestamp("created_at", { mode: "date" }).defaultNow().notNull(),
})

// ── Relations ─────────────────────────────────────────────────────────────────

export const clientsRelations = relations(clients, ({ many }) => ({
  projects: many(projects),
  messages: many(messages),
  files: many(files),
  resources: many(clientResources),
}))

export const projectsRelations = relations(projects, ({ one, many }) => ({
  client: one(clients, { fields: [projects.clientId], references: [clients.id] }),
  milestones: many(milestones),
  moduleExecutions: many(moduleExecutions),
  autopilotBuilds: many(autopilotBuilds),
}))

export const milestonesRelations = relations(milestones, ({ one }) => ({
  project: one(projects, {
    fields: [milestones.projectId],
    references: [projects.id],
  }),
}))

export const messagesRelations = relations(messages, ({ one }) => ({
  client: one(clients, {
    fields: [messages.clientId],
    references: [clients.id],
  }),
}))

export const filesRelations = relations(files, ({ one }) => ({
  client: one(clients, { fields: [files.clientId], references: [clients.id] }),
  project: one(projects, {
    fields: [files.projectId],
    references: [projects.id],
  }),
}))

export const clientResourcesRelations = relations(clientResources, ({ one }) => ({
  client: one(clients, { fields: [clientResources.clientId], references: [clients.id] }),
  project: one(projects, { fields: [clientResources.projectId], references: [projects.id] }),
}))

export const moduleExecutionsRelations = relations(moduleExecutions, ({ one }) => ({
  project: one(projects, {
    fields: [moduleExecutions.projectId],
    references: [projects.id],
  }),
}))

export const productsRelations = relations(products, ({ many }) => ({
  purchases: many(purchases),
}))

export const purchasesRelations = relations(purchases, ({ one }) => ({
  product: one(products, {
    fields: [purchases.productId],
    references: [products.id],
  }),
}))

export const autopilotBuildsRelations = relations(autopilotBuilds, ({ one, many }) => ({
  project: one(projects, {
    fields: [autopilotBuilds.projectId],
    references: [projects.id],
  }),
  phases: many(autopilotPhases),
  approvals: many(autopilotApprovals),
  logs: many(autopilotLogs),
}))

export const autopilotPhasesRelations = relations(autopilotPhases, ({ one }) => ({
  build: one(autopilotBuilds, {
    fields: [autopilotPhases.buildId],
    references: [autopilotBuilds.id],
  }),
}))

export const autopilotApprovalsRelations = relations(autopilotApprovals, ({ one }) => ({
  build: one(autopilotBuilds, {
    fields: [autopilotApprovals.buildId],
    references: [autopilotBuilds.id],
  }),
  reviewer: one(users, {
    fields: [autopilotApprovals.reviewerId],
    references: [users.id],
  }),
}))

export const autopilotLogsRelations = relations(autopilotLogs, ({ one }) => ({
  build: one(autopilotBuilds, {
    fields: [autopilotLogs.buildId],
    references: [autopilotBuilds.id],
  }),
}))
