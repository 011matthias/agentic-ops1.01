# Video Script -- AI Cold Email Tool

## Target Duration: 4-5 minutes

---

### PRE-ROLL (~30s)

>> Screen: Upwork job posting "AI Cold Email Tool Development"

SAY: Hi there, Nico here. I'm looking at your posting for the AI cold email tool. Apollo.io, Instantly.ai, AI personalization, scalable deliverability. I've built this exact pipeline before.

>> Scroll down briefly to "Other open jobs by this Client" section

SAY: One thing I noticed while doing my research. You've got a Sales Rep posting for lead gen and appointment setting, and a WordPress CRM recommendation request. Those aren't three separate problems. They're one pipeline. The tool I'd build handles the first two stages automatically.

>> Nav: browser tab to proposal site, enter access code jaret-2026

SAY: I put together a full proposal site that breaks this down. I also built a downloadable n8n workflow you can import and test yourself. Let me walk you through it.

---

### BEAT 1 -- The Opportunity (~40s)

>> Sidebar: The Opportunity

SAY: Here's how I'm reading this. You need a system that finds leads, writes personalized emails, and sends them without manual work at every step. Apollo.io handles the lead data, AI handles the personalization, and Instantly.ai handles the sending. The workflow I'd build connects all three.

>> Scroll to the paragraph about the Sales Rep posting

SAY: The cross-job angle is what stood out to me. Your cold email tool and your sales rep are two ends of the same pipeline. This system handles the top of funnel, prospecting and initial outreach, at scale. Your sales team only steps in when someone replies. That's the whole point.

---

### AUTHORITY (~15s)

SAY: Quick background. I run n8n workflows in production daily, including a marketing analytics pipeline that processes over 600,000 data points weekly through API integrations. I've also built a cold email pipeline with Instantly.ai for another client. So this isn't theoretical for me.

---

### BEAT 2 -- The Pipeline (~50s)

>> Sidebar: Your Pipeline

SAY: Four stages. Scrape, research, write, send.

>> Scroll slowly through the 4-zone grid

SAY: Stage one, Apollo.io pulls contacts by job title, company size, industry, and location. Stage two, OpenAI reads each company's website and figures out what they do, their industry, and likely pain points. Stage three, the AI uses that research to write a personalized subject line and opening paragraph for each lead. No two emails are the same. Stage four, Instantly.ai sends them on your schedule with warm-up and bounce handling built in.

>> Nav: click Solution in top nav

SAY: The solution page has the full technical breakdown if you want to see how each stage is wired.

>> Sidebar: Architecture Overview

SAY: Five n8n nodes in sequence, from trigger to send. Each stage is independent, so if one lead's company website is down, the pipeline skips the research step and keeps going.

---

### BEAT 3 -- Live Demo (~60s)

>> Nav: click Workflow in top nav

>> Sidebar: Pipeline Simulator

SAY: This is the part I'm most excited about. I built an interactive demo you can step through yourself.

>> Click "Start" or "Next Step" to advance to Stage 1

SAY: Stage one, we search Apollo for marketing directors at media companies in the US. The output shows real contact data: name, title, email, company, LinkedIn profile.

>> Click Next to Stage 2

SAY: Stage two takes the first lead, Sarah Chen at Bright Media Group, and researches her company. The AI pulls back their industry, focus area, size, and even recent activity like their podcast expansion.

>> Click Next to Stage 3

SAY: Now the AI writes the email. Look at the subject line: "Quick question about Bright Media's podcast expansion." That's not a template. That came from the research data two seconds ago. The opening paragraph references their specific move into podcasting. Every lead gets a unique version.

>> Click Next to Stage 4

SAY: The lead is enrolled in your Instantly.ai campaign with all the personalized fields attached. Sending is scheduled based on domain warm-up status.

>> Click Next to Stage 5 (logging)

SAY: And everything is logged to Google Sheets. Timestamp, lead info, campaign, status, personalization score. Full audit trail for every lead that goes through the pipeline.

---

### BEAT 4 -- Timeline and Pricing (~40s)

>> Nav: click Timeline in top nav

>> Sidebar: Phase 1: Lead Pipeline

SAY: Four phases over 14 days. Each phase has a checkpoint where you review the output before I move on. Phase one is the Apollo integration, you'll see leads in your sheet by day three. Phase two is the AI engine. Phase three connects Instantly. Phase four is end-to-end testing and the walkthrough video.

>> Nav: click Investment in top nav

>> Sidebar: Scope Breakdown

SAY: $800 fixed. That covers 16 hours of work across all four phases. Single milestone, payment after you've tested the pipeline yourself.

>> Sidebar: Pricing Note

SAY: I know the posted budget is $5 to $35 an hour. I'm proposing fixed-price because it scopes the work upfront and removes any incentive to stretch hours. If you want to start smaller, Phase 1 alone, just the Apollo scraping to Sheets, is $260 standalone.

---

### BEAT 5 -- Close (~20s)

>> Nav: click Overview in top nav

>> Sidebar: Download Workflow

SAY: One more thing. That downloadable workflow on the site is real. 19 n8n nodes, full error handling, Apollo to Instantly. Import it, plug in your API keys, and test it. Whether or not we work together, it's yours to keep.

SAY: If this looks interesting, the onboarding page collects everything I need to get started. API keys, target audience, sending preferences. Takes about five minutes. I'll confirm within 24 hours.

SAY: Thanks for watching. Talk soon.

---

## LOOM NOTES VERSION

- Open on Upwork job posting
- Note the other open jobs (Sales Rep, CRM) as one pipeline
- Enter access code, land on Overview
- The Opportunity: cross-job angle, automation replaces manual outreach
- Authority: 600K data points weekly, previous Instantly.ai build
- Your Pipeline: 4 zones (scrape/research/write/send)
- Solution page: architecture overview, 5 nodes in sequence
- Workflow page: step through the interactive demo (5 stages)
  - Apollo search results
  - AI company research
  - AI email with personalized subject line
  - Instantly enrollment
  - Sheets logging
- Timeline: 4 phases, 14 days, checkpoints at each
- Investment: $800 fixed, 16 hours, Phase 1 standalone at $260
- Download Workflow: 19 nodes, production-ready, free to keep
- Close: onboarding page, 5 min, 24hr confirmation
