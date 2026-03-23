const nodes = [
  {
    label: "Form Submission",
    tool: "Typeform / Tally",
    color: "blue" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Automation Engine",
    tool: "n8n",
    color: "purple" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Patient Record",
    tool: "Zoho CRM",
    color: "blue" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Email & SMS",
    tool: "Brevo + MessageBird",
    color: "green" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Booking",
    tool: "Cal.com",
    color: "blue" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Payment",
    tool: "Mollie",
    color: "green" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Monitoring",
    tool: "Dashboard",
    color: "purple" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: "Aftercare",
    tool: "Automated",
    color: "green" as const,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

const colorMap = {
  blue: {
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-200 dark:border-blue-800",
    icon: "text-blue-600 dark:text-blue-400",
    dot: "bg-blue-500",
  },
  purple: {
    bg: "bg-violet-50 dark:bg-violet-950/30",
    border: "border-violet-200 dark:border-violet-800",
    icon: "text-violet-600 dark:text-violet-400",
    dot: "bg-violet-500",
  },
  green: {
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    border: "border-emerald-200 dark:border-emerald-800",
    icon: "text-emerald-600 dark:text-emerald-400",
    dot: "bg-emerald-500",
  },
};

export function PatientJourneyFlow() {
  return (
    <div className="my-10 rounded-xl border border-border bg-surface p-6">
      <h3 className="text-base font-semibold text-foreground mb-1">
        How It All Connects
      </h3>
      <p className="text-xs text-muted mb-6">
        Your patient journey, fully automated end to end
      </p>

      {/* Desktop: horizontal flow */}
      <div className="hidden md:flex items-start gap-1 overflow-x-auto pb-2">
        {nodes.map((node, i) => {
          const c = colorMap[node.color];
          return (
            <div key={i} className="flex items-center shrink-0">
              <div
                className={`flex flex-col items-center w-[100px] rounded-lg border ${c.border} ${c.bg} p-3 transition-transform hover:-translate-y-0.5 hover:shadow-md`}
              >
                <div className={`${c.icon} mb-2`}>{node.icon}</div>
                <span className="text-[11px] font-semibold text-foreground text-center leading-tight">
                  {node.label}
                </span>
                <span className="text-[9px] text-muted text-center mt-1 leading-tight">
                  {node.tool}
                </span>
              </div>
              {i < nodes.length - 1 && (
                <svg width="20" height="20" viewBox="0 0 20 20" className="shrink-0 text-muted mx-0.5">
                  <path d="M4 10h12m-4-4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile: 2-column grid */}
      <div className="grid grid-cols-2 gap-3 md:hidden">
        {nodes.map((node, i) => {
          const c = colorMap[node.color];
          return (
            <div
              key={i}
              className={`flex items-center gap-2.5 rounded-lg border ${c.border} ${c.bg} p-3`}
            >
              <div className={`${c.icon} shrink-0`}>{node.icon}</div>
              <div>
                <span className="text-xs font-semibold text-foreground block leading-tight">
                  {node.label}
                </span>
                <span className="text-[10px] text-muted">{node.tool}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* GDPR badge */}
      <div className="mt-5 flex items-center gap-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 px-4 py-2.5">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0">
          <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div>
          <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">GDPR by Design</span>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 ml-2">
            Consent tracking at every data collection point. All tools EU-hosted. Medical data stays in EHR.
          </span>
        </div>
      </div>
    </div>
  );
}
