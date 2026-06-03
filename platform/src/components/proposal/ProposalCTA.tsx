"use client";

interface ProposalCTAProps {
  prospect: string;
}

export function ProposalCTA({ prospect }: ProposalCTAProps) {
  return (
    <section className="mt-16 rounded-xl border border-border bg-gradient-to-br from-accent/5 to-transparent p-8 text-center">
      <h2 className="text-xl font-bold text-foreground mb-3">
        Ready to get started?
      </h2>
      <p className="text-muted mb-6 max-w-md mx-auto">
        Reply to our message on the platform where we connected, or reach out
        directly.
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <a
          href="mailto:admin@unpauseai.com"
          className="inline-flex items-center rounded-full bg-accent px-8 py-3 text-sm font-medium text-white shadow-md transition-all hover:bg-accent-light hover:shadow-lg hover:-translate-y-0.5"
        >
          Let&apos;s Talk, {prospect}
        </a>
        <button
          onClick={() => window.print()}
          className="proposal-cta-print-btn inline-flex items-center gap-1.5 rounded-full border border-border px-6 py-3 text-sm font-medium text-muted transition-colors hover:bg-surface hover:text-foreground"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
            <path d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4H7v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Save as PDF
        </button>
      </div>
    </section>
  );
}
