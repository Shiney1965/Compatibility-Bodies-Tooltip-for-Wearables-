# AlanTooltipCompat — Sidecar (Phase 1.5)

Two Python utilities that together produce the `compat_cache.json` consumed by the BG3SE Lua runtime.

## Two-step workflow

```
+----------------+      +----------------+      +----------------+
| .pak files in  |      | unpacked mod   |      | compat_cache   |
| BG3 Mods folder|      | folders        |      | .json + .loca  |
|                | ---> |                | ---> |                |
|                |  (1) |                |  (2) |                |
| ~1300 paks     |      |                |      | (mod consumes  |
|                |      |                |      |  this)         |
+----------------+      +----------------+      +----------------+
       ^                       ^                       ^
       |                       |                       |
   1300 .pak              divine.exe-              JSON + loca for
   files installed        extracted folder         the BG3SE Lua
```

**Step 1 — `unpack_paks.py`:** Bulk-unpack `.pak` files via LSLib's `divine.exe`. Run this once after installing or removing mods. Idempotent — already-extracted paks are skipped on re-run (cached by md5).

**Step 2 — `sidecar.py`:** Walk the unpacked folders, extract EquipmentRace GUIDs and Description handles from RootTemplates, write `compat_cache.json` for the mod's runtime.


## One-click usage (NEW — recommended)

After Step 0 (locate divine.exe) below, you can run the entire pipeline by **double-clicking `run_all.bat`** in this folder. It will:

1. Auto-detect your BG3 Mods folder (`%LocalAppData%\Larian Studios\Baldur's Gate 3\Mods`)
2. Unpack all .pak files (idempotent — skips already-unpacked paks)
3. Run the sidecar to produce compat_cache.json
4. **Copy the cache directly to** `%LocalAppData%\Larian Studios\Baldur's Gate 3\Script Extender\AlanTooltipCompat\compat_cache.json` (creates the folder if missing)
5. Hold the console window open so you can read the output

After it finishes, launch BG3 — no manual file copying needed. Re-run any time you install or remove mods.

The manual two-step instructions below remain available for power users who want to customize paths.

## Quick start (full workflow)

### Step 0 — Locate `divine.exe`

`divine.exe` is part of LSLib. It ships bundled with **bg3-modders-multitool**. To find it:

1. Right-click your bg3-modders-multitool shortcut → **"Open file location"**.
2. Search the install folder for `divine.exe` (case-insensitive). Typical locations:
   - `<multitool_install>\divine.exe`
   - `<multitool_install>\Tools\Divine\Divine.exe`
   - `%LocalAppData%\BG3ModdersMultitool\divine.exe`

Once found, either:
- Copy `divine.exe` into this `AlanTooltipCompat_Sidecar` folder, **or**
- Note its full path and pass it via `--divine-exe <path>` in the commands below.

### Step 1 — Unpack your Mods folder

```bash
python unpack_paks.py ^
  --paks-dir "%LocalAppData%\Larian Studios\Baldur's Gate 3\Mods" ^
  --output-dir "C:\bg3-sidecar-work\unpacked"
```

For a first test, add `--limit 20 --verbose` to only process 20 paks (instead of all 1,327) so you can sanity-check the workflow before committing to a full run.

This step takes a while — `divine.exe` is invoked once per pak. Expect ~1–2 paks/second, so a full 1,327-mod run takes maybe 10–20 minutes. Idempotent: re-runs only process new/changed paks.

### Step 2 — Run the sidecar

```bash
python sidecar.py ^
  --mods-dir "C:\bg3-sidecar-work\unpacked" ^
  --output-dir "C:\bg3-sidecar-work\output"
```

Produces `compat_cache.json` and `AlanTooltipCompat.loca.xml` in the output directory. The loca.xml is unused in v3 architecture but harmless.

### Step 3 — Install the cache for the mod

Copy `compat_cache.json` from the output folder to:

```
%LocalAppData%\Larian Studios\Baldur's Gate 3\Script Extender\AlanTooltipCompat\compat_cache.json
```

(Create the `AlanTooltipCompat` subfolder if it doesn't exist.)

Re-launch BG3. Done.

## File-by-file

| File | Purpose |
|---|---|
| `sidecar.py` | Walks unpacked mod folders, parses RootTemplates, writes compat_cache.json + loca.xml |
| `unpack_paks.py` | Calls `divine.exe` to extract `.pak` files into unpacked mod folders. Idempotent. |
| `output/compat_cache.json` | Schema v3 — keyed by template UUID, contains description_handle + compat_text per item |
| `output/AlanTooltipCompat.loca.xml` | Synthetic loca handles (unused in v3, kept for compat with v2 systems if needed) |

## Phase 1.5 status

Working as of 2026-05-18. Bulk-unpack is implemented; full-mod-list scale test is the next step Alan plans to run.

## Future improvements (post-v1)

- **PyInstaller `.exe` distribution** — bundle Python + dependencies into a single `.exe`, no Python install needed for end-users
- **Bundled divine.exe** — ship `divine.exe` in the distribution so users don't have to find it
- **Auto-detect paths** — auto-find the BG3 Mods folder and Script Extender folder rather than requiring CLI args
- **Watch mode** — monitor the Mods folder for changes and auto-regenerate the cache
- **Direct .pak reading without divine.exe** — implement the pak format in pure Python (high effort)
