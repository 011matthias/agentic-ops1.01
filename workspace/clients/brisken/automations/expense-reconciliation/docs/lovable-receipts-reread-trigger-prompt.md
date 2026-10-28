Background: the month history shows the month's last re-match with a short
label for what caused it (`last_rematch.trigger`, keys `mh.rematch.trigger.*`).
The backend has a new cause, `receipts_reread`: an operator had the month's
stored receipts read again by the current receipt reader (backlog item 240).
Today the page would print the raw value `receipts_reread`.

Add one entry next to the existing `mh.rematch.trigger.*` keys:

EN
  "mh.rematch.trigger.receipts_reread": "receipts read again",

PT
  "mh.rematch.trigger.receipts_reread": "recibos lidos novamente",

Do not change: any other key, the fallback key used for an unknown trigger,
the month history's layout, any API call. There is no new control: the re-read
is an operator action with no button in the app. Auth stays the bearer token;
no Supabase.
