"use client";

import { useState, type FormEvent } from "react";

export default function ContactPage() {
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">(
    "idle"
  );

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("sending");

    const form = e.currentTarget;
    const data = {
      name: (form.elements.namedItem("name") as HTMLInputElement).value,
      company: (form.elements.namedItem("company") as HTMLInputElement).value,
      email: (form.elements.namedItem("email") as HTMLInputElement).value,
      message: (form.elements.namedItem("message") as HTMLTextAreaElement)
        .value,
    };

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) throw new Error("Failed");
      setStatus("sent");
      form.reset();
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <h1 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
        Get in touch
      </h1>
      <p className="mb-10 text-muted">
        Tell us about the workflow you want to automate. We&rsquo;ll get back to
        you within 24 hours with an initial assessment.
      </p>

      {status === "sent" ? (
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-6">
          <p className="font-medium">Message sent.</p>
          <p className="mt-1 text-sm text-muted">
            We&rsquo;ll get back to you within 24 hours.
          </p>
          <button
            onClick={() => setStatus("idle")}
            className="mt-4 text-sm text-accent hover:text-accent-light"
          >
            Send another message
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label
                htmlFor="name"
                className="mb-1.5 block text-sm font-medium"
              >
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
              <label
                htmlFor="company"
                className="mb-1.5 block text-sm font-medium"
              >
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
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium"
            >
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

          <div>
            <label
              htmlFor="message"
              className="mb-1.5 block text-sm font-medium"
            >
              Tell us about your workflow
            </label>
            <textarea
              id="message"
              name="message"
              rows={5}
              required
              placeholder="What systems do you use? What's the repetitive task you'd like to automate?"
              className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground outline-none transition-colors focus:border-accent"
            />
          </div>

          {status === "error" && (
            <p className="text-sm text-red-500">
              Something went wrong. Please try again or email us directly.
            </p>
          )}

          <button
            type="submit"
            disabled={status === "sending"}
            className="mt-2 self-start rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light disabled:opacity-50"
          >
            {status === "sending" ? "Sending..." : "Send Message"}
          </button>
        </form>
      )}

      <div className="mt-12 border-t border-border pt-8">
        <p className="text-sm text-muted">
          Prefer email directly?{" "}
          <a
            href="mailto:nicholas.neuman@unpauseai.com"
            className="text-accent hover:text-accent-light"
          >
            nicholas.neuman@unpauseai.com
          </a>
        </p>
      </div>
    </div>
  );
}
