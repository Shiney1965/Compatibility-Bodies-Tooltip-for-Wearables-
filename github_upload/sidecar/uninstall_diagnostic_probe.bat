@echo off
REM ============================================================================
REM uninstall_diagnostic_probe.bat — convenience wrapper
REM
REM Double-clickable equivalent of running
REM     install_diagnostic_probe.bat --uninstall
REM from a Command Prompt. Restores BootstrapClient.lua from the backup,
REM leaves DiagnosticProbe.lua in the mod source (per no-delete rule), and
REM re-packs the mod via build_pak.bat.
REM
REM Use this BEFORE shipping a public release of the mod, to ensure the
REM diagnostic probe code isn't loaded by end users' mods.
REM ============================================================================

cd /d "%~dp0"
call install_diagnostic_probe.bat --uninstall
