import { NextRequest, NextResponse } from "next/server"
import { stripe } from "@/lib/stripe"

export async function POST(request: NextRequest) {
  if (!stripe) {
    return NextResponse.json(
      { error: "Stripe not configured. Please contact us directly." },
      { status: 503 }
    )
  }

  const body = await request.json() as { email?: string }
  const { email } = body

  if (!email || !email.includes("@")) {
    return NextResponse.json({ error: "Valid email required" }, { status: 400 })
  }

  const origin = request.headers.get("origin") || "https://unpauseai.com"

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ["card"],
    customer_email: email,
    line_items: [
      {
        price_data: {
          currency: "usd",
          product_data: {
            name: "Automation Assessment",
            description:
              "Personalized written assessment of your workflow automation needs. Delivered within 24 hours.",
          },
          unit_amount: 100, // $1.00
        },
        quantity: 1,
      },
    ],
    mode: "payment",
    success_url: `${origin}/assessment/thank-you?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${origin}/assessment`,
    metadata: {
      type: "assessment",
      email,
    },
  })

  return NextResponse.json({ url: session.url })
}
