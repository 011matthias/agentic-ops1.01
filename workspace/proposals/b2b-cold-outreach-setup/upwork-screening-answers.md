# Upwork Screening Answers: B2B Cold Outreach Setup (p028)

Submitted with the application 2026-06-11. Plain text, pasted verbatim.

## Q1: General assessment of the tools / better alternative?

The stack you picked is the right one, I'd keep it. It's basically what I run today. Two honest notes though.

PhantomBuster is the riskiest piece. It does the job for exporting Sales Nav results, but for the actual DM sending it's a cloud automation and LinkedIn is good at spotting those patterns. I'd still use it, just configured conservatively: low daily caps, randomized timing, a warmed account. If an account restriction would really hurt you, tools like HeyReach or Expandi are built specifically for LinkedIn outreach with a dedicated IP per account, that's the one swap worth considering.

Apollo and Sales Navigator overlap on sourcing. I'd keep both anyway: Sales Nav for the LinkedIn-native targeting (you need it for the DM goal), Apollo for emails and company data on the same people.

One gap in your list: email verification. Apollo's emails aren't clean enough on their own, so I'd add NeverBounce or similar before anything gets saved. Instantly for the email side is the right pick, no change there.

## Q2: Workflow and each tool's contribution

Week 1: we lock the ICP together and I build it as Sales Navigator saved searches, so the list is reproducible instead of a one-off export. PhantomBuster pulls those results out. Apollo enriches the same people with verified work emails and company data, then everything goes through verification (deliverable / catch-all / invalid) before it's saved. That's the clean list part.

In parallel I set up Instantly on day one: separate sending domains, SPF/DKIM/DMARC records, mailbox warm-up. Warm-up takes 2-3 weeks, so starting immediately means the email channel is ready right when the list is.

Week 2 onward: PhantomBuster runs the LinkedIn outreach on a schedule that stays inside LinkedIn's limits, roughly 100 connection requests and 50-80 automated DMs per week per account. If your 500 targets are already 1st degree connections, the 2 week target works at about 35 DMs a day. If they're cold, connects go out first and DMs follow each acceptance, which lands the 500 over 3-4 weeks. I monitor account health daily during this phase.

So each tool has one job: Sales Nav finds them, PhantomBuster reaches them, Apollo gets their email, verification keeps the list clean, Instantly is the future email channel.

## Q3: Recent experience with similar projects

Most relevant: I run cold outbound end to end for a UK client right now. Built it from scratch this spring: registered the sending domains, set up mailboxes and DNS records, ran warm-up, built the lead lists in Apollo with role and company size filters plus a roughly 1,200 domain exclusion list from their CRM, verified everything through NeverBounce. Three campaigns are live in Instantly today across multiple sending domains.

The detail I'm probably most proud of: I caught a sequence timing bug in their live campaigns (follow-ups firing 20 minutes apart instead of days apart) by reading the Instantly API spec directly. That's the level I work at, not just clicking through a UI.

Before that, lead automation builds for other clients: instant form response systems, AI-personalized follow-up sequences, and reply detection that actually stops a sequence when someone answers.
