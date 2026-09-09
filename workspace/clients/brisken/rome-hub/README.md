# rome2026.brisken.com deploy source

Rescued into git 2026-09-09. Until then the only copy of what this live page
serves lived in `.scratch/brisken-rome-hub/` on one laptop, gitignored, and had
already drifted from the tracked canonical.

## What is here

| File | What it is |
|---|---|
| `index.html` | The canonical page. Carries the 2026-07-29 TC story alignment (PR #492): "TreasuryCentral, powered by OnePilot, grounded in SAP", "applications and use cases", "On SAP's own cloud, in your landscape". |
| `index.live-2026-07-13.html` | What the live site actually served as of 2026-09-09, byte-identical to production. Pre-alignment: "Treasury, run by AI, on your SAP data", "Delivered as SaaS". Kept as the record of what Rome visitors saw, not as a thing to deploy. |
| `brisken-rome-2026-og.png` | Open Graph image, unchanged. |

## Deploy target

Vercel project `brisken-rome-hub`, id `prj_EFYtjsRojr7xHONB9w4UhZg5JOAu`, in team
`matthias-neumanns-projects` (`team_MNNYUo2DofKqKUISX0X01rre`). The binding
previously existed only as a gitignored `.vercel/project.json` in the scratch
directory, which is why nobody could find the deploy target.

## The drift, and why it is not simply fixed

`status/p2-onepilot-site.md` recorded that Rome was "aligned in-repo but Rome has
no Vercel project (deploy target pending)". The first half is right; the second
half is wrong. The project exists and has served `rome2026.brisken.com` since
July. So the approved TC-story rewrite never shipped, not because there was
nowhere to ship it, but because the deploy target was believed missing while its
binding sat in an untracked folder.

Deploying `index.html` would close that gap in one command. It is deliberately
NOT done here, because `TARGET-ARCHITECTURE.md` P1 proposes retiring this
hostname with a 301 to brisken.com: the event ended in June 2026 and the page is
a post-event asset hub with no ongoing purpose. Shipping a copy edit to a page
scheduled for retirement is work that gets thrown away.

The decision is therefore one of two, and it belongs to the owner:

- **Retire** (recommended, and what the architecture plan assumes): 301 to
  brisken.com, delete the Vercel project, keep this directory as the record.
- **Keep**: deploy `index.html` so the live page stops contradicting the approved
  story, then treat this directory as the deploy source from now on.

Until one is chosen, the live page keeps serving June's copy. That is low-harm,
since the audience is Rome booth visitors who have already seen it, but it is not
nothing: the page states a positioning Brisken has since replaced.
