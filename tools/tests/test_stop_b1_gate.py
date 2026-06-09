"""stop-b1-gate (Stop): block ONLY when the final assistant message defers.

The most-fired gate in the register, previously with no test. Drives the
classifier via a synthetic transcript JSONL (the hook reads transcript_path,
not stdin content). A block is exit 0 with {"decision": "block"} on stdout;
a clean/loop-guard/no-transcript case emits nothing.
"""
import json

from hooklib import run_hook


def _transcript(tmp_path, text):
    p = tmp_path / "transcript.jsonl"
    event = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }
    p.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return p


def _run(tmp_path, text=None, stop_hook_active=False, transcript_path=None):
    payload = {"stop_hook_active": stop_hook_active}
    if transcript_path is not None:
        payload["transcript_path"] = transcript_path
    elif text is not None:
        payload["transcript_path"] = str(_transcript(tmp_path, text))
    return run_hook("stop-b1-gate.py", payload)


def _blocks(p):
    out = p.stdout.strip()
    if not out:
        return False
    try:
        return json.loads(out.splitlines()[-1]).get("decision") == "block"
    except (json.JSONDecodeError, IndexError):
        return False


def test_clean_message_allows(tmp_path):
    assert not _blocks(_run(tmp_path, "Done. All 70 tests pass and the PR is merged."))


def test_deferral_blocks(tmp_path):
    assert _blocks(_run(tmp_path, "That's the core fix. Want me to deploy it next?"))


def test_quoted_example_allows(tmp_path):
    # #103 precision: the trigger phrase quoted as an EXAMPLE must not block.
    assert not _blocks(_run(tmp_path, 'The stop hook blocks closing offers like "want me to deploy".'))


def test_stop_hook_active_allows(tmp_path):
    # Loop guard: never re-fire on a continuation, even with a deferral present.
    assert not _blocks(_run(tmp_path, "Want me to deploy?", stop_hook_active=True))


def test_no_transcript_allows(tmp_path):
    # Fail-open: a missing/unreadable transcript must allow the stop.
    assert not _blocks(_run(tmp_path, transcript_path=str(tmp_path / "nonexistent.jsonl")))
