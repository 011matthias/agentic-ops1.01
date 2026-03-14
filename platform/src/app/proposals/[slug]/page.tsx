import { notFound } from "next/navigation";
import { MDXRemote } from "next-mdx-remote/rsc";
import { getProposalBySlug, getProposalSlugs } from "@/lib/proposals";
import { ProposalLayout } from "@/components/proposal/ProposalLayout";
import { ProposalSection } from "@/components/proposal/ProposalSection";
import type { Metadata } from "next";

const mdxComponents = {
  h2: ({ children, ...props }: React.ComponentPropsWithoutRef<"h2">) => (
    <ProposalSection title={String(children)} {...props}>
      <></>
    </ProposalSection>
  ),
  p: (props: React.ComponentPropsWithoutRef<"p">) => (
    <p className="text-foreground/80 leading-relaxed mb-4" {...props} />
  ),
  ul: (props: React.ComponentPropsWithoutRef<"ul">) => (
    <ul className="list-disc pl-6 space-y-2 text-foreground/80" {...props} />
  ),
  ol: (props: React.ComponentPropsWithoutRef<"ol">) => (
    <ol
      className="list-decimal pl-6 space-y-2 text-foreground/80"
      {...props}
    />
  ),
  li: (props: React.ComponentPropsWithoutRef<"li">) => (
    <li className="leading-relaxed" {...props} />
  ),
  strong: (props: React.ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-semibold text-foreground" {...props} />
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
    title: `${proposal.frontmatter.project_title} | UnpausAI`,
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

  return (
    <ProposalLayout proposal={proposal}>
      <MDXRemote source={proposal.content} components={mdxComponents} />
    </ProposalLayout>
  );
}
