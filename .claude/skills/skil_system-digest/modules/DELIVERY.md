# Delivery

Instructions for delivering digests via email using Resend API.

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `RESEND_API_KEY` | Yes | Resend API key ([resend.com/api-keys](https://resend.com/api-keys)) |
| `DIGEST_FROM_EMAIL` | Yes | Verified sender address in Resend |
| `DIGEST_TO_EMAIL` | No | Default recipient (overridable via `--email` flag) |

## Setup (One-Time)

1. Create a free Resend account at [resend.com](https://resend.com)
2. Verify a sending domain or use `onboarding@resend.dev` for testing
3. Create an API key
4. Add to `.env` in workspace root:
   ```
   RESEND_API_KEY=re_xxxxxxxxxxxxx
   DIGEST_FROM_EMAIL=digests@yourdomain.com
   DIGEST_TO_EMAIL=you@yourdomain.com
   ```

## Email Delivery Process

### Step 1: Save digest to temp file

Save the generated markdown digest to a temporary file:
```bash
# The digest content should be saved to a temp file
# e.g., docs/digests/.tmp-digest.md
```

### Step 2: Send via script

```bash
uv run scripts/send-digest-email.py \
  --to "recipient@example.com" \
  --subject "Agentic Ops Digest — {MODE} — {DATE}" \
  --body-file docs/digests/.tmp-digest.md
```

### Step 3: Clean up temp file

```bash
rm docs/digests/.tmp-digest.md
```

## Subject Line Format

| Mode | Subject |
|------|---------|
| Overview | `Agentic Ops — System Overview — {DATE}` |
| Changes | `Agentic Ops — Changes Since {SINCE_DATE} — {DATE}` |
| Client | `{CLIENT_NAME} — Automation Report — {DATE}` |

## Fallback

If `RESEND_API_KEY` is not set:
1. Print a warning: "Email delivery requires RESEND_API_KEY. Saving to file instead."
2. Save to `docs/digests/YYYY-MM-DD-{mode}.md`
3. Print the file path for manual sharing

## HTML Styling

The email script converts markdown to HTML and wraps it in a clean, responsive template:
- Max width: 700px, centered
- Font: system font stack (sans-serif)
- Tables: bordered, zebra-striped
- Code blocks: light gray background
- Headers: dark color, clear hierarchy
- Status badges: colored inline spans

See `scripts/send-digest-email.py` for the full HTML template.
