# Shared-file change proposals (not applied)

Task-6 isolation rules forbid editing shared files. These are the four edits the
completed brief implies, written out so they can be applied in one pass by whoever
merges. Nothing here has been touched.

---

## 1. `workspace/clients/brisken/specs/1-spec/p2-bant-lead-generation.md`

Line 21 of `next_steps` currently reads:

> `- "Lane 1 (autonomous): build the MDH 'your [vendor] feed into SAP, mapped' teardown + ABM 1-pager template + Calvin/Remittance forwardable clip brief"`

All three Lane-1 forwardables now exist. Replace with:

> `- "Lane 1 DONE: MDH teardown + ABM 1-pager template (outreach-assets/mdh-outreach-assets.md) + Calvin clip brief (outreach-assets/calvin-clip-brief.md). Clip itself is unrecorded; blocked on a demo-tenant capture slot (see production-runbook.md Path A)."`

Bump `updated:` in the frontmatter and add to `last_changes` that the clip brief
landed, and that the asset is a funding-request-to-bank-transfer flow rather than a
remittance demo despite the "Calvin/Remittance" label the spec introduced.

## 2. `workspace/clients/brisken/context/lead-generation/outreach-assets/calvin-clip-brief.md`

The brief belongs beside its sibling `mdh-outreach-assets.md`, which is the canonical
home for Lane-1 forwardable content drafts. On merge, move
`output/leadgen-task-6/calvin-clip-brief.md` there and leave the runbook in the task
directory, or move both if the runbook is wanted next to the content.

## 3. `workspace/clients/brisken/context/lead-generation/evidence/brisken-product-catalog.md`

The "Naming OnePilot's AI" section recommends `OnePilot Agents` and rules out
"digital co-worker", but does not say what happens to **Calvin**, which is a proper
noun printed inside Brisken's own slide 8 and cannot be renamed by a marketing
decision. Add one line under that section:

> `Calvin` is not a competing label. `OnePilot Agents` is the category; `Calvin` is
> the name of one agent, already on screen in the Digital Co-Worker deck's slide 8
> chat box. New copy may say "Calvin is an agent on OnePilot" and must not say
> "digital co-worker".

This is the only reason the clip can retire the deprecated label without asking
Brisken to re-cut a deck. Worth recording so the next asset does not re-litigate it.

## 4. `workspace/clients/brisken/context/lead-generation/Rome-Event/booth-materials/booth-playbook.md`

Line 107 hedges: *"the 90-second Calvin/remittance clip if available"*. Once the clip
is recorded, drop the hedge and link it. Until then, leave it; the hedge is accurate.

## 5. `workspace/clients/brisken/context/comms-log.md`

The email below was **sent** on 2026-07-09 20:41 CET, from Matthias.Silva@brisken.com
to dirk.neumann@brisken.com, on the owner's explicit go. House rule is that sent
messages live verbatim in the comms log; that file is outside this task's directory,
so the entry is staged here for whoever merges.

> **Subject:** A 90-second OnePilot clip, on SharePoint next to the decks
>
> Hi Dirk,
>
> I made the 90-second clip we had on the list. It follows the funding-request flow
> from slide 8 of the Digital Co-Worker deck: an email arrives, Calvin reads it and
> proposes the action, checks the cash position in S/4HANA, a person approves, and the
> memo record is booked, with every step logged.
>
> It is in SharePoint beside the decks, in a new folder called 2026_VIDEO (hyperlinked
> to `.../OnePilot - Cloud Solutions Presentations/2026_VIDEO`). There is a version for
> email and one for LinkedIn.
>
> It is an illustration rather than a recording of the product, and it says so on
> screen. If you can get me 40 minutes with someone who can drive the live Calvin demo,
> I'll re-cut it from the real thing.
>
> Matthias

Open with Dirk, tracked here because the email deliberately does not carry them: the
ISO 27001 / SOC 1 certificate scope, and whether the chemicals customer clears a named
reference for this flow.

---

## Not proposed, deliberately

The Digital Co-Worker deck itself. It went to Adidas on 2026-07-07 carrying the
deprecated "digital co-worker" label throughout. Re-cutting it is a real decision
with a real cost, it touches a deck already in a prospect's inbox, and it is Dirk's
call, not a side effect of a clip brief. Question 4 in the brief surfaces it.
