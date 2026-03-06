#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown>=3.7",
# ]
# ///
"""
Export Meji Media client docs to a styled HTML file (open in browser → Print → PDF).

Usage:
    uv run build-export.py                          # outputs meji-media-complete-guide.html
    uv run build-export.py --output custom-name     # outputs custom-name.html
    uv run build-export.py --source individual      # builds from 4 individual docs instead of the consolidated file
"""
import argparse
import markdown
from pathlib import Path

DOCS_DIR = Path(__file__).parent

CSS = """
@media print {
    body { margin: 0; }
    .page-break { page-break-before: always; }
    h2 { page-break-before: always; }
    h2:first-of-type { page-break-before: avoid; }
    table { page-break-inside: avoid; }
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 0 30px;
    color: #1a1a1a;
    line-height: 1.65;
    font-size: 15px;
}

h1 {
    font-size: 28px;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 12px;
    margin-top: 0;
}

h2 {
    font-size: 22px;
    color: #1e40af;
    border-bottom: 1px solid #dbeafe;
    padding-bottom: 8px;
    margin-top: 48px;
}

h3 {
    font-size: 17px;
    color: #374151;
    margin-top: 32px;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 14px;
}

th {
    background-color: #1e40af;
    color: white;
    text-align: left;
    padding: 10px 14px;
    font-weight: 600;
}

td {
    padding: 9px 14px;
    border-bottom: 1px solid #e5e7eb;
    vertical-align: top;
}

tr:nth-child(even) td {
    background-color: #f8fafc;
}

tr:hover td {
    background-color: #eff6ff;
}

blockquote {
    border-left: 4px solid #2563eb;
    margin: 20px 0;
    padding: 12px 20px;
    background-color: #eff6ff;
    color: #1e40af;
    font-style: normal;
}

blockquote p {
    margin: 0;
}

code {
    background-color: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    color: #be185d;
}

pre {
    background-color: #1e293b;
    color: #e2e8f0;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
}

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 40px 0;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

ol, ul {
    padding-left: 24px;
}

li {
    margin-bottom: 6px;
}

strong {
    color: #111827;
}

em {
    color: #6b7280;
}

.footer {
    text-align: center;
    color: #9ca3af;
    font-size: 13px;
    margin-top: 60px;
    padding-top: 20px;
    border-top: 1px solid #e5e7eb;
}
"""

INDIVIDUAL_DOCS_ORDER = [
    "overview.md",
    "a1-enquiry-follow-up.md",
    "a2-reply-detection.md",
    "a3-follow-up-steps.md",
]


def build_from_consolidated() -> str:
    """Read the single consolidated markdown file."""
    path = DOCS_DIR / "meji-media-complete-guide.md"
    if not path.exists():
        raise FileNotFoundError(f"Consolidated doc not found: {path}")
    return path.read_text(encoding="utf-8")


def build_from_individual() -> str:
    """Concatenate individual docs with page breaks."""
    parts = []
    for filename in INDIVIDUAL_DOCS_ORDER:
        path = DOCS_DIR / filename
        if not path.exists():
            print(f"  Warning: {filename} not found, skipping")
            continue
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def md_to_html(md_text: str) -> str:
    """Convert markdown to styled HTML document."""
    # Strip mermaid code blocks (they don't render in static HTML)
    # Replace with the plain-text fallback that follows
    import re
    md_text = re.sub(r"```mermaid\n.*?```", "", md_text, flags=re.DOTALL)

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "smarty", "sane_lists"],
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meji Media — Automated Follow-Up System</title>
    <style>{CSS}</style>
</head>
<body>
{html_body}
<div class="footer">
    Meji Media — Automated Follow-Up System | Confidential
</div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Export client docs to HTML")
    parser.add_argument(
        "--output", "-o",
        default="meji-media-complete-guide",
        help="Output filename (without extension)",
    )
    parser.add_argument(
        "--source", "-s",
        choices=["consolidated", "individual"],
        default="consolidated",
        help="Build from consolidated file or individual docs",
    )
    args = parser.parse_args()

    print(f"Building from {args.source} source...")

    if args.source == "consolidated":
        md_text = build_from_consolidated()
    else:
        md_text = build_from_individual()

    html = md_to_html(md_text)

    output_path = DOCS_DIR / f"{args.output}.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"Exported to: {output_path}")
    print("Open in your browser and use Print (Ctrl+P) -> Save as PDF")


if __name__ == "__main__":
    main()
