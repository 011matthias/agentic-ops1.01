# VolaByg Lead Flow and Deliverability Audit Checklist

Prepared by UnpauseAI. This is the actual set of checks we run in Phase 1,
against your live setup, before any rebuild. Each item is read-only; nothing
that is sending today gets changed during the audit.

Last updated: 2026-06-10

---

## 1. Authentication (rejected vs filtered)

- [ ] SPF record on the sending domain: present, valid, single record, correct includes
- [ ] SPF policy: does `-all` (hard fail) match the actual sending sources
- [ ] DKIM: is a key published for the sending selector, and is mail signed with it
- [ ] DKIM alignment: does the signing domain match the from-domain
- [ ] DMARC record: present, policy level (none / quarantine / reject), reporting addresses
- [ ] DMARC alignment: do SPF and DKIM align with the visible from-address
- [ ] From-domain vs sending infrastructure: does the tool sending mail authenticate as that domain
- [ ] Reverse DNS (PTR) on the sending IP, if a dedicated IP is in use
- [ ] BIMI and MTA-STS: present or not (not required, noted for completeness)

Known finding for volabyg.dk (public DNS, 2026-06-09): SPF `include:spf.simply.com -all`,
DMARC `p=reject`, MX `mx.simply.com`. Public lookups did not resolve a DKIM key on the
common selectors, which does not prove one is absent. This is a strict, correctly
configured policy: only Simply.com is approved to send as `@volabyg.dk`. If a tool other
than Simply.com sends as `@volabyg.dk` without aligned authentication, that mail is
rejected; if it sends through the Simply.com mailbox, or from its own separate domains,
the reject policy does not apply. The reported symptom is spam, not bounced mail, so the
likelier driver is warm leads filtered through cold-outreach infrastructure rather than
outright rejection. The audit confirms which.

## 2. Sending infrastructure and reputation

- [ ] Which domains and mailboxes are actually sending the sequence
- [ ] Cold-outreach rotation vs a single authenticated identity for warm leads
- [ ] Mailbox warmup state and per-mailbox daily volume
- [ ] Blacklist status of the sending domain and IPs (Spamhaus, Barracuda, others)
- [ ] Domain age and prior sending history
- [ ] Bounce rate, spam-complaint rate, and unsubscribe handling
- [ ] List hygiene: invalid, role, and duplicate addresses entering the sequence
- [ ] Content checks: spammy phrasing, link domains, image-to-text ratio, unsubscribe presence

## 3. The automation flow (Facebook to Sheet to sequence)

- [ ] Facebook Lead Ads: which form fields are captured and how leads are delivered
- [ ] The transfer mechanism from Lead Ads to the Google Sheet (native, Zapier, Make, other)
- [ ] Error handling on the transfer: retries, timeouts, and whether failures are surfaced
- [ ] Sheet structure: column mapping the sequence depends on, and how fragile it is
- [ ] Trigger from Sheet to Instantly: real-time vs scheduled, and any gaps between runs
- [ ] Dedupe logic: does it drop legitimate separate leads
- [ ] Sequence configuration: steps, timing (day 0, day 2, day 4-5), and stop conditions
- [ ] Reply detection: does a reply actually stop the remaining emails
- [ ] Logging: is there any record of a lead moving through each stage

## 4. Transfer integrity (the count mismatch)

- [ ] Facebook reported lead count for a fixed recent window
- [ ] Rows in the Google Sheet for the same window
- [ ] Contacts that entered the Instantly sequence for the same window
- [ ] Reconcile the three numbers and locate where the drop happens
- [ ] Separate the loss into transfer loss (never reached the sequence) and deliverability loss (sent, never delivered)
- [ ] Spot-check a sample of leads end to end, from ad submission to email outcome

---

## Deliverable

A written findings report: what is wrong in each dimension, how much engagement
loss is deliverability versus transfer (with real numbers from your data), and a
concrete, scoped recommendation for the rebuild.

Contact: admin@unpauseai.com
