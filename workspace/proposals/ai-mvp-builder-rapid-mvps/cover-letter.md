Hi there,

Loom walkthrough plus the full scenario answer: https://unpauseai.com/clients/ai-mvp-builder-rapid-mvps/ (access code: ai-mvp-builder-2026)

Here's how I'd ship the 2,000-product MVP, detailed enough that you can decide if my thinking matches yours before any code is written.

The shape I'd use: targeted AI for the judgment parts, deterministic code for everything else. Embeddings are great at "these two product titles mean roughly the same thing" but terrible at "Phillips screwdriver is not Philips electronics." So I'd let a small focused LLM call handle similarity and category inference, then put hard rules on top for brand and category boundaries. That's the pattern I use in production work, and it's why those systems tend to work on the first run rather than after weeks of debugging.

The site includes:
- A detailed solution page walking through the full pipeline (ingest, dedupe, embed, search with confidence scores, UI)
- The runnable Python skeleton you can download and run on a sample CSV
- A timeline page (paid test first, week 1 MVP, week 2 UI, iteration after)
- An investment page comparing custom vs Algolia vs Pinecone with real tradeoffs
- An FAQ covering buy vs build, accuracy, handoff, and scope changes
- An onboarding page describing the paid test shape

Week one, two pieces. Ingest every supplier CSV through one normalize function, dedupe with a fuzzy match on SKU plus brand plus a spec hash, flag missing-spec rows into a triage queue rather than dropping them. Match: embed each product with OpenAI text-embedding-3-small, store vectors in FAISS or sqlite-vec, expose a CLI search returning top-K with visible confidence scores. Week two: a thin Next.js or Streamlit UI with search, compare view, and a "this match is wrong" feedback button.

On your "buy vs build" line: if your supplier feeds turn out cleaner than I'm assuming, a hosted product search like Algolia or a vector DB like Pinecone might cover this at low monthly cost with zero engineering. I'd want to see real data before quoting custom work over a SaaS.

Happy to start with the small paid test you described. Pick 200-500 products and 2-3 suppliers, I'll ship a working tool in 10 hours fixed at $400, with the matching code, docs, and a handoff so you're not dependent on me afterward. If we move forward from there, the MVP estimate gets tightened on actual numbers rather than guesses.

Cheers,
Matthias
UnpauseAI
