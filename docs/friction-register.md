# Friction Register

| Date | Client | Type | Description | Resolved? |
|------|--------|------|-------------|-----------|
| 2026-03-03 | kunde-inc | platform-limitation | n8n Cloud Code node sandbox blocks `this.helpers.httpRequestWithAuthentication()` — must use HTTP Request nodes with predefinedCredentialType instead | Yes |
| 2026-03-04 | kunde-inc | platform-limitation | n8n Cloud Code node sandbox blocks `fetch()` AND `$helpers.httpRequest()` — only HTTP Request nodes work for external API calls | Yes |
| 2026-03-04 | kunde-inc | syntax-bug | Python f-string collapses `{{...}}` to `{...}` — n8n expressions require double braces; use string concatenation to build expression strings | Yes |
| 2026-03-04 | kunde-inc | platform-limitation | n8n Split In Batches typeVersion 1 never fires done output[1]; need typeVersion 3 for the done signal | Yes |
| 2026-03-04 | kunde-inc | platform-gotcha | Google Sheets API 429 when Clear Sheet node receives N items (1 per campaign) instead of 1 — must place Clear before Read Campaigns in flow | Yes |
