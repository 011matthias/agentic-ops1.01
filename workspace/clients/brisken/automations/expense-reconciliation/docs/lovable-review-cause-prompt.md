# Lovable prompt - say WHY a pair still needs a click (front 5)

Paste this into the `brisken-expense-review` Lovable project (production:
`brisken-reconcile-dash.lovable.app`). It calls the existing FastAPI backend
at `brisken-expense-recon.fly.dev` as a JSON API. **Do NOT add Supabase or any
database.** Auth stays the existing `Authorization: Bearer <token>`.

## Background

Every charge in review shows the same sentence: "This match isn't certain.
More than one receipt could be this charge, or the best candidate scored
low." The real reason differs per row: another charge fits the receipt just
as well, the AI doubts the pair, the receipt names no card and the merchant
words disagree, the converted amount is outside the clean band, or (on a
Reconciled row) the receipt is a few days off. The backend now names that
cause, so the row can say it in the reviewer's language.

## 1. The new fields

`GET /api/runs/{id}` -> `rows[].review`, two parallel keys, **absent** (not
null) when the row has no such cause. `review.reason_code` is unchanged.

```json
"review": {
  "state": "check",
  "reason": "This match isn't certain. ...",
  "reason_code": "uncertain_match",
  "cause": "rival_agrees",
  "cause_detail": {
    "document_id": "0055__20260718_Receipt_Fuel_PostoSantos.pdf",
    "rival_charges": [{"transaction_id": "94b4…", "vendor": "POSTO SANTOS",
                       "amount": "9.80", "currency": "USD", "date": "2026-07-18"}],
    "rival_receipts": [{"document_id": "…", "vendor": "Posto Santos",
                        "total": "50.00", "currency": "BRL", "date": "2026-07-19"}],
    "rival": "charge POSTO SANTOS 9.80 USD on 2026-07-18",
    "model_p": 0.85
  }
}
```

`cause` is one of six values; `cause_detail` keys per cause (each may be
absent):

| cause | detail keys |
|---|---|
| `rival_agrees` | `rival_charges[]`, `rival_receipts[]`, `rival`, `model_p` |
| `model_doubts` | `model_p`, `model_reasoning` (English, the AI's own sentence) |
| `merchant_disagrees` | `vendor_pct` |
| `no_card_rival` | `rival` |
| `fx_review_zone` | `gap_pct`, `rate_source`, `model_p` |
| `probable_date_gap` | `date_gap_days`, `amount_diff` |

`rows[].reverses_transaction_id` (absent unless set): on a refund row, the
`transaction_id` of the purchase it reverses.

## 2. The render rule

- Where a row renders `review.reason` today, render the cause sentence
  instead when `review.cause` is present (i18n below, filled from
  `cause_detail`), and keep `review.reason` as the fallback when it is absent.
- `rival_agrees`: after the sentence, list up to three rivals, each as
  "{vendor} {amount} {currency} · {date}" from `rival_charges` (charges) and
  `rival_receipts` (receipts, using `total`). If both lists are absent but
  `rival` is present, print `rival` as is.
- `model_doubts`: print the sentence, then `model_reasoning` in a muted
  line, verbatim (it is English model text; do not translate it).
- `probable_date_gap` appears on **Reconciled** rows too: show it as a small
  muted note under the chosen receipt, not as a review warning.
- `reverses_transaction_id`: on the refund row, a link "Reverses the charge
  of {date}" that scrolls to and highlights that row. If the row is not on
  screen, show the text without the link.
- `model_p` renders as a percentage, no decimals (0.85 -> 85%).

## 3. i18n keys (EN + PT)

```
expx.review.cause.rival_agrees
  EN: Another charge or receipt fits just as well. Pick the right pair.
  PT: Outra cobrança ou recibo encaixa igualmente bem. Escolha o par certo.
expx.review.cause.model_doubts
  EN: The AI doubts this is the same purchase ({p}).
  PT: A IA duvida que seja a mesma compra ({p}).
expx.review.cause.merchant_disagrees
  EN: The receipt names no card and the merchant name does not match ({pct}%).
  PT: O recibo não indica cartão e o nome do comerciante não confere ({pct}%).
expx.review.cause.no_card_rival
  EN: The receipt names no card, and a charge on another card also fits.
  PT: O recibo não indica cartão, e uma cobrança em outro cartão também encaixa.
expx.review.cause.fx_review_zone
  EN: The converted amount is {gap}% off, outside the range the tool accepts on its own.
  PT: O valor convertido difere {gap}%, fora da faixa que a ferramenta aceita sozinha.
expx.review.cause.fx_review_zone_norate
  EN: No exchange rate to check this conversion. Confirm the pair.
  PT: Sem câmbio para conferir esta conversão. Confirme o par.
expx.review.cause.probable_date_gap
  EN: Receipt dated {days} days from the charge, amount differs by {diff}.
  PT: Recibo com {days} dias de diferença da cobrança, valor difere em {diff}.
expx.review.cause.rivals
  EN: Also fits:
  PT: Também encaixa:
expx.row.reverses
  EN: Reverses the charge of {date}
  PT: Estorna a cobrança de {date}
```

Use `fx_review_zone_norate` when `cause` is `fx_review_zone` and `gap_pct` is
absent. For `probable_date_gap`, `{days}` is the absolute value of
`date_gap_days`; omit the amount clause when `amount_diff` is "0.00".

## 4. Do not change

- `review.state`, `review.reason_code` and the grouping, sorting and
  bulk-confirm logic that read them.
- Which rows are in which bucket or section; `effective_bucket` is still
  the only bucket key.
- `candidates[].reason` rendering where it already appears.
- No new API calls; everything is on the run payload you already load.
