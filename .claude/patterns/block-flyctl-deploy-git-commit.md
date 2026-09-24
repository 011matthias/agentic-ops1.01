---
name: block-flyctl-deploy-git-commit
enabled: true
event: bash
action: block
message: This deploy would stamp /healthz with an EMPTY commit. The Dockerfile ARG is GIT_COMMIT, not EXPENSE_RECON_COMMIT: flyctl deploy "$M" --config "$M/fly.toml" -a brisken-expense-recon --remote-only --build-arg GIT_COMMIT="$(git -C "$M" rev-parse HEAD)", with $M a C:/ path when MSYS_NO_PATHCONV=1. Full command + clean-tree guard: docs/operating.md 'Deploy'.
source: 2026-09-21 slow-path; 2026-09-24 x2 (as a warn it arrived with the deploy's result, after the unstamped deploy had shipped); block + narrowed to brisken-expense-recon 2026-09-24
created: 2026-09-21
pattern: 'flyctl\s+deploy(?=[^\n]*brisken-expense-recon)(?![^\n]*GIT_COMMIT)'
---
Explain what went wrong, when, and what to do instead.
