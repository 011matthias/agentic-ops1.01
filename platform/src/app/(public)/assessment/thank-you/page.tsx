"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";

const industries = [
  "Healthcare",
  "Marketing & Agency",
  "SaaS / Software",
  "E-commerce",
  "Finance & Accounting",
  "Real Estate",
  "Manufacturing",
  "Other",
];

const timelines = [
  "ASAP",
  "1-2 months",
  "3+ months",
  "Just exploring",
];

export default function AssessmentThankYouPage() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("sending");

    const form = e.currentTarget;
    const data = {
      name: (form.elements.namedItem("name") as HTMLInputElement).value,
      company: (form.elements.namedItem("company") as HTMLInputElement).value,
      email: (form.elements.namedItem("email") as HTMLInputElement).value,
      industry: (form.elements.namedItem("industry") as HTMLSelectElement).value,
      currentTools: (form.elements.namedItem("currentTools") as HTMLInputElement).value,
      message: (form.elements.namedItem("message") as HTMLTextAreaElement).value,
      timeline: (form.elements.namedItem("timeline") as HTMLSelectElement).value,
      type: "assessment",
    };

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) throw new Error("Failed");
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  if (status === "sent") {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20 text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-bg">
          <svg className="h-8 w-8 text-green" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>
        <h1 className="mb-4 text-3xl font-extrabold tracking-tight">Assessment requested</h1>
        <p className="mb-2 text-lg text-muted">
          We&rsquo;ll have your personalized assessment within 24 hours.
        </p>
        <p className="text-sm text-muted">
          Check your inbox for a confirmation. In the meantime, feel free to{" "}
          <Link href="/work" className="text-accent hover:text-accent-light">
            browse our automation marketplace
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <div className="mb-8 rounded-xl border border-green/20 border-l-4 border-l-green bg-green-bg p-5">
        <p className="font-semibold text-green">Payment received. Thank you!</p>
        <p className="mt-1 text-sm text-muted">
          Now tell us about your workflow so we can write your assessment.
        </p>
      </div>

      <h1 className="mb-2 text-2xl font-extrabold tracking-tight">
        Describe your workflow
      </h1>
      <p className="mb-8 text-muted">
        The more detail you provide, the more specific your assessment will be.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm font-medium">
              Name
            </label>
            <input
              type="text"
              id="name"
              name="name"
              required
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
            />
          </div>
          <div>
            <label htmlFor="company" className="mb-1.5 block text-sm font-medium">
              Company
            </label>
            <input
              type="text"
              id="company"
              name="company"
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
            />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
            Email
          </label>
          <input
            type="email"
            id="email"
            name="email"
            required
            className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="industry" className="mb-1.5 block text-sm font-medium">
              Industry
            </label>
            <select
              id="industry"
              name="industry"
              required
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
            >
              <option value="">Select industry</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="timeline" className="mb-1.5 block text-sm font-medium">
              Timeline
            </label>
            <select
              id="timeline"
              name="timeline"
              required
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
            >
              <option value="">When do you need this?</option>
              {timelines.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="currentTools" className="mb-1.5 block text-sm font-medium">
            What tools do you currently use?
          </label>
          <input
            type="text"
            id="currentTools"
            name="currentTools"
            placeholder="e.g., HubSpot, Google Sheets, Slack, MySQL"
            className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
          />
        </div>

        <div>
          <label htmlFor="message" className="mb-1.5 block text-sm font-medium">
            Describe the workflow you want to automate
          </label>
          <textarea
            id="message"
            name="message"
            rows={5}
            required
            placeholder="What's the manual process? What triggers it? What systems are involved? What's the desired outcome?"
            className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
          />
        </div>

        {status === "error" && (
          <p className="text-sm text-red-500">
            Something went wrong. Please try again or email us directly at{" "}
            <a href="mailto:admin@unpauseai.com" className="underline">
              admin@unpauseai.com
            </a>
          </p>
        )}

        <button
          type="submit"
          disabled={status === "sending"}
          className="mt-2 self-start rounded-full bg-accent px-7 py-3 text-sm font-medium text-white shadow-[0_2px_8px_rgba(37,99,235,.3)] transition-all hover:bg-accent-light hover:-translate-y-0.5 disabled:opacity-50"
        >
          {status === "sending" ? "Submitting..." : "Submit for Assessment"}
        </button>
      </form>
    </div>
  );
}
