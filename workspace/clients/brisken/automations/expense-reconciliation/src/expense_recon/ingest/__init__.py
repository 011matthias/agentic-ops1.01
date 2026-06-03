"""Statement and receipt ingest — v2 spec §7, §8.

MVP intake is single-format CSV or Excel for statements
(call-outcomes Part 2 "Statement intake (MVP)"). Statements are
read as structured columns with no interpretation
(call-outcomes "C1 statements"); this is a tabular ingest, not a
parsing problem.

Two statement parsers, same interface, shared helpers:

* :mod:`statement_csv` — `parse_statement_csv`
* :mod:`statement_xlsx` — `parse_statement_xlsx`
* :mod:`_common` — `StatementParseError`, `parse_date`, `parse_amount`,
  `validate_required_map`, `REQUIRED_KEYS`, `OPTIONAL_KEYS`

Both parsers use the same column-map shape, the same error type, and
the same 1-indexed row-number convention (header is row 1).

Receipt ingest:

* :mod:`receipts_csv` — `parse_receipts_csv`: slice-1 bridge that
  accepts already-extracted receipt rows. Real OCR / Claude-vision
  extraction lands in slice 2 (v2 spec §24); the matcher contract
  stays the same, only the source of `Receipt` objects changes.
"""
