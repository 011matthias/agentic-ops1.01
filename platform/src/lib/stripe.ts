import Stripe from "stripe"

if (!process.env.STRIPE_SECRET_KEY) {
  // graceful degradation — Stripe features disabled if key not set
}

export const stripe = process.env.STRIPE_SECRET_KEY
  ? new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2025-02-24.acacia",
    })
  : null
