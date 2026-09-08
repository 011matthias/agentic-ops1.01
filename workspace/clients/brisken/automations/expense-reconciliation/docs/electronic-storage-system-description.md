---
project: brisken
workstream: p1-expense-reconciliation
kind: compliance-description
backlog_item: 48
state: draft-pending-owner-and-cpa-review
created: 2026-09-08
updated: 2026-09-08
revision: 2
---

# Description of the electronic storage system

**Prepared to satisfy Rev. Proc. 97-22, section 4.01(5).** That paragraph
requires the taxpayer to "maintain, and make available to the Service upon
request, complete descriptions of (a) the electronic storage system,
including all procedures relating to its use; and (b) the indexing system".
This document is intended to be that description.

> **DRAFT. Not yet a statement to anyone.** This has not been reviewed by
> the owner or by a US CPA, and it must not be handed to a tax authority
> until it has been. It is written to be handed over, which is why section
> 12 discloses where the system does not meet the revenue procedure rather
> than omitting it. An overstatement in a document like this is a false
> statement to the Service, so the drafting rule throughout has been:
> describe what the code does, not what it was designed to do.
>
> **Revision 2.** Revision 1 was checked line by line against the code by
> eight independent reviewers instructed to refute it. They produced 97
> challenges, of which 53 were confirmed and 7 rejected as misreadings.
> Five were flat false statements, including the two load-bearing integrity
> claims. Every confirmed correction is applied below. The scale of that
> correction is itself a fact about this document's reliability and is
> recorded rather than hidden.
>
> Every factual statement below was read from the deployed code on
> 2026-09-08 at commit `d4aa02fe`, or from the live hosting platform on the
> same day. Where something could not be verified it says so. Three
> statements about the revenue procedure's own text (4.02(2), the section 7
> deletion limb, and section 3.03 on third parties) need a CPA's
> confirmation, because they cannot be established from the code.

Companion document: `us-substantiation-criteria.md`, which assesses the
tool's OUTPUT against the substantiation rules. This one describes the
SYSTEM that stores the records.

---

## 1. Summary for the reader in a hurry

Brisken operates an expense-substantiation system that receives receipts,
reads them automatically, matches them against corporate-card statements,
and produces expense reports and reconciliation reports with the receipt
images appended as evidence.

The records are stored as **ordinary files** on a single encrypted volume in
Frankfurt, alongside SQLite databases holding the metadata. Bytes arriving
on the receiving paths are stored without transformation, nothing is held in
a proprietary format, and the stored records can be read with a file
browser, a spreadsheet application and any SQLite client without this
application.

Three areas fail outright and are stated up front rather than buried: there
is **no stored digest** for the main record store, so alteration of a stored
file cannot be detected (4.01(2)(b)); there is **no inspection and
quality-assurance program** (4.01(2)(c)); and there is **no retention
control** over the main record store, which a single authenticated request
can delete in full (4.01(8)). They are not the only failures. A further set
of defects, listed in section 12, falls under 4.01(1), 4.01(2)(a), 4.01(3),
4.01(4), 4.01(9), 4.02 and 4.01(7). Because **section 7 of the revenue
procedure permits destruction only after testing establishes reproduction in
compliance with all the provisions of this revenue procedure**, every open
item in section 12 stands between this system and that permission, not only
the three above. **Originals may not yet be destroyed.** Nothing in this
document should be read as asserting that a paragraph absent from section 12
is fully satisfied.

| Rev. Proc. 97-22 | Requirement | Status | Section |
|---|---|---|---|
| 4.01(1) | Accurate and complete transfer; index, store, preserve, retrieve, reproduce | Partly met. Transfer is byte-for-byte on the receiving paths but one path generates the record rather than receiving it (4.4) and several refusals leave no record (4.5); storage is verbatim; **preserve is not met** (one volume, no replication, no application-level backup, no retention rule over the run store); retrieval and reproduction are partly met | 4, 4.4, 4.5, 5, 5.4, 7, 9.2 |
| 4.01(2)(a) | Controls for integrity, accuracy, reliability | Partly met | 8.1 |
| 4.01(2)(b) | Controls to prevent and detect unauthorised creation of, addition to, alteration of, deletion of, or **deterioration of** stored records | **Not met** on all five limbs | 4.1, 5.4, 8.2 |
| 4.01(2)(c) | Inspection and quality assurance program | **Not met** | 9.1 |
| 4.01(2)(d), 4.02(1) | Retrieval system including an indexing system, functionally comparable to a reasonable hardcopy filing system | Partly met. Identifiers are unique within a period only and not always that (6.2); there is no retrieval by date, vendor, amount, currency or card even within a period; there is no cross-period retrieval; and the reproduction strips the index key from the printed page for the sequence-numbered records (6.5) | 6 |
| 4.02(2) | Reasonable controls protecting the indexing system against unauthorised creation, addition, alteration, deletion or deterioration of entries | **Not met.** The index is the metadata database; a single authenticated request deletes a period's index entries outright, no action is attributable to a person, and no audit record is kept | 6, 8.2 |
| 4.01(2)(e), 4.01(3) | Legible and readable hardcopies | Partly met | 7.2 |
| 4.01(4) | Audit trail between the books and the source documents | Partly met | 10 |
| 4.01(5) | Descriptions of the system and the indexing system | This document | all |
| 4.01(6) | Retrieve and reproduce at examination; provide the resources | Partly met | 7, 11 |
| 4.01(7) | No agreement restricting Service access | **Not assessed** | 11.2 |
| 4.01(8) | Retain so long as material | **Not met** for the run store | 9.2 |
| 4.01(9) | More than one system is permitted, but each must meet the requirements | **Not met.** More than one electronic storage system is in use. The run store fails 4.01(2)(b), 4.01(2)(c) and 4.01(8); because each system must comply, the failure of one is a failure of this paragraph | 5.3, 8.2, 9 |
| 4.01(10) | Reasonable compression or formatting permitted, but only so long as the requirements of the revenue procedure are satisfied | **Condition not satisfied.** The image conversion is of a kind this paragraph contemplates, but its proviso fails while 4.01(2)(b), 4.01(2)(c) and 4.01(8) are not met; the conversion also drops recorded image orientation and transparency, which is a legibility defect under 4.01(3) rather than permitted formatting | 7.2 |
| section 7 | Conditions for destroying originals | **Not met** | 13 |

---

## 2. The taxpayer, the records, and the period

**Taxpayer.** The Brisken entities whose corporate-card expenses this system
documents. At the time of writing, which entities file a US federal return
is being confirmed; this document should name them before it is handed over.

**Records covered.** Business-expense substantiation records: receipts,
invoices and similar documentary evidence for corporate-card purchases; the
corporate-card statements those purchases appear on; and the expense reports
and reconciliation reports produced from them.

**Records NOT covered.** This system is not a general ledger and files no
returns. The books of account are kept in Zoho Books, a separate system. The
relationship between the two is described in section 10.

**Period.** The system has been in production use during 2026. Records from
earlier periods, where they exist, were kept by the predecessor process
(per-card spreadsheets maintained by hand) and are not in this system.

---

## 3. Overview of the system

A hosted web application, written in Python, running as a single container
on Fly.io (app `brisken-expense-recon`, region `fra`, Frankfurt). It exposes
a JSON API and file downloads. The browser interface the operator uses is a
separate single-page application hosted by a third party; it holds no
records of its own and reads everything from this backend.

The application scales to zero when idle and starts on a request.

**Storage.** One persistent volume, `recon_data`, 1 GB, mounted at `/data`,
in Frankfurt, **encrypted at rest** (verified against the hosting platform
on 2026-09-08). Scheduled platform snapshots are enabled with a **5-day**
retention window. That is disaster recovery, not record retention; see
section 9.2.

**The operator.** One named person performs the month-end reconciliation.
Access is by an access code, which is a control weakness described in
section 8.2.

---

## 4. How records enter the system (4.01(1), accurate and complete transfer)

There are six entrances. Three are the principal ones described below: by
e-mail, by upload, and by statement. Three more exist and are described in
4.7: the reconciliation intake, the per-charge manual attach, and the bulk
folder attach. A seventh path creates a record rather than receiving one:
the body rendering described in 4.4. The last three use identifier schemes
and directories different from those described in 5.1 and 6.1.

**4.1 By e-mail.** The application runs its own mail listener. The MX record
for `expenses.brisken.com` points at it, and anyone may send a receipt to
that domain; there is deliberately no sender allowlist, because suppliers
and staff both send receipts. The listener accepts plain, unauthenticated
SMTP on port 25 and offers neither transport encryption nor authentication,
so a message and its attachments travel to it in cleartext across the public
internet. Nothing in the system detects a message that was altered,
substituted or injected in transit, and because no digest of the received
bytes is retained as an integrity control (8.1), there is no later means of
establishing that what is on the volume is what the sender transmitted.
Adding transport security to the listener is on the remediation list.

Boundaries that do apply: the envelope recipient must be inside the intake
domain, so the listener is not an open relay; at most 10 recipients and 25
MB per message; at most 30 attachments per message; and per-sender and
global daily budgets. Two filters also decide which attachments are kept as
records. Only PDF, PNG, JPEG and WebP attachments are taken; an attachment
in any other format, including TIFF, HEIC, GIF, HTML and spreadsheet
formats, is never written out as a separate file and never enters a period,
though its bytes remain inside the archived raw message. And any PNG, JPEG
or WebP attachment smaller than 4,096 bytes is discarded as presumed
signature or tracking imagery, which will also discard a small genuine
receipt image. Both cases are noted in the archive's own metadata but not in
the refusal list.

**Custody is taken before the message is accepted.** On receipt, the
application writes to the volume (a) the complete raw message as delivered,
(b) each accepted attachment as a separate file, byte for byte, and (c) a
metadata descriptor recording the sender address, the subject, the message
id, the arrival time, the connecting peer address, and, for recipients at
the intake domain only, a reduced form of the local part with the domain
removed and any plus-addressing collapsed to its tag. No recipient address
is stored verbatim, and recipients outside the intake domain are not
recorded in the descriptor at all; they remain readable only in the archived
raw message. Only after those writes does the application return the SMTP
"250 accepted" code. If the archive write fails it returns a
temporary-failure code instead, so the sending mail server retries rather
than the message being accepted and lost. An entry is appended to an
acceptance log.

**4.2 By upload.** An operator may drop receipt files on a page in the
application, or add them to a named month. Accepted types are PDF, PNG, JPEG
and WebP, at most 15 MB per file and 500 files per call. ZIP archives are
expanded member by member when files are added to a named month or to an
existing period. They are refused on the receipts drop page, where each file
must route to its own month, and on the mail path.

**4.3 By statement.** The corporate-card statement for a period is uploaded
as CSV, XLSX, XLSM or PDF. A month may take several statements, one per card
and often a partial followed by the full cycle.

**4.4 What happens to the bytes.** On the upload, statement and
mail-attachment paths the file is written to the volume exactly as received:
no transcoding, resizing or recompression is applied to it. Three
qualifications must be stated.

First, where a message carries its receipt in the body rather than as an
attachment, the application generates a record of its own: it extracts the
body text, discards anything past 15,000 characters, renders the remainder
as a paginated image PDF capped at four pages, writes that PDF into the
message's archive and takes it into the period as the record. This runs on
an operator click, and automatically on arrival for senders on the
known-sender list. The record taken into the period in that case is an
application-produced rendering, not bytes any sender transmitted; the raw
message it was derived from is retained unchanged beside it.

Second, while an upload is still queued, an operator may replace its
statement or receipts file; the replacement is written and the superseded
file is deleted from the volume, with no copy and no record of the
replacement.

Third, a receipt attached by hand to a single charge is stored under a name
derived from that charge, so re-attaching a file with the same name for the
same charge overwrites the stored bytes in place, again with no prior
version retained.

Where a PDF must be converted to an image so the reading software can see
it, that conversion happens in memory and is never written to disk.

**4.5 What is refused, and whether refusals leave a record.** Refusals are
recorded in two different places, and not everything refused reaches either.
A message turned away at the mail boundary, for a recipient outside the
domain, too many recipients, low disk, an intake-busy condition or an
exhausted daily budget, produces a row in the refusal list carrying the
time, stage, reason, sender, recipient and connecting address. That row does
not name a file. A file rejected on an upload path, for an unsupported type,
an empty file, a file over 15 MB or the 500-file cap, produces an issue
naming the file, held on the period's own record rather than in the refusal
list; if every file in one upload is rejected the period is deleted and only
the first issue is returned to the operator, so no record of that upload
survives. A mail attachment rejected inside an accepted message is noted in
the archive's own metadata, not in the refusal list.

Five rejections produce no entry anywhere: a file whose bytes duplicate
another file in the same upload; a file whose bytes are already held by that
period; every file after the first once the per-call cap is reached, because
the loop stops at the cap after naming one file; a zip member whose name
begins with a dot; and an empty file dropped on the receipts page. The
refusal list is also not a permanent record: it is capped at 512 KB and
rewritten to keep only the newest 200 rows, and a failed write to it is
deliberately ignored so that it can never block a refusal.

Refusals produced by the underlying SMTP library are not recorded at all. A
message over the 25 MB limit, a message declaring a size above the limit
before it is sent, and a message containing an over-long line are each
answered with an error code and discarded, with no archive and no ledger
row. An error while reading settings or while parsing the message produces
the same kind of unrecorded refusal, so a message the parser cannot read is
turned away silently. Within a message that is accepted, an attachment
carrying no filename and an unrecognised content type, and an attachment
that decodes to zero bytes, are dropped without an entry; in those two cases
alone the bytes survive inside the archived raw message.

**4.6 Contemporaneity.** Arrival time is recorded for mailed records, in the
archive directory name and in the metadata descriptor. The archive directory
is named from a one-second timestamp and a short digest of the message bytes
and is reused rather than refused if it already exists, so a byte-identical
duplicate delivered inside the same second overwrites the earlier archive's
metadata, resetting its recorded arrival time and status with no record of
the overwrite. Note also that the archive holds the message body as
delivered and does not add a system-generated transport header, so the
arrival evidence is in application-written metadata rather than in the
message itself.

**4.7 The three further entrances.** The reconciliation intake takes a card
statement together with a Zoho Expense report and stores both under
`/data/intakes/<intake id>/`. The per-charge manual attach stores one file
under a period's `manual-receipts/` directory against a single charge. The
bulk folder attach against an existing period stores files under
`folder-receipts/`, named by a digest of their own bytes.

---

## 5. How records are stored (4.01(1))

**5.1 The record store.** Each accounting period (a month, or a business
trip) is a "run". Its records live in that period's own directory on the
volume, in one of three subdirectories:

```
/data/runs/<run id>/receipts/<NNNN>__<original filename>
/data/runs/<run id>/manual-receipts/<charge key>__<original filename>
/data/runs/<run id>/folder-receipts/<digest of the file's bytes>__<original filename>
```

The first holds receipts taken in by upload or by mail; the four-digit
prefix is a sequence number assigned on upload and is what makes the name
unique inside that period. The second holds a receipt attached by hand to a
particular charge, keyed on that charge. The third holds bulk-loaded
receipts, named by a truncated digest of their own bytes. In all three the
trailing part is the file's own name, reduced to a conservative character
set. Files are stored unencrypted at the application layer; the volume
beneath them is encrypted by the platform.

Also inside a run's directory: the uploaded statement, and the generated
spreadsheets and CSV exports.

**5.2 The metadata stores.** Three SQLite databases sit on the volume.
`/data/recon-web.sqlite` holds twelve tables: the per-period record, the
reviewer's decisions, the override rows, the upload queue and the settings.
`/data/learning.sqlite` holds five tables of cross-period memory derived
from the reviewer's confirmations, including confirmed vendor-to-category
mappings, vendor aliases and per-vendor field corrections, each row naming
the period it was learned from. `/data/extraction-cache.sqlite` holds one
table mapping a digest of a document's content to the raw reply the reading
model returned for it, with the file name and a timestamp; an unchanged
document is re-answered from it instead of being read again. Neither of the
last two carries a retention rule, and neither is purged when a period is
deleted.

The per-period record, including every receipt's extracted date, total,
currency, vendor and line items, is held as a JSON document on the period's
row in the first of them. The paying card is not stored on the receipt. What
is stored is the payment-method text the receipt or report carried; the
card, the legal entity and the person are resolved from it at read time
against the card registry held in the period's own configuration, subject to
any reviewer override. A card shown on a report is therefore a derived value
dependent on configuration that can change, not a stored attribute of the
record. Monetary amounts are stored as strings so no decimal precision is
lost in the store.

Reviewer corrections are held as overlay rows in the database and are
applied when the review screen renders and when a report or export is
produced. They are not kept separate permanently. Whenever a period is
re-matched, which happens when a statement is attached and again on every
later receipt arrival, card assignment or master-data refresh, the corrected
values are written back into the period's stored JSON record in place of the
extracted values, and an expense the reviewer marked deleted is dropped from
that record at the same point. Since 2026-08-25 the pre-correction
extraction is copied once into a parallel `extracted_receipts` key before
the first such write, so for a period first re-matched after that date the
extracted value is still recoverable. For any period whose statement was
attached before that date there is no such copy: the extracted values were
overwritten, they are not recoverable, and no migration was performed. There
is no history of intermediate corrections in either case; only the baseline,
where it exists, and the current value.

**5.3 There is more than one storage system (4.01(9)).** This matters
because their rules differ:

- **The mail archive** (`/data/inbound/`) holds every message accepted
  within the retention floor, with its attachments and metadata. It has a
  retention floor and an automatic age-based deletion sweep (section 9.2).
- **The run store** (`/data/runs/`) holds the records that were taken into a
  period. It has no retention rule and can be deleted in full (section 9.2).
- **The upload queue** (`/data/intakes/`) holds the original statement and
  receipts file of every document set an operator queued, kept as delivered.
  Running the pipeline copies the bytes into the run store and leaves this
  copy in place; nothing deletes it and it has no retention rule. Replacing
  a file on a queued upload deletes the file it replaces, and no record of
  that deletion is kept.
- **The three databases** described in 5.2, of which two hold
  record-derived data with no retention rule and survive the deletion of the
  period they came from.

Because 4.01(9) requires each electronic storage system to meet the
requirements of the revenue procedure, the failure of any one of these is a
failure of that paragraph.

A fourth, content-addressed store exists in the codebase but is reachable
only from a command-line tool and holds nothing in production. It is
mentioned only because an earlier internal assessment credited the deployed
system with its properties in error.

**5.4 Durability.** One volume, one region, one machine. There is no
replication, no second region, and no application-level backup or restore
procedure. The only automated durability is the platform's scheduled
snapshots, with a 5-day retention window.

---

## 6. The indexing system (4.01(2)(d) and 4.02)

**6.1 The identifier.** Every stored document has an identifier. For records
taken in by upload or by mail, the identifier **is** the stored filename,
i.e. the sequence number plus the original name. For two other paths the
identifier is a prefixed string: a receipt attached by hand to a particular
charge, or a bulk-loaded receipt identified by a truncated digest of its own
bytes.

**6.2 Scope of uniqueness.** The identifier is unique **within one period**
and is not globally unique: every period restarts the sequence at 0000.
Re-uploading the same physical receipt into a second period produces a
second stored copy, and its identifier is not guaranteed to differ. On the
sequence-numbered paths a receipt occupying the same slot under the same
original name in two periods carries the identical identifier string in
both. On the bulk path the identifier is a digest of the file's own bytes,
so the second copy always carries the same identifier as the first. Only the
period id distinguishes them. Where two different receipts collide on one
identifier across periods, the system responds by excluding one of them from
cross-period matching rather than by renaming either.

The address that resolves a stored document is normally the pair (period id,
document id). One case breaks that pair and must be stated: when a month's
charge dates overlap a business trip, the month's record may reference
receipts that physically live in the trip period's directory. For such a
document the pair (referencing period, document id) resolves to nothing on
disk; the home period is recorded in the referencing period's
`receipt_sources` map and has to be read first. The report builders do not
follow that map, so a charge settled by a borrowed receipt is listed in the
reconciliation report without the receipt's pages behind it.

**6.3 What can be looked up.** The available lookups are: period plus
document identifier; the mail archive directory, which links back to the
period and the documents it produced; the attachment fingerprints recorded
in the mail metadata; and the period label, normally a month.

Two qualifications. For a receipt attached by hand to a charge the
identifier does not resolve deterministically: the file is located by
pattern-matching the charge key and taking the first match in sort order, so
re-attaching to the same charge under a different filename leaves both files
on disk and may serve the older one, while re-attaching under the same
filename overwrites the earlier file's bytes with no record of the
replacement. And a receipt this period borrowed from a trip does not resolve
under this period's identifier at all (6.2).

**6.4 Limits, disclosed.** There is no index on vendor, date, amount,
currency or card, and no cross-period search is offered to a reader of the
system. The engine does run cross-period searches of its own, which are not
reachable as lookups: it scans trips for a date range overlapping a month's
charges in order to draw on their receipts, it reads a claims table to see
whether another period has already settled a receipt, and it scans the mail
archive's recorded content fingerprints to identify a duplicate submission.
None of these answers a question about a stored document by vendor, date or
amount.

A request of the form "produce every receipt you hold for a given year"
cannot be answered directly by the system today; it is answerable by
inspecting the volume, since the records are ordinary files, but not by a
query.

**6.5 A defect in the reproduction, disclosed.** For receipts taken in by
upload or by mail, the filename printed above each receipt in a report has
the four-digit sequence prefix removed, and that prefix is the part that
makes the identifier unique inside the period, so the printed page does not
carry the full index key for those records. Receipts attached by hand or
bulk-loaded keep their key in the printed name and are unaffected. The page
is still distinguishable, because the caption above it carries a unique
expense number plus the date, amount and entity, but the stored identifier
itself is not reproduced. Correcting this is on the remediation list in
section 12.

---

## 7. Retrieval and reproduction (4.01(1), 4.01(3), 4.01(6))

**7.1 Retrieval.** A stored document is retrieved either individually or as
part of a report. Individual retrieval returns the original stored bytes
unchanged only for receipts held as their own file, which is every receipt
that arrived by mail, by upload or by hand-attachment to a charge. For a
receipt that exists only as a page inside an uploaded expense-report PDF,
individual retrieval returns a PNG image rendered from the single page the
receipt was mapped to: not the stored bytes, and not the whole document. The
stored PDF is unaffected but is retrievable only by inspecting the volume.

The report-building code calls no external service: it reads only the stored
metadata and the files on the volume, and no third party is consulted while
a report is produced. Reaching that code is a separate matter, and the
reproduction path as a whole is not offline-capable. The backend serves no
interface of its own, so in practice a report is produced through the
third-party-hosted browser interface described in 11.2, over the network,
from an application the hosting platform starts on demand and runs at zero
instances when idle. If the hosting platform or the network is unavailable,
no report can be produced by the system; records could then be recovered
only by inspecting the volume directly (11.1).

**7.2 Reproduction into a report, stated precisely.** Both the expense
report and the reconciliation report append the receipts themselves as
evidence pages behind a caption naming the expense or charge they prove.

A **PDF receipt's pages are copied into the report**, every page and in
order, with their visible content intact. They are copied page by page into
a new document, so anything the source PDF held at document level rather
than on a page is not carried across: an embedded XML invoice payload of the
kind a ZUGFeRD or Factur-X electronic invoice uses, interactive form-field
data, optional-content layers, document metadata and accessibility tagging.
Where a receipt is an electronic invoice whose XML payload is the
authoritative machine-readable record, the report page is not a complete
reproduction of it and the stored original must be produced instead. The
stored original is unaffected and remains retrievable in full.

An **image receipt is re-rendered**: converted to RGB, fitted inside a 1120
by 1634 pixel area of an A4 page (about 150 dots per inch), and written into
the report as a JPEG at the imaging library's default quality. It is never
enlarged, but any image larger than that area is downsampled: a 300 dpi A4
scan is reduced to roughly 136 effective dpi and then lossily re-compressed,
so fine print that is legible in the stored original may not be legible on
the report page. This is a formatting conversion of the kind 4.01(10)
contemplates, but it means the page in the report is neither a bit-exact
copy of the stored file nor guaranteed to be as legible as it. **The stored
original is unaffected and remains retrievable in full.**

Three known defects in this path are disclosed: **image rotation recorded in
a photograph's metadata is not applied**, so a receipt photographed with a
sideways phone appears rotated in the report while appearing upright in the
application; **transparency is discarded rather than composited onto the
white page**, so a receipt saved with a transparent background can reproduce
as a dark or blank page while displaying correctly in the application; and
**the reports carry no page numbers**, so a printed set cannot be shown on
its face to be complete or in order.

**7.3 Missing or unreadable documents, and where that safeguard fails.** An
expense with no document prints a caption saying so. A file that exists but
cannot be turned into pages normally prints a caption naming the file and
saying it could not be rendered. Three limits are disclosed here.

The renderability test opens a PDF's index only. A PDF whose contents cannot
be read until later, such as a password-protected receipt or one whose page
tree is damaged, passes that test and then fails while the report is being
assembled. When that happens the request fails and no report is produced at
all for the whole period: no caption, no partial report and no message
naming the offending file. A single such receipt makes a period
unreproducible until the file is removed by hand.

A document the period's record references whose file is no longer on the
volume prints the same caption as an expense that never had one, so a lost
stored record cannot be told apart from an absent one on the face of the
report. With no stored digest for the run store (8.1), the system cannot
detect that loss by any other means either.

The listing's Receipt column reads "attached" whenever the file was read off
disk, which is decided before its renderability is known, so the listing can
overstate how many expenses have a usable receipt page behind them. The
caption pages are authoritative.

**7.4 What the reports do not cover.** The reports are not an inventory of
everything stored. Classes of stored document that appear in no report:
documents the reading step set aside as not being receipts; mail that never
reached a period; the corporate-card statement files themselves, which are
stored in the period's directory but are only ever reproduced as parsed
charge rows, never as the uploaded document; files left in a period's
receipts directory by an ingest job that was interrupted, which no period
record references and which therefore carry no identifier at all; a receipt
physically living in another period that this period borrowed (6.2); and a
receipt whose stored file has gone missing, which is reported as an expense
that never had a document (7.3). All of these except the last remain on the
volume and are retrievable by inspecting it; the interrupted-job files are
reachable only that way, because nothing indexes them.

Expenses the reviewer marked deleted are a separate case. They are excluded
from the expense report. Their receipts still appear as evidence in the
reconciliation report for the same period until that period is next
re-matched, because the reconciliation report is built from the stored
period record rather than from the reviewer's overlay. At the next re-match
the deletion is written into the stored record and the expense disappears
from both. The two reports can therefore disagree about which documents a
period contains, and the stored file remains on the volume in either case.

**7.5 Producing hardcopies.** Reports download as PDFs and print directly. A
limit is disclosed: a report is assembled entirely in the memory of a single
512 MB machine, holding every receipt in the period plus the whole assembled
document at once, and an individual receipt may be up to 15 MB. A
sufficiently large period may therefore not be reproducible at all: the
request fails with no report, no partial output and no message naming a
cause. No maximum period size has been measured and no streaming or chunked
reproduction path exists. For records not in a report, see 7.4 and 6.4: they
are ordinary files and can be printed, but the system offers no bulk export.

---

## 8. Controls (4.01(2)(a) and (b))

**8.1 Integrity, accuracy and reliability, honestly assessed.**

What is in place: uploaded and mailed bytes are stored exactly as received,
without transformation; mail custody is taken before acceptance; monetary
values are stored as strings, so no decimal precision is lost in the store;
uploaded filenames are sanitised and archive expansion is protected against
path traversal.

Four qualifications belong with that list. Stored files are not immutable:
replacing a wrongly attached file on a queued upload deletes the file it
replaces, and re-attaching a receipt to the same charge under the same name
overwrites it, in both cases with no prior version and no record kept. The
generated reports do not preserve the stored precision: they convert amounts
to binary floating point when writing the spreadsheet and when summing
period and section totals for the PDF, and a row whose amount cannot be
parsed is omitted from the PDF total without notice. Reviewer corrections
are not held separately once a period is re-matched (5.2). And only some
concurrent writes to a period are serialised: one in-process lock covers the
mail-intake, add-receipts and delete-period paths, while the manual receipt
attach and the bulk receipt-folder ingest rewrite the whole period record
with no lock, so a write on either can be lost under a concurrent one.
Because the lock is in-process it holds only while the application runs as a
single machine, which the single attached volume currently enforces.

What is **not** in place, and must be stated:

- **No integrity digest for the run store.** For receipts held in a period's
  `receipts` directory, a digest is computed on upload, used to detect
  duplicates within that upload, and then discarded; nothing records what
  those files' contents were, so nothing can verify that such a stored file
  is the file that arrived. Partial content records do exist elsewhere and
  are stated for completeness. Each mailed attachment's truncated digest is
  kept in its archive's metadata. Bulk-loaded receipts are named and
  identified by a truncated digest of their own bytes. And the extraction
  cache keys each stored reading on a full digest of the document. None of
  these was designed as an integrity control: two of the three are truncated
  to 32 and 64 bits, the receipts loaded in a period's initial upload carry
  no digest at all, and no process in the system ever recomputes or checks
  any of them. There is therefore no integrity scheme, which is why
  4.01(2)(b) is reported as not met.
- **No verification pass.** Nothing re-reads the stored records to check
  them against anything.
- **Accuracy in a second sense.** The amounts, dates and vendors on the
  reports are read from the receipt images automatically by a language
  model. The model returns a confidence score with every reading. It is not
  carried onto the receipt record, is not shown on any report, and gates
  nothing, but it is retained: the model's raw reply, including the
  confidence value and every field it read, is stored in the extraction
  cache described in 5.2, keyed on a digest of the document's bytes. That
  cache has no retention rule and is not purged when a period is deleted, so
  a confidence score outlives the record it describes. The reports do not
  disclose that their values were machine-extracted, and no measured error
  rate exists. The receipt image is appended beside every figure, so a
  reader can check any value against its source, which is the mitigation;
  but the disclosure should be on the report and is on the remediation list.

**8.2 Prevention and detection of unauthorised change or deletion: not met.**

- **Access is by an access code, and there is one permission level.** The
  application supports either a single shared code or several named
  per-person codes; they differ only in that a named code can be revoked
  individually and identifies the session it opened. Every configured code
  grants the same and only role, so any person holding any code has the full
  interface, including deletion. As deployed for this period: *[state the
  configured value before this document is handed over]*. Where named codes
  are used, the session's identity is never written into any stored record,
  so it does not survive as attribution.
- **No action is attributable to a person.** Where the system records an
  "operator" against a change, it records a value from the server's own
  environment, which is the same for everyone.
- **There is no audit log** of who did what in the hosted application. An
  audit-logging component exists in the codebase with the right fields but
  is used only by a command-line tool and is not active in the hosted
  system.
- **Deletion is barely recorded and is not complete.** Deleting a period
  removes its database rows (the period, its decisions, receipt claims,
  category and field overrides, expense edits and jobs) and its on-disk
  directory. The only trace of the deletion is on the mail side: each
  archived message that belonged to the period is stamped with the time the
  period was deleted. Nothing records that a deletion happened for a period
  whose records arrived by upload, nothing records who performed it, and no
  retention, period-close or legal-hold check stands in front of it. The
  only guard is that the caller must type the period's label back, which any
  authenticated user can do.

  Two stores survive the deletion by design: the learned merchant, category
  and rate memory, and the extraction cache, which retains the model's full
  reading of each receipt (vendor, date, total, currency, tax, card and line
  items) keyed on a digest of the receipt's bytes, with no retention rule
  and no purge. The mail archive copy of anything that arrived by mail also
  survives, subject to the age-based retention sweep in 9.2, but its link to
  the records it produced does not: the deletion clears the archive's list
  of the documents it created, so the message remains and its association
  with the accounting records taken from it is erased.
- **No history of prior values.** A corrected value replaces the previous
  correction; only the extraction-time baseline, where one exists, and the
  current value survive.

These five together are why 4.01(2)(b) is reported as not met, and they are
items 1 and 2 on the remediation list.

---

## 9. Inspection, quality assurance, and retention

**9.1 Quality assurance (4.01(2)(c)): not met.** There is no periodic
inspection of the stored records, no sampling, no comparison of a reproduced
record against its original, and no record of any such check ever having
been performed.

The software itself is well tested, with an automated suite of roughly 1,400
tests run on every change, and a command exists that re-runs a period's
matching and fails if the reconciliation invariant breaks. Neither is a
check of the stored records, and neither is offered here as satisfying
4.01(2)(c).

**9.2 Retention (4.01(8)): split, and not met for the main store.**

- **The mail archive has a retention floor**, configurable, defaulting to
  ten years on the basis of the German Abgabenordnung, a foreign statute
  rather than a US one. A sweep runs once each time the application process
  starts, and deletes archives whose arrival stamp is older than the floor.
  It is not scheduled: how often it runs depends on how often the hosting
  platform starts the machine, which the system neither controls nor records
  and which has not been measured. It is also best-effort; a failure earlier
  in the same startup block silently skips it.

  The sweep keeps no record of what it destroyed: it writes a single count
  to the application log, which is not retained, and no manifest,
  per-archive entry or database row survives it. It deletes an archive
  whether or not its contents were ever taken into a period, applies no
  examination, litigation-hold or period-close check, and swallows a partial
  failure, so an archive can be left incomplete with nothing detecting it.
  The floor itself can be lowered to one year by any holder of the access
  code in a single settings request, which is not audited, and the next
  process start acts on the new value.

  The default floor is longer than the ordinary three, six and seven year
  periods, but Publication 583 sets no limit at all where a return was not
  filed or was false, and 4.01(8) requires retention for as long as the
  contents may become material. A fixed ten-year cutoff does not meet that
  standard in those cases.
- **The run store has no retention rule at all.** A single authenticated
  request deletes a period in full. A record can also be destroyed short of
  that: while an upload is still queued, re-posting a statement or receipts
  file permanently deletes the file it replaces, with no version kept and no
  record of the replacement; and re-attaching a receipt to the same charge
  under the same filename overwrites the stored bytes in place.
- **Beneath both**, the platform's scheduled snapshots retain for five days.

Nothing in the system currently guarantees that a record will still exist
for as long as its contents may become material.

---

## 10. Audit trail to the books (4.01(4))

The books of account are in Zoho Books, outside this system. This system
produces an export intended to carry the link, with a reference for each
expense and a column for the receipt's location. The export is not retained:
each download rebuilds the file from the period's current decisions and
edits and overwrites the previous copy, so the system holds no record of
which version of the export was imported into the books, or when. After any
later edit, the file that was actually posted cannot be reproduced.

Stated accurately: the system produces two exports. In the receipt-first
export the reference is the receipt's own printed reference number where the
receipt showed one, falling back to the stored filename. In the
statement-driven journal export, which is also live, the reference is the
bank-statement transaction identifier, which does not identify the receipt
at all. **The receipt-location column is empty on every row of both** in the
mode now in use, and two things are missing rather than one: the export is
called without a receipt-location map, and no receipt ingested through the
mail, upload or drop paths carries a stored location of its own, so the
fallback is empty as well. Closing this requires giving every stored receipt
an addressable location, not only wiring an existing value into the export.

So the working cross-reference today is the reference value plus the period,
and it is weaker than it should be in three specific ways: the reference is
a machine reading of the receipt that nothing verifies or checks for
uniqueness; where the receipt printed no reference it falls back to a
filename the system assigns by upload order rather than deriving from the
document; and a receipt booking to more than one account produces several
export rows carrying the same reference. It should be read as a label that
aids location, not as a key that identifies one record.

---

## 11. Access for the Service, and third parties (4.01(6), 4.01(7))

**11.1 Reading the records without this application.** No proprietary
format, no application-specific container, and no application-layer
encryption stand between a reader and the records. The receipts are ordinary
PDF and image files. The archived mail is standard `.eml`. The metadata is
SQLite with JSON documents inside it. A file browser, a PDF and image
viewer, any SQLite client and a text editor read the receipts, the archived
mail and the metadata. Card statements are stored in the format they were
supplied in, which includes Excel workbooks, and the period report is
written as an Excel workbook; those files need a spreadsheet application.
All of these are open, documented formats readable without this application.

Each period carries a partial copy of its own configuration
(`run.local.json`), written once when the period is created. It is not
self-contained and it does not support reproduction. The model configuration
and the chart-of-accounts validation block are stripped out of it; it is
written best-effort, so a period whose write failed carries no copy at all;
and it is not rewritten when the period's configuration later changes
through a card assignment, a master-data refresh or a statement attach, so
it goes stale. Because receipt reading in the mode now in use runs entirely
through the external reading service, a period cannot be re-reconciled from
the stored files alone: re-running the stored configuration against the
stored files stops with a configuration error. The extracted values
themselves live in the metadata database, not in the period's directory. The
stored file supports inspection of the settings that were in force at
creation, not reproduction of the result.

**11.2 Third parties, and 4.01(7): not assessed.** Four third parties are
between the Service and the records, and no agreement with any of them has
been read against the requirement that nothing may restrict Service access
to the system, its files, its indexes or its documentation:

- **Fly.io** hosts the application and holds the only copy of the volume.
- **The front-end host** serves the browser interface the operator uses.
  Records are fetched by the browser directly from this backend rather than
  passing through that host's servers, but the host supplies the code that
  makes those fetches, and that code holds the operator's session token and
  has unrestricted read access to every record. Whether it retains any
  record data in the browser or on its own host has not been verified: its
  source is maintained in a separate repository and was not inspected for
  this description. The backend additionally accepts cross-origin calls from
  any site served under that host's domains, so the trust placed in the host
  is not limited to the one page the operator uses. It is also the only
  human interface to the system.
- **OpenAI** receives the material needed to read each document: an image
  receipt whole; a PDF carrying a text layer as its extracted text; a
  scanned PDF as page images of at most its first four pages, so anything
  past page four is never read. Each reading call also carries the
  document's stored file name, the line-item descriptions, the account list,
  and the last four digits of every corporate card the payer holds, supplied
  so the model chooses among them rather than guessing. For the currency and
  ambiguous-match judgments it additionally receives the corporate-card
  statement line itself, with its amount, currency, date, vendor and card
  marker, alongside the candidate receipts. Where a receipt arrives as the
  body of an email rather than as an attachment, the rendered body is
  transmitted the same way. The calls use default client settings; no
  zero-retention option is configured.
- **Microsoft**, whose Graph service carries the outbound notifications
  described in 11.3 and retains a copy of each in the sending mailbox, and
  whose directory issues the application credential the system uses. That
  credential is issued for the whole tenant and requested with the default
  scope, so it carries every permission granted to the registration rather
  than a send-only permission; the sending mailbox and the recipient rules
  are enforced in this application's own code, not by the platform, and no
  application access policy currently narrows it.

Assessing these four agreements is a contract question and is outstanding.
Note separately that using a third party to supply part of the electronic
storage system does not relieve the taxpayer of any responsibility under the
revenue procedure, so reliance on Fly.io for the sole copy of the volume and
the transmission of every receipt to OpenAI under default retention terms
are the taxpayer's own compliance positions now, not questions deferred to a
vendor.

**11.3 Outbound notification mail** is sent through Microsoft Graph in two
forms. An acknowledgement to a submitter carries a file count, the
submitter's own subject line echoed back, and the month or trip label; it
adds no amounts, vendors or images of its own, though a submitter's subject
line may itself contain a vendor or an amount, and acknowledgements go to
addresses outside the tenant where an operator has listed the sender. An
alert to the operator when mail is held carries the submitting address, that
subject line, the archive identifier and the recorded error text. Neither
carries a receipt image or an extracted amount. The system reads no mailbox
through Graph; the only Graph call it makes is a send.

---

## 12. Known non-compliance and remediation status

Disclosed in full. None of these is yet remediated.

| # | Requirement | What is wrong | Priority |
|---|---|---|---|
| 1 | 4.01(2)(b) | No stored digest for the run store, so alteration is undetectable | Highest |
| 2 | 4.01(2)(b), 4.02(2) | One permission level; no per-person attribution on any stored record; no audit log; deletion effectively unrecorded | Highest |
| 3 | 4.01(8) | No retention control over the run store; one request deletes a period; queued-file replacement and same-name re-attach destroy bytes silently | High |
| 4 | 4.01(2)(c) | No inspection or quality-assurance program | High |
| 5 | 4.01(1) | Preservation: one volume, one region, no replication, no application-level backup or restore | High |
| 6 | 4.01(2)(b) | Mail arrives over unauthenticated, unencrypted SMTP; no transport security and no means of establishing what the sender transmitted | High |
| 7 | 4.01(1), 4.01(6) | A single unreadable PDF makes a whole period unreproducible, with no message naming the file; a large period may exhaust memory and produce nothing | High |
| 8 | 4.01(4) | Receipt-location column empty on every row of both exports; no receipt carries a stored location | Medium |
| 9 | 4.01(4) | The export is not retained, so the version posted to the books cannot be reproduced after a later edit | Medium |
| 10 | 4.02(1) | Reproduction strips the index key from the caption for sequence-numbered records | Medium |
| 11 | 4.01(3) | No page numbers; image orientation metadata not applied; transparency discarded; image receipts downsampled and re-compressed | Medium |
| 12 | 4.01(2)(a) | Reports do not disclose that values are machine-extracted; no measured error rate | Medium |
| 13 | 4.01(2)(a) | Report totals computed in binary floating point; an unparseable row is dropped from the PDF total without notice | Medium |
| 14 | 4.01(2)(a) | Manual attach and bulk folder ingest rewrite the period record without the lock, so a concurrent write can be lost | Medium |
| 15 | 4.01(1), 4.01(6) | No bulk retrieval; several classes of stored document reach no report; borrowed receipts have no pages behind them | Medium |
| 16 | 4.01(1) | A lost stored file is indistinguishable from an expense that never had one; the listing can overstate how many receipts are usable | Medium |
| 17 | 4.01(9) | Two databases hold record-derived data with no retention rule and survive deletion of the period they came from | Medium |
| 18 | 4.01(7) | Four third-party agreements not assessed | Open question |
| 19 | 4.01(1) | Several classes of refusal leave no record anywhere; the refusal list is capped and rewritten to the newest 200 rows | Low |
| 20 | 4.01(1) | A byte-identical duplicate arriving in the same second overwrites the earlier archive's recorded arrival time | Low |

Items 1 and 3 are the ones that would most change an examiner's view, and
item 1 is also the cheapest of the group: the digest is already computed on
upload and merely discarded, so storing it and re-checking it periodically
would close item 1 and supply the evidence item 4 requires.

---

## 13. Destruction of hardcopy originals and deletion of original computerized records: not yet permitted

Section 7 of the revenue procedure governs two acts, not one. It permits
destroying original hardcopy records, and deleting the original computerized
records other than machine-sensible records that are independently required
to be retained, only after the taxpayer has completed its own testing
establishing that the records are being reproduced in compliance with all
the provisions of the revenue procedure, and has instituted procedures
ensuring its continued compliance with all of them.

**Neither condition is met.** No such testing has been performed and no
continuing-compliance procedure exists. Most records here arrive as native
electronic originals rather than as scanned paper, so the deletion limb is
the operative one: the source e-mails, supplier PDFs and statement files
held outside this system must be retained on the same footing as paper.
Until both conditions are met, originals in either form must be retained,
and anyone discarding a paper receipt or deleting a source e-mail on the
assumption that this system holds an equivalent record should stop. Nothing
in this document relieves the taxpayer of any other record-retention duty.

---

## 14. Document control

| | |
|---|---|
| Prepared | 2026-09-08 |
| Revision | 2. Revision 1 was refuted line by line against the code; 53 corrections applied, 5 of them to flat false statements |
| Basis | Deployed code at commit `d4aa02fe`; hosting platform inspected the same day |
| Status | Draft. Not reviewed by the owner or by a US CPA. Not to be provided to any tax authority in this state |
| To settle before hand-over | Which entities file US (section 2); the deployed access-code configuration (8.2); CPA confirmation of the 4.02(2), section 7 and section 3.03 readings |
| Companion | `us-substantiation-criteria.md` (assessment of the output against the substantiation rules) |
| Next review | On any change to intake, storage, retrieval or access, and on remediation of any item in section 12 |
