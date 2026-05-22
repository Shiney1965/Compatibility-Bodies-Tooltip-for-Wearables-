@echo off
REM ============================================================
REM  v1.2 parallel verification — run sidecar.py directly against
REM  the manually-extracted mods tree in the workspace, bypassing
REM  the unpack_paks.py cache entirely.
REM
REM  Purpose: confirm the v1.2 sidecar.py glob change picks up
REM  per-UUID *.lsf.lsx files from real Class F + Class G mods
REM  (VHLarmrs, Luminiari Nox, ClaviculaNox, MenzoMenswear,
REM  OBSC Midnight Sparkle, r_CrissCross) even while the main
REM  cache marker bump is rolling out to %LocalAppData%\...\Mods\.
REM
REM  Output goes to a SIDE folder so it does NOT touch the live
REM  C:\bg3-sidecar-work\output\compat_cache.json that the game
REM  is currently reading.
REM ============================================================

setlocal

set "SIDECAR_DIR=%~dp0"
set "PY=C:\Users\Alan\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "MODS_DIR=C:\Users\Alan\OneDrive\Claude Projects\BG3 Mods\BG3 Extracted Files\Extracted Mods"
set "OUT_DIR=C:\bg3-sidecar-work\output_v12_test"
set "LOG_FILE=C:\Users\Alan\OneDrive\Claude Projects\BG3 Mods\v1.2 Parallel Sidecar Test Log.txt"

echo.
echo ============================================================
echo  v1.2 Parallel Sidecar Test
echo ============================================================
echo  Python:      %PY%
echo  Sidecar:     %SIDECAR_DIR%sidecar.py
echo  Mods dir:    %MODS_DIR%
echo  Output dir:  %OUT_DIR%
echo  Log file:    %LOG_FILE%
echo ============================================================
echo.

if not exist "%PY%" (
    echo ERROR: Python not found at %PY%
    echo Edit this .bat to point at your python.exe.
    pause
    exit /b 1
)

if not exist "%MODS_DIR%" (
    echo ERROR: extracted mods directory not found:
    echo   %MODS_DIR%
    pause
    exit /b 1
)

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

REM Run sidecar.py and tee output to both console and log file.
REM Using PowerShell Tee-Object so we get both streams.
powershell -NoProfile -Command ^
  "& '%PY%' '%SIDECAR_DIR%sidecar.py' --mods-dir '%MODS_DIR%' --output-dir '%OUT_DIR%' --cache-name compat_cache_v12_test.json 2>&1 | Tee-Object -FilePath '%LOG_FILE%'"

echo.
echo ============================================================
echo  Done. Outputs:
echo    %OUT_DIR%\compat_cache_v12_test.json
echo    %LOG_FILE%
echo ============================================================
pause
endlocal
