"""The receipt-reading prompt is pinned by its fingerprint (backlog item 128).

`llm.client._EXTRACT_FINGERPRINT` hashes the extraction instruction template,
the PDF text-layer suffix and the strict response schema
(`extraction_cache.prompt_fingerprint`, with the cache version in front). It
keys the extraction cache: any edit to any of the three changes the value,
every stored reading becomes unreachable, and the next re-match re-reads and
re-bills the whole history. The owner's record of prompt edits says each one
moved 12-41 of 129 stored readings, none of which was visible at the moment
the edit was made. Nothing guarded the edit; the cache invalidation was the
first sign.

This test is the guard. An edit that changes the fingerprint goes red here
until the literal below is updated, and updating it is meant to be the LAST
step of a deliberate prompt round, not the first:

1. Make the edit on a branch.
2. Re-run the reading comparison over the stored readings (the extraction
   A/B runner: every stored document read once under the old prompt and once
   under the new, the two parses diffed field by field) and count the
   readings that moved.
3. Put that count, and which fields moved, in the PR description.
4. Only then replace `PINNED` with the new value the failure prints.

An edit that changes the cache version in `extraction_cache._CACHE_VERSION`
moves the fingerprint the same way and takes the same steps.
"""
from __future__ import annotations

from expense_recon.llm import client, extraction_cache

# Computed 2026-09-18 from the prompt text and schema as committed that day.
PINNED = "918136353aa0384cd2f2b45080fca006cbcae5fc255cc37a389914d825fe868c"


def test_the_extraction_prompt_fingerprint_is_pinned():
    """Red until the literal moves with the prompt. The failure prints both
    values so the new one can be copied after the reading comparison."""
    assert client._EXTRACT_FINGERPRINT == PINNED, (
        "the receipt-reading prompt or its schema changed: fingerprint "
        f"{client._EXTRACT_FINGERPRINT} (pinned {PINNED}). Every cached "
        "reading is now unreachable. Run the reading comparison over the "
        "stored readings, attach the moved-readings count to the PR, then "
        "update PINNED (see this module's docstring)."
    )


def test_the_pin_covers_template_suffix_and_schema():
    """The pin is only worth something if it hashes what the model sees:
    the UNFORMATTED instruction template plus the text-layer suffix, and the
    response schema. A fingerprint computed from anything narrower would let
    a schema edit through."""
    recomputed = extraction_cache.prompt_fingerprint(
        client._EXTRACT_INSTRUCTIONS + client._EXTRACT_TEXT_SUFFIX,
        client._EXTRACT_SCHEMA,
    )
    assert recomputed == client._EXTRACT_FINGERPRINT == PINNED
    assert extraction_cache._CACHE_VERSION == "1"
    # the template keeps its placeholders unformatted: the cache key excludes
    # the file name, so the name must not be baked into the fingerprint
    assert "{file_name}" in client._EXTRACT_INSTRUCTIONS
    assert "{known_cards}" in client._EXTRACT_INSTRUCTIONS
    assert "{text}" in client._EXTRACT_TEXT_SUFFIX
