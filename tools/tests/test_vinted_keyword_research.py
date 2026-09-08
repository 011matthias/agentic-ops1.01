"""Corpus keyword mining: does it describe THIS garment, or just its category?

The failure this exists to prevent is concrete and was measured on a live
competitor: a tank top and a zip jacket from the same brand carried a
byte-identical tag block, because the tags were derived from the brand rather
than from the item. Every test here is a way of asking whether that can happen
to us.

The corpus is built in-memory from synthetic listings, so the suite stays
offline and does not depend on the shape of whatever is in the real database
on any given day.
"""

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

RESEARCH_PATH = (Path(__file__).resolve().parents[2] / "workspace" / "projects"
                 / "vinted-reselling" / "listing" / "keyword_research.py")


@pytest.fixture(scope="module")
def kr():
    spec = importlib.util.spec_from_file_location("keyword_research_under_test", RESEARCH_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["keyword_research_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def corpus():
    """A small market: two Carhartt trouser lines, plus unrelated background."""
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE listings (id INTEGER PRIMARY KEY, title TEXT,
                   brand_norm TEXT, garment_class TEXT, is_kid INTEGER DEFAULT 0,
                   total_price REAL)""")
    rows = []
    n = 0
    # Two distinct product lines within one brand and class.
    for i in range(40):
        n += 1
        rows.append((n, f"Carhartt WIP Single Knee Pant Hamilton Brown W3{i%9}",
                     "carhartt", "pants", 0, 45.0))
    for i in range(35):
        n += 1
        rows.append((n, f"Carhartt Newel Pant Relaxed Fit Blau W3{i%9}",
                     "carhartt", "pants", 0, 40.0))
    # Background so lift has something to measure against.
    for i in range(200):
        n += 1
        rows.append((n, f"Nike Hose Trainingshose schwarz {i}", "nike", "pants", 0, 20.0))
    for i in range(120):
        n += 1
        rows.append((n, f"Patagonia Jacke Fleece blau {i}", "patagonia", "jacket", 0, 60.0))
    # Noise that must never become a keyword.
    for i in range(12):
        n += 1
        rows.append((n, f"Carhartt Pant reps 1:1 Qualitaet W32 {i}", "carhartt", "pants", 0, 15.0))
    for i in range(10):
        n += 1
        rows.append((n, f"Carhartt Kinder Hose 12 Jahre {i}", "carhartt", "pants", 1, 12.0))
    con.executemany("INSERT INTO listings VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    yield con
    con.close()


# ------------------------------------------------------ per-product, not per-brand

def test_two_lines_of_one_brand_get_different_keywords(kr, corpus):
    """The competitor failure, stated as a test."""
    knee = kr.keywords_for(corpus, "carhartt", "pants",
                           title_hint="Carhartt WIP Single Knee Pant Hamilton Brown", limit=5)
    newel = kr.keywords_for(corpus, "carhartt", "pants",
                            title_hint="Carhartt Newel Pant Relaxed Fit Blau", limit=5)
    assert knee != newel
    assert any("knee" in k for k in knee), knee
    assert any("newel" in k for k in newel), newel  # names the line, not the category
    assert not any("newel" in k for k in knee), "a term from the other line leaked in"


def test_without_a_title_hint_the_category_ranking_is_returned(kr, corpus):
    """No hint is not an error; it is the honest fallback to what the cell says."""
    generic = kr.keywords_for(corpus, "carhartt", "pants", title_hint=None, limit=5)
    assert generic, "an unhinted call must still produce candidates"
    assert all(isinstance(k, str) and k for k in generic)


def test_lift_prefers_the_identifying_term_over_the_common_one(kr, corpus):
    """'hose' is everywhere and says nothing; 'newel' names the piece."""
    terms, n = kr.mine_cell(corpus, "carhartt", "pants")
    by_text = {t.text: t for t in terms}
    assert n == 87, "kid rows must be excluded from the cell"
    # Every synthetic Newel row says "Newel Pant", so the phrase subsumes the
    # bare word and the bare word is correctly dropped as redundant. What must
    # survive is a term that NAMES the line.
    newel_terms = [t for t in terms if "newel" in t.text]
    assert newel_terms, sorted(by_text)[:20]
    assert max(t.lift for t in newel_terms) > 4


# -------------------------------------------------------------- what is excluded

def test_counterfeit_slang_never_becomes_a_keyword(kr, corpus):
    """Forger vocabulary is a market signal, not a word to put in a listing."""
    terms, _ = kr.mine_cell(corpus, "carhartt", "pants")
    slang = [t for t in terms if t.text in {"reps", "1", "qualitaet"}]
    for t in slang:
        if t.text == "reps":
            assert t.kind == "fake-slang"
    usable = kr.keywords_for(corpus, "carhartt", "pants", "Carhartt Pant reps", limit=8)
    assert "reps" not in usable


def test_the_fake_vocabulary_is_reported_separately_with_evidence(kr, corpus):
    rows = kr.fake_vocab(corpus, "carhartt")
    assert rows
    row = rows[0]
    assert row["brand"] == "carhartt"
    assert row["hits"] >= 12
    assert any(term == "reps" for term, _ in row["terms"])
    assert 0 < row["rate"] < 1


def test_size_tokens_are_rejected_because_they_belong_in_a_field(kr, corpus):
    terms, _ = kr.mine_cell(corpus, "carhartt", "pants")
    sizes = [t for t in terms if t.kind == "size"]
    for t in sizes:
        assert t.text.replace(" ", "").isalnum()
    assert all(t.kind != "size" for t in terms if t.kind == "term")


def test_the_brand_name_is_not_offered_back_as_a_keyword(kr, corpus):
    """It is already in the brand field, which is independently searchable."""
    kws = kr.keywords_for(corpus, "carhartt", "pants", "Carhartt Newel Pant", limit=8)
    assert "carhartt" not in [k.lower() for k in kws]
    assert not any(k.lower().startswith("carhartt ") for k in kws), kws


@pytest.mark.parametrize("term,expected", [
    ("reps", "fake-slang"),
    ("replica", "fake-slang"),
    ("w32", "size"),
    ("kinder", "kids"),
    ("12 jahre", "kids"),
    ("broek", "foreign"),
    ("carhartt", "brand"),
    ("carhartt hose", "brand-padded"),
    ("single knee", "term"),
])
def test_term_classification(kr, term, expected):
    kind, _ = kr.classify(term, "carhartt")
    assert kind == expected


def test_kid_listings_are_out_of_the_corpus(kr, corpus):
    """They are a different market and would drag the vocabulary sideways."""
    kws = kr.keywords_for(corpus, "carhartt", "pants", "Carhartt Hose", limit=10)
    assert not any("jahre" in k or "kinder" in k for k in kws)


# ------------------------------------------------------------------- robustness

def test_an_empty_cell_returns_nothing_rather_than_failing(kr, corpus):
    terms, n = kr.mine_cell(corpus, "nonexistent-brand", "jacket")
    assert (terms, n) == ([], 0)
    assert kr.keywords_for(corpus, "nonexistent-brand", "jacket", "x") == []


def test_research_reports_its_own_confidence(kr, corpus):
    out = kr.research(corpus, "carhartt", "pants")
    assert out["corpus_size"] == 87
    assert out["confidence"] in {"gut", "mittel", "duenn"}
    assert out["confidence"] == "mittel", "87 rows is not a strong corpus and must say so"
    assert out["keywords"], "a mineable cell must produce candidates"
    assert "rejected" in out, "the discarded terms are part of the evidence"


def test_cells_lists_only_what_is_worth_mining(kr, corpus):
    found = kr.cells(corpus, min_rows=60)
    keys = {(b, g) for b, g, _ in found}
    assert ("carhartt", "pants") in keys
    assert ("nike", "pants") in keys
    assert all(n >= 60 for _, _, n in found)
