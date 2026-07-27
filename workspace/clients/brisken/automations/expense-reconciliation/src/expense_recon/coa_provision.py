"""Server-side COA-gate provisioning for the hosted web workbench.

The CLI takes a ``coa_validation:`` block directly in the run config
(`cli._build_coa_gate`). Web runs are built from an upload form and carry no
hand-written config, so the Phase-5 chart-of-accounts gate would never fire on
the hosted review surface (the canonical place Chris reviews). This module
injects a per-entity ``coa_validation`` block into a web run's config from a
provisioning file, so every run is validated against the chart of the legal
entity that actually paid.

The provisioning file and the Books COA JSON it points at are sensitive client
config: they live on the Fly ``/data`` volume (never committed, never baked
into the image, same home as the run DB + receipts). The provisioning path is
given by the ``EXPENSE_RECON_COA_PROVISION`` env var; unset => no injection and
existing behaviour byte for byte. Everything here is fail-open: any error
(missing file, malformed JSON, unknown entity) leaves the config unchanged
rather than breaking a run. The gate protects the export; it must never block
a reconciliation from running.

Provisioning file shape (authored by us, uploaded to ``/data``):

    {
      "chart_path": "/data/zoho-books-coa.json",
      "entities": {
        "Corporate Services": {
          "org_id": "822741658",
          "scope_groups": ["MS | OpeEx", "Bank Fees and Charges"]
        },
        "Cloud Services": {
          "org_id": "697686691",
          "scope_groups": ["Travel Expense", "Marketing & Selling Expenses", ...]
        }
      }
    }

The ``entities`` keys match a run's resolved legal entity
(`web.service.RunForm.resolve_legal_entity`, matched case-insensitively). An
unmatched entity leaves the run unguarded (visible in the workbench as
un-validated) rather than validated against the wrong entity's chart.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROVISION_ENV = "EXPENSE_RECON_COA_PROVISION"


def load_provisioning(path: str | Path) -> dict | None:
    """Load + parse the provisioning file. Returns the dict, or None when the
    file is missing or not valid JSON (fail-open, logged at debug)."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.debug("COA provisioning file unreadable (%s): %s", p, exc)
        return None
    return data if isinstance(data, dict) else None


def coa_validation_for(entity_label: str, provisioning: dict) -> dict | None:
    """Build a ``coa_validation`` block for ``entity_label`` from a loaded
    provisioning dict, or None when the entity is not provisioned.

    Entity matching is case-insensitive and whitespace-trimmed. The returned
    block is the exact shape `cli._build_coa_gate` consumes
    (`chart_path`/`org_id`/`scope_groups`/`entity_label`).
    """
    entities = provisioning.get("entities")
    chart_path = provisioning.get("chart_path")
    if not isinstance(entities, dict) or not chart_path:
        return None

    key = (entity_label or "").strip().lower()
    match = next(
        (v for k, v in entities.items() if str(k).strip().lower() == key and isinstance(v, dict)),
        None,
    )
    if match is None:
        return None
    org_id = match.get("org_id")
    if not org_id:
        return None

    block: dict = {
        "enabled": True,
        "chart_path": str(chart_path),
        "org_id": str(org_id),
        "entity_label": match.get("entity_label") or entity_label,
    }
    scope_groups = match.get("scope_groups")
    if scope_groups:
        block["scope_groups"] = list(scope_groups)
    if match.get("types"):
        block["types"] = list(match["types"])
    return block


def entity_from_settings(settings: dict | None, entity_label: str) -> dict | None:
    """The stored settings-registry entry for one legal entity
    (`settings["entities"]`, Phase 5), matched case-insensitively like the
    provisioning file's entities. None when the registry has no entry."""
    entities = (settings or {}).get("entities")
    if not isinstance(entities, dict):
        return None
    key = (entity_label or "").strip().lower()
    return next(
        (
            v
            for k, v in entities.items()
            if str(k).strip().lower() == key and isinstance(v, dict)
        ),
        None,
    )


def coa_validation_from_settings(
    entity_label: str, settings: dict | None, provisioning: dict | None
) -> dict | None:
    """Build a ``coa_validation`` block preferring the settings entity
    registry over the /data provisioning file (Phase 5: entities become
    definable in the UI, the file stays the fallback).

    The settings entry supplies ``org_id`` / ``scope_groups`` (and may carry
    its own ``chart_path``); the chart file path falls back to the
    provisioning file's ``chart_path``, so a registry entry works without
    re-stating where the chart lives. No settings entry => the file's own
    entity mapping, exactly as before. None when neither source can build a
    complete block (fail-open, run left unguarded)."""
    ent = entity_from_settings(settings, entity_label)
    file_chart = (provisioning or {}).get("chart_path")
    if ent is not None and ent.get("org_id"):
        chart_path = ent.get("chart_path") or file_chart
        if chart_path:
            block: dict = {
                "enabled": True,
                "chart_path": str(chart_path),
                "org_id": str(ent["org_id"]),
                "entity_label": entity_label,
            }
            if ent.get("scope_groups"):
                block["scope_groups"] = list(ent["scope_groups"])
            if ent.get("types"):
                block["types"] = list(ent["types"])
            return block
    if provisioning is not None:
        return coa_validation_for(entity_label, provisioning)
    return None


def apply_to_config(
    cfg: dict,
    entity_label: str,
    *,
    path: str | Path | None = None,
    settings: dict | None = None,
) -> dict:
    """Return ``cfg`` with a per-entity ``coa_validation`` block injected from
    the provisioning file, or the same ``cfg`` unchanged when provisioning is
    absent / disabled / does not cover this entity.

    ``path`` defaults to the ``EXPENSE_RECON_COA_PROVISION`` env var. An
    existing ``coa_validation`` block in ``cfg`` is never overwritten.
    ``settings`` (Phase 5) is the stored web settings; when its ``entities``
    registry covers this entity, that entry wins over the file's mapping
    (``coa_validation_from_settings``). Wholly fail-open: any unexpected
    error returns ``cfg`` untouched, because the gate guards the export and
    must not be able to break a run.
    """
    try:
        if cfg.get("coa_validation") is not None:
            return cfg  # respect an explicit block; don't clobber
        prov_path = path if path is not None else os.environ.get(PROVISION_ENV)
        provisioning = load_provisioning(prov_path) if prov_path else None
        block = coa_validation_from_settings(entity_label, settings, provisioning)
        if block is None:
            logger.info(
                "COA provisioning: no chart for legal entity %r; run left "
                "un-validated",
                entity_label,
            )
            return cfg
        new_cfg = dict(cfg)
        new_cfg["coa_validation"] = block
        logger.info(
            "COA provisioning: run validated against entity %r (org %s)",
            block["entity_label"],
            block["org_id"],
        )
        return new_cfg
    except Exception:  # noqa: BLE001 - never let provisioning break a run
        logger.debug("COA provisioning failed; leaving config unchanged", exc_info=True)
        return cfg
