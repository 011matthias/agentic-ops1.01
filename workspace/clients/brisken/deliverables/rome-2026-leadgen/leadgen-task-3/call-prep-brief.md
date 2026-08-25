# Call prep: Ian Haegemans, Sanofi

**Call:** next-week Friday, about 16:00. Dirk sends the invite.
**Prepared:** 2026-07-09
**Companion:** `demo-flow.md` (run of show), `collateral-pack/` (deck + one-pager)

Read the confidence column before you use a line. Public research is for asking sharper
questions, not for reciting at him. Nobody enjoys being told their own org chart.

## What Brisken already holds on him (first-party)

Corrected 2026-07-09. An earlier draft of this brief said Dirk's forward was the only
first-party source. That was wrong. It was an artefact of searching with ripgrep, which
honours `.gitignore`, over a repo where the client's whole `context/` tree is gitignored.

From Dirk's forward: Ian Haegemans, Treasury Process & Analytics Expert, Global Process
Owner Team, Sanofi, Brussels. `ian.haegemans@sanofi.com`. Replied to the Rome booth Tier 1
follow-up. "Friday is perfect". Dirk sends the invite.

From Brisken's own records:

| Record | Content | Source |
|---|---|---|
| **He came to the booth.** | Token registration, `fob_encoded: true`, `2026-06-24T06:51:05Z`. He typed his own title: "Treasury process & analytics expert" | `context/.../event-admin/brisken-token-registrations.csv` row 95 |
| Rome master sheet row | `source: Both` (invite roster and booth), `in_our_booth: Yes`, `no_show: No`, `sponsor_opt_in: Yes`, phone `492878309`, country Belgium, `post_event_outreach: Booth follow-up sent 2026-07-08`. No `dirk_notes` on him | `rome2026-post-event-master-contacts.xlsx` |
| **Sanofi is a lead, not a client** | Zoho account: `status: Lead - Cloud Subscription`, owner Dirk Neumann, last activity 2026-02-20. The sheet agrees: `brisken_customer: No (Lead - Cloud Subscription)` | `context/zoho-crm.json` |
| Prior Sanofi touches | Four `sanofi.com` contacts captured at 2025 trade shows, owned by Yashmica Roy | `context/zoho-crm.json` |
| **Isabelle Badoux** | A real Dirk-owned CRM contact: "General Manager Head of Global Treasury Operations, Systems & Treasury Transformation", Belgium, `+32 (2) 548 38 61`, lead_source Trade Show | `context/zoho-crm.json` |

So his title is first-party confirmed from his own registration, not inferred. And he is a
warm booth contact at a Dirk-owned lead account, not a cold name.

Two traps in the data. His `attendee_type` reads **"SAP customer"**, which means a customer
of SAP, not of Brisken. And `sales-nav-add-list-rome2026.md` classifies Sanofi as
`customer` in its Track column; that file was generated 2026-06-29, before Dirk's 2026-07-08
correction, and is stale. Client status is keyed on `Account_Status`, never `Account_Type`:
of 120 accounts reading `type: Customer`, 49 are leads and only 39 are active clients.

The comms log still carries no thread with Ian. Sanofi appears there only in list-building
and in Dirk's mislabel correction.

## What is publicly documented

| Fact | Why it matters | Confidence |
|---|---|---|
| Sanofi decided in 2017 to move to a global S/4HANA instance; treasury deployment began July 2018 and the core treasury solution went live **September 2020** ([intensum.com](https://www.intensum.com/2021/10/22/treasury-s4hana-sap/)) | Sanofi is not migrating. They finished. Do not pitch migration timing. | Directly fetched |
| **Treasury Core Model (TCM)**, launched 2017, redesigned **40+ treasury processes** onto SAP S/4HANA Treasury, inside the "iShift" One-ERP program ([Sanofi job posting](https://jobs.sanofi.com/en/job/bogota/senior-treasury-core-model-tcm-solution-expert/2649/35154702848)) | The process standardisation he owns already exists. The remaining variance is in the data feeding it. | Directly fetched, Sanofi's own posting |
| Sanofi's own posting for **"Treasury Process & Analytics Expert"** says the seat sits in the Treasury GPO team, supports the Treasury GPO and Global Process Leads in evolving the TCM, "standardizing, harmonizing, and optimizing the Treasury end-to-end processes", and builds "an analytical framework (using standard dashboards, KPIs, reports) to monitor process efficiencies, deviations, and process adherence" with Power BI/Tableau, SAP Treasury and data-governance tooling ([posting](https://be.linkedin.com/jobs/view/treasury-process-analytics-expert-at-sanofi-4224938774)) | This is Sanofi describing his job. Process adherence monitoring and KPI dashboards are what he is measured on. | Directly fetched |
| Ian's own LinkedIn post, after a data-governance and a Snowflake event: *"At Sanofi treasury we are making progress to level up our data governance maturity and building out a data foundation to become AI-ready"*, alongside *"Hard to believe it's only been 6 months at Sanofi!"* ([profile](https://be.linkedin.com/in/ian-haegemans-339716162)) | His own stated agenda, in his own words. Governed data foundation, then AI. That is the TreasuryCentral sentence. | LinkedIn public preview, wording approximate |
| **Sanofi European Treasury Center** is the group in-house bank, registered Rue de la Science 14, Brussels ([LEI record](https://lu.lei.report/LEI/549300O1V4CK6HCZHH75)) | Explains the Brussels posting. He sits at the in-house bank. | Directly fetched |
| SAP-based global payment factory since end-2012: PoBo and PiNo structures, 30,000+ automated payments/month from 50+ affiliates, over EUR 1bn/month, 30 currencies ([Zanders case study](https://zandersgroup.com/en/insights/case-studies/sanofi-overcoming-complexity-to-implement-a-global-factory-payment)) | Volume and centralisation are long settled. They are past "should we centralise". | Directly fetched, undated |
| Sanofi's finance function runs on **100+ Global Process Owners** who "formalize processes, define validations, thresholds, performance indicators and tools". Hermès Martet, Head of Global Finance Services: *"We are not there to perform processes... The idea is to create value for the group."* ([daf-mag.fr](https://www.daf-mag.fr/bi-1244/transformation-processus-2133/transformation-pourquoi-sanofi-remplace-les-silos-par-une-logique-de-processus-26554)) | The GPO model is institutional, not a pilot. Speaking GPO language is speaking Sanofi language. | Directly fetched, French trade press |
| Recent TMI award for a Collections-on-Behalf-Of structure with multi-currency virtual accounts, with BNP Paribas, reportedly involving HighRadius ([treasury-management.com](https://treasury-management.com/articles/sanofi-injects-innovation-into-ihb-with-impressive-cobo-structure)) | Shows the in-house bank still ships new structures. | **Lower confidence**: page returned 403, snippet only |
| CFO **François-Xavier Roger** since 1 April 2024; previously Nestlé CFO, and Head of Finance, Treasury and Tax at Danone ([Sanofi press release](https://www.sanofi.com/en/media-room/press-releases/2024/2024-02-01-06-30-00-2821665)) | A CFO who has personally run treasury reads a treasury business case differently. | Directly fetched |

## Not found, so do not assume

- No conference talk, panel, trade-press quote or byline for him anywhere. Only his own
  LinkedIn activity.
- No stated relationship between Ian and Isabelle Badoux. She is senior and she is at
  Sanofi treasury in Belgium; nothing sourced says she is his manager, his skip-level, or
  connected to this call. An earlier session was corrected for asserting exactly that.
- No employment history before Sanofi.
- No current named Group Treasurer, VP Treasury or Head of Treasury at Sanofi. Wolfgang
  Weber is named as Head of In-House Bank in 2015-era sources; unconfirmed today.
- Nothing from Sanofi's own annual report or Form 20-F. The treasury and SAP narrative rests
  on secondary sources: two consultancies who did the work, and Sanofi's own job postings.
- His LinkedIn preview gives the location as Antwerp metro while Dirk's forward says
  Brussels. The in-house bank is registered in Brussels. Probably a commute, not a conflict.
  It is not worth mentioning.

## The angle this actually produces

Sanofi standardised the treasury process. Since 2017 they redesigned 40+ processes into one
Treasury Core Model and ran it onto S/4HANA Treasury, live since 2020. Ian's team evolves
that model and monitors adherence to it with dashboards and KPIs.

So the pitch is not "standardise your process". It is the sentence after that one. When the
process is standard but the data arriving into it is assembled differently in each place,
the adherence KPI measures the reporting, not the process. A governed data layer is what
makes a process-adherence metric mean something.

And this is his own agenda, unprompted, in public: data governance maturity first, AI-ready
foundation second. TreasuryCentral is a governed data layer with AI automation on top. He
already believes the premise. The call is about whether we are the layer.

The deck's Sanofi proof line was written before this research and lands on it anyway:

> Standardise the process once, governed and analytics-ready, and run it the same way across
> the whole group.

Keep it.

## Three questions worth the call

These are informed by the research without reciting it. Each one is a question he can only
answer from the inside, which is the point.

1. "When you look at process adherence across the entities, how much of the deviation you
   see is genuinely process, and how much is the data arriving in different shapes?"
2. "You have the Core Model. What still gets hand-assembled before it reaches the dashboard?"
3. "You mentioned building a data foundation that is AI-ready. What has to be true about the
   data before you would let a model near a treasury number?"

Question 3 quotes his public post back at him. Use it only if it can be delivered as
genuine interest. If it would land as surveillance, drop it and ask question 2 harder.

## What would sink the call

- **Pitching the S/4HANA migration moment.** It is the Zalando angle. Sanofi finished five
  years ago. Saying it tells him we did not look.
- **Saying BTP.** Standing directive from Dirk. Stripped from the deck and one-pager in this
  pack.
- **Naming a pharma reference.** We have none. Evonik and RWZ are the OnePilot references,
  and Dirk has not yet signed off on naming them.
- **Selling him a TMS.** He has SAP Treasury. TreasuryCentral is the layer feeding it.
- **Reciting his job description at him.**
