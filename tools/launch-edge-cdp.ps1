# Launch a DEDICATED Edge automation instance with CDP enabled, without
# touching the user's main Edge session (separate --user-data-dir sidesteps
# the "must close all tabs to get the debug port" problem entirely).
#
# Usage:  powershell -File tools/launch-edge-cdp.ps1 [-Port 9223] [-Url <start url>]
#
# The profile persists at %LOCALAPPDATA%\EdgeCdpAutomation, so web sessions
# (e.g. brisken.sharepoint.com) survive relaunches: sign in once, reuse forever.
# Scripts attach via CDP_PORT=9223 (see .scratch/deckgen/_sp_reorg_execute.py
# pattern: read the port from the CDP_PORT env var, default 9222).
param(
    [int]$Port = 9223,
    [string]$Url = "about:blank"
)

$alive = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
if ($alive) {
    Write-Output "CDP already listening on :$Port -- reusing the running instance."
    exit 0
}

$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Error "msedge.exe not found"; exit 1 }

$profileDir = "$env:LOCALAPPDATA\EdgeCdpAutomation"
New-Item -ItemType Directory -Force $profileDir | Out-Null

& $edge --user-data-dir="$profileDir" --remote-debugging-port=$Port --no-first-run --new-window $Url
Start-Sleep 5
$alive = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
Write-Output "automation Edge on :$Port alive=$alive profile=$profileDir"
exit ($alive ? 0 : 1)
