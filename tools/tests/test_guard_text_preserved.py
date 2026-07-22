"""guard-text-preserved.py - the anti-content-deletion guard for weight runs.

A page-weight optimize run has one dominant cheat: deleting content makes the
page smaller, and `validate-html.py` still passes because the smaller page is
perfectly valid HTML. This guard is what makes such a run honest, so its two
halves are both load-bearing and both tested here:

  PERMISSIVE  every legitimate weight win (minifying CSS/JS, stripping
              comments, reindenting, slimming markup, entity churn) must NOT
              trip the guard, or the run has no moves left and converges at
              round 0.

  STRICT      every content loss (deleted copy, reworded copy, reordered
              copy, a deleted page) MUST trip it.

The strict half is the one that matters: without these assertions the guard
could be a no-op that always exits 0, and the run would look rigorous while
protecting nothing.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hooklib import REPO

GUARD = REPO / "tools" / "guard-text-preserved.py"

PAGE = """<!doctype html>
<html><head>
  <title>Alpha</title>
  <style>  .a { color : red }  </style>
  <!-- a comment that costs bytes -->
</head>
<body>
  <h1>Pricing</h1>
  <p>The engagement is  4,000 EUR &amp; runs for six weeks.</p>
  <script>  console.log( "hi" );  </script>
</body></html>
"""


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD), *args],
        capture_output=True, text=True,
    )


@pytest.fixture()
def site(tmp_path: Path) -> tuple[Path, Path]:
    """A one-page site plus its snapshotted baseline."""
    page = tmp_path / "index.html"
    page.write_text(PAGE, encoding="utf-8")
    baseline = tmp_path / "baseline-text.json"
    r = run("--snapshot", str(baseline), str(page))
    assert r.returncode == 0, r.stderr
    assert baseline.is_file()
    return page, baseline


def test_unchanged_page_passes(site):
    page, baseline = site
    r = run(str(baseline), str(page))
    assert r.returncode == 0, r.stderr
    assert "PASS" in r.stdout


# --- PERMISSIVE half: real weight wins must survive the guard --------------

@pytest.mark.parametrize("mutation,label", [
    (lambda s: s.replace("  .a { color : red }  ", ".a{color:red}"), "minify CSS"),
    (lambda s: s.replace('  console.log( "hi" );  ', 'console.log("hi")'), "minify JS"),
    (lambda s: s.replace("  <!-- a comment that costs bytes -->\n", ""), "strip comment"),
    (lambda s: s.replace("\n  ", "\n"), "reindent"),
    (lambda s: s.replace("<h1>Pricing</h1>", '<h1 class="t">Pricing</h1>'), "attr churn"),
    (lambda s: s.replace("&amp;", "&"), "entity unescape"),
])
def test_weight_wins_do_not_trip_guard(site, mutation, label):
    page, baseline = site
    page.write_text(mutation(PAGE), encoding="utf-8")
    assert page.read_text(encoding="utf-8") != PAGE, f"{label}: fixture no-op"
    r = run(str(baseline), str(page))
    assert r.returncode == 0, f"{label} should pass but failed:\n{r.stdout}{r.stderr}"


# --- STRICT half: content loss must be caught ------------------------------

@pytest.mark.parametrize("mutation,label", [
    (lambda s: s.replace("<h1>Pricing</h1>", ""), "deleted a heading"),
    (lambda s: s.replace("4,000 EUR", "4,000"), "dropped the currency"),
    (lambda s: s.replace("six weeks", "five weeks"), "reworded copy"),
    (lambda s: s.replace("<p>The engagement is  4,000 EUR &amp; runs for six weeks.</p>", ""),
     "deleted a paragraph"),
])
def test_content_loss_fails_guard(site, mutation, label):
    page, baseline = site
    page.write_text(mutation(PAGE), encoding="utf-8")
    r = run(str(baseline), str(page))
    assert r.returncode == 1, f"{label} should FAIL the guard but exited {r.returncode}"
    assert "DRIFT" in r.stderr


def test_deleted_page_fails_guard(site):
    """The largest possible 'win': remove the file entirely."""
    page, baseline = site
    page.unlink()
    r = run(str(baseline), str(page))
    assert r.returncode == 1
    assert "MISSING" in r.stderr


def test_shrinking_argv_cannot_hide_a_deleted_page(site, tmp_path):
    """The check loop is driven by the baseline, not argv.

    If it were driven by argv, dropping a page from the manifest's guard
    command would silently stop checking it - the guard would be neutered by
    an edit that never touches the guard script.
    """
    page, baseline = site
    other = tmp_path / "faq.html"
    other.write_text(PAGE.replace("Pricing", "FAQ"), encoding="utf-8")
    r = run("--snapshot", str(baseline), str(page), str(other))
    assert r.returncode == 0, r.stderr

    other.unlink()
    r = run(str(baseline), str(page))  # argv no longer mentions faq.html
    assert r.returncode == 1, "deleted page must fail even when omitted from argv"
    assert "MISSING" in r.stderr


def test_tags_are_replaced_by_a_separator_not_joined(tmp_path):
    """`<p>a</p><p>b</p>` must not normalize to `ab`.

    Naive tag-stripping welds adjacent words together, which would let a
    deletion be masked by a neighbouring insertion.
    """
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    a.write_text("<body><p>alpha</p><p>beta</p></body>", encoding="utf-8")
    b.write_text("<body><p>alphabeta</p></body>", encoding="utf-8")
    base = tmp_path / "base.json"
    assert run("--snapshot", str(base), str(a)).returncode == 0
    digests = json.loads(base.read_text(encoding="utf-8"))["pages"]
    a_digest = next(iter(digests.values()))

    base_b = tmp_path / "base_b.json"
    assert run("--snapshot", str(base_b), str(b)).returncode == 0
    b_digest = next(iter(json.loads(base_b.read_text(encoding="utf-8"))["pages"].values()))
    assert a_digest != b_digest


def test_unreadable_baseline_is_a_usage_error_not_a_pass(tmp_path):
    """Fail closed: a missing baseline must never read as 'nothing drifted'."""
    page = tmp_path / "index.html"
    page.write_text(PAGE, encoding="utf-8")
    r = run(str(tmp_path / "nope.json"), str(page))
    assert r.returncode == 2, f"expected usage error, got {r.returncode}"


def test_empty_baseline_is_rejected(tmp_path):
    """An empty page map would make the check loop vacuously pass."""
    page = tmp_path / "index.html"
    page.write_text(PAGE, encoding="utf-8")
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"_schema": "guard-text-preserved/1", "pages": {}}),
                    encoding="utf-8")
    r = run(str(base), str(page))
    assert r.returncode == 2
