# Proposed edits to shared files (none applied)

Per the isolation rules this session edits nothing outside `output/leadgen-task-7/`. Three proposals for whoever owns the shared surfaces:

1. **Master sheet `linkedin_url` back-fill.** 24 verified profile URLs in `tier3-roster.csv` (`resolve_confidence` high or medium), of which 2 are new (Forst, Hacikyaner) and 21 confirm existing values. One on-file value should be flagged rather than trusted: Lukas Blauth's `lukas-blauth-92368a418` could not be corroborated anywhere and the only public profile under that name is an unrelated academic. Suggested action: copy the `resolved_linkedin_url` column into the master sheet at the next regeneration of `rome2026-post-event-master-contacts.xlsx`, and mark Blauth's cell for visual verification.

2. **Master sheet `linkedin_status` for the 29.** Once the connect batch runs, set `linkedin_status` = "Invited YYYY-MM-DD" per row (the column exists and currently reads "-" / "No profile on file"). Keeping the status in the sheet as well as the roster CSV is what protects the NEXT tier's dedup now that `post_event_outreach` is gone.

3. **`post-event-sequences.md` Tier-3 paragraph.** It still sizes Tier 3 at "~90" fob contacts. After stop, prior-tier name-dedup and personal-note routing, the actually contactable templated set is 29 (plus 11 routed to personal motions). A one-line update there would stop the next session from re-deriving the same arithmetic.
