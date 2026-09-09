# AI Lead Gen & Follow-Up System -- Video Script

## Duration: ~3-4 min (content-driven)

---

### BEAT 1 -- Reframe (0:00-0:40)

SAY: Hi there, Nico here. I saw Emma's posting for an AI-powered lead generation system in n8n, and I wanted to show you what I'd build.

SAY: The interesting thing about lead gen in Food and Beverage is that finding businesses isn't the hard part. Google Maps, Yelp, industry directories. The information is out there. The hard part is what happens after you find them. You write a personalized email, get busy, forget to follow up, and the lead goes cold. Multiply that by 50 a week and your pipeline leaks faster than you can fill it.

SAY: So the system I'd build solves the follow-through problem, not just the sourcing problem.

---

### AUTHORITY (0:40-1:00)

SAY: Quick context on fit. I've built production n8n workflows with this kind of multi-stage pipeline logic, and my background is in marketing systems. I've designed pipelines that generated 600K+ weekly impressions. So I understand what lead gen is supposed to achieve, not just how to connect APIs.

---

### BEAT 2 -- Structure (1:00-1:50)

>> Show solution page, scrolled to pipeline diagram

SAY: Here's the pipeline. Five stages, four n8n workflows.

SAY: Stage one pulls leads from Google Maps, Yelp, and industry directories on a schedule. Each source runs independently so if one goes down the others keep working.

SAY: Stage two deduplicates and stores everything in your Google Sheet. No double entries. Missing emails get enriched from the business website.

SAY: Stage three scores every lead zero to one hundred. Online presence, review activity, business type, location fit, growth signals. The weights are configurable.

SAY: Stage four is where the AI comes in. Instead of a generic template, each lead gets a personalized email that references something specific about their business.

SAY: Stage five handles follow-up. Two to three messages over a configurable window. Reply detection stops the sequence the moment someone responds.

---

### BEAT 3 -- Live Demo (1:50-2:40)

>> Switch to workflow page, scroll to the live demo section

SAY: Let me show you what the AI piece actually does. This is a live demo on the proposal site.

SAY: I'll type in a sample business. Rosie's BBQ in Champaign, Illinois.

>> Type "Rosie's BBQ Champaign" into the business name field, "BBQ Restaurant" in type, "Champaign, IL" in location. Click "Score This Lead."

SAY: The AI is analyzing the business now. It comes back with a lead score and reasoning, plus a full personalized outreach email. This is the same logic that would run inside the n8n workflow, processing each lead automatically.

>> Scroll through the result showing score, tags, and generated email

SAY: That email references their cuisine, their review presence, their location. Every lead gets a different message. That's the difference between a system and a spreadsheet.

---

### BEAT 4 -- Edge Cases + Close (2:40-end)

>> Scroll to investment page

SAY: A few things about reliability. Duplicate leads are caught before they hit your sheet. Bounced emails stop the follow-up sequence. Opt-outs are permanent. And there's a fallback to template-based emails if the AI is temporarily unavailable.

SAY: Pricing is $750 fixed for the complete system. $500 for Phase 1 which gets leads sourcing and basic outreach running in four days. $250 for Phase 2 which adds the AI personalization and follow-up sequence.

SAY: There's also a downloadable n8n starter workflow on the site you can import right now and see the node layout.

SAY: If this looks like a fit, the onboarding form on the site collects everything I'd need to start building. Happy to talk through any of it.

---

## LOOM NOTES VERSION

- Open with job posting visible, mention Emma by name
- Reframe: the problem is follow-through, not sourcing
- Authority: n8n production workflows, 600K impressions marketing background
- Show solution page pipeline diagram, walk through 5 stages
- Switch to workflow page, do the live demo with Rosie's BBQ
- Demo: type in business, show score + generated email
- Scroll to investment: $750 fixed ($500 Phase 1 + $250 Phase 2)
- Mention downloadable starter workflow
- Close: onboarding form, happy to talk
