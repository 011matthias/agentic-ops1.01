"""Pure-function tests for tools/optimize_overview.py (no git needed)."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "..", "optimize_overview.py")
spec = importlib.util.spec_from_file_location("optimize_overview", MOD_PATH)
ov = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(ov)


MANIFEST = """---
tag: recon-match-v1
project: brisken
scorer: tools/scorers/recon-match-accuracy.py
direction: maximize
assets:
  - workspace/clients/brisken/automations/recon/rules/*.yaml
---
prose body
"""

TSV_CLOSED = (
    "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
    "0\taaaaaaa\t80.0\t0\tbaseline\tbaseline (asset as-is)\n"
    "1\tbbbbbbb\t83.5\t+3.5\tkeep\ttighten merchant normalization\n"
    "2\tccccccc\t81.0\tNA\tdiscard\tlooser fuzzy threshold\n"
    "3\tddddddd\t85.0\t+1.5\tkeep\tseed table from zoho history\n"
    "4\t-\tNA\tNA\tstopped\tgoal reached\n"
)

TSV_INTERRUPTED = (
    "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
    "0\taaaaaaa\t26145.0\t0\tbaseline\tbaseline (asset as-is)\n"
    "1\tbbbbbbb\t25425.0\t-720\tkeep\tstrip comments\n"
)


def test_parse_frontmatter_reads_project_and_direction():
    meta = ov.parse_frontmatter(MANIFEST)
    assert meta["project"] == "brisken"
    assert meta["direction"] == "maximize"
    assert meta["tag"] == "recon-match-v1"


def test_parse_frontmatter_tolerates_missing_or_bad_block():
    assert ov.parse_frontmatter("no frontmatter here") == {}
    assert ov.parse_frontmatter("---\n: bad: [yaml\n---\nx") == {}


def test_tsv_summary_closed_run():
    s = ov.tsv_summary(TSV_CLOSED)
    assert s["baseline"] == "80.0"
    assert s["best"] == "85.0"          # last keep row wins (scores ratchet)
    assert s["rounds"] == 3             # baseline + stopped rows excluded
    assert s["last_status"] == "stopped"


def test_tsv_summary_interrupted_run():
    s = ov.tsv_summary(TSV_INTERRUPTED)
    assert s["best"] == "25425.0"
    assert s["last_status"] == "keep"


def test_classify_matrix():
    closed = ov.tsv_summary(TSV_CLOSED)
    interrupted = ov.tsv_summary(TSV_INTERRUPTED)
    assert ov.classify("t", closed, None) == "CLOSED"
    assert ov.classify("t", interrupted, None) == "INTERRUPTED"
    assert ov.classify("t", closed, {"round": 3}) == "ACTIVE"
    assert ov.classify("t", None, None) == "INTERRUPTED"
