"""Warmness classification: rule evaluation + classify_enrollments guardrails."""
from __future__ import annotations

import json

from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore


def make_contact(store, cid_suffix, email=None, **fields):
    cid = f"c-{cid_suffix}"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": "A", "last_name": cid_suffix.title(), "company": "Co",
            "email": email if email is not None else f"{cid_suffix}@x.com"}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_engine_campaign(store, campaign_id="camp-b", contact_ids=()):
    """Campaign + template + cold sequence + enrollments, approved via the gate."""
    now = now_iso()
    store.create_campaign(campaign_id, "Camp B", now)
    store.replace_rules(campaign_id, cadence.DEFAULT_RULES)
    store.save_template("t1", "email", "Hello {{first_name}}",
                        "Hi {{first_name}} of {{company}}", "tester", now)
    store.upsert_sequence(campaign_id, "cold", "Cold seq", "auto-matthias",
                          [{"step_no": 1, "channel": "email",
                            "template_key": "t1", "day_offset": 0}])
    for cid in contact_ids:
        store.enroll(cid, campaign_id, "tester", now)
    cadence.classify_enrollments(store, campaign_id, "tester",
                                 "2026-07-12T08:00:00+00:00")
    result = cadence.approve_campaign(store, campaign_id, "tester", campaign_id)
    assert result["ok"], result
    return result


def _rule(priority, degree, predicate, label):
    return {"priority": priority, "degree": degree,
            "predicate": json.dumps(predicate), "label": label}


# -- evaluate_rules: ordering + catch-all ------------------------------------

def test_first_match_by_priority_wins():
    rules = [
        _rule(10, "warm", {"all": [{"fact": "has_replied"}]}, "replied"),
        _rule(20, "cold_touched", {"all": [{"fact": "prior_outbound"}]}, "prior"),
        _rule(90, "cold", {"all": []}, "catch-all"),
    ]
    # Both rule 10 and 20 match; the earlier one wins.
    both = {"has_replied": True, "prior_outbound": True}
    assert cadence.evaluate_rules(rules, {}, both) == ("warm", "replied")
    only_prior = {"has_replied": False, "prior_outbound": True}
    assert cadence.evaluate_rules(rules, {}, only_prior) == ("cold_touched", "prior")


def test_catch_all_matches_anything():
    rules = [_rule(90, "cold", {"all": []}, "catch-all")]
    assert cadence.evaluate_rules(rules, {}, {}) == ("cold", "catch-all")
    assert cadence.evaluate_rules(
        rules, {"scanned_at_booth": 1}, {"has_replied": True}) == ("cold", "catch-all")
    # No rules at all -> no classification.
    assert cadence.evaluate_rules([], {}, {}) is None


def test_get_rules_returns_priority_order(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        s.create_campaign("camp-a", "Camp A", now_iso())
        # Insert scrambled; get_rules must come back sorted by priority.
        s.replace_rules("camp-a", [
            _rule(90, "cold", {"all": []}, "catch-all"),
            _rule(10, "warm", {"all": [{"fact": "has_replied"}]}, "replied"),
        ])
        rules = [dict(r) for r in s.get_rules("camp-a")]
        assert [r["priority"] for r in rules] == [10, 90]
        hit = cadence.evaluate_rules(rules, {}, {"has_replied": True})
        assert hit == ("warm", "replied")


# -- fact conditions ----------------------------------------------------------

def test_fact_prior_outbound_and_has_replied(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        sent = make_contact(s, "sent")
        s.add_event(contact_id=sent, ts="2026-07-10T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        replied = make_contact(s, "replied")
        s.add_event(contact_id=replied, ts="2026-07-10T09:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        touched = make_contact(s, "touched")  # a personal touch is NOT prior_outbound
        s.add_event(contact_id=touched, ts="2026-07-10T09:00:00+00:00", channel="meeting",
                    direction="outbound", type="touch", now=now_iso())

        assert cadence.contact_facts(s, sent) == {
            "prior_outbound": True, "has_replied": False}
        assert cadence.contact_facts(s, replied) == {
            "prior_outbound": False, "has_replied": True}
        assert cadence.contact_facts(s, touched) == {
            "prior_outbound": False, "has_replied": False}

        rules = [
            _rule(10, "warm", {"all": [{"fact": "has_replied"}]}, "replied"),
            _rule(20, "cold_touched", {"all": [{"fact": "prior_outbound"}]}, "prior"),
        ]
        assert cadence.evaluate_rules(
            rules, {}, cadence.contact_facts(s, sent)) == ("cold_touched", "prior")
        assert cadence.evaluate_rules(
            rules, {}, cadence.contact_facts(s, replied)) == ("warm", "replied")
        assert cadence.evaluate_rules(
            rules, {}, cadence.contact_facts(s, touched)) is None


def test_fact_booth_scan_reads_contact_flag(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        scanned = make_contact(s, "scanned", scanned_at_booth=1)
        unscanned = make_contact(s, "unscanned")
        rules = [_rule(10, "warm", {"all": [{"fact": "booth_scan"}]}, "booth")]
        assert cadence.evaluate_rules(
            rules, dict(s.get_contact(scanned)), {}) == ("warm", "booth")
        assert cadence.evaluate_rules(
            rules, dict(s.get_contact(unscanned)), {}) is None


# -- field conditions ----------------------------------------------------------

def test_field_matches_regex_case_insensitive():
    rules = [_rule(10, "warm",
                   {"all": [{"field": "if_we_know_them", "matches": "dirk|yes|know"}]},
                   "known")]
    assert cadence.evaluate_rules(
        rules, {"if_we_know_them": "DIRK met him at the booth"}, {}) == ("warm", "known")
    assert cadence.evaluate_rules(
        rules, {"if_we_know_them": "stranger"}, {}) is None
    assert cadence.evaluate_rules(rules, {"if_we_know_them": None}, {}) is None
    assert cadence.evaluate_rules(rules, {}, {}) is None


def test_field_nonempty():
    rules = [_rule(10, "warm", {"all": [{"field": "persona", "nonempty": True}]},
                   "has persona")]
    assert cadence.evaluate_rules(rules, {"persona": "CFO"}, {}) == ("warm", "has persona")
    assert cadence.evaluate_rules(rules, {"persona": ""}, {}) is None
    assert cadence.evaluate_rules(rules, {"persona": "   "}, {}) is None
    assert cadence.evaluate_rules(rules, {}, {}) is None


# -- classify_enrollments --------------------------------------------------------

def test_classify_sets_degree_and_audits(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        s.create_campaign("camp-a", "Camp A", now_iso())
        s.replace_rules("camp-a", cadence.DEFAULT_RULES)

        warm = make_contact(s, "warm", scanned_at_booth=1, if_we_know_them="Dirk")
        prior = make_contact(s, "prior")
        s.add_event(contact_id=prior, ts="2026-07-10T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=now_iso())
        new = make_contact(s, "new")
        manual = make_contact(s, "manual")
        for cid in (warm, prior, new, manual):
            s.enroll(cid, "camp-a", "tester", now_iso())
        # Manual override: rules would say 'cold', a human said 'warm'.
        enr_manual = s.find_enrollment(manual, "camp-a")
        s.set_degree(enr_manual["enrollment_id"], "warm", "manual", "hand-set")

        res = cadence.classify_enrollments(s, "camp-a", "tester",
                                           "2026-07-12T09:00:00+00:00")
        assert res == {"changed": 3, "skipped": 1}

        e_warm = s.find_enrollment(warm, "camp-a")
        assert (e_warm["degree"], e_warm["degree_source"],
                e_warm["degree_rule"]) == ("warm", "rules", "Booth scan + known to Dirk")
        e_prior = s.find_enrollment(prior, "camp-a")
        assert (e_prior["degree"], e_prior["degree_rule"]) == (
            "cold_touched", "Prior outreach recipient")
        e_new = s.find_enrollment(new, "camp-a")
        assert (e_new["degree"], e_new["degree_rule"]) == ("cold", "Net new")
        e_manual = s.find_enrollment(manual, "camp-a")
        assert (e_manual["degree"], e_manual["degree_source"],
                e_manual["degree_rule"]) == ("warm", "manual", "hand-set")

        # One audit note per change; the skipped manual row got none.
        notes = [e for e in s.get_events(new) if e["type"] == "note"]
        assert len(notes) == 1
        assert notes[0]["subject"] == "degree classified"
        assert "degree=cold" in notes[0]["detail"]
        assert s.get_events(manual) == []
        assert s.count_events() == 1 + 3  # prior's sent event + 3 audit notes

        # Re-run is a no-op: degrees already match, no new audit events.
        res2 = cadence.classify_enrollments(s, "camp-a", "tester",
                                            "2026-07-12T10:00:00+00:00")
        assert res2 == {"changed": 0, "skipped": 1}
        assert s.count_events() == 4


def test_classify_never_touches_approved_enrollment(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, "app")
        make_engine_campaign(s, "camp-b", [cid])  # classifies (cold) then approves

        enr = s.find_enrollment(cid, "camp-b")
        assert enr["degree"] == "cold"
        assert enr["approved_at"] is not None

        # The contact now replies: the rules would re-classify to 'warm',
        # but the approval froze the enrollment.
        s.add_event(contact_id=cid, ts="2026-07-12T10:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        events_before = s.count_events()

        res = cadence.classify_enrollments(s, "camp-b", "tester",
                                           "2026-07-13T09:00:00+00:00")
        assert res == {"changed": 0, "skipped": 1}
        enr2 = s.find_enrollment(cid, "camp-b")
        assert (enr2["degree"], enr2["degree_source"]) == ("cold", "rules")
        assert s.count_events() == events_before  # no audit note emitted
