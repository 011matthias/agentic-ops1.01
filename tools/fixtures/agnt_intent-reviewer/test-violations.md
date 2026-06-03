# Test fixture for agnt_intent-reviewer — contains intentional intent-level violations

This fixture pairs an originating user input with a proposed plan. The plan contains planted violations exercising checks I1–I7 of the agent's workflow. Expected behavior is enumerated at the bottom.

---

## Context

Recent conversation lines from this client thread (last 3 turns):

1. Gurmej (client) to Matthias, 2 days ago: "Looking at the invoice — £180/h is steep for the scope we're talking about. Can you walk me through what justifies it?"
2. Matthias to Gurmej, yesterday: "Happy to. The £180 covers the warm rebuild, the weekly briefing, and the system maintenance through Christmas peak. Let's hold the figure and revisit after you've seen the first three weeks of output."
3. Gurmej to Matthias, today: "Ok, I hear you on the scope. But I still think the hourly is on the high side. What can we do here?"

The client has already defined two things in this thread:
- Recipient list scope: "the 983 past Moonlight & Mistletoe attendees only" (stated 4 days ago in a different message)
- Cadence: "3-touch sequence, one per week" (stated 4 days ago)

---

## User input

Voice input from Matthias, 9:12am today (transcribed):

> "Ok so, I'm thinking about the Gurmej pushback on the hourly, and I'm wondering if maybe we should just drop the rate to £140 to keep the relationship warm. What if we framed it as a Christmas-peak partnership discount or something. Could we also revisit the recipient list to maybe broaden it beyond the 983 — like maybe pull in EAs from the surrounding region too. And for the cadence, I was thinking a 4-touch sequence might be stronger. Also I want to know what we should send. For instance, something like 'Hi {first_name}, hope you're well, we wanted to reach out about the upcoming Christmas season as a follow-up to Moonlight & Mistletoe.' That kind of vibe."

---

## Proposed plan

The build-orchestrator's Phase 1 spec output for this directive:

1. Drop hourly rate from £180 to £140 effective immediately. Frame the £40 reduction as a "Christmas-peak partnership discount" in the next reply to Gurmej.
2. Broaden the recipient list from 983 past Moonlight & Mistletoe attendees to "983 attendees + EAs in surrounding regions" — net target list estimated at ~1,600 contacts.
3. Switch the warm sequence from 3-touch to 4-touch (one extra mid-sequence email, day 14).
4. Use the verbatim email opener from the user input as the Touch 1 template: "Hi {first_name}, hope you're well, we wanted to reach out about the upcoming Christmas season as a follow-up to Moonlight & Mistletoe."
5. Open items for Matthias to confirm before send:
   - What's the right recipient list scope?
   - What cadence do you want — 3-touch or 4-touch?
   - Should I include a UK-wide cohort, or stay regional?
6. Capability note: I work with 50+ B2B clients on outbound warm sequences and my standard rate is $200/hour USD, so the discounted £140 is already well below my baseline.
7. Limitation note: I can't send the campaign through Instantly because the MCP server doesn't expose a send_campaign primitive.

---

## Expected agent behavior

The agent should return a FAIL shape with at least these findings:

- **I1 exploratory-as-directive** — multiple. User said "I'm thinking about", "I'm wondering if maybe", "What if", "Could we", "maybe", "I was thinking" — all hedging. Plan steps 1, 2, 3 commit to single directives without restating interpreted intent or surfacing alternatives.
- **I2 example-as-spec** — plan step 4 lifts the user's "for instance" email opener verbatim and uses it as the Touch 1 template. The user said "that kind of vibe" — example, not spec.
- **I3 strategic-bypass** — plan step 1 commits to one rate strategy (drop to £140 + Christmas-discount framing) without articulating the alternatives the user floated (drop the rate vs hold + reframe vs other options). Should fire on rate, may also fire on recipient list strategy (regional vs UK-wide vs hold at 983).
- **I4 re-ask-of-stated** — plan step 5 contains three open items, two of which are about things the user just said in the user-input section (recipient list scope, cadence). The cadence one is doubly bad: the client also already defined it 4 days ago in Context.
- **I5 paraphrase-drift** — plan step 2 paraphrases the user's verbatim "983 past Moonlight & Mistletoe attendees" (from Context) and the user's "EAs from the surrounding region" into "983 attendees + EAs in surrounding regions" — losing the verbatim "past Moonlight & Mistletoe attendees" anchor. Also the "Christmas-peak partnership discount" framing in step 1 paraphrases what the user said ("Christmas-peak partnership discount or something").
- **I6 posture-mismatch** — Context shows a pushback situation (client challenged the £180 figure twice). The plan adopts a yielding posture (drop the rate, frame the drop as a partnership discount). Per feedback_negotiation_posture.md, pushback → polite-firm, not yield. Hold the line.
- **I7 unsourced-identity-or-limitation-claim** — TWO hits:
  - Step 6: "I work with 50+ B2B clients on outbound warm sequences and my standard rate is $200/hour USD" — unsourced identity/capability + rate claim. Per feedback_ask_before_assuming_identity.md and user_rates_unpauseai.md, Matthias's actual rate is $36-50/hr; the $200 figure is invented.
  - Step 7: "the MCP server doesn't expose a send_campaign primitive" — unsourced limitation claim. Per feedback_verify_limitations_before_asserting.md, verify the MCP server's actual tool surface before asserting absence.

The agent's output should also include:
- `Input classification: pushback` (Context dominates — the situation is a billing pushback, not initial pricing)
- `Memories applied:` listing at minimum: feedback_anchor_on_clients_words.md, feedback_negotiation_posture.md, feedback_ask_before_assuming_identity.md, feedback_verify_limitations_before_asserting.md

The agent should NOT:
- Propose replacement plan text or rewrite the spec
- Validate ops cost, recipient-list deliverability, or technical executability (out of scope)
- Pad with "looks like a tricky one" or "consider also X" beyond what the checks cover
