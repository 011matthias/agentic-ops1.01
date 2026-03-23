import type { Proposal } from "@/lib/proposals";
import { ProposalHeader } from "./ProposalHeader";
import { ProposalCTA } from "./ProposalCTA";
import { ProposalTOC, ProposalTOCMobile } from "./ProposalTOC";

interface Heading {
  id: string;
  text: string;
  level: 2 | 3;
}

interface ProposalLayoutProps {
  proposal: Proposal;
  headings: Heading[];
  children: React.ReactNode;
}

export function ProposalLayout({ proposal, headings, children }: ProposalLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-6 py-12 sm:py-20 lg:grid lg:grid-cols-[220px_1fr] lg:gap-12">
        {/* Desktop TOC sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-24">
            <ProposalTOC headings={headings} />
          </div>
        </aside>

        {/* Main content */}
        <div className="min-w-0">
          <ProposalHeader frontmatter={proposal.frontmatter} />
          <ProposalTOCMobile headings={headings} />
          <article className="proposal-prose">{children}</article>
          <ProposalCTA prospect={proposal.frontmatter.prospect} />
        </div>
      </div>
    </div>
  );
}
