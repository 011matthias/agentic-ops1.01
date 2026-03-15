import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Order cancelled",
  description: "Your order was cancelled. No charge was made.",
}

export default function BuyCancelPage() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-32 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
        <span className="text-2xl text-muted">&#x2715;</span>
      </div>

      <h1 className="mb-3 text-3xl font-bold tracking-tight">
        Order cancelled
      </h1>

      <p className="mb-8 text-muted">
        No charge was made. You can return to the automations catalogue whenever
        you&rsquo;re ready.
      </p>

      <Link
        href="/automations#ready-setup"
        className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90"
      >
        Back to automations
      </Link>
    </div>
  )
}
