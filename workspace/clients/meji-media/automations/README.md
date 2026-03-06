# meji-media — Make.com Scenarios

Scenarios are imported via blueprint JSON files. See `context/setup-guide.md` for import instructions.
Blueprints are stored in `blueprints/` for version control.

## Scenarios

| Scenario ID | Name | Trigger | Blueprint |
|-------------|------|---------|-----------|
| A1 | Enquiry Follow-Up Sequence | Webhook (form submission) | `blueprints/a1-enquiry-follow-up-sequence.json` |
| A2 | Reply Detection & Stop | Gmail Watch (every 5 min) | `blueprints/a2-reply-detection-stop.json` |
| A3 | Scheduled Follow-Up Steps | Schedule (every 15 min) | `blueprints/a3-scheduled-follow-up-steps.json` |

## Connections Required

| Service | Connection Type | Status |
|---------|----------------|--------|
| Gmail | OAuth2 | Configure on import |
| Google Sheets | OAuth2 | Configure on import |
| Custom Webhook | Built-in (auto-generated) | Created on import |

## Supporting Docs

- `context/google-sheets-schema.md` — Tracking table column definitions
- `context/email-templates.md` — All email templates with Make.com field mappings
- `context/setup-guide.md` — Step-by-step import and testing guide

## Blueprint Exports

Blueprints are stored in `blueprints/` for version control.
After any scenario change in Make.com, export the blueprint and update the file here.
