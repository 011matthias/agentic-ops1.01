"""send_email.py: the Graph-primary internal-telemetry sender.

Pins the two safety-critical properties: the sender is hard-pinned to the
user's own mailbox (this tool must never write from anyone else's), and the
env-file parser that feeds credentials behaves predictably. No test sends
mail; the live path is covered by weekly_synthesis --preflight.
"""
import importlib.util

from hooklib import TOOLS

spec = importlib.util.spec_from_file_location("send_email", TOOLS / "send_email.py")
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)


def test_sender_hard_pinned_to_own_mailbox():
    assert se.SENDER == "matthias.silva@brisken.com"
    assert se.DEFAULT_TO == "matthias.silva@brisken.com"


def test_env_file_points_at_primary_clone_not_relative():
    # worktrees have no gitignored files; the path must be absolute into
    # the primary clone
    assert se.ENV_FILE.lower().startswith(r"c:\users")
    assert "agentic-ops1\\workspace\\clients\\brisken\\context" in se.ENV_FILE


def test_parse_env_file():
    text = ("# comment\n"
            "\n"
            "BRISKEN_TENANT_ID=aa3b-tenant\n"
            "QUOTED='sec=ret'\n"
            'DQUOTED="v a l"\n'
            "no_equals_line skipped? no: has no =\n"
            "TRAILING = spaced \n")
    env = se.parse_env_file(text)
    assert env["BRISKEN_TENANT_ID"] == "aa3b-tenant"
    assert env["QUOTED"] == "sec=ret"
    assert env["DQUOTED"] == "v a l"
    assert env["TRAILING"] == "spaced"
    assert "# comment" not in env


def test_graph_send_refuses_tampered_sender(monkeypatch):
    monkeypatch.setattr(se, "SENDER", "dirk.neumann@brisken.com")
    creds = {k: "x" for k in se.GRAPH_KEYS}
    try:
        se.graph_send(creds, "s", "to@example.com", "b")
        raised = False
    except RuntimeError as e:
        raised = "not allowlisted" in str(e)
    assert raised, "tampered sender must be refused before any network call"
