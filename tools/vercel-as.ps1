<#
.SYNOPSIS
Run the Vercel CLI as a named identity, so this machine can work on BOTH
unpauseai.com (akkton account) and the Brisken projects (matthias account)
without either login evicting the other.

.DESCRIPTION
PowerShell twin of tools/vercel-as.sh, and the one that actually runs on this
machine: the `bash` on PATH here is the WSL stub
(AppData\Local\Microsoft\WindowsApps\bash.exe), not Git Bash, so the .sh
version executes in a Linux filesystem where the Windows `vercel` install does
not exist. The Vercel CLI itself resolves to a .ps1, so PowerShell is the
native home for this wrapper.

WHY IT EXISTS
The Vercel CLI keeps ONE interactive session, and `--scope` only switches
between TEAMS INSIDE the logged-in account. akkton and matthias are two
separate ACCOUNTS, so whoever logged in last wins and the other account's
projects become invisible. Recorded live 2026-07-22: the session was
matthias-5647, `vercel project ls` showed only the Brisken/personal projects,
and the akkton org owning `platform` (unpauseai.com) reported "scope does not
exist" -- so the platform force-deploy could not run at all. Deploying under
the only visible scope would have created a phantom "platform" project under
the wrong team.

`vercel -Q DIR` / `--global-config=DIR` (verified on CLI 53.2.0) relocates the
CLI's global directory, and with it the auth store. Point each identity at its
own directory and both stay logged in side by side, permanently.

.EXAMPLE
# One-time setup per identity (interactive browser login):
tools\vercel-as.ps1 unpause login
tools\vercel-as.ps1 brisken login

.EXAMPLE
# Daily use; identity comes from the project, never from "who am I today":
tools\vercel-as.ps1 unpause --prod --force --yes
tools\vercel-as.ps1 brisken project ls
tools\vercel-as.ps1 unpause whoami          # -> akkton

.EXAMPLE
# Headless / CI / agent use, no interactive login at all:
$env:VERCEL_TOKEN_UNPAUSE = '...'; tools\vercel-as.ps1 unpause --prod
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Identity,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'

function Show-Usage {
    @'
usage: tools\vercel-as.ps1 <identity> [vercel args...]

identities:
  unpause   akkton account     -> unpauseai.com (project: platform)
  brisken   matthias account   -> brisken.com, resources.brisken.com, etc.
                                  (scope: matthias-neumanns-projects)

examples:
  tools\vercel-as.ps1 unpause login
  tools\vercel-as.ps1 unpause --prod --force --yes
  tools\vercel-as.ps1 brisken project ls

Each identity keeps its own auth store under ~\.vercel-<identity>, so the two
logins coexist. Set VERCEL_TOKEN_UNPAUSE / VERCEL_TOKEN_BRISKEN to run headless.
'@ | Write-Error -ErrorAction Continue
    exit 64
}

if ([string]::IsNullOrWhiteSpace($Identity) -or $Identity -in @('-h', '--help', 'help')) {
    Show-Usage
}
if (-not $Args -or $Args.Count -eq 0) { Show-Usage }

# Identities are declared, never guessed. Adding one is a three-line edit.
switch ($Identity) {
    'unpause' {
        $configDir = if ($env:VERCEL_CONFIG_UNPAUSE) { $env:VERCEL_CONFIG_UNPAUSE }
                     else { Join-Path $HOME '.vercel-unpause' }
        $token = $env:VERCEL_TOKEN_UNPAUSE
        # akkton's own account scope is the default; forcing a foreign scope
        # here is precisely the wrong-team deploy this wrapper prevents.
        $scope = ''
    }
    'brisken' {
        $configDir = if ($env:VERCEL_CONFIG_BRISKEN) { $env:VERCEL_CONFIG_BRISKEN }
                     else { Join-Path $HOME '.vercel-brisken' }
        $token = $env:VERCEL_TOKEN_BRISKEN
        $scope = 'matthias-neumanns-projects'
    }
    default {
        Write-Error "unknown identity: $Identity" -ErrorAction Continue
        Show-Usage
    }
}

if (-not (Test-Path -LiteralPath $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$cliArgs = @('--global-config', $configDir)
if (-not [string]::IsNullOrWhiteSpace($token)) { $cliArgs += @('--token', $token) }
# `login` establishes the identity; there is no session yet to scope.
if ($scope -and $Args[0] -notin @('login', 'logout')) { $cliArgs += @('--scope', $scope) }

$tokenNote = if ($token) { ' (token mode)' } else { '' }
Write-Host "[vercel-as] identity=$Identity config=$configDir$tokenNote" -ForegroundColor DarkGray

& vercel @cliArgs @Args
exit $LASTEXITCODE
