"""tools/scrub-test-data.py and the WW automations guard (layout plan W1-20).

The last test is the guard itself: no consumer-domain address anywhere under
workspace/clients/warme-wimmer/automations/. It passes trivially until the WW
import lands, and runs on every PR (CI 'every PR' step), so the import branch
cannot skip it. Every address is assembled at runtime from fake parts, so no
literal reaches the repo.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent
SCRIPT = TOOLS / "scrub-test-data.py"
spec = importlib.util.spec_from_file_location("scrub_test_data", SCRIPT)
std = importlib.util.module_from_spec(spec)
spec.loader.exec_module(std)

CONSUMER = "gm" + "ail.com"
BUSINESS = "heizung-fixture-qx.de"


def addr(local: str, domain: str = CONSUMER) -> str:
    return f"{local}@{domain}"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


# --- through main(): what an operator runs ----------------------------------

def test_write_rewrites_consumer_addresses_consistently(tmp_path, capsys):
    a, b = addr("anna.k"), addr("bernd.q")
    f1 = _write(tmp_path / "t1.test.mjs", f"const x = '{a}'; const y = '{b}';\n")
    f2 = _write(tmp_path / "t2.test.mjs", f"expect(dedupe(['{a}', '{a.upper()}']))\n")
    assert std.main(["--write", str(tmp_path)]) == 0
    t1, t2 = f1.read_text(encoding="utf-8"), f2.read_text(encoding="utf-8")
    assert CONSUMER not in t1 + t2
    # one person, one placeholder, across files and case
    assert t1 == "const x = 'person-1@example.com'; const y = 'person-2@example.com';\n"
    assert t2 == "expect(dedupe(['person-1@example.com', 'person-1@example.com']))\n"
    out = capsys.readouterr().out
    assert "anna" not in out and "bernd" not in out
    assert "2 file(s), 4 address occurrence(s) rewritten" in out


def test_check_exits_1_until_written_then_0(tmp_path):
    _write(tmp_path / "a.mjs", addr("c.r") + "\n")
    assert std.main(["--check", str(tmp_path)]) == 1
    assert std.main([str(tmp_path)]) == 0  # dry run never fails
    assert std.main(["--write", str(tmp_path)]) == 0
    assert std.main(["--check", str(tmp_path)]) == 0


def test_leaves_reserved_kept_and_business_addresses_by_default(tmp_path):
    text = " ".join([
        addr("x", "example.com"), addr("x", "mail.example.org"), addr("x", "host.test"),
        addr("sabine", "waerme-fixture.de"), addr("max.m", BUSINESS),
    ])
    f = _write(tmp_path / "a.mjs", text)
    assert std.main(["--write", "--keep-domain", "waerme-fixture.de", str(tmp_path)]) == 0
    assert f.read_text(encoding="utf-8") == text


def test_all_domains_rewrites_personal_local_part_and_keeps_domain(tmp_path):
    text = f"{addr('max.m', BUSINESS)} {addr('info', BUSINESS)} {addr('sabine', 'waerme-fixture.de')}"
    f = _write(tmp_path / "a.mjs", text)
    assert std.main(["--write", "--all-domains", "--keep-domain", "waerme-fixture.de",
                     str(tmp_path)]) == 0
    assert f.read_text(encoding="utf-8") == (
        f"person-1@{BUSINESS} {addr('info', BUSINESS)} {addr('sabine', 'waerme-fixture.de')}")


def test_numbering_starts_above_existing_placeholders_and_reruns_are_noops(tmp_path):
    f = _write(tmp_path / "a.mjs", f"person-7@example.com {addr('neu')}")
    assert std.main(["--write", str(tmp_path)]) == 0
    assert f.read_text(encoding="utf-8") == "person-7@example.com person-8@example.com"
    assert std.main(["--check", str(tmp_path)]) == 0


def test_preserves_crlf_and_skips_context_binary_and_missing(tmp_path, capsys):
    f = _write(tmp_path / "a.py", f"x = '{addr('d.e')}'\r\ny = 1\r\n")
    ctx = _write(tmp_path / "context" / "raw.json", addr("secret.person"))
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe" + addr("bin.x").encode("utf-16-le"))
    assert std.main(["--write", str(tmp_path)]) == 0
    assert f.read_bytes() == b"x = 'person-1@example.com'\r\ny = 1\r\n"
    assert ctx.read_text(encoding="utf-8") == addr("secret.person")
    assert std.main([str(tmp_path / "nope")]) == 2


def test_entry_point_runs_standalone(tmp_path):
    _write(tmp_path / "a.mjs", addr("f.g"))
    proc = subprocess.run([sys.executable, str(SCRIPT), "--check", str(tmp_path)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 1, proc.stderr
    assert "f.g" not in proc.stdout


# --- the guard ----------------------------------------------------------------

def test_ww_automations_hold_no_consumer_address():
    root = REPO / "workspace" / "clients" / "warme-wimmer" / "automations"
    if not root.exists():
        return  # nothing imported yet; the same assertion holds vacuously
    pending = std.plan([root])
    assert not pending, (
        "consumer-domain addresses under workspace/clients/warme-wimmer/automations/ "
        "(counts only): " + "; ".join(
            f"{f.relative_to(REPO).as_posix()} {dict(c)}" for f, _, c in pending)
        + ". Run `uv run tools/scrub-test-data.py --write <file>` on test data, or move "
        "a functional address into env/config.")
