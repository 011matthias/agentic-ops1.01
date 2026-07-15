"""Card presets for the hosted upload form (testing mode).

The user upload form must not ask a bookkeeper for account ids, JSON entity
maps, or currencies. Instead a provisioning file on the Fly ``/data`` volume
(same private home as the run DB and the COA provisioning) lists Brisken's
real cards; the form renders them as a dropdown and the server derives the
run parameters (``account_id`` / legal entity / currency) from the picked
card.

The path comes from the ``EXPENSE_RECON_CARDS`` env var; unset or unreadable
=> no presets (fail-open) and the form falls back to a plain card-name text
input. The real file is authored with Chris/Dirk and uploaded to ``/data``,
never committed; ``examples/cards.example.json`` documents the shape:

    {
      "cards": [
        {
          "key": "corp-2838",
          "label": "Corporate card ending 2838",
          "label_pt": "Cartao corporativo final 2838",
          "account_id": "card-2838",
          "legal_entity": "Corporate Services",
          "currency": "USD"
        }
      ]
    }

``legal_entity`` values must match the COA provisioning's entity keys so the
Phase-5 chart gate keeps firing on preset-driven runs.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CARDS_ENV = "EXPENSE_RECON_CARDS"


@dataclass(frozen=True)
class CardPreset:
    key: str
    label: str
    label_pt: str | None
    account_id: str
    legal_entity: str
    currency: str


def load_cards(path: str | Path | None = None) -> list[CardPreset]:
    """The provisioned card presets, or [] when unprovisioned (fail-open)."""
    cards_path = path if path is not None else os.environ.get(CARDS_ENV)
    if not cards_path:
        return []
    p = Path(cards_path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.debug("cards provisioning file unreadable (%s): %s", p, exc)
        return []
    raw = data.get("cards") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    presets: list[CardPreset] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        account_id = str(entry.get("account_id") or "").strip()
        legal_entity = str(entry.get("legal_entity") or "").strip()
        if not key or not account_id or not legal_entity:
            continue
        presets.append(
            CardPreset(
                key=key,
                label=str(entry.get("label") or key),
                label_pt=(str(entry["label_pt"]) if entry.get("label_pt") else None),
                account_id=account_id,
                legal_entity=legal_entity,
                currency=str(entry.get("currency") or "USD").strip().upper(),
            )
        )
    return presets


def card_by_key(key: str | None, cards: list[CardPreset]) -> CardPreset | None:
    if not key:
        return None
    wanted = key.strip()
    return next((c for c in cards if c.key == wanted), None)
