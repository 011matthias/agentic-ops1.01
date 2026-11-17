# Mini-Checkpoint: Ad Game Viability Ranker

**Date:** 2026-10-29
**Status:** Ranker published and seeded; no code in this repo changed
**Type:** mini

---

## Summary
Answered a Zombie Cafe copyright question, brainstormed app ideas, then built a published scoring page that ranks ad-funded game ideas on anchored criteria with knock-out gates.

## What Was Done
- Zombie Cafe: no special restriction found and no takedown reports. Copyright persists after a shutdown; mechanics are free to copy, code, art, audio, name and logo are not. The rights holder was not verified.
- Built the Ad Game Viability Ranker artifact (https://claude.ai/artifact/DDU6f8tdGSSHfgvGbRGuLW, private): 14 criteria in 5 weighted pillars (Build 15, Retention 20, Monetization 25, Distribution 25, Audience 15), 4 gates (own IP, policy-safe ads, distinct game, children handled), verdict tiers at 75/60/45, and daily players needed for a revenue target.
- Seeded 7 ideas in the artifact db (collection `ideas`) and read them back. Scores: idle factory 77.5, German daily puzzle 77.3, physics stacker 74.2, zombie diner 73.0, AI suspect game 68.6, .io arena 66.8, reskin ad farm blocked on the distinct-game gate (48.3).

## What Did NOT Work (and why)
- **Saving db documents to disk with `out_dir`:** refused by the file-edit safety rules on that location; read with `list` instead.
- **`query` with `where gates.g_spam == false`:** rejected `invalid_argument`; the nested-field filter shape is not accepted, so the check used `list`.
- **Viewing the rendered page:** never done. Only the inline script's syntax and the db contents were checked.

## Current Status
Artifact live at version 1, private to the owner. Benchmarks behind the anchors are vendor-blog figures and directional only. Verdict thresholds are a judgment call. All seed scores are desk estimates by Claude.

## Next Steps
1. Open the artifact once in a browser and check the layout and that saving an idea works.
2. Replace desk scores with prototype retention data before moving any idea up a verdict.
3. Verify who holds the Zombie Cafe rights before any rebuild.

## Files to Read First
- C:\Users\NEUMA_~1\AppData\Local\Temp\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\320a7a5e-15fd-4838-a322-7a176b598027\scratchpad\ad-game-ranker.html (temp scratchpad, may be cleaned; the published artifact is the durable copy)
