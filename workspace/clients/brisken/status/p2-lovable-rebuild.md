---
project: brisken
workstream: p2-lovable-rebuild
group: lead-generation
spec: p2
state: active
updated: 2026-09-10
general_ref: status/p2-lead-gen-general.md
---

# Brisken / Lovable rebuild (p2)

Dirk's greenlight 2026-09-10: **the expense reconciliation tool stays
unchanged**; everything else we built is replicated, and improved where
sensible, in Lovable, inside **Brisken's existing Lovable workspace** (the one
already serving brisklet, mbc-faq, tac-2025, token, articles, insights and
sap-ai-brief, all on `185.158.133.1`).

Method agreed with the owner: this list on record, then one site at a time,
together, Lead Desk last. Each item gets a **1:1 replication pass** that is
checkable against the live page, then a separate **improvement pass**, so a
difference from live is never ambiguous between a fix and a loss.

Ownership, identity model and the Fly-org move for the expense engine are a
separate track: `../OWNERSHIP-HANDOFF.md` sections 4 to 12. Nothing in this
workstream touches the expense tool.

## Elements

| # | Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|---|
| 0 | Workspace access + mechanic probes | blocked | Two mechanics the whole plan leans on are UNVERIFIED on Lovable hosting: a route-loader `301`, and files pushed into `public/` through GitHub sync being served at root paths. A throwaway project answers both in minutes. | Dirk names the Brisken Lovable account and invites matthias.silva@; then build the throwaway project and probe | Dirk's invite | Probe: `curl -I` a legacy-style path expecting 301 + Location; push a PDF into `public/`, publish, expect 200 with the pushed byte size |
| 1 | onepilot.brisken.com | not started | Smallest surface and the safest place to learn the editor: one page, no forms, no legacy redirects pointing at it. Live title "OnePilot, the orbit of your working day", 144,532 b. | Rebuild by prompt once 0 is green | 0 | Source `website/onepilot.html`, served at the apex of that host by a vercel.json host rewrite. Carry `og-op.png` |
| 2 | resources.brisken.com | not started | Mostly files: 10 generated deck pages + 10 deck PDFs + the Rome one-pager, all carried verbatim into `public/` at their current root paths. Proves the file carry-over at scale. Live index 117,452 b. | Rebuild after 1 | 0, 1 | `resources-site/`. Index links 8 of the 10 pages; `smart-trading-deck.html` is linked by nothing (confirm orphan before dropping it). Regenerating a deck page needs the generator, which is developer work |
| 3 | brisken.com + www | not started | The largest: `/` and `/treasury` both served from `treasury.html` (455,061 b), `/demo` (15,102 b) posting to `api/book-demo.js` -> Neon, the five legal PDFs at `/docs/`, and 18 legacy Wix/WordPress redirects. | Rebuild after 2 | 0, 2; which mailbox receives demo requests | See "brisken.com detail" below |
| 4 | rome2026.brisken.com | not started | Retirement, not a rebuild (decided 2026-09-09). GoDaddy subdomain forward, 301 to brisken.com, then delete Vercel project `brisken-rome-hub`. Recommended as Dirk's first hands-on GoDaddy edit, because it also proves he holds that login (UNVERIFIED whose account owns it). | Hand Dirk the GoDaddy steps whenever he is at that screen | none (independent of 0 to 3) | `rome-hub/README.md`; canonical `index.html` was never deployed, live serves the 2026-07-13 copy |
| 5 | Lead Desk | not started | Lovable Cloud rebuild scoped to what Brisken uses: contacts, mailbox truth-scan history, review queue, unmatched queue, user admin. Campaign sender stays dormant until Dirk arms it. **Access-checked 2026-09-10: nothing new needs granting.** The Entra app credential we already hold works from Cloud, the Application Access Policy already covers both mailboxes, the data is on our Fly volume. | Scope after 3 ships | 0, 3; Cloud enabled on the workspace | ~11,400 lines of Python, 19 SQLite tables. Sign-in becomes Lovable Cloud's own email login, so no Graph dependency for login. IT is needed only later, and for the same things the Fly route needs: `tools@` as sender, matthias.silva@ converted to shared, Graph secret reissued |
| 6 | Close-out | not started | Seven-day soak per cutover, then delete the Vercel projects and Neon (after a CSV export of the leads table), and write the editor runbook lines. | After each cutover soaks | 1 to 5 | `brisken-onepilot-proto` is NOT destroyed here: the expense-engine track needs it as the `fly apps move` rehearsal |

## brisken.com detail (element 3)

Everything below has to keep resolving, byte-identical where marked.

- **Pages.** `/` and `/treasury` (same document today), `/onepilot`, `/demo`.
  `cleanUrls: true`, `trailingSlash: false`.
- **Legal PDFs, byte-identical at the same paths** (`website/docs/`, the
  footer publishes them and GDPR Art. 13/14 makes them load-bearing):
  `brisken-cloud-services-gtc.pdf` 522,555 b;
  `brisken-privacy-statement-2021.pdf` 203,542 b;
  `brisken-privacy-statement-2018.pdf` 589,769 b;
  `brisken-market-data-hub-terms.pdf` 215,208 b;
  `brisken-accenture-case-study.pdf` 2,297,668 b (largest asset in the estate,
  inside Lovable's 10 MB per-file limit).
- **18 redirects**, all `permanent: true`. Five point at those PDFs from
  Wix/WordPress-era paths (`/_files/ugd/...`, `/assets/pdfs/...`,
  `/wp-content/uploads/2019/10/...`); thirteen are legacy page paths
  (`/sap-consulting`, `/one-pilot-apps` and its six app sub-paths,
  `/rapsody`, `/digital-workforce`, `/ai-powered-automation`,
  `/contact-page`). Nobody holds Search Console, so the traffic through them
  is unmeasured rather than zero.
- **The demo form.** Replaced by Lovable's built-in transactional email to a
  Brisken mailbox (no Cloud needed on a TanStack Start project; the sender
  domain is `notify.brisken.com` by NS delegation at GoDaddy). Neon's leads
  table is exported to CSV before anything is deleted. Today's only other
  egress is an ntfy push to a subscriber no document names.
- **Also carry:** `og-tc.png`, `og-op.png`, `favicon.png`, `robots.txt`,
  `sitemap.xml`.

## The per-site loop

1. **Brief.** Live page inventory (routes, sections, forms, links, assets),
   the canon sentences from `context/tc-story-canon.md`, the design tokens
   from the `brisken-design` skill, the asset list to push. Source of truth is
   the **live** page, not the repo: they have drifted before (the Rome hub is
   the standing example).
2. **Build** in Brisken's workspace, by prompt.
3. **Parity pass.** Nav parity, copy parity against the canon, zero
   em-dashes, legal and PDF links resolve, mobile, Lighthouse.
4. **Improvement pass.** Named improvements only, so each is deliberate.
5. **Sign-off.** Dirk on a shared preview link; pin that version.
6. **Cutover.** GoDaddy A `185.158.133.1` + the `_lovable` TXT for the
   hostname; verify from a private window; Vercel stays alive as the
   rollback.
7. **Update this file.**

## Definition of done, per site

Hostname resolves to `185.158.133.1`; every route from the live inventory
returns 200; every PDF's `Content-Length` equals the local file's size; every
redirect that targets this host returns 301 to its mapped path; a form
submission from a private window lands in the chosen mailbox; and a Brisken
person makes one inline text edit and publishes it without help.

## Pointers

- `../OWNERSHIP-HANDOFF.md` sections 4 to 12: ownership, identity, sequence
- `../TARGET-ARCHITECTURE.md` 1b: why Lovable, and the three superseded calls
- `../rome-hub/README.md`: the Rome retire-vs-deploy decision
- `context/tc-story-canon.md`: the approved TreasuryCentral story
- Memory `reference_lovable_merge_is_not_live`: merge is not publish
