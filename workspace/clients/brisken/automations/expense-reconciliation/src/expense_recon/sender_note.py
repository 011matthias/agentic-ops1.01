"""What the sender's own note says about a receipt (item 250).

Above a forwarded receipt Dirk and Criss type the filing instruction: "BTS
only", "CorpServ only / IT costs", "BCS / Verve.Works", "CorpServ - split /
IT subscriptions". Item 155 carried that text to the row for a human to read.
Owner rulings of 2026-10-07 make it classify:

1. A note from one of our own senders that names ONE company sets the
   receipt's company, over the paying card. Only the reviewer's own pick on
   the row beats it (`service.resolve_batch_row_cards`).
2. A note that says the cost is split books it WHOLE in Corporate Services,
   on one of its own accounts that Zoho never allocates onward
   (`CORPSERV_UNSPLIT_CODES`). The tool still never splits a charge.
3. A note whose words name one account of that company's chart decides the
   account (`categorize`, source NOTE); anything less clear decides nothing
   and the receipt runs the normal chain.

What it never does: a note from a stranger, or from a mail that carried
agent-directed text, is filtered out before it reaches here
(`intake_mail.trusted_sender_notes`), and nothing a note decides is learned
at Publish, because the 2026-09-24 ruling lets memory learn corrections only
and a note is not one (it lives on the receipt, never in the override
tables the learners read).

This module is pure: it reads text and stamps receipts. Trust is the web
layer's job; it knows who our senders are.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from .matching.types import Receipt

# The three curated companies, by Zoho org, under the label the rest of the
# app holds for them (the card registry's `entity`, the provisioning file,
# `entity_options`). The short names are the curated chart's own tab names
# (`curated_leaves` ORG_TABS: BCS / BTS / CorpServ); BTS is Consulting LLC,
# not the TEST-BTS sandbox.
CLOUD_SERVICES = "Cloud Services"
CONSULTING = "Consulting"
CORPORATE_SERVICES = "Corporate Services"
COMPANY_ORGS = {
    CLOUD_SERVICES: "697686691",
    CONSULTING: "808232536",
    CORPORATE_SERVICES: "822741658",
}

# How the notes name them. Measured on the 72 live notes (2026-10-07): "BCS",
# "BTS", "CorpServ", "Corpserv", "Corp Serv", "CORP SERV". "BTA" (one note)
# maps to nothing on purpose: it is a typo for BTS or for nothing, and a
# guess here would move a receipt between companies. A bare "Consulting" is
# left out too: it is also an account word ("Technical and Business
# Consulting").
_COMPANY_PATTERNS = (
    (re.compile(r"\bBCS\b", re.I), CLOUD_SERVICES),
    (re.compile(r"\bcloud\s+services\b", re.I), CLOUD_SERVICES),
    (re.compile(r"\bBTS\b", re.I), CONSULTING),
    (re.compile(r"\bbrisken\s+consulting\b", re.I), CONSULTING),
    (re.compile(r"\bcorp\s*serv(?:ices?)?\b", re.I), CORPORATE_SERVICES),
    (re.compile(r"\bcorporate\s+services\b", re.I), CORPORATE_SERVICES),
)
_SPLIT = re.compile(r"\bsplit\b|\bshared\b|\b50\s*/\s*50\b", re.I)

# Corporate Services' own accounts: Allocation Rule "N/A" on Dirk's marked
# chart (`CoA BRISKEN BCS BTS CorpServ 260923.xlsx`, CorpServ tab, Expense
# Relevant = Y). Everything else he marked in that chart carries an
# allocation (50/50, by users, or 100% to one company) and Zoho moves it on.
# Owner 2026-10-07: a split note books here, "own account, never split".
# `E100020-30 Technical and Business Consulting` is NOT here: its rule sends
# 100% to Cloud Services. Parents are listed for completeness; the model is
# never offered one.
CORPSERV_UNSPLIT_CODES = frozenset({
    "E100000", "E100010", "E100010-01", "E100010-06", "E100010-26",
    "E100010-31", "E100020", "E100020-10", "E100020-20", "E100020-41",
    "E100020-80", "E100020-90", "E300000-60", "E300000-70", "E900010",
})

# Words that carry no account meaning once the company names are gone: a
# note that is only these ("BTS only", "CorpServ - split", "FYI") asks no
# account question, so no model call is spent on it.
_FILLER = frozenset({
    "only", "split", "shared", "fyi", "the", "this", "that", "is", "it",
    "for", "and", "to", "in", "of", "on", "so", "be", "booked", "between",
    "all", "these", "charges", "charge", "are", "please", "pls", "thanks",
    "thank", "you", "receipt", "invoice",
})
_WORD = re.compile(r"[A-Za-zÀ-ÿ]{2,}")


@dataclass(frozen=True)
class NoteReading:
    """What a note says about the company. `company` is the label the note
    decides ("" when it decides none); `companies` every company it names;
    `split` whether it says the cost is shared."""

    company: str
    companies: tuple[str, ...]
    split: bool


def read_companies(note: str) -> NoteReading:
    """The company a note decides.

    Split wins: a note that says split books in Corporate Services whatever
    else it names (every live split note names CorpServ anyway). Otherwise
    exactly one named company decides; two or more without "split" decide
    nothing, because the note itself is ambiguous."""
    text = note or ""
    named: list[str] = []
    for pattern, company in _COMPANY_PATTERNS:
        if pattern.search(text) and company not in named:
            named.append(company)
    split = bool(_SPLIT.search(text))
    if split:
        company = CORPORATE_SERVICES
    elif len(named) == 1:
        company = named[0]
    else:
        company = ""
    return NoteReading(company=company, companies=tuple(named), split=split)


def account_hint(note: str) -> str:
    """The part of a note that could name an account, or "" when nothing is
    left once company names and filler are gone ("BTS only" asks nothing).
    Only decides whether a model call is worth making; the model reads the
    whole note."""
    text = note or ""
    for pattern, _company in _COMPANY_PATTERNS:
        text = pattern.sub(" ", text)
    text = _SPLIT.sub(" ", text)
    words = [w for w in _WORD.findall(text) if w.lower() not in _FILLER]
    return " ".join(words)


# Item 254: words an account name shares with almost every other account, so
# a note matching only these names nothing.
_ACCOUNT_GENERIC = frozenset({
    "expense", "expenses", "cost", "costs", "other", "others", "and", "for",
    "the", "of", "business", "cogs", "corpserv", "ms", "opex", "opeex",
})
_IT_WORD = re.compile(r"\bI[Tt]\b")


def _account_words(text: str) -> set[str]:
    words = set()
    for w in _WORD.findall(text or ""):
        low = w.lower()
        if low in _ACCOUNT_GENERIC or low == "it":
            continue
        words.add(low[:-1] if len(low) > 3 and low.endswith("s") else low)
    return words


def names_account(note: str, account: str) -> bool:
    """Whether the note's own words name the account: one meaningful word in
    common between what is left of the note once company names are gone and
    the account's name ("IT costs" names "CorpServ | IT Expenses", "Marketing"
    names "Marketing Expenses - others", "Travel" names "CorpServ | Travel
    Expense | Transportation").

    Item 254 (2026-10-07). Item 250's "decide when clear" trusted the model's
    confidence alone, and the dry runs of item 252 showed it deciding accounts
    from notes that name no kind of cost: "Nicolas/Lydar" became a travel
    account, three "BCS only / Verve.Works" Railway receipts (a hosting
    company) became conference train travel. The model's answer now decides
    only when this lexical check agrees; otherwise the receipt runs the usual
    chain. "IT" counts only written as "IT" or "It", so the pronoun "it" in
    "so it is split" names nothing."""
    text = note or ""
    for pattern, _company in _COMPANY_PATTERNS:
        text = pattern.sub(" ", text)
    note_words = _account_words(text)
    account_words = _account_words(account)
    if _IT_WORD.search(text) and re.search(r"\bIT\b", account or ""):
        return True
    return bool(note_words & account_words)


def strip_signature(note: str, names: tuple[str, ...] = ()) -> str:
    """The note without the sender's signature block.

    Criss forwards with no note at all and her client appends "Cristiane
    Cavalcanti / Finance Manager", which `body_render.operator_note` keeps as
    prose (14 of the 72 live notes are only that). Cut at the first line that
    is exactly one of our people's names (the intake aliases' full names):
    everything from there down is the signature."""
    wanted = {_squash(n) for n in names if _squash(n)}
    kept: list[str] = []
    for line in (note or "").splitlines():
        if wanted and _squash(line) in wanted:
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _squash(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text or "").lower().split())


def stamp_sender_notes(
    receipts: list[Receipt], notes: Mapping[str, str] | None,
) -> list[Receipt]:
    """Stamp each receipt that has a trusted note with it, and with the
    company it decides.

    `notes` is `{document_id: note}`, already filtered to our own senders and
    stripped of signatures by the web layer. The company also replaces the
    receipt's stamped entity, because the note outranks the card (ruling 1)
    and the categorizer picks the company's chart off that stamp. A note that
    decides no company leaves the stamp alone."""
    if not notes:
        return receipts
    out = []
    for r in receipts:
        note = (notes.get(r.document_id) or "").strip()
        if not note:
            out.append(r)
            continue
        reading = read_companies(note)
        kw = {
            "sender_note": note,
            "sender_note_entity": reading.company,
            "sender_note_split": reading.split,
        }
        if reading.company:
            kw["legal_entity_id"] = reading.company
        out.append(replace(r, **kw))
    return out
