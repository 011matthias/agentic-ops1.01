# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Anti-slop voice checker for client-facing deliverables.

Greps for LLM-style phrases, corporate-speak, vague adjectives, and
hedging patterns that signal AI-generated content or shallow thinking.
Bilingual (DE/EN).

The rule: a text that survives this check is not automatically good --
it is just not obviously slop. Passing the check is necessary, not
sufficient. Use alongside adversarial-prereview.py for substance.

Usage:
  uv run tools/voice-check.py path/to/file.md [path/to/another.md ...]
  uv run tools/voice-check.py --dir workspace/clients/warme-wimmer/context/hero-exports/notion-pages

Exit 0 = no hits. Exit 1 = hits found (non-blocking warning; caller decides).
Exit 2 = usage error.

The banned-pattern list is deliberately conservative: false positives are
cheap (you override with --allow-line), false negatives are the point.
"""
# /// script
# requires-python = ">=3.11"
# ///
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# (regex, category, explanation)
# Patterns are case-insensitive. Word boundaries where appropriate.
BANNED = [
    # --- LLM boilerplate openers ---
    (r"\b(it'?s worth noting that|hierbei ist zu beachten|anzumerken ist)\b",
     "llm-opener", "LLM-Phrase: klingt nach GPT-Boilerplate."),
    (r"\b(in summary|zusammenfassend|abschliessend laesst sich sagen)\b",
     "llm-opener", "LLM-Phrase: Artikel-Schluss-Floskel."),
    (r"\b(it should be noted|beachten sie dass|es ist wichtig zu erwaehnen)\b",
     "llm-opener", "LLM-Phrase: performativer Hinweis."),
    (r"\b(diving into|let'?s dive into|eintauchen in)\b",
     "llm-opener", "Content-Marketing-Floskel."),
    (r"\b(it is important to note|erwaehnenswert ist)\b",
     "llm-opener", "LLM-Hedge."),

    # --- Vague power adjectives ---
    (r"\b(comprehensive|umfassend|vollumfaenglich)\b",
     "vague-adjective", "Vage: sagt nichts ueber Scope. Nenne stattdessen konkrete Elemente."),
    (r"\b(robust|widerstandsfaehig)\b(?! gegen)",
     "vague-adjective", "Vage ohne 'gegen X'. Nenne den Fehlermodus explizit."),
    (r"\b(seamless|seamlessly|nahtlos)\b",
     "vague-adjective", "Marketing-Adjektiv. Was genau passiert ohne Bruch?"),
    (r"\b(cutting-?edge|bleeding-?edge|state-of-the-art|zukunftsweisend)\b",
     "vague-adjective", "Marketing-Adjektiv ohne Substanz."),
    (r"\b(powerful|maechtig|leistungsstark)\b",
     "vague-adjective", "Vage. Nenne die Zahl/Metrik."),
    (r"\b(best-in-class|marktfuehrend|fuehrend)\b",
     "vague-adjective", "Selbstlob ohne Beleg."),
    (r"\b(effective|effizient|effektiv)\b(?! fuer| at| im)",
     "vague-adjective", "Vage ohne 'effizient bei X' oder Metrik."),
    (r"\b(streamline|streamlining|straffen|optimieren)\b(?! durch| by)",
     "vague-adjective", "Vage ohne 'durch X'. Nenne den konkreten Mechanismus."),
    (r"\b(leverage|leverages|leveraging|nutzt die leistung|die macht von)\b",
     "corporate-speak", "Corporate-Speak. 'benutzt' reicht."),
    (r"\b(empowers?|empowering|befaehigt)\b",
     "corporate-speak", "Marketing-Verb."),
    (r"\b(solution|loesung)\b(?! fuer| for)",
     "corporate-speak", "Ueberstrapaziertes Wort. 'Tool', 'Script', 'Scenario' ist praeziser."),
    (r"\b(approach|ansatz)\b(?!: )",
     "corporate-speak", "Oft Fuell-Wort. Nenne was konkret gemacht wird."),

    # --- Hedging / passive voice patterns ---
    (r"\b(man kann|man koennte|man sollte)\b",
     "hedge", "Passiv-Hedge. Wer konkret? Verwende aktives Subjekt."),
    (r"\b(it can be|could be considered|kann als)\b",
     "hedge", "Hedging ohne Akteur."),
    (r"\bwir koennen\b(?! bis| ab)",
     "hedge", "Schwach. Ersetze durch 'wir bauen/liefern/testen'."),

    # --- Filler intensifiers / adverbs ---
    (r"\b(effectively|seamlessly|effortlessly|successfully)\b",
     "filler-adverb", "Filler-Adverb. Meistens streichbar."),
    (r"\b(various|verschiedene|zahlreiche|mehrere)\b(?! [A-Z0-9])",
     "vague-quantifier", "Vage. Nenne Anzahl oder enumeriere."),
    (r"\b(complex|komplex)\b(?!er als| with| mit)",
     "vague-quantifier", "Vage. 'N Module + M Branches' ist praeziser."),

    # --- Em-dash (per user feedback memory: banned) ---
    # Matches em-dash surrounded by spaces where a comma or colon would fit.
    (r" \u2014 ",
     "em-dash", "Em-Dash. Ersetze durch Komma, Doppelpunkt oder Punkt."),
    # Double-hyphen as em-dash substitute (also banned). Fenced code blocks are
    # skipped at the line-loop level, so legitimate `--flag` syntax inside ```
    # blocks won't false-positive. Inline-code (`--flag` with backticks) is
    # left alone as a deliberate trade-off; rare in prose.
    (r" -- ",
     "em-dash-substitute", "Doppel-Bindestrich als Em-Dash-Ersatz. Ersetze durch Komma, Doppelpunkt oder Punkt."),

    # --- Claude-specific tells ---
    (r"\b(delve|delving into|vertiefen wir uns)\b",
     "llm-tell", "Claude-Tell. Streichen."),
    (r"\b(it'?s crucial that|es ist entscheidend dass)\b",
     "llm-tell", "Floskel. Benenne den Risiko-Fall."),
    (r"\b(whether it'?s|sei es)\b",
     "llm-tell", "Parallelismus-Floskel."),
    (r"\b(in today'?s (world|landscape|environment))\b",
     "llm-tell", "Artikel-Opener-Floskel."),

    # --- Three-item symmetric lists via comma+and (hard to detect reliably; sample only) ---
    (r"\b\w+, \w+,? and \w+\.",
     "triplet-symmetry", "Moegliches rhetorisches Triplet. Pruefe ob Inhalt reicht."),

    # --- Best practices without citation ---
    (r"\b(best practices?|best-?practice|empfehlungen)\b(?!.*(source:|siehe|per|laut|RFC|ISO))",
     "uncited-claim", "'Best practice' ohne Quelle. Welche? Wer sagt das?"),
]


def check_file(path: Path) -> list[tuple[int, str, str, str]]:
    """Return list of (line_no, category, explanation, line_text)."""
    hits = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    lines = text.splitlines()
    in_fence = False  # Tracks ``` fenced code blocks
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        # Toggle fenced-code state on ``` lines (open or close). The fence line
        # itself is not scanned either — it's a fence delimiter, not prose.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Skip indented code blocks (4+ leading spaces, but not list items).
        if line.startswith("    ") and not stripped.startswith("-"):
            continue
        for regex, category, explanation in BANNED:
            m = re.search(regex, line, flags=re.IGNORECASE)
            if m:
                # Skip if line is a blockquote citation (starts with "> ")
                if line.lstrip().startswith("> "):
                    continue
                hits.append((i, category, explanation, line.strip()))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="Markdown files to check")
    ap.add_argument("--dir", help="Directory to recursively check")
    ap.add_argument("--glob", default="**/*.md", help="Glob pattern within --dir")
    ap.add_argument("--allow-category", action="append", default=[],
                    help="Suppress a category (can repeat)")
    args = ap.parse_args()

    targets: list[Path] = []
    for f in args.files:
        p = Path(f)
        if p.is_file():
            targets.append(p)
    if args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            print(f"ERROR: not a directory: {d}", file=sys.stderr)
            sys.exit(2)
        targets.extend(d.glob(args.glob))

    if not targets:
        print("ERROR: no files to check. Pass files or --dir.", file=sys.stderr)
        sys.exit(2)

    total_hits = 0
    by_category: dict[str, int] = {}

    for path in sorted(set(targets)):
        hits = [h for h in check_file(path) if h[1] not in args.allow_category]
        if not hits:
            continue
        print(f"\n## {path}")
        for line_no, cat, exp, text in hits:
            print(f"  L{line_no:4d}  [{cat}]  {exp}")
            print(f"        → {text[:140]}")
            by_category[cat] = by_category.get(cat, 0) + 1
            total_hits += 1

    print(f"\n---\nTotal hits: {total_hits} across {len(targets)} file(s).")
    if by_category:
        print("By category:")
        for cat, n in sorted(by_category.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4d}  {cat}")

    sys.exit(1 if total_hits else 0)


if __name__ == "__main__":
    main()
