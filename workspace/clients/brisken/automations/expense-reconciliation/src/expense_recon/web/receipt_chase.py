"""Which receipts to chase, from whom, and the mail that would ask (item 107).

Chasing receipts is the biggest thing Criss does by hand every month: she
reads the month for charges with nothing behind them, works out whose card
each one is, and mails Dirk and Nicolas herself. The tool already knows every
part of that. What it lacked was the grouping, the two states a chase
produces, and the mail.

Three pieces, in the order they are used:

1. `chase_groups` groups the month's charges that need a receipt BY CARD
   HOLDER. The membership predicate is item 99's `charge_needs_receipt`, read
   from the same rows the page renders, so the list and
   `summary.n_charges_need_receipt` cannot disagree: the sum of the groups'
   `n_charges` IS that count.
2. The two reviewer-set states, whose storage lives beside every other
   per-charge verdict (`decisions`, see `store.set_receipt_requested` /
   `set_no_receipt_expected`) and whose readiness meaning lives in
   `month_readiness`. `receipt_requested_at` records that the holder was
   asked and closes nothing; `no_receipt_expected` is a verdict that closes
   the charge, the way an already-booked one does.
3. `compose_requests` renders one plain-text mail per holder, EN and PT-BR,
   addressed from the intake address so a reply with the PDFs attached lands
   back in the tool as ordinary intake mail.

**Nothing here sends.** This module imports no mail transport and calls none:
there is no code path from a route to `graph_notify` for a request mail, by
construction rather than by a flag. The flag (`settings["receipt_requests"]
.enabled`, off by default) says whether the owner has approved the chase mail
at all; until a later build wires a guarded sender under the Brisken
send-by-id standard, `POST .../receipt-requests/send` refuses either way and
names which of the two gates it is refusing on.
"""
from __future__ import annotations

from decimal import Decimal

# `settings["receipt_requests"]`: the owner's switch plus the addresses the
# chase mail would go to. Two facts, one key, because neither is any use
# without the other: an enabled chase with no address for the holder sends
# nothing, and an address with the chase off is inert.
RECEIPT_REQUESTS_KEY = "receipt_requests"
RECEIPT_REQUESTS_DEFAULT: dict = {"enabled": False, "holders": {}}

# The two refusals `POST .../receipt-requests/send` can answer with. Both are
# refusals in this build; the second exists so turning the flag on reports
# the real remaining gate (no sender is wired) instead of silently seeming
# to work.
SEND_DISABLED = "receipt_requests_disabled"
SEND_NOT_WIRED = "receipt_send_not_wired"

# A holder with no `person` on the card. Kept as a group rather than dropped:
# "whose card is this" is exactly the question the list exists to answer, and
# a charge nobody owns is the one most likely to be forgotten.
NO_HOLDER = ""
NO_HOLDER_LABEL = "No card holder on file"

# How many charges one mail lists before it says "and N more". A holder with
# 36 open charges gets a readable mail, not a wall.
MAX_LISTED = 50


def _plain_address(value: object) -> str:
    """A single well-formed address, or "". Same structural rule as the
    intake's `_is_plain_address`: exactly one @, nothing that could smuggle a
    second recipient past a single-recipient send."""
    text = str(value or "").strip().lower()
    if (
        text.count("@") != 1
        or any(c in text for c in " \t,;<>\r\n")
        or text.startswith("@")
        or text.endswith("@")
    ):
        return ""
    return text


def normalize_receipt_requests_setting(raw: object) -> dict:
    """Validate + clean a `receipt_requests` settings payload at the PUT edge.

    Raises ValueError on a malformed shape (the settings PUT answers 400).
    Whole-object replace, the same contract as `intake`. `enabled` must be a
    real boolean: a truthy string that silently enabled an outbound chase
    would be the worst kind of tolerance."""
    if raw is None:
        return dict(RECEIPT_REQUESTS_DEFAULT)
    if not isinstance(raw, dict):
        raise ValueError("receipt_requests must be an object")
    cleaned: dict = {}
    if "enabled" in raw:
        if not isinstance(raw["enabled"], bool):
            raise ValueError("receipt_requests.enabled must be true or false")
        cleaned["enabled"] = raw["enabled"]
    else:
        cleaned["enabled"] = False
    holders_raw = raw.get("holders")
    holders: dict[str, str] = {}
    if holders_raw is not None:
        if not isinstance(holders_raw, dict):
            raise ValueError(
                "receipt_requests.holders must map a card holder's name to "
                "an e-mail address"
            )
        for person, address in holders_raw.items():
            name = str(person or "").strip()
            if not name:
                continue
            addr = _plain_address(address)
            if not addr:
                raise ValueError(
                    f"receipt_requests.holders[{name!r}] must be a single "
                    "plain e-mail address"
                )
            holders[name] = addr
    cleaned["holders"] = holders
    return cleaned


def requests_enabled(settings: dict | None) -> bool:
    raw = (settings or {}).get(RECEIPT_REQUESTS_KEY) or {}
    return bool(raw.get("enabled")) if isinstance(raw, dict) else False


def holder_addresses(settings: dict | None) -> dict[str, str]:
    """`{person: address}` as stored, malformed entries dropped rather than
    raising: a hand-edited settings blob must never break the month page."""
    raw = (settings or {}).get(RECEIPT_REQUESTS_KEY) or {}
    if not isinstance(raw, dict) or not isinstance(raw.get("holders"), dict):
        return {}
    out: dict[str, str] = {}
    for person, address in raw["holders"].items():
        name = str(person or "").strip()
        addr = _plain_address(address)
        if name and addr:
            out[name] = addr
    return out


def portal_hints(merchants: dict | None, vendors: dict[str, str]) -> dict[str, str]:
    """`{transaction_id: hint}` from the merchant registry's optional
    `receipt_portal` ("platform.openai.com", "Chase statements portal").

    `vendors` maps each charge to its statement description. Returns {} the
    moment no merchant carries a portal, without building a registry or
    resolving anything: that is the live state today, and the month payload
    must not pay for a feature nobody has filled in yet."""
    entries = {
        name: str(entry.get("receipt_portal") or "").strip()
        for name, entry in (merchants or {}).items()
        if isinstance(entry, dict) and str(entry.get("receipt_portal") or "").strip()
    }
    if not entries or not vendors:
        return {}
    from ..merchant_registry import MerchantRegistry

    registry = MerchantRegistry(merchants)
    out: dict[str, str] = {}
    for tx_id, vendor in vendors.items():
        match = registry.resolve(None, vendor)
        if match is None:
            continue
        hint = entries.get(match.canonical_name, "")
        if hint:
            out[tx_id] = hint
    return out


def chase_groups(
    rows: list[dict],
    *,
    card_info: dict[str, dict] | None = None,
    amounts: dict[str, Decimal] | None = None,
    addresses: dict[str, str] | None = None,
    hints: dict[str, str] | None = None,
) -> list[dict]:
    """The month's missing-receipt list, one group per card holder.

    `rows` are the payload's own rows; membership is item 99's
    `charge_needs_receipt`, so the groups' charges are exactly the charges
    `summary.n_charges_need_receipt` counts. `card_info` maps a row's
    `coverage_key` to `{card_key, label, person}` (the same coverage
    identity the per-card panel totals under, so a card is never split in
    two). `amounts` carries the unformatted amount per charge; a charge
    missing from it contributes nothing to the totals rather than guessing
    one. Empty list when nothing needs chasing, which is what July reads.
    """
    from .month_readiness import charge_needs_receipt

    card_info = card_info or {}
    amounts = amounts or {}
    addresses = addresses or {}
    hints = hints or {}
    groups: dict[str, dict] = {}
    for row in rows:
        if not charge_needs_receipt(row):
            continue
        key = row.get("coverage_key") or ""
        info = card_info.get(key) or {}
        person = str(info.get("person") or "").strip()
        group = groups.get(person)
        if group is None:
            group = groups[person] = {
                "holder": person,
                "holder_label": person or NO_HOLDER_LABEL,
                # None, never a guessed address: an invented recipient is the
                # one mistake a chase mail cannot take back (B4).
                "holder_address": addresses.get(person) or None,
                "cards": [],
                "n_charges": 0,
                "n_requested": 0,
                "amounts_by_ccy": {},
                "charges": [],
            }
        card_label = str(info.get("label") or key or "")
        if card_label and card_label not in [c["label"] for c in group["cards"]]:
            group["cards"].append({
                "key": key,
                "card_key": str(info.get("card_key") or ""),
                "label": card_label,
            })
        tx_id = row.get("transaction_id") or ""
        charge = {
            "transaction_id": tx_id,
            "date": row.get("date") or "",
            "vendor": row.get("vendor") or "",
            "amount": row.get("amount") or "",
            "currency": row.get("currency") or "",
            "card_key": str(info.get("card_key") or ""),
            "card_label": card_label,
            "coverage_key": key,
        }
        hint = hints.get(tx_id)
        if hint:
            charge["portal_hint"] = hint
        if row.get("receipt_requested_at"):
            charge["receipt_requested_at"] = row["receipt_requested_at"]
            group["n_requested"] += 1
        if row.get("requested_to"):
            charge["requested_to"] = row["requested_to"]
        group["charges"].append(charge)
        group["n_charges"] += 1
        amount = amounts.get(tx_id)
        ccy = charge["currency"]
        if amount is not None and ccy:
            totals = group.setdefault("_totals", {})
            totals[ccy] = totals.get(ccy, Decimal("0")) + abs(amount)
    out = []
    for group in groups.values():
        totals = group.pop("_totals", {})
        group["amounts_by_ccy"] = {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(totals.items())
        }
        group["charges"].sort(key=lambda c: (c["date"], c["vendor"], c["transaction_id"]))
        group["cards"].sort(key=lambda c: c["label"])
        out.append(group)
    # Biggest chase first, then by name: the holder with 36 open charges is
    # the one worth opening.
    out.sort(key=lambda g: (-g["n_charges"], g["holder_label"].lower()))
    return out


def _lines(group: dict, *, en: bool) -> list[str]:
    listed = group["charges"][:MAX_LISTED]
    out = []
    for c in listed:
        parts = [c["date"], c["vendor"], f"{c['currency']} {c['amount']}".strip()]
        if c.get("card_label"):
            parts.append(f"({c['card_label']})")
        if c.get("portal_hint"):
            parts.append(
                f"invoice: {c['portal_hint']}" if en
                else f"fatura: {c['portal_hint']}"
            )
        out.append("- " + "  ".join(p for p in parts if p))
    rest = group["n_charges"] - len(listed)
    if rest > 0:
        out.append(
            f"- and {rest} more, all listed in the tool." if en
            else f"- e mais {rest}, todos listados na ferramenta."
        )
    return out


def compose_request(
    group: dict, *, month_label: str, intake_address: str
) -> dict:
    """One holder's request mail, EN and PT-BR, composed and not sent.

    `to` is None when no address is on file for the holder, and the mail
    carries `blocked: "no_address"` so the page can say which holder is
    unreachable rather than the send quietly skipping them."""
    n = group["n_charges"]
    subject = f"{month_label}: {n} receipt{'s' if n != 1 else ''} still missing"
    subject_pt = f"{month_label}: {n} recibo{'s' if n != 1 else ''} ainda faltando"
    charge_word = "charges" if n != 1 else "charge"
    body = "\n".join([
        f"{n} {charge_word} on your card in {month_label} have no receipt in "
        "the expense tool yet:",
        "",
        *_lines(group, en=True),
        "",
        "Reply to this email with the PDFs attached and they land in the "
        "month directly. If a charge will never have a receipt, say which "
        "one and why, and Criss marks it as not expected.",
        "",
        intake_address,
    ])
    body_pt = "\n".join([
        f"{n} lançamento{'s' if n != 1 else ''} do seu cartão em "
        f"{month_label} ainda está sem recibo na ferramenta:",
        "",
        *_lines(group, en=False),
        "",
        "Responda a este e-mail com os PDFs anexados; eles entram direto no "
        "mês. Se algum lançamento nunca terá recibo, diga qual e por quê, e "
        "a Criss marca como não esperado.",
        "",
        intake_address,
    ])
    mail = {
        "holder": group["holder"],
        "holder_label": group["holder_label"],
        "to": group.get("holder_address"),
        # The reply has to land in the intake mailbox for the loop to close,
        # so both the sender and the reply-to are the intake address. Graph
        # sends as matthias.silva today, which is why a future sender has to
        # set Reply-To explicitly rather than inherit it.
        "from_address": intake_address,
        "reply_to": intake_address,
        "n_charges": n,
        "subject": subject,
        "body": body,
        "subject_pt": subject_pt,
        "body_pt": body_pt,
    }
    if not mail["to"]:
        mail["blocked"] = "no_address"
    return mail


def compose_requests(
    groups: list[dict], *, month_label: str, intake_address: str
) -> list[dict]:
    return [
        compose_request(g, month_label=month_label, intake_address=intake_address)
        for g in groups
    ]
