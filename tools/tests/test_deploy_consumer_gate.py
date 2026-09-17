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

import pytest

from hooklib import run_hook

HOOK = "deploy-consumer-gate.py"


def env(tmp_path) -> dict:
    return {
        "AGENTIC_OPS_SESSION_STATE": "",
        "DEPLOY_CONSUMER_MARKER": str(tmp_path / "marker.txt"),
    }


def post(
    tmp_path,
    tool: str,
    command: str | None = None,
    *,
    background: bool = False,
    response: dict | None = None,
) -> str:
    payload = {"hook_event_name": "PostToolUse", "tool_name": tool}
    if command is not None:
        payload["tool_input"] = {"command": command}
    if background:
        payload.setdefault("tool_input", {})["run_in_background"] = True
    if response is not None:
        payload["tool_response"] = response
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
    """Navigating gets you to the page; the SNAPSHOT is what sees it. Until
    2026-09-15 the navigate alone closed this, which is how the gate came to
    print "closed" about a drive that had asserted nothing."""
    post(tmp_path, "Bash", "flyctl deploy -a brisken-expense-recon")
    post(tmp_path, "mcp__playwright__browser_navigate")
    assert stop(tmp_path, CLAIM) is not None
    post(tmp_path, "mcp__playwright__browser_snapshot")
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
    assert "CONSUMER DRIVEN" in post(tmp_path, "mcp__playwright__browser_snapshot")


def test_vercel_deploy_then_claim_without_any_check_is_blocked(tmp_path):
    post(tmp_path, "Bash", "vercel --prod")
    assert stop(tmp_path, CLAIM) is not None


def test_agent_browser_closes_marker(tmp_path):
    """`open` reaches the page and reads nothing back; `snapshot` is the
    observation."""
    post(tmp_path, "Bash", "fly deploy")
    assert post(tmp_path, "Bash", "agent-browser open https://x") == ""
    assert stop(tmp_path, CLAIM) is not None
    assert "CONSUMER DRIVEN" in post(tmp_path, "Bash", "agent-browser snapshot -i")
    assert stop(tmp_path, CLAIM) is None


# ---- A drive has to have actually observed something --------------------
#
# 2026-09-15: the gate printed CONSUMER DRIVEN for a backgrounded command
# that had asserted nothing and later timed out. A gate closable by
# something that proves nothing protects less than it appears to, because
# its own advisory then reads back as evidence.


@pytest.mark.parametrize("cmd", [
    "agent-browser open https://x",
    "agent-browser click @e3",
    "agent-browser fill @e2 hello",
    "agent-browser close",
])
def test_navigation_only_commands_leave_the_marker_open(tmp_path, cmd):
    post(tmp_path, "Bash", "fly deploy")
    assert post(tmp_path, "Bash", cmd) == "", cmd
    assert stop(tmp_path, CLAIM) is not None


@pytest.mark.parametrize("cmd", [
    "agent-browser snapshot -i -c",
    "agent-browser screenshot out.png",
    "agent-browser get text @e1",
    "agent-browser get url",
    "agent-browser find role button click --name Save",
    "agent-browser eval --stdin",
    "agent-browser wait --text Arriving",
])
def test_observing_commands_close_the_marker(tmp_path, cmd):
    post(tmp_path, "Bash", "fly deploy")
    assert "CONSUMER DRIVEN" in post(tmp_path, "Bash", cmd), cmd


def test_a_backgrounded_drive_does_not_close_the_marker(tmp_path):
    """The 2026-09-15 shape: the command had produced no output yet."""
    post(tmp_path, "Bash", "fly deploy")
    text = post(
        tmp_path, "Bash", "agent-browser snapshot -i", background=True,
    )
    assert "DRIVE NOT COMPLETE" in text
    assert "backgrounded" in text
    assert stop(tmp_path, CLAIM) is not None


def test_a_failed_drive_does_not_close_the_marker(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    text = post(
        tmp_path, "Bash", "agent-browser snapshot -i",
        response={"is_error": True},
    )
    assert "DRIVE NOT COMPLETE" in text
    assert stop(tmp_path, CLAIM) is not None


def test_a_nonzero_exit_does_not_close_the_marker(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    assert "DRIVE NOT COMPLETE" in post(
        tmp_path, "Bash", "agent-browser snapshot -i",
        response={"returncode": 1},
    )


def test_an_unreadable_response_still_closes_the_marker(tmp_path):
    """Fail-open on the response shape. A gate that refuses to close on a
    drive that DID happen becomes noise, and noise gets approved
    reflexively -- the failure mode this whole hook exists to avoid."""
    post(tmp_path, "Bash", "fly deploy")
    assert "CONSUMER DRIVEN" in post(
        tmp_path, "Bash", "agent-browser snapshot -i", response={"x": "y"},
    )


# ---- 2026-09-16/17: holes the register kept logging after #885 -----------


def test_a_drive_the_harness_backgrounded_at_its_timeout_does_not_close(tmp_path):
    """A FOREGROUND command moved to the background at 120 s has no
    run_in_background in its input; the result says so instead (the shape
    items 73, 77, 80, 81 and 83 hit)."""
    post(tmp_path, "Bash", "fly deploy")
    text = post(
        tmp_path, "Bash",
        "agent-browser --session recon open https://x && agent-browser --session recon wait --load networkidle && agent-browser --session recon snapshot -i",
        response={"stdout": "", "stderr": "", "interrupted": False, "isImage": False,
                  "noOutputExpected": False, "backgroundTaskId": "bw73s5jh3",
                  "timedOutAfterMs": 120000},
    )
    assert "DRIVE NOT COMPLETE" in text
    assert stop(tmp_path, CLAIM) is not None


def test_a_background_notice_as_text_does_not_close(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    assert "DRIVE NOT COMPLETE" in post(
        tmp_path, "Bash", "agent-browser snapshot -i",
        response={"stdout": "Command running in background with ID: bx1. Output is being written to: C:\\t\\bx1.output"},
    )


def test_an_agent_browser_failure_line_does_not_close(tmp_path):
    post(tmp_path, "Bash", "fly deploy")
    text = post(
        tmp_path, "Bash", "agent-browser --cdp 9222 get url",
        response={"stdout": "✗ Failed to read: connection timed out (os error 10060)", "stderr": ""},
    )
    assert "DRIVE NOT COMPLETE" in text
    assert stop(tmp_path, CLAIM) is not None


@pytest.mark.parametrize("cmd", [
    "ls $LOCALAPPDATA/ms-playwright",
    'Get-ChildItem "$env:LOCALAPPDATA\\ms-playwright"',
    'uv run tools/pattern_rules.py test --text "agent-browser --session x snapshot -i" --event bash',
    'grep -rn "agent-browser snapshot" .claude/hooks',
    "echo agent-browser get url",
    "uv run --with playwright python -m playwright install chromium",
])
def test_a_mention_of_a_browser_command_does_not_close(tmp_path, cmd):
    post(tmp_path, "Bash", "fly deploy")
    assert post(tmp_path, "Bash", cmd, response={"stdout": "ok"}) == "", cmd
    assert stop(tmp_path, CLAIM) is not None


@pytest.mark.parametrize("cmd", [
    'B="agent-browser --session recon-item77"; $B eval "document.title"',
    "AB='agent-browser --session s'\n$AB snapshot -i",
    '$ab = "agent-browser"; & $ab get text @e1',
    'agent-browser --session s open https://x && agent-browser --session s wait --text "Arriving"',
    "npx playwright test e2e/smoke.spec.ts",
    "uv run --with playwright python drive.py",
    'uv run python -c "from playwright.sync_api import sync_playwright; print(1)"',
    "python - <<'EOF'\nfrom playwright.sync_api import sync_playwright\n"
    "with sync_playwright() as p:\n    b = p.chromium.connect_over_cdp('http://localhost:9333')\nEOF",
])
def test_a_real_observation_still_closes(tmp_path, cmd):
    post(tmp_path, "Bash", "fly deploy")
    assert "CONSUMER DRIVEN" in post(tmp_path, "Bash", cmd, response={"stdout": "ok"}), cmd
    assert stop(tmp_path, CLAIM) is None


def test_a_backgrounded_navigation_says_nothing_extra(tmp_path):
    """Navigation is silent whether or not it is backgrounded: it was never
    going to close the marker, so there is nothing to explain."""
    post(tmp_path, "Bash", "fly deploy")
    assert post(
        tmp_path, "Bash", "agent-browser open https://x", background=True,
    ) == ""


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


# ---- One marker per session ---------------------------------------------
#
# The marker used to be a single file in the machine's temp dir while this repo
# runs concurrent sessions by design. On 2026-09-15 a sibling session's Fly
# deploy blocked an unrelated session's Stop, naming a deploy that session had
# never run. The reverse is the expensive one: any session's browser drive
# closed any other session's marker.
#
# These drive the REAL per-session path (no explicit DEPLOY_CONSUMER_MARKER),
# pointing only the directory at tmp_path.


def sess_env(tmp_path) -> dict:
    return {
        "AGENTIC_OPS_SESSION_STATE": "",
        "DEPLOY_CONSUMER_MARKER": "",
        "DEPLOY_CONSUMER_MARKER_DIR": str(tmp_path),
    }


def post_as(tmp_path, session: str, tool: str, command: str | None = None,
            response: dict | None = None) -> str:
    payload = {"hook_event_name": "PostToolUse", "tool_name": tool,
               "session_id": session}
    if command is not None:
        payload["tool_input"] = {"command": command}
    if response is not None:
        payload["tool_response"] = response
    r = run_hook(HOOK, payload, env=sess_env(tmp_path))
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


def stop_as(tmp_path, session: str, text: str) -> str | None:
    r = run_hook(
        HOOK,
        {"hook_event_name": "Stop", "session_id": session,
         "transcript_path": transcript(tmp_path, text),
         "stop_hook_active": False},
        env=sess_env(tmp_path),
    )
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return None
    obj = json.loads(r.stdout)
    return obj.get("reason") if obj.get("decision") == "block" else None


def test_a_siblings_deploy_does_not_block_this_session(tmp_path):
    post_as(tmp_path, "session-A", "Bash", "flyctl deploy -a brisken-recon")
    assert stop_as(tmp_path, "session-B", CLAIM) is None


def test_the_deploying_session_is_still_blocked(tmp_path):
    post_as(tmp_path, "session-A", "Bash", "flyctl deploy -a brisken-recon")
    reason = stop_as(tmp_path, "session-A", CLAIM)
    assert reason is not None and "CONSUMER NOT DRIVEN" in reason


def test_a_siblings_browser_drive_does_not_close_this_marker(tmp_path):
    """The expensive direction: another session's snapshot must not stand in
    for the drive this session still owes."""
    post_as(tmp_path, "session-A", "Bash", "flyctl deploy -a brisken-recon")
    post_as(tmp_path, "session-B", "mcp__playwright__browser_snapshot",
            response={"ok": True})
    reason = stop_as(tmp_path, "session-A", CLAIM)
    assert reason is not None and "CONSUMER NOT DRIVEN" in reason


def test_own_browser_drive_still_closes_it(tmp_path):
    post_as(tmp_path, "session-A", "Bash", "flyctl deploy -a brisken-recon")
    post_as(tmp_path, "session-A", "mcp__playwright__browser_snapshot",
            response={"ok": True})
    assert stop_as(tmp_path, "session-A", CLAIM) is None


def test_a_payload_without_a_session_id_still_tracks(tmp_path):
    """No session_id falls back to the shared path. Occasionally shared beats
    silently untracked."""
    post_as(tmp_path, "", "Bash", "flyctl deploy -a brisken-recon")
    reason = stop_as(tmp_path, "", CLAIM)
    assert reason is not None and "CONSUMER NOT DRIVEN" in reason


# ---- Writing about a deploy is not deploying ----------------------------
#
# The gate sees the whole Bash command string, and a commit message lives
# inside it. Committing the session-scope fix opened a marker, because the
# message explains the bug and therefore contains the words "fly deploy".

COMMIT_ABOUT_A_DEPLOY = """git commit -F - <<'EOF'
hooks: scope the deploy-consumer marker

A sibling's fly deploy opened the marker and blocked another session.
EOF"""


def test_a_commit_message_about_a_deploy_opens_nothing(tmp_path):
    assert post(tmp_path, "Bash", COMMIT_ABOUT_A_DEPLOY) == ""


def test_a_commit_dash_m_about_a_deploy_opens_nothing(tmp_path):
    assert post(tmp_path, "Bash",
                'git commit -m "note: flyctl deploy broke the marker"') == ""


def test_a_pr_body_about_a_deploy_opens_nothing(tmp_path):
    assert post(tmp_path, "Bash",
                'gh pr create --title "x" --body "fixes the fly deploy gate"') == ""


def test_a_heredoc_piped_to_a_shell_still_opens(tmp_path):
    """The syntax is the same; the meaning is not. This one runs."""
    out = post(tmp_path, "Bash", "bash <<'EOF'\nflyctl deploy -a brisken-recon\nEOF")
    assert "CONSUMER NOT DRIVEN" in out


def test_a_real_deploy_beside_a_commit_still_opens(tmp_path):
    out = post(tmp_path, "Bash",
               'flyctl deploy -a brisken-recon && git commit -m "ship it"')
    assert "CONSUMER NOT DRIVEN" in out


def test_a_commit_message_does_not_close_an_open_marker(tmp_path):
    """The mirror of the same confusion: prose mentioning playwright must not
    count as a drive."""
    post(tmp_path, "Bash", "flyctl deploy -a brisken-recon")
    post(tmp_path, "Bash", 'git commit -m "ran playwright snapshot earlier"')
    assert stop(tmp_path, CLAIM) is not None
