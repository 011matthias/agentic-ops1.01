# Video Script -- n8n HubSpot/Xero Automation

## Target Duration: 3 minutes

---

### BEAT 1 -- Reframe (~30s)

>> Nav: Overview page, hero visible ("n8n Automation for HubSpot + Xero")

SAY: "Hi there, Nico here. I saw your posting for two n8n automations and put together a proposal site showing how I'd build them."

>> Nav: scroll to "What Gets Automated" on Overview

SAY: "The folder automation is straightforward. The invoice one is where the detail matters. You've got 3 pricing options coming from a custom field in HubSpot, and that field needs to map cleanly into Xero line items. If it doesn't, invoices go out wrong or fail silently. That's the piece I'd focus on first."

---

### (continued -- Authority ~15s)

>> Nav: stay on Overview, "How It Works" section visible

SAY: "Quick context. I build n8n workflows full-time, self-hosted and cloud. I've designed CRM sync patterns that handle exactly this kind of field mapping and contact matching."

SAY: "I'm based in Germany, one hour ahead of you. English is native."

---

### BEAT 2 -- Structure (~60s)

>> Nav: Solution page, "Automation 1: Deal Won to Xero Invoice"

SAY: "Starting with the invoice automation. The trigger watches for deal stage changes in HubSpot. When a deal hits Won, it extracts the amount, contact details, and the custom pricing field. Then it maps the pricing tier to the correct Xero line items."

>> Nav: scroll to show the detail grid (Field Extraction, Pricing Mapping, Contact Matching)

SAY: "Before creating the invoice, it looks up the contact in Xero by email. If they don't exist, it creates them. Then it builds the invoice with the right line items, sends it, and logs the reference back to the deal in HubSpot."

>> Nav: scroll to "Automation 2: Form Submission to Google Drive Folder"

SAY: "The folder automation is simpler. Form submission triggers n8n, it pulls the contact details, creates a Drive folder with a naming convention, sets up subfolders, and writes the folder URL back to the HubSpot contact."

>> Nav: Workflow page, "Automation 1: Deal Won to Xero Invoice" flow diagram

SAY: "The workflow page shows the full data flow with decision points. Notice the branching: if the pricing field is invalid, it flags the deal instead of creating a broken invoice. And if a contact doesn't exist in Xero, it creates one before proceeding."

---

### BEAT 3 -- Edge Cases + Value (~40s)

>> Nav: scroll to "Automation 2: Form Submission to Google Drive Folder" flow on Workflow page

SAY: "Same pattern on the folder side. Duplicate detection, missing field handling, permission checks."

>> Nav: Investment page, price hero ($350)

SAY: "$350 fixed for both automations. I know the posting says hourly, but for a defined scope, fixed is simpler."

>> Nav: scroll to "How It Compares" table

SAY: "I've put together a comparison. HubSpot's native workflows can't connect to Xero directly. And since you've already got n8n self-hosted, there's no additional platform cost per operation. The comparison table has the details, sourced from your job posting and HubSpot's pricing page."

>> Nav: Timeline page, phases visible

SAY: "Timeline is 5 days. Day 1 I review your existing mock-ups and give you an honest recommendation on whether to fix or rebuild. Days 2-3 are the build. Days 4-5 are testing and handoff with documentation."

---

### BEAT 4 -- Close (~15s)

>> Nav: Solution page, scroll to "Starter Template"

SAY: "There's also a downloadable n8n workflow template on the solution page that covers the core invoice flow. You can import it right now and see the structure."

>> Nav: Overview page, hero

SAY: "If useful, I can start with a quick review of your mock-ups before we commit to anything. Looking forward to hearing from you."

---

## LOOM NOTES VERSION

- Open on Overview page, hero
- Two automations: invoice is where detail matters (3 pricing tiers, Xero contact matching)
- Authority: n8n full-time, CRM sync patterns, Germany/CET, 1hr ahead
- Solution page: invoice automation flow (trigger, extract, map tier, Xero contact lookup/create, invoice, log back)
- Solution page: folder automation (form trigger, Drive folder, subfolders, URL back to HubSpot)
- Workflow page: show decision branching (invalid pricing field, missing contact)
- Investment page: $350 fixed, comparison table (HubSpot DIY vs freelancer avg vs ours, sourced)
- Timeline page: 3 phases, 5 days, review first
- Solution page: downloadable n8n workflow JSON
- Close: review mock-ups first, honest recommendation, looking forward
