# Brisken Expense Reconciliation Platform: Open Decisions

**Prepared:** 2026-05-14
**For:** Dirk (Brisken CEO)
**Purpose:** Capture every open decision the development team needs answered before the product specification can be finalized and the build can start. Each decision lists three options with the benefits and downsides of each, so the conversation focuses on choice instead of on framing the question.

## How to use this document

1. Read each decision once end to end. The decisions are grouped by theme (architecture, integration, matching, users, compliance, productization). Decisions in the same group sometimes depend on each other, so reading the group together helps.
2. Pick one option per decision. Write your pick under each one, or send the picks back as a list (A1 = Option 1, A2 = Option 2, etc.).
3. If a decision needs more context to choose, flag it. Some decisions have downstream effects that are worth a short call before locking in.
4. Once the picks come back, the team writes the finalized product specification and breaks it into implementation specs aligned with the phased build plan in the functional document (foundation, statement import, receipt processing, matching, classification, review table, export, hardening).

Defaults that the team is assuming without asking are listed at the bottom of this document. Override any of them by replying.

---

## Team recommendation at a glance

The picks below assume one headline goal: build the platform so it can be productized and sold to other companies later, with Brisken's own reconciliation overhead as the binding budget constraint on what ships in MVP. Each pick is the option that serves that goal combination best without inflating MVP scope. Override any of them by replying with a different option number; the table is a starting point, not a final answer.

If the headline goal should be different (internal-only with no productization, or full enterprise-grade from day one), the picks shift. The companion goal-clarification message covers this.

| Decision | Recommended pick | Reason in one line |
|---|---|---|
| A1 | Option 1: USD, post statement amount | Simplest, accurate, no internal FX engine needed |
| A2 | Option 1: Multi-tenant scaffolded, single org MVP | Productize-ready with near-zero added MVP cost |
| A3 | Option 1: Azure Blob scaffolded, local disk MVP | Fast MVP, clean migration path to production |
| A4 | Option 1: Azure Document Intelligence plus Anthropic Claude | Best receipt accuracy, strong German handling |
| B1 | Option 1: CSV plus Excel for data, plus the Zoho API for attachments | Preserves the receipt-linkage requirement without a full API integration |
| B2 | Option 1: Imported from the Zoho Books API at setup | Single source of truth, no chart-of-accounts drift |
| B3 | Option 1: Custom fields on the Zoho expense record | Filterable in Zoho reports for the accountant |
| C1 | Option 1: CSV plus Excel with a column-mapping wizard | Covers every bank, no PDF flakiness |
| D1 | Option 1: Plus or minus three days, plus or minus two percent | Start tight, loosen with real data after the first month |
| D2 | Option 1: Review everything in MVP, configurable auto-approval in Release 2 | Earn trust in the AI before letting it run unattended |
| D3 | Option 2: One transaction to multiple receipts, no category splits | Covers hotel and grouped-meal cases, skips the rest |
| E1 | Option 2: Strict plus a Needs Mapping placeholder | No invented categories; gaps surface for the admin |
| F1 | Option 1: Single admin user, role enum scaffolded | Simplest UI, future roles added without migration |
| G1 | Option 2: Configurable retention per category from day one | Required before commercial customers arrive |
| G2 | Option 1: Direct send with data-processing agreements | Standard pattern, fast, defensible for resale |
| G3 | Option 3: AI-decision logging plus approval log | Captures the most product-improvement-relevant data |
| H1 | Option 1: No billing in MVP, internal Brisken use first | Don't build billing until a paying customer demands it |
| H2 | Option 1: Locked after export, corrections via reversal workflow | Standard accounting principle, clean audit trail |

---

## A. Architecture and infrastructure

### A1. Base currency and which amount gets posted

**Context:** When a receipt is in one currency and the credit card statement is in another, only one number becomes the official accounting amount. The choice affects how foreign expenses appear in the books and whether the platform needs to handle FX (foreign exchange, currency conversion) rates internally.

**Option 1: USD base, post the statement amount**
- Benefits: The card issuer already converted the FX. The platform's amount matches the bank record exactly. No FX engine needed inside the product. Simplest for management reporting.
- Downsides: Receipt amount and posted amount can differ visibly. An auditor reading the books needs to check both fields to understand the variance.

**Option 2: USD base, post the receipt amount and store the FX rate as metadata**
- Benefits: Reflects what the vendor actually charged before card processing fees. Cleaner if Brisken wants to track FX losses as a separate line in management reporting.
- Downsides: Requires an internal FX rate source (a daily rate feed or a derived rate from the statement). More moving parts. Mismatches with the bank record turn into reconciliation work.

**Option 3: EUR base instead of USD**
- Benefits: Pick this if Brisken's primary operations and accounting are in EUR. Simpler if most receipts are euro-denominated.
- Downsides: Wrong base currency creates lifetime FX overhead. Hard to change later. Only pick if EUR is genuinely the operating currency.

---

### A2. Multi-tenant approach

**Context:** A multi-tenant system, the architecture pattern where one application serves many companies in isolation, costs slightly more upfront but enables selling the platform to other companies later without rebuilding.

**Option 1: Multi-tenant scaffolded, single organization for MVP (minimum viable product, the first shippable version)**
- Benefits: Every database table carries an organization identifier from day one. Brisken is the only provisioned organization at MVP. Future expansion to other companies is a configuration and UI change, not a data migration. Small added upfront work.
- Downsides: Small extra complexity in every database query and access check. The team needs to follow tenant-isolation discipline from the start.

**Option 2: Strict single-tenant for Brisken only**
- Benefits: Simplest schema. No organization identifier columns. Smallest MVP scope.
- Downsides: If Brisken later wants to sell the platform to other companies, or run a second internal entity on it, expect a multi-week data migration and the risk of cross-tenant data leaks during the transition.

**Option 3: Full multi-tenant SaaS (software-as-a-service, a hosted product sold to multiple customers) in MVP**
- Benefits: Tenant signup, organization-admin invitations, and billing hooks ready on day one. No future productization work needed.
- Downsides: Substantially larger MVP scope. Pick only if Brisken intends to sell the platform to outside companies within six months.

---

### A3. File storage provider for receipt files

**Context:** The platform needs durable storage for receipt images and PDFs. Storage choice affects security posture and operational cost.

**Option 1: Azure Blob Storage scaffolded for production, local disk for MVP**
- Benefits: Local disk speeds MVP shipping. The storage interface is abstracted, so swapping to Azure Blob (Microsoft's cloud object-storage service) for production is a configuration change. Keeps the AI processing stack and storage on the same cloud later.
- Downsides: MVP storage on a single server has weaker durability and no encryption at rest by default. Not suitable for production without the swap.

**Option 2: Azure Blob Storage from day one**
- Benefits: Encryption at rest by default. Tight pairing with Azure Document Intelligence (the OCR service in option A4) reduces latency. Production-grade durability from MVP onward.
- Downsides: Small additional setup. Carries Azure storage cost from day one (current rate to be confirmed against Azure pricing at the time of build).

**Option 3: Amazon S3 or Cloudflare R2 (S3, Amazon's cloud object-storage service; R2 is a similar product from Cloudflare with zero egress fees)**
- Benefits: Industry standard. Mature SDK (software development kit, the developer library) support. R2 has zero egress fees if previewing receipts gets heavy.
- Downsides: Splits the stack across two clouds (storage on AWS or Cloudflare, AI on Azure). Slight added latency on cross-cloud calls. Egress costs on AWS S3 can grow with frequent receipt previews.

---

### A4. OCR and AI provider stack

**Context:** The platform reads text from receipts using OCR (optical character recognition, the technology that turns scanned images into searchable text) and uses an LLM (large language model, the underlying AI behind systems like ChatGPT or Claude) for classification and reasoning. Provider choice affects accuracy, cost per receipt, and data residency.

**Option 1: Azure Document Intelligence plus Anthropic Claude**
- Benefits: Azure Document Intelligence has a prebuilt receipt model trained on receipts specifically. Strong German-language handling for European receipts. Claude (Anthropic's LLM) handles classification, line-item reasoning, and ambiguity detection well.
- Downsides: Two vendor relationships. Per-document Azure cost plus per-token Anthropic cost (exact pricing TBD against current Azure and Anthropic rate cards at the time of build). Slightly more setup than a single-vendor stack.

**Option 2: Google Document AI plus Anthropic Claude**
- Benefits: Google Document AI has an expense receipt parser that is often strong on US-issued receipts. Same Claude benefits for classification.
- Downsides: Splits across Google Cloud and Anthropic. Slightly weaker German-language handling than Azure Document Intelligence. Requires a GCP (Google Cloud Platform, Google's cloud computing service) account setup.

**Option 3: Open-source OCR plus Claude doing everything else**
- Benefits: Lowest per-document cost. Open-source OCR libraries like Tesseract or PaddleOCR pull raw text, then Claude does field extraction, classification, and matching reasoning in one pass. No OCR vendor cost.
- Downsides: Open-source OCR is less mature on low-quality phone-camera receipts. Multi-language handling weaker. More tuning work upfront. Latency higher because Claude carries more of the load.

---

## B. Zoho Books integration

### B1. Zoho Books integration method for MVP

**Context:** Zoho Books accepts expenses by file upload or via its API (the programmatic interface that lets software talk to Zoho directly). File upload alone does not transfer receipt attachments; the attachments must come through the API.

**Option 1: CSV plus Excel for the data, plus the Zoho API for the attachments**
- Benefits: Hybrid approach. Use Zoho's standard expense import CSV for the records, then push the receipt files to Zoho through its API. Preserves the receipt-linkage requirement. Avoids building the full API integration for record creation.
- Downsides: Two paths to maintain. The Zoho API still needs authentication setup in MVP. If the CSV import fails after the attachments have already been pushed, the platform needs cleanup logic.

**Option 2: Pure CSV file import, attachments deferred to Release 2**
- Benefits: Smallest MVP scope. Zero Zoho API work. Ships fastest.
- Downsides: Receipts stay only inside our platform until Release 2. Zoho Books expenses have no attached receipts in MVP. Weakly matches the stated requirement that receipts must live with the expense record in Zoho.

**Option 3: Full Zoho Books API for both records and attachments in MVP**
- Benefits: Skip the file step entirely. Expenses post live to Zoho. Attachments post live. No Release 2 rework needed for this integration.
- Downsides: Pulls API integration forward by one phase of work. Moderately larger MVP scope. More Zoho-side authentication, rate-limit handling, and error-recovery logic on day one.

---

### B2. Chart of accounts source

**Context:** The expense categories the AI assigns must match what Zoho Books has configured. Categories can come from Zoho directly (the source of truth) or be entered manually in the platform.

**Option 1: Imported from the Zoho Books API at setup, refreshable on demand**
- Benefits: Single source of truth. The AI classifies only against real Zoho categories. No drift when Brisken adds or renames an expense account in Zoho.
- Downsides: Requires Zoho API access at MVP setup even if you pick file-only export in B1. Adds one setup step.

**Option 2: Manually entered in platform settings and mapped to Zoho names**
- Benefits: No Zoho API dependency. Works even if Zoho API access is delayed. Fast to set up for a small fixed list.
- Downsides: Drifts whenever Zoho's chart of accounts changes. Risk of typos and mapping errors. Manual re-entry whenever categories change.

**Option 3: Manual list in MVP, API import in Release 2**
- Benefits: Smallest MVP scope. Defers the Zoho API setup.
- Downsides: Locks in category re-entry now. The later transition can leave stale mappings until cleaned up.

---

### B3. Personal, business, and reimbursement classification

**Context:** Some expenses on a business card are personal (the employee pays the company back), and some expenses on a personal card are business (the company reimburses the employee). The platform needs a way to flag and route each case to the right accounting destination.

**Option 1: Custom fields on the Zoho expense record**
- Benefits: Status (business, personal, reimbursement) lives on the official accounting record. Filterable in Zoho reports. A reimbursement workflow can hook off the field later.
- Downsides: Requires Brisken to add the custom fields in Zoho Books. One-time setup, but it needs Zoho admin access.

**Option 2: Description tagging only**
- Benefits: No Zoho setup required. The status appears in the description text as a tag like `[PERSONAL]` or `[REIMBURSEMENT]`.
- Downsides: Not filterable in Zoho reports without text-search workarounds. Less clean for the accountant.

**Option 3: Separate Zoho expense accounts per category**
- Benefits: Personal-on-business-card and reimbursement-from-personal-card become their own expense accounts. Strong segregation for reporting.
- Downsides: The chart of accounts grows. Setup effort. Less flexible if the company changes its reimbursement policy later.

---

## C. Source data formats

### C1. Statement file formats supported in MVP

**Context:** Credit card statements come from banks in different formats. The tradeoff is coverage breadth against build effort.

**Option 1: CSV plus Excel, with a column-mapping wizard**
- Benefits: Covers every bank and card. User maps the columns once per account on first upload (Date is column A, Amount is column B, etc.); the mapping is saved and reused on every later upload from that account. Handles uncommon issuers automatically. PDF deferred to Release 2.
- Downsides: A one-time mapping step per account at setup. The mapping wizard adds about half a phase of UI work.

**Option 2: CSV plus Excel plus PDF**
- Benefits: Catches banks that only offer PDF statements. Uses Python libraries (pdfplumber or Camelot) that extract tables from PDFs.
- Downsides: PDF table extraction is flaky on uncommon issuers. Adds about one phase of work and a fallback manual-mapping path for failures.

**Option 3: CSV plus Excel plus named templates per provider**
- Benefits: For supported providers (e.g., Chase, Amex), no mapping wizard appears: the platform recognizes the file format automatically. Smoother user experience for common cards.
- Downsides: Each new provider needs a hand-built template. Falls back to generic mapping for any unsupported provider.

---

## D. Matching engine and automation

### D1. Matching tolerances

**Context:** The platform needs to know how much slack to allow between a receipt and a statement line. Too strict misses valid matches; too loose creates wrong matches.

**Option 1: Plus or minus three days on date, plus or minus two percent on amount**
- Benefits: Catches most card-issuer settlement delays and minor tip-rounding. Industry-standard tolerance.
- Downsides: Some weekend and holiday settlement delays exceed three days. Tip-heavy restaurants can vary by more than two percent of the bill.

**Option 2: Plus or minus seven days on date, plus or minus five percent on amount**
- Benefits: Generous tolerance. Handles long bank delays and international tips. Fewer no-match cases for human review.
- Downsides: More borderline matches enter the review queue at low confidence. Higher risk of an incorrect auto-match if the confidence thresholds in D2 are loose.

**Option 3: Configurable per financial account**
- Benefits: Admin sets tolerances per card type. Tight for domestic cards, looser for international cards.
- Downsides: One more setup step. Admins may pick the wrong values and only notice after errors compound.

---

### D2. Confidence thresholds and auto-approval policy

**Context:** Each match and classification gets a confidence score. The threshold sets when the platform proceeds without human review.

**Option 1: Review everything in MVP, configurable auto-approval in Release 2**
- Benefits: Maximum human control. No surprises during the first month. Builds trust in the AI before letting it run unattended.
- Downsides: The user still reviews every record at MVP, which cuts into the fifteen-minute promise from the functional document. The auto-approval value comes later.

**Option 2: Auto-approve above ninety-five percent confidence in MVP**
- Benefits: High-confidence records skip review. Closer to the fifteen-minute target from day one. The review queue only contains records that actually need attention.
- Downsides: Calibrating the ninety-five percent threshold correctly is empirical. Early data may need adjustment after the first month.

**Option 3: Auto-approve only low-risk categories above ninety-five percent**
- Benefits: Auto-approves obvious cases (recurring software subscriptions from known vendors) but holds high-value or ambiguous categories (travel, meals, entertainment) for review.
- Downsides: A per-category policy is more setup. The definition of "low-risk" needs to be agreed.

---

### D3. Splits and multi-receipt cases in MVP

**Context:** Sometimes one card charge corresponds to multiple receipts (a hotel split across multiple nights), or one receipt spans multiple accounting categories (groceries plus electronics on one Costco trip), or one card charge includes a tip that the receipt does not show.

**Option 1: No splits or multi-receipt in MVP, manual handling for now**
- Benefits: Smallest MVP. These edge cases get handled outside the platform initially. Most expenses are one-to-one.
- Downsides: Power users hit the limit quickly. The workaround adds friction. Some accountants find this dealbreaking.

**Option 2: One transaction to multiple receipts supported, no category splits**
- Benefits: Hotel-split and grouped-meal cases work. Still skips the category-split complexity. Moderate MVP cost.
- Downsides: Splitting one transaction across multiple expense categories still requires manual handling outside the platform.

**Option 3: Full splits and multi-receipt in MVP**
- Benefits: Every edge case from day one. No workarounds needed.
- Downsides: Adds about one phase of work. Complicates the review table UI.

---

## E. AI behavior

### E1. Category suggestions: strict or allowed to propose new

**Context:** When the AI is uncertain about a receipt, should it stick to the existing chart of accounts or be allowed to suggest a new category?

**Option 1: Strict, AI picks from the existing chart only**
- Benefits: No invented categories. Predictable behavior. Cleaner Zoho output.
- Downsides: When an obviously new category appears (a new vendor type Brisken hasn't seen before), the AI picks the closest existing match, possibly wrongly. The user has to notice and correct.

**Option 2: Strict plus a "Needs Mapping" placeholder**
- Benefits: When the AI cannot confidently place an expense in an existing category, it tags the record "Needs Mapping" and the user decides whether to extend the chart of accounts or pick an existing match.
- Downsides: A small extra review step. Risk of "Needs Mapping" becoming a dumping ground if users avoid the decision.

**Option 3: Allowed to propose new categories with a warning flag**
- Benefits: AI surfaces patterns that suggest the chart of accounts needs extension. Admin reviews proposals before they get added to Zoho.
- Downsides: More noise in the review queue. Risk of category sprawl if admin approves new categories too liberally.

---

## F. Users and access

### F1. User roles in MVP

**Context:** The MVP target user is a single admin doing the whole workflow (upload, review, approve, export). Future versions need other roles (employee submitter, separate reviewer, separate approver, accountant, read-only auditor).

**Option 1: Single admin user, role enum scaffolded in the database**
- Benefits: MVP has just one user account, but the database is ready for more roles without migration. Future additions are a UI change. Simplest authentication: email plus password plus magic-link reset.
- Downsides: Brisken's accountant cannot view records read-only until Release 2.

**Option 2: Admin plus read-only accountant**
- Benefits: Brisken's accountant gets early view-only access plus CSV export. Common request from external accounting-services arrangements.
- Downsides: Two user types means slightly more UI work for view-permission filtering.

**Option 3: Admin plus employee submitter**
- Benefits: Employees upload their own receipts and see only their own records. Admin reviews everyone's. Pulls a piece of Release 3 forward.
- Downsides: Per-user record filtering is moderate work. Adds an invitation flow.

---

## G. Compliance and data handling

### G1. Retention policy and GDPR deletion

**Context:** Financial documents have legal retention periods that vary by jurisdiction (the exact required period for Brisken's tax jurisdictions should be confirmed with the company's accountant or legal counsel). European data privacy law (GDPR, the EU's data privacy regulation) requires that personal data can be deleted on request.

**Option 1: Indefinite retention in MVP, retention configuration in Release 2**
- Benefits: No deletion logic needed in MVP. Receipts kept forever until Brisken decides otherwise. Smallest MVP.
- Downsides: When commercial customers arrive, retention configuration becomes mandatory and the migration of legacy data is fiddly.

**Option 2: Configurable retention per category from day one, with the default value set by Brisken's accountant**
- Benefits: Retention policy ready before commercial customers arrive. Receipts auto-archive or auto-delete based on policy. Cleaner long-term storage cost.
- Downsides: Adds a retention engine in MVP. About half a phase of work. Requires Brisken's accountant to specify the default retention duration before the build starts.

**Option 3: Configurable retention plus a GDPR deletion-request workflow**
- Benefits: Right-to-be-forgotten (the GDPR rule that lets a person demand their data be erased) supported from day one. An anonymization workflow handles fiscal records that must stay retained but with personal data removed.
- Downsides: Adds about one phase of work. Most relevant if Brisken operates in or sells to the EU.

---

### G2. Third-party AI service authorization for financial documents

**Context:** Receipts and statements contain financial and possibly personal data. Sending them to a third-party AI provider needs explicit authorization or anonymization.

**Option 1: Direct send to Azure Document Intelligence and Anthropic Claude with data-processing agreements**
- Benefits: Full receipt accuracy. Both providers offer enterprise data-processing agreements and do not train their models on customer data. Standard pattern.
- Downsides: The customer must accept that their receipts and statements briefly pass through Azure and Anthropic systems. Some companies forbid this.

**Option 2: Redact personally identifiable fields before sending**
- Benefits: Names, cardholder numbers, and addresses get blanked out locally before AI processing. Reduces sensitivity exposure.
- Downsides: Redaction can break vendor name matching (the redacted name might actually be the vendor on a sole-proprietor receipt). More tuning work. Some accuracy loss.

**Option 3: Self-hosted OCR and LLM only**
- Benefits: No data leaves the environment. Pick if Brisken or their clients refuse any third-party AI exposure to financial documents.
- Downsides: Much higher infrastructure cost (GPU servers, ongoing model maintenance). Lower accuracy. Slower to ship.

---

### G3. Audit logging scope in MVP

**Context:** An audit log records who changed what and when. Required for accounting compliance and useful for debugging where AI suggestions diverge from human decisions.

**Option 1: Minimal: log approvals, rejections, and exports only**
- Benefits: Smallest MVP audit footprint. Covers the most-asked-for compliance question (who approved this expense and when).
- Downsides: Field-level edits (vendor changed, amount corrected) are not logged. Some auditors will want this later.

**Option 2: Full field-level audit log from day one**
- Benefits: Every change recorded with before-and-after values. Strongest audit trail. Easier root-cause analysis if a posting goes wrong.
- Downsides: Adds about a third of a phase of work. Storage cost grows slowly over time.

**Option 3: AI-decision logging plus approval log, no field edits**
- Benefits: Captures the most product-improvement-relevant data: what the AI suggested versus what the user picked. Drives future AI model tuning.
- Downsides: Field-level corrections still untracked. Mixed coverage.

---

## H. Commercial productization

### H1. Billing model for future commercial use

**Context:** If Brisken plans to sell this platform to other companies, the billing model affects what the MVP needs to instrument.

**Option 1: No billing in MVP, internal Brisken use only for now**
- Benefits: Zero billing work. Validate the product on Brisken's own books before opening it up to other companies.
- Downsides: When the commercial launch comes, billing scaffolding is greenfield work.

**Option 2: Per-organization flat monthly fee, billing implemented in Release 2**
- Benefits: Simple pricing. The multi-tenancy scaffolding from A2 supports this naturally. Billing software (Stripe or Paddle) gets integrated when the first paying customer signs.
- Downsides: Flat fees may not capture value well for very-large-volume customers.

**Option 3: Per-document-processed pricing, with usage metering in MVP**
- Benefits: Aligns price with cost (OCR and AI charge per document). Fair for both small and large customers.
- Downsides: Usage metering adds infrastructure to MVP. Customers may dislike unpredictable bills.

---

### H2. Locking records after export

**Context:** Once an expense has been exported or posted to Zoho Books, should the platform allow further edits to the original record?

**Option 1: Locked after export, corrections require a reversal workflow**
- Benefits: Matches the accounting principle that posted records should not change silently. The audit trail stays clean. Standard pattern in finance software.
- Downsides: If a small typo is found post-export, the user must go through a reversal step rather than fix it inline.

**Option 2: Editable with warning, changes flagged in the audit log**
- Benefits: Fast correction for small mistakes. Less friction for the user.
- Downsides: Risk of silent edits to posted records. Cleanup work later if the Zoho copy and the platform copy drift.

**Option 3: Locked plus per-field unlock by admin**
- Benefits: Default locked, but the admin can selectively unlock fields (e.g., description) for correction without a full reversal.
- Downsides: Per-field rules add UI complexity. Slightly more setup.

---

## Defaults assumed (not blocking, override by replying)

The team is assuming these defaults so the decision list stays focused on the load-bearing choices. Override any of them by replying.

| Default | Assumption | Why this default |
|---------|------------|------------------|
| Encryption at rest for all stored receipts | Yes from day one, regardless of which storage option in A3 is picked | Industry minimum, near-zero cost when using Azure or S3 |
| Inactive Zoho expense accounts hidden from AI classification | Yes | Avoids the AI picking an account that's been retired |
| Confidence score methodology | Use the OCR provider's per-field confidence score, combined with an LLM-derived semantic confidence on classification, on a zero-to-one hundred scale | Standard pattern, no business reason to deviate |
| Authentication | Email and password, with magic-link password reset | Lowest-friction pattern for an internal tool |
| Duplicate detection | Image hash plus the combination of vendor, date, and amount; never auto-deleted, always flagged for user review | Matches Section 18 of the functional document |
| File size limit per receipt | Ten megabytes | Covers high-resolution phone-camera PDFs comfortably |
| Supported receipt languages in MVP | English, German, Portuguese, with English as the system's working language | Matches Section 12 of the functional document |
| Mobile receipt scanning | Deferred to Release 3 per the functional document | Already aligned with the source spec |
| VAT extraction | Captured as metadata but not posted to accounting in MVP | Matches Section 11 of the functional document, since the initial use case is management reporting |
| Hosting environment for the application | Azure App Service or a similar managed container platform on Azure, given the AI provider choice | Co-locates application and AI provider for latency and data residency |

---

## What happens after the picks come back

Once Dirk's picks are in, the development team will:

1. Finalize the product specification document with every decision locked in.
2. Break the product into implementation specifications aligned with the eight-phase build plan (foundation, statement import, receipt processing, matching engine, AI classification, review table, Zoho export, hardening).
3. Provide a development estimate and an implementation roadmap, as listed in Section 33 of the functional document.
4. Begin Phase 1 (foundation: application structure, authentication, database, organization and account setup, file storage).

Any decision that turns out to need more discussion can be revisited; the spec is not frozen until the team confirms back to Brisken that it is ready for the build.
