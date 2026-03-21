import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Payment successful",
  description: "Your purchase was completed successfully.",
}

export default function BuySuccessPage() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-32 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
        <span className="text-2xl text-green-600 dark:text-green-400">&#10003;</span>
      </div>

      <h1 className="mb-3 text-3xl font-bold tracking-tight">
        Payment successful!
      </h1>

      <p className="mb-8 text-muted">
        You&rsquo;ll receive an email with access details shortly. If you have
        any questions, contact us and we&rsquo;ll get back to you within one
        business day.
      </p>

      <div className="flex gap-4">
        <Link
          href="/automations"
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          Back to automations
        </Link>
        <Link
          href="/contact"
          className="rounded-lg border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-border/30"
        >
          Contact us
        </Link>
      </div>
    </div>
  )
}
