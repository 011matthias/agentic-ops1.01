"""infra_yaml.py: one loader over the three infrastructure.yaml shapes (W1-16).

The real meji-media file and the agnt_n8n-builder fixture are read as they
are; the WW shape is a synthetic copy (tools/fixtures/infra_yaml/ww-shape)
because the real file holds client data and is not in this repo.
"""
from __future__ import annotations

import importlib.util
import sys

from hooklib import REPO, TOOLS

WW = TOOLS / "fixtures" / "infra_yaml" / "ww-shape" / "infrastructure.yaml"


def _load():
    spec = importlib.util.spec_from_file_location("infra_yaml", TOOLS / "infra_yaml.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["infra_yaml"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_meji_media_instances_list_shape():
    d = _load().load("meji-media")
    assert d["orchestrator"] == "make"
    prod = [i for i in d["instances"] if i["mcp_server"] == "make-meji-media"]
    assert len(prod) == 1 and prod[0]["type"] == "make"
    assert prod[0]["workflows"] and prod[0]["credentials"]
    first = next(iter(prod[0]["workflows"].values()))
    assert first["id"].isdigit() and first["name"]


def test_n8n_instances_map_shape():
    d = _load().load(TOOLS / "fixtures" / "agnt_n8n-builder" / "infrastructure.yaml")
    (inst,) = d["instances"]
    assert inst["type"] == "n8n" and inst["name"] == "fixture_dev"
    assert inst["credentials"]["gmail_dev"] == 9999
    assert d["orchestrator"] == "n8n"


def test_ww_top_level_blocks_walk_nested_workflows():
    d = _load().load(WW)
    n8n = next(i for i in d["instances"] if i["type"] == "n8n")
    assert n8n["mcp_server"] == "n8n-ww-shape"
    assert n8n["api_key_env"] == "N8N_API_KEY_WW_SHAPE"
    # a sibling block carrying n8n_workflow_id, and two under a nested workflows: map
    assert set(n8n["workflows"]) == {"absence_notice", "w2_09_overdue_tasks", "w2_10_status_change"}
    assert n8n["workflows"]["w2_09_overdue_tasks"]["name"] == "W2-09 overdue tasks"
    assert n8n["workflows"]["absence_notice"]["export"].endswith("absence-notice.json")
    assert n8n["credentials"] == {"hero_api_assistant": "credHero0001"}
    make = next(i for i in d["instances"] if i["type"] == "make")
    assert set(make["workflows"]) == {"s1_alarms", "h2_task_status"}
    assert make["workflows"]["h2_task_status"]["id"] == "2000002"
    assert make["url"] == "eu1.make.invalid"


def test_orchestrator_detection_order(tmp_path):
    m = _load()
    f = tmp_path / "c" / "infrastructure.yaml"
    f.parent.mkdir()
    # top-level orchestrator wins over an instance type
    f.write_text("orchestrator: fastapi\ninstances:\n  - type: make\n", encoding="utf-8")
    assert m.load(f)["orchestrator"] == "fastapi"
    # then the first orchestrator-typed instance
    f.write_text("instances:\n  - kind: fly-app\n  - type: make\n", encoding="utf-8")
    assert m.load(f)["orchestrator"] == "make"
    # then files in automations/
    f.write_text("type: client\n", encoding="utf-8")
    assert m.load(f)["orchestrator"] is None
    (f.parent / "automations").mkdir()
    (f.parent / "automations" / "trigger.config.ts").write_text("", encoding="utf-8")
    assert m.load(f)["orchestrator"] == "trigger-dev"


def test_brisken_deploy_pointer_outranks_the_fastapi_lane():
    d = _load().load("brisken")
    assert d["orchestrator"] == "fastapi"
    assert d["deploy"].endswith("expense-reconciliation/deploy.py")
    assert (REPO / d["deploy"]).is_file()


def test_every_tracked_file_loads():
    m = _load()
    files = [p for home in m.HOMES for p in home.glob("*/infrastructure.yaml")]
    assert files, REPO
    for p in files:
        assert m.load(p)["slug"] == p.parent.name
