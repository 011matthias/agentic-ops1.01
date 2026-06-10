# Receipt folder (example)

Drop receipt images (`.jpg`, `.jpeg`, `.png`, `.webp`) and PDFs here,
then run:

```
expense-recon doctor --config ../run.with-folder.example.json   # validate first
expense-recon --config ../run.with-folder.example.json          # OCR + reconcile
```

Each file becomes one receipt. Digital PDFs (Uber email receipts,
train tickets) are read from their text layer; photos and scans go
through vision OCR. Files that are not images or PDFs are skipped and
listed on the report's Errors sheet, never silently dropped.

This folder is intentionally empty in the repo (real receipts are
client data and never committed). The example config points here so
`doctor` has a valid path to check.
