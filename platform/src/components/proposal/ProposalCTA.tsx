interface ProposalCTAProps {
  prospect: string;
}

export function ProposalCTA({ prospect }: ProposalCTAProps) {
  return (
    <section className="mt-12 border-t border-border pt-8 text-center">
      <h2 className="text-xl font-semibold mb-3">Ready to get started?</h2>
      <p className="text-muted mb-6">
        Reply to our message on the platform where we connected, or reach out
        directly.
      </p>
      <a
        href="mailto:hello@unpauseai.com"
        className="inline-block rounded-full bg-accent px-8 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
      >
        Let&apos;s Talk, {prospect}
      </a>
    </section>
  );
}
