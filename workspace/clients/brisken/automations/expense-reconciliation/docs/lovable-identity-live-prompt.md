# Lovable prompt: the merchant list read live, and one new refusal (backlog item 224, front 3)

Paste the block below into Lovable (Brisken expense recon SPA).

````
Background: the backend now reads each row's merchant from the merchant list
as it is today, not from what was stored when the receipt arrived. Most of
this needs no change from you: `vendor.display` on the Expenses grid already
shows the new name, and a merchant's account for the row's company now comes
back as an ordinary `posting_category` with `origin: "rule"`. Three small
additions, all optional fields (absent, never null). Auth stays the bearer
token; no Supabase.

1. New refusal code. A row's `review` can now carry
   `refusal: "account_vendor_specific"` (with `reason_code: "category_refused"`,
   the same shape as the existing refusals such as `model_picked_parent`).
   Render it exactly like the other refusal codes, with this text:
   - EN: "The tool's reading named an account kept for one vendor's product (Cloud Subscriptions-ZOHO ERP is for Zoho), and this merchant is not that vendor, so it was not used. Pick one by hand."
   - PT: "A leitura da ferramenta indicou uma conta reservada ao produto de um fornecedor (Cloud Subscriptions-ZOHO ERP é da Zoho), e este comerciante não é esse fornecedor, por isso não foi usada. Escolha uma à mão."
   i18n key: `review.refusal.account_vendor_specific`.

2. What a row read before (Expenses grid rows and Matching tab rows).
   `posting_category.stamped` = `{category, zoho_account, source, origin}` is
   present only when the merchant list decided the account at read time and
   the row carried something else before (usually the model's suggestion).
   Under the posting account, show one muted line:
   - EN: "Was: {stamped.zoho_account} ({origin label})" where the origin label
     is "suggested" for `origin: "suggestion"`, "rule" for `"rule"`.
   - PT: "Antes: {stamped.zoho_account} ({sugerido | regra})"
   i18n keys: `category.stamped.was`, `category.stamped.suggested`,
   `category.stamped.rule`. No button, no action.

3. The merchant, on the Matching tab. A charge row may carry
   `merchant: {name, match}` (`match` is "exact", "fuzzy" or "descriptor").
   Where the row shows the bank's text (`vendor`), add the merchant name
   after it in muted text when it is present and differs from the bank text
   ignoring case: "{vendor} · {merchant.name}". Same on Expenses grid rows,
   which also carry `merchant`, but only when `merchant.name` differs from
   `vendor.display` (usually it does not). Do not show `match`.
   `vendor.stamped` ({display, source}) also exists on grid rows; do not
   render it.

Do not change: how `posting_category`, `suggested_category`, the Confirm
button, `books_as`, the review states or the filters work; the Settings
merchant editor; any request the app sends.
````

## Verify after publish

`uv run tools/lovable-bundle-audit.py` greps the bundle for
`account_vendor_specific`, `stamped` and `merchant.name` / `category.stamped.was`.
A live check: a September OpenAI receipt on the Expenses grid shows its
registry account with "Was: ... (suggested)" under it.
