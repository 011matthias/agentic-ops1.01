### Opening

SAY: Hi there, Matthias here.

SAY: You asked for a detailed answer to the 2,000-product scenario in the proposal itself, so this video is exactly that. I'm going to walk through how I'd ship the first working MVP, what the failure modes are, and where I'd push back on the spec.

>> Open the proposal site at unpauseai.com/clients/ai-mvp-builder-rapid-mvps

---

### Beat 1, Reframe

SAY: The way I'm reading this: the real problem isn't "build a search tool." It's that 2,000 products live across multiple supplier feeds in inconsistent shape, and your team can't trust the data when they're trying to find compatible alternatives. Search is the visible symptom. The data layer is the root.

SAY: So the MVP has to do two things in week one: clean the data well enough that search is trustworthy, and ship a search interface that actually proves it. If we only ship one of those, the tool gets ignored.

---

### Authority

SAY: The way I build AI automation is targeted AI for the judgment calls plus deterministic code for everything else. Small focused LLM calls where they earn their cost, rules and validation everywhere else. Every build ships with documentation, tests, and a handoff so the client isn't dependent on me to keep it running.

SAY: That's relevant here because the win on this project isn't the slickest search UI, it's the matching being right often enough that the team starts trusting it, and that comes from the deterministic layer, not the AI layer.

---

### Beat 2, Structure

>> Click Solution in top nav

SAY: Here's the pipeline. Step one, ingest. Load every supplier CSV into a single normalize function. Lowercase, strip whitespace, parse numeric specs out of free-text fields, generate a deterministic content hash per row so we can detect duplicates across feeds.

SAY: Step two, dedupe and flag. Fuzzy match on normalized SKU plus brand plus a spec hash. Rows that match get merged with provenance kept. Rows missing critical specs get flagged into a triage queue, not dropped.

SAY: Step three, embed. OpenAI text-embedding-3-small on title plus brand plus normalized specs. Store vectors in FAISS or sqlite-vec, whichever fits the deploy target. Re-embed only on row changes. Cache aggressively.

SAY: Step four, search. Query goes through the same embed function, top-K by cosine similarity, results scored with a confidence number the team can see. That score is important. It tells the user "this match is 0.91, trust it" versus "this match is 0.62, double-check."

SAY: Step five, UI. Thin Next.js or Streamlit interface. Search box, result cards with confidence, compare view side-by-side, a "this match is wrong" button that writes corrections to a table I can use to retrain ranking later.

---

### Beat 3, Edge cases and tradeoffs

>> Click FAQ in top nav

SAY: Three things I'd flag before writing any code.

SAY: First, embeddings are not magic. They confuse product names that sound similar but mean different things. Phillips screwdriver versus Philips electronics. So I'd add a hard categorical filter before the similarity search: brand and category match required, then rank by embedding similarity within that filtered set.

SAY: Second, the duplicate problem is harder than it looks. Same product across suppliers often has slightly different specs because suppliers measure differently. My approach is to keep both rows, flag them as candidate-duplicates with a confidence score, and let the team confirm or split rather than auto-merge.

SAY: Third, and this matters to your "buy vs build" line in the post: if your supplier feeds are cleaner than I'm assuming, a hosted product search like Algolia or a vector DB like Pinecone plus their JS SDK might solve this at low monthly cost and zero engineering time. I'd want to see the real data before I'd quote you a build versus pointing you at a SaaS.

---

### Beat 4, What ships when

>> Click Timeline in top nav

SAY: Week one: ingest plus dedupe plus embed plus CLI search. That's the runnable skeleton, downloadable from the site right now if you want to look. Real data, two suppliers, 200 products, end to end.

SAY: Week two: the team UI. Whichever framework matches your stack. If you're already on Next.js, that. If not, Streamlit ships faster and is easier to throw away later.

SAY: Week three onward: iteration. Watch what the team actually searches for. Tune ranking, add filters, add the corrections feedback loop. The thing that makes this work over time is the feedback loop, not the initial model.

---

### Beat 5, Close

>> Click Onboarding in top nav

SAY: You mentioned a small paid test project to start. That's the right shape. Pick a slice of real data, 200 to 500 products, two or three suppliers. I'll ship a working tool in ten hours fixed at four hundred dollars. You see the actual code, the actual matching quality on your actual data, and we both find out fast whether this is the right fit.

SAY: If it's a fit, we go to the week-one MVP on the full 2,000. If not, you've spent four hundred dollars and learned something concrete about what your data needs.

SAY: Skeleton is on the proposal site. Cheers.

---

## LOOM NOTES VERSION

- Reframe: real problem is messy data, not search. Both must ship in week one.
- Authority: targeted AI plus deterministic code. Docs, tests, handoff with every build. Trust comes from the deterministic layer, not the AI layer.
- Pipeline: ingest, dedupe-flag, embed, search, UI. Walk Solution page top to bottom.
- Edge case 1: categorical filter before similarity. Phillips vs Philips example.
- Edge case 2: dedupe with confidence flag, no auto-merge.
- Tradeoff: if data is clean, Algolia or Pinecone may be the low-cost answer. Say so.
- Timeline: w1 CLI MVP, w2 UI, w3+ feedback loop.
- Close: paid test = 200-500 products, 10hr, $400 fixed. Skeleton on the site.
- Open with proposal URL on screen. Walk pages in order via top nav: Solution, FAQ, Timeline, Onboarding.
