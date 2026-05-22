#!/usr/bin/env python3
# Raw-string docstring (r""") so Windows-style backslash paths like
# "\Larian Studios\Baldur's Gate 3\Mods" inside the docstring don't trigger
# Python's "invalid escape sequence" SyntaxWarning (deprecation in 3.12+).
# Without this, PowerShell wraps the warning as a NativeCommandError and
# decorates it loudly in tee'd-pipeline runs, which makes the pipeline look
# like it crashed when it's actually fine.
r"""
AlanTooltipCompat — Phase 1.5 — Bulk pak unpacker

Takes a folder of BG3 .pak files (typically %LocalAppData%\Larian Studios\Baldur's Gate 3\Mods),
runs LSLib's divine.exe on each one to extract its contents, and writes the unpacked
data to an output directory. The existing sidecar.py can then run against that
output directory in folder mode.

Why a separate script: divine.exe is a Windows-only binary, slow per-pak invocation,
and extraction produces large temporary data. Splitting concerns lets us:
  - Cache unpacked data and skip re-unpacking unchanged paks
  - Run the unpacker once after installing new mods, then re-run the sidecar quickly
  - Keep the extraction logic isolated from RootTemplate parsing

Usage:
    python unpack_paks.py --paks-dir <path-to-Mods-folder>
                          --divine-exe <path-to-divine.exe>
                          --output-dir <path-to-unpacked-output>
                          [--filter Description,RootTemplates]    # extract only matching paths
                          [--force]                                # re-unpack even if cached
                          [--limit N]                              # only do first N (for testing)

Requirements: divine.exe from LSLib (ships with bg3-modders-multitool, also available
standalone from https://github.com/Norbyte/lslib).
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# The ONLY files sidecar.py reads from each extracted pak. We extract every
# pak to a TEMP dir, do any needed format conversion there, then copy only
# these files to the persistent target dir and delete the TEMP dir. Cuts
# per-pak persistent footprint from ~hundreds of MB to ~hundreds of KB.
#
# Pattern: Path.glob with leading "**/" so we tolerate paks whose extraction
# wraps content in an outer folder. Sidecar's own glob is the canonical
# definition: sidecar.py main() -> "*/Public/*/RootTemplates/*.lsf.lsx".
#
# v1.2: second glob added to keep per-UUID RootTemplate files (Class F + G
# mods). The first glob is kept for documentation clarity — it's a strict
# subset of the second; Path.glob deduplicates internally so no double work.
KEEP_GLOBS = [
    "**/Public/*/RootTemplates/_merged.lsf.lsx",
    "**/Public/*/RootTemplates/*.lsf.lsx",
]


def find_divine_exe(explicit_path: str | None) -> Path:
    """Locate divine.exe. Prefer explicit path, fall back to common locations."""
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"divine.exe not found at given path: {explicit_path}")

    # Common locations to search (search order matters — most common first).
    # The non-OneDrive location is tried first because OneDrive's Files-On-Demand
    # has been observed to dehydrate divine.exe even when "Always keep on this
    # device" is set, causing WinError 193 ("not a valid Win32 application")
    # when Python's subprocess tries to launch it.
    candidates = [
        # Non-OneDrive bundled location (PREFERRED — safe from OneDrive dehydration)
        Path(r"C:\bg3-sidecar-work\tools\divine.exe"),
        # Sidecar-bundled in OneDrive (legacy — may be dehydrated by OneDrive)
        Path(__file__).parent / "divine.exe",
        Path(__file__).parent / "tools" / "divine.exe",
        # bg3-modders-multitool install location guesses
        Path.home() / "AppData/Local/bg3-modders-multitool/Tools/Divine/Divine.exe",
        Path.home() / "AppData/Local/BG3ModdersMultitool/Divine.exe",
        # Documents-based installs
        Path.home() / "Documents/BG3 Mod Tools/Divine.exe",
    ]
    for c in candidates:
        if c.is_file():
            return c

    raise FileNotFoundError(
        "Could not locate divine.exe. Searched:\n  "
        + "\n  ".join(str(c) for c in candidates)
        + "\nUse --divine-exe <path> to specify."
    )


def md5_of_file(path: Path, chunk_size: int = 1 << 16) -> str:
    """Fast md5 of a file (for change detection)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _convert_lsf_in_dir(dir_path: Path, divine_exe: Path) -> int:
    """Convert every .lsf in dir_path (under any RootTemplates/) to .lsf.lsx (best effort).

    v1.2: was '_merged.lsf' literal; now matches ALL .lsf files so per-UUID
    binary RootTemplate files (Class F mods like VHLarmrs, obsc_midnight_sparkle)
    get converted too. Filename pattern is broadened to '*.lsf' but the parent
    directory must still be 'RootTemplates' to avoid converting unrelated .lsf
    files elsewhere in a pak (Generated/, Levels/, etc.).
    """
    converted = 0
    for lsf in dir_path.rglob("*.lsf"):
        # Restrict to files directly under a RootTemplates/ directory.
        # Avoids picking up .lsf files in unrelated subsystems (Levels, Generated, etc.).
        if lsf.parent.name != "RootTemplates":
            continue
        lsx = lsf.with_suffix(".lsf.lsx")
        if lsx.is_file():
            continue
        try:
            proc = subprocess.run(
                [
                    str(divine_exe),
                    "-g", "bg3",
                    "-a", "convert-resource",
                    "-s", str(lsf),
                    "-d", str(lsx),
                    "-l", "error",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                converted += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # best-effort; missing .lsx -> sidecar just won't find items
    return converted


def extract_one_pak(pak_path: Path, output_dir: Path, divine_exe: Path,
                    force: bool = False, verbose: bool = False) -> tuple[bool, str]:
    """
    Extract a single .pak file, keep only the files sidecar.py needs, discard
    the rest. Persistent footprint per pak: a few hundred KB at most.

    Workflow:
      1. Idempotency check via md5 marker in <output_dir>/<pak_stem>/ — return
         "cached" if the marker matches the current pak's md5.
      2. Extract the full pak into a TEMP directory.
      3. Convert any .lsf under any RootTemplates/ -> .lsf.lsx inside TEMP
         (covers both Larian's _merged.lsf and per-UUID <uuid>.lsf — the
         latter is needed for Class F mods like VHLarmrs).
      4. Copy only files matching KEEP_GLOBS to <output_dir>/<pak_stem>/,
         preserving relative paths.
      5. Write the md5 marker. TEMP dir auto-deletes when the context exits.

    Returns (success, message). Success messages:
      "cached"            — cache marker matches; no work done
      "extracted (kept N)" — N files persisted to the target dir
    """
    pak_stem = pak_path.stem
    target_dir = output_dir / pak_stem
    # v1.2: marker filename bumped from ".extracted_md5" to ".extracted_md5_v2".
    # v1.1 extractions kept ONLY _merged.lsf.lsx; v1.2 widened KEEP_GLOBS to
    # also keep per-UUID *.lsf.lsx (Class F + G mods). Re-using the v1.1 marker
    # would let unpack_paks.py declare those mods "cached (no work)" even though
    # the cached folder is missing the per-UUID files v1.2's sidecar.py expects.
    # Bumping the marker name forces a one-time re-extraction on v1.2 first run,
    # after which the v2 marker steady-states normally. (slim_existing.py keeps
    # both marker names so it doesn't wipe either one from co-existing trees.)
    cache_marker = target_dir / ".extracted_md5_v2"

    # Idempotency check
    current_md5 = md5_of_file(pak_path)
    if not force and cache_marker.is_file():
        try:
            if cache_marker.read_text().strip() == current_md5:
                return (True, "cached")
        except Exception:
            pass

    # Clean target dir (we always start with an empty persistent dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Use a TEMP dir for the bulk extraction so it never lives on persistent
    # disk longer than needed. TemporaryDirectory cleans up on context exit
    # even if exceptions are raised inside.
    with tempfile.TemporaryDirectory(prefix="atc_unpack_") as tmpdir_str:
        tmp_path = Path(tmpdir_str)

        cmd = [
            str(divine_exe),
            "-g", "bg3",
            "-a", "extract-package",
            "-s", str(pak_path),
            "-d", str(tmp_path),
            "-l", "error",
        ]
        # 1800s (30 min) ceiling. Previous 600s value worked early on but on
        # 2026-05-21 (post-v2 cache-marker bump that forced re-extraction),
        # Game.pak AND Gustav.pak both timed out at 600s on the maintainer's
        # machine — likely due to a combination of multi-GB pak size, disk
        # contention, and divine.exe's per-pak unpack cost. 1800s gives 3x the
        # margin and is still effectively unlimited for small mod paks (which
        # finish in seconds and exit immediately). If 1800s is also insufficient,
        # bump further; there is no downside for the fast path.
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            return (False, "divine timeout (>1800s)")
        except FileNotFoundError:
            return (False, f"divine.exe not executable: {divine_exe}")

        if proc.returncode != 0:
            err_short = (proc.stderr or proc.stdout or "")[:200]
            return (False, f"divine exit {proc.returncode}: {err_short}")

        # Convert .lsf -> .lsf.lsx inside TEMP (the .lsx is the wanted file).
        # Some mod authors ship .lsx directly so this is a no-op then. As of
        # v1.2 this covers per-UUID <uuid>.lsf files too, not just _merged.lsf.
        _convert_lsf_in_dir(tmp_path, divine_exe)

        # Copy only the files we keep, preserving relative paths.
        kept = 0
        for pattern in KEEP_GLOBS:
            for src in tmp_path.glob(pattern):
                if not src.is_file():
                    continue
                rel = src.relative_to(tmp_path)
                dst = target_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                kept += 1
    # tmp_path auto-deleted here

    # Mark as extracted even if kept == 0, so we don't re-do the work next run.
    cache_marker.write_text(current_md5)
    return (True, f"extracted (kept {kept})")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk-unpack BG3 .pak files for sidecar consumption."
    )
    parser.add_argument(
        "--paks-dir", "-p", required=True,
        help="Folder containing .pak files (typically the BG3 Mods folder)."
    )
    parser.add_argument(
        "--output-dir", "-o", required=True,
        help="Output folder for unpacked mod content."
    )
    parser.add_argument(
        "--divine-exe", "-d", default=None,
        help="Path to divine.exe (LSLib). If omitted, search common locations."
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Re-unpack everything even if cached."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only process first N paks (for testing)."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose per-pak output."
    )
    args = parser.parse_args()

    paks_dir = Path(args.paks_dir)
    output_dir = Path(args.output_dir)
    if not paks_dir.is_dir():
        print(f"ERROR: paks directory not found: {paks_dir}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    # Locate divine.exe
    try:
        divine_exe = find_divine_exe(args.divine_exe)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"divine.exe: {divine_exe}")

    # Find paks
    paks = sorted(paks_dir.glob("*.pak"))
    if args.limit:
        paks = paks[:args.limit]
    print(f"Found {len(paks)} .pak file(s) in {paks_dir}.")
    print(f"Output: {output_dir}\n")

    if not paks:
        return 0

    # Process each
    t0 = time.time()
    extracted = 0
    cached = 0
    failed = 0

    for i, pak in enumerate(paks, 1):
        ok, msg = extract_one_pak(pak, output_dir, divine_exe,
                                  force=args.force, verbose=args.verbose)
        if not ok:
            failed += 1
            print(f"  [{i}/{len(paks)}] FAIL  {pak.name}: {msg}")
            continue
        if msg == "cached":
            cached += 1
            if args.verbose:
                print(f"  [{i}/{len(paks)}] cached {pak.name}")
            continue
        extracted += 1
        if args.verbose:
            print(f"  [{i}/{len(paks)}] {msg:24s} {pak.name}")

        # Progress beacon every 50 paks
        if i % 50 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  ... {i}/{len(paks)} done "
                  f"({rate:.1f} pak/s, ext={extracted}, cached={cached}, fail={failed})")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Processed {len(paks)} paks in {elapsed:.1f}s")
    print(f"  extracted (this run): {extracted}")
    print(f"  cached (no work):     {cached}")
    print(f"  failed:               {failed}")
    print(f"\nOutput is in: {output_dir}")
    print(f"Next step: run sidecar.py --mods-dir {output_dir} --output-dir <out>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
