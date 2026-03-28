export type CatalogTier = "marketplace" | "custom"

export interface CatalogItem {
  id: string
  slug: string
  tier: CatalogTier
  name: string
  tagline: string
  description: string
  selfServicePrice: string
  premiumPrice: string
  whatYouGet: string[]
  premiumIncludes: string[]
  tools: string[]
  category: string
}

export const catalog: CatalogItem[] = [
  {
    id: "cat-001",
    slug: "lead-follow-up-engine",
    tier: "marketplace",
    name: "Lead Follow-Up Engine",
    tagline: "Instant auto-response + AI-personalized follow-up sequence with reply detection",
    description:
      "Battle-tested automation that fires the moment a lead submits your form. Sends a personalized response within seconds, then follows up at configurable intervals, stopping the moment they reply. Built from real client deployments handling hundreds of leads per week.",
    selfServicePrice: "$199",
    premiumPrice: "$1,500",
    whatYouGet: [
      "Make.com or n8n blueprint file",
      "Instant auto-response on form submission",
      "3-step AI-personalized follow-up sequence",
      "Reply detection that stops the sequence",
      "Lead logging to Google Sheets or CRM",
      "Setup documentation + video walkthrough",
    ],
    premiumIncludes: [
      "Full implementation and testing with your accounts",
      "Custom follow-up copy and timing",
      "CRM integration (HubSpot, Pipedrive, etc.)",
      "30-day post-launch support",
    ],
    tools: ["Make.com", "n8n", "Gmail", "Google Sheets", "OpenAI"],
    category: "Lead Automation",
  },
  {
    id: "cat-002",
    slug: "crm-erp-bidirectional-sync",
    tier: "marketplace",
    name: "CRM-ERP Bidirectional Sync",
    tagline: "Keep your CRM and ERP in lockstep with zero manual data entry",
    description:
      "Production-grade bidirectional sync between your CRM and ERP. Handles deduplication, conflict resolution, and retry logic. Built from real integrations connecting HubSpot, Pipedrive, Fortnox, and similar platforms.",
    selfServicePrice: "$349",
    premiumPrice: "$2,500",
    whatYouGet: [
      "n8n workflow file with full error handling",
      "Bidirectional sync on deal stage changes",
      "Automated invoice creation on deal close",
      "Deduplication and conflict resolution logic",
      "Error logging with retry mechanism",
      "Setup documentation + video walkthrough",
    ],
    premiumIncludes: [
      "Full implementation with your CRM and ERP accounts",
      "Custom field mapping for your data model",
      "Historical data migration assistance",
      "30-day post-launch support",
    ],
    tools: ["n8n", "HubSpot", "Fortnox", "Pipedrive"],
    category: "CRM & ERP",
  },
  {
    id: "cat-003",
    slug: "ai-classification-pipeline",
    tier: "marketplace",
    name: "AI Classification Pipeline",
    tagline: "Claude API-powered routing with confidence thresholds and fallback logic",
    description:
      "Classify incoming requests, leads, or support tickets using Claude API with structured confidence-threshold routing. High-confidence items get auto-processed; uncertain ones get flagged for human review. Built from agentic AI projects.",
    selfServicePrice: "$299",
    premiumPrice: "$2,200",
    whatYouGet: [
      "Make.com or n8n workflow with Claude API integration",
      "Confidence-threshold routing (auto/review/escalate tiers)",
      "Structured JSON output parsing",
      "Fallback logic for API failures",
      "Classification logging and analytics",
      "Setup documentation + video walkthrough",
    ],
    premiumIncludes: [
      "Custom classification categories for your domain",
      "Prompt engineering tuned to your data",
      "Integration with your ticketing/CRM system",
      "30-day post-launch support",
    ],
    tools: ["Make.com", "n8n", "Claude API", "Slack"],
    category: "AI & Classification",
  },
  {
    id: "cat-004",
    slug: "database-poller-alert-system",
    tier: "marketplace",
    name: "Database Poller & Alert System",
    tagline: "Poll MySQL or Postgres on a schedule and trigger downstream actions",
    description:
      "Scheduled database polling with new-row detection, deduplication, and configurable downstream actions. Fires when new data appears. Built from production polling systems handling thousands of records.",
    selfServicePrice: "$149",
    premiumPrice: "$1,200",
    whatYouGet: [
      "Make.com scenario with database polling module",
      "Configurable polling interval (1 min to daily)",
      "New-row detection with deduplication",
      "Downstream action triggers (email, Slack, API)",
      "Error alerting if poll fails",
      "Setup documentation + video walkthrough",
    ],
    premiumIncludes: [
      "Database connection setup and query optimization",
      "Custom downstream action configuration",
      "Monitoring and alerting setup",
      "30-day post-launch support",
    ],
    tools: ["Make.com", "MySQL", "Postgres", "Slack"],
    category: "Infrastructure",
  },
  {
    id: "cat-005",
    slug: "weekly-campaign-report",
    tier: "marketplace",
    name: "Weekly Campaign Report",
    tagline: "Auto-delivered campaign summary with AI-written insights every Monday morning",
    description:
      "Every Monday, a clean campaign summary lands in your inbox. Open rates, reply rates, and trend vs. last week, pulled from your outreach tool and written in plain English by AI.",
    selfServicePrice: "$99",
    premiumPrice: "$800",
    whatYouGet: [
      "n8n workflow with outreach tool integration",
      "Weekly email report with key metrics",
      "Trend comparison vs. previous week",
      "AI-written summary in plain English",
      "Google Sheets data logging",
      "Setup documentation + video walkthrough",
    ],
    premiumIncludes: [
      "Integration with your specific outreach platform",
      "Custom metrics and KPI configuration",
      "Branded report template",
      "30-day post-launch support",
    ],
    tools: ["n8n", "Smartlead", "OpenAI", "Gmail", "Google Sheets"],
    category: "Reporting",
  },
  {
    id: "cat-006",
    slug: "custom-automation",
    tier: "custom",
    name: "Custom Automation",
    tagline: "Fully scoped to your workflow. Any tools, any complexity.",
    description:
      "For workflows that don't fit a template. We scope the project, propose a solution, and build it end-to-end. Includes discovery, written proposal, full implementation, testing, and documentation.",
    selfServicePrice: "",
    premiumPrice: "From EUR 2,500",
    whatYouGet: [],
    premiumIncludes: [
      "Discovery call to map your workflow",
      "Written proposal with scope, architecture, and price",
      "Full implementation and testing",
      "Documentation and team training",
      "30-day post-launch support included",
    ],
    tools: ["Make.com", "n8n", "Trigger.dev", "Claude API", "Any API"],
    category: "Custom",
  },
]

export const marketplaceItems = catalog.filter((item) => item.tier === "marketplace")
export const customItems = catalog.filter((item) => item.tier === "custom")
