---
description: Deploy project automation (Trigger.dev or Railway)
argument-hint: <project-name>
---

# Deploy Automation

Deploy a project's automation to production. Delegates to the `agnt_deployer` agent.

## Prerequisites
- Project name from arguments. If missing, ask.
- Resolve project directory — check `workspace/clients/{project}/` first, then `workspace/projects/{project}/`.
- The agnt_deployer agent auto-detects the orchestrator from `infrastructure.yaml` and the automations folder structure.

## Execute

Invoke the `agnt_deployer` agent with the project name.

The agnt_deployer handles:
1. Pre-deployment test gate (blocks on failure)
2. Git commit and push to main
3. Subtree push to client repo
4. Deploy via `npx trigger.dev deploy` (Trigger.dev) or `railway up` (FastAPI)
5. Post-deploy health verification

## Verification gate (mandatory before claiming success)

After the agnt_deployer reports deploy completion AND the orchestrator is web-surface (Vercel / Railway HTTP / static HTML), spawn `agnt_done-verifier` BEFORE declaring "deployed" to the user. Closes the verification-theater class (register #12, #91, #107).

Skip the verifier ONLY for:
- Trigger.dev task deploys (no public URL; the testing-agent's task-run check is the verifier)
- Make.com / n8n scenario "deploys" (scenarios MCP gives canonical state)
- Code-only commits with no deployed surface

Use the Task tool:

```text
Launch agent: agnt_done-verifier

Prompt:
Verify the deploy just completed by agnt_deployer.

Inputs:
- urls: {list of deployed URLs from the deploy step output}
- expected_content: {list of strings that prove the new build is live — e.g.,
  the new feature's heading, the new commit SHA prefix from a hidden meta tag,
  or a string from the changeset}
- files: {list of source HTML file absolute paths if the deploy is a static
  HTML deliverable — these get validate-html.py'd}
- state_checks: {optional list of {cmd, expect} pairs, e.g.,
  {cmd: "gh pr view {N} --json state -q .state", expect: "MERGED"}}
- context: "{project} deploy after commit {sha}"

Return either VERIFIED or the failure-list shape.
```

Apply the verifier's output:
- `VERIFIED`: include its summary line in the final user-facing message ("Verified: {URL} — 1 page 200, all expected_content present.").
- Failure list: do NOT declare deploy complete. Surface the failure list verbatim to the user and stop. Diagnosing + fixing is a separate action.
