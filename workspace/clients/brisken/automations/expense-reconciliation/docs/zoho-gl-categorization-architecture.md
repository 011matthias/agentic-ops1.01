# Direct-to-Zoho-GL categorization

**Status:** Phase 1 in flight, 2026-09-23. Steps 1 to 3 of the order below have
shipped, plus the chain itself: the tolerant read (#1232), the taxonomy module
(#1234), accept-and-drop on every write path (#1236), and `gl_accounts` served
beside the old keys together with `zoho/posting_resolution.py` (#1238).

**Step 4 is built (2026-09-24), not deployed.** The engine calls the chain:
a run whose config carries `gl_entity_orgs` (injected by
`coa_provision.apply_to_config` for every hosted batch created from now on,
settings registry first, then the `/data` file) categorizes each receipt and
receiptless charge into ITS entity's curated leaves, with the org id, never
the entity name, handed to `llm_leaf_labels`. `category` is the leaf code or
None; a refusal carries a named `refusal` that reaches the row's review as
`category_refused`. A batch without the key (every batch created before, every
CLI run) keeps the eight buckets, so no month mixes vocabularies. Steps 5 and 6
are still open, and so is the SPA: the published bundle renders buckets and
does not localize `category_refused`, so nothing here deploys before the owner
publishes a bundle that reads leaf codes.

Two gaps the wiring surfaced. The live settings registry keys entities by the
long legal names (`Brisken Corp Services, LLC` ...) while receipts carry the
short ones the `/data` file uses, and its Corp Services row reads org
`8227416528`, one digit off `822741658`; the short-name receipts resolve
through the file, a receipt on the long name refuses `org_not_curated`.
`Consulting` has an org id in neither source, so its receipts refuse. And the
categorization is fixed at ingest: an expense whose company is set later keeps
its `entity_missing` refusal until something re-categorizes it.

Receipts are classified directly into Dirk's curated Zoho GL leaf accounts, per
legal entity. The eight coarse buckets (`EXPENSE_CATEGORIES`) and the
category-to-account translation table (`zoho/category_accounts.py`) are retired.

## Why the middle step goes

The old path was receipt to bucket to translation table to GL account. Both known
silent mis-posts happened in that middle step: OpenAI landing in Advertising &
Promotion, and 6 of 9 sandbox rows falling back to `Office Infra and Admin` on
2026-09-22 because an account was passed as a NAME where a numeric `account_id`
was expected. Neither errored. Both posted.

The owner's worry, in his words: if an expense is sorted into the wrong Zoho GL
account, nobody would notice for months. Everything here serves that, which is
why the design prefers a refusal that names a row over a default that is right
most of the time.

The chart is not 1,252 unconstrained accounts. Dirk curated it, and the curation
is what makes direct classification tractable: 199 postable leaves across three
entities, of which roughly 44 see real use.

## The data, and how it was verified

Source: `CoA BRISKEN BCS BTS CorpServ 260923.xlsx`, Dirk's own marking, three
tabs. Derived output and the script that made it live beside the history pull in
the gitignored `context/expense-reconciliation/`.

**Dirk's test**, read off his marks rather than asked for: Y means a real
purchase can be booked here and arrives as a receipt, card charge or expense
claim. The tell is that he moved `Payroll Expenses: Salaries`, the five payroll
taxes and SEP IRA to N while keeping `Payroll Expenses: Payroll Service` and
`Payroll Expense: Continuing Education` as Y. The cut is not "payroll", it is
"can a card pay for it".

Inside the COGS tree the roll-up is N and you post to a leaf. Outside COGS the
parent is postable.

| Tab | Zoho org | Y | N |
|---|---|---|---|
| CorpServ | 822741658 Corporate Services | 68 | 29 |
| BCS | 697686691 Cloud Services | 67 | 58 |
| BTS | **808232536 Consulting LLC** | 64 | 40 |

The tab-to-org mapping was verified by matching every `Account ID` in each tab
against the live chart pull, never by the tab label. Each tab resolved to exactly
one org with zero crossover. **BTS is not the TEST-BTS sandbox (822116290)**,
which is a clone of it; the label reads like the sandbox and is not, and assuming
otherwise aims the whole mapping at a test company.

Dirk's marking is internally consistent: no Y row is inactive, and no Y row is
DO-NOT-USE.

## Four findings that shaped the design

**The account code is stable across entities; the name is not.**
`E600010-10-20-30` is `Business Travel Expenses - CRM | Food` in all three orgs.
But CorpServ names its general food leaf `CorpServ | Travel Expense | Food` where
the other two say `Travel Expense | Food`, on the same code `E100010-31`. A
name-keyed mapping silently skips CorpServ. Key on the code; resolve code to
`account_id` per entity.

**The code tree does not describe the hierarchy.** `Business Travel Expenses -
CRM` is code `E600010-20`, but its children are `E600010-10-20-*`, nested under
`E600010-10`, the Conferences parent. Identical in all three sheets. Any
resolution that infers a family from a code prefix mis-resolves CRM travel. Match
on the account name or the id, never the prefix. This coexists with the rule
above: the code is a stable cross-entity KEY, not a path.

**`zoho-books-coa.json` was short for Cloud Services, and not because of
pagination.** It held 199 accounts for org 697686691 with zero
`cost_of_goods_sold` and zero `other_expense`, while Consulting carried 25 and 5
and Corporate Services 11 and 4. Nineteen accounts Dirk marked Y were absent,
including `2031056000014161139 COGS - DEV Infrastructure (SAP Apps & others)`,
the account Anthropic posts to under Cloud Services and the design's own
flagship Tier 1 example.

199 sits one below a 200-row page boundary, which is what a pull that stopped
paginating looks like, and that is how it was first filed. Measured against the
live API on 2026-09-24, walking `has_more_page` to exhaustion every time, it is
not what happened:

| params | per_page | rows | pages | `has_more_page` |
|---|---|---|---|---|
| default | 200 | 199 | 1 | false |
| default | 100 | 89 | 1 | false |
| default | 50 | 47 | 1 | false |
| showbalance | 200 | 247 | 2 | false at the end |
| showbalance | 100 | 86 | 1 | false |

A smaller page returns fewer total rows, and the server reports completion every
time. So no page size makes this endpoint trustworthy for this org, and the fix
the first reading implies, "follow the pagination and fail on a short page",
cannot work: every short page here also says there is nothing more.

The two listings are not nested either. Seven accounts appear only under the
default params and 55 only under `showbalance`, whose documented spelling
`show_balance` is accepted and silently ignored. Their union is 254 and still
omits `2031056000023745007 E600010-30-10 Marketing Expenses - people`, which
`GET /chartofaccounts/{id}` returns as active and typed `expense`.

Completeness therefore cannot be judged from inside the listing, because the
listing is the thing that is wrong. It needs the curated taxonomy as an outside
answer key, which is what `tools/pull-brisken-zoho-coa.py` asserts: every
account_id Dirk marked postable is present, topped up by id where no listing
produced it. Live on 2026-09-24 that took Cloud Services from 199 to 255 with
nothing dropped, 67 of 67 curated accounts present.

The sheet remains the source for the compiled asset and the pull remains a
cross-check; what changed is that the pull is now complete enough for the COA
gate, which reads it and answers UNKNOWN for anything absent.

**`resolve_account_id` did not check leaf-ness or scope.** A reference naming a
parent or roll-up resolved and posted, and the only thing holding that line was
that `category_accounts._TEST_BTS` had been hand-audited for leafness. Closed
2026-09-24 in the change that deleted the table (item 4), but not by lifting
`coa_gate.classify_account` as written, because that rule contradicts the
curation: 35 of the 194 postable accounts are chart parents (`Travel Expense`,
`IT: Computer and Internet Expenses`, `Professional Fees` ...), and Zoho does
accept a posting on a parent (Brisken's books hold 8 over 2024-09..2026-09, and
the 2026-09-22 silent default was itself a parent). So in a curated org the
resolver asks the curation, which already makes COGS roll-ups N and payroll N;
an org nobody curated keeps the chart's parent rule. A chart whose id for a code
differs from the curated id for the target org also refuses, since codes are
shared across the three orgs.

**The export COA gate still disagrees with the curation.** Measured against the
live provisioning `scope_groups`, `coa_gate.classify_account` diverts 56 of the
194 postable accounts (23 of 64 Cloud Services, 11 of 62 Consulting, 22 of 68
Corporate Services), `COGS - DEV Infrastructure` among them, and passes some
accounts marked N. On a GL batch the export would blank those accounts before
the resolver sees them. Queue item 4b.

## The chain

```
(entity, vendor) rule in the per-entity learning store
  -> [Tier 2: ruled out, refuses]
  -> direct LLM match against that entity's curated leaves
  -> refuse: account_unresolved
```

Tier 1 lives in `learning/store.merchant_category`, already keyed
`(legal_entity_id, vendor_norm)` and already carrying a `zoho_account` column,
with `consult.py` supplying the company then no-company then vendor-only
fallback. It is not the settings merchant registry, which gives each merchant one
global account with no entity dimension. Where an `(entity, vendor)` pair
resolves to more than one account, the chain refuses; it does not pick.

`resolve_account_id` validates that the target is an active, postable leaf and
returns a numeric `account_id`, never a name.

Built as `zoho/posting_resolution.py` (PR #1238), pure and called by nothing
yet. Two rules in it are worth restating because they are easy to soften
later. A learned rule naming a leaf this entity cannot post to REFUSES rather
than falling through to the model, since falling through is the same
substitution the translation table made one layer up; a learned rule naming NO
leaf does fall through, because a bucket-only rule answers a different
question and overrides nothing. And `PostingResolution` rejects a non-numeric
`account_id` at construction, which is the assertion the 2026-09-22 mis-post
went through unchallenged.

## Tier 2 is ruled out

The owner ruled 2026-09-24 that it will not be built: "trip does not define
category because during a trip there can be expenses from multiple categories."
The reasons below predate the ruling and agree with it.

Trip-purpose inheritance is not built, and it is deliberately not built.
`cost_centers.py:44`: *"Category is not one either; co-varying the two dimensions
destroys the point of cutting the money a second way."* Wiring a trip's purpose
to an account reverses a written design decision rather than filling a gap.

Three further reasons, any one of which would be enough:

The trip feature has never carried production data. Live on 2026-09-23,
`GET /api/trips` returns no trips, all seven expense batches are `company-month`,
and the cost-centre registry is empty, each proven against a control in the same
call. Item 38 also puts the trip and cost-centre design explicitly on hold
pending the owner's brainstorm.

A purpose cannot pick a leaf. Each family has three children, not one:
Conferences, CRM and general Travel each split into Transportation,
Accommodation and Food. `conference -> Conferences: Travel Expenses | Food`
silently chooses one of three.

The codebase already refused this exact shortcut. `category_accounts.py:102-107`
leaves `Travel & Transport` unmapped because its July rows split between gasoline
and vehicle rental: *"A default that is wrong half the time is worse than a
refusal that names the row."*

Travel and dining that no vendor rule resolves refuses to
`(assign)`. Do not wire `cost_center` to an account.

## What breaks, and in what order it is safe

The break is not storage. Category columns are plain TEXT and nothing validates
on read, so months frozen under the old vocabulary keep loading. The break is in
validation, in round-trip, and above all in silence.

**Seventeen truthiness gates on `cat.category`** across ten files flip branch if
category goes None, with no error: `posting_common.py:132/137`,
`sheet_writeback.py:143/185-186`, `zoho_export.py:398/428`, `coa_gate.py:332`,
`report_xlsx.py:347/633`, `reconciled_csv.py:205/206/276`,
`web/service.py:2609`, `cli.py:866/1943`, `categorize.py:1047/1057`. Exports
blank, journal rows become unpostable, the SPA's suggestion disappears.

**The registry goes inert rather than loud.** `merchant_registry.resolve:435` and
`categorize.apply_registry_category:281` both do `category if category in
EXPENSE_CATEGORIES else None`. Under a new vocabulary every live rule stops
firing and receipts fall through to the LLM at full cost, with no error and no
log line. It looks exactly like working software.

**A settings save is wholesale.** `PUT /api/settings` validates before it
patches, and the SPA sends the entire map back on every merchant save, so one
stored merchant carrying an old bucket string 400s the whole save including the
cards and entities tabs. The precedent to follow is `RETIRED_ENTITY_KEYS`
(`web/store.py:210-216`): report the retired value under `ignored` instead of
raising.

The busiest reviewer write path, `POST /api/runs/{run_id}/categories`, never
validated the vocabulary at all and already accepts leaf codes.

Order:

1. Tolerant read, alone and first. Shipped, PR #1232.
2. Accept-and-drop on every 400-ing write path, before any behaviour changes.
   Shipped, PR #1236. Six paths, not the five that were planned:
   `learning_cli.cmd_set` writes the same table the chain reads first, and it
   takes both vocabularies now while still refusing an unrecognised value,
   because a CLI has no wholesale round-trip to break and a silent no-op on a
   typed argument is worse feedback than an error.
3. Serve both vocabularies, adding a new key beside `categories` and
   `category_options` rather than repurposing them, so the published SPA keeps
   rendering until the owner publishes a new bundle. Shipped, PR #1238, as
   `gl_accounts` + `gl_revision`; both joined `SETTINGS_DERIVED_KEYS`, without
   which adding them would have broken every save that round-trips the
   payload.
4. Convert the engine, keeping `category` written as a mirror of the leaf so no
   truthiness gate flips silently.
5. In the same PR as 4, remove both copies of the leak and every gate that would
   flip. Grepping `_debit_account_and_note` finds one of the two leaks; the other
   is inline in `sheet_writeback.py`. Done 2026-09-24 as its own PR after 4: all
   three sites (the writeback has two) write `(account unmapped - assign)` for a
   categorized line with no account, the value a charted batch already wrote,
   and the category moves to the journal note. The `cat.category` gates are
   unchanged: a refused GL line (`None`, REVIEW) still reads uncategorized.
6. Relabel `categorization_gate.py` and regress-check it. Left alone it keeps
   measuring the retired vocabulary through the keyword stubs and reports green
   over a path that no longer runs. Done 2026-09-24 (queue item 6): it is now
   the BUCKET-path gate by name, in its report ("GL path (batches with
   gl_entity_orgs): NOT measured by this gate") and in calibrate's JSON
   (`path: bucket`, `gl_path_measured: false`). A test pins that it routes
   through `_categorize_one` and never reaches `_categorize_one_gl`, and
   breaking the GL chain's refusal leaves it green, which is the point of the
   label: no deterministic gate measures the GL chain today.

## Open, and whose it is

- The six accounts flagged `SPOT-CHECK` in the workbook are judgement calls, not
  rule applications: per diem, Tax Management Services - Holding in both orgs,
  R&D, COGS - Support BRISKEN Tech / JB, and third-party-reimbursement travel.
  Dirk's.
- Card 3645's registry entry holds another card's label in its `zoho_account`
  field (backlog item 172). The real chart account has to come from Dirk.
- `registry_upserts_from_expense_run` fires automatically on Publish, not on a
  deliberate reviewer save, and its conflict detection compares category only,
  never `zoho_account`: two rows agreeing on category and naming different
  accounts do not conflict and the first account wins silently. Under a design
  where the account is the answer, that is a nearest-plausible default sitting
  inside the writer of durable memory. Needs fixing before the chain writes
  through it.
- ~~`paid_through_account_id` is a raw numeric id that passes through no
  resolution and no validity check.~~ Closed 2026-09-24 (backlog item 184):
  `zoho.accounts.resolve_paid_through`, called from `build_expense_payload`.
  Which card each production entity pays from is still master data, and Dirk's
  (item 172).

## Why the July and August dry runs are not in Phase 1

`reconcile_month.assert_org` permits only the sandbox org 822116290 and refuses
production by name pending Brisken's sign-off. Dirk's curated orgs are
697686691, 808232536 and 822741658, and 808232536 appears in neither
`PRODUCTION_ORG_IDS` nor `SANDBOX_ORG_ID`. The only runner that can post cannot
be pointed at any org the curated leaves cover, so a curated-leaf dry run against
July or August cannot be produced without an `ORG_PROFILES` row that does not
exist. The chain is unit-testable; it is not yet month-runnable.

Unrelated and unchanged: the Zoho token is read-only, and July must never be
injected because Criss hand-entered it and there is no bank feed.
