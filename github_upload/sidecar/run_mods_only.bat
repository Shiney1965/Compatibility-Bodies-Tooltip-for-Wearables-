@echo off
REM ============================================================================
REM AlanTooltipCompat — Mods-only sidecar pipeline (FAST PATH)
REM
REM Same as run_all.bat but SKIPS the maintainer steps (1B/2B/3B) that re-extract
REM base-game .pak files (Gustav.pak, Shared.pak, etc.) and regenerate
REM vanilla_cache.lua. Use this when:
REM
REM   - You've installed/removed/updated user mods and want to refresh
REM     compat_cache.json without waiting for the base-game extract.
REM   - You don't need to ship a fresh vanilla_cache.lua bundled in the mod
REM     (the existing one inside the .pak is still valid).
REM
REM Mechanism: sets ATC_GAME_DATA_DIR to a path that doesn't exist.
REM run_all.py's detect_bg3_install_data_dir() returns None for non-existent
REM paths, which causes the maintainer banner "Maintainer steps skipped — game
REM Data folder not found" and only steps 1A / 2A / 3A run.
REM
REM If you ALSO need vanilla_cache.lua refreshed (e.g. after a BG3 patch),
REM run run_all.bat (the full pipeline) instead.
REM
REM v1.2 (2026-05-21): tee'd logging via _pipeline_runner.ps1. Every run
REM writes a complete log to BG3 Mods\Pipeline Logs\pipeline_modsonly_<ts>.txt
REM in addition to the live console.
REM ============================================================================

cd /d "%~dp0"

REM Hold the console window open after run_all.py finishes via input().
set ALAN_TOOLTIP_COMPAT_PAUSE=1

REM This path intentionally doesn't exist. run_all.py reads ATC_GAME_DATA_DIR,
REM verifies the path is a directory, and falls back to None when it isn't.
REM None triggers the "skip maintainer steps" branch.
set ATC_GAME_DATA_DIR=C:\__intentionally_nonexistent_path_to_skip_vanilla_extract__

echo.
echo ============================================================================
echo  AlanTooltipCompat - Mods-only refresh
echo ============================================================================
echo  Mode:              mods-only ^(skipping base-game extract^)
echo  ATC_GAME_DATA_DIR: %ATC_GAME_DATA_DIR%
echo  ^(this path is intentionally fake to force the skip^)
echo ============================================================================
echo.

echo [run_mods_only.bat] Sidecar dir: %~dp0
echo [run_mods_only.bat] Helper .ps1: %~dp0_pipeline_runner.ps1
if exist "%~dp0_pipeline_runner.ps1" (
    echo [run_mods_only.bat] Helper present: YES
) else (
    echo [run_mods_only.bat] Helper present: NO -- file is missing!
)
echo [run_mods_only.bat] About to invoke PowerShell...
echo.

REM Delegate to the helper PowerShell script. Using -ExecutionPolicy Bypass
REM so an unsigned local .ps1 runs regardless of system policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_pipeline_runner.ps1" -Mode modsonly

set RC=%errorlevel%
echo.
echo ============================================================================
echo  PowerShell exited with code %RC%
echo ============================================================================

REM Unconditional pause so the window ALWAYS stays open.
echo.
echo Press any key to close this window...
pause >nul
