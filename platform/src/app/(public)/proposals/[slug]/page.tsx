import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import { getProposalBySlug, getProposalSlugs, extractHeadings, slugify } from "@/lib/proposals";
import { ProposalLayout } from "@/components/proposal/ProposalLayout";
import { ProposalTable } from "@/components/proposal/ProposalTable";
import { ProposalTimeline } from "@/components/proposal/ProposalTimeline";
import { PatientJourneyFlow } from "@/components/proposal/PatientJourneyFlow";
import type { Metadata } from "next";

const mdxComponents = {
  h2: ({ children, ...props }: React.ComponentPropsWithoutRef<"h2">) => (
    <h2 id={slugify(String(children))} className="proposal-h2" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: React.ComponentPropsWithoutRef<"h3">) => (
    <h3 id={slugify(String(children))} className="proposal-h3" {...props}>
      {children}
    </h3>
  ),
  p: (props: React.ComponentPropsWithoutRef<"p">) => (
    <p className="text-foreground/80 leading-relaxed mb-4" {...props} />
  ),
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="list-disc pl-6 space-y-2 text-foreground/80 mb-4" {...props} />
  ),
  ol: (props: React.ComponentPropsWithoutRef<"ol">) => (
    <ol className="list-decimal pl-6 space-y-2 text-foreground/80 mb-4" {...props} />
  ),
  li: (props: React.ComponentPropsWithoutRef<"li">) => (
    <li className="leading-relaxed" {...props} />
  ),
  strong: (props: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-semibold text-foreground" {...props} />
  ),
  table: (props: React.ComponentPropsWithoutRef<"table">) => (
    <ProposalTable {...props} />
  ),
  th: (props: React.ComponentPropsWithoutRef<"th">) => (
    <th className="proposal-th" {...props} />
  ),
  td: (props: React.ComponentPropsWithoutRef<"td">) => (
    <td className="proposal-td" {...props} />
  ),
  tr: (props: React.ComponentPropsWithoutRef<"tr">) => (
    <tr className="proposal-tr" {...props} />
  ),
  a: (props: React.ComponentPropsWithoutRef<"a">) => (
    <a className="proposal-link" {...props} />
  ),
  blockquote: (props: React.ComponentPropsWithoutRef<"blockquote">) => (
    <blockquote className="proposal-blockquote" {...props} />
  ),
  hr: (props: React.ComponentPropsWithoutRef<"hr">) => (
    <hr className="proposal-hr" {...props} />
  ),
  code: (props: React.ComponentPropsWithoutRef<"code">) => (
    <code className="proposal-code" {...props} />
  ),
  pre: (props: React.ComponentPropsWithoutRef<"pre">) => (
    <pre className="proposal-pre" {...props} />
  ),
};

export async function generateStaticParams() {
  const slugs = getProposalSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const proposal = getProposalBySlug(slug);
  if (!proposal) return { title: "Proposal Not Found" };

  return {
    title: `${proposal.frontmatter.project_title} | UnpauseAI`,
    description: `Proposal for ${proposal.frontmatter.prospect}: ${proposal.frontmatter.project_title}`,
  };
}

export default async function ProposalPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const proposal = getProposalBySlug(slug);

  if (!proposal) {
    notFound();
  }

  const headings = extractHeadings(proposal.content);
  const showPatientJourney = slug === "menovia-patient-journey-automation";

  return (
    <ProposalLayout proposal={proposal} headings={headings}>
      <MDXRemote source={proposal.content} components={mdxComponents} />
      {showPatientJourney && <PatientJourneyFlow />}
      {proposal.frontmatter.phases && (
        <ProposalTimeline phases={proposal.frontmatter.phases} />
      )}
    </ProposalLayout>
  );
}
