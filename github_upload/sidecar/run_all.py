#!/usr/bin/env python3
"""
AlanTooltipCompat — One-click pipeline orchestrator

Runs the full workflow with zero CLI args:
  1. Auto-detect BG3 Mods folder and Script Extender folder
  2. Unpack all .pak files (idempotent — only new/changed paks)
  3. Run the sidecar to produce compat_cache.json
  4. Copy compat_cache.json to the Script Extender folder
     where the mod's BG3SE Lua will read it on next game launch

Run from inside the AlanTooltipCompat_Sidecar folder:
    python run_all.py
or double-click run_all.bat in Windows Explorer.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SIDECAR_DIR = Path(__file__).resolve().parent

# Default work paths live OUTSIDE OneDrive so the ~hundreds-of-MB extracted
# data never gets cloud-synced. Override either with env vars or by editing
# the two constants below.
#
#   ATC_WORK_DIR      = where temp/persistent unpack and sidecar output live
#   ATC_UNPACKED_DIR  = explicit unpack location (defaults to <WORK_DIR>/unpacked)
#   ATC_OUTPUT_DIR    = explicit sidecar-output location (defaults to <WORK_DIR>/output)
#
# Historical note: this used to default to <sidecar>/work/ inside the OneDrive
# folder. That caused ~187 GB of unpacked pak content to start syncing to the
# cloud — bad. Default is now C:\bg3-sidecar-work\ which matches the original
# prior extraction location used during development.
DEFAULT_WORK_DIR = Path(r"C:\bg3-sidecar-work")
WORK_DIR = Path(os.environ.get("ATC_WORK_DIR", str(DEFAULT_WORK_DIR)))
# Two separate unpack dirs so sidecar can be aimed at user-mods only OR
# vanilla only. We deliberately keep them isolated so a future end-user
# distribution can ship vanilla_cache.lua pre-baked and skip the vanilla unpack.
UNPACKED_DIR = Path(os.environ.get("ATC_UNPACKED_DIR", str(WORK_DIR / "unpacked")))
UNPACKED_VANILLA_DIR = Path(os.environ.get("ATC_UNPACKED_VANILLA_DIR", str(WORK_DIR / "unpacked_vanilla")))
OUTPUT_DIR = Path(os.environ.get("ATC_OUTPUT_DIR", str(WORK_DIR / "output")))

# Where the vanilla_cache.lua needs to be dropped so it gets packed into the
# distributed mod .pak. Calculated relative to this script's location
# (assumes the standard repo layout: <repo>/AlanTooltipCompat_Sidecar/run_all.py
# and <repo>/AlanTooltipCompat_Mod/Mods/AlanTooltipCompat_<UUID>/ScriptExtender/Lua).
DEFAULT_MOD_LUA_DIR = (SIDECAR_DIR.parent / "AlanTooltipCompat_Mod" / "Mods"
                       / "AlanTooltipCompat_a7c0ffee-7501-4f00-a17a-c00b08ec4377"
                       / "ScriptExtender" / "Lua")
MOD_LUA_DIR = Path(os.environ.get("ATC_MOD_LUA_DIR", str(DEFAULT_MOD_LUA_DIR)))

# Where automated cache backups land. Each pipeline run, BEFORE overwriting
# the live SE-folder compat_cache.json and mod-source vanilla_cache.lua, the
# existing (previous-run) copy is timestamp-renamed and saved here. This
# preserves the LAST KNOWN GOOD cache so a bad run can be reverted by hand.
# Override with ATC_BACKUP_DIR env var. Default is alongside the workspace
# folder so backups stay easy to find next to the rest of the project.
DEFAULT_BACKUP_DIR = SIDECAR_DIR.parent / "Cache Backups"
BACKUP_DIR = Path(os.environ.get("ATC_BACKUP_DIR", str(DEFAULT_BACKUP_DIR)))


def backup_cache(source: Path, label: str) -> None:
    """
    Back up `source` (the about-to-be-overwritten cache file) to BACKUP_DIR
    with a timestamp suffix. No-op if source doesn't exist (first run on a
    fresh machine). Best-effort — backup failure does NOT abort the pipeline,
    just prints a warning, since the new cache is still about to be written.
    """
    if not source.is_file():
        print(f"  [backup] no prior {label} to back up (first run?) — skipping")
        return
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        # Insert timestamp before the file's extension(s). Use .name so we
        # carry the FULL extension chain (handles compat_cache.json AND
        # vanilla_cache.lua without special-casing).
        stem = source.name.rsplit(".", 1)[0] if "." in source.name else source.name
        ext = source.name[len(stem):]  # ".json" / ".lua"
        backup_path = BACKUP_DIR / f"{stem}_{ts}{ext}"
        shutil.copy2(source, backup_path)
        print(f"  [backup] {source}")
        print(f"           -> {backup_path} ({backup_path.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"  [backup] WARNING: could not back up {label}: {e}")
        print(f"  [backup] continuing without backup — the new cache will still be written")


def detect_bg3_paths():
    """Return (mods_dir, se_dir) auto-detected from %LocalAppData%."""
    appdata = os.environ.get("LOCALAPPDATA")
    if not appdata:
        # fallback on non-Windows or unusual setups
        appdata = str(Path.home() / "AppData" / "Local")
    base = Path(appdata) / "Larian Studios" / "Baldur's Gate 3"
    return (base / "Mods", base / "Script Extender" / "AlanTooltipCompat")


def detect_bg3_install_data_dir():
    """
    Find the BG3 game install's Data folder. Contains vanilla paks
    (Gustav.pak, Shared.pak, etc.) needed for vanilla-item compat coverage.

    Search order:
      1. ATC_GAME_DATA_DIR env var (manual override)
      2. Steam default: C:\\Program Files (x86)\\Steam\\steamapps\\common\\Baldurs Gate 3\\Data
      3. Steam alt:     D:\\Steam\\... and other common drive letters
      4. GOG default:   C:\\GOG Games\\Baldur's Gate 3\\Data
      5. Windows %ProgramFiles%/%ProgramFiles(x86)%\\Larian Studios\\...

    Returns the Path of the Data folder, or None if not found.
    """
    env = os.environ.get("ATC_GAME_DATA_DIR")
    if env:
        p = Path(env)
        return p if p.is_dir() else None

    candidates = []
    # Steam — most common. Several Steam Library folder naming conventions
    # spotted in the wild: "SteamLibrary", "Steam Library" (with space),
    # "Steam", and various Program Files variants.
    for drive in ("C:", "D:", "E:", "F:"):
        candidates.append(Path(rf"{drive}\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Program Files\Steam\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\SteamLibrary\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Steam Library\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Steam\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Games\SteamLibrary\steamapps\common\Baldurs Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Games\Steam Library\steamapps\common\Baldurs Gate 3\Data"))
    # GOG
    for drive in ("C:", "D:", "E:", "F:"):
        candidates.append(Path(rf"{drive}\GOG Games\Baldur's Gate 3\Data"))
        candidates.append(Path(rf"{drive}\Games\Baldur's Gate 3\Data"))
    # Larian-direct
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates.append(Path(pf) / "Larian Studios" / "Baldur's Gate 3" / "Data")
    candidates.append(Path(pf86) / "Larian Studios" / "Baldur's Gate 3" / "Data")

    for c in candidates:
        if c.is_dir() and any(c.glob("*.pak")):
            return c
    return None


def banner(text):
    print()
    print("=" * 70)
    print("  " + text)
    print("=" * 70)


def run_subprocess(args, step_name):
    """Run a python subprocess; return its returncode.

    Inserts -u after the python interpreter argument so child stdout is
    unbuffered. Without this, when run_all.py is invoked via a pipe (e.g.
    tee'd by PowerShell into a log file), the child's print() output is
    block-buffered (~4 KB) and short cached runs never fill the buffer,
    so the log captures the child's invocation banner from the parent but
    none of the child's actual output. Added 2026-05-21 after the modsonly
    run produced a 2.8 KB log instead of the expected ~1 MB.

    If args[0] looks like a Python interpreter and -u isn't already present,
    splice it in. Skip the splice if -u is already there (idempotent) or
    if args[0] is something else (e.g. a Windows .exe other than python).
    """
    if (args
            and len(args) >= 2
            and isinstance(args[0], str)
            and "python" in args[0].lower()
            and "-u" not in args[1:3]):
        args = [args[0], "-u"] + list(args[1:])

    print(f"\n>>> {step_name}: {' '.join(str(a) for a in args)}\n")
    try:
        proc = subprocess.run(args, check=False)
        return proc.returncode
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C). Exiting.")
        return 130


def main():
    print()
    print("AlanTooltipCompat — One-click pipeline")
    print(f"Sidecar folder: {SIDECAR_DIR}")

    mods_dir, se_dir = detect_bg3_paths()
    game_data_dir = detect_bg3_install_data_dir()
    print(f"BG3 Mods folder:           {mods_dir}")
    print(f"BG3 game Data folder:      {game_data_dir or '(not found — vanilla_cache.lua will NOT be regenerated)'}")
    print(f"Unpack dir (user mods):    {UNPACKED_DIR}")
    print(f"Unpack dir (vanilla):      {UNPACKED_VANILLA_DIR}")
    print(f"Sidecar output dir:        {OUTPUT_DIR}")
    print(f"Mod Lua dir (vanilla bake):{MOD_LUA_DIR}")
    print(f"Script Extender target:    {se_dir}")
    print(f"Cache backup folder:       {BACKUP_DIR}")
    if str(UNPACKED_DIR).lower().startswith(str(Path.home()).lower() + os.sep + "onedrive"):
        print()
        print("WARNING: unpack dir appears to be inside OneDrive. Hundreds of GB")
        print("         of unpacked pak content will sync to the cloud. Override")
        print("         with: set ATC_WORK_DIR=C:\\bg3-sidecar-work")

    if not mods_dir.is_dir():
        print(f"\nERROR: BG3 Mods folder not found at:\n  {mods_dir}")
        print("If your BG3 install is in a non-standard location, edit run_all.py")
        print("to point at the correct path.")
        return 1

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    UNPACKED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    python = sys.executable  # use the SAME interpreter that's running this script

    # Total step count depends on whether vanilla generation runs.
    n_steps = 5 if game_data_dir else 3

    # -----------------------------------------------------------------
    # Step 1A — unpack user-installed mod paks
    # -----------------------------------------------------------------
    banner(f"STEP 1A / {n_steps} — Unpacking .pak files from user Mods folder (idempotent)")
    rc = run_subprocess(
        [
            python,
            str(SIDECAR_DIR / "unpack_paks.py"),
            "--paks-dir", str(mods_dir),
            "--output-dir", str(UNPACKED_DIR),
        ],
        "unpack_paks.py (user Mods)",
    )
    if rc != 0:
        print(f"\nERROR: unpack_paks.py (user Mods) exited with code {rc}. Stopping pipeline.")
        return rc

    # -----------------------------------------------------------------
    # Step 2A — sidecar pass over user mods -> compat_cache.json -> SE folder
    # -----------------------------------------------------------------
    banner(f"STEP 2A / {n_steps} — Generating user compat_cache.json")
    rc = run_subprocess(
        [
            python,
            str(SIDECAR_DIR / "sidecar.py"),
            "--mods-dir", str(UNPACKED_DIR),
            "--output-dir", str(OUTPUT_DIR),
            "--cache-name", "compat_cache.json",
        ],
        "sidecar.py (user)",
    )
    if rc != 0:
        print(f"\nERROR: sidecar.py (user) exited with code {rc}. Stopping pipeline.")
        return rc

    user_cache_file = OUTPUT_DIR / "compat_cache.json"
    if not user_cache_file.is_file():
        print(f"\nERROR: sidecar did not produce {user_cache_file}")
        return 2

    # -----------------------------------------------------------------
    # Step 3A — install user compat_cache.json into Script Extender folder
    # -----------------------------------------------------------------
    banner(f"STEP 3A / {n_steps} — Installing user cache to Script Extender folder")
    se_dir.mkdir(parents=True, exist_ok=True)
    se_target = se_dir / "compat_cache.json"
    # Back up the existing (about-to-be-overwritten) SE-folder compat_cache.json
    # to the workspace backup folder. Preserves last-known-good state.
    backup_cache(se_target, "user compat_cache.json")
    try:
        shutil.copy2(user_cache_file, se_target)
    except Exception as e:
        print(f"\nERROR: could not copy user cache to {se_target}: {e}")
        return 3
    print(f"  Copied {user_cache_file}")
    print(f"  ->     {se_target}")
    print(f"  ({se_target.stat().st_size / 1024:.1f} KB)")

    # -----------------------------------------------------------------
    # Maintainer-only: regenerate vanilla_cache.lua bundled inside the mod.
    # End-user distributions skip these steps (vanilla cache is pre-baked).
    # -----------------------------------------------------------------
    if game_data_dir is None:
        banner("Maintainer steps skipped — game Data folder not found")
        print("vanilla_cache.lua will NOT be regenerated. If this is the maintainer")
        print("machine, set ATC_GAME_DATA_DIR to your BG3 install Data folder, e.g.")
        print('     set ATC_GAME_DATA_DIR=D:\\Steam\\steamapps\\common\\Baldurs Gate 3\\Data')
    else:
        UNPACKED_VANILLA_DIR.mkdir(parents=True, exist_ok=True)

        # Step 1B — unpack base-game paks into the separate vanilla dir
        banner(f"STEP 1B / {n_steps} — Unpacking base-game .pak files (maintainer step)")
        rc = run_subprocess(
            [
                python,
                str(SIDECAR_DIR / "unpack_paks.py"),
                "--paks-dir", str(game_data_dir),
                "--output-dir", str(UNPACKED_VANILLA_DIR),
            ],
            "unpack_paks.py (game Data)",
        )
        if rc != 0:
            print(f"\nERROR: unpack_paks.py (game Data) exited with code {rc}. "
                  "Vanilla cache will NOT be updated this run.")
        else:
            # Step 2B — sidecar over vanilla unpacks -> vanilla_cache.lua
            banner(f"STEP 2B / {n_steps} — Generating vanilla_cache.lua (maintainer step)")
            rc = run_subprocess(
                [
                    python,
                    str(SIDECAR_DIR / "sidecar.py"),
                    "--mods-dir", str(UNPACKED_VANILLA_DIR),
                    "--output-dir", str(OUTPUT_DIR),
                    "--cache-name", "vanilla_cache.lua",
                    "--output-format", "lua",
                    "--skip-loca",
                ],
                "sidecar.py (vanilla)",
            )
            if rc != 0:
                print(f"\nERROR: sidecar.py (vanilla) exited with code {rc}. "
                      "vanilla_cache.lua may not be valid.")
            else:
                vanilla_cache_file = OUTPUT_DIR / "vanilla_cache.lua"
                if not vanilla_cache_file.is_file():
                    print(f"\nERROR: sidecar did not produce {vanilla_cache_file}")
                else:
                    # Step 3B — drop vanilla_cache.lua into the mod source so
                    # a subsequent re-pack bundles it inside the .pak.
                    print(f"  Copying vanilla cache into mod source for next re-pack...")
                    MOD_LUA_DIR.mkdir(parents=True, exist_ok=True)
                    mod_target = MOD_LUA_DIR / "vanilla_cache.lua"
                    # Back up the existing (about-to-be-overwritten) mod-source
                    # vanilla_cache.lua. Same pattern as Step 3A.
                    backup_cache(mod_target, "vanilla_cache.lua")
                    try:
                        shutil.copy2(vanilla_cache_file, mod_target)
                        print(f"  Copied {vanilla_cache_file}")
                        print(f"  ->     {mod_target}")
                        print(f"  ({mod_target.stat().st_size / 1024:.1f} KB)")
                        print()
                        print("  IMPORTANT: re-pack AlanTooltipCompat.pak now to ship the")
                        print("  new vanilla cache. The mod's BootstrapClient.lua will")
                        print("  Ext.Require this file at game start.")
                    except Exception as e:
                        print(f"\nERROR: could not copy vanilla cache: {e}")

    # -----------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------
    banner("DONE")
    print()
    print("Launch BG3 (via BG3MM if you use it). The AlanTooltipCompat mod will")
    print("pick up the new cache(s) at game start. Hover an armor item to see the")
    print("Compatible Bodies line appended to its tooltip.")
    if game_data_dir is not None:
        print()
        print("Reminder: if vanilla_cache.lua was regenerated above, re-pack the")
        print("AlanTooltipCompat.pak before relaunching BG3.")
    print()
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 130
    # When run via .bat double-click, hold the console open so the user can read
    if os.environ.get("ALAN_TOOLTIP_COMPAT_PAUSE", "0") == "1":
        input("\nPress Enter to close this window...")
    sys.exit(rc)
