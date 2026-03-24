# Platform Development Module

Reference for building the unpauseai.com platform — portal, dashboard, and public site.

## Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Framework | Next.js 16 (App Router) | `platform/src/app/` |
| Styling | Tailwind CSS 4 | CSS variables, not tailwind.config.js |
| Components | shadcn/ui | Installed as local files in `src/components/ui/` |
| Database | Drizzle ORM + Neon | Schema: `src/lib/schema.ts`, DB: `src/lib/db.ts` |
| Auth | next-auth 5 (beta) | Config: `src/lib/auth.ts` |
| Email | Resend | Used in `src/app/api/contact/route.ts` |
| Deploy | Vercel (auto via PR) | Root dir: `platform/`, env vars in Vercel dashboard |

## Tailwind CSS 4 Conventions

Tailwind 4 uses CSS variables — no `tailwind.config.js`. Define custom tokens in `src/app/globals.css`:

```css
@import "tailwindcss";

:root {
  --color-brand: oklch(0.6 0.2 250);
}
```

Use in classes: `bg-[--color-brand]` or define utility classes. Do NOT create `tailwind.config.js` — it's not used.

## Component Library: shadcn/ui

Install components with:
```bash
cd platform && npx shadcn@latest add button card input label
```

Components install as local files in `src/components/ui/`. Edit them freely. Import with:
```tsx
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
```

When starting portal work, install the core set first:
```bash
npx shadcn@latest add button card input label badge separator skeleton
```

## Auth Guard Pattern

All protected routes follow the pattern in `src/app/portal/page.tsx`:

```tsx
import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"

export default async function ProtectedPage() {
  const session = await auth()
  if (!session?.user) redirect("/login")
  // ... page content
}
```

User roles: `"admin"` (UnpausAI team) | `"client"` (portal users). Check role with `session.user.role`.

## Data Fetching Patterns

**Server components (preferred for data display):**
```tsx
import { db } from "@/lib/db"
import { clients } from "@/lib/schema"
import { eq } from "drizzle-orm"

// In a server component:
const clientData = await db.query.clients.findFirst({
  where: eq(clients.userId, session.user.id)
})
```

**API routes (for mutations, webhooks, form submissions):**
```
src/app/api/{name}/route.ts
```

**Client components:** Only use `"use client"` for interactivity (forms, toggles, real-time). Never use it just for data fetching — use server components + server actions instead.

## Database Schema

Tables in `src/lib/schema.ts`:
- `users` — auth users, `role: "admin" | "client"`
- `accounts`, `sessions`, `verificationTokens` — next-auth adapter tables
- `clients` — business entity linked to user (`companyName`, `status`)

**Add new tables** by exporting from `schema.ts`, then running:
```bash
cd platform && npx drizzle-kit generate && npx drizzle-kit migrate
```

## Visual Verification with Playwright

After making UI changes, run the smoke test to capture screenshots:

```bash
cd platform && npx playwright test --project=chromium
```

Screenshots saved to `platform/test-results/`. View them to verify layout, colors, and components render correctly before pushing.

**Run against local dev server:**
```bash
# Terminal 1
cd platform && npm run dev

# Terminal 2
cd platform && npx playwright test
```

The `playwright.config.ts` is configured to use `http://localhost:3000` and auto-start the dev server if not running.

**Run a specific test:**
```bash
npx playwright test tests/smoke.spec.ts
```

## Seed Database for Development

Populate test data for local portal development:

```bash
cd platform && npx tsx scripts/seed.ts
```

Creates:
- Test user: `dev@unpauseai.com` (role: `admin`)
- Test client user: `test@client.com` (role: `client`)

**Note:** Requires `DATABASE_URL` env var. Copy from `.env.local`:
```bash
cd platform && cp .env.local.example .env.local  # if exists
```

## Dev Commands

```bash
cd platform && npm run dev          # Start dev server at localhost:3000
cd platform && npm run build        # Production build (run before pushing)
cd platform && npx drizzle-kit studio  # Visual DB browser
cd platform && npx playwright test  # Visual smoke tests
cd platform && npx tsx scripts/seed.ts  # Seed DB
```

## Portal Routes

| Route | Status | Description |
|-------|--------|-------------|
| `/portal` | Skeleton | Dashboard overview (4 cards) |
| `/portal/automations` | Not built | Automation list + run history |
| `/portal/messages` | Not built | Client ↔ team messaging |
| `/portal/reports` | Not built | Usage metrics, monthly digests |
| `/portal/settings` | Not built | Account + notification settings |
| `/login` | Built | Email sign-in via next-auth |

## Design Workflow

For new portal sections:
1. Use **Canva MCP** to generate a wireframe/mockup (`generate-design` or `generate-design-structured`)
2. Export as image (`export-design`)
3. Implement the layout in Next.js/shadcn
4. Run Playwright smoke test to verify rendered output

## File Layout

```
platform/src/
├── app/
│   ├── layout.tsx          # Root layout + Header + Providers
│   ├── page.tsx            # Home (public)
│   ├── login/page.tsx      # Auth UI
│   ├── portal/page.tsx     # Portal dashboard (protected)
│   ├── api/
│   │   ├── auth/           # next-auth endpoints
│   │   ├── contact/        # Contact form (Resend)
│   │   └── modules/        # Automation module webhooks
├── components/
│   ├── Header.tsx          # Nav (public + portal states)
│   ├── Providers.tsx       # SessionProvider wrapper
│   └── ui/                 # shadcn/ui components (add as needed)
├── lib/
│   ├── auth.ts             # next-auth config
│   ├── db.ts               # Drizzle + Neon connection
│   └── schema.ts           # Database schema
└── modules/
    └── registry.ts         # Automation module webhook registry
```
