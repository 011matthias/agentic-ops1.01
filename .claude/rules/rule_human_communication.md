# Human Communication Standard

**Hard constraint.** All outbound human-to-human communication from
the UnpauseAI account — Upwork DMs, Upwork cover letters, client and
prospect emails, scheduling messages, video-script `SAY:` lines,
Loom narration, status updates, invoice notes, handoff messages, and
any other message a human will read on the other side — abides by ONE
language and posture standard. This rule is the source of truth for
that standard.

`rule_platform_standards.md` covers the marketing website
(unpauseai.com); this rule covers what we say TO the prospect or
client outside the website. They share typography rules; they
diverge on tone (the platform is editorial; outbound messages are
relational).

Scope of "human-to-human":
- `workspace/clients/{client}/context/comms-log.md` — drafts, sent
  messages, and our half of every thread
- `workspace/clients/{client}/context/drafts/**` — staged drafts
- `platform/src/content/proposals/*.txt` — Upwork cover letters
  (e.g. `menovia-upwork-cover-letter.txt`)
- `workspace/projects/platform/proposals/*/cover-letter.md`
- `workspace/projects/platform/proposals/*/video-script.md`
- `workspace/projects/platform/upwork-agency/intro-video-script.md`
- Transactional emails from the platform (invite, role promotion,
  signup notify) — these are short and templated but the body text
  is still human-to-human prose

Out of scope:
- Internal session logs, friction register entries, rule files
- The platform website itself (governed by [[rule_platform_standards]])
- The proposal markdown bodies rendered AS website pages
  (governed by [[rule_platform_standards]] §3 canonical shape)
- Code comments, commit messages, PR descriptions

## 1. Two registers, never blurred

Outbound messages run in exactly two registers. Picking the wrong
one is the most expensive failure mode in this category.

- **Register A — soft on money, deferential on access, consultative
  on recommendations.** Used when:
  - Stating an initial price into a vacuum (no prior number)
  - Requesting access, credentials, account-share, calendar invite
  - Offering a recommendation when the client has not asked
  - Sending an apology proportional to a single, minor mistake
- **Register B — polite-firm.** Used when:
  - Holding a price or scope under client pushback
  - Restating a commitment the client has just challenged
  - Responding to a one-line probe ("are you sure?", "seems high")
  - Reframing a structural ask (a cap, a freeze, a process change)
    into a softer one (cadence, rhythm, timing)

Both registers use polite tone. The difference is posture: A yields,
B holds. Yielding in B is capitulation in slow motion; holding in
A is aggressive selling. See [[feedback_client_comms_tone]] for
Register A; [[feedback_negotiation_posture]] for Register B; and
the litmus test below.

**Litmus test for which register applies:**

| Situation | Register |
|---|---|
| Asking for a number for the first time | A (soft) |
| Pushing back on a number we stated | B (polite-firm) |
| Probe of conviction ("are you sure?") | B |
| Asking for access / files / accounts | A |
| Recommending an approach unprompted | A |
| Responding to "your hours seem high" | B |
| Apologizing for a single specific lapse | A, contained |
| Defending the engagement model | B |

## 2. Anti-patterns (banned constructions)

Inherits the platform language rule's bans, with three additions
specific to outbound human comms:

- **No imperatives aimed at the client.** Banned starters when the
  subject is the client: "Send me…", "Give me…", "Point me to…",
  "Tell me…", "Confirm…". Rewrite as a soft optional request:
  "Whenever it's convenient, if you could…", "No rush at all on
  this; when you have a moment…".
- **No telling the client how/when to pay or commit.** Banned:
  "You shouldn't commit to ongoing money before X.", "Wait until
  you've seen it before paying.", any prescription on their
  cashflow or commitment process. Reframe as deferral to their
  comfort: "Whenever you're comfortable we can settle on something
  that feels fair to you. No pressure either way."
- **No pre-emptive concession / bidding against ourselves.** Banned
  inside a pushback context: "Happy to lower the figure", "If
  that's too much, the natural trim is…", "You're right to flag…"
  (this last validates the broader framing as well as the specific
  point). When holding a line, restate it; do not pre-discount it.

All enumerated voice bans in [[rule_anti_slop]] apply (corporate
thesaurus, meta-phrases, "not just X but Y", sentence-opening adverbs,
performed-humanness), and so does its golden-middle register standard
(direct, precise, and warm at once; never slop, never cold or
vaguely-hedged), plus the platform typography rule in
[[rule_platform_standards]] §2: zero em-dashes (` — `, `&mdash;`,
` -- `).

## 3. Anchor on the client's actual words

When acting on a client directive or producing a deliverable in
the client's voice (an email they'll send, copy for their
platform, a video script narrated as them):

- Pull up the client's exact wording from the comms log or source
  artifact BEFORE drafting.
- Lift phrases verbatim when the deliverable IS the client's
  voice. Paraphrasing dilutes the voice; verbatim preserves it.
  See [[feedback_anchor_on_clients_words]].
- Don't add scope beyond what was said. If they named three
  cities, the geography is those three cities; don't invent "and
  the surrounding area".
- Don't re-ask items the client has settled. If they stated a
  count, a structure, a preference, build to it; ask only about
  items they have not addressed.
- If something genuinely needs interpretation, flag it as our
  interpretation explicitly, never assert it as theirs.

## 4. Closing discipline

Every outbound message ends in one of three ways. No fourth option.

- **A soft offer to talk** (Register A or any thread where the
  next step is a conversation): "Happy to jump on a quick call
  if that's easier; whenever suits you." Used sparingly; one
  per thread, not per message.
- **A concrete next-step proposal** (any register, when there
  IS a next step in our court): "I'll draft X by Thursday and
  send it your way." Promise something specific and deliverable;
  don't dangle conditionals.
- **A clean sign-off** when neither of the above applies. First
  name; no honorifics; no "Best regards, looking forward to your
  reply at your earliest convenience" performative closers.

Banned closings:
- "Thanks for being direct, that's a better way to run this." —
  grateful-for-criticism, subordinate energy.
- "Understood on the cap, that's a fair guardrail." — accepting
  a structural change as if it were a process tweak.
- "Let me know if you want me to…" — deferral dressed as
  helpfulness (the platform-internal [[feedback_no_closing_offers]]
  applies internally; the equivalent for outbound is "I'll do X
  next" instead of "want me to do X?").

## 5. Length and density

- **Default to short.** A four-sentence email beats a fourteen-
  sentence one. Density of meaning per line is the metric, not
  word count.
- **Three paragraphs is a soft ceiling** for any non-proposal
  message. If the message wants to be longer, surface "this is
  longer because the situation is complex" rather than padding
  with filler ("Hope you're well. As you know, …").
- **Bulleted lists only when there are 3+ items and the order
  matters or recall matters.** Two items belong in prose.
  Numbered lists imply sequence; use only when there IS a
  sequence.
- **Subject lines** are headlines, not labels. "Patient-journey
  build: Phase 1 ready for your review" beats "Update".

## 6. Voice-pass checklist (run before sending any outbound)

Before any message goes out, scan once for the following. The
scan is fast (the patterns are pattern-matchable) and catches
the most common Layer-3 drift.

1. **Em-dashes**: zero. Replace with `; ` or `, ` or `: ` per
   context.
2. **Imperatives at the client**: zero. Rewrite as soft
   optional request.
3. **Money in Register-A scope but written in Register-B
   posture**, or vice versa: rewrite to the correct register
   per §1.
4. **Banned vocabulary**: any hit on the corporate-thesaurus
   list, the meta-phrase list, or the performed-humanness tics.
5. **Pre-emptive concession**: any "happy to lower / cap / trim"
   that the client did not specifically request. Strip.
6. **Re-asking settled items**: any question to the client about
   something they already defined. Strip.
7. **Voice paraphrasing in client-voice deliverables**: any
   paraphrase where the client's verbatim phrase is available.
   Replace with verbatim.
8. **Closing**: ends in one of the three sanctioned ways from §4.
9. **Date / fact accuracy** (inherits [[rule_platform_standards]]
   §7 + [[rule_behaviors]] B4): every number, name, date, and
   commitment traces to a queryable source. Unverified → TBD or
   rephrased as a capability.

## 7. Spoken vs written: video scripts

Video-script `SAY:` lines are heard, not read. Two extra rules
beyond §1–§6:

- **Use specific terminology and abbreviations confidently** —
  don't strip them to plain language. Stripping makes the
  speaker sound like a beginner translating for a child.
- **Any non-universal abbreviation gets a 3–8 word inline
  gloss the first time it appears**, embedded naturally:
  "the SKU, the product code each supplier uses to identify
  an item". Universal exemptions: AI, API, UI, URL, HTML,
  CSS, JS, JSON, XML, SQL, OS, CSV, HTTP, HTTPS, PDF, TCP,
  IP, DNS, CRM, CEO, CTO, CFO, COO, CMO, VP, B2B, B2C, KPI,
  ROI, IT, HR, PR, QA, UX, EU, US, UK, USA, EMEA, APAC, FAQ,
  AM, PM, TBD, OK.

`>>` stage directions and `LOOM NOTES VERSION` blocks are
silent — exempt from these rules. See
[[feedback_video_script_human_language]].

## 8. The "would a competent peer say this?" test

The simplest single-pass test for an outbound message. Before
sending, read the message as if it were sent TO us by a peer
who works in the same domain. Ask:

- Would I believe this person is talented if I read this?
- Would I feel respected by them, or talked down to?
- Would I want to reply, or would the message close itself?

If the answer to any of these is "no", rewrite. This test
catches what the structural checks (§6) miss: tonality drift,
flatness, performative warmth, and AI-tells that don't
pattern-match a single banned phrase.

## 9. Enforcement

Three mechanisms, all working together:

1. **Hook `post-write-gate.py`** routes writes under
   `workspace/clients/**/context/drafts/**`,
   `**/comms-log.md`, and proposal text/markdown into
   `lint-comms-draft.py` and `validate-output.py`. These
   already catch many of the §2 bans. This rule expands the
   ban list those tools enforce, where they don't already.
2. **`tools/validate-proposal.py`** runs the spoken-line
   abbreviation check from §7. Already wired; don't fork.
3. **`tools/strip-em-dash.py`** is the corrective tool for §6.1.
   Run on a draft before sending.

The post-write gate is the structural backstop. The voice-pass
checklist in §6 is the procedural backstop. The peer test in §8
is the perceptual backstop. All three fire before the message
leaves; ALL THREE failing on the same draft is the only path
to user-visible drift.

**Self-detection.** A violation of any section above caught by
the client (em-dash slip, register-mismatch, voice paraphrase
when verbatim was available) is a friction event (`outbound-
language-drift`) — log at `/comd_checkpoint`. The recurrence-
kill is to strengthen the checklist run, not to memorize harder.

## Why

The two registers (soft / polite-firm), the "no closing offers"
discipline, and the "anchor on client's words" rule each surfaced
from a separate Meji or Wimmer incident in May 2026. Each is a
load-bearing rule by itself; together they form the same
standard, but they had been distributed across four feedback
memories (Layer 3 — depends on agent recall) instead of one
operationalized rule (Layer 1 — fires at decision time). This
rule consolidates them at Layer 1 so that the next outbound
draft doesn't need to remember four separate memory files in
order to land the tone correctly.

Related: [[rule_platform_standards]] (sibling rule, marketing
surface); [[feedback_client_comms_tone]], [[feedback_negotiation_posture]],
[[feedback_anchor_on_clients_words]], [[feedback_video_script_human_language]],
[[feedback_no_closing_offers]] (the memory files this rule
synthesizes — left in place as historical context, but the
operational source of truth is now this rule).
