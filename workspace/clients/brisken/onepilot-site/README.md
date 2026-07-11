# Brisken OnePilot prototype host

Gated host + feedback collector for the OnePilot marketing-site prototype
(`../deliverables/lead-generation/onepilot/brisken-onepilot-website-prototype.html`). Tiny FastAPI app:
serves the prototype behind a shared access code and appends reviewer feedback
to JSONL on a Fly volume. Internal pre-Dirk review only; nothing published to
brisken.com.

## Routes
- `GET /` prototype HTML (gated)
- `GET/POST /login`, `GET /logout` access-code gate
- `POST /feedback` `{name, role, section, comment, path, title}` -> JSONL on `/data`
- `GET /feedback-log` reviewer feedback table (gated)
- `GET /feedback.jsonl` raw log (gated)
- `GET/POST /inquiry` public contact form (open, honeypot-filtered) ->
  `inquiries.jsonl` on `/data` + notification email to Dirk when the
  Resend env vars are set (reply-to = submitter)
- `POST /api/book-demo` (open) JSON endpoint the platform page's contact
  modal posts to; same store + notification pipeline as `/inquiry`
- `GET /inquiry-log` inquiries table (gated)
- `GET /inquiries.xlsx` the submissions log as a downloadable Excel
  workbook (gated)
- `GET /healthz` liveness (open)

## Env
- `BRISKEN_SITE_ACCESS_CODE` shared code; gate is on only when set
- `BRISKEN_SITE_AUTH_SECRET` cookie HMAC key (set in prod)
- `BRISKEN_SITE_DATA` feedback dir (default `./data`; `/data` on Fly)
- `BRISKEN_SITE_HTML` prototype path (default `./site/index.html`)
- `BRISKEN_SITE_INSECURE_COOKIE=1` drop cookie Secure flag for local http only
- `BRISKEN_INQUIRY_RESEND_KEY` Resend API key for inquiry notifications
  (unset: inquiries stored on the volume only, no email)
- `BRISKEN_INQUIRY_FROM` verified Resend sender (required for sending)
- `BRISKEN_INQUIRY_TO` recipient (default `dirk.neumann@brisken.com`)

## Run locally
```
uv run sync-site.py                       # copy canonical HTML into ./site
uv run --with 'fastapi' --with 'uvicorn[standard]' --with python-multipart \
  uvicorn app:app --port 8080             # open (no gate) since no access code set
```

## Deploy (Fly)
```
uv run sync-site.py                       # refresh ./site/index.html first
flyctl deploy ./ --remote-only --ha=false
```
App `brisken-onepilot-proto`, region `fra`, volume `onepilot_data` at `/data`,
scale-to-zero. Secrets (`flyctl secrets set ...`): `BRISKEN_SITE_ACCESS_CODE`,
`BRISKEN_SITE_AUTH_SECRET`. `./site/index.html` and `./data` are gitignored.

## Standalone OnePilot platform app (second Fly app)

The same app code also backs a separate Fly app, `brisken-onepilot`
(`brisken-onepilot.fly.dev`), for reviewing the OnePilot platform page on its
own host (intended to become `onepilot.brisken.com`). It is fully isolated from
the proto host: its own app, its own `onepilot_data` volume, its own
`BRISKEN_SITE_AUTH_SECRET`. The only behavioural difference is
`BRISKEN_SITE_ROOT=platform` (set in `fly.onepilot.toml` `[env]`), which makes
`/` serve `brisken-onepilot-platform.html`; the TreasuryCentral prototype stays
reachable at `/brisken-onepilot-website-prototype.html` so the cross-links work.

```
uv run sync-site.py
flyctl deploy ./ --config fly.onepilot.toml --remote-only --ha=false
```
