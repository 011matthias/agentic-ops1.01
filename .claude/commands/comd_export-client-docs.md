---
description: Export client-facing docs to a single consolidated markdown or HTML file
argument-hint: <client-name>
---

# Export Client Docs

Generates a consolidated, export-ready document from a client's `docs/client/` folder.

## Process

1. Read all `.md` files in `workspace/clients/$ARGUMENTS/docs/client/`
2. Identify the overview doc (contains "overview" in filename) — this goes first
3. Order remaining docs alphabetically (a1, a2, a3, etc.)
4. Generate a consolidated markdown file:
   - Add a title page with client name, version, and date
   - Add a table of contents
   - Restructure headings: overview H2s stay as H2s, individual doc H1s become H2s, their H2s become H3s
   - Add horizontal rules between major sections
   - Write to `docs/client/{client}-complete-guide.md`
5. If `build-export.py` exists in the same directory, run it with `uv run build-export.py` to generate the HTML version
6. Report the output file paths

## Notes

- The individual source files remain untouched — they are the canonical source of truth
- The consolidated file is for export only
- If the client already has a `*-complete-guide.md`, overwrite it (it's generated, not hand-edited)
- Mermaid diagrams are stripped from the HTML output (they don't render in static HTML) — make sure each diagram has a plain-text fallback
