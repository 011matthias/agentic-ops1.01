' Runs the passed command line with no visible console window, WAITS for it,
' and exits with the child's exit code.
'
' The wait is deliberate. The first version launched detached (bWaitOnReturn =
' False), so the scheduled task recorded LastTaskResult 0 whatever happened to
' the watcher; the 2026-09-07 auth outage therefore looked healthy in Task
' Scheduler for 46 hours. Propagating the real code makes task history honest:
' 0 = collected, 1 = cycle collected nothing (backoff, dead session, no data).
'
' Usage: wscript run-hidden.vbs "<full command line>"
If WScript.Arguments.Count < 1 Then WScript.Quit 2
WScript.Quit CreateObject("WScript.Shell").Run(WScript.Arguments(0), 0, True)
