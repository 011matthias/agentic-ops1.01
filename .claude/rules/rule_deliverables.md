# Deliverable Standards

**HTML deliverables.** Self-contained HTML files (infographic, dashboard, doc site, tool) MUST include:
1. Dark/light mode toggle (pill button, `[data-theme]` CSS, localStorage persistence)
2. Copy-to-clipboard on code/command blocks (hover-reveal, brief feedback)
3. Keyboard search (Ctrl/Cmd+K, visible hint)
4. Filter/search state persistence (localStorage)

**HTML deliverables MUST NOT include:**
- Emoji icons in sidebar/left-nav. Plain text labels only. Reason: client directive 2026-05-08 ("ERADICATE THE EMOJIS FROM THE WEBSITE LEFT SIDE NAVIGATION BAR"). Applies retroactively to existing pages, not just new ones.
- Any form of em-dash. Banned: `—` (U+2014), `&mdash;` entity, AND `--` as a typographic substitute. Reason: client directive 2026-05-08 ("NO MORE EM DASHES EITHER ... DO NOT REPLACE EM DASHES WITH DOUBLE DASHES"). Use commas, semicolons, colons, or split into separate sentences. This is stricter than the "max 2" rule in the PDF voice pass below; for HTML it is zero.
- Stale or fabricated dates. Every date stamp must reflect the actual day the document was prepared or last updated. Update `Last updated:` footers on every meaningful edit.

**HTML structural validation.** Before deploying any self-contained HTML, run `uv run tools/validate-html.py {files}`. Fix all failures before deploy. For multi-page sets, run in directory mode to check cross-page consistency. This is a B2 gate extension — failing validation = do not deploy.

**Static HTML paths (Vercel).** Always use absolute paths between static HTML files. Vercel cleanUrls + trailingSlash:false breaks relative paths on nested routes.

**Client-facing content accuracy.** Every number, field name, and config value must trace to a queried source. Unverified = "TBD". See B4 gate in rule_behaviors.md.

**Brand accuracy.** For platform work, read `workspace/projects/platform/context/brand.md` at session start. Never assume brand name spelling or contact info.

## Video script humanness (proposal Loom walkthroughs)

Video scripts must read like a human speaking, not like written technical notes. The spoken-aloud parts (lines prefixed `SAY:`) are heard, not read — jargon and abbreviations land badly in the ear. Authenticity is the core differentiator on Upwork; unexplained jargon makes the proposer sound like a written-by-AI list rather than a person who understands the problem. Proposals win or lose on the first 30 seconds of the Loom.

**Rules for `SAY:` lines:**

1. **Plain human language by default.** "Embeddings turn each product into a vector" not "OpenAI text-embedding-3-small embeds the catalog."
2. **Any abbreviation needs a 3-8 word inline gloss the first time it appears**, unless it's as universal as: AI, API, UI, URL, HTML, CSS, JS, JSON, XML, SQL, OS, CSV, HTTP, HTTPS, PDF, TCP, IP, DNS, CRM, CEO, CTO, CFO, COO, CMO, VP, B2B, B2C, KPI, ROI, IT, HR, PR, QA, UX, EU, US, UK, USA, EMEA, APAC, FAQ, AM, PM, TBD, OK.
3. **Examples of correct glossing:**
   - "the SKU, the product code each supplier uses to identify an item"
   - "FAISS or sqlite-vec, two libraries for fast similarity search"
   - "a vector database like Pinecone"
   - "a small focused language model call" (not "LLM call")
   - "a command-line search tool" (not "CLI search")
   - "with their JavaScript library" (not "JS SDK")
   - "the first working MVP, the minimum viable product"

**Exempt sections (abbreviations OK):**
- `>>` lines — stage directions, not spoken
- `## LOOM NOTES VERSION` block — silent teleprompter cues
- Tool/library proper nouns (Algolia, Pinecone, FAISS, Streamlit) are not abbreviations; they're names. Still benefit from one-line explanations on first mention.

**Enforcement.** `tools/validate-proposal.py` `check_video_script_abbreviations()` scans `SAY:` lines, slices out LOOM NOTES, and **FAILs** on any non-exempt abbreviation without a gloss within 120 chars of first occurrence. This is a B2 gate extension — fix before sending the proposal. Backed by `feedback_video_script_human_language.md`.

## PDF deliverable protocol

PDF generation is a high-stakes deliverable, not a quick output. This protocol fires on every PDF request without the user having to invoke it. Skipping any step is a friction event (`pdf-protocol-skipped`).

**Step 1. Format question first.** Before drafting or generating anything, ask the user which of three formats fits:

- **Short and valuable** — 2 to 5 pages. Max signal-to-page ratio. Tight prose, minimal tables. For executive summaries, client one-pagers, distilled insights.
- **Long and extensive** — 8 to 20+ pages. Comprehensive reference. Detailed tables, full appendices. For audits, inventories, technical reference, anything where completeness matters more than brevity.
- **Graphs and visuals** — visual-first document built around charts, diagrams, comparison visuals. Prose supports the visuals, not the other way around. For data presentations, performance reports, anything where the picture is the point.

Wait for the user's pick. Do not assume. If the chosen format doesn't fit the content (e.g., "short and valuable" requested for material that's clearly a 15-page inventory), recommend the alternative rather than silently compromising.

**Step 2. Read `/mnt/skills/public/pdf/SKILL.md`** (or current equivalent) to refresh on PDF generation in this environment.

**Step 3. Build a fact inventory with attribution before drafting.** Every fact, number, quote, name, and table row tracked back to its source (screenshot, correction, derived). The inventory is the reference for verification in step 5.

**Step 4. Draft in markdown.**

**Step 5. Triple verification, three independent passes (not one combined check):**

- **Source verification.** Every number, name, table row, and quoted fragment traces to a specific source. Unsourced facts become flagged gaps in the document, never omitted-pretending-verified, never filled from memory.
- **Internal consistency.** Subtotals add to totals. Variant counts match step totals. Quoted numbers match elsewhere in the document. Discrepancies flagged explicitly, not hidden.
- **Claim-vs-evidence.** For every finding, re-read the evidence and ask: does it support this claim, or am I overstating? Downgrade any finding where the evidence is thinner than the claim.

**Step 6. Voice pass against banned constructions:**

- No "not just X but Y" constructions
- No three-part lists where two work; vary sentence shape
- No "it's important to note", "keep in mind", "worth mentioning", meta-commentary about the writing
- Em-dashes (and `&mdash;`, `--`): zero in HTML deliverables per the "MUST NOT include" rule above. For markdown drafts and PDFs, still keep to zero or one. The "max 2" framing is retired.
- No corporate-thesaurus: robust, leverage, ensure, facilitate, comprehensive, streamline, optimize, holistic, drive, unlock
- No sentence-opening adverbs (Notably, Importantly, Interestingly)
- No "in summary", "in conclusion", "to summarize"
- No section intros that summarize what the section is about to say
- Contractions in prose, full forms in table cells
- Specificity over abstraction
- No performed humanness either (no "Honestly,", "Look,", "Here's the thing")

**Step 7. Draft-review gate — non-negotiable.** Show the user the markdown draft AND the list of facts that couldn't be cleanly sourced. Wait for review. Catching issues in markdown is fast; regenerating PDFs is slow.

**Step 8. After user review, generate the PDF.** Save to a sensible location with a clear filename including the date. Report the path.

**Ambiguity surfacing.** If source material is ambiguous or self-contradicting, surface as a question during step 4 or 5 rather than picking an answer silently. Pause and ask beats publish-wrong-fact-confidently.

**Reliability target.** When the user opens the PDF, they should not be the one catching factual errors, arithmetic mismatches, AI-tell phrasings, or padding. If they are, the process failed before reaching them.
