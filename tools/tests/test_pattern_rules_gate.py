"""pattern-rules-gate: the generic runtime for `.claude/patterns/*.md`.

Every behavioral test drives the WIRED hook as a subprocess with a real hook
payload (rule_behaviors B2 fix-bites-the-caller), pointed at a tmp rules dir
through PATTERN_RULES_DIR. The library is unit-tested only where the parser's
edge cases are cheaper to pin directly, never instead of the subprocess path.
"""
import json
import time

import pytest

from hooklib import HOOKS, REPO, TOOLS, permission_decision, run_hook

import sys

sys.path.insert(0, str(HOOKS))
import _pattern_rules as pr  # noqa: E402

HOOK = "pattern-rules-gate.py"


def _rule(d, name, event, action="warn", pattern=None, conditions=None,
          enabled="true", body="Do the other thing.", message="Headline."):
    lines = ["---", f"name: {name}", f"enabled: {enabled}", f"event: {event}",
             f"action: {action}", f"message: {message}",
             "source: 2026-09-17 slow-path", "created: 2026-09-17"]
    if pattern is not None:
        lines.append(f"pattern: '{pattern}'")
    if conditions is not None:
        lines.append("conditions:")
        for fld, op, pat in conditions:
            lines += [f"  - field: {fld}", f"    operator: {op}", f"    pattern: '{pat}'"]
    lines += ["---", body, ""]
    (d / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    rules = tmp_path / "patterns"
    rules.mkdir()
    return {
        "dir": rules,
        "env": {
            "PATTERN_RULES_DIR": str(rules),
            "PATTERN_RULES_PENDING": str(tmp_path / "pending.json"),
            "PATTERN_RULES_HOOK_LOG": str(tmp_path / "hook-log.txt"),
        },
        "log": tmp_path / "hook-log.txt",
        "tmp": tmp_path,
    }


def _bash(env, command):
    return run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                           "tool_input": {"command": command}}, env=env["env"])


def _write(env, path, content, tool="Write"):
    ti = {"file_path": path}
    if tool == "Write":
        ti["content"] = content
    else:
        ti.update({"old_string": "x", "new_string": content})
    return run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": tool,
                           "tool_input": ti}, env=env["env"])


def _prompt(env, text, session="s1"):
    return run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "prompt": text,
                           "session_id": session}, env=env["env"])


def _stop(env, text, session="s1", active=False):
    t = env["tmp"] / f"transcript-{time.monotonic_ns()}.jsonl"
    entries = [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {"type": "assistant", "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": text}]}},
    ]
    t.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return run_hook(HOOK, {"hook_event_name": "Stop", "transcript_path": str(t),
                           "session_id": session, "stop_hook_active": active},
                    env=env["env"])


def _json(p):
    out = p.stdout.strip()
    return json.loads(out) if out else None


def _context(p):
    obj = _json(p) or {}
    return (obj.get("hookSpecificOutput") or {}).get("additionalContext", "")


# ------------------------------------------------------------ bash event
def test_bash_match_warns_with_rule_text(env):
    _rule(env["dir"], "warn-foo", "bash", pattern=r"\bfoo\s+--bar\b", body="Use baz.")
    p = _bash(env, "foo --bar")
    assert p.returncode == 0
    assert permission_decision(p.stdout) is None
    ctx = _context(p)
    assert "[PATTERN WARN: warn-foo] Headline." in ctx and "Use baz." in ctx


def test_bash_no_match_is_silent(env):
    _rule(env["dir"], "warn-foo", "bash", pattern=r"\bfoo\s+--bar\b")
    assert _bash(env, "echo hello").stdout.strip() == ""


def test_bash_command_is_normalized_like_the_other_gates(env):
    # _shell.normalize_command reduces `& "C:\x\vercel.cmd"` to `vercel`.
    _rule(env["dir"], "warn-vercel-deploy", "bash", pattern=r"\bvercel\s+deploy\b")
    p = _bash(env, '& "C:\\tools\\node\\vercel.cmd" deploy --prod')
    assert "warn-vercel-deploy" in _context(p)


def test_ask_action_returns_permission_ask(env):
    _rule(env["dir"], "require-confirm-drop", "bash", action="ask", pattern=r"\bdrop\s+table\b")
    p = _bash(env, "psql -c 'drop table x'")
    assert permission_decision(p.stdout) == "ask"
    assert "require-confirm-drop" in _json(p)["hookSpecificOutput"]["permissionDecisionReason"]


def test_block_action_denies_and_strongest_action_wins(env):
    _rule(env["dir"], "warn-rm", "bash", pattern=r"\brm\b")
    _rule(env["dir"], "block-rm-rf", "bash", action="block", pattern=r"\brm\s+-rf\b")
    p = _bash(env, "rm -rf build")
    assert permission_decision(p.stdout) == "deny"
    reason = _json(p)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "block-rm-rf" in reason and "warn-rm" in reason


def test_disabled_rule_is_silent(env):
    _rule(env["dir"], "block-foo", "bash", action="block", pattern=r"foo", enabled="false")
    assert _bash(env, "foo").stdout.strip() == ""


def test_rule_for_another_event_does_not_fire(env):
    _rule(env["dir"], "warn-foo", "prompt", pattern=r"foo")
    assert _bash(env, "foo").stdout.strip() == ""


# ------------------------------------------------------------ file event
def test_conditions_are_and_logic(env):
    _rule(env["dir"], "block-secret-in-docs", "file", action="block", conditions=[
        ("file_path", "regex_match", r"/docs/"),
        ("new_text", "contains", "SECRET"),
    ])
    assert permission_decision(_write(env, "C:/r/docs/a.md", "has SECRET").stdout) == "deny"
    assert _write(env, "C:/r/docs/a.md", "clean").stdout.strip() == ""
    assert _write(env, "C:/r/tools/a.py", "has SECRET").stdout.strip() == ""


def test_file_event_reads_edit_new_string(env):
    _rule(env["dir"], "warn-todo", "file", pattern=r"\bTODO\b")
    assert "warn-todo" in _context(_write(env, "C:/r/a.py", "# TODO later", tool="Edit"))


def test_windows_backslash_path_matches_forward_slash_rule(env):
    _rule(env["dir"], "warn-drafts", "file", conditions=[
        ("file_path", "regex_match", r"/context/drafts/"),
        ("new_text", "regex_match", r"."),
    ])
    assert "warn-drafts" in _context(_write(env, "C:\\r\\context\\drafts\\x.md", "hi"))


def test_allow_marker_suppresses_file_rule(env):
    _rule(env["dir"], "block-foo", "file", action="block", pattern=r"foo")
    p = _write(env, "C:/r/a.md", "foo <!-- pattern-allow: block-foo (client quote) -->")
    assert p.stdout.strip() == ""


# ---------------------------------------------------------- prompt event
def test_prompt_warn_adds_context(env):
    _rule(env["dir"], "warn-deploy-friday", "prompt", pattern=r"(?i)deploy on friday")
    assert "warn-deploy-friday" in _context(_prompt(env, "Please deploy on Friday"))


def test_prompt_code_fence_and_quotes_are_stripped(env):
    # The 2026-05-19 self-referential false positive: a trigger phrase quoted
    # as an example must not fire.
    _rule(env["dir"], "warn-deploy-friday", "prompt", pattern=r"(?i)deploy on friday")
    assert _prompt(env, "The rule matches ```deploy on friday``` text").stdout.strip() == ""
    assert _prompt(env, 'It catches "deploy on friday" phrasing').stdout.strip() == ""


def test_prompt_block_uses_decision_block(env):
    _rule(env["dir"], "block-paste-token", "prompt", action="block", pattern=r"ghp_[A-Za-z0-9]{10}")
    obj = _json(_prompt(env, "here is ghp_abcdefghijklmnop"))
    assert obj["decision"] == "block" and "block-paste-token" in obj["reason"]


# ------------------------------------------------------------ stop event
def test_stop_block_blocks(env):
    _rule(env["dir"], "block-offer", "stop", action="block", pattern=r"(?i)say the word")
    obj = _json(_stop(env, "Done. Say the word and I will ship it."))
    assert obj["decision"] == "block" and "block-offer" in obj["reason"]


def test_stop_block_honors_stop_hook_active(env):
    _rule(env["dir"], "block-offer", "stop", action="block", pattern=r"(?i)say the word")
    assert _stop(env, "Say the word.", active=True).stdout.strip() == ""


def test_stop_code_stripped(env):
    _rule(env["dir"], "block-offer", "stop", action="block", pattern=r"(?i)say the word")
    assert _stop(env, "The gate catches `say the word` offers.").stdout.strip() == ""


def test_stop_warn_is_parked_then_delivered_on_next_prompt_once(env):
    _rule(env["dir"], "warn-queue", "stop", pattern=r"(?i)queued")
    stop = _stop(env, "3 edits queued.", session="abc")
    assert stop.stdout.strip() == ""  # Stop has no context channel
    first = _context(_prompt(env, "next task", session="abc"))
    assert "warn-queue" in first and "previous closing message" in first
    assert _prompt(env, "another", session="abc").stdout.strip() == ""
    # another session never sees it
    _stop(env, "3 edits queued.", session="abc")
    assert _prompt(env, "hi", session="other").stdout.strip() == ""


def test_stop_missing_transcript_is_silent(env):
    _rule(env["dir"], "block-offer", "stop", action="block", pattern=r".")
    p = run_hook(HOOK, {"hook_event_name": "Stop", "transcript_path": "nope.jsonl"},
                 env=env["env"])
    assert p.returncode == 0 and p.stdout.strip() == ""


# ------------------------------------------------------------ fail-open
def test_malformed_rule_is_skipped_logged_and_others_still_fire(env):
    (env["dir"] / "warn-broken.md").write_text("---\nname: warn-broken\nevent bash\n---\nx\n",
                                               encoding="utf-8")
    (env["dir"] / "warn-badregex.md").write_text(
        "---\nname: warn-badregex\nenabled: true\nevent: bash\naction: warn\n"
        "pattern: '(unclosed'\n---\nx\n", encoding="utf-8")
    _rule(env["dir"], "warn-foo", "bash", pattern=r"foo")
    p = _bash(env, "foo")
    assert p.returncode == 0
    assert "warn-foo" in _context(p)
    log = env["log"].read_text(encoding="utf-8")
    assert "SKIP malformed warn-broken.md" in log and "SKIP malformed warn-badregex.md" in log


def test_garbage_payload_exits_zero(env):
    import subprocess
    p = subprocess.run([sys.executable, str(HOOKS / HOOK)], input="not json",
                       capture_output=True, text=True, timeout=30)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_hook_is_fast_enough(env):
    for i in range(20):
        _rule(env["dir"], f"warn-rule-{i}", "bash", pattern=rf"\bcmd{i}\b")
    start = time.perf_counter()
    _bash(env, "cmd19 --flag")
    elapsed = time.perf_counter() - start
    # 200 ms is the design budget for the hook itself; the bound here is loose
    # because it includes interpreter startup on a cold CI runner.
    assert elapsed < 2.0, f"hook took {elapsed:.3f}s"


# -------------------------------------------------------- the real rules
def test_repo_rules_lint_clean():
    rules, errors = pr.load_rules(str(REPO / ".claude" / "patterns"))
    assert not errors, errors
    assert rules, "no seed rules found"
    problems = {r.name: pr.lint_rule(r) for r in rules}
    assert not any(problems.values()), problems


SEEDS = [
    ("block-pre-conceding-comms", "file",
     {"file_path": "C:/repo/workspace/clients/meji-media/context/drafts/reply.md",
      "new_text": "Understood on the cap, that's a fair guardrail and I'm happy to lower it."},
     {"file_path": "C:/repo/workspace/clients/meji-media/context/drafts/reply.md",
      "new_text": "The retainer reflects the scope we agreed on in March."}),
    ("block-pre-conceding-comms", "file",
     {"file_path": "C:/repo/workspace/clients/meji-media/context/comms-log.md",
      "new_text": "Thanks for being direct, you’re right to flag the hours."},
     {"file_path": "C:/repo/docs/friction-register.md",
      "new_text": "banned: happy to lower, fair guardrail"}),
    ("warn-transient-queue-phrasing", "stop",
     {"final_text": "8 queued edits will apply when the file unlocks."},
     {"final_text": "All 8 edits applied after the lock cleared."}),
    ("warn-transient-queue-phrasing", "stop",
     {"final_text": "I will retry when the deploy lock unlocks."},
     {"final_text": "Retried in a background loop; the deploy is live."}),
    ("warn-git-add-all", "bash",
     {"command": "git add -A && git commit -m wip"},
     {"command": "git add .claude/patterns/warn-git-add-all.md tools/pattern_rules.py"}),
    ("warn-git-add-all", "bash",
     {"command": "git -C /c/Repo/x add ."},
     {"command": "git add ./tools/x.py"}),
    ("warn-start-process-working-file", "bash",
     {"command": 'Start-Process "C:/Repo/docs/spec.md"'},
     {"command": 'Start-Process msedge -ArgumentList "file:///c:/x/deck.html"'}),
    ("warn-start-process-working-file", "bash",
     {"command": "Start-Process C:/Repo/out/deck.html"},
     {"command": "Start-Process C:/Repo/out/report.pdf"}),
    ("warn-git-exit-masked-by-pipe", "bash",
     {"command": "git -C /c/x rebase origin/main 2>&1 | tail -1 && git -C /c/x branch -f b HEAD~1"},
     {"command": "git log --oneline -3 | head -2 && echo done"}),
    ("warn-git-exit-masked-by-pipe", "bash",
     {"command": "git push -q -u origin br 2>&1 | grep -v remote | tail -1 && gh pr create"},
     {"command": "git -C /c/x rebase origin/main > log 2>&1; echo $?"}),
]


@pytest.mark.parametrize("name,event,hit,miss", SEEDS)
def test_seed_rule_fires_on_incident_and_not_on_benign(name, event, hit, miss):
    rules, _ = pr.load_rules(str(REPO / ".claude" / "patterns"))
    rule = [r for r in rules if r.name == name]
    assert rule, f"seed {name} missing"
    assert [r.name for r in pr.evaluate(rule, event, hit)] == [name]
    assert pr.evaluate(rule, event, miss) == []


def test_seed_queue_rule_covers_a_sentence_stop_b1_misses():
    # The rule is not a duplicate: stop-b1-gate's passive-queue pattern does
    # not match the literal 2026-05-11 sentence.
    import importlib.util
    spec = importlib.util.spec_from_file_location("b1", HOOKS / "stop-b1-gate.py")
    b1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b1)
    sentence = "8 queued edits will apply when the file unlocks."
    assert not any(rx.search(sentence) for rx in b1.COMPILED)


# --------------------------------------------------------------- library
def test_parser_quoting_and_lists():
    meta, body = pr.parse_frontmatter(
        "---\nname: warn-x\nenabled: false\npattern: 'it''s \\s+'\n"
        'message: "say \\"hi\\""\nconditions:\n  - field: command\n    operator: contains\n'
        "    pattern: a: b\n---\nbody text\n")
    assert meta["enabled"] is False
    assert meta["pattern"] == "it's \\s+"
    assert meta["message"] == 'say "hi"'
    assert meta["conditions"] == [{"field": "command", "operator": "contains", "pattern": "a: b"}]
    assert body == "body text"


@pytest.mark.parametrize("text,err", [
    ("name: x\n", "opening"),
    ("---\nname: x\n", "closing"),
    ("---\nname: x\nname: y\n---\n", "duplicate"),
    ("---\nname: x\nevent: bash\n---\n", "exactly one"),
    ("---\nevent: bash\npattern: a\nconditions:\n  - field: command\n    pattern: b\n---\n", "exactly one"),
    ("---\nevent: nope\npattern: a\n---\n", "event must be"),
    ("---\nevent: bash\nconditions:\n  - field: file_path\n    pattern: b\n---\n", "not available"),
    ("---\nevent: bash\nconditions:\n  - field: command\n    operator: fuzzy\n    pattern: b\n---\n", "operator"),
])
def test_build_rule_rejects(text, err):
    with pytest.raises(pr.RuleError, match=err):
        pr.build_rule("x.md", text)


def test_lint_catches_contract_breaks(tmp_path):
    _rule(tmp_path, "block-mismatch", "stop", action="ask", pattern="x", body="")
    rule = pr.build_rule(str(tmp_path / "block-mismatch.md"),
                         (tmp_path / "block-mismatch.md").read_text(encoding="utf-8"))
    problems = " | ".join(pr.lint_rule(rule))
    assert "not expressible" in problems
    assert "block-* rule must use action block" in problems
    assert "body" in problems


def test_cli_lint_exit_codes(tmp_path):
    import subprocess
    good = tmp_path / "good"
    good.mkdir()
    _rule(good, "warn-ok", "bash", pattern="x")
    bad = tmp_path / "bad"
    bad.mkdir()
    _rule(bad, "nope", "bash", pattern="x")  # not verb-first
    cli = str(TOOLS / "pattern_rules.py")
    ok = subprocess.run([sys.executable, cli, "lint"], capture_output=True, text=True,
                        env={**__import__("os").environ, "PATTERN_RULES_DIR": str(good)})
    ko = subprocess.run([sys.executable, cli, "lint"], capture_output=True, text=True,
                        env={**__import__("os").environ, "PATTERN_RULES_DIR": str(bad)})
    assert ok.returncode == 0, ok.stdout
    assert ko.returncode == 1 and "verb-first" in ko.stdout


def test_digest_extracts_user_turns_for_the_miner(tmp_path):
    import subprocess
    t = tmp_path / "s.jsonl"
    entries = [
        {"type": "user", "message": {"role": "user", "content": "Build the thing <system-reminder>secret ctx</system-reminder>"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "I ran git add -A and pushed."}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
        {"type": "user", "message": {"role": "user", "content": "No, don't use git add -A here, stage paths."}},
    ]
    t.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    cli = str(TOOLS / "pattern_rules.py")
    out = subprocess.run([sys.executable, cli, "digest", "--transcript", str(t)],
                         capture_output=True, text=True, timeout=30).stdout
    assert out.count("user:") == 2
    assert "secret ctx" not in out and "tool_result" not in out
    assert "* user: No, don't use git add -A" in out
    assert "agent: ...I ran git add -A and pushed." in out
    missing = subprocess.run([sys.executable, cli, "digest", "--session", "no-such-session"],
                             capture_output=True, text=True, timeout=30)
    assert missing.returncode == 0 and missing.stdout.strip() == "transcript unavailable"
