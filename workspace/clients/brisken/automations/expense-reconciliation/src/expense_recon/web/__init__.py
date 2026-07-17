"""Local browser UI for the expense-reconciliation tool.

A single-process FastAPI app Chris runs on her own machine
(`expense-recon-web`) and drives in the browser, instead of hand-editing
a JSON config and reading an xlsx. It wraps the exact same pipeline the
CLI runs (`expense_recon.cli.reconcile`), persists each run, and renders
an editable review workbench (confirm / reject / reclassify) whose
decisions flow into the xlsx and Zoho exports.

Nothing here is multi-tenant or hosted: it is the standalone Path-A tool
with a front end, consistent with the 2026-06-12 STANDALONE decision.
All financial data stays on the machine running the server.
"""
