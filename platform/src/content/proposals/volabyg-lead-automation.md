---
id: p026
slug: volabyg-lead-automation
prospect: VolaByg
contact: Ibrahim
source: upwork
source_url: ""
project_title: "Lead Flow & Email Deliverability Automation"
status: draft
track: 2
created: "2026-06-09"
sent: null
value_estimate: "EUR 850 audit + EUR 1,900 rebuild + EUR 600/mo"
timeline: "2-3 weeks to verified rebuild, then ongoing"
tags: [instantly, deliverability, lead-automation, facebook-lead-ads, google-sheets, spf-dkim-dmarc, email]
access_code: "volabyg-2026"
deliverables:
  letter: true
  video: true
  site: true
research:
  prospect_company: "Volabyg Aps"
  prospect_industry: "Construction and renovation SMB (painting, floor sanding, facade and tile work; Danish, serving private clients, businesses, and housing associations)"
  prospect_location: "Denmark (CET); domain volabyg.dk confirmed"
  prospect_contact: "Ibrahim"
  prospect_systems:
    - "Meta (Facebook Lead Ads)"
    - "Google Sheets"
    - "Instantly (3-step email sequence)"
  prospect_pain_points:
    - "A significant share of the sequence emails land in spam"
    - "Facebook lead count does not match email replies and engagement: a silent drop somewhere in the Lead Ads to Sheet to Instantly handoff"
    - "No confidence whether the failure is authentication, domain reputation, tool mismatch, or a data-transfer gap"
    - "Wants one owner for the whole flow, A to Z, not a hand-off between specialists"
  job_language_echoes:
    - "complete lead automation solution"
    - "from A to Z"
    - "take ownership of the complete lead flow and email automation process"
    - "landing in the recipient's spam folder"
    - "the number of leads generated in Facebook does not match the number of replies"
    - "full audit of the current setup"
    - "Ongoing management of the entire process"
  location_advantage: "EU residency, CET timezone (same as Denmark), GDPR by design. Facebook Lead Ads collect consumer personal data under GDPR; an EU-based owner lowers compliance risk versus a non-EU contractor."
  relevant_proof_points:
    - "Instantly run in production for a live client (sequencing, mailbox health, SPF/DKIM/DMARC, reply detection)"
    - "Lead pipelines: form/webhook to Sheet to sequenced email with reply detection that stops the sequence"
    - "Deliverability diagnosis: SPF/DKIM/DMARC alignment, domain reputation, sending infrastructure"
  budget_gap: "No budget posted. Ibrahim asked for a pricing structure directly, so the proposal leads with a transparent audit-first structure rather than defending a number."
  profile_cherry_picks:
    - "Instantly in production (not just listed) is what makes the tool-mismatch diagnosis earned rather than generic"
    - "Reply detection that actually stops the sequence maps to the count-mismatch concern"
    - "Build and test with real data: the lead-transfer drop is an untested edge case"
    - "EU/CET/GDPR fit for a Danish company capturing consumer data"
---

## What We Understood

Facebook Lead Ads bring leads in, a Google Sheet holds them, and Instantly fires a three-step sequence (day 0, day 2, day 4-5). Two separate things are wrong: a large share of those emails land in spam, and the number of leads in Facebook does not match the replies you actually see. They have different causes and need different fixes; what they share is the pipeline and, ideally, one owner. Some mail is being filtered on the way to the inbox, and separately some leads never make it through the handoff.

The spam side is mostly a tool fit. Instantly is built for cold outreach: rotating mailboxes, warmup, aggressive sending. Your leads are warm, they opted in through a form. Warm leads sent through cold infrastructure is one of the most common reasons good mail lands in spam, even when authentication passes.

## Our Proposed Solution

One owner for the whole flow, in three phases.

First, an audit of every link in the chain: SPF, DKIM, DMARC and domain alignment; sending infrastructure and reputation; and the Lead Ads to Sheet to Instantly handoff, tested with real leads to find where the count drops.

Then the rebuild: warm leads moved onto an authenticated, transactional sending path instead of cold-outreach rotation, with the three-step sequence preserved, reply detection that stops the sequence, and a logged handoff so no lead is silently dropped.

Then ongoing management: deliverability monitoring, sequence iteration, and a single place to see lead counts end to end.

## How It Works

Lead Ads webhook to a validation and dedupe step to the Sheet (or CRM), then an authenticated sequenced send, with reply detection stopping the sequence and every stage logged. Each handoff is verified, so the Facebook count and the delivered count finally agree.

## Timeline & Milestones

Week 1: audit and findings. Weeks 2-3: rebuild, migrate the sequence, and verify with real leads. Then ongoing management on a monthly basis.

## Investment

Audit-first and project-fixed. Phase 1 audit EUR 850. Phase 2 rebuild and verified handoff EUR 1,900. Phase 3 ongoing management EUR 600 per month. The audit alone is a low-commitment way to see the findings before deciding on the rebuild.

## About UnpauseAI

EU-based automation consultancy in Karlsruhe, CET timezone, GDPR by design. We run Instantly and lead-automation pipelines in production for live clients, including the exact pattern here: form to sheet to authenticated sequenced send with reply detection. We build and test with real data and hand off with documentation and monitoring, so you own the system.
