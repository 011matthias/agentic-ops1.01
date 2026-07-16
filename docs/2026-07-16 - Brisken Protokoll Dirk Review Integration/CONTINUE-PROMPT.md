Resume the Brisken Jochen-protokoll integration. Read the checkpoint at
`docs/2026-07-16 - Brisken Protokoll Dirk Review Integration/Checkpoint.md`
first for full context, then:

1. Fetch the SharePoint item's current version history via Graph (app-only
   creds in `workspace/clients/brisken/context/.env`, delegated token at
   `.scratch/graph_token.txt` if still valid — check for 401 first, re-sniff
   via CDP :9222 if dead). Item id `01SQ6DZAFF5BC365BXDZFI2BWYJ22QPWUM`,
   site `brisken.sharepoint.com,65b8d36f-2777-4cff-bd80-58ff9022d17c,e9089a15-9498-4149-a6f3-b4bc8e4d21ac`,
   path `01_MEETINGS/JOCHEN IN KA 260714/Protokoll-Jochen-Treasury-Assessment_2026-07-14_EN.docx`.

2. Check whether the upload landed: if the latest version's
   `lastModifiedDateTime` is at/after `2026-07-16T15:32:24Z` with size ≠
   43,801 bytes and author = Matthias Silva, it landed — just confirm and
   report done. (My session's background retry loop was still running,
   unconfirmed, when this session ended — it will NOT have carried over.)

3. If it did NOT land: the document is still Dirk's v10.0 (or later, if
   he's kept editing). Re-run the integration pipeline documented in the
   `project_jochen_treasury_assessment.md` memory (search "Protokoll-EN
   Runde 2") — unpack via `document-skills:docx` skill (needs
   `uv run --with defusedxml --with lxml`, `PYTHONUTF8=1` env on this
   Windows box), accept all of Dirk's tracked changes (unwrap `w:ins`,
   strip `w:del`/`trPr del` rows/`pPr rPr` paragraph marks/`*PrChange`),
   re-apply the fix list for his typing artifacts if his content changed
   again, re-answer his two comments (27: maturity/priority coding scope;
   108: Köhler/Scherif DE/US geography) with tracked Matthias-authored
   edits + threaded replies if not already resolved, pack + validate, then
   PUT to the SharePoint item content endpoint. If 423 (locked), don't
   loop blindly — check `lastModifiedDateTime` age; if he's been idle
   >20 min, either retry a few times or ask the user whether Dirk still
   has the file open.

4. Once uploaded and confirmed: this specific task is done. Do NOT
   forward or publish to Jochen — distribution is double-gated (Dirk's
   explicit "if good" in-thread, then a separate owner per-send yes for
   any actual mail). Just report the landed version to the user.

Don't re-derive anything already established in the checkpoint — it has
the full mechanics, the exact fix list, and the reasoning for every
integration decision made so far.
