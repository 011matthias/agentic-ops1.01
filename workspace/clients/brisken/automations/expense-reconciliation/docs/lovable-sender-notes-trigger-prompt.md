Background: the month history shows the month's last re-match with a short
label for what caused it (`last_rematch.trigger`, keys `mh.rematch.trigger.*`).
The backend has a new cause, `sender_notes`: an operator applied the notes our
senders typed above their forwarded receipts to a month's stored receipts, and
a receipt's company moved (backlog item 251). Today the page would print the
raw value `sender_notes`.

Add one entry next to the existing `mh.rematch.trigger.*` keys:

EN
  "mh.rematch.trigger.sender_notes": "senders' notes applied",

PT
  "mh.rematch.trigger.sender_notes": "notas dos remetentes aplicadas",

Do not change: any other key, the fallback key used for an unknown trigger,
the month history's layout, any API call. There is no new control: applying
the notes is an operator action with no button in the app. Auth stays the
bearer token; no Supabase.
