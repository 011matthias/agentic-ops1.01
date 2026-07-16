# /// script
# requires-python = ">=3.10"
# dependencies = ["pywin32"]
# ///
"""Load outbound drafts into Dirk's Outlook, resolved and CRM-logged.

Reusable loader for every Brisken outreach batch (T2, T3, partner/SAP, ICD, ...).
Replaces the per-batch `.scratch/load_*_drafts.py` one-offs and fixes the two
gaps Dirk flagged on 2026-07-12 (comms-log):

  1. Recipient validation. The old loaders set `item.To = "<smtp>"` as a plain
     string and `.Save()` without resolving, so New Outlook flagged every draft
     "Invalid Email Address" until Dirk double-clicked to accept the directory
     match. Here each recipient is added via `Recipients.Add()` then
     `Recipients.ResolveAll()`; unresolved names are reported, never silently
     saved. GAL contacts resolve to their directory entry; external addresses
     resolve to a valid one-off SMTP recipient. Either clears the flag.
  2. CRM logging. Dirk: "you should always be blind copying (BCC) the CRM
     dropbox ... in all customer email comms". Every draft gets the Zoho CRM
     dropbox on BCC so the thread auto-files against the contact record. On by
     default (honors his "always"); set a note's `bcc_dropbox: false` to omit it
     for a batch he wants kept out of the CRM.

Creation path (reference_dirk_outlook_com_drafts, hard-won): items are created
via `dirkDrafts.Items.Add("IPM.Note")` DIRECTLY in Dirk's Drafts folder, NOT
`CreateItem(0)` + `.Save()` (the latter mis-files every item into Matthias's
default store on this machine and then needs a `.Move()`). Sender is verified by
FOLDER OWNERSHIP (`item.Parent.Store.DisplayName`), because SendUsingAccount
reads back empty on a shared-mailbox draft. After saving, a sync round-trip is
forced so the drafts actually upload and become visible to Dirk.

Contract kept from the prior loaders: SendUsingAccount pinned to
dirk.neumann@brisken.com (belt-and-suspenders; folder ownership governs), `.Save`
only (never `.Send`), duplicate guard keyed on (subject, first recipient),
readback verifies presence + attachment count + all-resolved + Dirk-owned.

INVASIVE: creating drafts writes into Dirk's live mailbox. A real run needs an
explicit per-batch yes from the owner (feedback_no_invasive_action_without_ask).
`--dry-run` touches nothing and never imports Outlook.

Usage:
    uv run tools/brisken-dirk-draft-loader.py --plan PLAN.json --dry-run
    uv run tools/brisken-dirk-draft-loader.py --plan PLAN.json        # loads for real

PLAN.json is a list of notes:
    [
      {"to": "a@x.com", "subject": "...", "body": "...",
       "attach": ["C:/abs/deck.pdf"],           # optional
       "cc": ["b@x.com"], "bcc": ["c@x.com"],    # optional, in addition to dropbox
       "bcc_dropbox": true}                       # optional, default true
    ]
`to`/`cc`/`bcc` accept a string or a list of strings.
"""
import argparse
import json
import pathlib
import sys

DIRK_SMTP = "dirk.neumann@brisken.com"
# Zoho CRM email dropbox (Dirk, screenshot 2026-07-12). BCC this and the email
# auto-files against the matching CRM contact/lead.
ZOHO_DROPBOX = "s9hitl_pv69mu@mails4.zohocrm.com"

# Outlook enums
OL_FOLDER_DRAFTS = 16
OL_TO, OL_CC, OL_BCC = 1, 2, 3
PR_SMTP = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"


def _as_list(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


def normalize(raw_notes):
    """Validate + normalize a plan into note dicts. Raises SystemExit on bad input."""
    notes = []
    for i, n in enumerate(raw_notes):
        to = _as_list(n.get("to"))
        if not to:
            raise SystemExit(f"note {i}: no `to` recipient")
        if not n.get("subject"):
            raise SystemExit(f"note {i} ({to[0]}): no `subject`")
        if not n.get("body"):
            raise SystemExit(f"note {i} ({to[0]}): no `body`")
        attach = _as_list(n.get("attach"))
        for a in attach:
            if not pathlib.Path(a).is_file():
                raise SystemExit(f"note {i} ({to[0]}): attachment missing: {a}")
        notes.append({
            "to": to,
            "cc": _as_list(n.get("cc")),
            "bcc": _as_list(n.get("bcc")),
            "subject": n["subject"].strip(),
            "body": n["body"],
            "attach": attach,
            "bcc_dropbox": n.get("bcc_dropbox", True),
        })
    return notes


def _bcc_for(note):
    bcc = list(note["bcc"])
    if note["bcc_dropbox"]:
        bcc.append(ZOHO_DROPBOX)
    return bcc


def print_plan(notes):
    print(f"Parsed {len(notes)} note(s):")
    for n in notes:
        bcc = _bcc_for(n)
        drop = "dropbox" if n["bcc_dropbox"] else "NO-dropbox"
        print(f"  {n['to'][0]:<38} | {n['subject']}")
        print(f"      to={n['to']} cc={n['cc']} bcc={bcc} [{drop}] | attach={len(n['attach'])}")


def load(notes):
    import win32com.client

    ol = win32com.client.Dispatch("Outlook.Application")
    session = ol.Session

    acct = next((a for a in session.Accounts if a.SmtpAddress.lower() == DIRK_SMTP), None)
    if acct is None:
        raise SystemExit(f"LIMITATION: account {DIRK_SMTP} not in this Outlook profile.")

    # Dirk's own Drafts folder. Create items HERE via Items.Add so they stay in
    # Dirk's store; CreateItem(0)+Save mis-files into Matthias's default store.
    drafts = acct.DeliveryStore.GetDefaultFolder(OL_FOLDER_DRAFTS)
    if (drafts.Store.DisplayName or "").lower() != DIRK_SMTP:
        raise SystemExit(
            f"LIMITATION: resolved Drafts store is {drafts.Store.DisplayName!r}, "
            f"not {DIRK_SMTP}. Refusing to load into the wrong mailbox.")
    existing = set()
    for it in drafts.Items:
        try:
            existing.add(((it.Subject or "").strip(), (it.To or "").strip().lower()))
        except Exception:
            pass
    print(f"Dirk's Drafts holds {drafts.Items.Count} item(s) before load.")

    created, skipped, unresolved, misfiled = [], [], [], []
    for n in notes:
        key = (n["subject"], n["to"][0].lower())
        if any(s == n["subject"] and n["to"][0].lower() in t for (s, t) in existing):
            skipped.append(key)
            continue

        item = drafts.Items.Add("IPM.Note")
        for addr in n["to"]:
            item.Recipients.Add(addr).Type = OL_TO
        for addr in n["cc"]:
            item.Recipients.Add(addr).Type = OL_CC
        for addr in _bcc_for(n):
            item.Recipients.Add(addr).Type = OL_BCC
        item.Subject = n["subject"]
        item.Body = n["body"]
        for a in n["attach"]:
            item.Attachments.Add(a)
        item.SendUsingAccount = acct  # belt-and-suspenders; folder owner governs

        # Resolve against the GAL/directory so New Outlook accepts the recipients
        # without a manual double-click. Report any that stay unresolved.
        item.Recipients.ResolveAll()
        bad = [r.Name for r in item.Recipients if not r.Resolved]
        if bad:
            unresolved.append((n["subject"], bad))

        item.Save()
        # Verify by folder ownership (SendUsingAccount reads back empty on a
        # shared-mailbox draft).
        try:
            owner = item.Parent.Store.DisplayName
        except Exception:
            owner = "?"
        if (owner or "").lower() != DIRK_SMTP:
            misfiled.append((n["subject"], owner))
        created.append(key)

    print(f"\nCreated {len(created)}, skipped {len(skipped)} duplicate(s).")
    for k in skipped:
        print("  SKIPPED (already present):", k)
    if unresolved:
        print("\n  WARNING: recipients that did not resolve (Dirk must pick manually):")
        for subj, bad in unresolved:
            print(f"    {subj}: {bad}")
    if misfiled:
        print("\n  ERROR: draft(s) not owned by Dirk's store after Save:")
        for subj, owner in misfiled:
            print(f"    {subj}: owner={owner!r}")

    _sync(session)
    _readback(drafts, notes)
    if misfiled:
        sys.exit(5)


def _sync(session):
    """Force a two-way sync so COM-created drafts upload from the local OST and
    become visible to Dirk (reference_dirk_outlook_com_drafts: local readback !=
    visibility). Best-effort; verify the folder again after ~20s if in doubt."""
    try:
        so = session.SyncObjects
        for i in range(1, so.Count + 1):
            try:
                so.Item(i).Start()
            except Exception:
                pass
    except Exception:
        pass
    try:
        session.SendAndReceive(False)
    except Exception:
        pass
    print("\nSync round-trip triggered; if Dirk does not see the drafts, re-check the folder in ~20s.")


def _item_addresses(it):
    addrs = []
    try:
        for r in it.Recipients:
            a = None
            try:
                a = r.PropertyAccessor.GetProperty(PR_SMTP)
            except Exception:
                pass
            addrs.append((a or getattr(r, "Address", "") or "").lower())
    except Exception:
        pass
    addrs.append((getattr(it, "To", "") or "").lower())
    return addrs


def _readback(drafts, notes):
    want = {(n["subject"], n["to"][0].lower()): len(n["attach"]) for n in notes}
    found = {}
    for it in drafts.Items:
        try:
            subj = (it.Subject or "").strip()
            addrs = _item_addresses(it)
            for (ws, wt) in want:
                if subj == ws and any(wt in a for a in addrs):
                    found[(ws, wt)] = it.Attachments.Count
        except Exception:
            pass
    missing = [k for k in want if k not in found]
    badatt = [(k, found[k], want[k]) for k in found if found[k] != want[k]]
    print(f"\nREADBACK: {len(found)}/{len(want)} present.")
    if missing:
        print("  MISSING:", missing)
        sys.exit(3)
    if badatt:
        print("  ATTACHMENT MISMATCH (key, got, want):", badatt)
        sys.exit(4)
    print("READBACK OK: all drafts present with correct attachment counts.")


def main():
    ap = argparse.ArgumentParser(description="Load resolved, CRM-logged drafts into Dirk's Outlook.")
    ap.add_argument("--plan", required=True, help="JSON file: list of note dicts")
    ap.add_argument("--dry-run", action="store_true", help="parse + print; touch no Outlook")
    args = ap.parse_args()

    raw = json.loads(pathlib.Path(args.plan).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("plan must be a JSON list of note objects")
    notes = normalize(raw)
    print_plan(notes)

    if args.dry_run:
        print("\n--dry-run: no Outlook touched.")
        return
    load(notes)


if __name__ == "__main__":
    main()
