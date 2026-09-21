---
name: warn-flyctl-deploy-git-commit
enabled: true
event: bash
action: warn
message: This deploy will stamp /healthz with an EMPTY commit. The Dockerfile ARG is GIT_COMMIT, not EXPENSE_RECON_COMMIT: flyctl deploy . -a brisken-expense-recon --build-arg GIT_COMMIT=$(git rev-parse HEAD). Full command + clean-tree guard: docs/operating.md 'Deploy'.
source: 2026-09-21 slow-path
created: 2026-09-21
pattern: 'flyctl\s+deploy(?!.*GIT_COMMIT)'
---
Explain what went wrong, when, and what to do instead.
