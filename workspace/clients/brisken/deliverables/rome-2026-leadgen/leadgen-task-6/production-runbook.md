# Calvin clip: production runbook

Everything below is a manual step, because the two things this asset needs are a
logged-in OnePilot demo tenant and a video editor, and neither is reachable from
this repo. The brief (`calvin-clip-brief.md`) is the content spec. This file is the
execution order.

Pick Path A. Path B exists so the asset is not blocked on calendar availability.

---

## Path A: record the live demo (preferred)

The clip's whole trust advantage is that it is the real product. A schematic of a
product is a schematic; a recording of a product is evidence.

**Who:** Dirk, or whoever at Brisken can drive the Calvin demo end to end.
**Time:** about 40 minutes of recording for a usable take, plus editing.

### A1. Before the recording starts

- [ ] Confirm the demo tenant can run the full slide-8 flow live: mail fetch,
      summary, cash position from S/4HANA Cash Management, memo record creation,
      confirmation in chat. If any step is stubbed, note which, and stop; a clip
      that cuts around a broken step will not survive a technical viewer.
- [ ] Confirm the approval prompt (shot 6) exists in the demo tenant. If four-eye
      approval is configuration rather than a visible screen, find out what the
      screen looks like when it is switched on, and switch it on.
- [ ] Seed the demo mailbox with the funding request. Synthetic amount, fictional
      entity code, non-existent counterparty. Nothing that resembles a real customer,
      a real IBAN, or a real employee.
- [ ] Set the OS display to 1920x1080. Not a scaled 4K panel; the text has to be
      crisp at native resolution.
- [ ] Turn off every notification: Teams, Outlook, Windows toasts, calendar popups.
      One Teams banner in the corner and the take is dead.
- [ ] Sign out of anything in the browser chrome that shows a real name or tenant.
      Use a clean profile with no bookmark bar and no extension icons.
- [ ] Browser zoom to a level where the chat text is comfortably readable on a phone.
      Test by recording ten seconds and watching it on a phone before committing.

### A2. Masking checklist (run this again after editing)

Nothing in the final frame may show: a real customer name, a real bank name tied to
a customer, a real IBAN or account number, a real employee name or photo, a real
email address, a live ticket or incident reference, or a tenant URL that identifies
a customer. The reviewer for this is not the editor.

### A3. Recording

- [ ] Record the whole flow in one take, slowly, without narration. Narration comes
      later or not at all.
- [ ] Record shot 2 (the manual path) separately: the three windows, the keying.
      This is a re-enactment of the status quo, and it is the shot everyone forgets
      to capture because it is the boring one. It is also the shot that makes the
      rest land.
- [ ] Hold on the approval prompt in shot 6 for a slow count of three before
      clicking. The edit needs the room.
- [ ] Capture at 1920x1080, 30fps minimum, with a cursor highlight if the tool has
      one. Record system audio off.
- [ ] Do a second full take. There is always something in the first one.

### A4. Editing to the brief

- [ ] Cut to the nine shots and the timings in `calvin-clip-brief.md` §4.
- [ ] Burn the captions in. Do not ship an .srt sidecar as the only caption route;
      the clip has to work in an email client that will never load one.
- [ ] Speed-ramp shot 2 so the manual path feels tedious without taking real time.
- [ ] Hold shot 6 at full speed. If the edit runs long, cut from 4 and 7.
- [ ] Build the end card exactly as §6 specifies. Check it against the three
      "must not appear" items before exporting; the SAP Store line is the one that
      slips through.

### A5. Export matrix

| Variant | Ratio | Use |
|---|---|---|
| Master | 16:9, 1920x1080, H.264 | Email attachment link, landing page, the archive copy |
| Feed cut | 1:1, 1080x1080 | LinkedIn feed, where a 16:9 clip loses half the screen |

Both carry burned-in captions. The 1:1 cut needs its own caption placement, not a
centre-crop of the 16:9; text lands outside the safe area otherwise.

Keep the master well under 50 MB. Confirm the per-file limit of whatever host is
chosen before uploading, rather than discovering it at upload time.

---

## Path B: the labelled schematic (fallback only)

If no one can record the live demo inside two weeks, build the clip as motion
graphics from the existing deck design system. The build scripts and the dark
cockpit palette already exist in `.scratch/deckgen/build-digital-coworker.js`, and
slide 8 already encodes the exact five-step flow, so this is an animation job, not a
design job.

**The hard rule:** a schematic is never presented as a product recording. The end
card of a Path B cut carries the line *"Illustration of the OnePilot Agents flow"*.
A viewer who later sees the real UI must not feel they were shown something else.
Breaking this costs more trust than the clip ever earned.

Path B is materially weaker for the second viewer described in the brief's section 2,
who is looking for evidence and will read an animation as marketing. Treat it as a
placeholder that gets replaced the week the demo tenant is free, not as the asset.

---

## Hosting, tracking, and where the file lives

**Host it first-party.** `resources.brisken.com` is live and already serves the SAP
brochure PDFs from its own Vercel project, isolated from the main site. A clip at
`resources.brisken.com/onepilot/calvin` is a Brisken URL in a Brisken email. A
YouTube link in a cold treasury email is a different kind of link, and it hands the
click to a page with a competitor's ad on it.

- [ ] Upload the master and the feed cut to the `resources-site` project.
- [ ] Wrap the master in a minimal landing page rather than linking the raw MP4, so
      the click has somewhere to land and the end-card URL has a destination.
- [ ] Give each outreach tier its own tracked link, so a forward inside a buying
      committee is visible as a second view from a different source. The forward
      count is the only metric that tells you whether the asset did its job.
- [ ] Archive the master to SharePoint under `MARKETING/20_Assets/` alongside the
      product decks, so it is findable by someone who is not in this repo.

## The gate before it is sent to anyone

Do not send until all five are true.

- [ ] The masking checklist (A2) has been run by someone who did not edit the clip.
- [ ] The end card carries no SAP Store claim, no named customer, and no ISO or SOC
      line that Dirk has not confirmed.
- [ ] The clip is watchable with the sound off, on a phone, by someone who has never
      heard of Brisken. Test this on an actual person, not on yourself.
- [ ] Nothing in it says "digital co-worker".
- [ ] Dirk has watched it and signed off, because his name is on the email that
      carries it.
