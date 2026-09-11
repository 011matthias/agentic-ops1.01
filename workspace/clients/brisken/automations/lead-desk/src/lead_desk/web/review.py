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

from .cadence import deny_domains
from .store import ContactStore

PACKET_STATE_PREFIX = "review:"

_KINDS = ("decision", "sequence", "note")
_SEQ_STATUSES = ("approved", "edited", "changes")


# Auto-reply shapes. An out-of-office is not a human answering, so it must
# never count as a conversation or take someone off a follow-up list.
_AUTO_SQL = (
    "(lower(coalesce(subject,'')) LIKE 'automatic reply%' OR "
    " lower(coalesce(subject,'')) LIKE 'automatische antwort%' OR "
    " lower(coalesce(subject,'')) LIKE 'out of office%' OR "
    " lower(coalesce(subject,'')) LIKE 'accepted:%' OR "
    " lower(coalesce(subject,'')) LIKE 'declined:%')"
)

FACT_KEYS = ("reached", "in_conversation", "booked", "no_response",
             "wave_people", "wave_mails")


def packet_facts(store: ContactStore, packet_id: str,
                 since: str | None = None) -> dict:
    """The packet's headline figures, recomputed from the event log.

    Definitions, so any number on the page can be re-derived:

    - ``reached``          distinct contacts with an outbound event
    - ``booked``           distinct contacts with a 'booked' event
    - ``in_conversation``  contacts who replied for real (an inbound 'reply'
                           that is not an auto-reply) OR have a booking
    - ``no_response``      reached minus in_conversation, as a set difference
                           so ``in_conversation + no_response == reached``
                           holds by construction rather than by hope
    - ``wave_people`` /    the distinct recipients across this packet's
      ``wave_mails``       sequence items, and recipients x steps

    These exist because the numbers used to be prose typed into the seed
    file: on 2026-09-10 every one of them was wrong and the sentence's own
    arithmetic did not close (it claimed 124 reached, 34 in conversation and
    71 non-responders). A figure that is computed at render cannot go stale
    and cannot be invented.
    """
    where = " AND ts >= ?" if since else ""
    args = (since,) if since else ()

    def ids(sql, extra=()):
        return {r[0] for r in store.conn.execute(sql, (*extra, *args))}

    reached = ids("SELECT DISTINCT contact_id FROM outreach_events "
                  "WHERE direction='outbound'" + where)
    replied = ids("SELECT DISTINCT contact_id FROM outreach_events "
                  "WHERE direction='inbound' AND type='reply' "
                  "AND NOT " + _AUTO_SQL + where)
    booked = ids("SELECT DISTINCT contact_id FROM outreach_events "
                 "WHERE type='booked'" + where)
    convo = replied | booked

    people, mails = set(), 0
    for row in store.list_review_items(packet_id):
        if row["kind"] != "sequence":
            continue
        body = json.loads(row["body"])
        rec = body.get("recipients") or []
        people |= {(r.get("email") or "").strip().lower() for r in rec if r.get("email")}
        mails += len(rec) * len(body.get("steps") or [])
    return {
        "reached": len(reached),
        "in_conversation": len(convo),
        "booked": len(booked),
        "no_response": len(reached - convo),
        "wave_people": len(people),
        "wave_mails": mails,
    }


def fill_facts(text: str, facts: dict) -> str:
    """Substitute the known {fact} placeholders; anything else is left
    alone, so an unrecognised brace can never be silently blanked."""
    for k in FACT_KEYS:
        text = text.replace("{" + k + "}", str(facts.get(k, "{" + k + "}")))
    return text


def unsendable_reason(store: ContactStore, email: str) -> str | None:
    """Why the ENGINE would refuse this recipient, or None.

    Deliberately the send path's own predicates rather than a lookalike, so
    a roster can never be built against a laxer rule than the one that
    actually fires at claim time.
    """
    addr = (email or "").strip().lower()
    if not addr or "@" not in addr:
        return "no usable address"
    if addr.rsplit("@", 1)[1] in deny_domains(store):
        return f"denied domain ({addr.rsplit('@', 1)[1]})"
    row = store.suppression_block(addr)
    if row is not None:
        return f"suppression ledger ({row['note'] or row['kind']})"
    return None


def responded_reason(store: ContactStore, email: str) -> str | None:
    """When this person last answered us, or None.

    A roster is static seed data while the mailbox keeps moving, so a reply
    that lands (or is recovered) after seeding does not take anyone off a
    follow-up list. Writing again to somebody who already answered is the
    worst outcome this surface can produce, so the page re-asks the question
    at every render instead of trusting the list it was given.

    Auto-replies and meeting responses are excluded: an out-of-office is not
    an answer, and treating it as one would quietly shrink a wave.
    """
    addr = (email or "").strip().lower()
    if not addr:
        return None
    row = store.conn.execute(
        "SELECT contact_id FROM contacts WHERE lower(coalesce(email,'')) = ? "
        "OR lower(coalesce(alt_email,'')) = ? LIMIT 1", (addr, addr)).fetchone()
    if row is None:
        return None
    hit = store.conn.execute(
        "SELECT ts, type FROM outreach_events WHERE contact_id = ? AND ("
        "  (direction = 'inbound' AND type = 'reply' AND NOT " + _AUTO_SQL + ")"
        "  OR type = 'booked') ORDER BY ts DESC LIMIT 1",
        (row["contact_id"],)).fetchone()
    if hit is None:
        return None
    what = "a meeting" if hit["type"] == "booked" else "replied"
    return f"{what} on {(hit['ts'] or '')[:10]}"


def unsendable_recipients(store: ContactStore, packet: dict) -> list[dict]:
    """Every recipient in a packet definition the engine would refuse."""
    out = []
    for pos, item in enumerate(packet.get("items") or [], start=1):
        if item.get("kind") != "sequence":
            continue
        for r in (item.get("body") or {}).get("recipients") or []:
            why = unsendable_reason(store, r.get("email") or "")
            if why:
                out.append({"item": pos, "title": item.get("title"),
                            "name": r.get("name"), "email": r.get("email"),
                            "reason": why})
    return out


def packet_meta(store: ContactStore, packet_id: str) -> dict | None:
    raw = store.get_state(PACKET_STATE_PREFIX + packet_id)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def seed_packet(store: ContactStore, packet: dict, now: str,
                replace: bool = False,
                allow_unsendable: bool = False) -> dict:
    """Load a packet definition (title, intro, items[]) into the DB.

    Refuses to overwrite an existing packet unless ``replace`` is set; a
    replace drops the prior items AND their responses (a reseed is a new
    review round).

    Also refuses, unless ``allow_unsendable``, to seed a wave containing a
    recipient the send path would reject. The reviewer approves a list on the
    understanding that approving it makes it go; a name the engine will
    silently drop at claim time makes the page a lie. On 2026-09-10 the live
    September packet asked for sign-off on 62 people of whom 36 were
    unsendable, wave 2 being 23 listed and 0 sendable, and nothing anywhere
    said so.
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
    if not allow_unsendable:
        bad = unsendable_recipients(store, packet)
        if bad:
            lines = "; ".join(f"{b['name'] or b['email']} [{b['reason']}]"
                              for b in bad[:8])
            more = f" and {len(bad) - 8} more" if len(bad) > 8 else ""
            raise ValueError(
                f"{len(bad)} recipient(s) the engine would refuse: "
                f"{lines}{more}. Remove them or pass allow_unsendable.")
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
    facts = packet_facts(store, packet_id, (meta or {}).get("facts_since"))
    # Recomputed at render, not trusted from seed time: a suppression entry
    # or deny rule added after seeding must show up on the page rather than
    # wait to be discovered at claim time.
    unsendable = []
    responded = []
    items = []
    open_decisions = 0
    open_sequences = 0
    for r in rows:
        body = json.loads(r["body"])
        response = json.loads(r["response"]) if r["response"] else None
        if r["kind"] == "note" and isinstance(body.get("text"), str):
            body["text"] = fill_facts(body["text"], facts)
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
            for rec in body.get("recipients") or []:
                why = unsendable_reason(store, rec.get("email") or "")
                if why:
                    unsendable.append({"name": rec.get("name"),
                                       "email": rec.get("email"),
                                       "reason": why, "wave": r["title"]})
                answered = responded_reason(store, rec.get("email") or "")
                if answered:
                    responded.append({"name": rec.get("name"),
                                      "email": rec.get("email"),
                                      "reason": answered, "wave": r["title"]})
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
        "facts": facts,
        "unsendable": unsendable,
        "responded": responded,
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
