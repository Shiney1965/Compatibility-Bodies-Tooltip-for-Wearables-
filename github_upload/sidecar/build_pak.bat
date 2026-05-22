@echo off
REM AlanTooltipCompat — One-click mod packer.
REM
REM Runs divine.exe create-package against the AlanTooltipCompat_Mod source folder
REM and writes the resulting .pak straight into the BG3 Mods folder so it's
REM installed immediately.
REM
REM Edit the paths below if your divine.exe or mod source moves.

setlocal

set DIVINE_EXE=C:\bg3-sidecar-work\tools\divine.exe
set MOD_SRC=%~dp0..\AlanTooltipCompat_Mod
REM Pak filename matches NexusMods listing name "Compatible Bodies Tooltip".
REM Old AlanTooltipCompat.pak will NOT be overwritten — see warning below.
set PAK_OUT=%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\CompatibleBodiesTooltip.pak
set OLD_PAK=%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\AlanTooltipCompat.pak

echo.
echo AlanTooltipCompat — Build pak
echo   divine.exe:  %DIVINE_EXE%
echo   Source:      %MOD_SRC%
echo   Output:      %PAK_OUT%
echo.

if not exist "%DIVINE_EXE%" (
    echo ERROR: divine.exe not found at %DIVINE_EXE%
    echo Put a fresh copy there, e.g. from C:\Modding\ExportTool-v1.20.4.zip\Packed\Tools\
    pause
    exit /b 1
)

if not exist "%MOD_SRC%\meta.lsx" if not exist "%MOD_SRC%\Mods" (
    echo ERROR: mod source folder is missing or empty at %MOD_SRC%
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM Pre-flight stowaway check (added 2026-05-20 after the v1.1 incident
REM where AlanTooltipCompat_Mod\CompatibleBodiesTooltip.pak got nested
REM inside a new pak and triggered BG3's modsettings-reset behavior).
REM
REM divine.exe packs EVERYTHING under MOD_SRC. A valid BG3 mod source has
REM only subdirectories at the root (Mods\, Public\, Localization\, etc.)
REM and meta.lsx -- it should NEVER have a .pak, .md, .zip, .bak, or .tmp
REM file sitting at the mod-source root. Abort with a clear error if any
REM are found.
REM ----------------------------------------------------------------------
set "STOWAWAY_FOUND="
for %%P in ("%MOD_SRC%\*.pak" "%MOD_SRC%\*.md" "%MOD_SRC%\*.zip" "%MOD_SRC%\*.bak" "%MOD_SRC%\*.tmp") do (
    if exist "%%~P" (
        echo STOWAWAY at mod-source root: %%~P
        set "STOWAWAY_FOUND=1"
    )
)
if defined STOWAWAY_FOUND (
    echo.
    echo ERROR: Stowaway file^(s^) detected at the mod source ROOT above.
    echo        divine.exe would pack these INSIDE the new .pak, which can
    echo        cause BG3 to wipe modsettings.lsx at mod-discovery time
    echo        ^(known as the "modsettings reset" or "nausea response"^).
    echo        Move or delete the stowaway file^(s^) and re-run this script.
    echo.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM Warn if any .bak files exist anywhere under MOD_SRC. The earlier
REM multitool pipeline used to pack .lua.bak files in place of the real
REM .lua files, so .bak presence is worth flagging.
REM
REM NOTE: use *.bak (wildcard) so 'for /r' only enumerates actual files.
REM The earlier `for /r MOD_SRC %%F in (BootstrapClient.lua.bak)` form
REM enumerated every subdirectory and printed false warnings even when
REM no .bak existed. The wildcard form is what we want.
REM ----------------------------------------------------------------------
for /r "%MOD_SRC%" %%F in (*.bak) do (
    echo.
    echo WARNING: %%F still exists in source. It will be packed too.
    echo          Consider deleting it before re-running this script.
    echo.
)

REM Warn if the old AlanTooltipCompat.pak still exists alongside the new
REM CompatibleBodiesTooltip.pak. Both share the same internal mod UUID, so
REM BG3 will conflict on load.
if exist "%OLD_PAK%" (
    echo.
    echo WARNING: Old pak still installed at:
    echo   %OLD_PAK%
    echo Delete it before launching BG3 to avoid duplicate-mod conflicts.
    echo.
)

echo ----------------------------------------------------------------------
echo Calling divine.exe...
echo ----------------------------------------------------------------------
"%DIVINE_EXE%" -g bg3 -a create-package -s "%MOD_SRC%" -d "%PAK_OUT%" -l info
set RC=%ERRORLEVEL%
echo ----------------------------------------------------------------------

if %RC% NEQ 0 (
    echo.
    echo ERROR: divine.exe exited with code %RC%
    pause
    exit /b %RC%
)

echo.
echo SUCCESS — pak written. Verify:
for %%F in ("%PAK_OUT%") do echo   Size:          %%~zF bytes
for %%F in ("%PAK_OUT%") do echo   Last modified: %%~tF
echo.
echo You can now launch BG3 via BG3MM.
echo.
pause
endlocal
