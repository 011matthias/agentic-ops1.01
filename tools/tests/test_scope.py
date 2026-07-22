"""_scope.py: the shared path -> category scope predicates used by the
.claude/hooks layer. These assertions pin the (intentionally distinct)
behavior of each predicate so a future edit to the shared segment data can't
silently change what any hook fires on. Imported directly (the module is a
plain stdlib lib, not a wired hook).
"""
import importlib.util
import sys

from hooklib import HOOKS


def _load_scope():
    path = HOOKS / "_scope.py"
    spec = importlib.util.spec_from_file_location("_scope", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_scope"] = mod
    spec.loader.exec_module(mod)
    return mod


S = _load_scope()


# --- in_deliverable_scope: html/md, the 5 deliverable segments -------------
def test_deliverable_html_in_public():
    assert S.in_deliverable_scope("/repo/platform/public/clients/x/index.html")


def test_deliverable_md_in_deliverables():
    assert S.in_deliverable_scope("workspace/clients/brisken/deliverables/statement.md")


def test_deliverable_rejects_non_doc_ext():
    assert not S.in_deliverable_scope("workspace/clients/brisken/deliverables/data.json")


def test_deliverable_rejects_outside_segments():
    assert not S.in_deliverable_scope("docs/sessions/2026-06-18.md")


def test_deliverable_empty_path():
    assert not S.in_deliverable_scope("")


# --- in_comms_scope: md, drafts/proposals + comms-log.md -------------------
def test_comms_drafts():
    assert S.in_comms_scope("workspace/clients/meji/context/drafts/note.md")


def test_comms_log_included():
    assert S.in_comms_scope("workspace/clients/meji/context/comms-log.md")


def test_comms_rejects_html():
    assert not S.in_comms_scope("workspace/clients/meji/context/drafts/note.html")


# --- .txt joins the comms / human-to-human sets (2026-07-22 blind-spot fix:
# Upwork cover letters and plain-text drafts bypassed the whole pipeline) ----
def test_comms_txt_draft_included():
    assert S.in_comms_scope("workspace/clients/meji/context/drafts/note.txt")


def test_comms_txt_cover_letter_included():
    assert S.in_comms_scope(
        "platform/src/content/proposals/menovia-upwork-cover-letter.txt"
    )


def test_h2h_txt_cover_letter_included():
    assert S.in_human_to_human_scope("/x/platform/src/content/proposals/cover.txt")


def test_deliverable_still_rejects_txt():
    # .txt is comms-shaped, not a deliverable; the deliverable validator's
    # HTML/markdown checks make no sense on plain text.
    assert not S.in_deliverable_scope("workspace/clients/b/deliverables/x.txt")


# --- in_human_to_human_scope: deliverables + drafts/proposals, NO comms-log -
def test_h2h_deliverable():
    # Absolute path: the "/platform/public/" segment needs its leading slash
    # (real hook invocations always pass absolute paths).
    assert S.in_human_to_human_scope("/repo/platform/public/docs/wimmer/index.html")


def test_h2h_drafts():
    assert S.in_human_to_human_scope("workspace/clients/meji/context/drafts/x.md")


def test_h2h_excludes_comms_log_by_design():
    # The mutating em-dash hook must NOT touch the verbatim sent-message record.
    assert not S.in_human_to_human_scope("workspace/clients/meji/context/comms-log.md")


# --- in_reference_anchor_scope: broad, not extension-gated -----------------
def test_anchor_any_file_in_client_tree():
    assert S.in_reference_anchor_scope("workspace/clients/brisken/deliverables/x.pdf")


def test_anchor_excludes_automations_specs_context():
    assert not S.in_reference_anchor_scope("workspace/clients/brisken/automations/run.py")
    assert not S.in_reference_anchor_scope("workspace/clients/brisken/specs/2-build/p1.md")
    assert not S.in_reference_anchor_scope("workspace/clients/brisken/context/notes.md")


def test_anchor_proposal_and_commslog_segments():
    assert S.in_reference_anchor_scope("platform/src/content/proposals/menovia.md")
    assert S.in_reference_anchor_scope("workspace/clients/x/context/comms-log.md")


# --- in_protected_segment: the auto-approve tree ---------------------------
def test_protected_tree_members():
    for seg in ("/.claude/", "/tools/", "/workspace/", "/docs/", "/platform/"):
        assert S.in_protected_segment(f"/repo{seg}file.py")


def test_protected_relative_prefix():
    assert S.in_protected_segment("tools/new.py")
    assert S.in_protected_segment(".claude/hooks/x.py")


def test_protected_rejects_outside():
    assert not S.in_protected_segment("/some/other/place/file.py")
    assert not S.in_protected_segment("scripts/x.py")  # scripts/ is not auto-approved


# --- segment data is single-sourced (no accidental drift) ------------------
def test_reference_anchor_superset_of_deliverable():
    for seg in S.DELIVERABLE_SEGMENTS:
        assert seg in S.REFERENCE_ANCHOR_SEGMENTS
