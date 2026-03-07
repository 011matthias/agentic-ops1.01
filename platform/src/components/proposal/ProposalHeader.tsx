import type { ProposalFrontmatter } from "@/lib/proposals";

interface ProposalHeaderProps {
  frontmatter: ProposalFrontmatter;
}

export function ProposalHeader({ frontmatter }: ProposalHeaderProps) {
  return (
    <header className="border-b border-border pb-8 mb-10">
      <p className="text-sm font-medium text-accent uppercase tracking-wider mb-2">
        Proposal for {frontmatter.prospect}
      </p>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl mb-4">
        {frontmatter.project_title}
      </h1>
      <div className="flex flex-wrap gap-4 text-sm text-muted">
        {frontmatter.timeline && <span>Timeline: {frontmatter.timeline}</span>}
        {frontmatter.value_estimate && (
          <span>Investment: ${frontmatter.value_estimate}</span>
        )}
      </div>
    </header>
  );
}
