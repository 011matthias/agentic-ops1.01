# Lovable prompt: what the bookkeeper knows about a merchant (note item M4)

Paste the block below into Lovable. It adds one free-text field to the
Merchants editor in Settings and one read-only block on the Memory page.

---

## Background

The merchant registry holds a merchant's structured facts: its canonical name,
its default category, its Zoho account, its cost centre, its card. What it has
never held is the part that does not fit a field: what Brisken actually buys
from this merchant, on which card and for which company, the thing Criss or
Dirk would tell a new bookkeeper on their first day.

`profile` is that. Free prose on the merchant entry. The backend reads it as
CONTEXT when it asks the model to categorise that merchant's receipts, which
is the only thing that reads it: no filter keys on it, no review state fires
on it, it carries no category and no account of its own, and it appears on no
expense row.

The backend half is live. This prompt is the screen half: somebody has to be
able to write the prose, and the Memory page should show what the tool is
actually reading for a vendor.

## 1. Settings, Merchants editor: one new field on each entry

`GET /api/settings` returns `merchants` as a map of canonical name to entry.
Each entry may now carry a `profile`. **It is optional and absent when unset**
(not null), exactly like `cost_center`, `receipt_portal` and `card_key`:

```json
{
  "merchants": {
    "Anthropic": {
      "aliases": ["Anthropic, PBC"],
      "category": "Software & Subscriptions",
      "zoho_account": null,
      "card_key": "card-2838",
      "card_key_learned": true,
      "cards_seen": ["card-2838"],
      "profile": "Cloud compute for the Lidar build. Always billed to Cloud Services on Dirk's card; the monthly line is committed-use, the spiky ones are training runs."
    }
  }
}
```

| Key | Type | Who writes it | Editable on screen |
|---|---|---|---|
| `profile` | string | an editor, and later the tool | **yes**, a multi-line text area |

**A multi-line text area, not a single-line input.** This is a paragraph, not
a label. Give it at least 4 visible rows and let it grow. Placeholder: the EN
/ PT-BR strings in section 4.

**The cap is 2,000 characters.** The backend truncates silently above that, so
show a counter once the text passes 1,800 and stop accepting input at 2,000
rather than letting somebody write a page that is cut off on save.

**Blank means absent.** Sending `"profile": ""` or whitespace removes the key.
Clearing the box and saving is how a profile is deleted; there is no separate
delete control.

**Lines starting `[tool YYYY-MM-DD]` are the tool's, not a person's.** The
backend may later append an observation it read off real receipts, always
marked with that prefix. Today nothing writes one, so you will not see any
yet, but build for it now:

- render those lines in a dimmer colour (the muted / secondary text colour
  already in the theme) with the rest of the prose in normal text;
- **never rewrite or reorder them.** They are part of the same string. When
  the editor saves, the whole value goes back exactly as it was shown, the
  person's edits included. Do not strip the machine lines on save.

## 2. THE WHOLE-MAP-REPLACE HAZARD (read this one twice)

`PUT /api/settings {"merchants": ...}` **replaces the entire merchant map**.
Anything your payload leaves out is erased, for every merchant, not just the
one being edited.

So the Merchants editor must read the full entry, keep every key it does not
understand, and send them all back. Concretely, on save each entry must still
carry: `aliases`, `category`, `zoho_account`, `multi_category`, `cost_center`,
`receipt_portal`, `card_key`, `card_key_learned`, `cards_seen`, **and now
`profile`**. If the editor builds its payload from a fixed list of fields it
knows about, adding `profile` to that list is the whole job; if it round-trips
the entry object, nothing breaks as long as you do not drop unknown keys.

This has bitten before: the `person` field on cards was erased exactly this
way. Round-trip the object.

## 3. Memory page: the profile on the vendor line

`GET /api/memory` returns `by_vendor[]`, one entry per vendor, already
rendered as a group with its per-company lines. Each entry now carries:

```json
{ "by_vendor": [
    { "vendor": "anthropic pbc",
      "merchant": "Anthropic",
      "category": "Software & Subscriptions",
      "multi_category": false,
      "profile": "Cloud compute for the Lidar build. ...",
      "companies": [ ... ] } ] }
```

| Key | Type | Meaning |
|---|---|---|
| `profile` | string, always present | the merchant's prose; `""` when it has none, or when the vendor resolves to no registry merchant |

**Render rule.** Under the vendor's heading, above the company lines, show the
profile as a read-only paragraph block when it is a non-empty string. When it
is `""`, render nothing at all: no empty box, no "No profile" placeholder, no
dash. A merchant without prose is the normal case today and must not look
like a gap.

Preserve the line breaks in the string (`white-space: pre-wrap`). Dim the
`[tool YYYY-MM-DD]` lines here too, same as in the editor.

Label it with the EN / PT-BR heading in section 4, and make the heading a link
or button that opens that merchant in the Settings > Merchants editor if that
navigation already exists; if it does not, do not build it.

## 4. Strings (EN + PT-BR)

| Key | EN | PT-BR |
|---|---|---|
| `merchants.profile.label` | What we know about this merchant | O que sabemos sobre este fornecedor |
| `merchants.profile.help` | What we buy here, on which card, for which company. Anything you would tell someone taking over the books. | O que compramos aqui, em qual cartão, para qual empresa. Tudo o que você contaria a quem assumisse a contabilidade. |
| `merchants.profile.placeholder` | Cloud compute for the Lidar build. Always billed to Cloud Services on Dirk's card. | Computação em nuvem para o projeto Lidar. Sempre faturado para a Cloud Services no cartão do Dirk. |
| `merchants.profile.counter` | {n} of 2000 characters | {n} de 2000 caracteres |
| `merchants.profile.machineLine` | Added by the tool | Adicionado pela ferramenta |
| `memory.profile.heading` | What we know about this merchant | O que sabemos sobre este fornecedor |

`merchants.profile.machineLine` is a tooltip / aria-label on a dimmed line,
not a visible caption on every one of them.

## 5. Do not change

- The auth model. Bearer token, exactly as today. No Supabase, no new client.
- Any other field on the merchant entry, in the editor or on the payload.
- The company lines under `by_vendor[]`, their sorting, or the `seeded` /
  `validated` chips on them.
- The expense grid. `profile` appears on no row and must not be added to one.
- The `unvalidated=1` filter behaviour on the Memory page.

## 6. Checks before you call it done

1. Open Settings > Merchants, write a two-paragraph profile on one merchant,
   save, reload the page: the prose comes back with its line breaks.
2. In the same session, edit a DIFFERENT merchant's category and save. Reload
   and confirm the first merchant still has its profile, its aliases and its
   card fields. This is the whole-map-replace check and it is the one that
   matters most.
3. Clear the profile box, save, reload: the field is gone, and the rest of the
   entry is intact.
4. Paste 2,500 characters: the counter appears, input stops at 2,000, and what
   saves is what was shown.
5. Open the Memory page: a vendor whose merchant has prose shows it; a vendor
   whose merchant has none shows no block at all, not an empty one.
6. Hand-add a line reading `[tool 2026-09-20] test line` in the editor, save,
   reopen: it is dimmed, it survives, and editing the paragraph above it does
   not disturb it. Remove it afterwards.
