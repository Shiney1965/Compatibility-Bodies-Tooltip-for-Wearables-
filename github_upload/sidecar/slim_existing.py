#!/usr/bin/env python3
"""
AlanTooltipCompat — Slim an existing unpacked-paks directory.

Walks a directory that was extracted by an older version of unpack_paks.py
(when it kept the entire pak contents) and prunes every file except the
ones sidecar.py actually reads. Reclaims the bulk of the disk usage from
the original ~140 MB/pak extraction down to a few hundred KB/pak.

Files KEPT under each <pak_stem>/ subfolder:
  - Public/*/RootTemplates/*.lsf.lsx           (every RootTemplate XML —
    covers both Larian's _merged.lsf.lsx and per-UUID <uuid>.lsf.lsx files;
    the latter are how Class F + G mods like VHLarmrs, Luminiari Nox, etc.
    ship their RootTemplates. v1.2 sidecar.py reads both forms.)
  - .extracted_md5 / .extracted_md5_v2          (idempotency markers;
    v1 is pre-v1.2, v2 is v1.2+. Both kept so a mixed tree isn't disturbed.)

Everything else under each <pak_stem>/ is removed.

Usage (dry-run by default — nothing is deleted until you pass --apply):
    python slim_existing.py --unpacked-dir C:\\bg3-sidecar-work\\unpacked
    python slim_existing.py --unpacked-dir C:\\bg3-sidecar-work\\unpacked --apply

Run with --verbose to see per-pak counts and sizes.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path


# Mirror unpack_paks.KEEP_GLOBS exactly. If you add a new file to keep there,
# add it here too or this script will delete it next time you run --apply.
# v1.2: widened to *.lsf.lsx to preserve per-UUID RootTemplate files (Class
# F + G mods). The first glob is a strict subset of the second; kept for
# documentation clarity. Path.glob deduplicates internally.
KEEP_GLOBS = [
    "Public/*/RootTemplates/_merged.lsf.lsx",
    "Public/*/RootTemplates/*.lsf.lsx",
]
KEEP_FILES = {
    ".extracted_md5",       # v1.1 idempotency marker (pre-v1.2).
    ".extracted_md5_v2",    # v1.2+ idempotency marker. Both kept so a mixed
                            # tree isn't disturbed. Without these, unpack_paks
                            # would re-extract every pak on next run.
}


def collect_kept_paths(pak_dir: Path) -> set[Path]:
    """Return the absolute paths of every file we want to keep under pak_dir."""
    kept = set()
    # Glob-matched files
    for pattern in KEEP_GLOBS:
        for p in pak_dir.glob(pattern):
            if p.is_file():
                kept.add(p.resolve())
    # Top-level marker files
    for name in KEEP_FILES:
        p = pak_dir / name
        if p.is_file():
            kept.add(p.resolve())
    return kept


def slim_one_pak(pak_dir: Path, apply_changes: bool,
                 verbose: bool) -> tuple[int, int, int, int]:
    """
    Prune one pak's extraction folder.

    Returns (files_removed, bytes_freed, files_kept, bytes_kept).
    When apply_changes is False, files_removed and bytes_freed represent
    the planned deletions but nothing actually gets deleted.
    """
    kept_paths = collect_kept_paths(pak_dir)

    files_removed = 0
    bytes_freed = 0
    files_kept = len(kept_paths)
    bytes_kept = sum(p.stat().st_size for p in kept_paths if p.is_file())

    # Walk every file under pak_dir; if it's not in kept_paths, remove it.
    for p in pak_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.resolve() in kept_paths:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        files_removed += 1
        bytes_freed += size
        if apply_changes:
            try:
                p.unlink()
            except OSError as e:
                if verbose:
                    print(f"      unlink failed: {p}: {e}", file=sys.stderr)

    # Clean up any directories that are now empty (best-effort). Walk bottom-up.
    if apply_changes:
        for d in sorted(
            (p for p in pak_dir.rglob("*") if p.is_dir()),
            key=lambda x: len(x.parts),
            reverse=True,
        ):
            try:
                next(d.iterdir())
            except StopIteration:
                try:
                    d.rmdir()
                except OSError:
                    pass
            except OSError:
                pass

    return (files_removed, bytes_freed, files_kept, bytes_kept)


def fmt_bytes(n: int) -> str:
    """Human-readable byte count."""
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    i = 0
    while f >= 1024 and i < len(units) - 1:
        f /= 1024
        i += 1
    return f"{f:.1f} {units[i]}"


def main():
    parser = argparse.ArgumentParser(
        description="Prune an existing unpacked-paks directory down to "
                    "just the files sidecar.py needs."
    )
    parser.add_argument(
        "--unpacked-dir", "-u", required=True,
        help="The directory containing one subfolder per .pak (e.g. "
             r"C:\bg3-sidecar-work\unpacked)."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually delete the files. Without this flag, runs in dry-run "
             "mode and only reports what WOULD be deleted."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-pak summaries."
    )
    args = parser.parse_args()

    root = Path(args.unpacked_dir)
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 1

    mode = "APPLY (will delete files)" if args.apply else "DRY-RUN (no changes)"
    print(f"slim_existing.py — {mode}")
    print(f"Root: {root}\n")

    pak_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    print(f"Found {len(pak_dirs)} pak subfolder(s).\n")
    if not pak_dirs:
        return 0

    t0 = time.time()
    total_removed = 0
    total_freed = 0
    total_kept = 0
    total_kept_bytes = 0

    for i, pak_dir in enumerate(pak_dirs, 1):
        rem, freed, kept, kept_b = slim_one_pak(pak_dir, args.apply, args.verbose)
        total_removed += rem
        total_freed += freed
        total_kept += kept
        total_kept_bytes += kept_b

        if args.verbose:
            print(f"  [{i}/{len(pak_dirs)}] {pak_dir.name}: "
                  f"keep={kept} ({fmt_bytes(kept_b)}), "
                  f"remove={rem} ({fmt_bytes(freed)})")
        elif i % 100 == 0:
            print(f"  ... {i}/{len(pak_dirs)} paks scanned, "
                  f"removed-so-far={fmt_bytes(total_freed)}")

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"  Files kept:      {total_kept:>10,}   ({fmt_bytes(total_kept_bytes)})")
    print(f"  Files removed:   {total_removed:>10,}   ({fmt_bytes(total_freed)})")
    if not args.apply:
        print()
        print("This was a DRY RUN. No files were deleted.")
        print("Re-run with --apply to actually free the disk space.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
