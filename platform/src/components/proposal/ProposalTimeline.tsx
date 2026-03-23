interface Phase {
  name: string;
  weeks: string;
  price?: string;
  items: string[];
}

interface ProposalTimelineProps {
  phases: Phase[];
}

const phaseColors = [
  { border: "border-l-accent", badge: "bg-accent/10 text-accent", dot: "bg-accent" },
  { border: "border-l-emerald-500", badge: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400", dot: "bg-emerald-500" },
  { border: "border-l-violet-500", badge: "bg-violet-500/10 text-violet-600 dark:text-violet-400", dot: "bg-violet-500" },
  { border: "border-l-amber-500", badge: "bg-amber-500/10 text-amber-600 dark:text-amber-400", dot: "bg-amber-500" },
];

export function ProposalTimeline({ phases }: ProposalTimelineProps) {
  return (
    <div className="my-10">
      <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
        {phases.map((phase, i) => {
          const color = phaseColors[i % phaseColors.length];
          return (
            <div key={i} className="flex-1 flex flex-col lg:flex-row lg:items-stretch">
              <div
                className={`flex-1 rounded-lg border border-border ${color.border} border-l-4 bg-surface p-5 shadow-sm transition-shadow hover:shadow-md`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${color.badge}`}>
                    Week {phase.weeks}
                  </span>
                  {phase.price && (
                    <span className="text-xs font-medium text-muted">
                      {phase.price}
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-2">
                  {phase.name}
                </h3>
                <ul className="space-y-1">
                  {phase.items.map((item, j) => (
                    <li key={j} className="flex items-start gap-2 text-xs text-foreground/70">
                      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${color.dot}`} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              {i < phases.length - 1 && (
                <div className="hidden lg:flex items-center px-2">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-muted">
                    <path d="M5 12h14m-6-6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
