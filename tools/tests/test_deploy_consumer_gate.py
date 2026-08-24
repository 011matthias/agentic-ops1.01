"""Tests for .claude/hooks/deploy-consumer-gate.py.

The gate couples two things nothing else connected: "a deploy changed a
payload" and "the consumer that renders it has never been driven".

  PostToolUse  deploy command            -> open marker + [CONSUMER NOT DRIVEN]
               browser drive             -> close marker
               curl / healthz / WebFetch -> marker STAYS open (that is the
                                            incident's own move, not the cure)
  Stop         marker open + the response claims verified -> block once
               marker open, no claim / marker closed      -> silent allow

2026-08-24: a Fly deploy passed /healthz and API reads and was declared
verified; the SPA rendered the new `pooled` status as "Arriving" with a blank
Month and six real receipts misreported until a human found it.

The NEGATIVE cases are the contract: with no deploy in the session the gate is
completely inert, and `stop_hook_active` guarantees it costs one turn rather
than wedging the session.
"""
from __future__ import annotations

import json

from hooklib import run_hook

HOOK = "deploy-consumer-gate.py"


def env(tmp_path) -> dict:
    return {
        "AGENTIC_OPS_SESSION_STATE": "",
        "DEPLOY_CONSUMER_MARKER": str(tmp_path / "marker.txt"),
    }


def post(tmp_path, tool: str, command: str | None = None) -> str:
    payload = {"hook_event_name": "PostToolUse", "tool_name": tool}
    if command is not None:
        payload["tool_input"] = {"command": command}
    r = run_hook(HOOK, payload, env=env(tmp_path))
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


def transcript(tmp_path, text: str) -> str:
    p = tmp_path / "transcript.jsonl"
    p.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": text}]},
        }) + "\n",
        encoding="utf-8",
    )
    return str(p)


def stop(tmp_path, text: str, active: bool = False) -> str | None:
    r = run_hook(
        HOOK,
        {
            "hook_event_name": "Stop",
            "transcript_path": transcript(tmp_path, text),
            "stop_hook_active": active,
        },
        env=env(tmp_path),
    )
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return None
    obj = json.loads(r.stdout)
    return obj.get("reason") if obj.get("decision") == "block" else None


CLAIM = "Deployed v86 to Fly. Verified: /healthz 200 and the API returns pooled."
NO_CLAIM = "Deployed v86 to Fly. Next I will drive the receipts route."


# ---- The incident, end to end -------------------------------------------

def test_deploy_then_verified_claim_is_blocked(tmp_path):
    post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    blocked = stop(tmp_path, CLAIM)
    assert blocked is not None
    assert "CONSUMER NOT DRIVEN" in blocked
    assert "browser_navigate" in blocked


def test_deploy_then_browser_drive_then_claim_passes(tmp_path):
    post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    post(tmp_path, "mcp__playwright__browser_navigate")
    assert stop(tmp_path, CLAIM) is None


def test_healthz_check_does_not_close_the_marker(tmp_path):
    """The exact substitution the incident made."""
    post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    advisory = post(tmp_path, "Bash", "curl -s https://app.fly.dev/healthz")
    assert "STILL NOT DRIVEN" in advisory
    assert stop(tmp_path, CLAIM) is not None


# ---- PostToolUse arm -----------------------------------------------------

def test_deploy_opens_marker_with_app_label(tmp_path):
    text = post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    assert "CONSUMER NOT DRIVEN" in text
    assert "brisken-expense-recon" in text


def test_vercel_deploy_opens_the_fetch_class_marker(tmp_path):
    text = post(tmp_path, "Bash", "vercel --prod")
    assert "VERIFY THE SHIPPED PAGE" in text
    assert "CONSUMER NOT DRIVEN" not in text


def test_force_deploy_script_opens_the_fetch_class_marker(tmp_path):
    assert "VERIFY THE SHIPPED PAGE" in post(
        tmp_path, "Bash", "tools/vercel-force-deploy.sh"
    )


# ---- Two deploy classes: what closes which ------------------------------

def test_webfetch_closes_a_server_rendered_deploy(tmp_path):
    """rule_behaviors already makes the no-slash URL fetch the correct check
    for a platform deploy; the gate must not tax it with a browser demand."""
    post(tmp_path, "Bash", "vercel --prod")
    assert "CONSUMER DRIVEN" in post(tmp_path, "WebFetch")
    assert stop(tmp_path, CLAIM) is None


def test_webfetch_does_not_close_an_app_deploy(tmp_path):
    """The SPA shell is what WebFetch sees; the rendered state is not in it."""
    post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    assert "STILL NOT DRIVEN" in post(tmp_path, "WebFetch")
    assert stop(tmp_path, CLAIM) is not None


def test_curl_closes_a_server_rendered_deploy(tmp_path):
    post(tmp_path, "Bash", "vercel --prod")
    assert "CONSUMER DRIVEN" in post(tmp_path, "Bash", "curl -sL https://unpauseai.com")
    assert stop(tmp_path, CLAIM) is None


def test_browser_drive_closes_a_server_rendered_deploy_too(tmp_path):
    post(tmp_path, "Bash", "vercel --prod")
    assert "CONSUMER DRIVEN" in post(tmp_path, "mcp__playwright__browser_navigate")


def test_vercel_deploy_then_claim_without_any_check_is_blocked(tmp_path):
    post(tmp_path, "Bash", "vercel --prod")
    assert stop(tmp_path, CLAIM) is not None


def test_agent_browser_closes_marker(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    assert "CONSUMER DRIVEN" in post(tmp_path, "Bash", "agent-browser open https://x")
    assert stop(tmp_path, CLAIM) is None


def test_playwright_snapshot_closes_marker(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    assert "CONSUMER DRIVEN" in post(tmp_path, "mcp__playwright__browser_snapshot")


def test_browser_drive_without_pending_deploy_is_silent(tmp_path):
    assert post(tmp_path, "mcp__playwright__browser_navigate") == ""


def test_healthz_without_pending_deploy_is_silent(tmp_path):
    assert post(tmp_path, "Bash", "curl -s https://x/healthz") == ""


def test_webfetch_without_pending_deploy_is_silent(tmp_path):
    assert post(tmp_path, "WebFetch") == ""


def test_unrelated_command_is_silent(tmp_path):
    assert post(tmp_path, "Bash", "uv run pytest -q") == ""


def test_build_is_not_a_deploy(tmp_path):
    assert post(tmp_path, "Bash", "npm run build") == ""
    assert stop(tmp_path, CLAIM) is None


# ---- Stop arm ------------------------------------------------------------

def test_no_deploy_no_block(tmp_path):
    assert stop(tmp_path, CLAIM) is None


def test_deploy_without_verification_claim_passes(tmp_path):
    post(tmp_path, "Bash", "flyctl deploy -a x")
    assert stop(tmp_path, NO_CLAIM) is None


def test_stop_hook_active_never_refires(tmp_path):
    """One turn, not a wedge -- the containment shape stop-b1-gate uses."""
    post(tmp_path, "Bash", "flyctl deploy -a x")
    assert stop(tmp_path, CLAIM, active=True) is None


def test_claim_inside_code_span_does_not_block(tmp_path):
    post(tmp_path, "Bash", "flyctl deploy -a x")
    assert stop(tmp_path, "Deployed. The log line reads `verified` there.") is None


def test_various_claim_spellings_block(tmp_path):
    for text in (
        "Deployed and the page is now live.",
        "v86 shipped and verified.",
        "Confirmed working after the deploy.",
        "Deployment is clean.",
    ):
        post(tmp_path, "Bash", "flyctl deploy -a x")
        assert stop(tmp_path, text) is not None, text


def test_unreadable_transcript_fails_open(tmp_path):
    post(tmp_path, "Bash", "flyctl deploy -a x")
    r = run_hook(
        HOOK,
        {"hook_event_name": "Stop", "transcript_path": str(tmp_path / "nope.jsonl")},
        env=env(tmp_path),
    )
    assert r.returncode == 0
    assert not r.stdout.strip()


def test_global_off_switch(tmp_path):
    e = {**env(tmp_path), "DEPLOY_CONSUMER_GATE_OFF": "1"}
    r = run_hook(HOOK, {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                        "tool_input": {"command": "flyctl deploy -a x"}}, env=e)
    assert not r.stdout.strip()
