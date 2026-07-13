"""Local Windows send worker: the 'hands' of the Lead Desk campaign engine.

The Fly app is the brain (who is due, what copy, caps, stop conditions);
this worker only executes: it claims due sends over the outbox API, fires
them through Outlook COM from matthias.silva@ (or stages warm-degree drafts
in Dirk's mailbox), polls both inboxes for replies/bounces, and reports
everything back. It never decides who gets mailed.

Runs as a Windows scheduled task ("run only when user is logged on" -
Outlook COM needs the interactive session) from a pinned worktree. All
state + secrets live under a gitignored home dir (``--home``).
"""
