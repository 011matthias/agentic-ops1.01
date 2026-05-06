import type { Metadata } from "next";
import Link from "next/link";
import ScrollReveal from "@/components/ScrollReveal";

export const metadata: Metadata = {
  title: "OneProposal — Upwork proposals that don't sound like ChatGPT",
  description:
    "Paste an Upwork job posting. Get a tailored cover letter and a personalized proposal page in 30 seconds. $5 per proposal, refunded on failure.",
};

const APP_URL = "https://proposal-scribe-bot.lovable.app";
// SAMPLE_PROPOSAL_URL intentionally not displayed inline -- the privacy rule
// (no prospect/client names on unpauseai.com) means we cannot expose a
// generated proposal's slug here, since the slug contains the prospect name.
// The "See a sample" CTA below is rendered as a deferred affordance ("on
// request") until we generate a fully fictional demo with an obviously
// non-real name (e.g. "Acme Corp.") and dedicate it as the public demo.

const features = [
  {
    title: "Research-first, not template-first",
    body: "Every proposal starts by extracting the prospect's real problem from their post. You confirm the interpretation before generation runs. No generic boilerplate.",
    color: "blue" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
        <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    title: "No AI tells in the output",
    body: "Em dashes are sanitized. The banned-phrase list is enforced at generation. The result reads like a freelancer wrote it because the constraints assume nothing else is acceptable.",
    color: "purple" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
        <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a.75.75 0 00-1.207-.882l-3.13 4.286-1.85-1.851a.75.75 0 10-1.06 1.06l2.5 2.5a.75.75 0 001.124-.082l3.625-4.962z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    title: "A real page, not just text",
    body: "Each proposal includes a personalized one-page site at a public URL — the kind of polish 99% of Upwork applicants don't bother with. Send the cover letter; let the page do the rest.",
    color: "green" as const,
    icon: (
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
        <path fillRule="evenodd" d="M4.083 9h1.946c.089-1.546.383-2.97.837-4.118A6.004 6.004 0 004.083 9zM10 2a8 8 0 100 16 8 8 0 000-16zm0 2c-.076 0-.232.032-.465.262-.238.234-.497.623-.737 1.182-.389.907-.673 2.142-.766 3.556h3.936c-.093-1.414-.377-2.649-.766-3.556-.24-.56-.5-.948-.737-1.182C10.232 4.032 10.076 4 10 4zm3.971 5c-.089-1.546-.383-2.97-.837-4.118A6.004 6.004 0 0115.917 9h-1.946zm-2.003 2H8.032c.093 1.414.377 2.649.766 3.556.24.56.5.948.737 1.182.233.23.389.262.465.262.076 0 .232-.032.465-.262.238-.234.498-.623.737-1.182.389-.907.673-2.142.766-3.556zm1.166 4.118c.454-1.147.748-2.572.837-4.118h1.946a6.004 6.004 0 01-2.783 4.118zm-6.268 0C6.412 13.97 6.118 12.546 6.03 11H4.083a6.004 6.004 0 002.783 4.118z" clipRule="evenodd" />
      </svg>
    ),
  },
];

const iconStyles = {
  blue: "bg-blue/10 text-blue",
  purple: "bg-purple/10 text-purple",
  green: "bg-green/10 text-green",
} as const;

const steps = [
  {
    n: "01",
    title: "Paste the job posting",
    body: "Drop in the brief. Any Upwork job, any RFP, any project description. No formatting required.",
    color: "blue" as const,
  },
  {
    n: "02",
    title: "Confirm the interpretation",
    body: "We extract prospect, problem, budget, timeline in 3 seconds. You edit if anything's off. No black-box guessing.",
    color: "purple" as const,
  },
  {
    n: "03",
    title: "Send the result",
    body: "Cover letter ready to paste into Upwork (with the link to your proposal page already inserted). Public page renders for the prospect to read.",
    color: "green" as const,
  },
];

const stepColors = {
  blue: "bg-blue text-white",
  purple: "bg-purple text-white",
  green: "bg-green text-white",
} as const;

const faqs = [
  {
    q: "Why $5 per proposal and not a subscription?",
    a: "Subscriptions price for the heavy users and overcharge the light ones. Most freelancers send a handful of high-value proposals a week — pay-as-you-go fits that better. If you send 30+ proposals a month, write us; we'll work out a tier.",
  },
  {
    q: "What if the output isn't usable?",
    a: "Refund on request, no questions. We've also built in three regenerate-with-angle buttons (shorter, different angle, push back on price) so you can iterate without re-pasting the brief.",
  },
  {
    q: "How is this different from just using ChatGPT?",
    a: "ChatGPT will write you a cover letter that opens with 'I am excited to leverage my experience.' This won't. The constraint set — banned phrases, em-dash sanitization, brief-quoting requirements, sign-off discipline — is what produces output that doesn't pattern-match to AI. Plus you get the personalized page, which ChatGPT doesn't produce.",
  },
  {
    q: "Does it work for non-Upwork briefs?",
    a: "Yes. Any free-text project description works — RFPs, email threads, internal scoping notes. The engine is generic; the output style is tuned for freelancer-style proposals.",
  },
  {
    q: "Where does my data go?",
    a: "Your brief and your generated proposals stay in our database, scoped to your account via row-level security. We don't share, train on, or resell your data. Anthropic processes the brief during generation under their standard data terms.",
  },
  {
    q: "Can I edit the proposal after it's generated?",
    a: "You can regenerate with a different angle (shorter, different framing, push back on price). Inline editing of the rendered text is on the roadmap — not in this version.",
  },
];

export default function OneProposalPage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-accent/5 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-3xl px-6 py-20 text-center">
          <span className="mb-4 inline-flex items-center rounded-full bg-blue-bg px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-blue">
            OneProposal · by UnpauseAI
          </span>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            Upwork proposals that don't sound like ChatGPT.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-muted">
            Paste a job posting. Get a tailored cover letter and a personalized
            proposal page in 30 seconds. $5 per proposal, refunded on failure.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={`${APP_URL}/sign-up`}
              className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-accent/90 hover:shadow-lg"
            >
              Sign up &mdash; $5 per proposal
            </Link>
            <Link
              href="/contact"
              className="rounded-full border border-border px-6 py-3 text-sm font-medium transition-all hover:-translate-y-0.5 hover:bg-surface-hover"
            >
              Request a sample &rarr;
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted">
            No subscription. No trial gimmicks. Pay per generation, get the
            credit back if it fails.
          </p>
        </div>
      </section>

      {/* What you get strip (replaces the live-sample link block --
          live sample is on-request to avoid exposing prospect-named URLs
          on public unpauseai.com pages). */}
      <ScrollReveal>
        <section className="border-y border-border bg-surface/40">
          <div className="mx-auto max-w-3xl px-6 py-10 text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-muted">
              What ships in 30 seconds
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              A copy-paste-ready cover letter (5&ndash;25 lines) plus a public
              one-page proposal at a unique URL. Prospects open the link from
              the cover letter, read the full pitch on a clean page that looks
              like an agency built it. Want a real example before signing up?
              Use the sample request link above.
            </p>
          </div>
        </section>
      </ScrollReveal>

      {/* Features */}
      <ScrollReveal>
        <section className="mx-auto max-w-5xl px-6 py-20">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
              Why this exists
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted">
              ChatGPT writes the same proposal as 800 other applicants. We
              built the engine that doesn't.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="flex flex-col rounded-xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-lg"
              >
                <span
                  className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg ${iconStyles[f.color]}`}
                >
                  {f.icon}
                </span>
                <h3 className="mb-2 text-lg font-bold">{f.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{f.body}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* How it works */}
      <ScrollReveal>
        <section className="bg-surface/40">
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="mb-12 text-center">
              <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
                How it works
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-muted">
                Three steps. About 30 seconds. No setup beyond your profile.
              </p>
            </div>
            <div className="grid gap-6 md:grid-cols-3">
              {steps.map((s) => (
                <div
                  key={s.n}
                  className="rounded-xl border border-border bg-background p-6"
                >
                  <span
                    className={`mb-4 inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold ${stepColors[s.color]}`}
                  >
                    {s.n}
                  </span>
                  <h3 className="mb-2 text-lg font-bold">{s.title}</h3>
                  <p className="text-sm leading-relaxed text-muted">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Pricing */}
      <ScrollReveal>
        <section className="mx-auto max-w-3xl px-6 py-20">
          <div className="rounded-2xl border-2 border-accent bg-surface p-8 shadow-lg sm:p-12">
            <div className="text-center">
              <span className="mb-3 inline-block rounded-full bg-blue-bg px-3 py-1 text-xs font-semibold uppercase tracking-wider text-blue">
                Pricing
              </span>
              <div className="mb-2 text-5xl font-extrabold">
                $5
                <span className="ml-2 text-lg font-medium text-muted">
                  per proposal
                </span>
              </div>
              <p className="text-muted">
                One-time charge. Refunded if generation fails.
              </p>
            </div>
            <ul className="mx-auto mt-8 max-w-md space-y-3 text-sm text-muted">
              <li className="flex items-start gap-2">
                <svg
                  className="mt-0.5 h-4 w-4 shrink-0 text-green"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                Tailored cover letter (5–25 lines, voiced as you, not as ChatGPT)
              </li>
              <li className="flex items-start gap-2">
                <svg
                  className="mt-0.5 h-4 w-4 shrink-0 text-green"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                Personalized one-page site at a public URL the prospect can open
              </li>
              <li className="flex items-start gap-2">
                <svg
                  className="mt-0.5 h-4 w-4 shrink-0 text-green"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                Three regenerate-with-angle options (shorter / different angle /
                push back on price), 1 credit each
              </li>
              <li className="flex items-start gap-2">
                <svg
                  className="mt-0.5 h-4 w-4 shrink-0 text-green"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                Refund on request, no questions
              </li>
            </ul>
            <div className="mt-10 text-center">
              <Link
                href={`${APP_URL}/sign-up`}
                className="rounded-full bg-accent px-8 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-accent/90 hover:shadow-lg"
              >
                Start with one proposal
              </Link>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* FAQ */}
      <ScrollReveal>
        <section className="mx-auto max-w-3xl px-6 py-20">
          <h2 className="mb-10 text-center text-3xl font-extrabold tracking-tight sm:text-4xl">
            Questions
          </h2>
          <div className="space-y-4">
            {faqs.map((f) => (
              <details
                key={f.q}
                className="group rounded-xl border border-border bg-surface p-5 transition-all hover:border-accent/40"
              >
                <summary className="cursor-pointer list-none text-base font-semibold">
                  <span className="flex items-center justify-between gap-4">
                    {f.q}
                    <span className="text-muted transition-transform group-open:rotate-180">
                      <svg
                        className="h-4 w-4"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        aria-hidden
                      >
                        <path
                          fillRule="evenodd"
                          d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </span>
                  </span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* Final CTA */}
      <ScrollReveal>
        <section className="border-t border-border bg-surface/40">
          <div className="mx-auto max-w-2xl px-6 py-20 text-center">
            <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
              Ready to send proposals that get read?
            </h2>
            <p className="mx-auto mt-4 max-w-md text-muted">
              No subscription. No trial. Pay $5, get a proposal, send it. If
              it's not usable, the credit comes back.
            </p>
            <div className="mt-8">
              <Link
                href={`${APP_URL}/sign-up`}
                className="rounded-full bg-accent px-8 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-accent/90 hover:shadow-lg"
              >
                Start &rarr;
              </Link>
            </div>
          </div>
        </section>
      </ScrollReveal>
    </div>
  );
}
