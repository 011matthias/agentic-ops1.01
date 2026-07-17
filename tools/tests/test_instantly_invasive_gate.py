"""instantly-invasive-gate (B5): mutating api.instantly.ai calls -> ask.

Reads pass through (any GET, plus the allowlisted read POST endpoints like
/leads/list and /campaigns/analytics). A -X POST/PUT/PATCH/DELETE to any other
path forces a permission stop. AGENTIC_OPS_SESSION_STATE is redirected so the
"ask"-path friction-candidate capture can't touch live state.
"""
from hooklib import permission_decision, run_hook


def _run(cmd, tmp_path):
    return run_hook(
        "instantly-invasive-gate.py",
        {"tool_input": {"command": cmd}},
        env={"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "s.json")},
    )


def test_non_instantly_passes(tmp_path):
    p = _run("curl -X POST https://api.example.com/x -d '{}'", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_plain_get_passes(tmp_path):
    p = _run("curl https://api.instantly.ai/api/v2/accounts", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_read_path_post_passes(tmp_path):
    p = _run("curl -X POST https://api.instantly.ai/api/v2/leads/list -d '{}'", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_mutating_post_asks(tmp_path):
    p = _run("curl -X POST https://api.instantly.ai/api/v2/campaigns -d '{}'", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_mutating_delete_asks(tmp_path):
    p = _run("curl -X DELETE https://api.instantly.ai/api/v2/leads/123", tmp_path)
    assert permission_decision(p.stdout) == "ask"


# --- 2026-06-09 hardening: script-wrapper bypass (register #11 + #177) ---

# Layer B: known invasive loader script classified by --stage.
def test_loader_activate_asks(tmp_path):
    p = _run("python meji_p1_instantly_load.py --stage activate", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_loader_create_via_uv_asks(tmp_path):
    p = _run("uv run meji_p1_instantly_load.py --stage create", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_loader_archive_asks(tmp_path):
    p = _run("python meji_p2_instantly_load.py --stage archive", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_loader_stage_equals_form_asks(tmp_path):
    p = _run("python meji_p1_instantly_load.py --stage=load", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_loader_preview_passes(tmp_path):
    p = _run("python meji_p1_instantly_load.py --stage preview", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_loader_audit_passes(tmp_path):
    p = _run("python meji_p1_instantly_load.py --stage audit", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# Layer C: non-loader .py whose contents touch the API with a mutating method.
def test_file_scan_mutating_asks(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(
        "import urllib.request as u\n"
        'u.urlopen(u.Request("https://api.instantly.ai/api/v2/campaigns", method="POST"))\n',
        encoding="utf-8",
    )
    p = _run(f"python {script}", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_file_scan_readonly_passes(tmp_path):
    # api.instantly.ai present but only GET + a POST to a read path -> allow.
    script = tmp_path / "census.py"
    script.write_text(
        "import urllib.request as u\n"
        'u.urlopen("https://api.instantly.ai/api/v2/accounts")\n'
        'def api(method, path): pass\n'
        'api("POST", "/leads/list")\n',
        encoding="utf-8",
    )
    p = _run(f"python {script}", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# Layer A: inline urllib mutating method (not curl -X).
def test_inline_urllib_put_asks(tmp_path):
    p = _run(
        "python -c \"import urllib.request as u; "
        "u.urlopen(u.Request('https://api.instantly.ai/api/v2/leads', method='PUT'))\"",
        tmp_path,
    )
    assert permission_decision(p.stdout) == "ask"


# Layer D: fail-toward-ask only with an uninspectable Instantly signal.
def test_unresolvable_loader_activate_asks(tmp_path):
    p = _run("uv run /tmp/does-not-exist-instantly-load.py --stage activate", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_unrelated_python_passes(tmp_path):
    p = _run("python /tmp/nonexistent_build.py", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_build_py_passes(tmp_path):
    p = _run("python build.py", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# False-positive guard: running THIS test file (which contains api.instantly.ai
# + -X POST as test data) must not trip the gate.
def test_running_instantly_test_file_does_not_ask(tmp_path):
    p = _run("uv run python -m pytest tools/tests/test_instantly_invasive_gate.py", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# --- 2026-06-18: curl body flag implies POST with no -X. A body-bearing curl
# (register #11/#177 follow-up) was slipping through as a read. ---
def test_curl_data_implicit_post_to_pause_asks(tmp_path):
    p = _run("curl --data '{}' https://api.instantly.ai/api/v2/campaigns/123/pause", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_curl_short_d_file_implicit_post_asks(tmp_path):
    p = _run("curl -d @body.json https://api.instantly.ai/api/v2/campaigns/123/activate", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_curl_form_upload_import_asks(tmp_path):
    p = _run("curl -F file=@leads.csv https://api.instantly.ai/api/v2/leads/import", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_curl_data_to_read_path_still_passes(tmp_path):
    # read-path short-circuit precedes the method check: a body POST to a read
    # endpoint still allows, so the new clause adds no read-path false positive.
    p = _run("curl --data '{}' https://api.instantly.ai/api/v2/leads/list", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


# --- 2026-07-10: PowerShell spellings + Layer-A compound-command reorder ----

def test_ps_invoke_restmethod_post_asks(tmp_path):
    p = _run(
        "Invoke-RestMethod -Uri https://api.instantly.ai/api/v2/campaigns/x/activate "
        "-Method Post",
        tmp_path,
    )
    assert permission_decision(p.stdout) == "ask"


def test_ps_irm_get_passes(tmp_path):
    p = _run("irm https://api.instantly.ai/api/v2/accounts", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_ps_method_post_to_read_path_passes(tmp_path):
    p = _run(
        "Invoke-RestMethod -Uri https://api.instantly.ai/api/v2/campaigns/analytics "
        "-Method Post -Body $b",
        tmp_path,
    )
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_compound_read_then_activate_asks(tmp_path):
    # The 2026-07-10 audit hole: a read path ANYWHERE in the command used to
    # short-circuit the whole gate, so read-then-activate one-liners passed.
    p = _run(
        "curl https://api.instantly.ai/api/v2/campaigns/analytics && "
        "curl -X POST https://api.instantly.ai/api/v2/campaigns/x/activate -d '{}'",
        tmp_path,
    )
    assert permission_decision(p.stdout) == "ask"


def test_ps_body_alone_not_mutating(tmp_path):
    # -Body without -Method does not imply POST in PowerShell.
    p = _run(
        "Invoke-RestMethod -Uri https://api.instantly.ai/api/v2/accounts -Body $b",
        tmp_path,
    )
    assert p.returncode == 0 and p.stdout.strip() == ""
