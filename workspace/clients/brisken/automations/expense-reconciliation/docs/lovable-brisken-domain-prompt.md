# Lovable prompt: move the app onto Brisken's own domain

Written 2026-09-08. Two halves: a **settings change** the owner makes in
the Lovable project (no prompt needed), and a **paste** that switches the
API base URL. Do the settings half first; the paste alone would point the
old lovable.app front end at the new API, which works but leaves the
vendor name in the address bar.

## Why

Criss opens `brisken-reconcile-dash.lovable.app` and the receipts and
downloads inside it come from `brisken-expense-recon.fly.dev`. Neither
name is Brisken's. After this change the app is
`expenses.brisken.com` and its API is `api.expenses.brisken.com`, which
is also the domain receipts are already mailed to.

## Half 1: the custom domain (owner, in Lovable)

In the `brisken-reconcile-dash` project: Settings, then Domains, then
add `expenses.brisken.com`. Lovable answers with a verification value
that looks like `lovable_verify=<hex>`.

Send that value over; the DNS records are published from here (GoDaddy
API), matching the five Brisken sites Lovable already serves:

- `A` `expenses` to `185.158.133.1`
- `TXT` `_lovable.expenses` to `lovable_verify=<hex>`

The existing `MX expenses -> mx.expenses.brisken.com` record stays
untouched, so mailed receipts keep arriving. An A record and an MX
record on one name do not conflict; a CNAME would, which is why the A
form is the one to pick if Lovable offers a choice.

The backend already accepts this origin (CORS allow-list, PR #751).

## Half 2: the API base URL (paste into Lovable)

> The API has moved to its own Brisken hostname. Replace every use of
> `https://brisken-expense-recon.fly.dev` with
> `https://api.expenses.brisken.com`. It is the same server with the
> same routes, auth and payloads; only the hostname changes. Check the
> API client module, any hardcoded fetch URLs, environment/config
> constants, and any place a receipt image or CSV download URL is built,
> so no screen still points at the old host. Do not change any request
> path, header or body.

## Verifying the paste landed

Fetch the published bundle and grep the chunks for
`api.expenses.brisken.com` (present) and `brisken-expense-recon.fly.dev`
(absent). The old host keeps working either way, so a half-applied
change shows up as a mix rather than a broken page: grep for both, not
just the new one.

Then drive it cold: open `https://expenses.brisken.com` in a fresh
profile, sign in with the operator code, open a month, and confirm a
receipt image renders (that is the request most likely to still carry a
hardcoded host).
