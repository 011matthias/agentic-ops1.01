' Runs the passed command line with no visible console window.
' Used by the VintedWatcher scheduled task so the 5-minute cycle never
' flashes a terminal. Usage: wscript run-hidden.vbs "<full command line>"
If WScript.Arguments.Count < 1 Then WScript.Quit 1
CreateObject("WScript.Shell").Run WScript.Arguments(0), 0, False
