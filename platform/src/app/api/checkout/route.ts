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

  const body = await request.json() as { slug?: string }
  const { slug } = body
  const item = catalog.find((i) => i.slug === slug)

  if (!item || item.type !== "ready-setup") {
    return NextResponse.json({ error: "Product not found" }, { status: 404 })
  }

  if (item.startingFrom === "Free") {
    return NextResponse.json(
      { error: "This item is free — no checkout needed" },
      { status: 400 }
    )
  }

  // Parse price: "$49" → 4900 cents
  const priceMatch = item.startingFrom.match(/\$(\d+)/)
  const priceUsd = priceMatch ? parseInt(priceMatch[1]) * 100 : 0

  if (!priceUsd) {
    return NextResponse.json(
      { error: "Could not determine price" },
      { status: 400 }
    )
  }

  const origin = request.headers.get("origin") ?? "http://localhost:3000"

  const checkoutSession = await stripe.checkout.sessions.create({
    mode: "payment",
    customer_email: session?.user?.email ?? undefined,
    line_items: [
      {
        price_data: {
          currency: "usd",
          unit_amount: priceUsd,
          product_data: {
            name: item.name,
            description: item.tagline,
          },
        },
        quantity: 1,
      },
    ],
    metadata: {
      catalogSlug: item.slug,
      userId: session?.user?.id ?? "",
    },
    success_url: `${origin}/buy/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${origin}/automations#ready-setup`,
  })

  return NextResponse.json({ url: checkoutSession.url })
}
