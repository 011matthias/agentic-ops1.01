# Video Guide; n8n Multi-Client Ops (p027)

A guide for a 3 to 4 minute Loom, spoken in your own words. Each
section is what that part needs to land, not a line to read. Keep it
calm and plain. You are an operator talking to another operator, not
selling.

## Open (about 20 seconds)

- Say who you are in one line: Matthias, you run production automation
  for a handful of clients and you want to operate as his execution
  arm.
- The promise: he asked for a documented operator who keeps many
  clients straight, and you are going to show him the actual system
  you use to do that, not talk about it.
- Name that you answered all six screening questions in full, and this
  video walks the two that matter most.

## The reframe (about 30 seconds)

- His real worry is not which tool. It is "will work fall through the
  cracks across all these clients." Say that back to him.
- Your answer is structural, not a promise to try hard: hard isolation
  per client plus written state, so picking a client back up is
  reading a file, not remembering.

## What I already built for you (about 60 seconds)

- Show the n8n workflow JSON you are attaching: a client-onboarding
  orchestrator for the exact case in his post (a new client kicks off
  across Asana, QuickBooks, Drive, Slack, from a JotForm intake).
- Walk the shape quickly: one intake trigger, branch per system, each
  branch documented with a sticky note, error handling on the calls
  that can fail.
- The point to land: this is a working n8n workflow built for his
  stated problem, with the documentation baked into the workflow
  itself. That is the difference between an operator and a
  template-user.

## The two stories (about 60 seconds)

- Q5, the production break: the double-send. The follow-up fired
  twenty minutes after the first email instead of two days later,
  because the delay field is the gap before the next email, not after
  the current one. You caught it auditing live sends, across three
  campaigns, before the client did, then changed your own checklist so
  it never happens again.
- Q6, the LLM one, in a sentence: a finance reconciliation workflow
  where the model never decides alone; a deterministic layer and a
  confidence gate sit around it.

## Rate, hours, and the honest part (about 30 seconds)

- Rate: forty to fifty dollars an hour depending on the week's mix.
- Hours: you are CET, his EST afternoon is your evening, and you will
  hold a daily overlap window with his business hours. Say it plainly;
  it is non-negotiable for him, so meet it head on.
- The honest line: your heaviest production hours are across n8n and
  adjacent tools; you would rather he start with one real task and
  judge the work than take your word for it.

## Close (about 20 seconds)

- One next step: he picks a small real task, you build and document
  it, he sees the operating rhythm before any ongoing commitment.
- Offer a short call if that is easier, whenever suits him.
- End on his name and the site link.

## Terms to gloss if you say them on camera

- API: the way one tool talks to another.
- JSON: the plain text file format an n8n workflow exports to.
- LLM: a language model, the AI that reads and writes text.
- Webhook: a URL that fires the workflow the moment something happens.
- Deterministic: rule-based, same input gives the same output every
  time, no guessing.
