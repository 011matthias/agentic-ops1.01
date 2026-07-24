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


# --- C5: Track-family detection by exact heading lines (2026-07-22 residual:
# the substring test exempted any file merely CONTAINING "## Track", so a
# "## Tracking metrics" heading switched off ALL heading checks) ------------

def _headings(body: str):
    lines = body.splitlines(keepends=True)
    return [f.rule for f in VPC.check_proposal_headings(VPC.PROPOSALS / "x.md", lines)]


def test_tracking_metrics_heading_does_not_exempt():
    assert _headings("## Tracking metrics\n\n## Timeline\n") == ["heading-drift"]


def test_exact_track_heading_still_exempts():
    assert _headings("## Track\n\n## Timeline\n") == []


def test_exact_centerpiece_heading_still_exempts():
    assert _headings("## Centerpiece\n\n## Timeline\n") == []


def test_prose_mention_of_track_heading_does_not_exempt():
    body = "We describe the ## Track shape here.\n\n## Timeline\n"
    assert _headings(body) == ["heading-drift"]


# --- C3: "not just X but Y" must cross commas/apostrophes/hyphens ------------

def _vocab_rules(path: Path, body: str):
    lines = body.splitlines(keepends=True)
    return [f.rule for f in VPC.check_banned_vocab(path, lines)]


def test_not_just_but_crosses_comma():
    rules = _vocab_rules(VPC.PROPOSALS / "x.md", "This is not just fast, but reliable.\n")
    assert "banned-phrase" in rules


def test_not_just_but_crosses_apostrophe_and_hyphen():
    body = "It's not just a client's one-off build but a re-usable system.\n"
    assert "banned-phrase" in _vocab_rules(VPC.PROPOSALS / "x.md", body)


def test_not_just_but_plain_form_still_flagged():
    body = "This is not just a sample but a framework.\n"
    assert "banned-phrase" in _vocab_rules(VPC.PROPOSALS / "x.md", body)


def test_not_just_but_never_spans_sentences():
    body = "This is not just it. But we also ship the docs.\n"
    assert "banned-phrase" not in _vocab_rules(VPC.PROPOSALS / "x.md", body)


def test_not_just_but_bounded_at_60_chars():
    filler = "a" * 70
    body = f"This is not just {filler} but more.\n"
    assert "banned-phrase" not in _vocab_rules(VPC.PROPOSALS / "x.md", body)


# --- C4: quoted-demotion is markdown-only; TSX string literals ARE the
# rendered copy (full severity), with a narrow nested-quotation carve --------

def _vocab(path: Path, body: str):
    lines = body.splitlines(keepends=True)
    return VPC.check_banned_vocab(path, lines)


def test_md_double_quoted_banned_word_stays_low():
    fs = _vocab(VPC.PROPOSALS / "x.md", '- "robust JSON parser" from the posting\n')
    assert [(f.rule, f.severity) for f in fs] == [("banned-word:robust", "LOW")]


def test_md_blockquote_banned_word_still_exempt():
    assert _vocab(VPC.PROPOSALS / "x.md", "> We need a robust system\n") == []


def test_tsx_string_literal_banned_word_full_severity():
    body = '  title: "A robust automation stack",\n'
    fs = _vocab(Path("page.tsx"), body)
    assert [(f.rule, f.severity) for f in fs] == [("banned-word:robust", "MEDIUM")]


def test_tsx_nested_quotation_specimen_demoted_low():
    # The oneproposal FAQ shape: rendered copy QUOTING a slop specimen.
    body = "    a: \"ChatGPT opens with 'I am excited to leverage my experience.' This won't.\",\n"
    fs = _vocab(Path("page.tsx"), body)
    assert [(f.rule, f.severity) for f in fs] == [("banned-word:leverage", "LOW")]
    assert "(quoted specimen — review)" in fs[0].text


def test_tsx_contraction_apostrophes_do_not_form_a_carve_span():
    # won't ... doesn't must not delimit a fake quotation around the word.
    body = '  a: "It won\'t streamline anything and it doesn\'t try to.",\n'
    fs = _vocab(Path("page.tsx"), body)
    assert [(f.rule, f.severity) for f in fs] == [("banned-word:streamline", "MEDIUM")]


# --- check_dead_links (2026-07-22 blind spot: the walk-up loop reduced every
# target to "/", which was unconditionally in the available set, so hit=True
# for every href and the check was a no-op) ---------------------------------

def _mk_public_app(tmp_path: Path) -> Path:
    app = tmp_path / "app" / "(public)"
    (app / "contact").mkdir(parents=True)
    (app / "contact" / "page.tsx").write_text("x", encoding="utf-8")
    (app / "proposals" / "[slug]").mkdir(parents=True)
    (app / "proposals" / "[slug]" / "page.tsx").write_text("x", encoding="utf-8")
    return app


def _dead_links(tmp_path, monkeypatch, href: str) -> list[str]:
    monkeypatch.setattr(VPC, "PUBLIC_APP", _mk_public_app(tmp_path))
    page = tmp_path / "page.tsx"
    page.write_text(f'<Link href="{href}">x</Link>\n', encoding="utf-8")
    return [f.rule for f in VPC.check_dead_links([page])]


def test_dead_href_is_flagged(tmp_path, monkeypatch):
    assert _dead_links(tmp_path, monkeypatch, "/really-dead") == ["dead-link"]


def test_deep_dead_href_is_flagged(tmp_path, monkeypatch):
    assert _dead_links(tmp_path, monkeypatch, "/really/dead/deep") == ["dead-link"]


def test_real_route_not_flagged(tmp_path, monkeypatch):
    assert _dead_links(tmp_path, monkeypatch, "/contact") == []


def test_dynamic_child_not_flagged(tmp_path, monkeypatch):
    # /proposals/foo should match the [slug] dynamic route (/proposals/*).
    assert _dead_links(tmp_path, monkeypatch, "/proposals/some-prospect") == []


def test_child_of_static_route_is_flagged(tmp_path, monkeypatch):
    # /contact exists but has no dynamic child route, so /contact/foo is dead.
    assert _dead_links(tmp_path, monkeypatch, "/contact/foo") == ["dead-link"]


def test_trailing_slash_route_not_flagged(tmp_path, monkeypatch):
    assert _dead_links(tmp_path, monkeypatch, "/contact/") == []
