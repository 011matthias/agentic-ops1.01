# Anti AI-Slop Standard (Layer 2 voice rule)

**Hard constraint.** Every paragraph, bullet, sentence, and section
in any agent-written artifact has to earn its keep. Volume that does
not carry novel information is slop. Slop dilutes signal: every
unearned paragraph teaches the reader to skim, and in client-facing
context it reads as AI-generated even when the underlying judgment
is human-quality.

This rule is the canonical home for the enumerated voice bans (the
corporate-thesaurus words, banned meta-phrases, "not just X but Y",
performed-humanness, sentence-opening adverbs). The surface rules
reuse this list by cross-reference and add only their surface-specific
deltas: [[rule_deliverables]] (HTML/PDF), [[rule_platform_standards]]
§2 (marketing site), [[rule_human_communication]] §2 (outbound). It
supersedes the older PDF voice pass in `rule_deliverables.md` (still
valid, narrower).

## What counts as slop (banned)

**Per-category narration on intuitive variance.** When N values vary
across N categories under ONE intuitive structural rule, state the
rule once and stop. Do not give each category a sentence of similar
shape and similar information density. The smell: every row reads
"category X is large/small because reason X" with the same sentence
shape. If the structural rule is itself intuitive once stated, the
narration is slop. Source: 2026-06-01 meji corporate-sample bloat
on universe-size variance. See [[feedback_no_per_category_narration]].

**Three-part lists where two work.** Symmetry of categories is NOT a
reason to enumerate. If three bullets read in the same shape with
the same information density, collapse them.

**Empty section intros.** Do not start a section by summarizing what
the section is about to say. Just start it.

**Hedging / buffer language.** "It's worth noting", "it's important
to note", "to be clear", "keep in mind", "worth mentioning", "as you
can see", and similar meta-commentary about the writing itself. Cut.

**Corporate thesaurus.** Banned verbs: robust, leverage, ensure,
facilitate, comprehensive, streamline, optimize, holistic, drive,
unlock, empower. Banned adverbs at sentence open: notably,
importantly, interestingly, ultimately, fundamentally, essentially.

**Performed humanness.** "Honestly,", "Look,", "Here's the thing,",
"At the end of the day". The opposite failure mode of corporate
thesaurus, equally slop.

**Em-dashes.** Zero in client-facing HTML / PDF / web deliverables
per `rule_deliverables.md`. Auto-stripped by the
`em-dash-strip-gate.py` hook on Write/Edit to client paths.

**"Not just X but Y" constructions.** "This is not just a sample,
it's a strategic framework." Banned. Just say what it is.

**Headings that re-state the body.** If an H3 reads "Why X Happens"
and the body says "X happens because Y," fold the heading into the
body sentence. The H3 adds no signal.

**Closing meta-summary.** "In summary", "in conclusion", "to
summarize", "the bottom line". The last sentence of the section IS
the close; do not announce it.

**Invented or padded sections (IA-level slop).** The prose bans above
have a structural sibling: a *section* the content does not support is
slop at the information-architecture level. A stat band with no real
metric, an evidence block with no real proof, a three-card row padded
to three for symmetry. Structure follows content: a section exists
because the content earns it, never because "a page like this usually
has one." Thin content is a signal to surface and ask, not a gap to
fill with an invented claim, metric, testimonial, or logo. This is the
IA-derivation-time catch; B4 and `validate-output.py` `unsourced-claim`
are the downstream backstop. Source: 2026-06-17 content-adaptive
prototype work (Brisken OnePilot hero `81%` off n=21, `#why-now`
three-symmetric-card row); operationalized in the `skil_prototype`
front end.

## What is NOT slop (allowed)

- Per-category narration where each category breaks the pattern in
  a way the reader cannot infer (e.g., "CEO segment is the smallest
  because Apollo under-indexes UK family businesses at that band" is
  non-obvious operator judgment, earns the sentence).
- Lists with variable sentence shape and unique information per row.
- Specific facts and numbers with sources, even when "long" — length
  earned by load-bearing detail is not slop.
- Brief contextual note before a code/config block ("the SPF push
  drops the Porkbun include") is necessary scaffolding, not slop.

## The golden middle (the register the bans serve)

The bans above kill one failure mode; over-correcting into the other is
its own. Writing that is exact but cold, clinical, or affectless reads
as machine-authored too, and loses the reader as fast as padding does.
Two poles to stay off:

- **Slop:** padded, evenly-paced, hedged, symmetric, corporate. An
  agent performing thoroughness.
- **Cold:** jargon-walled, affectless, or retreating into vague
  non-committal hedging to avoid stating the exact thing
  (imprecision-as-safety). An agent performing rigor.

The middle is direct, precise, and warm at once: say the exact thing,
in plain words, the way a sharp human peer would say it aloud, and
commit to it.

- One clear claim per sentence; no padding, no retreat into vagueness.
  Precision is stating what is true, not hedging so nothing can be wrong.
- Keep the terms that carry meaning; drop the ones that only perform.
- Warmth is plain directness written to a person, not performed
  friendliness or stacked adjectives.
- Name uncertainty precisely (B4, [[rule_behaviors]]) rather than
  smearing it into hedge-language.

Test: read it aloud as if a sharp colleague said it to you. If it sounds
like someone who knows the subject and respects you, it passes; if it
reads like a brochure (slop pole) or a compliance memo (cold pole),
rewrite.

Source: 2026-07-20 owner directive (meji ROI page): clean and direct,
language that does not defer to imprecision, no need to be cold or
ruthlessly precise, find the golden middle. Cross-surface: this governs
every agent-authored human-facing artifact (client pages, deliverables,
outbound messages), inherited by the surface rules that already
reference this file.

## Required protocol

Before publishing a paragraph, bullet, sentence, or section into
any agent-written artifact, run the slop check at write-time:

1. **Information-per-token check.** Does each sentence carry novel
   information that the prior sentences did not establish? If no,
   delete the sentence.
2. **Symmetry-collapse check.** Do my bullets / paragraphs read in
   the same shape with the same information density? If yes,
   collapse to a single statement of the underlying rule.
3. **Heading-earns-it check.** Does this H2/H3/H4 add a navigation
   anchor I will reference, OR introduce a body that itself adds
   signal? If neither, drop the heading and fold the body into the
   surrounding flow.
4. **Voice scan.** Sentence by sentence, scan for banned constructions
   above. Fix in place.

For deliverables that pass through the PostToolUse dispatcher
(`platform/public/`, `workspace/clients/*/deliverables/`,
`workspace/clients/*/context/drafts/`), the validators
`validate-output.py` and `lint-comms-draft.py` already catch some
banned constructions (em-dashes via strip gate, cost-anchor drift,
unsourced claims), and since 2026-07-22 flag suspected
symmetry-collapse and per-category narration as LOW advisories (see
Enforcement). Information-per-token stays agent discipline; the slop
check is still the gate that decides.

## Why

Three failure modes converge on this rule:

1. **Performed thoroughness.** Writing more paragraphs to "look
   thorough" when transparency requires brevity. The bloat reads as
   uncertainty padded with words.
2. **Symmetry illusion.** N categories triggers N sentences because
   the structure of the data feels like it demands the structure of
   the prose. It doesn't.
3. **AI-tell.** Bloated, evenly-paced, per-category narration is the
   strongest AI-output tell across every client-facing surface. On
   Upwork-style trust contexts, this is direct credibility damage.

Repeated user corrections at 2026-05-30 (mejievent routing slop in
draft) and 2026-06-01 (universe-variance narration on
corporate-sample) escalated this from per-incident memory to a
rule-layer standard.

## Enforcement

Honored at write-time by the agent on every paragraph, bullet,
section in any client-facing artifact. Hooks that already operate
in this space:

- `em-dash-strip-gate.py` (auto-strip on Write/Edit to client paths)
- `post-write-gate.py` dispatcher routing to
  `validate-output.py` + `lint-comms-draft.py`
- `validate-pilot-routing.py` (piece cross-wire check)

Built 2026-07-22 in `validate-output.py`, markdown only, both **LOW /
advisory** (the tool's LOW band is "nudge"; a heuristic over prose that
fired at HIGH would bury the brand / placeholder / unsourced-claim rules
in the same advisory):

- `symmetry-collapse`: >=3 sibling bullets or >=3 consecutive
  paragraphs in one section whose lengths cluster (stddev/mean <= 12%)
  AND whose openings share one template. Both signals are required;
  either alone matches ordinary prose.
- `per-category-narration`: a table column whose every body cell, or a
  `**Name** sentence` run whose every sentence, follows one grammar
  template.

The template test approximates opening grammar with no NLP dependency:
function words survive literally, content words collapse to `X`, a bold
lead to `**`. An all-placeholder skeleton (`X X X X`) is the shape of any
English sentence and never counts on its own, which is what keeps the
"What is NOT slop" cases above silent. Exempt by construction, because
their symmetry is the point rather than the smell: numbered lists and
sequence-labelled runs (`**Week 3:**`), question checklists,
comma-separated inventories, and columns of noun phrases. Suppress a
judged-good run with `<!-- output-allow:symmetry-collapse -->` or
`<!-- output-allow:per-category-narration -->` plus a reason.

Calibrated against 958 repo markdown files (friction register, proposals,
rules, client deliverables): 3 files flagged, 3 hits. Tests:
`tools/tests/test_validate_output_slop.py`, where the negative cases are
the contract.

Related rules and memories: [[rule_deliverables]] (PDF voice pass,
banned constructions), [[feedback_no_per_category_narration]] (the
2026-06-01 triggering incident), [[feedback_video_script_human_language]]
(spoken-aloud variant of the same discipline).
