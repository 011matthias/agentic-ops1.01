# Brisken OnePilot prototype host

Gated host + feedback collector for the OnePilot marketing-site prototype
(`../deliverables/brisken-onepilot-website-prototype.html`). Tiny FastAPI app:
serves the prototype behind a shared access code and appends reviewer feedback
to JSONL on a Fly volume. Internal pre-Dirk review only; nothing published to
brisken.com.

## Routes
- `GET /` prototype HTML (gated)
- `GET/POST /login`, `GET /logout` access-code gate
- `POST /feedback` `{name, role, section, comment, path, title}` -> JSONL on `/data`
- `GET /feedback-log` reviewer feedback table (gated)
- `GET /feedback.jsonl` raw log (gated)
- `GET /healthz` liveness (open)

## Env
- `BRISKEN_SITE_ACCESS_CODE` shared code; gate is on only when set
- `BRISKEN_SITE_AUTH_SECRET` cookie HMAC key (set in prod)
- `BRISKEN_SITE_DATA` feedback dir (default `./data`; `/data` on Fly)
- `BRISKEN_SITE_HTML` prototype path (default `./site/index.html`)
- `BRISKEN_SITE_INSECURE_COOKIE=1` drop cookie Secure flag for local http only

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
