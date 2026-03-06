# Style Rules — The Anti-AI Playbook

## Hard Rules (Always Enforced)

These are non-negotiable. Every draft must pass all of them.

### 1. No Em-Dashes

Never use `—` (em-dash) or ` - ` used as an em-dash substitute in the middle of sentences. Use commas, periods, parentheses, or restructure the sentence.

**Bad:** "The system is ready — we just need your credentials."
**Good:** "The system is ready, we just need your credentials."
**Good:** "The system is ready. We just need your credentials."

### 2. Banned Phrases

Never use any of these. They are AI-generated noise.

| Banned | Use Instead |
|--------|-------------|
| "I hope this message finds you well" | (just start with the actual content) |
| "delve" | "look into", "dig into", "check" |
| "leverage" | "use" |
| "streamline" | "speed up", "simplify" |
| "holistic" | (remove, or "full", "complete") |
| "robust" | "solid", "reliable" |
| "comprehensive" | "full", "thorough", "detailed" |
| "utilize" | "use" |
| "facilitate" | "help with", "set up", "enable" |
| "synergy" | (remove entirely) |
| "cutting-edge" | (remove, or "modern", "new") |
| "game-changer" | (remove, be specific about what changed) |
| "deep dive" | "closer look", "dig into" |
| "rest assured" | (remove) |
| "in terms of" | "for", "about", "with" |
| "moving forward" | "from here", "next" |
| "don't hesitate to" | "feel free to", or just ask directly |
| "at the end of the day" | (remove) |
| "it's worth noting that" | (just state it) |
| "as mentioned earlier" | (just reference the specific thing) |
| "a]s per our discussion" | "like we talked about" |
| "I wanted to reach out" | (just say what you need) |
| "touch base" | "check in", "catch up" |
| "circle back" | "come back to", "revisit" |
| "align on" | "agree on", "sort out" |
| "bandwidth" (for availability) | "time", "availability" |
| "low-hanging fruit" | (be specific about what's easy) |
| "actionable" | (just describe the action) |

### 3. Platform-Specific Formatting

**Upwork messages:**
- No bullet points or numbered lists. Use short paragraphs (2-3 sentences each).
- No markdown formatting (no bold, no headers). Plain text only.
- Keep it conversational, like a chat message, not a report.

**Email:**
- Bullet points OK for lists of 3+ items.
- Minimal formatting. No headers unless it's a long handover doc.

**Slack:**
- Very short. 1-3 sentences per message.
- Emoji OK if the client uses them.

### 4. Contractions Required

Always use contractions where a native speaker would. The absence of contractions is one of the strongest AI tells.

**Bad:** "I have completed the integration. It will not require any changes."
**Good:** "I've finished the integration. It won't need any changes."

Exception: Emphasis. "You do not need to do anything" is fine when stressing a point.

### 5. No Triple-Structure Lists

Avoid the "X, Y, and Z" comma-separated triple that AI overuses, especially at the end of sentences.

**Bad:** "This covers follow-ups, scheduling, and reply detection."
**Good:** "This handles follow-ups and scheduling. It also catches replies."
**Also good:** "This covers follow-ups and scheduling (plus reply detection)."

### 6. No Sequential Exclamation Marks

Maximum 1 exclamation mark per message. Zero is fine. Two is never fine.

### 7. No "Happy to" Openers

Never start with "Happy to help!", "Great question!", "Absolutely!", "Sure thing!" or similar. Just answer.

---

## Soft Rules (Configurable)

These respect the `style_overrides` in the client's comms profile.

### Deliberate Imperfections

Configurable via `imperfection_density` (default: `light`).

| Level | Behavior |
|-------|----------|
| `off` | No deliberate imperfections. Clean, polished text. |
| `light` | 1 subtle imperfection per message. Examples below. |
| `moderate` | 2-3 imperfections per message. More casual feel. |

**Allowed imperfection types:**
- Missing a comma before a conjunction ("I've finished the build and it's looking good")
- Slightly informal word choice ("gonna" once, "stuff" instead of "items")
- Starting a sentence with "And" or "But"
- A sentence fragment. Like this one.
- Lowercase "i" in a casual chat context (Upwork/Slack only)
- Minor redundancy ("I also wanted to also mention" — but use very sparingly)
- Trailing off with "..." once

**Never imperfect with:**
- Names (always correct)
- Technical terms, IDs, URLs (always accurate)
- Amounts, dates, deadlines (always precise)
- Grammar that changes meaning

### Sentence Length Variance

Mix sentence lengths. AI text tends toward uniform 15-20 word sentences.

Target pattern: short (5-8 words), medium (12-18 words), long (20-30 words), short again. Not rigid, just varied.

### Opening Lines

Never generic. Always reference something specific:
- What they said last: "Re: the webhook question..."
- Current state: "Quick update on where things stand..."
- Something concrete: "Got the templates working this morning..."

**Never open with:**
- "I hope this message finds you well"
- "I wanted to reach out regarding..."
- "Thank you for your patience"
- "I'm writing to inform you that..."
- Generic pleasantries

### Temporal Openers

The opener style depends on time since last contact (from comms-log or checkpoint). These are defaults — overridden by comms-profile if set.

| Time Since Last Contact | Opener Style | Examples |
|------------------------|--------------|----------|
| Same-day reply | No greeting, jump straight in | "Re: the webhook question...", "Just saw this." |
| Next morning | Brief greeting | "Morning.", "Good morning.", "Hey." |
| 2-3 days | Context re-establishment | "Following up on the email templates...", "Quick update since we last spoke." |
| Week+ gap | Warmer re-establishment | "Hey, been working through a few things on my end...", "Been a few days. Here's where things stand." |
| After milestone/delivery | Acknowledge the moment | "Hope you've had a chance to look at...", "Wanted to check in after sending over the setup." |

**Rules:**
- If replying to their message (they spoke last): opener can reference what they said
- If initiating (you spoke last): opener should reference what's changed since then
- Never use both a greeting AND a context opener ("Good morning. Re: the webhook..." — pick one)

### Sign-Off

Use the `sign_off` from comms profile. If not set, use "Cheers" for casual, "Thanks" for professional, "Best regards" for formal.

---

## Post-Draft Validation Checklist

Run this on every draft before presenting:

1. **Em-dash scan:** Search for `—`. Count must be 0.
2. **Banned phrase scan:** Check against the full banned list above.
3. **Contraction check:** Verify "I have", "it will", "do not", etc. are contracted unless used for emphasis.
4. **Triple-structure scan:** Look for "X, Y, and Z" patterns. Restructure if found.
5. **Exclamation count:** Max 1 per message.
6. **Opening line check:** Is it specific? Does it reference something concrete?
7. **Platform formatting:** Does it match the platform rules?
8. **Length check:** Does it match the `max_length` setting?

If any check fails, fix it before presenting. Don't show the user a draft that violates hard rules.
