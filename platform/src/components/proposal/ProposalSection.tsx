interface ProposalSectionProps {
  title: string;
  children: React.ReactNode;
}

export function ProposalSection({ title, children }: ProposalSectionProps) {
  return (
    <section className="mb-10">
      <h2 className="text-xl font-semibold mb-4 tracking-tight">{title}</h2>
      <div className="text-foreground/80 leading-relaxed space-y-4">
        {children}
      </div>
    </section>
  );
}
