"""PLATFORM CONTENT GATE wiring (2026-07-22 blind-spot fix).

rule_platform_standards §10.3 promised that writes under
platform/src/app/(public)/** and platform/src/content/proposals/** fire
validate-platform-content.py via the post-write-gate dispatcher. The wiring
never existed. These tests pin the new scope predicate, the dispatcher plan
entry, and the validator's single-file --format json hook contract.
"""
import importlib.util
import json
import subprocess
import sys

from hooklib import HOOKS, REPO

VALIDATOR = REPO / "tools" / "validate-platform-content.py"


def _load_gate():
    path = HOOKS / "post-write-gate.py"
    spec = importlib.util.spec_from_file_location("post_write_gate", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["post_write_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


G = _load_gate()


# --- in_platform_content_scope ----------------------------------------------

def test_scope_public_page():
    assert G.in_platform_content_scope("platform/src/app/(public)/services/page.tsx")


def test_scope_proposal_md():
    assert G.in_platform_content_scope("platform/src/content/proposals/x.md")


def test_scope_proposal_txt_cover_letter():
    assert G.in_platform_content_scope(
        "platform/src/content/proposals/menovia-upwork-cover-letter.txt"
    )


def test_scope_blog_post():
    # Blog joined the validator's scope 2026-07-22 (PR #376); the dispatcher
    # gate covers it the same way.
    assert G.in_platform_content_scope("platform/src/content/blog/some-post.md")


def test_scope_windows_backslashes():
    assert G.in_platform_content_scope(
        r"C:\repo\platform\src\app\(public)\about\page.tsx"
    )


def test_scope_rejects_admin():
    assert not G.in_platform_content_scope("platform/src/app/admin/page.tsx")


def test_scope_rejects_api_routes():
    assert not G.in_platform_content_scope("platform/src/app/api/modules/route.ts")


def test_scope_rejects_non_text_suffix():
    assert not G.in_platform_content_scope("platform/src/app/(public)/og.png")


def test_scope_empty_path():
    assert not G.in_platform_content_scope("")


# --- plan_validators wiring --------------------------------------------------

def test_plan_public_page_routes_platform_gate():
    plan = G.plan_validators("platform/src/app/(public)/services/page.tsx")
    labels = [p[0] for p in plan]
    assert "PLATFORM CONTENT GATE" in labels
    tool = next(p[1] for p in plan if p[0] == "PLATFORM CONTENT GATE")
    assert tool == "validate-platform-content.py"


def test_plan_proposal_txt_routes_comms_and_platform():
    plan = G.plan_validators("platform/src/content/proposals/cover-letter.txt")
    labels = {p[0] for p in plan}
    assert {"COMMS GATE", "OUTPUT GATE", "PLATFORM CONTENT GATE"} <= labels


def test_plan_out_of_scope_stays_empty():
    assert G.plan_validators("docs/sessions/2026-07-22.md") == []


# --- validator single-file --format json: the dispatcher contract ------------

def _run_json(path) -> tuple[int, dict]:
    proc = subprocess.run(
        ["uv", "run", str(VALIDATOR), str(path), "--format", "json"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO),
    )
    return proc.returncode, json.loads(proc.stdout)


def test_json_contract_shape_out_of_scope_file(tmp_path):
    # A file outside platform/src is filtered out; the contract shape must
    # still come back so the dispatcher can parse it.
    f = tmp_path / "x.md"
    f.write_text("UnpausAI\n", encoding="utf-8")
    code, payload = _run_json(f)
    assert code == 0
    assert payload == {"total": 0, "hits": [], "by_category": {}, "by_severity": {}}


def test_json_contract_on_real_findings(monkeypatch, capsys, tmp_path):
    """In-process: point the module at a tmp platform tree and check the
    single-file JSON payload carries dispatcher-shaped hits."""
    spec = importlib.util.spec_from_file_location("validate_platform_content", VALIDATOR)
    vpc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = vpc
    spec.loader.exec_module(vpc)

    platform = tmp_path / "platform" / "src"
    proposals = platform / "content" / "proposals"
    proposals.mkdir(parents=True)
    f = proposals / "x.md"
    f.write_text("UnpausAI ships well—fast.\n", encoding="utf-8")

    monkeypatch.setattr(vpc, "PLATFORM", platform)
    monkeypatch.setattr(vpc, "PUBLIC_APP", platform / "app" / "(public)")
    monkeypatch.setattr(vpc, "PROPOSALS", proposals)
    monkeypatch.setattr(sys, "argv", ["validate-platform-content.py", str(f), "--format", "json"])

    rc = vpc.main()
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1  # brand typo is HIGH
    assert payload["total"] >= 2
    cats = {h["category"] for h in payload["hits"]}
    assert any(c.startswith("brand:") for c in cats)
    assert "em-dash:unicode" in cats
    assert payload["by_severity"].get("HIGH", 0) >= 2
    for h in payload["hits"]:
        assert {"line", "category", "severity", "message", "snippet"} <= set(h)
