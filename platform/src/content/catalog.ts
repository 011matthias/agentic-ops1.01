export type CatalogItemType = "ready-setup" | "custom"

export interface CatalogItem {
  id: string
  slug: string
  type: CatalogItemType
  name: string
  tagline: string
  description: string
  startingFrom: string
  whatYouGet: string[]
  tools: string[]
  category: string
}

export const catalog: CatalogItem[] = [
  {
    id: "cat-001",
    slug: "lead-follow-up-starter",
    type: "ready-setup",
    name: "Lead Follow-Up Starter",
    tagline: "Instant auto-response + 3-step AI follow-up sequence",
    description:
      "A pre-built automation that fires the moment a lead submits your form. Sends a personalized response within seconds, then follows up at day 1, day 3, and day 7 — stopping the moment they reply.",
    startingFrom: "$49",
    whatYouGet: [
      "Instant auto-response email on form submission",
      "3-step AI-personalized follow-up sequence",
      "Reply detection — sequence stops when they respond",
      "Lead logged to Google Sheets",
      "Setup guide + 30-day support",
    ],
    tools: ["Make.com", "Gmail", "Google Sheets", "OpenAI"],
    category: "Lead Automation",
  },
  {
    id: "cat-002",
    slug: "crm-erp-sync-starter",
    type: "ready-setup",
    name: "CRM–ERP Sync Starter",
    tagline: "Bidirectional sync between your CRM and ERP, no manual data entry",
    description:
      "Keep your CRM and ERP in lockstep. When a deal closes in your CRM, it flows into your ERP automatically — and vice versa. No more copy-paste, no more stale records.",
    startingFrom: "$149",
    whatYouGet: [
      "Bidirectional sync on deal stage changes",
      "Automated invoice creation on deal close",
      "Slack or email notification on sync",
      "Error logging with retry logic",
      "Setup guide + 30-day support",
    ],
    tools: ["n8n", "HubSpot", "Fortnox"],
    category: "CRM & ERP",
  },
  {
    id: "cat-003",
    slug: "weekly-campaign-report",
    type: "ready-setup",
    name: "Weekly Campaign Report",
    tagline: "Auto-delivered campaign summary every Monday morning",
    description:
      "Every Monday, a clean campaign summary lands in your inbox. Open rates, reply rates, and trend vs. last week — pulled from your outreach tool and written in plain English.",
    startingFrom: "$49",
    whatYouGet: [
      "Weekly email report with key metrics",
      "Trend comparison vs. previous week",
      "AI-written summary in plain English",
      "Data pulled from your outreach tool",
      "Setup guide + 30-day support",
    ],
    tools: ["n8n", "Smartlead", "OpenRouter", "Gmail"],
    category: "Reporting",
  },
  {
    id: "cat-004",
    slug: "webhook-router",
    type: "ready-setup",
    name: "Webhook Router",
    tagline: "Route incoming webhooks to multiple destinations without code",
    description:
      "Connect any tool that sends webhooks to any tool that receives them. Filter by payload fields, transform the data, and fan out to multiple endpoints — all configured through a visual interface.",
    startingFrom: "$49",
    whatYouGet: [
      "Receive webhooks from any source",
      "Field-based filtering and routing rules",
      "Payload transformation (rename, map, drop fields)",
      "Fan-out to multiple endpoints",
      "Setup guide + 30-day support",
    ],
    tools: ["Make.com", "n8n"],
    category: "Infrastructure",
  },
  {
    id: "cat-005",
    slug: "database-poller",
    type: "ready-setup",
    name: "Database Poller",
    tagline: "Poll MySQL or Postgres on a schedule and trigger downstream actions",
    description:
      "Run a query on your database every N minutes. When new rows appear, trigger any downstream action — send an email, update a CRM record, post to Slack, or call an API.",
    startingFrom: "$49",
    whatYouGet: [
      "Scheduled polling (1 min to daily)",
      "New-row detection with deduplication",
      "Configurable downstream action (email, Slack, API call)",
      "Error alerting if poll fails",
      "Setup guide + 30-day support",
    ],
    tools: ["Make.com", "MySQL", "Postgres"],
    category: "Infrastructure",
  },
  {
    id: "cat-006",
    slug: "custom-automation",
    type: "custom",
    name: "Custom Automation",
    tagline: "Fully scoped to your workflow — any tools, any complexity",
    description:
      "For workflows that don't fit a template. We scope the project, propose a solution, and build it end-to-end. Includes discovery call, written proposal, and full implementation.",
    startingFrom: "From $299",
    whatYouGet: [
      "Discovery call to map your workflow",
      "Written proposal with scope and price",
      "Full implementation and testing",
      "Documentation for your team",
      "Ongoing support available",
    ],
    tools: ["Make.com", "n8n", "Trigger.dev", "Any API"],
    category: "Custom",
  },
  {
    id: "cat-007",
    slug: "automation-audit",
    type: "custom",
    name: "Automation Audit",
    tagline: "We review your existing automations and tell you what to fix",
    description:
      "Already running automations but not sure if they're reliable? We review your workflows, identify failure points, and give you a prioritized list of fixes with estimated impact.",
    startingFrom: "Free",
    whatYouGet: [
      "Review of up to 5 existing automations",
      "Written report with findings",
      "Prioritized fix recommendations",
      "30-minute walkthrough call",
      "No obligation to proceed",
    ],
    tools: ["Make.com", "n8n", "Zapier", "Any platform"],
    category: "Consulting",
  },
]
