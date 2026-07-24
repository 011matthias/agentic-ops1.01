"""validate-output.py structural slop detectors (rule_anti_slop Enforcement).

Two heuristics over markdown structure, both LOW / advisory:

  symmetry-collapse       N sibling bullets or N consecutive paragraphs whose
                          lengths cluster AND whose openings share one template
  per-category-narration  a table column or a `**Name** sentence` run where
                          every entry follows one grammar template

The negative cases are the calibration contract. rule_anti_slop's own "What is
NOT slop" list, short factual lists, numbered procedures, question checklists,
sequence-labelled timelines and pure data tables must all stay silent; a
regression there floods the post-write-gate advisory and buries the HIGH rules.
"""
import importlib.util
import json
import subprocess
import sys

from hooklib import REPO, TOOLS


def _load():
    path = TOOLS / "validate-output.py"
    spec = importlib.util.spec_from_file_location("validate_output", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vo = _load()


def cats(text: str) -> list[str]:
    return [h["category"] for h in vo.check_structural_slop(text)]


# --- positives ------------------------------------------------------------

# The 2026-06-01 meji shape rule_anti_slop cites: one intuitive structural rule,
# narrated once per category in the same sentence shape.
MEJI_SHAPE = """## Universe sizes

- The CEO segment is the smallest because the band skews toward owners.
- The CFO segment is the largest because the band skews toward finance.
- The COO segment is the middle one because the band skews toward ops.
"""


def test_templated_bullets_fire():
    hits = vo.check_structural_slop(MEJI_SHAPE)
    assert [h["category"] for h in hits] == ["symmetry-collapse"]
    assert hits[0]["line"] == 3          # first element of the run
    assert hits[0]["severity"] == "LOW"  # advisory, never a ship-blocker
    assert "Three-part lists where two work" in hits[0]["message"]


def test_templated_paragraphs_fire():
    text = (
        "## Why\n\n"
        "The first driver is the queue depth, which the scheduler never "
        "rebalances once a burst lands on one shard for long.\n\n"
        "The first driver is the retry storm, which the scheduler never "
        "dampens once a burst lands on one shard for long.\n\n"
        "The first driver is the lock churn, which the scheduler never "
        "releases once a burst lands on one shard for long.\n"
    )
    assert cats(text) == ["symmetry-collapse"]


def test_bold_definition_list_fires_as_per_category_narration():
    text = (
        "## Modes\n\n"
        "- **Slop:** padded writing that performs thoroughness for a reader.\n"
        "- **Cold:** clinical writing that performs rigor for a reader here.\n"
        "- **Warm:** direct writing that performs nothing for a reader now.\n"
    )
    hits = vo.check_structural_slop(text)
    assert [h["category"] for h in hits] == ["per-category-narration"]
    assert "Per-category narration" in hits[0]["message"]


def test_templated_table_column_fires():
    text = (
        "| Segment | Why the size lands where it does |\n"
        "|---|---|\n"
        "| CEO | The segment is small because the vendor under-indexes it. |\n"
        "| CFO | The segment is large because the vendor over-indexes it. |\n"
        "| COO | The segment is mid because the vendor evenly indexes it. |\n"
    )
    hits = vo.check_structural_slop(text)
    assert [h["category"] for h in hits] == ["per-category-narration"]
    assert hits[0]["line"] == 3  # first BODY row, not the header
    assert "Why the size lands where it does" in hits[0]["message"]


# --- negatives (the calibration contract) ---------------------------------

def test_rule_own_not_slop_list_is_silent():
    """rule_anti_slop's own 'What is NOT slop' bullets: variable sentence shape
    and unique information per row. If this fires, the heuristic is wrong."""
    text = (REPO / ".claude" / "rules" / "rule_anti_slop.md").read_text(
        encoding="utf-8")
    start = text.index("## What is NOT slop")
    section = text[start:text.index("## The golden middle")]
    assert cats(section) == []


def test_variable_shape_bullets_are_silent():
    text = (
        "## Notes\n\n"
        "- Apollo under-indexes UK family businesses at the owner band, so the "
        "CEO cohort lands smallest.\n"
        "- Lists with variable sentence shape and unique information per row.\n"
        "- Specific facts and numbers with sources, even when long; length "
        "earned by load-bearing detail is not slop.\n"
    )
    assert cats(text) == []


def test_short_factual_list_is_silent():
    text = (
        "## Facts\n\n"
        "- 295 rows, 40 columns\n"
        "- list id 7477347207906676736\n"
        "- 34 members, 90 opt-outs\n"
        "- Tier column: H5, T1, T2, T3\n"
    )
    assert cats(text) == []


def test_numbered_procedure_is_silent():
    text = (
        "## Protocol\n\n"
        "1. Information-per-token check. Does each sentence carry information "
        "the prior sentences did not establish?\n"
        "2. Symmetry-collapse check. Do the bullets read in the same shape "
        "with the same information density here?\n"
        "3. Heading-earns-it check. Does this heading add a navigation anchor "
        "that will actually be referenced?\n"
    )
    assert cats(text) == []


def test_question_checklist_is_silent():
    text = (
        "## Gate\n\n"
        "- Did the trigger receive the correct data from the live webhook?\n"
        "- Did the mapping write every field the downstream module reads?\n"
        "- Did the run finish inside the operation budget for the month?\n"
    )
    assert cats(text) == []


def test_sequence_labelled_timeline_is_silent():
    """`**Week 1:**` is an ordered list in disguise; sequence is the point."""
    text = (
        "## Timeline & Milestones\n\n"
        "**Week 1:** Discovery plus the first agent. Deliverable: a working "
        "webhook to classification pipeline in n8n.\n\n"
        "**Week 2:** Escalation pipeline plus a second agent. Deliverable: "
        "tiered routing with Slack alerts and CRM writes.\n\n"
        "**Week 3:** Third agent plus testing. Deliverable: the full system "
        "live with monitoring and a written runbook.\n"
    )
    assert cats(text) == []


def test_data_only_table_is_silent():
    text = (
        "| Date | Client | Type | Resolved |\n"
        "|---|---|---|---|\n"
        "| 2026-03-03 | kunde-inc | platform-limitation | Yes |\n"
        "| 2026-03-04 | meji-media | syntax-bug | Yes |\n"
        "| 2026-03-06 | brisken | missed-tool | No |\n"
    )
    assert cats(text) == []


def test_friction_register_is_silent():
    """598 rows of one uniform table by design; the canonical must-not-scream
    corpus for the table detector."""
    path = REPO / "docs" / "friction-register.md"
    assert cats(path.read_text(encoding="utf-8", errors="replace")) == []


def test_scaffolding_before_code_block_is_silent():
    text = (
        "## SPF\n\n"
        "The SPF push drops the Porkbun include.\n\n"
        "```\nv=spf1 include:_spf.google.com ~all\n```\n"
    )
    assert cats(text) == []


def test_fenced_code_never_forms_a_run():
    """Three same-shape lines inside a fence are code, not prose."""
    text = (
        "## Config\n\n"
        "```python\n"
        "- the alpha value is set here because the caller never overrides it\n"
        "- the gamma value is set here because the caller never overrides it\n"
        "- the delta value is set here because the caller never overrides it\n"
        "```\n"
    )
    assert cats(text) == []


def test_task_checkboxes_are_silent():
    text = (
        "## Targets\n\n"
        "- [ ] Enumerate every sendAnEmail module in the scenario before edits\n"
        "- [ ] Enumerate every env var that the deploy step reads at buildtime\n"
        "- [ ] Enumerate every spec whose frontmatter stage says build or test\n"
    )
    assert cats(text) == []


def test_all_placeholder_skeleton_alone_does_not_fire():
    """`X X X X` is the shape of any English sentence; without a shared literal
    anchor it is not evidence of a template."""
    assert vo._is_templated(["X X X X", "X X X X"]) is False
    assert vo._is_templated(["the X X is", "the X X is"]) is True
    assert vo._is_templated(["the X X is", "a X X is"]) is False


# --- suppression + wiring -------------------------------------------------

def test_suppression_marker_silences_a_run():
    text = MEJI_SHAPE.replace(
        "## Universe sizes\n\n",
        "## Universe sizes\n\n"
        "<!-- output-allow:symmetry-collapse parallelism is load-bearing -->\n",
    )
    assert cats(text) == []


def test_non_prose_suffix_skips_structural_checks(tmp_path):
    """HTML source lines would read as paragraphs; gate on a prose suffix."""
    body = MEJI_SHAPE
    md = tmp_path / "a.md"
    md.write_text(body, encoding="utf-8")
    html = tmp_path / "a.html"
    html.write_text(body, encoding="utf-8")
    md_cats = {h["category"] for h in vo.check_text(body, md)}
    html_cats = {h["category"] for h in vo.check_text(body, html)}
    assert "symmetry-collapse" in md_cats
    assert "symmetry-collapse" not in html_cats


def test_hits_capped_per_category():
    section = "".join(
        f"## S{n}\n\n"
        f"- The alpha segment is the smallest because the band skews one way.\n"
        f"- The gamma segment is the largest because the band skews two ways.\n"
        f"- The delta segment is the middle one because the band skews evenly.\n\n"
        for n in range(8)
    )
    hits = vo.check_structural_slop(section)
    assert len(hits) == vo.MAX_STRUCT_HITS_PER_CATEGORY


def test_json_mode_reports_slop(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text(MEJI_SHAPE, encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(TOOLS / "validate-output.py"), str(p),
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0  # JSON mode always exits 0 for the hook
    payload = json.loads(r.stdout)
    assert payload["by_category"]["symmetry-collapse"] == 1
    assert payload["by_severity"] == {"LOW": 1}


def test_text_mode_exit_contract_unchanged(tmp_path):
    clean = tmp_path / "clean.md"
    clean.write_text("# Title\n\nOne short paragraph, nothing templated.\n",
                     encoding="utf-8")
    dirty = tmp_path / "dirty.md"
    dirty.write_text(MEJI_SHAPE, encoding="utf-8")
    run = [sys.executable, str(TOOLS / "validate-output.py")]
    assert subprocess.run(run + [str(clean)], capture_output=True).returncode == 0
    assert subprocess.run(run + [str(dirty)], capture_output=True).returncode == 1
