@echo off
REM ============================================================================
REM install_diagnostic_probe.bat — v1.1 R&D helper
REM
REM Adds DiagnosticProbe.lua to the mod source, edits BootstrapClient.lua to
REM Ext.Require it, then calls build_pak.bat to re-pack the mod.
REM
REM USAGE:
REM   install_diagnostic_probe.bat            (install)
REM   install_diagnostic_probe.bat --uninstall (revert)
REM
REM Idempotent — safe to run twice.
REM Backup of original BootstrapClient.lua is kept OUTSIDE the mod source
REM (so it doesn't accidentally get packed into the .pak).
REM ============================================================================

setlocal EnableDelayedExpansion

REM --- Paths (edit only if the project layout moves) -------------------------
set "SIDECAR_DIR=%~dp0"
set "MOD_SRC=%SIDECAR_DIR%..\AlanTooltipCompat_Mod"
set "LUA_DIR=%MOD_SRC%\Mods\AlanTooltipCompat_a7c0ffee-7501-4f00-a17a-c00b08ec4377\ScriptExtender\Lua"
set "BOOT_LUA=%LUA_DIR%\BootstrapClient.lua"
set "PROBE_SRC=%SIDECAR_DIR%DiagnosticProbe.lua"
set "PROBE_DST=%LUA_DIR%\DiagnosticProbe.lua"
REM Backup intentionally OUTSIDE the mod source (so divine.exe doesn't pack it).
set "BOOT_BAK=%SIDECAR_DIR%BootstrapClient.lua.before_probe"
set "BUILD_BAT=%SIDECAR_DIR%build_pak.bat"

REM Marker line we add to BootstrapClient.lua. findstr matches a substring so
REM the unique sentinel "DiagnosticProbe-INSTALL-MARKER" makes idempotency
REM checks unambiguous even if the comment text drifts.
set "MARKER=DiagnosticProbe-INSTALL-MARKER"

echo.
echo ============================================================================
echo Compatible Bodies Tooltip - Diagnostic Probe installer
echo ============================================================================
echo   Mode:           %1
echo   Mod source:     %MOD_SRC%
echo   Bootstrap Lua:  %BOOT_LUA%
echo   Probe source:   %PROBE_SRC%
echo   Probe dest:     %PROBE_DST%
echo   Backup path:    %BOOT_BAK%
echo   build_pak.bat:  %BUILD_BAT%
echo.

REM --- Sanity checks ---------------------------------------------------------
if not exist "%BOOT_LUA%" (
    echo ERROR: BootstrapClient.lua not found at:
    echo   %BOOT_LUA%
    echo Check the path. Aborting.
    pause
    exit /b 1
)
if not exist "%BUILD_BAT%" (
    echo ERROR: build_pak.bat not found at:
    echo   %BUILD_BAT%
    echo Aborting.
    pause
    exit /b 1
)

REM --- Branch on install vs uninstall ----------------------------------------
if /I "%1"=="--uninstall" goto :uninstall
if /I "%1"=="-u" goto :uninstall
goto :install


REM ============================================================================
REM INSTALL PATH
REM ============================================================================
:install
echo --- INSTALL ---
echo.

if not exist "%PROBE_SRC%" (
    echo ERROR: DiagnosticProbe.lua not found next to this script at:
    echo   %PROBE_SRC%
    echo Aborting.
    pause
    exit /b 1
)

REM 1. Copy DiagnosticProbe.lua into the mod source folder.
echo [1/4] Copying DiagnosticProbe.lua into mod source...
copy /Y "%PROBE_SRC%" "%PROBE_DST%" >nul
if errorlevel 1 (
    echo ERROR: copy failed.
    pause
    exit /b 1
)
echo       OK -^> %PROBE_DST%

REM 2. Back up BootstrapClient.lua if no backup exists yet.
echo [2/4] Backing up BootstrapClient.lua...
if exist "%BOOT_BAK%" (
    echo       Existing backup found at %BOOT_BAK% -- leaving it alone.
) else (
    copy /Y "%BOOT_LUA%" "%BOOT_BAK%" >nul
    if errorlevel 1 (
        echo ERROR: backup copy failed.
        pause
        exit /b 1
    )
    echo       OK -^> %BOOT_BAK%
)

REM 3. Append the require line if not already present.
REM
REM NOTE: every `(` and `)` inside an echo that lives inside an `if (...)`
REM block must be escaped as `^(` and `^)`. Otherwise cmd.exe treats the
REM inner `)` as the close of the IF block, splitting the conditional in
REM half and printing BOTH branches' output. This is the bug that produced
REM the spurious "Already present -- skipped." line after a fresh install
REM and left the appended Lua comment missing its closing paren.
echo [3/4] Adding require line to BootstrapClient.lua...
findstr /C:"%MARKER%" "%BOOT_LUA%" >nul 2>&1
if errorlevel 1 (
    REM Not present -- append.
    >>"%BOOT_LUA%" echo.
    >>"%BOOT_LUA%" echo -- %MARKER%  ^(added by install_diagnostic_probe.bat; remove via --uninstall^)
    REM IMPORTANT: BG3SE's Ext.Require does NOT auto-append .lua — must pass full filename.
    >>"%BOOT_LUA%" echo pcall^(Ext.Require, "DiagnosticProbe.lua"^)
    echo       OK -- added 3 lines.
) else (
    echo       Already present -- skipped.
)

REM 4. Re-pack.
echo [4/4] Calling build_pak.bat to re-pack the mod...
echo ----------------------------------------------------------------------
call "%BUILD_BAT%"
set "BUILD_RC=%ERRORLEVEL%"
echo ----------------------------------------------------------------------
if not "%BUILD_RC%"=="0" (
    echo.
    echo WARNING: build_pak.bat returned %BUILD_RC%. The probe IS installed in
    echo source, but the .pak was not ^(re^)built. Fix the build error and re-run.
    pause
    exit /b %BUILD_RC%
)

echo.
echo DONE. The diagnostic probe is installed in the packed mod.
echo.
echo Next steps:
echo   1. Launch BG3 via BG3MM.
echo   2. Load any save and let the world finish loading.
echo   3. Open the BG3SE Debug Console window. You should see four
echo      ===== STAGE: ... ===== blocks prefixed [CompatProbe].
echo   4. Copy the entire BG3SE Debug Console window's contents OR
echo      the latest 'Extender Runtime ....log' from
echo      %%LOCALAPPDATA%%\Larian Studios\Baldur's Gate 3\Script Extender\
echo      into the workspace so Claude can read it.
echo   5. When done, run:  install_diagnostic_probe.bat --uninstall
echo.
pause
endlocal
exit /b 0


REM ============================================================================
REM UNINSTALL PATH
REM ============================================================================
:uninstall
echo --- UNINSTALL ---
echo.

REM 1. Restore BootstrapClient.lua from backup if we have one.
if exist "%BOOT_BAK%" (
    echo [1/3] Restoring BootstrapClient.lua from backup...
    copy /Y "%BOOT_BAK%" "%BOOT_LUA%" >nul
    if errorlevel 1 (
        echo ERROR: restore copy failed.
        pause
        exit /b 1
    )
    echo       OK -- BootstrapClient.lua restored.
    echo       (Leaving %BOOT_BAK% in place for safety. Delete it manually if you wish.)
) else (
    echo [1/3] No backup found at %BOOT_BAK%
    echo       Skipping restore. If the require line is still in BootstrapClient.lua,
    echo       remove it manually.
)

REM 2. DiagnosticProbe.lua in mod source: NOT deleted (workspace-safety rule).
echo [2/3] DiagnosticProbe.lua at:
echo       %PROBE_DST%
echo       is left in place. It does nothing without the require line in
echo       BootstrapClient.lua. Delete it manually before the v1.1 ship build
echo       if you want to keep the pak clean.

REM 3. Re-pack so the next pak no longer registers the probe.
echo [3/3] Calling build_pak.bat to re-pack without the probe...
echo ----------------------------------------------------------------------
call "%BUILD_BAT%"
set "BUILD_RC=%ERRORLEVEL%"
echo ----------------------------------------------------------------------
if not "%BUILD_RC%"=="0" (
    echo.
    echo WARNING: build_pak.bat returned %BUILD_RC%. The probe is removed from
    echo source, but the .pak was not (re)built.
    pause
    exit /b %BUILD_RC%
)

echo.
echo DONE. Probe uninstalled and mod re-packed.
echo.
pause
endlocal
exit /b 0
