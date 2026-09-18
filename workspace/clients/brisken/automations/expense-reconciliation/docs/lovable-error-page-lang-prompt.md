# Lovable prompt: the two error screens in the reader's language (item 130 §6)

> **NOT APPLIED** (see PROMPT-STATUS.md). No backend gate: this is copy only.
> Item 130's other five sections are live and verified (the `errorText` helper,
> the advisory helper, 16 converted `toast.error` call sites in the workbench
> route chunk and zero `.message)` left, and the row chips driven on screen as
> NEAR MISS in EN and QUASE IGUAL in PT). The two screens below are the one half
> that never landed: both still render hardcoded English on a Portuguese screen.
>
> Measured 2026-09-18 against the published bundle (44 chunks, 1,174 KB) and
> driven cold in PT: `/this-route-does-not-exist-xyz` with `brisken.lang` set to
> `pt` renders "404 / Page not found / The page you're looking for doesn't exist
> or has been moved. / Go home", in English, while the rest of the app is in
> Portuguese. `data-pt`, "Esta página não carregou", "Algo deu errado do nosso
> lado", "Tentar de novo" and "Voltar ao início" are absent from every chunk;
> "This page didn't load" and "Something went wrong on our end" are present in
> the entry chunk as plain JSX string children.

````markdown
The app calls the FastAPI backend at `https://api.expenses.brisken.com` as a JSON API. Do NOT add Supabase or any database. Do not change any request the app makes: this is a copy change only, in two components. Auth is untouched.

## Why

The tool speaks Portuguese to Criss everywhere except the two screens she meets when something has gone wrong, which are exactly the screens where a reader most needs to understand what happened and what to do next. Both are React components with English strings written straight into the JSX, so neither follows the language the rest of the app is already reading.

Both live in the app's root route file (the one that defines `notFoundComponent` and the TanStack root `errorComponent`). Today they render:

- **Not found:** `404`, `Page not found`, `The page you're looking for doesn't exist or has been moved.`, `Go home`
- **Crash:** `This page didn't load`, `Something went wrong on our end. You can try refreshing or head back home.`, `Try again`, `Go home`

## 1. Read the language WITHOUT the provider

Do not call `useT()` in either component. The crash component is the root error boundary: it renders precisely when the tree below it has failed, and the i18n provider is part of that tree, so a hook into it can throw inside the boundary that was supposed to catch the failure. The not-found component is written the same way for one reason only: the two screens should stay identical in shape, so the next person editing one does not have to work out why the other is different.

Add one tiny local helper in the same file, above both components:

```ts
const errLang = (): "en" | "pt" => {
  try {
    return localStorage.getItem("brisken.lang") === "pt" ? "pt" : "en";
  } catch {
    return "en";
  }
};
```

`"brisken.lang"` with the values `"en"` and `"pt"` is the key the app already stores the language under; read it, never write it.

## 2. The strings, picked in the component

Keep the existing markup, classes and behaviour exactly as they are (the `Link to="/"`, the `router.invalidate()` plus `reset()` on Try again, the `Pc(e, { boundary: "tanstack_root_error_component" })` report call). Change only the string children, each one picked by `errLang()`:

Not found:

| Today (EN, keep) | PT-BR |
|---|---|
| `Page not found` | Página não encontrada |
| `The page you're looking for doesn't exist or has been moved.` | A página que você procura não existe ou foi movida. |
| `Go home` | Voltar ao início |

The bare `404` is a numeral and stays as it is.

Crash:

| Today (EN, keep) | PT-BR |
|---|---|
| `This page didn't load` | Esta página não carregou |
| `Something went wrong on our end. You can try refreshing or head back home.` | Algo deu errado do nosso lado. Você pode atualizar a página ou voltar ao início. |
| `Try again` | Tentar de novo |
| `Go home` | Voltar ao início |

## 3. Two details that are easy to miss

- Set `document.documentElement.lang` to `pt-BR` or `en-US` to match, in the same `useEffect` the crash component already uses for its error report, and in a small one on the not-found component. A screen reader announcing Portuguese text with an English lang attribute reads it wrong.
- Do NOT touch `src/lib/error-capture.ts` or `lovable-error-reporting.ts`. Those report to the server and must keep sending the raw English, so the reports stay greppable.

## Do not change

Every other screen, the `errorText` helper and its call sites, the advisory helper, the row warning chips, the dictionary in `src/lib/i18n.tsx`, and anything that makes a request. None of the strings above goes in the dictionary: both components have to work when the dictionary's own chunk is the thing that failed to load.

## Checking it landed

1. In the app, switch to Portuguese, then open `/this-route-does-not-exist-xyz`. It reads "Página não encontrada" and "A página que você procura não existe ou foi movida.", with "Voltar ao início" on the link. In English it reads exactly what it reads today.
2. `document.documentElement.lang` is `pt-BR` on that page in Portuguese.
3. The crash screen, forced by throwing inside a route (or by blocking a lazy chunk in devtools), reads "Esta página não carregou" with "Tentar de novo" and "Voltar ao início". "Tentar de novo" still reloads the route and "Voltar ao início" still goes to `/`.
4. Clearing site data and opening the not-found page with no stored language reads English, not a blank screen.
5. Searching the built bundle for "Voltar ao início" hits; searching for "Page not found" still hits too, because English is kept.
````
