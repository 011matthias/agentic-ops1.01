# Brisken Lead Desk

Single-source-of-truth lead-generation tracker AND campaign engine. Contacts
plus an append-only outreach event log in one SQLite database; pipeline
stage, status buckets, and cadence progress are derived from the log, never
hand-stamped. Replaces the scattered Rome master-sheet copies, send-log
CSVs, booth notes, and Planner board.

Campaign engine (iteration 3): upload a list -> rules classify each lead
into a warmness degree -> each degree runs a predetermined sequence
(N steps, day offsets) -> one approval freezes copy + list -> the local
Windows worker auto-sends (cold: from matthias.silva@ CC Dirk; warm: staged
as drafts in Dirk's mailbox) and polls both inboxes -> follow-up stops on
reply/bounce/suppress -> every send BCCs the Zoho CRM dropbox.

See `BLUEPRINT.md` for the architecture and `worker/README.md` for the
Windows worker runbook + TEST-campaign gate.

## Local run

```bash
# from this directory
uv run --extra web --extra dev pytest              # tests

# import the Rome master sheet into a local (gitignored) db
uv run --extra web lead-desk-migrate --data ../../../../../.scratch/lead-desk-data

# serve the UI (loopback, no gate)
uv run --extra web lead-desk-web --data ../../../../../.scratch/lead-desk-data
```

The database holds lead PII; keep it under `.scratch/` locally and on the Fly
volume in production. It is never committed.

## Deploy (Fly)

```bash
fly deploy
fly secrets set \
  LEAD_DESK_AUTH_SECRET=... \
  LEAD_DESK_ACCESS_CODES="matthias:...,dirk:...,chris:..." \
  LEAD_DESK_INGEST_SECRET=... \
  LEAD_DESK_WORKER_SECRET=...
```

Load the database by running `lead-desk-migrate` against a `--data` dir, then
copying `lead-desk.sqlite` onto the `/data` volume (or run the importer inside
the machine). The gate is active whenever `LEAD_DESK_ACCESS_CODES` is set.
The campaign-engine tables self-create additively on first open; run
`lead-desk-adopt` once to enroll the legacy Rome cohort (history untouched,
can never auto-send).

## Console scripts

- `lead-desk-web` : the gated FastAPI app.
- `lead-desk-migrate` : one-time, idempotent import of the master sheet.
- `lead-desk-export` : regenerate the master sheet (csv/xlsx) from the db.
- `lead-desk-adopt` : enroll a legacy contact cohort into the campaign model.
- `lead-desk-reconcile` : repair outbox lock-table / event-log drift.
- `lead-desk-capture` : Phase 2 Graph capture (gated on Brisken IT creds).
- `lead-desk-worker` : local Windows send/capture worker (see `worker/`).
