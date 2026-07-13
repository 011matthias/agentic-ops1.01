# Registers the LeadDeskWorker scheduled task: every 15 minutes, weekdays,
# "run only when user is logged on" (Outlook COM needs the interactive
# session - an S4U/service task fails at Dispatch).
#
# Run once, elevated not required:
#   powershell -ExecutionPolicy Bypass -File install-task.ps1
#
# Disable / re-enable (the blunt kill switch):
#   schtasks /Change /TN LeadDeskWorker /DISABLE
#   schtasks /Change /TN LeadDeskWorker /ENABLE
param(
    [string]$TaskName = "LeadDeskWorker",
    [int]$EveryMinutes = 15
)

$cmd = Join-Path $PSScriptRoot "run-worker.cmd"
if (-not (Test-Path $cmd)) { throw "run-worker.cmd not found next to this script" }

$action = New-ScheduledTaskAction -Execute $cmd
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew
# Interactive logon type = "run only when user is logged on".
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Force
Write-Host "Registered $TaskName (every $EveryMinutes min, interactive session)."
Write-Host "The worker itself no-ops outside each campaign's send window; the"
Write-Host "capture pass (replies/bounces) still runs on every tick."
