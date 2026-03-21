import { db } from "@/lib/db"
import {
  clients,
  projects,
  messages,
  users,
  files,
  clientResources,
  moduleExecutions,
  products,
  purchases,
  autopilotBuilds,
} from "@/lib/schema"
import { count, max, sql } from "drizzle-orm"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"

export const metadata = { title: "Architecture — Admin" }

// ── Types ────────────────────────────────────────────────────────────────────

type PageEntry = {
  route: string
  label: string
  area: "portal" | "admin" | "api" | "public"
  reads: string[]
  writes: string[]
  status: "live" | "stubbed" | "planned"
  notes?: string
}

type DataFlow = {
  from: string
  arrow: string
  to: string
  description: string
}

// ── Static data ──────────────────────────────────────────────────────────────

const pages: PageEntry[] = [
  // Public
  { route: "/", label: "Homepage", area: "public", reads: [], writes: [], status: "live" },
  { route: "/login", label: "Login", area: "public", reads: ["users"], writes: ["users", "sessions"], status: "live" },
  { route: "/services", label: "Services", area: "public", reads: [], writes: [], status: "live" },
  { route: "/contact", label: "Contact", area: "public", reads: [], writes: [], status: "live" },
  { route: "/proposals/[slug]", label: "Proposals", area: "public", reads: [], writes: [], status: "live", notes: "SSG from markdown" },
  { route: "/buy/[slug]", label: "Buy Page", area: "public", reads: ["products"], writes: ["purchases"], status: "live", notes: "Stripe checkout" },

  // Portal (client-facing)
  { route: "/portal", label: "Dashboard", area: "portal", reads: ["clients", "projects", "milestones", "messages"], writes: [], status: "live" },
  { route: "/portal/automations", label: "Automations", area: "portal", reads: ["projects", "milestones", "moduleExecutions"], writes: [], status: "live", notes: "Shows execution stats" },
  { route: "/portal/messages", label: "Messages", area: "portal", reads: ["messages"], writes: ["messages"], status: "live" },
  { route: "/portal/files", label: "Files", area: "portal", reads: ["files"], writes: [], status: "live" },
  { route: "/portal/resources", label: "Resources", area: "portal", reads: ["clientResources"], writes: [], status: "live" },
  { route: "/portal/reports", label: "Reports", area: "portal", reads: [], writes: [], status: "stubbed", notes: "Page exists, no data" },
  { route: "/portal/settings", label: "Settings", area: "portal", reads: ["users"], writes: [], status: "live" },

  // Admin
  { route: "/admin", label: "Dashboard", area: "admin", reads: ["clients", "projects", "messages", "users", "milestones"], writes: [], status: "live" },
  { route: "/admin/clients", label: "Clients", area: "admin", reads: ["clients", "projects", "messages"], writes: [], status: "live" },
  { route: "/admin/clients/[id]", label: "Client Detail", area: "admin", reads: ["clients", "projects", "messages", "files", "clientResources", "purchases"], writes: ["projects", "messages", "clientResources"], status: "live", notes: "6 tabs: Overview, Projects, Messages, Files, Resources, Purchases" },
  { route: "/admin/projects", label: "Projects", area: "admin", reads: ["projects", "milestones", "clients"], writes: [], status: "live" },
  { route: "/admin/projects/[id]", label: "Project Detail", area: "admin", reads: ["projects", "milestones"], writes: ["milestones"], status: "live" },
  { route: "/admin/users", label: "Users", area: "admin", reads: ["users"], writes: ["users", "clients"], status: "live", notes: "Invite + role management" },
  { route: "/admin/messages", label: "Messages", area: "admin", reads: ["messages", "clients"], writes: ["messages"], status: "live" },
  { route: "/admin/builds", label: "Builds", area: "admin", reads: ["autopilotBuilds"], writes: [], status: "live", notes: "Autopilot monitoring" },
  { route: "/admin/revenue", label: "Revenue", area: "admin", reads: ["products", "purchases"], writes: ["products"], status: "live" },
  { route: "/admin/architecture", label: "Architecture", area: "admin", reads: ["all tables"], writes: [], status: "live", notes: "This page" },

  // API endpoints
  { route: "/api/modules/[module]", label: "Module Webhook", area: "api", reads: ["projects"], writes: ["moduleExecutions"], status: "live", notes: "Orchestrators POST here" },
  { route: "/api/admin/invite", label: "Invite Client", area: "api", reads: [], writes: ["users", "clients"], status: "live", notes: "Sends magic link email" },
  { route: "/api/admin/projects", label: "Projects CRUD", area: "api", reads: [], writes: ["projects"], status: "live" },
  { route: "/api/admin/milestones", label: "Milestones CRUD", area: "api", reads: [], writes: ["milestones"], status: "live" },
  { route: "/api/admin/resources", label: "Resources CRUD", area: "api", reads: [], writes: ["clientResources"], status: "live" },
  { route: "/api/admin/messages", label: "Messages", area: "api", reads: ["messages"], writes: ["messages"], status: "live" },
  { route: "/api/checkout", label: "Stripe Checkout", area: "api", reads: ["products"], writes: ["purchases"], status: "live" },
  { route: "/api/webhooks/stripe", label: "Stripe Webhook", area: "api", reads: [], writes: ["purchases"], status: "live" },
]

const dataFlows: DataFlow[] = [
  {
    from: "Make.com / n8n / Trigger.dev",
    arrow: "POST /api/modules/{name}",
    to: "module_executions table",
    description: "Orchestrators push execution results after each run",
  },
  {
    from: "module_executions",
    arrow: "queried by",
    to: "/portal/automations",
    description: "Client sees status badge, run count, last execution time",
  },
  {
    from: "Admin creates project",
    arrow: "/api/admin/projects",
    to: "projects table",
    description: "Client sees project in portal dashboard + automations page",
  },
  {
    from: "Admin invites client",
    arrow: "/api/admin/invite",
    to: "users + clients tables",
    description: "Client gets magic link email, logs in, sees portal",
  },
  {
    from: "Admin publishes resource",
    arrow: "/api/admin/resources",
    to: "client_resources table",
    description: "Client sees docs, videos, links in /portal/resources",
  },
  {
    from: "Stripe webhook",
    arrow: "/api/webhooks/stripe",
    to: "purchases table",
    description: "Payment confirmed, purchase status updated",
  },
]

const areaLabel: Record<string, string> = {
  public: "Public Pages",
  portal: "Client Portal",
  admin: "Admin Panel",
  api: "API Endpoints",
}

const areaOrder = ["public", "portal", "admin", "api"] as const

const statusVariant: Record<string, "success" | "warning" | "default"> = {
  live: "success",
  stubbed: "warning",
  planned: "default",
}

// ── Milestones ───────────────────────────────────────────────────────────────

type Milestone = {
  number: number
  title: string
  outcome: string
  status: "done" | "current" | "upcoming"
  items: { label: string; done: boolean }[]
}

const roadmapMilestones: Milestone[] = [
  {
    number: 1,
    title: "Foundation Verified",
    outcome: "Admin can log in and see everything working. Architecture map gives permanent transparency.",
    status: "current",
    items: [
      { label: "Auth works (admin via Google)", done: true },
      { label: "Module execution tracking (schema + API + portal)", done: true },
      { label: "Architecture map admin page", done: true },
      { label: "Verify end-to-end: admin + portal views", done: false },
    ],
  },
  {
    number: 2,
    title: "First Real Client Live",
    outcome: "First paying client using the portal with real, live automation data.",
    status: "upcoming",
    items: [
      { label: "Wire Make.com scenario to POST execution data", done: false },
      { label: "Create Meji Media client account (invite)", done: false },
      { label: "Seed project + resources via admin UI", done: false },
      { label: "Client logs in, sees live data + docs", done: false },
    ],
  },
  {
    number: 3,
    title: "Funnel + Onboarding",
    outcome: "New prospects can find you, request service, and get onboarded.",
    status: "upcoming",
    items: [
      { label: "Proposal pages: 'Get Started' CTA", done: false },
      { label: "Portal first-login onboarding", done: false },
      { label: "Outbound: proposal -> send -> sign -> invite", done: false },
    ],
  },
  {
    number: 4,
    title: "Self-Service + Payments",
    outcome: "Someone can buy an automation and start using it without manual admin work.",
    status: "upcoming",
    items: [
      { label: "Stripe -> auto-deploy template -> portal auto-activate", done: false },
      { label: "Buy page polish (real output, pricing)", done: false },
    ],
  },
  {
    number: 5,
    title: "Agentic Story",
    outcome: "The unique selling point is visible on the public site.",
    status: "upcoming",
    items: [
      { label: "Homepage 'How it works' section", done: false },
      { label: "About page: AI-assisted delivery model", done: false },
      { label: "Portal 'Autopilot activity' feed", done: false },
    ],
  },
]

const milestoneStatusVariant: Record<string, "success" | "warning" | "default"> = {
  done: "success",
  current: "warning",
  upcoming: "default",
}

// ── Page component ───────────────────────────────────────────────────────────

export default async function ArchitecturePage() {
  // ── Live health check queries ────────────────────────────────────────────

  const [userCounts] = await db
    .select({
      total: count(users.id),
      admins: count(sql`CASE WHEN ${users.role} = 'admin' THEN 1 END`),
      clientUsers: count(sql`CASE WHEN ${users.role} = 'client' THEN 1 END`),
      prospects: count(sql`CASE WHEN ${users.role} = 'prospect' THEN 1 END`),
    })
    .from(users)

  const [clientCounts] = await db
    .select({
      total: count(clients.id),
      active: count(sql`CASE WHEN ${clients.status} = 'active' THEN 1 END`),
    })
    .from(clients)

  const [projectCounts] = await db
    .select({
      total: count(projects.id),
      active: count(sql`CASE WHEN ${projects.status} = 'active' THEN 1 END`),
      paused: count(sql`CASE WHEN ${projects.status} = 'paused' THEN 1 END`),
      complete: count(sql`CASE WHEN ${projects.status} = 'complete' THEN 1 END`),
    })
    .from(projects)

  const [execCounts] = await db
    .select({
      total: count(moduleExecutions.id),
      lastAt: max(moduleExecutions.executedAt),
    })
    .from(moduleExecutions)

  const [msgCount] = await db.select({ total: count(messages.id) }).from(messages)
  const [fileCount] = await db.select({ total: count(files.id) }).from(files)
  const [resourceCount] = await db.select({ total: count(clientResources.id) }).from(clientResources)
  const [productCount] = await db.select({ total: count(products.id) }).from(products)
  const [purchaseCount] = await db.select({ total: count(purchases.id) }).from(purchases)
  const [buildCount] = await db.select({ total: count(autopilotBuilds.id) }).from(autopilotBuilds)

  const envVars = [
    { name: "DATABASE_URL", set: !!process.env.DATABASE_URL },
    { name: "AUTH_SECRET", set: !!process.env.AUTH_SECRET },
    { name: "AUTH_GOOGLE_ID", set: !!process.env.AUTH_GOOGLE_ID },
    { name: "AUTH_GOOGLE_SECRET", set: !!process.env.AUTH_GOOGLE_SECRET },
    { name: "RESEND_API_KEY", set: !!process.env.RESEND_API_KEY },
    { name: "STRIPE_SECRET_KEY", set: !!process.env.STRIPE_SECRET_KEY },
    { name: "STRIPE_WEBHOOK_SECRET", set: !!process.env.STRIPE_WEBHOOK_SECRET },
    { name: "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", set: !!process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY },
  ]

  function formatLastAt(d: Date | null): string {
    if (!d) return "never"
    const diffMs = Date.now() - d.getTime()
    const mins = Math.floor(diffMs / 60000)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <PageHeader
        title="Architecture"
        subtitle="Platform map, data flows, live health, and roadmap. Everything in one place."
      />

      {/* ── Section A: Live Health Check ──────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Live Health
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <HealthCard
            label="Users"
            value={userCounts.total}
            detail={`${userCounts.admins} admin, ${userCounts.clientUsers} client, ${userCounts.prospects} prospect`}
          />
          <HealthCard
            label="Clients"
            value={clientCounts.total}
            detail={`${clientCounts.active} active`}
          />
          <HealthCard
            label="Projects"
            value={projectCounts.total}
            detail={`${projectCounts.active} active, ${projectCounts.paused} paused, ${projectCounts.complete} complete`}
          />
          <HealthCard
            label="Executions"
            value={execCounts.total}
            detail={`last: ${formatLastAt(execCounts.lastAt)}`}
          />
          <HealthCard label="Messages" value={msgCount.total} />
          <HealthCard label="Files" value={fileCount.total} />
          <HealthCard label="Resources" value={resourceCount.total} />
          <HealthCard
            label="Purchases"
            value={purchaseCount.total}
            detail={`${productCount.total} products`}
          />
          <HealthCard label="Autopilot Builds" value={buildCount.total} />
        </div>

        {/* Env vars */}
        <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Environment Variables
          </h3>
          <div className="flex flex-wrap gap-2">
            {envVars.map((v) => (
              <span
                key={v.name}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono ${
                  v.set
                    ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                }`}
              >
                <span>{v.set ? "OK" : "MISSING"}</span>
                {v.name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section B: Data Flow ──────────────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Data Flow
        </h2>
        <div className="space-y-2">
          {dataFlows.map((flow, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3"
            >
              <span className="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap shrink-0">
                {flow.from}
              </span>
              <span className="text-xs text-gray-400 font-mono shrink-0">
                {flow.arrow}
              </span>
              <span className="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap shrink-0">
                {flow.to}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto hidden sm:block">
                {flow.description}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Section C: Platform Pages ─────────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Platform Pages
        </h2>
        {areaOrder.map((area) => {
          const areaPages = pages.filter((p) => p.area === area)
          return (
            <div key={area} className="mb-6">
              <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-2">
                {areaLabel[area]}
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                      <th className="pb-2 pr-4 font-medium">Route</th>
                      <th className="pb-2 pr-4 font-medium">Page</th>
                      <th className="pb-2 pr-4 font-medium">Reads</th>
                      <th className="pb-2 pr-4 font-medium">Writes</th>
                      <th className="pb-2 pr-4 font-medium">Status</th>
                      <th className="pb-2 font-medium">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {areaPages.map((p) => (
                      <tr key={p.route} className="text-gray-700 dark:text-gray-300">
                        <td className="py-2 pr-4 font-mono text-xs text-gray-500 dark:text-gray-400">
                          {p.route}
                        </td>
                        <td className="py-2 pr-4 font-medium">{p.label}</td>
                        <td className="py-2 pr-4 text-xs text-gray-500 dark:text-gray-400">
                          {p.reads.length > 0 ? p.reads.join(", ") : "-"}
                        </td>
                        <td className="py-2 pr-4 text-xs text-gray-500 dark:text-gray-400">
                          {p.writes.length > 0 ? p.writes.join(", ") : "-"}
                        </td>
                        <td className="py-2 pr-4">
                          <Badge variant={statusVariant[p.status]}>{p.status}</Badge>
                        </td>
                        <td className="py-2 text-xs text-gray-400 dark:text-gray-500">
                          {p.notes ?? ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </section>

      {/* ── Section D: Roadmap ────────────────────────────────────────────── */}
      <section className="mb-12">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Roadmap
        </h2>
        <div className="space-y-4">
          {roadmapMilestones.map((ms) => (
            <div
              key={ms.number}
              className={`rounded-xl border bg-white dark:bg-gray-900 p-5 ${
                ms.status === "current"
                  ? "border-amber-300 dark:border-amber-700"
                  : "border-gray-200 dark:border-gray-800"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-bold text-gray-400 dark:text-gray-500">
                  M{ms.number}
                </span>
                <span className="text-base font-semibold text-gray-900 dark:text-white">
                  {ms.title}
                </span>
                <Badge variant={milestoneStatusVariant[ms.status]}>{ms.status}</Badge>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                {ms.outcome}
              </p>
              <ul className="space-y-1">
                {ms.items.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <span
                      className={`w-4 h-4 rounded border flex items-center justify-center text-xs shrink-0 ${
                        item.done
                          ? "bg-green-100 border-green-300 text-green-700 dark:bg-green-900/30 dark:border-green-700 dark:text-green-400"
                          : "border-gray-300 dark:border-gray-600"
                      }`}
                    >
                      {item.done ? "x" : ""}
                    </span>
                    <span
                      className={
                        item.done
                          ? "text-gray-400 dark:text-gray-500 line-through"
                          : "text-gray-700 dark:text-gray-300"
                      }
                    >
                      {item.label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ── Section E: Quick Links ────────────────────────────────────────── */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Quick Test Links
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <QuickLink href="/portal" label="Portal (client view)" />
          <QuickLink href="/portal/automations" label="Automations" />
          <QuickLink href="/portal/resources" label="Resources" />
          <QuickLink href="/admin" label="Admin Dashboard" />
          <QuickLink href="/admin/clients" label="Manage Clients" />
          <QuickLink href="/admin/users" label="Manage Users" />
          <QuickLink href="/login" label="Login Page" />
          <QuickLink href="/" label="Public Homepage" />
        </div>
      </section>
    </div>
  )
}

// ── Sub-components ───────────────────────────────────────────────────────────

function HealthCard({
  label,
  value,
  detail,
}: {
  label: string
  value: number | string
  detail?: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
      {detail && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{detail}</p>
      )}
    </div>
  )
}

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-700 transition-colors"
    >
      {label}
    </a>
  )
}
