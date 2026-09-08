"""Listing keyword engine: the rules that keep a listing visible on Vinted.

The negative cases are the contract. Vinted hides or deletes listings that name
irrelevant brands or pile on tags, and it does not refund the paid push on a
hidden listing, so a validator that waves those through is worse than none.
The positive cases guard the opposite failure: a validator so eager that a
clean listing cannot pass is one nobody will keep running.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ENGINE_PATH = (Path(__file__).resolve().parents[2] / "workspace" / "projects"
               / "vinted-reselling" / "listing" / "keyword_engine.py")


@pytest.fixture(scope="module")
def ke():
    spec = importlib.util.spec_from_file_location("keyword_engine_under_test", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["keyword_engine_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


JEANS = {
    "brand": "Levis", "model": "501", "type": "Jeans", "garment_class": "pants",
    "size": "W32 L32", "color": "Dunkelblau", "material": "100% Baumwolle",
    "condition": "Sehr gut", "schnitt": "Straight Leg", "leibhoehe": "Mid Rise",
    "waschung": "Stonewashed", "verschluss": "Button Fly", "era": "90s",
    "measurements": {"Bundweite": "40cm"},
}
JACKET = {
    "brand": "Carhartt", "type": "Jacke", "garment_class": "jacket", "size": "L",
    "color": "Braun", "condition": "Gut", "bauform": "Arbeitsjacke",
    "futter": "Teddyfutter", "kapuze": "ohne Kapuze",
}


# --------------------------------------------------------- dimension anchoring

def test_keywords_differ_by_garment_class_not_just_by_brand(ke):
    """The failure of the tool this replaces: one tag block reused per brand.

    A live Lonsdale tank top carried the identical block to a Lonsdale zip
    jacket. Class axes are what make a keyword set describe THIS garment.
    """
    jeans_kw = set(ke.build_keywords(JEANS)[0])
    jacket_kw = set(ke.build_keywords(JACKET)[0])
    assert {"Straight Leg", "Stonewashed"} <= jeans_kw
    assert {"Arbeitsjacke", "Teddyfutter"} <= jacket_kw
    assert not (jeans_kw & jacket_kw), "two different garments share no keywords"


def test_every_keyword_traces_to_a_supplied_field(ke):
    """No invented attributes: a keyword nobody verified is a false claim."""
    sparse = {"brand": "Patagonia", "type": "Fleece", "garment_class": "sweater",
              "size": "M"}
    kws, notes = ke.build_keywords(sparse)
    supplied = " ".join(str(v) for v in sparse.values()).lower()
    for kw in kws:
        assert all(part.lower() in supplied for part in kw.split()), \
            f"{kw!r} is not backed by any supplied field"
    assert any("nicht befuellte Achsen" in n for n in notes)


def test_keyword_count_is_capped_and_the_drop_is_reported(ke):
    """Tag volume is a documented reason to hide a listing, so the cap is hard."""
    kws, notes = ke.build_keywords(JEANS)
    assert len(kws) <= ke.MAX_KEYWORDS
    assert any("gekuerzt" in n for n in notes), "a silent truncation hides the loss"


def test_title_leads_with_the_class_defining_attribute(ke):
    """Jeans are distinguished by cut, jackets by shape; the title says which."""
    assert "Straight Leg" in ke.build_title(JEANS)
    assert "Arbeitsjacke" in ke.build_title(JACKET)
    assert ke.build_title(JEANS).startswith("Levis 501 Jeans |")


def test_a_class_without_axes_says_so_rather_than_inventing_them(ke):
    kws, notes = ke.build_keywords({"brand": "Nike", "type": "Cap",
                                    "garment_class": "other", "size": "One"})
    assert any("keine Dimensions-Achsen" in n for n in notes)


# ------------------------------------------------------- catalog-rule guards

def test_foreign_brand_in_plain_text_is_a_problem(ke):
    report = ke.validate("Carhartt Jacke", "Passt gut zu Nike Schuhen.", "Carhartt")
    assert not report["ok"]
    assert any("nike" in p for p in report["problems"])


def test_foreign_brand_hidden_in_a_tag_compound_is_caught(ke):
    """The live shape: #niketrack and #adidastrack on a Lonsdale garment."""
    report = ke.validate("Lonsdale Tank Top", "#niketrack #adidastrack #tracksuit",
                         "Lonsdale")
    assert not report["ok"]
    problems = " ".join(report["problems"])
    assert "nike" in problems and "adidas" in problems


def test_the_listings_own_brand_and_sub_brands_are_never_foreign(ke):
    report = ke.validate("Polo Ralph Lauren Pullover",
                         "Ralph Lauren Strick, Rundhals, Schwarz.", "Ralph Lauren")
    assert report["ok"], report["problems"]


def test_a_few_accurate_hashtags_are_a_nudge_not_a_block(ke):
    """Vinted does linkify tags; the rule bites on volume and on strangers."""
    report = ke.validate("Levis 501", "Schwarz #vintage #denim", "Levis")
    assert report["ok"], report["problems"]
    assert any("Hashtag" in w for w in report["warnings"])


def test_a_wall_of_hashtags_is_a_problem(ke):
    tags = " ".join(f"#tag{i}" for i in range(20))
    report = ke.validate("Levis 501", "Schwarz " + tags, "Levis")
    assert not report["ok"]
    assert any("Hashtags" in p for p in report["problems"])


def test_a_word_in_a_numeric_slot_is_caught(ke):
    """'Condition: Neu/10' is a live template bug in the tool we are replacing."""
    report = ke.validate("Lonsdale Tank Top", "Condition: Neu/10", "Lonsdale")
    assert any("Zahlen-Slot" in p for p in report["problems"])


def test_duplicate_keywords_are_caught(ke):
    report = ke.validate("Adidas Jacke", "Schwarz", "Adidas",
                         keywords=["Jacke", "jacke", "Trainingsjacke"])
    assert any("doppelte" in p for p in report["problems"])


def test_missing_material_and_measurements_warn_but_do_not_block(ke):
    """They are the top buyer questions, and material is a filter field."""
    out = ke.suggest({"brand": "Patagonia", "type": "Fleece",
                      "garment_class": "sweater", "size": "M", "color": "Blau"})
    v = out["validation"]
    assert v["ok"], "an incomplete listing is publishable, just weaker"
    assert any("Material" in w for w in v["warnings"])


def test_a_complete_clean_listing_passes(ke):
    """The counterweight: a validator nobody can satisfy gets switched off."""
    out = ke.suggest(JEANS)
    assert out["validation"]["ok"], out["validation"]["problems"]
    assert "#" not in out["description"]
    assert out["title_len"] <= 80


def test_structured_fields_are_surfaced_because_filters_run_first(ke):
    """Vinted filters on these before ranking touches any text (help/409)."""
    out = ke.suggest(JEANS)
    assert out["structured_fields"]["material"] == "100% Baumwolle"
    assert out["structured_fields"]["color"] == "Dunkelblau"
    thin = ke.suggest({"brand": "Nike", "type": "Hoodie", "garment_class": "sweater"})
    assert thin["structured_fields"]["size"] is None
    assert "TBD" in thin["description"]


def test_the_real_tool_output_fails_on_every_defect_it_actually_has(ke):
    """Regression anchor: the verbatim block from a live vintagezai listing."""
    body = ("Size: M\nCondition: Neu/10\n"
            "#lonsdalejacke #trackjacket #tracksuit #vestelonsdale #giaccalonsdale "
            "#vintagestyle #2000s #retro #90s #niketrack #niktracksuit #adidas "
            "#adidastrack")
    report = ke.validate("Lonsdale Tank Top | Classic Fit | Size M| Schwarz | Vintage y2k",
                         body, "Lonsdale")
    assert not report["ok"]
    joined = " ".join(report["problems"])
    assert "nike" in joined and "adidas" in joined
    assert "Hashtag" in joined
    assert "Zahlen-Slot" in joined


# ---------------------------------------------------- hashtags, added 2026-09-09
#
# The owner asked three times for the bot to define hashtags for a specific
# item. It never produced any: MAX_HASHTAGS existed only in the validator, to
# complain about tags HE had written. The first draft that generated them
# offered "#cargo #knee #chino" for one pair of trousers and "#nuptse" for a
# North Face jacket whose model nobody had entered, because it drew from the
# corpus terms of the cell. A hashtag is a claim about the garment, and
# "nicht zugehoerige Hashtags" is an enumerated reason for Vinted to hide the
# listing. So chosen tags come only from supplied fields; corpus terms come
# back as candidates to confirm.

def test_a_tag_is_only_ever_built_from_what_the_seller_supplied(ke):
    tags, candidates = ke.build_hashtags(
        {"brand": "The North Face", "type": "Jacke", "garment_class": "jacket",
         "size": "M", "color": "Schwarz"},
        keywords=[], mined=["nuptse", "doudoune", "1996"])
    assert "nuptse" not in tags, "a model nobody entered must never be asserted"
    assert "doudoune" not in tags
    assert "nuptse" in candidates, "the corpus finding is still offered, to confirm"


def test_the_cargo_chino_contradiction_cannot_reach_the_tags(ke):
    """One pair of trousers is not both. This is the defect that was shipped."""
    tags, candidates = ke.build_hashtags(
        {"brand": "Carhartt", "type": "Hose", "garment_class": "pants",
         "size": "M", "color": "Beige"},
        keywords=[], mined=["cargo", "knee", "chino"])
    assert not ({"cargo", "chino"} <= set(tags)), "asserted two exclusive cuts"
    assert {"cargo", "chino"} <= set(candidates)


def test_the_model_is_the_first_tag_because_nothing_else_carries_it(ke):
    tags, _ = ke.build_hashtags(
        {"brand": "Levis", "model": "501", "type": "Jeans",
         "garment_class": "pants", "cut": "Straight", "size": "W31"},
        keywords=[])
    assert tags[0] == "levis501"
    assert "straight" in tags


def test_never_more_than_the_cap(ke):
    tags, _ = ke.build_hashtags(
        {"brand": "Levis", "model": "501", "cut": "Straight", "style": "Mom",
         "era": "90er", "type": "Jeans", "garment_class": "pants"},
        keywords=[])
    assert len(tags) <= ke.MAX_HASHTAGS


def test_a_field_vinted_already_filters_on_is_not_worth_a_slot(ke):
    """Category, size and colour have their own filters; a tag adds nothing."""
    _, candidates = ke.build_hashtags(
        {"brand": "Carhartt", "type": "Hose", "garment_class": "pants",
         "size": "W32", "color": "Beige"},
        keywords=[], mined=["pants", "beige", "w32", "hose", "single knee"])
    assert candidates == ["singleknee"], candidates


def test_singular_and_plural_are_one_word_not_two_slots(ke):
    _, candidates = ke.build_hashtags(
        {"brand": "Carhartt", "type": "Trousers", "garment_class": "pants"},
        keywords=[], mined=["pant", "pants", "carpenter"])
    assert "carpenter" in candidates
    assert "pant" not in candidates and "pants" not in candidates


def test_a_candidate_never_repeats_a_chosen_tag(ke):
    tags, candidates = ke.build_hashtags(
        {"brand": "Levis", "model": "501", "type": "Jeans", "garment_class": "pants"},
        keywords=[], mined=["levis501", "selvedge"])
    assert set(tags).isdisjoint(candidates)


def test_with_nothing_distinctive_it_falls_back_rather_than_inventing(ke):
    tags, _ = ke.build_hashtags(
        {"brand": "Nike", "type": "Shirt", "garment_class": "shirt"}, keywords=[])
    assert tags == ["nikeshirt"]


def test_a_tag_has_to_survive_as_one_linkifiable_word(ke):
    assert ke.slug_tag("Straight Leg") == "straightleg"
    assert ke.slug_tag("Grün & Weiß") == "gruenweiss"
    assert ke.slug_tag("Größe") == "groesse"
    assert ke.slug_tag("H&M") is None, "two characters is not a tag"
    assert ke.slug_tag("") is None
    assert ke.slug_tag(None) is None


def test_the_suggestion_carries_both_lists(ke):
    out = ke.suggest({"brand": "Levis", "model": "501", "type": "Jeans",
                      "garment_class": "pants", "cut": "Straight", "size": "W31",
                      "condition": "Sehr gut"}, use_corpus=False)
    assert out["hashtags"] == ["levis501", "straight"]
    assert out["hashtag_candidates"] == []
