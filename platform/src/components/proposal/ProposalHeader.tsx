import type { ProposalFrontmatter } from "@/lib/proposals";

interface ProposalHeaderProps {
  frontmatter: ProposalFrontmatter;
}

export function ProposalHeader({ frontmatter }: ProposalHeaderProps) {
  const value = frontmatter.value_estimate;
  const displayValue = /^\d/.test(value) ? `EUR ${value}` : value;

  return (
    <header className="border-b border-border pb-8 mb-10">
      <span className="inline-flex items-center rounded-full bg-accent/10 text-accent px-3 py-1 text-xs font-semibold uppercase tracking-wider mb-4">
        Proposal for {frontmatter.prospect}
      </span>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl text-foreground mb-5">
        {frontmatter.project_title}
      </h1>
      <div className="flex flex-wrap gap-3">
        {frontmatter.timeline && (
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-foreground/70">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
              <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {frontmatter.timeline}
          </span>
        )}
        {value && (
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-foreground/70">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
              <path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {displayValue}
          </span>
        )}
      </div>
      {frontmatter.tags && frontmatter.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-4">
          {frontmatter.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-surface-hover px-2.5 py-0.5 text-[11px] font-medium text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
