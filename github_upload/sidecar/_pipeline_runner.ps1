# _pipeline_runner.ps1
# ---------------------
# AlanTooltipCompat — pipeline runner with tee'd logging.
#
# Why a separate .ps1: cmd-to-PowerShell quoting (with paths that contain
# spaces like "BG3 Mods", plus the call operator &, pipes, and Tee-Object
# arguments) is brittle. A real .ps1 file with parameters is far more
# reliable than inline -Command strings.
#
# Called from run_all.bat / run_mods_only.bat (and shipped refresh_cache.bat)
# with a single argument: the run "mode" used in the log filename.
#
# What it does:
#   1. Resolve <sidecar>\..\Pipeline Logs\  (one level up from this .ps1).
#   2. Make the dir if missing.
#   3. Generate a sortable timestamp.
#   4. Build the log path: pipeline_<mode>_<YYYY-MM-DD_HHMMSS>.txt.
#   5. Invoke `python -u run_all.py` and tee stdout+stderr to console + log.
#   6. Exit with Python's exit code.
#
# Note on Python's input() prompt at the end:
#   run_all.py calls input() if ALAN_TOOLTIP_COMPAT_PAUSE=1. stdin is
#   not affected by the pipeline, so the prompt still reads from the console.

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('full', 'modsonly', 'refresh')]
    [string]$Mode
)

$ErrorActionPreference = 'Continue'

# All paths resolved relative to THIS .ps1's location so the same file
# works from the dev folder AND from a shipped bundle.
$sidecarDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir     = Join-Path $sidecarDir '..\Pipeline Logs'
$pyScript   = Join-Path $sidecarDir 'run_all.py'

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$logFile   = Join-Path $logDir ("pipeline_${Mode}_${timestamp}.txt")

Write-Host ''
Write-Host '============================================================================'
Write-Host "  Logging this run to:"
Write-Host "    $logFile"
Write-Host '============================================================================'
Write-Host ''

# Run Python unbuffered (-u) so console output appears live rather than
# block-buffered to the pipe. Merge stderr into stdout (2>&1) so warnings
# and tracebacks land in the log too.
#
# -W ignore::SyntaxWarning is a defensive measure: if any Python source in
# the project triggers a SyntaxWarning (e.g. an unescaped Windows path like
# "\Larian" in a docstring), Python writes the warning to stderr, PowerShell
# 5.1 wraps the stderr line as a NativeCommandError with multi-line error
# decoration, and the resulting backpressure on the stderr pipe can cause
# the rest of the pipeline to appear stuck. Suppressing SyntaxWarnings at
# the Python level prevents this whole class of problem. (The known offender
# in unpack_paks.py's docstring was already converted to a raw string on
# 2026-05-21, but this flag is cheap insurance against future similar bugs.)
#
# Note: NO -Encoding parameter on Tee-Object. That flag was introduced
# in PowerShell 6+ (Core), but Windows ships with PowerShell 5.1 by default
# where it doesn't exist. Passing -Encoding on 5.1 produces:
#   "Tee-Object : A parameter cannot be found that matches parameter
#    name 'Encoding'."
# 5.1's Tee-Object writes UTF-16LE by default; Notepad and any modern text
# editor read that fine. If we later need UTF-8 logs (e.g. for cross-platform
# grep tooling) we'd need to use a StreamWriter explicitly or convert post-run.
& python -u -W ignore::SyntaxWarning $pyScript 2>&1 | Tee-Object -FilePath $logFile

$exit = $LASTEXITCODE
if ($null -eq $exit) { $exit = 0 }
exit $exit
