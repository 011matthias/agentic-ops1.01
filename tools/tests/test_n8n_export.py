"""n8n_export.py: id -> file map from infra, scrubbed stable export, live diff (W1-18).

Runs against a copy of the synthetic WW-shape fixture with an injected fetch;
no network, no tenant credential.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys

import pytest

from hooklib import TOOLS

FIXTURE = TOOLS / "fixtures" / "infra_yaml" / "ww-shape"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _live(wid):
    return {
        "id": wid, "name": f"flow {wid}", "active": True, "updatedAt": "2026-10-29T10:00:00Z",
        "versionId": "v1", "meta": {"instanceId": "inst"}, "pinData": {}, "staticData": None,
        "nodes": [{"name": "B", "type": "n8n-nodes-base.set"}, {"name": "A", "type": "n8n-nodes-base.webhook"}],
        "connections": {"A": {"main": [[{"node": "B", "type": "main", "index": 0}]]}},
        "settings": {"executionOrder": "v1"},
    }


@pytest.fixture()
def client(tmp_path):
    dest = tmp_path / "ww-shape"
    shutil.copytree(FIXTURE, dest)
    ix = _load("infra_yaml")
    return dest, ix.load(dest / "infrastructure.yaml")


def _fetch_for(state):
    def fetch_for(_inst):
        return lambda wid: copy.deepcopy(state[wid])
    return fetch_for


def test_targets_come_from_infra_with_export_or_flat_default(client):
    ne = _load("n8n_export")
    _, data = client
    got = {t["key"]: t["path"] for t in ne.targets(data)}
    assert got["absence_notice"] == "automations/n8n/absence-notice.json"
    assert got["w2_09_overdue_tasks"] == "automations/w2-09-overdue-tasks.n8n.json"
    assert "s1_alarms" not in got  # a Make scenario is never an n8n export
    assert [t["key"] for t in ne.targets(data, only="wfStatus0001")] == ["w2_10_status_change"]


def test_export_then_check_is_clean_and_scrubbed(client, capsys):
    ne = _load("n8n_export")
    cdir, data = client
    state = {w: _live(w) for w in ("wfAbsence0001", "wfOverdue0001", "wfStatus0001")}
    assert ne.run(cdir, data, _fetch_for(state), check=False) == 0
    written = json.loads((cdir / "automations" / "w2-09-overdue-tasks.n8n.json").read_text(encoding="utf-8"))
    assert not {"id", "active", "updatedAt", "versionId", "meta", "pinData"} & set(written)
    assert [n["name"] for n in written["nodes"]] == ["A", "B"]
    capsys.readouterr()
    assert ne.run(cdir, data, _fetch_for(state), check=True) == 0
    assert "3 workflow(s) match live" in capsys.readouterr().out


def test_volatile_change_is_not_drift_but_a_real_change_is(client, capsys):
    ne = _load("n8n_export")
    cdir, data = client
    state = {w: _live(w) for w in ("wfAbsence0001", "wfOverdue0001", "wfStatus0001")}
    ne.run(cdir, data, _fetch_for(state), check=False)
    state["wfOverdue0001"]["updatedAt"] = "2026-10-30T00:00:00Z"
    state["wfOverdue0001"]["nodes"].reverse()
    capsys.readouterr()
    assert ne.run(cdir, data, _fetch_for(state), check=True) == 0
    state["wfOverdue0001"]["settings"]["timezone"] = "Europe/Berlin"
    assert ne.run(cdir, data, _fetch_for(state), check=True) == 1
    out = capsys.readouterr().out
    assert "differs: automations/w2-09-overdue-tasks.n8n.json" in out


def test_check_writes_nothing_and_reports_missing(client, capsys):
    ne = _load("n8n_export")
    cdir, data = client
    state = {w: _live(w) for w in ("wfAbsence0001", "wfOverdue0001", "wfStatus0001")}
    assert ne.run(cdir, data, _fetch_for(state), check=True) == 1
    assert "missing: automations/w2-09-overdue-tasks.n8n.json" in capsys.readouterr().out
    assert not (cdir / "automations" / "w2-09-overdue-tasks.n8n.json").exists()


def test_missing_env_names_the_variables_not_values(client, tmp_path):
    ne = _load("n8n_export")
    _, data = client
    (inst,) = [i for i in data["instances"] if i["type"] == "n8n"]
    with pytest.raises(SystemExit) as exc:
        ne.fetcher_for(inst, tmp_path, "ww-shape")
    assert "N8N_API_URL_WW_SHAPE" in str(exc.value) and "N8N_API_KEY_WW_SHAPE" in str(exc.value)
