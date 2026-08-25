Calvin clip: "A bank transfer, from an email"
=============================================

Two cuts of the same 100-second forwardable (a 10s "Meet Calvin" overview card, then
the 90-second story), captions burned in, built to read muted.

  calvin-clip-16x9-1080p.mp4   1920x1080   email, landing page, the archive copy
  calvin-clip-1x1-1080.mp4     1080x1080   LinkedIn feed, where 16:9 loses half the screen

These are the SILENT masters. The narrated distribution cuts (Kokoro am_michael male
voice, -14 LUFS integrated / -1.5 dBTP, one connected walkthrough muxed identically
into both ratios) are built in the video-gen repo (out/brisken-calvin/) by
pipeline/narrate-calvin.mjs. The clip STILL reads fully muted: the captions are burned
in and the voice only says what the frame already shows, so it works watched muted in
a feed or an email client, or with sound on. (Note: a real Brisken voice can replace
the synthetic one at any time.)

WHAT THIS IS
------------
An illustration of the OnePilot Agents flow, animated from slide 8 of the
Digital Co-Worker deck ("Use Case: Create Bank Transfer from an Email request").
The five steps, the named agent Calvin, and the S/4HANA Cash Management source
are Brisken's own; the approval gate and the audit trail are shown explicitly
rather than implied.

It is NOT a screen recording of the product. Every frame carries an
"ILLUSTRATION" label and the end card says so. Do not present it as a product
recording. When someone can screen-record the live Calvin demo, that recording
replaces this file and is materially stronger.

All figures, names, and record IDs on screen are synthetic demo data.

WHAT IS DELIBERATELY NOT CLAIMED
-------------------------------
  - No SAP Store listing. Only Market Data Hub and Trade Automation are listed
    (Store audit, 2026-06-17). Digital Co-Worker is not.
  - No named customer. The proof for this flow is anonymized.
  - No ISO 27001 or SOC 1 line, pending confirmation of certificate scope.

The clip is a soft CTA. It ends with a URL and no booking link; the meeting ask
belongs in the message that carries it, which is what lets a treasurer forward
it without forwarding a sales ask.

Brief and production runbook: repo agentic-ops1, branch leadgen/task-6,
output/leadgen-task-6/.

Prepared 2026-07-09. Revised 2026-07-11: workspace emphasis per Dirk's feedback
(the manual beat, the cash beat, and the end card now name Calvin building the
workspace around the request). Revised 2026-07-12: generated narration added
(connected walkthrough, af_heart) and the real full-color Brisken logo swapped in
for the earlier reverse mark; the film still reads fully muted. Revised 2026-07-14
per Dirk's feedback (overview missing / male voice / more informative monologue):
10s intro overview card added (film 90s -> 100s), narrator switched to the male
am_michael, and the read/cash/book/conf lines carry more of what each frame shows.
