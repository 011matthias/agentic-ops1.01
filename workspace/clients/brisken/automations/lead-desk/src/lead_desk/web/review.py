"""Campaign review packets: the owner-facing sign-off page for a roll-out.

A packet is one gated in-app page (``/review/{packet_id}``) that puts every
open decision and every suggested mail in front of the reviewer (Dirk):

- ``decision`` items render as a multiple-choice question with an optional
  comment. The stored response is {choice, comment, by, at}.
- ``sequence`` items render the suggested wave: audience, timing, and the
  verbatim text of every step in editable fields. The reviewer approves the
  wording as-is, saves an edited version, or leaves a change request. The
  stored response is {status: approved|edited|changes, steps, comment, by, at};
  ``steps`` carries the reviewer's latest text and is what the campaign build
  loads at arming time.
- ``note`` items are read-only context blocks.

Item body shapes (JSON, authored by the seed file):

    decision: {question, options: [{key, label, detail?}], recommended?}
    sequence: {audience, timing, from_line?, recipients: [{name, company,
               email?}], steps: [{step_no, label?, subject?, text}]}
    note:     {text}

Packet metadata lives in the state KV as ``review:{packet_id}`` with
{title, intro, created_at}. Responses never send anything; the packet is a
review surface only, upstream of the engine's own approve/start gates.
"""
from __future__ import annotations

import json

from .store import ContactStore

PACKET_STATE_PREFIX = "review:"

_KINDS = ("decision", "sequence", "note")
_SEQ_STATUSES = ("approved", "edited", "changes")


def packet_meta(store: ContactStore, packet_id: str) -> dict | None:
    raw = store.get_state(PACKET_STATE_PREFIX + packet_id)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def seed_packet(store: ContactStore, packet: dict, now: str,
                replace: bool = False) -> dict:
    """Load a packet definition (title, intro, items[]) into the DB.

    Refuses to overwrite an existing packet unless ``replace`` is set; a
    replace drops the prior items AND their responses (a reseed is a new
    review round).
    """
    packet_id = str(packet.get("packet_id") or "").strip()
    if not packet_id:
        raise ValueError("packet_id is required")
    existing = store.list_review_items(packet_id)
    if existing and not replace:
        raise ValueError(
            f"packet '{packet_id}' already has {len(existing)} items; "
            "pass replace to reseed")
    removed = store.delete_review_packet(packet_id) if existing else 0
    items = packet.get("items") or []
    if not items:
        raise ValueError("packet has no items")
    for pos, item in enumerate(items, start=1):
        kind = item.get("kind")
        if kind not in _KINDS:
            raise ValueError(f"item {pos}: unknown kind '{kind}'")
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError(f"item {pos}: title is required")
        body = item.get("body") or {}
        if kind == "decision":
            options = body.get("options") or []
            keys = [o.get("key") for o in options]
            if len(options) < 2 or len(set(keys)) != len(keys) or not all(keys):
                raise ValueError(f"item {pos}: decision needs >=2 unique option keys")
            if not (body.get("question") or "").strip():
                raise ValueError(f"item {pos}: decision needs a question")
        if kind == "sequence":
            steps = body.get("steps") or []
            if not steps or not all((s.get("text") or "").strip() for s in steps):
                raise ValueError(f"item {pos}: sequence needs steps with text")
        store.add_review_item(packet_id, pos, kind, title,
                              json.dumps(body, ensure_ascii=False), now)
    store.set_state(PACKET_STATE_PREFIX + packet_id, json.dumps({
        "title": packet.get("title") or packet_id,
        "intro": packet.get("intro") or "",
        "created_at": now,
    }, ensure_ascii=False), now)
    return {"packet_id": packet_id, "items": len(items), "replaced": removed}


def build_review_view(store: ContactStore, packet_id: str) -> dict | None:
    meta = packet_meta(store, packet_id)
    rows = store.list_review_items(packet_id)
    if not rows:
        return None
    items = []
    open_decisions = 0
    open_sequences = 0
    for r in rows:
        body = json.loads(r["body"])
        response = json.loads(r["response"]) if r["response"] else None
        item = {
            "item_id": r["item_id"], "kind": r["kind"], "title": r["title"],
            "body": body, "response": response,
        }
        if r["kind"] == "decision":
            if not response:
                open_decisions += 1
            else:
                labels = {o["key"]: o.get("label", o["key"])
                          for o in body.get("options", [])}
                item["chosen_label"] = labels.get(response.get("choice"),
                                                  response.get("choice"))
        if r["kind"] == "sequence":
            if not response or response.get("status") == "changes":
                open_sequences += 1
            # The editor prefills with the reviewer's latest text when there
            # is one, else the suggestion.
            latest = {s.get("step_no"): s for s in
                      (response or {}).get("steps") or []}
            for step in body.get("steps") or []:
                got = latest.get(step.get("step_no")) or {}
                step["current_subject"] = got.get("subject", step.get("subject") or "")
                step["current_text"] = got.get("text", step.get("text") or "")
        items.append(item)
    return {
        "packet_id": packet_id,
        "title": (meta or {}).get("title", packet_id),
        "intro": (meta or {}).get("intro", ""),
        "items": items,
        "open_decisions": open_decisions,
        "open_sequences": open_sequences,
        "complete": open_decisions == 0 and open_sequences == 0,
    }


def submit_decision(store: ContactStore, item_id: int, choice: str,
                    comment: str, by: str, now: str) -> None:
    row = store.get_review_item(item_id)
    if row is None or row["kind"] != "decision":
        raise ValueError("no such decision")
    body = json.loads(row["body"])
    keys = {o.get("key") for o in body.get("options", [])}
    if choice not in keys:
        raise ValueError(f"choice must be one of {sorted(keys)}")
    store.set_review_response(item_id, json.dumps({
        "choice": choice, "comment": (comment or "").strip(),
        "by": by, "at": now,
    }, ensure_ascii=False), now)


def submit_sequence(store: ContactStore, item_id: int, action: str,
                    steps: list[dict], comment: str, by: str, now: str) -> None:
    """``action``: 'approve' freezes the current text as the approved wording;
    'save' stores an edit without approving; 'changes' records a change
    request (comment required)."""
    row = store.get_review_item(item_id)
    if row is None or row["kind"] != "sequence":
        raise ValueError("no such sequence item")
    status = {"approve": "approved", "save": "edited", "changes": "changes"}.get(action)
    if status is None:
        raise ValueError("action must be approve, save or changes")
    comment = (comment or "").strip()
    if status == "changes" and not comment:
        raise ValueError("a change request needs a comment")
    body = json.loads(row["body"])
    wanted = {s.get("step_no") for s in body.get("steps") or []}
    got = {s.get("step_no") for s in steps}
    if wanted != got:
        raise ValueError("submitted steps do not match the sequence")
    if not all((s.get("text") or "").strip() for s in steps):
        raise ValueError("every step needs text")
    store.set_review_response(item_id, json.dumps({
        "status": status, "steps": steps, "comment": comment,
        "by": by, "at": now,
    }, ensure_ascii=False), now)
