# Brisken Lead Desk

Single-source-of-truth lead-generation tracker. Contacts plus an append-only
outreach event log in one SQLite database; pipeline stage and every status
bucket are derived from the log, never hand-stamped. Replaces the scattered
Rome master-sheet copies, send-log CSVs, booth notes, and Planner board.

See `BLUEPRINT.md` for the architecture and the Phase 2 cloud-capture plan.

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
  LEAD_DESK_INGEST_SECRET=...
```

Load the database by running `lead-desk-migrate` against a `--data` dir, then
copying `lead-desk.sqlite` onto the `/data` volume (or run the importer inside
the machine). The gate is active whenever `LEAD_DESK_ACCESS_CODES` is set.

## Console scripts

- `lead-desk-web` : the gated FastAPI app.
- `lead-desk-migrate` : one-time, idempotent import of the master sheet.
- `lead-desk-export` : regenerate the master sheet (csv/xlsx) from the db.
