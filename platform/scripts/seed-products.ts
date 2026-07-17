/**
 * Seed the products table from catalog.ts
 *
 * Run: source <(grep -v '^#' .env.local | sed 's/^/export /') && npx tsx scripts/seed-products.ts
 *
 * Requires DATABASE_URL env var
 */

import { neon } from "@neondatabase/serverless"
import { drizzle } from "drizzle-orm/neon-http"
import { products } from "../src/lib/schema"
import { catalog } from "../src/content/catalog"

async function main() {
  if (!process.env.DATABASE_URL) {
    console.error("DATABASE_URL not set. Source .env.local first:")
    console.error('  source <(grep -v \'^\' .env.local | sed \'s/^/export /\') && npx tsx scripts/seed-products.ts')
    process.exit(1)
  }

  const sql = neon(process.env.DATABASE_URL)
  const db = drizzle(sql)

  console.log(`Seeding ${catalog.length} products from catalog.ts...\n`)

  for (const item of catalog) {
    // Parse price from string like "$199" or "From EUR 2,500"
    const priceStr = item.selfServicePrice || item.premiumPrice
    const priceMatch = priceStr.match(/[\d,]+/)
    const priceUsd = priceMatch ? parseInt(priceMatch[0].replace(",", "")) * 100 : 0

    try {
      await db
        .insert(products)
        .values({
          catalogSlug: item.slug,
          name: item.name,
          priceUsd: priceUsd,
          active: true,
        })
        .onConflictDoNothing()

      console.log(`  + ${item.name} (${item.slug}) -- $${(priceUsd / 100).toFixed(2)}`)
    } catch (err) {
      console.error(`  x ${item.name}: ${err}`)
    }
  }

  console.log("\nDone.")
}

main().catch(console.error)
