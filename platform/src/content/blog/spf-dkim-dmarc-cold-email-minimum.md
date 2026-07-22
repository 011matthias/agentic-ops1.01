---
title: "SPF, DKIM, DMARC for Cold Email: The Minimum That Actually Passes"
slug: spf-dkim-dmarc-cold-email-minimum
date: "2026-07-22"
category: Technical
excerpt: "The three DNS records every sending domain needs, the minimal working values, the setup order that avoids rework, and when to tighten DMARC from monitoring to enforcement."
---

Three DNS records decide whether your cold email is even considered for the inbox: SPF says which servers may send for your domain, DKIM cryptographically signs each message, and DMARC tells receivers what to do when the first two fail. The minimal working setup is one SPF record with your provider's include, a 2048-bit DKIM key with signing enabled, and DMARC in monitoring mode while the domain warms up.

Major mailbox providers require authentication from bulk senders outright; without these records the copy in your emails never gets a vote.

## The three records

| Record | What it proves | Minimal working value (Google Workspace) | Common mistake |
|---|---|---|---|
| SPF | This server is allowed to send for the domain | TXT at root: `v=spf1 include:_spf.google.com ~all` | Two SPF records on one domain, which is invalid and fails both |
| DKIM | The message is signed by the domain and unaltered | 2048-bit key published at `google._domainkey`, signing turned ON in admin | Publishing the key but never enabling signing, so mail goes out unsigned |
| DMARC | What receivers should do on failure, and where to report | TXT at `_dmarc`: `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` | Jumping to `p=reject` on day one and losing legitimate mail |

Values above are for Google Workspace senders; other providers swap the include and the DKIM selector, the structure stays identical.

## The setup order that avoids rework

DKIM keys are generated inside your mailbox provider, which means the mailboxes must exist before the DNS work can finish. The order:

1. Add the domain to your mailbox provider and verify ownership.
2. Create the mailboxes.
3. Publish MX records so the domain receives mail.
4. Publish SPF.
5. Generate the DKIM key in the provider's admin, publish the TXT record, then enable signing.
6. Publish DMARC with `p=none` and a reporting address you actually read.
7. Verify everything before connecting the domain to any sending tool.

Doing DNS first and mailboxes later means coming back for DKIM anyway; this order is one pass.

## Verifying it actually passes

Records existing is not the same as authentication passing. Send a message from each new mailbox to an inbox you own and open the message source (in Gmail: "show original"). You want to see `spf=pass`, `dkim=pass`, and `dmarc=pass` on your sending domain, not on a provider domain. Free checkup tools (Google Admin Toolbox, any DMARC record checker) catch syntax errors, but the show-original check on a real delivered message is the one that proves the chain end to end.

## When to tighten DMARC

`p=none` is a listening post: mail flows normally and the reports sent to your `rua` address show who is sending as your domain and whether alignment holds. After the domain has a few clean weeks behind it, move to `p=quarantine` so that mail failing authentication lands in spam instead of the inbox. `p=reject` is the end state for a mature domain, but reaching for it during warm-up turns configuration mistakes into silently vanished mail.

## Cold-email specifics

Two structural rules sit on top of the records themselves.

**Never cold-send from your primary domain.** Outreach happens from separate look-alike sending domains, each carrying its own SPF, DKIM, and DMARC, each redirecting to the main site. Reputation damage on a sending domain is a replaceable loss; on your primary domain it follows every invoice and support email you send.

**Authentication does not replace warm-up.** A fully authenticated fresh domain is still a fresh domain. Providers score sending history, and new domains earn inbox placement over weeks of gradually increasing, human-paced volume. The records are the entry ticket; warm-up is the queue.
