# Mini-Checkpoint: Brisken Recon Ops Tail, Item 123 Closed Out

**Date:** 2026-09-20
**Status:** Item 123's scheduling question decided and closed; the alert path proven live; one credential question left
**Type:** mini

---

## Summary

Second half of 2026-09-20, after the day's first checkpoint (#1122). The owner
took the item 123 decision, authorised the first live firing of the alert path,
and asked for alerts to reach their Brisken mailbox instead of the developer's
Gmail. Two PRs merged. The mail redirect turned out to be blocked at the sender,
which is now proven with two live refusals rather than inferred from a comment.

## What Was Done

- **Owner decision recorded: the ~5h worst-case blind window is accepted.** The
  scheduling half of item 123 is closed and nothing was built for it. The three
  options stay in the item as the record of what was weighed.
- **Fired the alert path for real, first time ever** (run `35517060243`). Issue
  #1125 opened, the `recon-uptime` label created, and the recovery run commented,
  closed it and delivered its mail. A dry run cannot exercise the real GitHub and
  Resend calls, and this path was silently broken once before (#1106), so this is
  the first evidence the notification half works rather than merely rehearses.
  Each drill issue was commented as a drill before closing, because the repo is
  public and an issue titled "expenses.brisken.com is down" should not read as a
  real outage to anyone finding it later.
- **Located the Brisken-recipient block at the SENDER** (PR #1128, `27c87f03`).
  Two live 403s: with the recipient set to the Brisken address, Resend answers
  "You can only send testing emails to your own email address"; the sender
  `onboarding@resend.dev` is Resend's shared onboarding address and owner-only by
  design. It was a module constant, so no configuration could move it. Now
  `RECON_UPTIME_RESEND_FROM` overrides it, passed from a repo variable, and the
  dry run prints who it would send as. Red-proven through the real caller
  (reverting the payload to the constant fails the new test with
  `'onboarding@resend.dev' != 'no-reply@unpauseai.com'`), restored byte-identical,
  `preflight-hooks --full` 1968 to 1969 passed.
- **Tested the unpauseai.com hypothesis in one run** rather than a code change,
  which is what the knob was for. It is not verified in this Resend account
  either. Both repo variables restored to the working default, so alerts reach the
  Gmail today and nothing is left half configured.
- **Recorded the decision and the residue** (PR #1132, `89a78d9e`) in backlog item
  123 and the status row.

## What Did NOT Work (and why)

- **Assuming the recipient was the knob.** Setting `BRIEFING_TO` to the Brisken
  address was the obvious first move and it failed: Resend's restriction is on the
  sender, not the destination. The comment at the top of the workflow had said
  "Resend's free tier delivers only to the account owner's address" since the day
  it shipped, which is true but reads as a fact about recipients, so it pointed at
  the wrong knob for a week. The 403 body names the fix explicitly.
- **`unpauseai.com` as the verified sending domain.** Plausible, since the
  platform sends transactional mail from `no-reply@unpauseai.com`, but this Resend
  account has not verified it: `The unpauseai.com domain is not verified`. That
  the platform uses the address does not mean this account can send as it.
- **Reading the GitHub account's notification address** to check whether the issue
  already reaches the Brisken inbox. The `gh` token lacks the `user` and
  `notifications` scopes, and `gh auth refresh` needs an interactive OAuth flow
  this session cannot run. Left unverified and flagged rather than guessed.

## Current Status

Item 123's scheduling question is closed by owner decision. The monitor runs, the
issue-and-mail path is proven end to end, no `recon-uptime` issue is open and the
app is up. Alerts currently land in `matneumann07@gmail.com`.

`main` at `9ea2b30f`. No ops worktrees or branches remain.

## Next Steps

1. **Getting alerts to the Brisken mailbox is now a credential question, not an
   engineering one.** Cheapest first: check whether the GitHub account's
   notification address is already the Brisken one, since the issue is the primary
   signal and GitHub mails it; that needs nothing built. Otherwise: verify a
   sending domain in Resend (free, the knob exists, but not `brisken.com`, whose
   production mail records should not be touched for a monitor), send through the
   Brisken Graph app (a tenant secret in a public repo's Actions, owner's call), or
   forward the Gmail (zero code, works today).
2. Owner note #70 still needs assigning to a session.
3. Item 125 leg 2 closes itself on the first mail arriving after Fly v187.
4. Residues unchanged: 127's per-month verdict tally, 128's reader-version stamp,
   129's per-file "matched with X" line, 125's CA certificate.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 123 carries
  the decision, the two 403s and the three remaining options)
- `docs/2026-09-20 - Brisken Recon Ops Tail Follow-Ups/Mini-Checkpoint-2.md` (the
  earlier checkpoint this one continues)
