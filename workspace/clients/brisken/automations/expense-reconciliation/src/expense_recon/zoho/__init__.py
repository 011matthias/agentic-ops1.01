"""Zoho Books integration (BLUEPRINT slice 4.7 / 4b / 4.8).

`client.py` holds the OAuth client: read endpoints plus the slice-4b
`create_journal` write path. `idempotent.py` is the 4.8 idempotency
ledger + guarded poster that makes double-posting structurally
impossible. Posting is reachable only through `zoho_post_cli` and is
OFF by default (config `zoho.post.enabled` AND env
`EXPENSE_RECON_ZOHO_POST=1` AND the org allowlist AND `--go`).
"""
