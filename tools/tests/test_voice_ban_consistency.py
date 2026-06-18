"""Voice-ban consistency tests.

Backs the B2 consolidation (2026-06-18): the universal abbreviation-gloss
exemption set was triplicated (rule_deliverables.md, rule_human_communication.md
§7, and the enforcement copy in tools/validate-proposal.py) and had drifted.
rule_deliverables now cross-references rule_human_communication §7, and §7 is the
single documented home. This test keeps the single documented list and the single
enforced list (validate-proposal.py COMMON_ABBREVIATIONS) from diverging again.
"""
import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / ".claude" / "rules"


def _load_validate_proposal():
    path = REPO / "tools" / "validate-proposal.py"
    spec = importlib.util.spec_from_file_location("validate_proposal", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rule_universal_set() -> set[str]:
    text = (RULES / "rule_human_communication.md").read_text(encoding="utf-8")
    m = re.search(r"Universal exemptions:(.+?)\.", text, re.S)
    assert m, "'Universal exemptions:' list not found in rule_human_communication.md §7"
    return {tok.strip() for tok in m.group(1).replace("\n", " ").split(",") if tok.strip()}


def test_gloss_exemption_list_matches_enforcement():
    """rule §7 documented set == validate-proposal.py enforced set."""
    vp = _load_validate_proposal()
    rule_set = _rule_universal_set()
    tool_set = set(vp.COMMON_ABBREVIATIONS)
    assert rule_set == tool_set, (
        "gloss-exemption drift between rule §7 and validate-proposal.py: "
        f"only-in-rule={sorted(rule_set - tool_set)}, "
        f"only-in-tool={sorted(tool_set - rule_set)}"
    )


def test_gloss_list_deduped_from_deliverables():
    """rule_deliverables.md no longer carries its own copy of the abbreviation
    list; it cross-references rule_human_communication §7 (B2 consolidation)."""
    text = (RULES / "rule_deliverables.md").read_text(encoding="utf-8")
    assert "rule_human_communication" in text, "deliverables must cross-ref §7"
    # The full inline list (its tell: the EMEA, APAC, FAQ tail) must be gone.
    assert "EMEA, APAC, FAQ" not in text, "deliverables still inlines the gloss list"
