import { NextRequest, NextResponse } from "next/server"
import type Stripe from "stripe"
import { stripe } from "@/lib/stripe"
import { db } from "@/lib/db"
import { products, purchases } from "@/lib/schema"
import { eq } from "drizzle-orm"

export async function POST(request: NextRequest) {
  if (!stripe) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 503 })
  }

  const body = await request.text()
  const sig = request.headers.get("stripe-signature")
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET

  if (!sig || !webhookSecret) {
    return NextResponse.json(
      { error: "Missing signature or secret" },
      { status: 400 }
    )
  }

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, sig, webhookSecret)
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 })
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session
    const { catalogSlug, userId } = session.metadata ?? {}

    if (catalogSlug) {
      const product = await db.query.products.findFirst({
        where: eq(products.catalogSlug, catalogSlug),
      })

      if (product) {
        await db
          .insert(purchases)
          .values({
            userId: userId || null,
            productId: product.id,
            stripeSessionId: session.id,
            status: "complete",
          })
          .onConflictDoNothing()
      }
    }
  }

  return NextResponse.json({ received: true })
}
