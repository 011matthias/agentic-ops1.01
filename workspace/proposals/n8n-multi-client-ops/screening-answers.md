# Screening Answers, paste-ready (n8n Multi-Client Ops, p027)

These are written to be pasted directly into the six Upwork screening
fields. Plain text, no markdown. Each one is honest and specific; the
same six are presented on the site's Screening page as proof of the
documentation habit the role is built around.

---

## Q1, n8n depth: the most complex workflow

The most complex one is a multi-campaign cold-outreach engine for a
media and events client, running three separate sending identities at
the same time without them ever crossing.

Inputs: lead lists from a few sources (form intake, an enriched
audience list, and a CRM export), each tagged by campaign and audience.

Outputs: personalised, sequenced sends through the sending platform
(Instantly, called over its API from HTTP Request nodes), a
reply-detection path that stops a lead's sequence the instant they
respond, and a running count written back to a sheet so the client can
see volume end to end.

Logic: dedupe across the three sources, lead scoring to decide who
enters which campaign, a Switch that routes by domain and audience so
the three identities never mix, schedule windows per campaign, and
per-step sequence timing.

Hardest problem: the workload is polling-heavy but low in actual
volume, so a naive "check every few minutes" design burns resources
doing nothing most of the time. I restructured it to be event-driven
where the source allowed it and to poll only where it forced me to,
and I had to make reply-detection reliable enough that it never let a
sequence keep emailing someone who had already replied. The subtle
bugs all live in the sequence timing, which is exactly where one bit
me later (see Q5).

---

## Q2, documentation habits: what I produce and where it lives

Every client gets the same structure, in version control, so nothing
lives in my head or in a chat thread.

Per workflow I keep three things: a one-page spec (the trigger, the
systems it touches, inputs and outputs, the edge cases, and the test
that proves it works), the workflow itself exported as JSON in git so
changes diff cleanly, and a canonical state file per client that lists
every live workflow, its IDs, which credentials it uses (names, never
secrets), and its current status.

Every change gets a dated note: what changed, why, and what it
affects. When I edit a live workflow I update that state file in the
same sitting, so the documentation never drifts from what is actually
running.

Where it lives: a git repository, one folder per client, fully
isolated. The test I hold myself to is handoff-readiness. If someone
else could not pick the system up from the docs and run it without me,
it is not documented yet.

---

## Q3, multiple clients: keeping context straight

Yes, I run several at once right now. The thing that keeps them
straight is hard isolation: no shared workflows, no shared
credentials, no shared state between clients. Each one is a separate
namespace with its own context file.

When I switch to a client I reload that client's state file first, so
I am working from written truth, not memory. Each client's live
config, IDs, routing, and open items sit in one canonical place,
updated as I go.

What stops things falling through the cracks is that open items and
next steps are written down per client at the end of every working
session, not carried in my head. Picking a client back up after a few
days is then reading a file, not reconstructing context. The cost of
one unowned detail multiplied across five clients is exactly the
failure mode you are describing, and isolation plus written state is
how I avoid it.

---

## Q4, unfamiliar tool or API: how I approach it

Most recent example: the Instantly sending platform's API, which I had
not used before.

Approach: I read the API docs end to end first, then build the
smallest possible test against a throwaway setup before touching
anything live, to confirm I understood the real behaviour rather than
the documented behaviour. I map the endpoints I need, confirm auth and
rate limits, and only then wire it into the workflow.

What went wrong: the docs described the sequence-timing field one way,
but the live behaviour was different. The delay value applied to the
gap before the next email, not after the current one. I only caught it
because I tested actual sends instead of trusting the field name. That
is the habit it reinforced: verify behaviour, not configuration, on
any unfamiliar system. It is the same habit I would bring to picking
up your stack (Clay, Lemlist, Pandloc, JotForm, QuickBooks, whatever a
given client needs).

---

## Q5, broke in production: what happened and what I did

A cold-outreach sequence started sending the first follow-up about
twenty minutes after the initial email, instead of two days later.
Recipients got two emails almost back to back.

How I found out: I was auditing the live campaigns and noticed the
send timestamps were wrong before the client did. It was happening
across three campaigns at once.

Cause: the platform's per-step delay is the gap before the next email,
not after the current one. A delay of zero on the first step meant the
second email fired almost immediately. The step copy and the step
count were both correct, which is exactly why a surface-level check
missed it; the bug was in the timing field, which I had not audited.

What I did: moved the gap onto the correct step, re-checked all three
campaigns, then changed my own audit checklist so it always verifies
step delays, not just step count and copy. The fix was small. The
lesson I kept is the larger one: audit the thing that actually changed
the behaviour, not just the parts that are easy to eyeball.

---

## Q6, AI and LLM integration: what it did and how I handled bad output

Yes. One workflow runs expense reconciliation for a finance client. It
reads expense documents, extracts the line items, and matches them
against records, using an LLM (currently gpt-4o-mini) for the judgment
calls a rules engine cannot make cleanly, like deciding whether two
differently worded entries are the same expense.

The important part is how I handle the model being unreliable. It
never gets the final say on its own. Three guards:

First, a deterministic matching engine handles everything that can be
matched by rules, so the model is only asked about genuine ambiguity,
not the easy ninety percent.

Second, every model call returns a confidence signal, and anything
below threshold is routed to a human-review queue instead of being
applied automatically.

Third, the prompt forces a structured output I can validate, so a
malformed or hedging answer is caught and retried rather than silently
trusted.

So unexpected output is designed for, not hoped against. The model
proposes; the deterministic layer and the confidence gate dispose.
