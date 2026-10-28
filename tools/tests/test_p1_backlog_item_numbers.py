"""Each Brisken recon backlog item number names one item.

On 2026-10-07 two sessions merged different items as 248 within the hour,
and a third session's merge resolution then kept both copies of one of them,
so `main` carried two "### 248." headings and an empty "### 251." until a
checkpoint found it. Each PR was clean on its own branch; the clash only
existed on the merge commit, which is exactly what CI checks out for a PR.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKLOG = REPO / "workspace" / "clients" / "brisken" / "status" / "p1-improvement-backlog.md"
HEADING = re.compile(r"^### (\d+[A-Za-z]?)\. ", re.MULTILINE)


def duplicate_numbers(text: str) -> list[str]:
    counts = Counter(HEADING.findall(text))
    return sorted(n for n, c in counts.items() if c > 1)


def test_no_backlog_item_number_is_used_twice():
    dupes = duplicate_numbers(BACKLOG.read_text(encoding="utf-8"))
    assert dupes == [], (
        f"p1-improvement-backlog.md uses item number(s) {dupes} more than once: "
        "renumber yours to the next free number (and its code comments, test "
        "file name, api-contract and PROMPT-STATUS lines) before merging"
    )


def test_the_check_sees_a_duplicate():
    text = "### 247. A\n\nbody\n\n### 248. B\n\n### 248. C\n\n### 77a. D\n"
    assert duplicate_numbers(text) == ["248"]
    assert duplicate_numbers("### 1. A\n### 2. B\n") == []
