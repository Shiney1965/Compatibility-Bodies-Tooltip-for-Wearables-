@echo off
REM AlanTooltipCompat — One-click sidecar pipeline (FULL: user mods + vanilla).
REM Double-click this in Explorer to run.
REM
REM v1.2 (2026-05-21): tee'd logging via _pipeline_runner.ps1. Every run
REM writes a complete log to BG3 Mods\Pipeline Logs\pipeline_full_<ts>.txt
REM in addition to the live console.

cd /d "%~dp0"

REM Tell run_all.py to keep the console open via input() when it finishes.
set ALAN_TOOLTIP_COMPAT_PAUSE=1

echo.
echo [run_all.bat] Sidecar dir: %~dp0
echo [run_all.bat] Helper .ps1: %~dp0_pipeline_runner.ps1
if exist "%~dp0_pipeline_runner.ps1" (
    echo [run_all.bat] Helper present: YES
) else (
    echo [run_all.bat] Helper present: NO -- file is missing!
)
echo [run_all.bat] About to invoke PowerShell...
echo.

REM Delegate to the helper PowerShell script. Using -ExecutionPolicy Bypass
REM so an unsigned local .ps1 runs regardless of system policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_pipeline_runner.ps1" -Mode full

set RC=%errorlevel%
echo.
echo ============================================================================
echo  PowerShell exited with code %RC%
echo ============================================================================

REM Unconditional pause so the window ALWAYS stays open. Removes prior
REM if-errorlevel-1 gating which was failing to fire in some error paths.
echo.
echo Press any key to close this window...
pause >nul
