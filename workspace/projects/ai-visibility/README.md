# AI-visibility probe

Dogfood + seed for a possible client service: measure and improve whether AI
engines (ChatGPT, Perplexity, Gemini, AI Overviews) can find and cite a site.

Two halves, independent:

- **On-site audit** grades the AEO surface (AI-crawler access, sitemap,
  `llms.txt`, structured data, freshness, machine-readable pricing). No keys
  needed. This is the gradeable deliverable.
- **Citation probe** asks the target's buyer-intent queries against AI engines
  and records whether the domain appears in the cited sources. Needs an engine
  key. This is the proof-of-presence loop and the monthly metric.

## Run

```bash
# audit only (no key needed)
uv run workspace/projects/ai-visibility/ai_visibility_probe.py \
  --target workspace/projects/ai-visibility/targets/unpauseai.yaml --audit-only

# full run, writes dated md + json into reports/
uv run workspace/projects/ai-visibility/ai_visibility_probe.py \
  --target workspace/projects/ai-visibility/targets/unpauseai.yaml \
  --out workspace/projects/ai-visibility/reports/ --date 2026-06-07
```

Run from the repo root (the enforcement hooks resolve relative paths there;
do not `cd` into this folder).

## Keys

- `PERPLEXITY_API_KEY` — primary engine, returns source URLs natively (~$5
  covers months of monthly probes).
- `AI_VISIBILITY_OPENAI_KEY` — adds the ChatGPT-search engine. Dedicated key
  only; never reuse a client's key.

## Files

- `ai_visibility_probe.py` — the probe (audit + citation).
- `targets/<brand>.yaml` — domain, brand, engines, buyer-intent queries.
- `reports/baseline-<brand>-<date>.json` — machine snapshot, diff month over
  month.
- `reports/baseline-<brand>-<date>.md` — human report. Re-running the same
  date overwrites it, so enrich a copy if you add interpretation.

## Adding a target

Copy `targets/unpauseai.yaml`, change `domain`/`brand`, and write the 8 to 12
queries a real buyer would type. Derive them from the client's positioning,
not from keywords.
