# Video Script -- Email Compliance Monitor

## Recording Setup
- Screen: proposal site open at index.html
- Camera: bubble overlay (bottom-right)
- Duration: 3-4 minutes
- Opening: proposal site overview page visible

---

## BEAT 1 -- Reframe the Problem

SAY: Hi there, Nico here. I saw your posting for the OpenWebUI deployment and email compliance monitor. The Open WebUI part is straightforward -- it's a Docker deployment with some auth configuration. The real project is the email monitoring system.

>> Show: index.html hero section

SAY: And the part that makes this project different from a typical API integration is the GDPR angle. You're a UK company with over 100 staff, routing customer emails through AI. That's not a hobby project -- that's a data processing operation with specific legal requirements.

>> Scroll to "The Real Challenge" section

SAY: I noticed you've done a version of this before -- the Azure/OpenAI email monitoring project. This time you want it production-grade. So I designed the system around that.

---

## AUTHORITY (max 20 seconds)

>> Show: Upwork profile or portfolio briefly

SAY: Quick context -- I'm based in the EU, so I deal with GDPR requirements on every project I build. I've delivered compliance-grade automation systems for enterprise clients running similar email processing pipelines.

---

## BEAT 2 -- Show the System

>> Nav: Solution

SAY: There are two systems here. The email compliance monitor is the priority -- that's Phase 1.

>> Scroll to email monitor pipeline flow diagram

SAY: Emails come in from M365 or Gmail in near real-time. They go through a pre-processing step where we strip attachments, minimize headers, and extract just the text we need. That's data minimization in practice -- we're not sending your entire email archive to an API.

>> Scroll to AI processing section

SAY: Claude then analyzes each email and returns structured output -- sentiment, complaint detection, severity score, and key tags like urgent, legal risk, or escalation. The results go into encrypted storage, and anything severity 4 or 5 triggers an immediate Slack alert.

>> Nav: Workflow

SAY: Here's the data flow. You can see what goes where, and the GDPR column shows the legal basis for each data movement.

>> Scroll to GDPR data lifecycle section

SAY: The retention lifecycle is automated. Active data stays searchable for 30 days, gets archived at 90, and purges at 120. All configurable. Every transition is logged for audit purposes.

---

## BEAT 3 -- Edge Cases and GDPR

>> Nav: GDPR

SAY: This is the page I think matters most. Most proposals you'll get won't mention GDPR at all, or they'll treat it as a checkbox at the end.

>> Scroll to "Why GDPR Matters Here" section

SAY: Here's the reality: sending email content to Anthropic's US servers is an international transfer. Automated complaint flagging could trigger Article 22 rights. Storing processed results without retention management accumulates liability. These aren't theoretical -- they're the things your compliance team will ask about.

>> Scroll to "International Transfers" section

SAY: We handle the transfer issue by configuring Anthropic's API for zero data retention and preparing Standard Contractual Clauses documentation. The data transits their servers for processing but isn't stored.

>> Scroll to "Rights and Requests" section

SAY: And the system supports all the key GDPR rights -- subject access requests, right to erasure, right to object. The human review queue for high-severity alerts isn't just a safety feature, it's also an Article 22 compliance mechanism.

---

## BEAT 4 -- Extensions

>> Nav: Timeline

SAY: Phase 1 takes three weeks and delivers the complete email monitoring system with all the GDPR documentation -- DPIA, transfer assessments, retention policies. Phase 2 adds Open WebUI and production hardening in two more weeks.

>> Nav: Investment

SAY: I know the brief listed $600. I've broken down why the scope costs what it does on this page, including a market comparison. Phase 1 stands alone at $1,850 if you'd prefer to start there.

---

## BEAT 5 -- Close

>> Nav: Onboarding

SAY: If this resonates, the onboarding form collects the details I'd need to start -- your email provider, approximate volume, and who should get alerts. No preparation needed on your end.

SAY: Happy to discuss scope or phasing. Thanks for reading.

---

## LOOM NOTES VERSION

- Open proposal site (index.html)
- Reframe: "Real project is email monitoring, not Open WebUI. GDPR is what makes it different."
- Authority: EU-based, compliance-grade automation for enterprise clients
- Nav to Solution: two systems, email monitor is Phase 1, show pipeline flow
- Nav to Workflow: data flow table, GDPR lifecycle (30/90/120 day retention)
- Nav to GDPR: the differentiator page. International transfers, Article 22, SARs
- Nav to Timeline: Phase 1 = 3 weeks, Phase 2 = 2 weeks
- Nav to Investment: $3,250 total, address $600 gap, Phase 1 stands alone at $1,850
- Nav to Onboarding: form to get started, no prep needed
- Close: "Happy to discuss scope or phasing."
