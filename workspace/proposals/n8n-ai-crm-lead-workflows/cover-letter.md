# Cover Letter: AI CRM and Lead Workflows, Riyadh (p031)

Hi, Matthias here. Duplicate records, failed executions and incorrect AI-generated actions are the three places a setup like yours breaks, and each one gets its own control. Here's how I'd structure it, and where I've built the same pieces.

I've attached two files: a two-page brief that draws the whole pipeline with the phase plan, and an n8n workflow of its first stage (the key claim, the duplicate stop, the review route and the dead-letter route).

1) Relevant work
- n8n + CRM: I run and maintain a production n8n setup of about 20 live workflows for a heating-installation company, wired to their CRM's API. It covers new-lead intake from web forms, tasks triggered by status changes, timed follow-ups, an error-handler workflow and a watchdog that sends a health digest.
- Python/FastAPI + AI: a FastAPI service a finance team uses for its monthly close. An LLM reads every receipt, the service proposes the matching charge and a category, and a person confirms; nothing the model guessed reaches the accounting system until they do. It also folds duplicates, so one charge printed on two statements counts once.

2) Duplicate records: every incoming lead gets an idempotency key (the source plus that source's own lead ID, falling back to normalized email), written to a Postgres table with a unique constraint before anything else runs. A webhook that fires twice, or an execution that gets replayed, hits the constraint and stops. CRM writes are upserts keyed on email, never blind creates. On GoHighLevel the upsert follows the location's duplicate-contact setting, so that setting gets checked before go-live.

3) Failed executions: API calls retry with backoff on rate limits and server errors only; a bad payload fails at once instead of looping. Whatever still fails lands in a dead-letter table with its payload and error, the n8n error workflow alerts you, and a replay endpoint re-runs it. Because every step is keyed, a replay can't create a second record or a second task.

4) Incorrect AI actions: OpenAI or Claude returns structured JSON (score, reasons, summary) that's checked against a schema. Output that fails the schema or lands below a confidence threshold goes to a person, not the CRM. The AI can write a short allowlist of fields and never touches stage, owner or deletes. Outreach drafts wait in an approval queue: someone approves the exact text, an edit afterwards voids the approval, and each message is sent once, by its ID. I've built that approval-and-send gate for a B2B outreach tool and tested it end to end. LangGraph earns its place where a flow branches on the model's answer; qualification, summary and draft usually fit one validated call, which is easier to debug.

5) Price: fixed-price in three phases, about $3,500 in total:
- Phase 1, $1,000: lead intake, dedupe, CRM sync, retries, logging and alerts
- Phase 2, $1,500: AI qualification, lead summaries, outreach drafts and the approval queue
- Phase 3, $1,000: follow-up scheduling, tasks, notifications, documentation and Docker deployment
If we move forward, we start with Phase 1; it stands on its own, so you can judge the work before deciding on the rest.

Which CRM are you on today, HubSpot or GoHighLevel, and roughly how many new leads come in each week?

Matthias
