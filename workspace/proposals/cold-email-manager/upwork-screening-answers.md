# Upwork Screening Answers: Cold Email Manager (p029)

Plain text, paste verbatim. Field 1 is the cover letter (see cover-letter.md).

## Field 2: Video or Loom explaining why you would be a good fit

Recorded a 2-minute walkthrough of how I'd run your list-to-launch cycle, including the field-by-field mapping check before anything goes live, and the sequence-timing bug I caught in live campaigns by reading the API spec instead of trusting the UI: {LOOM-LINK}

The full one-page plan (price, process, proof) is at https://unpauseai.com/clients/cold-email-manager/

## Field 3: Describe your recent experience with similar projects

Most relevant: I run cold email ops end to end for a UK client right now. The current state, all live today: a 945-lead warm re-engagement campaign with a personalized first touch per lead, plus a 452-lead cold campaign split by role into decision-makers (239) and organisers (213), sending from 3 warmed mailboxes on a shared daily cap. The lists were built in Apollo with role, company size, and geography filters plus a roughly 1,200-domain exclusion list from their CRM, sample-validated on 200 contacts before the full pull, and every address verified (deliverable / catch-all / invalid) before import.

The detail that matches your "double-check before marking complete" line: I caught a sequence-timing bug across all 3 live campaigns (follow-ups firing 20 minutes apart instead of days apart) by reading the Instantly API spec directly, fixed it, and verified the next send window was clean. I also diagnosed a dead sending domain via DNS that had silently disabled 3 mailboxes, retired them, and stood up a fresh domain with authentication records and warm-up from zero.

Alongside that, I build automation systems for a logistics client: an AI-assisted reconciliation platform with around 170 automated tests, plus a 5-stage lead pipeline design (LinkedIn ingest, website forms, follow-up, reply monitoring) in n8n. Documentation and per-task completion notes are how I work by default, not an extra.
