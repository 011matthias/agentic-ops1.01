export type ProductType = "custom" | "ready-setup"

export interface CatalogItem {
  id: string
  slug: string
  type: ProductType
  name: string
  tagline: string
  description: string
  whatYouGet: string[]
  typicalTimeline: string
  startingFrom: string
  tags: string[]
  popular?: boolean
}

export const catalog: CatalogItem[] = [
  // --- CUSTOM BUILDS ---
  {
    id: "custom-lead-nurture",
    slug: "lead-nurture-sequence",
    type: "custom",
    name: "Lead Nurture Sequence",
    tagline: "Automated follow-up that converts enquiries into booked clients",
    description:
      "We build a multi-step follow-up automation tailored to your sales process — from first enquiry through to booking confirmation. Integrates with your CRM, email, and calendar.",
    whatYouGet: [
      "Custom-built automation in Make.com or n8n",
      "Personalised email sequences (3–5 steps)",
      "CRM integration (HubSpot, Airtable, Notion, or similar)",
      "30-day monitoring and iteration",
    ],
    typicalTimeline: "1–2 weeks",
    startingFrom: "$800",
    tags: ["CRM", "Email", "Lead Gen"],
    popular: true,
  },
  {
    id: "custom-enquiry-pipeline",
    slug: "enquiry-pipeline",
    type: "custom",
    name: "Enquiry-to-Invoice Pipeline",
    tagline:
      "From new enquiry to signed contract and first invoice — fully automated",
    description:
      "End-to-end pipeline that captures enquiries, qualifies leads, sends proposals, collects signatures, and generates invoices — without manual steps.",
    whatYouGet: [
      "Multi-platform automation (form → email → contract → invoice)",
      "E-signature integration (DocuSign or similar)",
      "Automated invoicing (Xero, QuickBooks, or Stripe)",
      "Client onboarding triggered on contract sign",
    ],
    typicalTimeline: "2–3 weeks",
    startingFrom: "$1,200",
    tags: ["Sales", "Finance", "Onboarding"],
  },
  {
    id: "custom-reporting",
    slug: "automated-reporting",
    type: "custom",
    name: "Automated Reporting Dashboard",
    tagline: "Weekly reports delivered to your inbox — no spreadsheet wrangling",
    description:
      "Pull data from multiple sources (ad platforms, CRMs, spreadsheets), aggregate it, and deliver formatted reports on a schedule. You set the metrics, we automate the delivery.",
    whatYouGet: [
      "Data pipeline from 2–4 sources",
      "Custom report template (Google Sheets, Notion, or PDF)",
      "Scheduled delivery via email or Slack",
      "Anomaly alerts for key metrics",
    ],
    typicalTimeline: "1–2 weeks",
    startingFrom: "$600",
    tags: ["Analytics", "Reporting", "Data"],
  },
  {
    id: "custom-client-portal",
    slug: "client-portal-setup",
    type: "custom",
    name: "Client Portal Setup",
    tagline:
      "Give your clients a branded hub for files, messages, and project status",
    description:
      "We configure and customise a client portal connected to your project management tools — so clients always know what's happening without chasing you for updates.",
    whatYouGet: [
      "Branded portal (white-label or UnpauseAI hosted)",
      "File delivery and versioning",
      "Project timeline and milestone tracker",
      "Automated status update notifications",
    ],
    typicalTimeline: "2–4 weeks",
    startingFrom: "$1,500",
    tags: ["Portal", "Client Experience", "Projects"],
  },
  // --- READY SETUP ---
  {
    id: "ready-upwork-profile",
    slug: "upwork-profile-optimiser",
    type: "ready-setup",
    name: "Upwork Profile Optimiser",
    tagline: "A step-by-step system to rank higher and win more proposals",
    description:
      "A complete Upwork setup system — profile audit checklist, proposal templates, niche positioning guide, and a tracked outreach tracker. Self-guided, delivered instantly.",
    whatYouGet: [
      "Profile audit checklist (25 points)",
      "5 proven proposal templates by job type",
      "Niche positioning workbook",
      "Weekly outreach tracking spreadsheet",
    ],
    typicalTimeline: "Instant access",
    startingFrom: "Free",
    tags: ["Upwork", "Freelance", "Templates"],
    popular: true,
  },
  {
    id: "ready-make-starter",
    slug: "make-starter-pack",
    type: "ready-setup",
    name: "Make.com Starter Pack",
    tagline: "5 plug-and-play automation templates for service businesses",
    description:
      "Ready-to-import Make.com blueprints for the most common service business automations. Import, connect your apps, and run — no custom build required.",
    whatYouGet: [
      "5 Make.com blueprint files (.json)",
      "Setup guide for each blueprint",
      "Video walkthrough (15 min)",
      "Community Discord access",
    ],
    typicalTimeline: "Instant access",
    startingFrom: "$49",
    tags: ["Make.com", "Templates", "DIY"],
  },
  {
    id: "ready-n8n-starter",
    slug: "n8n-starter-pack",
    type: "ready-setup",
    name: "n8n Workflow Starter Pack",
    tagline: "Self-hosted automation templates — own your stack",
    description:
      "5 n8n workflow templates for businesses that want full control. Export to your own n8n instance and customise freely.",
    whatYouGet: [
      "5 n8n workflow JSON files",
      "Docker setup guide for self-hosting",
      "Customisation tips per workflow",
      "Email support for 14 days",
    ],
    typicalTimeline: "Instant access",
    startingFrom: "$49",
    tags: ["n8n", "Self-hosted", "Templates"],
  },
]

export const customItems = catalog.filter((i) => i.type === "custom")
export const readyItems = catalog.filter((i) => i.type === "ready-setup")
