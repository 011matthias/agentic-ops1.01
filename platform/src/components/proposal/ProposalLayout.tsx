import type { Proposal } from "@/lib/proposals";
import { ProposalHeader } from "./ProposalHeader";
import { ProposalCTA } from "./ProposalCTA";

interface ProposalLayoutProps {
  proposal: Proposal;
  children: React.ReactNode;
}

export function ProposalLayout({ proposal, children }: ProposalLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
        <ProposalHeader frontmatter={proposal.frontmatter} />
        <article className="prose-custom">{children}</article>
        <ProposalCTA prospect={proposal.frontmatter.prospect} />
        <footer className="mt-16 border-t border-border pt-6 text-center text-xs text-muted">
          <p>UnpauseAI &mdash; Custom Automation Solutions</p>
        </footer>
      </div>
    </div>
  );
}
