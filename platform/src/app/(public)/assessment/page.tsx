"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";

const benefits = [
  "Written assessment of your automation needs",
  "Recommended architecture and platform (Make.com, n8n, or Trigger.dev)",
  "Estimated timeline and investment range",
  "Delivered to your inbox within 24 hours",
];

export default function AssessmentPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/assessment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Something went wrong");
      }

      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setStatus("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    }
  }

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            $1 Automation Assessment
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Find out what we&rsquo;d build for you
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Describe your workflow. Within 24 hours, you&rsquo;ll receive a
            personalized written assessment: what we&rsquo;d automate, which
            platform we&rsquo;d use, and what it would cost.
          </p>
        </div>
      </section>

      {/* Main content */}
      <section className="mx-auto max-w-4xl px-6 pb-20">
        <div className="grid gap-12 sm:grid-cols-2">
          {/* What you get */}
          <div>
            <h2 className="mb-4 text-xl font-bold">What you get</h2>
            <ul className="space-y-3">
              {benefits.map((benefit) => (
                <li key={benefit} className="flex items-start gap-3 text-sm text-muted">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-green" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  {benefit}
                </li>
              ))}
            </ul>

            <div className="mt-8 rounded-xl border border-border bg-surface p-5">
              <h3 className="mb-2 text-sm font-semibold">Why $1?</h3>
              <p className="text-sm leading-relaxed text-muted">
                Every assessment is written personally using AI-assisted analysis
                of your specific workflow. The $1 filters spam and ensures
                we&rsquo;re only spending time on real inquiries. It&rsquo;s a
                qualification gate, not a revenue model.
              </p>
            </div>
          </div>

          {/* Payment form */}
          <div>
            <div className="rounded-xl border border-border bg-surface p-6">
              <div className="mb-6 flex items-baseline justify-between">
                <h2 className="text-xl font-bold">Get started</h2>
                <span className="text-2xl font-bold text-accent">$1</span>
              </div>

              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div>
                  <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
                    Work email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
                  />
                </div>

                {status === "error" && (
                  <p className="text-sm text-red-500">{errorMsg}</p>
                )}

                <button
                  type="submit"
                  disabled={status === "loading"}
                  className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5 disabled:opacity-50"
                >
                  {status === "loading" ? "Redirecting to checkout..." : "Pay $1 & Continue"}
                </button>

                <p className="text-center text-xs text-muted">
                  Secure payment via Stripe. After payment, you&rsquo;ll fill
                  out a short intake form about your workflow.
                </p>
              </form>
            </div>

            <p className="mt-4 text-center text-sm text-muted">
              Prefer to skip the form?{" "}
              <Link href="/contact" className="text-accent hover:text-accent-light">
                Contact us directly
              </Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
