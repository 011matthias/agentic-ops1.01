# Lovable prompt: a month stops fetching the all-months card roll-up it does not need

**NOT PASTED.** Owner, 2026-09-25: "months are also pretty slow to open",
beside "[the months card strip] is lagging and loading way later than the
rest when initially opening tool".

**No backend gate.** The backend half (the same PR) makes
`GET /api/cards/status` about 28% cheaper and changes no payload byte; this
prompt removes the call from every full load of a month with no card picked.

**What it fixes, measured.** `CardScope` (rendered on both the Expenses and
the Matching page of every month) looks up the picked card's chip text with
`useQuery(["cards", "status"])`, before it checks whether a card is picked
at all. Navigating inside the app reuses the months list's copy, but a FULL
load of a month (a reload, a bookmark, a link, a new tab: how the tool is
opened) has no copy, so it fires `/api/cards/status`, which builds every
month on the one backend machine alongside the month's own payload.
Driven 2026-09-25 on a local build of the SPA against a copy of the live
data, alternating builds: a full load of July took 2.21-3.00 s with the
roll-up fired (today) and 1.78-1.89 s with this change (no roll-up request);
July deep-linked with `?card=card-2838` still made exactly one request and
showed 2838; in-app opens made none either way. Every drive was read-only
(non-GET requests aborted; none was attempted).

````markdown
On the month pages (`/expenses/$batchId` and `/runs/$runId`), stop the card scope line from fetching the all-months card roll-up when no card is picked. Nothing on screen changes. Do NOT add Supabase or any database; the app calls the FastAPI backend at `https://api.expenses.brisken.com` with the existing `Authorization: Bearer <token>`. No new backend field.

## Why

`GET /api/cards/status` builds every month on the server. The months list (`/months`) needs it for its card strip. A month page only needs it for one thing: the chip text of the card picked with `?card=`, in the scope line `CardScope` renders. Today that lookup also runs when no card is picked, so every full load of a month (reload, bookmark, link, new tab) fetches the whole roll-up alongside the month's own data, and the month arrives about a second later than it needs to.

## 1. `useCardName` in `src/components/CardScope.tsx`

It is called unconditionally at the top of `CardScope`, before `if (scope === null) return null;`. Keep the call where it is (hooks must run in the same order every render), and change its query to:

```ts
const status = useQuery({
  queryKey: ["cards", "status"],
  queryFn: getCardsStatus,
  retry: 1,
  enabled: !!key,
  staleTime: 60_000,
});
```

- `enabled: !!key`: with no card picked (`scope === null`) or on the no-card section (`scope === ""`), nothing is fetched. For `""` the lookup never found a card anyway (no card has the key `""`), so the text it shows today already comes from the month's own `sections`, and it still does.
- `staleTime: 60_000`: with a card picked, a copy fetched in the last minute is used as it is. Coming from `/months` with a card selected, that copy is always there, so opening the month fetches nothing extra. After a minute the chip text refreshes as it does today.

Everything else in `useCardName` stays: the `cards.find((c) => c.key === key)` lookup, the fallback to `sections` when the card is not in the payload or the query has not answered, and the `unknown` flag.

## 2. Do not change

The `/months` page's own `["cards", "status"]` query in `MonthsHome` (it keeps refreshing its badges every time the page opens). The `/cards` page. The scope line's text, its links and its statement line. Anything the month page fetches for itself.

## How to check it worked

Open the browser's network panel.

1. Open `/expenses/<a month id>` directly in a fresh tab (no `?card=`), then reload it. **No** request to `/api/cards/status`, either time. Switch to its Matching page and reload: still none. (Today each of those loads makes one.)
2. Open `/expenses/<a month id>?card=card-2838` directly in a fresh tab. Exactly **one** request to `/api/cards/status`, and the scope line reads 2838 as today.
3. On `/months`, pick card **2838** and click a month row. The scope line reads 2838, with **no new** request to `/api/cards/status` (the strip's copy is reused).
4. With **No card** picked on `/months`, open a month: the scope line reads the no-card text as today, with no request to `/api/cards/status`.
````

## Verify after publish

Field names cannot prove this one (it removes a call rather than reading a
new field), so the check is a drive: steps 1 and 2 above, counting
`/api/cards/status` requests. Replay the heavy payloads per
`feedback_recon_drive_replay_payloads` and let `/api/cards/status` itself go
to the network only in step 3, where exactly one request is the pass.
