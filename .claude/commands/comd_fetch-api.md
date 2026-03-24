---
description: Fetch API docs from URL and generate Python client boilerplate
argument-hint: <api-name> <docs-url>
---

# Fetch API & Generate Client

Fetch API documentation and generate a typed Python client. Delegates to the `agnt_api-fetcher` agent.

## Arguments
- API name (e.g., `smartlead`, `fortnox`)
- Documentation URL

If arguments are missing, ask the user.

## Execute

Invoke the `agnt_api-fetcher` agent which:
1. Fetches API docs using the `skil_api-docs-fetcher` skill
2. Generates a typed Python client using the `skil_api-boilerplate` skill
3. Outputs to `workspace/templates/api-clients/{api-name}/`
