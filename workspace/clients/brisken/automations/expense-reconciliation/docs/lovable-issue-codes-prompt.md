# Lovable prompt - upload rejections in the reviewer's language

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth is the existing `Authorization: Bearer <token>`.

Backend is live. Nothing breaks if this is not applied: the English sentences
still render exactly as they do today.

## What changed

When the upload refuses a file, the reason now ships twice: the English
sentence you already render, and a stable code beside it.

```json
"upload_issues": [
  "notes.txt: unsupported type .txt (skipped)",
  "empty.jpg: empty or unreadable (skipped)"
],
"upload_issue_details": [
  { "code": "unsupported_type", "file": "notes.txt", "suffix": ".txt", "limit": null },
  { "code": "empty_or_unreadable", "file": "empty.jpg", "suffix": null, "limit": null }
]
```

**`upload_issues` keeps its type (`string[]`) and its wording.** Do not change
how it is typed or rendered; retyping a live list in place is what blanked the
batch page on 2026-08-22.

Where the pair appears:

| Screen | Payload | Fields |
|---|---|---|
| Batch page | `GET /api/expense-batches/{id}` | `summary.upload_issues` + `summary.upload_issue_details` |
| Add receipts (job result) | add-job summary | `issues` + `issue_details` |
| Workbench receipts upload | folder-ingest reply | `issues` + `issue_details` |

## 1. Render from the details, fall back to the prose

For each list: if `*_details` is non-empty, compose the sentence from the code
(one detail per prose line, same order). If it is empty, render the prose
strings as today. Runs created before 2026-08-22 have no details, so the
fallback is the normal path for old batches, not an error case.

Every detail object always has all four keys. `suffix` and `limit` are `null`
where the code does not use them; never assume a key is missing.

## 2. The four codes

| `code` | Uses | EN | PT |
|---|---|---|---|
| `unsupported_type` | `file`, `suffix` | "{file}: not a supported file type ({suffix}), skipped" | "{file}: tipo de ficheiro nao suportado ({suffix}), ignorado" |
| `empty_or_unreadable` | `file` | "{file}: empty or unreadable, skipped" | "{file}: vazio ou ilegivel, ignorado" |
| `too_large` | `file`, `limit` (MB) | "{file}: larger than {limit} MB, skipped" | "{file}: maior que {limit} MB, ignorado" |
| `upload_cap` | `file`, `limit` (files) | "Upload limit of {limit} files reached; {file} and everything after it was skipped" | "Limite de {limit} ficheiros atingido; {file} e os seguintes foram ignorados" |

`suffix` can be `null` for a file with no extension at all; say "no extension"
/ "sem extensao" in that case rather than printing `null`.

An unrecognized `code` (a future one) falls back to the matching prose string
by index. Never render the raw code.

## 3. Do not change

`parse_issues` (the per-receipt notes) is a different list and is untouched
this round. No other field changed shape or type.
