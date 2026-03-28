import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { stripe } from "@/lib/stripe"
import { catalog } from "@/content/catalog"

export async function POST(request: NextRequest) {
  if (!stripe) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 503 })
  }

  const session = await auth()
  // Allow unauthenticated checkout — they can create an account post-purchase

  const body = await request.json() as { slug?: string; tier?: "self-service" | "premium" }
  const { slug, tier = "self-service" } = body
  const item = catalog.find((i) => i.slug === slug)

  if (!item || item.tier !== "marketplace") {
    return NextResponse.json({ error: "Product not found" }, { status: 404 })
  }

  const priceStr = tier === "premium" ? item.premiumPrice : item.selfServicePrice
  const priceMatch = priceStr.match(/\$?([\d,]+)/)
  const priceUsd = priceMatch ? parseInt(priceMatch[1].replace(",", "")) * 100 : 0

  if (!priceUsd) {
    return NextResponse.json(
      { error: "Could not determine price" },
      { status: 400 }
    )
  }

  const origin = request.headers.get("origin") ?? "https://unpauseai.com"

  const checkoutSession = await stripe.checkout.sessions.create({
    mode: "payment",
    customer_email: session?.user?.email ?? undefined,
    line_items: [
      {
        price_data: {
          currency: "usd",
          unit_amount: priceUsd,
          product_data: {
            name: `${item.name} (${tier === "premium" ? "Premium" : "Self-Service"})`,
            description: item.tagline,
          },
        },
        quantity: 1,
      },
    ],
    metadata: {
      catalogSlug: item.slug,
      tier,
      userId: session?.user?.id ?? "",
    },
    success_url: `${origin}/work?purchased=${item.slug}`,
    cancel_url: `${origin}/work`,
  })

  return NextResponse.json({ url: checkoutSession.url })
}
