"""All Outlook COM in one place, ported from the proven Brisken scripts.

Patterns carried over verbatim (hard-won, do not "simplify"):
  * account resolution by SmtpAddress over Session.Accounts
    (send-rome-campaign.ps1) - a missing account is a config abort;
  * auto-send: CreateItem(0) in OUR store, Recipients.Add + ResolveAll
    before .Send() (draft-loader lesson: never send unresolved), sender
    pinned via SendUsingAccount;
  * Dirk drafts: Items.Add("IPM.Note") DIRECTLY in his Drafts folder (NOT
    CreateItem+Save which mis-files into Matthias's store), folder-ownership
    verify, dupe guard, sync round-trip (brisken-dirk-draft-loader.py);
  * inbox polling with Items.Restrict on a receive-time window
    (brisken-website-inquiries.py);
  * internetMessageId via PropertyAccessor proptag 0x1035001F; SMTP of an
    EX-type sender via GetExchangeUser().PrimarySmtpAddress.

Everything COM-touching guards its win32com import so the module still
imports on CI/Linux; the pure mapping helpers (NDR detection, address
extraction) live here too so tests can drive them with fake objects.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from ..graph_mail import _norm_subject

OL_MAIL_ITEM = 0
OL_FOLDER_INBOX = 6
OL_FOLDER_DRAFTS = 16
OL_FOLDER_SENT = 5
OL_TO, OL_CC, OL_BCC = 1, 2, 3
PR_INTERNET_MESSAGE_ID = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"
PR_SMTP = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_BOUNCE_SUBJECT_RE = re.compile(
    r"undeliverable|delivery (has )?failed|delivery status notification"
    r"|mail delivery failed|returned mail|failure notice", re.I)


# -- pure helpers (unit-testable without COM) -----------------------------------

def is_bounce(message_class: str | None, subject: str | None) -> bool:
    mc = (message_class or "").upper()
    if mc.startswith("REPORT.IPM.NOTE.NDR"):
        return True
    return bool(_BOUNCE_SUBJECT_RE.search(subject or ""))


def extract_bounced_addresses(body: str | None, watch: set[str]) -> list[str]:
    """Failed recipients from an NDR body: every watched address mentioned."""
    found = {m.group(0).lower() for m in _EMAIL_RE.finditer(body or "")}
    return sorted(a for a in found if a in watch)


def reply_payload(sender: str, subject: str | None, ts_iso: str,
                  imid: str | None, body_head: str | None = None) -> dict:
    return {"email": sender, "type": "reply", "direction": "inbound",
            "channel": "email", "occurred_at": ts_iso,
            "subject": subject or None,
            "detail": (body_head or "")[:400] or None,
            "source": "worker-auto",
            "internet_message_id": imid or None}


def bounce_payload(failed_addr: str, subject: str | None, ts_iso: str,
                   imid: str | None) -> dict:
    return {"email": failed_addr, "type": "bounce", "direction": "inbound",
            "channel": "email", "occurred_at": ts_iso,
            "subject": subject or None,
            "detail": "NDR / delivery failure", "source": "worker-auto",
            "internet_message_id": (imid or None) and f"{imid}#{failed_addr}"}


def match_drafted(sent_items: list[dict], drafted: list[dict]) -> list[dict]:
    """Correlate Dirk's actually-sent mail with 'drafted' attempts by
    (recipient, subject). Subjects compare via _norm_subject (a superset of
    the old exact match) so a staged reply step whose sent copy gained a
    'RE: ' prefix still completes. Returns draft-sent confirmations."""
    out = []
    for d in drafted:
        want_to = (d.get("to") or "").lower()
        want_subj = _norm_subject(d.get("subject") or "")
        for m in sent_items:
            if want_subj and _norm_subject(m.get("subject", "")) == want_subj and \
                    want_to and want_to in [a.lower() for a in m.get("to_addrs", [])]:
                out.append({"attempt_key": d["attempt_key"],
                            "occurred_at": m.get("ts"),
                            "internet_message_id": m.get("imid")})
                break
    return out


# -- COM layer --------------------------------------------------------------------

def get_outlook():
    import win32com.client
    ol = win32com.client.Dispatch("Outlook.Application")
    ol.GetNamespace("MAPI")
    return ol


def resolve_account(ol, smtp: str):
    smtp_l = smtp.lower()
    for acct in ol.Session.Accounts:
        if (acct.SmtpAddress or "").lower() == smtp_l:
            return acct
    return None


def _prop(item, tag: str) -> str | None:
    try:
        return item.PropertyAccessor.GetProperty(tag)
    except Exception:
        return None


def smtp_of(item) -> str | None:
    try:
        if (item.SenderEmailType or "") == "EX":
            exu = item.Sender.GetExchangeUser()
            if exu is not None:
                return (exu.PrimarySmtpAddress or "").lower() or None
        return (item.SenderEmailAddress or "").lower() or None
    except Exception:
        return None


def _com_time(dt: datetime) -> str:
    # Outlook Restrict wants US-style local time.
    return dt.strftime("%m/%d/%Y %I:%M %p")


def send_auto(ol, acct, send: dict) -> None:
    """Fire one auto-send from our account. Raises on unresolved recipients
    (caller nacks 'resolve'). The .Send() call is the irreversible moment -
    the caller journals com_issued IMMEDIATELY before calling this."""
    mail = ol.CreateItem(OL_MAIL_ITEM)
    mail.Recipients.Add(send["to"]).Type = OL_TO
    for addr in send.get("cc") or []:
        mail.Recipients.Add(addr).Type = OL_CC
    for addr in send.get("bcc") or []:
        mail.Recipients.Add(addr).Type = OL_BCC
    mail.Subject = send["subject"]
    mail.Body = send["body"]
    try:
        mail.SendUsingAccount = acct
    except Exception:
        pass
    mail.Recipients.ResolveAll()
    bad = [r.Name for r in mail.Recipients if not r.Resolved]
    if bad:
        raise UnresolvedRecipients(bad)
    mail.Send()


class UnresolvedRecipients(RuntimeError):
    def __init__(self, names: list[str]):
        super().__init__(f"unresolved recipients: {names}")
        self.names = names


def readback_sent(acct, to_addr: str, subject: str,
                  since: datetime, budget_seconds: int = 60) -> dict | None:
    """Find the just-sent mail in the account's Sent Items and return
    {imid, entry_id, ts}. Non-fatal on miss (the deterministic attempt_key is
    the idempotency anchor; imid is enrichment)."""
    import time as _time
    sent = acct.DeliveryStore.GetDefaultFolder(OL_FOLDER_SENT)
    deadline = _time.time() + budget_seconds
    want_to = to_addr.lower()
    while _time.time() < deadline:
        try:
            items = sent.Items.Restrict(f"[SentOn] >= '{_com_time(since)}'")
            items.Sort("[SentOn]", True)
            for it in items:
                try:
                    if (it.Subject or "").strip() != subject.strip():
                        continue
                    addrs = []
                    for r in it.Recipients:
                        addrs.append((_prop(r, PR_SMTP) or getattr(r, "Address", "") or "").lower())
                    if any(want_to in a for a in addrs):
                        return {"imid": _prop(it, PR_INTERNET_MESSAGE_ID),
                                "entry_id": getattr(it, "EntryID", None),
                                "ts": _iso(getattr(it, "SentOn", None))}
                except Exception:
                    continue
        except Exception:
            pass
        _time.sleep(5)
    return None


def load_dirk_draft(ol, dirk_acct, send: dict) -> dict:
    """Stage one fully-resolved draft in Dirk's Drafts (draft-dirk mode).
    Verbatim port of brisken-dirk-draft-loader.py: Items.Add on HIS folder,
    dupe guard, ResolveAll, folder-ownership verify, sync round-trip."""
    drafts = dirk_acct.DeliveryStore.GetDefaultFolder(OL_FOLDER_DRAFTS)
    owner = (drafts.Store.DisplayName or "").lower()
    if owner != (dirk_acct.SmtpAddress or "").lower():
        raise RuntimeError(f"Drafts store owner is {owner!r}; refusing to load")
    want = ((send["subject"] or "").strip(), send["to"].lower())
    for it in drafts.Items:
        try:
            if (it.Subject or "").strip() == want[0] and \
                    want[1] in (it.To or "").lower():
                return {"duplicate": True, "entry_id": getattr(it, "EntryID", None)}
        except Exception:
            continue
    item = drafts.Items.Add("IPM.Note")
    item.Recipients.Add(send["to"]).Type = OL_TO
    for addr in send.get("cc") or []:
        item.Recipients.Add(addr).Type = OL_CC
    for addr in send.get("bcc") or []:
        item.Recipients.Add(addr).Type = OL_BCC
    item.Subject = send["subject"]
    item.Body = send["body"]
    try:
        item.SendUsingAccount = dirk_acct
    except Exception:
        pass
    item.Recipients.ResolveAll()
    bad = [r.Name for r in item.Recipients if not r.Resolved]
    item.Save()
    post_owner = ""
    try:
        post_owner = (item.Parent.Store.DisplayName or "").lower()
    except Exception:
        pass
    if post_owner != (dirk_acct.SmtpAddress or "").lower():
        raise RuntimeError(f"draft mis-filed into {post_owner!r}")
    _sync(ol.Session)
    return {"duplicate": False, "entry_id": getattr(item, "EntryID", None),
            "unresolved": bad}


def _sync(session) -> None:
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


def _iso(com_dt) -> str | None:
    if com_dt is None:
        return None
    try:
        return datetime(com_dt.year, com_dt.month, com_dt.day, com_dt.hour,
                        com_dt.minute, com_dt.second).astimezone().isoformat(
                            timespec="seconds")
    except Exception:
        return None


def poll_inbox(acct, since: datetime) -> list[dict]:
    """Inbound items since the watermark -> plain dicts (COM-free downstream)."""
    inbox = acct.DeliveryStore.GetDefaultFolder(OL_FOLDER_INBOX)
    out = []
    try:
        items = inbox.Items.Restrict(f"[ReceivedTime] >= '{_com_time(since)}'")
        items.Sort("[ReceivedTime]", True)
    except Exception:
        return out
    for it in items:
        try:
            out.append({
                "message_class": getattr(it, "MessageClass", "") or "",
                "subject": (getattr(it, "Subject", "") or ""),
                "sender": smtp_of(it),
                "ts": _iso(getattr(it, "ReceivedTime", None)),
                "imid": _prop(it, PR_INTERNET_MESSAGE_ID),
                "body_head": (getattr(it, "Body", "") or "")[:2000],
            })
        except Exception:
            continue
    return out


def poll_sent(acct, since: datetime) -> list[dict]:
    """Sent items since the watermark (drafted-attempt correlation)."""
    sent = acct.DeliveryStore.GetDefaultFolder(OL_FOLDER_SENT)
    out = []
    try:
        items = sent.Items.Restrict(f"[SentOn] >= '{_com_time(since)}'")
        items.Sort("[SentOn]", True)
    except Exception:
        return out
    for it in items:
        try:
            addrs = []
            for r in it.Recipients:
                addrs.append((_prop(r, PR_SMTP) or getattr(r, "Address", "") or "").lower())
            out.append({
                "subject": (getattr(it, "Subject", "") or ""),
                "to_addrs": addrs,
                "ts": _iso(getattr(it, "SentOn", None)),
                "imid": _prop(it, PR_INTERNET_MESSAGE_ID),
            })
        except Exception:
            continue
    return out


def search_sent_for(acct, to_addr: str, subject: str,
                    since: datetime) -> dict | None:
    """Crash-reconcile evidence search: was this mail actually sent?"""
    for m in poll_sent(acct, since):
        if m["subject"].strip() == subject.strip() and \
                any(to_addr.lower() in a for a in m["to_addrs"]):
            return m
    return None


def default_since(days: int = 3) -> datetime:
    return datetime.now() - timedelta(days=days)
