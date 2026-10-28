"""A stable code beside the English sentence of every refusal (item 130).

Every error body the web API sends is ``{"error": <one English sentence>,
"code": <stable snake_case id>, ...named values}``. The sentence is
unchanged and stays what an English reader and every existing client
reads; the code names the CONDITION, not the wording, so a reworded
sentence never breaks a front end; the named values (a file name, a month,
a count, a card) ride as their own fields, so the screen builds its own
Portuguese sentence from data instead of translating English with numbers
baked into it.

Two carriers let a code travel from where a refusal is decided to where it
is answered, without changing any type a caller already depends on:

* ``Refusal`` IS a ``str``. The service helpers that return an error
  sentence keep returning one (every ``==`` against the sentence, and
  every ``if err:``, still holds); the route reads ``.code`` / ``.fields``
  off it, through ``code_of`` / ``fields_of`` so a plain string is still
  answerable.
* ``CodedValueError`` IS a ``ValueError``. The settings normalizers keep
  raising the type their callers already catch.

``service.RunInputError`` carries the same two attributes directly.

Nothing here imports anything: it is the one module both the web layer and
the settings normalizers (cards, merchants, cost centers) can depend on.
"""
from __future__ import annotations


class Refusal(str):
    """An English refusal sentence that also knows its own code.

    ``Refusal("card 2838 is inactive", code="card_inactive", card="2838")``
    is the sentence, everywhere a sentence was used before. String
    operations on it return plain strings, which is correct: a sliced or
    reformatted sentence is no longer the refusal that was decided.
    """

    code: str
    fields: dict

    def __new__(cls, message: str, *, code: str, **fields: object) -> "Refusal":
        obj = super().__new__(cls, message)
        obj.code = code
        obj.fields = dict(fields)
        return obj


class CodedValueError(ValueError):
    """A ``ValueError`` that names its condition (the settings normalizers).

    Callers that only catch ``ValueError`` and print ``str(exc)`` are
    unaffected; the route adds the code and the named values.
    """

    def __init__(self, message: str, *, code: str, **fields: object) -> None:
        super().__init__(message)
        self.code = code
        self.fields = dict(fields)


def code_of(obj: object, default: str) -> str:
    """The code carried by a refusal, or ``default`` for a plain string.

    The default is what a refusal that has not been given a code yet
    answers with: the front end then shows the English sentence, which is
    what it did before any of this existed.
    """
    code = getattr(obj, "code", None)
    return code if isinstance(code, str) and code else default


def fields_of(obj: object) -> dict:
    """The named values carried by a refusal; empty for a plain string."""
    fields = getattr(obj, "fields", None)
    return dict(fields) if isinstance(fields, dict) else {}


def error_body(message: object, code: str, **fields: object) -> dict:
    """One error body: the sentence, its code, and its named values."""
    return {"error": str(message), "code": code, **fields}


def detail_of(text: object) -> dict | None:
    """``{code, ...named values}`` for a coded sentence, else ``None``.

    Used for the advisories, which travel as prose on an existing field: the
    detail rides BESIDE the sentence as a parallel field rather than
    retyping the field the SPA already reads (the 2026-08-22 lesson in
    docs/api-contract.md). ``None`` means "no advisory" or "an advisory
    written before this existed", and both read the same to a consumer.
    """
    if isinstance(text, Refusal):
        return {"code": text.code, **text.fields}
    return None
