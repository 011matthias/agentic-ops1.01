"""validate-platform-content.py: the em-dash scan's comment-skip heuristic.

Pins the 2026-07-22 blind spot. `check_em_dashes` skipped any line whose
stripped text started with `*`, a heuristic written for JS/TS block-comment
continuation lines (` * foo`). Applied to markdown it silently exempted every
bullet (`* item -- text`) and every bold-lead line (`**Phase 1** -- text`),
which is how four real ` -- ` em-dash substitutes shipped in
platform/src/content/proposals/ without the validator saying a word.

The skip is now JS/TS-family only. These tests hold both halves: markdown
`*` lines are scanned, TSX comment lines still skip.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load():
    """Import the hyphenated script as a module.

    It must be registered in sys.modules BEFORE exec_module: the file defines a
    @dataclass, and dataclasses resolves the owning module by name at class
    creation time."""
    path = REPO / "tools" / "validate-platform-content.py"
    spec = importlib.util.spec_from_file_location("validate_platform_content", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


VPC = _load()


def _rules(path: Path, body: str):
    lines = body.splitlines(keepends=True)
    return [f.rule for f in VPC.check_em_dashes(path, lines)]


def test_markdown_bold_lead_is_scanned():
    body = "**Phase 1 discovery** -- we map the pipeline.\n"
    assert _rules(Path("proposal.md"), body) == ["em-dash:dd-substitute"]


def test_markdown_bullet_is_scanned():
    body = "* bullet item -- with a substitute\n"
    assert _rules(Path("proposal.md"), body) == ["em-dash:dd-substitute"]


def test_markdown_indented_star_line_is_scanned():
    # The exact shape the old heuristic mistook for a block-comment body.
    body = "  * indented bullet -- still markdown, still renders\n"
    assert _rules(Path("proposal.md"), body) == ["em-dash:dd-substitute"]


def test_markdown_unicode_and_entity_on_star_lines():
    body = "* bullet — unicode\n**Lead** &mdash; entity\n"
    assert _rules(Path("proposal.md"), body) == [
        "em-dash:unicode", "em-dash:entity",
    ]


def test_plain_markdown_line_still_scanned():
    # The one case that worked before the fix; guards against over-correction.
    body = "Plain line -- always caught.\n"
    assert _rules(Path("proposal.md"), body) == ["em-dash:dd-substitute"]


def test_tsx_block_comment_continuation_still_skipped():
    body = (
        "/**\n"
        " * Block comment continuation -- must stay skipped.\n"
        " */\n"
        "// line comment -- also skipped\n"
    )
    assert _rules(Path("page.tsx"), body) == []


def test_tsx_rendered_line_is_flagged():
    body = "  return <p>Rendered body -- must be flagged</p>;\n"
    assert _rules(Path("page.tsx"), body) == ["em-dash:dd-substitute"]


def test_js_family_suffixes_cover_the_jsx_set():
    assert {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"} <= VPC.JS_FAMILY_SUFFIXES


def test_txt_cover_letter_star_line_is_scanned():
    # Upwork cover letters (.txt) are in scope and are not JS source.
    body = "* One line pitch -- the hook.\n"
    assert _rules(Path("cover-letter.txt"), body) == ["em-dash:dd-substitute"]


# --- content/blog scope (2026-07-22: the corpus surface must be gated) -------

def test_blog_markdown_is_in_scope():
    assert VPC.is_in_scope(VPC.BLOG / "some-post.md")


def test_blog_dir_is_in_default_scan():
    # The default walk must include content/blog, or an un-named run never
    # sees the corpus even though is_in_scope would accept the files.
    assert VPC.BLOG in {VPC.PUBLIC_APP, VPC.PROPOSALS, VPC.BLOG}
    # Behavioral half: a file physically under BLOG is yielded when it exists.
    if VPC.BLOG.exists():
        found = {p.resolve() for p in VPC.iter_target_files(None)}
        for p in VPC.BLOG.rglob("*.md"):
            assert p.resolve() in found


def test_blog_post_banned_word_is_flagged():
    body = "We leverage robust automation.\n"
    lines = body.splitlines(keepends=True)
    rules = [f.rule for f in VPC.check_banned_vocab(VPC.BLOG / "post.md", lines)]
    assert "banned-word:leverage" in rules and "banned-word:robust" in rules


def test_blog_post_is_exempt_from_proposal_heading_contract():
    # "## Timeline" is heading drift in a PROPOSAL; in a blog post it is just
    # a heading. The canonical-shape check must stay proposal-scoped.
    body = "## Timeline\n\nSome article content.\n"
    lines = body.splitlines(keepends=True)
    assert VPC.check_proposal_headings(VPC.BLOG / "post.md", lines) == []


def test_proposal_heading_drift_still_flagged():
    body = "## Timeline\n"
    lines = body.splitlines(keepends=True)
    findings = VPC.check_proposal_headings(VPC.PROPOSALS / "x.md", lines)
    assert [f.rule for f in findings] == ["heading-drift"]
