# Proposal Templates

## Template 0 — Short Hook (current default, <=225 chars)

Owner directive 2026-06-09: the cover letter is now a single hook of at most
225 characters on BOTH tracks. It does three jobs in order, then points to the
walkthrough. The Loom link + site URL + access code sit below a `---` divider
and are not counted in the 225. The validator enforces the cap
(`Cover letter hook <=225 chars`).

The three jobs, in one tight block:

1. **Understanding** — name their specific problem, echo a phrase from the post.
2. **Proof** — one concrete piece of comparable past work (not a credential dump).
3. **Implementation** — the fix in a clause, plus a pointer to the walkthrough.

```text
# Cover Letter -- {Prospect} ({id})

{Hook: <=225 chars. Understanding + proof + short implementation + walkthrough pointer.}

---
Walkthrough: {VIDEO_LINK}
Full plan: https://unpauseai.com/clients/{slug}/  (access code: {access_code})
```

Worked example (211 chars):

```text
Your Meta leads dying in spam is almost always auth + sending the wrong way. I run this exact stack daily (Instantly, SPF/DKIM/DMARC) for a lead-gen client. Fix: authenticate the domain, split warm from cold, verify every lead lands. 2-min walkthrough:
```

Drafting discipline:
- Write the full thought first, then cut to 225. The cut IS the craft.
- Lead with their problem, not "Hi, I can help."
- One proof, the most relevant. A second proof is noise at this length.
- The implementation is a clause, not a plan. The plan lives in the video/site.
- Count characters, not lines or words. Use the validator to confirm.

The long-form bodies below (Templates 1 and 2) are RETIRED as cover letters.
Keep them only as a thinking aid: they show the reasoning that the hook now
compresses. Do not ship a multi-paragraph cover letter.

## Template 1 — Short (Video-Led) [RETIRED as a letter; thinking aid only]

Best for: jobs where a video walkthrough is the primary proof.

```
Hi -- I'm confident I'm a strong fit for this, so instead of overselling,
I recorded a short walkthrough showing how I'd structure your automation:
[link]

From what I see, the key piece is making sure {core challenge},
especially around {specific edge case}.

I've worked on similar systems where reliability matters, so I tend to
design these flows with clear routing logic and fallback handling
from the start.

Happy to extend this further if useful.
```

**Why it works:** Starts with proof, shows understanding, stays tight.

## Template 2 — Longer (Peer-Tone)

Best for: more complex jobs where you need to show deeper thinking.

```
Hello -- I work on systems like this regularly, so I put together a short
walkthrough where I outline and partially build your setup:
[link]

The main thing I focused on is structuring the pipeline so {data/process}
moves cleanly from {input} to {output}, without silent failures.

My background is in automation systems and workflow design, with a focus
on building things that hold up under real usage, not just ideal conditions.

If you want to go deeper, I can extend this into a full implementation.
```

**Why it works:** Sounds like a peer, not an applicant. No hype. Clear thinking.

## Adaptation Rules

1. **Always customize** the `{core challenge}` and `{specific edge case}` placeholders with language from the job post
2. **Never copy templates verbatim** — they're structures, not scripts
3. **Video link is the anchor** — everything else supports it
4. **Keep it short** — if you can say it in 4 lines, don't use 8
5. **Reference `feedback_upwork_formatting.md`** for Upwork-specific formatting (plain text, numbered sections, no markdown)

## Success Criteria

After reading the proposal, the client should think:
- "This person gets it"
- "This already makes sense"
- "I want to talk to them"

## Failure Signals

- Generic (could apply to any job)
- Skill-focused (tools and years, not understanding)
- Too long (more than ~8 lines for Upwork)
- Unclear (no specific reference to their problem)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Explaining instead of showing | Record a video |
| Presenting multiple ideas | ONE system, one artifact |
| Writing before thinking | Decompose the job first (see SYSTEM-THINKING.md) |
| Trying to impress | Demonstrate understanding instead |
| Opening with credentials | Open with proof or insight |
| Asking obvious questions | Answer them in the proposal |