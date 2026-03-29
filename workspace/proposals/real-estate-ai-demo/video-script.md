# Video Script -- Real Estate AI Demo

## Target Duration: 3-4 minutes

---

### BEAT 1 -- Reframe and Authority (~30 seconds)

>> Their job posting

SAY: Hi there, Nico here. I saw your posting for an n8n developer to build a real estate AI demo. Google Sheet trigger, RAG on a property PDF, and Twilio SMS.

>> Highlight "live magic" and "speed-to-lead"

SAY: The way I read this, the demo needs to create a moment where the agent watches a text message land on their phone before they've finished reading the question out loud. That's the speed-to-lead proof you're selling.

SAY: The harder part is making this demo reset-proof. Back-to-back meetings, different properties each time. The PDF swap and vector store refresh have to be invisible to you.

---

### (continued)

>> My Upwork profile

SAY: Quick context on me. I'm based in Karlsruhe, Germany, six hours ahead of Louisville. I build n8n workflows full-time, including RAG pipelines with vector stores and AI agent nodes. So the exact stack you described is something I work with regularly.

---

### BEAT 2 -- Walkthrough (~90 seconds)

>> Open proposal site, hero + stat cards

SAY: I put together a full proposal site showing how I'd build this. Let me walk through it.

>> Nav: Solution

SAY: The main workflow starts with a Google Sheets trigger. A new row comes in with the lead name, phone number, and their question. That fires an AI Agent node.

>> Sidebar: "Lead Response Workflow"

SAY: The agent has a vector store loaded with your property PDF. It finds the relevant section, drafts a concise answer that fits in one SMS, and sends it through Twilio. The whole thing takes under 10 seconds.

---

### (Solution page continued)

>> Sidebar: "PDF Ingestion Workflow"

SAY: The second workflow handles the property swap. You drop a new PDF into a Google Drive folder. The workflow extracts the text, chunks it, and rebuilds the vector store. After that, the demo is ready for the new property with zero manual steps.

>> Nav: Workflow

SAY: Here's the visual flow showing both workflows side by side. The top path is the lead response, the bottom is the ingestion pipeline.

---

### (FAQ page -- ~30 seconds)

>> Nav: FAQ

SAY: A few things about reliability. The SMS arrives in under 10 seconds. If Twilio returns an error, the Google Sheet row turns red and logs the message immediately. Nothing fails silently.

>> Scroll to "SMS character limits"

SAY: The AI prompt is tuned to keep responses under 160 characters, which is one SMS segment. No split messages, no cut-off text on the recipient's phone.

>> Scroll to "vector store refresh"

SAY: When you drop a new PDF, ingestion takes 30 to 60 seconds. A status indicator in the Sheet tells you when it's ready for the next demo.

---

### (Investment page -- ~15 seconds)

>> Nav: Investment

SAY: On pricing, I'm proposing $650 fixed. I see this posted as hourly, but for a clearly scoped demo build like this, fixed-price makes more sense. You pay for the complete working system regardless of hours.

---

### BEAT 3 -- Close (~20 seconds)

>> Scroll to "What Comes Next"

SAY: Once the core demo is solid, the natural extensions are multi-property support, demo analytics to track what questions agents ask most, and a CRM push so leads flow into your pipeline.

>> Nav: Onboarding

SAY: The onboarding page collects what I need to start. Your n8n access, a sample property PDF, and your preferred AI tone. I can have this ready for testing inside your 5 to 7 day window. Looking forward to hearing from you.

---

## LOOM NOTES VERSION

- Open on their job posting. "The demo isn't about AI answering questions. It's a live magic moment where SMS arrives before the agent finishes reading."
- My profile: Karlsruhe (6hr ahead of Louisville), n8n full-time, RAG pipelines with vector stores.
- Overview page: stat cards (<10s response, 2 workflows, 5 days, $650).
- Solution page -- 2 workflows:
  - Lead response: Sheets trigger, AI Agent + vector store, Twilio SMS. Under 10 seconds.
  - PDF ingestion: Drive folder, extract, chunk, rebuild vector store. Zero manual steps.
- Workflow page: visual flow, both pipelines side by side.
- FAQ page: SMS under 10s, failure = red row, 160-char limit, vector store refresh 30-60s.
- Investment: $650 fixed, not hourly. Defined scope, no surprises.
- Close: extensions (multi-property, analytics, CRM). Onboarding page collects everything. 5-7 day delivery.
