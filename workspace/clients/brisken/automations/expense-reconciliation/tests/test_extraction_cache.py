"""Extraction cache — "same photo, same answer" (backlog item 1).

The live defect (2026-08-13/15, smoke10 set): the vision extractor
re-reads an IDENTICAL image differently across runs at temperature 0 —
vendor spellings (MEGA CENTER / CENTRO / CENTRE), reference numbers,
tax labels, and on 2026-08-15 a BRL→EUR currency flip and a
50.50→50.00 tax drift. Every new spelling fragments learned memory.

These tests pin the fix: identical document content is answered from a
content-hash raw-payload store instead of a fresh API call. The fake
OpenAI transport DRIFTS on purpose (each call returns a different
vendor spelling), so any test asserting two identical extractions must
fail without the cache — which `test_no_cache_reproduces_the_drift`
demonstrates explicitly.

CI-safe: no network; the OpenAI SDK client object is replaced with a
SimpleNamespace fake (the test_categorize_llm.py pattern).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("openai")

from expense_recon.llm.client import (  # noqa: E402
    _EXTRACT_FINGERPRINT,
    OpenAIClient,
)
from expense_recon.llm.extraction_cache import (  # noqa: E402
    ExtractionCache,
    extraction_cache_key,
)

PNG_A = b"\x89PNG-fake-mega-centro-receipt-bytes"
PNG_B = b"\x89PNG-fake-erick-sport-receipt-bytes"

# The drifting spellings actually observed on one identical image.
DRIFT_VENDORS = ["MEGA CENTER", "MEGA CENTRO", "MEGA CENTRE"]


def _payload(vendor: str) -> str:
    return json.dumps({
        "date": "2026-04-02", "total": "1350.00", "currency": "BRL",
        "vendor": vendor, "vendor_clean": vendor.title(),
        "reference": "461017", "tax": "50.50", "tax_label": "Tributos Totais",
        "payment_hint": None, "document_type": "receipt",
        "line_items": [{"description": "Produto 30 Dias",
                        "line_total": "1350.00",
                        "quantity": None, "unit_price": None}],
        "confidence": 0.95, "notes": "",
    })


def _drifting_client(cache=None, **kwargs) -> tuple[OpenAIClient, list]:
    """An OpenAIClient whose transport returns a DIFFERENT vendor spelling
    on every call — the observed run-to-run drift, made deterministic."""
    client = OpenAIClient(api_key="sk-test-not-real", extraction_cache=cache, **kwargs)
    calls: list = []

    def _fake_create(**call_kwargs):
        calls.append(call_kwargs)
        vendor = DRIFT_VENDORS[(len(calls) - 1) % len(DRIFT_VENDORS)]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_payload(vendor)))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
    )
    return client, calls


def test_no_cache_reproduces_the_drift():
    """Without the cache, the same image read twice comes back with two
    vendor spellings — the exact pre-fix failure this feature closes."""
    client, calls = _drifting_client(cache=None)

    first = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])
    second = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls) == 2
    assert first.vendor != second.vendor  # MEGA CENTER vs MEGA CENTRO


def test_identical_image_answered_from_cache(tmp_path):
    """Same bytes twice => ONE API call, byte-identical reading, and no
    usage recorded for the hit (a cache hit costs nothing)."""
    cache = ExtractionCache(tmp_path / "cache.sqlite")
    client, calls = _drifting_client(cache=cache)

    first = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])
    second = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls) == 1
    assert second == first
    assert second.vendor == "MEGA CENTER"
    assert client.cost_tracker.call_count == 1


def test_cache_survives_client_rebuild(tmp_path):
    """The CLI re-run case: a NEW client (new process) over the same cache
    file answers from the store — re-runs are deterministic and free."""
    path = tmp_path / "cache.sqlite"
    client1, calls1 = _drifting_client(cache=ExtractionCache(path))
    first = client1.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    client2, calls2 = _drifting_client(cache=ExtractionCache(path))
    second = client2.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls1) == 1 and len(calls2) == 0
    assert second == first


def test_file_name_is_not_part_of_the_key(tmp_path):
    """Same photo, same answer — whatever the file is called this month."""
    client, calls = _drifting_client(cache=ExtractionCache(tmp_path / "c.sqlite"))

    first = client.extract_receipt(file_name="april/IMG_001.png",
                                   images=[(PNG_A, "image/png")])
    second = client.extract_receipt(file_name="may/receipt_07.png",
                                    images=[(PNG_A, "image/png")])

    assert len(calls) == 1
    assert second == first


def test_different_content_is_a_miss(tmp_path):
    client, calls = _drifting_client(cache=ExtractionCache(tmp_path / "c.sqlite"))

    client.extract_receipt(file_name="a.png", images=[(PNG_A, "image/png")])
    client.extract_receipt(file_name="b.png", images=[(PNG_B, "image/png")])

    assert len(calls) == 2


def test_model_change_invalidates(tmp_path):
    """A different vision model must not be answered with another model's
    reading."""
    path = tmp_path / "cache.sqlite"
    client1, calls1 = _drifting_client(cache=ExtractionCache(path))
    client1.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    client2, calls2 = _drifting_client(
        cache=ExtractionCache(path), vision_model="gpt-4o"
    )
    client2.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls1) == 1 and len(calls2) == 1


def test_text_extraction_cached_too(tmp_path):
    """The PDF text-layer path caches on the text content."""
    client, calls = _drifting_client(cache=ExtractionCache(tmp_path / "c.sqlite"))
    text = "Uber\nTrip receipt\nTotal $24.50\nReference: TRIP-9931"

    first = client.extract_receipt(file_name="uber.pdf", text=text)
    second = client.extract_receipt(file_name="uber.pdf", text=text)

    assert len(calls) == 1
    assert second == first


def test_parser_stays_live_on_cached_payloads(tmp_path):
    """The cache stores the RAW payload, so parser guards run on every
    hit: a stored junk document_type collapses to "receipt" via the
    whitelist exactly as a fresh API answer would."""
    cache = ExtractionCache(tmp_path / "cache.sqlite")
    key = extraction_cache_key(
        fingerprint=_EXTRACT_FINGERPRINT, model="gpt-4o-mini",
        images=[(PNG_A, "image/png")],
    )
    raw = json.loads(_payload("MEGA CENTER"))
    raw["document_type"] = "totally-bogus-type"
    cache.put(key, json.dumps(raw), model="gpt-4o-mini", file_name="seed.png")

    client, calls = _drifting_client(cache=cache)
    result = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls) == 0  # answered from the store
    assert result.document_type == "receipt"  # whitelist applied live


def test_broken_cache_is_fail_open(tmp_path):
    """A cache path that cannot be a database (it is a directory) must
    degrade to plain API calls, never break the run."""
    broken = tmp_path / "iam-a-directory"
    broken.mkdir()
    client, calls = _drifting_client(cache=ExtractionCache(broken))

    result = client.extract_receipt(file_name="r.png", images=[(PNG_A, "image/png")])

    assert len(calls) == 1
    assert result.vendor == "MEGA CENTER"


def test_build_llm_client_attaches_cache_from_config(tmp_path, monkeypatch):
    """`llm.extraction_cache_path` lands on the built client. NOTE the
    single-arg call: the web tests replace this builder with a 1-arg
    lambda, so the signature must stay `(cfg)`."""
    from expense_recon import cli as cli_module

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-test")
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)
    cache_path = tmp_path / "cache.sqlite"
    cfg = {"llm": {"provider": "openai", "extraction_cache_path": str(cache_path)}}

    client, _tracker = cli_module._build_llm_client(cfg)

    cache = getattr(client, "extraction_cache", None)
    assert isinstance(cache, ExtractionCache)
    assert cache.path == cache_path


def test_build_llm_client_attaches_cache_from_env(tmp_path, monkeypatch):
    """EXPENSE_RECON_EXTRACTION_CACHE (the fly.toml switch) turns the
    cache on without any config change."""
    from expense_recon import cli as cli_module

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-test")
    env_path = tmp_path / "global-cache.sqlite"
    monkeypatch.setenv("EXPENSE_RECON_EXTRACTION_CACHE", str(env_path))
    cfg = {"llm": {"provider": "openai"}}

    client, _tracker = cli_module._build_llm_client(cfg)

    cache = getattr(client, "extraction_cache", None)
    assert isinstance(cache, ExtractionCache)
    assert cache.path == env_path


def test_build_llm_client_no_cache_by_default(monkeypatch):
    from expense_recon import cli as cli_module

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-test")
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)
    cfg = {"llm": {"provider": "openai"}}

    client, _tracker = cli_module._build_llm_client(cfg)

    assert getattr(client, "extraction_cache", None) is None


def test_run_resolves_relative_cache_path_against_config_dir(tmp_path, monkeypatch):
    """End to end through run(): a RELATIVE `extraction_cache_path` in the
    run config lands beside the config file, not in the process CWD (the
    CLI is invoked with `uv run --directory <module>`, so CWD-relative
    would silently write the cache into the module tree)."""
    from expense_recon import cli as cli_module
    from expense_recon.llm.client import ExtractedReceipt, MockLLMClient

    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"fake-jpeg-bytes")

    mock_client = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-04-02", total="10.00", currency="USD", vendor="Uber",
            reference="r1", line_items=(), confidence=0.9, notes="",
        ),
    ])

    def fake_openai_client(*, model, api_key, cost_tracker, vision_model=None):
        mock_client.cost_tracker = cost_tracker
        return mock_client

    monkeypatch.setattr(cli_module, "OpenAIClient", fake_openai_client)
    monkeypatch.setenv("FAKE_KEY", "sk-fake-for-test")
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)

    cfg = {
        "mode": "expense_generation",
        "expense": {"legal_entity_id": "brisken-llc"},
        "receipts": {"path": "receipts", "source": "folder"},
        "llm": {"provider": "openai", "api_key_env": "FAKE_KEY",
                "extraction_cache_path": "extraction-cache.sqlite"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    cli_module.run(config_path)

    cache = getattr(mock_client, "extraction_cache", None)
    assert isinstance(cache, ExtractionCache)
    assert cache.path == tmp_path / "extraction-cache.sqlite"
