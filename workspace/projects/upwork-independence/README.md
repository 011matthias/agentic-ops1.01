# Upwork Independence (uwi)

Execution program for replacing Upwork as the lead source with owned client
acquisition. The STRATEGY layer is settled by five optimize runs
(`docs/optimize/upwork-independence-*/SUMMARY.md`); this directory is the
execution layer beneath it.

## Map

| Path | What |
|---|---|
| `gtm-plan.json` | Optimize asset — GTM decisions (capacity 32, alloc 0.24/0.76, prices). Do not move: RUN.md asset globs reference this exact path. |
| `acquisition-portfolio.json` | Optimize asset — channel effort mix (cold-email 0.378, LinkedIn 0.289, referral 0.154, AEO 0.178, demo-first 0.0). |
| `pricing-tiers.json` | Optimize asset — canonical offer values (good 650/0.20, better 1850/0.55, best 6300/1.00). Public surfaces derive from this file, never duplicate it. |
| `infrastructure.yaml` | Accounts roster: what the program owns, absent -> live as purchased. |
| `context/` | Tracked program context (ICP). `context/.env` (gitignored) holds owned credentials as they exist. |
| `status/` | One status-of-elements file per workstream (u1-u7) + `uwi-general.md` group reference. Start there. |

## Conventions

- Scope code `uwi`; branch family `uwi/{description}` (documented, not
  hook-enforced — no branch gate covers workspace/projects).
- Status files follow `rule_project_status`; `tools/project_status.py --client
  upwork-independence --check` covers this directory.
- The operative acquisition plan is the leadgen-portfolio mix. The gtm-v2-confirm
  referral finding is a model artifact (no referral-supply constraint), not a
  channel pivot; see `status/u4-referral-partnership.md`.
- Cold email is UK/US only (UWG §7). Structural in the optimize guards; carried
  into every list-sourcing step.
