# Message Types

Each message type defines structure, tone, context sources, and pitfalls.

The structures below are guidance, not rigid templates. Adapt to the situation. The goal is to sound like a real person wrote it, not to fill in blanks.

---

## status-update

**When:** Regular progress report. The client hasn't asked for anything specific, you're just keeping them in the loop.

**Structure:**
1. What's done since last update (1-2 sentences, specific)
2. What's next (1 sentence)
3. Any blockers or things you need from them (if applicable)

**Context to load:** Latest checkpoint, spec frontmatter (stages), infrastructure.yaml (ship flags)

**Tone:** Confident, brief. Don't oversell or pad. If you did 2 things, say 2 things.

**Pitfalls:**
- Don't list every micro-task. Summarize at the feature level.
- Don't say "everything is going great" without specifics.
- Don't mention internal tooling (UTIL scenarios, test fixtures, agents).

---

## info-request

**When:** You need something from the client to continue.

**Structure:**
1. Brief context for why you need it (1 sentence)
2. The specific ask (be precise about what format, what info, what access)
3. How to provide it (screenshot, link, credentials in a specific way)

**Context to load:** Latest checkpoint (blockers), process-notes (who owns what)

**Tone:** Direct but not demanding. Make it easy for them to respond.

**Pitfalls:**
- Don't bury the ask in a wall of text. Lead with it or make it clearly visible.
- Don't ask for multiple unrelated things in one message (unless platform is Upwork chat where threading is limited).
- Be specific: "Can you share the Google Sheets URL?" not "Could you provide access to the relevant spreadsheet?"

---

## blocker-notification

**When:** You're stuck and need client action before you can continue.

**Structure:**
1. What you're blocked on (specific)
2. What impact it has (what can't proceed)
3. What you need from them (specific action)
4. What you're doing in the meantime (if anything)

**Context to load:** Latest checkpoint (blockers), spec frontmatter (needs_fixes), infrastructure.yaml

**Tone:** Factual, not alarming. Don't make them feel bad. Frame it as "here's what we need to keep moving."

**Pitfalls:**
- Don't say "urgent" unless it genuinely is.
- Don't repeat blockers they already know about without adding new info.
- Always mention what you CAN do in the meantime if possible.

---

## deliverable-handover

**When:** Shipping work to the client. Could be a finished feature, a handover package, documentation.

**Structure:**
1. What's included (brief summary)
2. How to use/access it (link, instructions, or reference to setup guide)
3. What they should expect (behavior, timing, any known limitations)
4. Next steps (what happens after they review)

**Context to load:** docs/client/overview.md, handover/README.md, infrastructure.yaml (ship: true items)

**Tone:** Clear and helpful. This is a moment of value delivery. Be specific about what they're getting.

**Pitfalls:**
- Don't use jargon they won't understand (scenarios, modules, data stores). Use client-facing language.
- Don't skip the "how to use it" part. They need to know what to do with what you gave them.
- Don't include dev artifacts (test fixtures, debug tools) in the handover.

---

## milestone

**When:** Something significant was completed. A feature went live, a major phase finished.

**Structure:**
1. What was achieved (in their language, not technical)
2. What it means for them (the benefit, the problem it solves)
3. Brief next steps

**Context to load:** Spec frontmatter (stage transitions), checkpoint

**Tone:** Warm but not over-the-top. One line of genuine positivity is fine. Don't gush.

**Pitfalls:**
- Don't list technical details they don't care about.
- Don't oversell. Let the work speak for itself.

---

## follow-up

**When:** You sent something (an ask, an update, a deliverable) and got no response.

**Structure:**
1. Brief reference to what you're following up on (not a full restatement)
2. Restate the specific ask or decision needed
3. Close warmly, no pressure

**Context to load:** Previous checkpoint or message context

**Tone:** Light, no guilt. "Just bumping this" energy.

**Pitfalls:**
- Don't passive-aggressively reference the time elapsed.
- Don't re-explain everything. They saw the first message, they just didn't respond.
- Keep it very short. 2-3 sentences max.

---

## technical-to-dev

**When:** Communicating with the client's developer or technical contact.

**Structure:**
1. Technical context (specific IDs, endpoints, formats)
2. What you need or what you did (precise, with code/config references if helpful)
3. Expected behavior / what to look for

**Context to load:** infrastructure-ids.md, spec details, process-notes (developer contact)

**Tone:** Direct, peer-to-peer. Skip the pleasantries. Be precise.

**Pitfalls:**
- Don't dumb it down for a developer. Be specific.
- Don't assume they know your system's internals. Explain what your side does in brief.
- Include actual IDs, URLs, and payload examples where relevant.

---

## scope-discussion

**When:** Discussing new features, changes, or additional work.

**Structure:**
1. Acknowledge the request or idea
2. What's involved (brief technical summary in client language)
3. Rough effort indication (not exact hours, but "small change" vs "significant addition")
4. Questions to clarify before committing

**Context to load:** Process-notes (contract type, rate), specs (existing scope)

**Tone:** Consultative. You're the expert giving honest input.

**Pitfalls:**
- Don't commit to timelines or scope without clarifying unknowns.
- Don't over-promise. Under-promise and over-deliver.
- If it's hourly, you don't need to quote. Just describe the work.

---

## invoice-context

**When:** Sending or accompanying an invoice or hours log.

**Structure:**
1. Period covered
2. Summary of what was accomplished (feature-level, not task-level)
3. Brief note on what's next

**Context to load:** Checkpoint history for the billing period, spec frontmatter (stage changes)

**Tone:** Professional, factual. Let the work speak.

**Pitfalls:**
- Don't justify hours. Just describe what was delivered.
- Don't be apologetic about the total.

---

## proposal

**When:** Initial pitch, project proposal, or response to a job posting.

**Structure:**
1. Show you understand their problem (reference specifics from their brief)
2. Your proposed approach (tools, architecture, high level)
3. Why this approach works for them specifically
4. Rough scope/timeline indication
5. Clear next step

**Context to load:** Process-notes (original brief if available), client context

**Tone:** Confident, specific, not salesy. Show expertise through specificity, not adjectives.

**Pitfalls:**
- Don't be generic. Reference their exact situation.
- Don't list every tool you know. Focus on what's relevant to them.
- Don't use buzzwords. Describe what you'll actually build.
- Don't under-explain or over-explain. Match their technical level.

---

## meeting-recap

**When:** After a call or meeting with the client.

**Structure:**
1. Numbered sections for each topic discussed (`1) Topic:`, `2) Topic:`, etc.)
2. Inline context and action items within each topic section
3. Consolidated action items at the end, grouped by person (`For {Name}:`)
4. Supporting links (recording, docs, references) placed inline where contextually relevant, not as separate sections

**Context to load:** Latest checkpoint, process-notes, comms-log (last 3 entries)

**Tone:** Clear, organized, conversational. Reference document, not a corporate memo.

**Pitfalls:**
- Don't include everything discussed. Focus on decisions and actions.
- Don't attribute opinions to people ("you said...") in a way that could feel like you're putting words in their mouth. Focus on what was agreed.
- On Upwork: no markdown formatting (bold, bullets). Use numbered sections and plain text with line breaks.
- Don't open with pleasantries ("Great meeting you today"). Start with context ("So as promised, here's the post-meeting summary").
- Credit client contributions when they spotted issues ("Good spot, Jess!").
