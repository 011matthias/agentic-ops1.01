# Lovable prompt: drop the "asked for" mark from the chase list

**Background.** On 2026-10-29 the owner asked what the "Mark the receipt as
asked for" button in the charges-without-receipts list was for. It only
records that someone asked for the receipt elsewhere: it sends nothing and
closes nothing (`POST /api/runs/{id}/receipt-requested`, item 107). The owner
answered "remove it". UI only: the route, the row fields and the summary
counter stay in the API, unused, so any marks already stored survive and the
button can come back without a backend change.

## Paste this into Lovable

````
Remove the "Mark the receipt as asked for" button from the "Charges without receipts" list, on every row and in any bulk or detail view that repeats it.

Also remove everything that only exists because of that button:
- the "asked" badge or "Asked on {date}" / "requested to {address}" text on a row
- the "n_requested" / "already asked for" counter in the group headers
- the undo/clear control for the asked state
- the call to POST /api/runs/{run_id}/receipt-requested

Do not change anything else:
- Keep the "No receipt expected" button and its reason dialog exactly as they are.
- Keep the list grouping, amounts, portal hints and sorting.
- Do not touch the backend or the API client types. Fields like receipt_requested_at may still arrive in responses; ignore them.

Check afterwards that no row renders an empty gap where the button used to be, and that the list looks the same on mobile width.
````

## Verify after publish

Bundle audit over all chunks, lazy ones included
([[reference_lovable_merge_is_not_live]]): `receipt-requested` and
`receipt_requested_at` read 0 files, while the control `no-receipt-expected`
still reads 1. Applied as Lovable `21082b4` (`ReceiptChasePanel.tsx` -120,
`RunWorkbench.tsx` -9) and verified on the published site 2026-10-29: 0 / 0
across 49 chunks, control 1.
