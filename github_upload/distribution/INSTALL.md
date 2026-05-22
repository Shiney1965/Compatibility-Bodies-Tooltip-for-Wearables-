# Install — Compatible Bodies Tooltip

Two paths: **basic** (vanilla armor only, takes 60 seconds) or **full** (vanilla + your modded armor, requires Python and a one-time sidecar run of about 10-20 minutes).

## Prerequisites

1. **Baldur's Gate 3** installed, Patch 8 or later.
2. **BG3 Script Extender (BG3SE)** installed and working. If you don't have it, get it from <https://bg3.community/> — installation guide is on their site.
3. **Recommended:** A mod manager like BG3 Mod Manager (BG3MM). Not strictly required.

## Where to extract this download

Extract `CompatibleBodiesTooltip-1.2.0.zip` to anywhere convenient — Documents, a Mods folder you keep, etc. **Avoid extracting directly to a OneDrive- or Dropbox-synced folder.** Cloud sync can dehydrate the bundled `divine.exe` and break the sidecar. If your Downloads folder is auto-synced, move the extracted folder elsewhere first. A path like `C:\Mods\CompatibleBodiesTooltip-1.2.0\` is safe.

## Basic install — vanilla armor only (1 minute)

This gets you Compatible Bodies tooltips on Larian's base-game armor. Your installed armor mods are NOT covered by this path.

1. Open File Explorer and paste this into the address bar:
   ```
   %LocalAppData%\Larian Studios\Baldur's Gate 3\Mods
   ```
   Press Enter. That's your BG3 Mods folder.
2. Copy `CompatibleBodiesTooltip.pak` from this download into that folder.
3. If you use BG3 Mod Manager, refresh its mod list and ensure "Compatible Bodies Tooltip" is in your active mods list.
4. Launch BG3. Hover any vanilla armor (e.g., Padded Armour +1, Adamantine Scale Mail, Luminous Armour, or any chain-mail variant) — you should see "Compatible Bodies: …" appended to the description.

Done if you only care about vanilla armor.

## Full install — vanilla + your modded armor (10-20 min first time, ~1 min on re-runs)

Adds Compatible Bodies tooltips for your installed armor mods. Requires Python and a one-time sidecar run.

### One-time setup

1. **Install Python 3.10 or newer.** Get it from <https://www.python.org/downloads/>. During installation, make sure **"Add Python to PATH"** is checked. Verify by opening a Command Prompt and running `python --version`.

2. **Install the `lxml` package** (the sidecar uses it to parse BG3 data files). Open Command Prompt and run:
   ```
   pip install lxml
   ```

3. **divine.exe and its DLL siblings are bundled** inside `sidecar/tools/`. You should see four files there: `Divine.exe`, `Divine.dll`, `Divine.dll.config`, and `Divine.runtimeconfig.json`. All four are needed — Divine.exe is just a launcher; the actual code is in Divine.dll. The sidecar will find them automatically.

4. **Check for the .NET runtime.** Divine.exe is a .NET application and needs the .NET runtime installed. Most Windows 10/11 machines already have it, but a clean install may not. To check, open Command Prompt and run:
   ```
   dotnet --list-runtimes
   ```
   - If you see one or more `Microsoft.NETCore.App` entries, you're good.
   - If you see "dotnet is not recognized" or no `NETCore.App` entries, install the latest .NET 8 Desktop Runtime from <https://dotnet.microsoft.com/download> (pick "Run desktop apps" → ".NET Desktop Runtime").

### Run the sidecar

1. Open the `sidecar` subfolder inside this download.
2. **Double-click `refresh_cache.bat`.** A Command Prompt window opens and shows progress. First-time run takes 10-20 minutes (most of that is unpacking your installed armor mods' paks). Safe to leave running in the background.
3. When you see `DONE` at the end, close the window.
4. The sidecar wrote a `compat_cache.json` file to your Script Extender folder. (You don't need to do anything with it — Compatible Bodies Tooltip reads it on next game launch.)
5. Launch BG3. Hover an armor item from one of your installed mods — you should see "Compatible Bodies: …" appended.

### Refreshing after adding new mods

Just **double-click `refresh_cache.bat` again**. The sidecar only does work for paks it hasn't seen before, so re-runs are fast (about a minute, typically).

## Troubleshooting

### "Compatible Bodies" doesn't show up on ANY tooltip

- Confirm BG3 Script Extender is loaded. There should be a tray icon when BG3 is running with Script Extender active, and a Script Extender console window.
- Open the Script Extender console window. Look for lines starting with `[AlanTooltipCompat]` (the mod's internal log prefix). If they're absent, the mod isn't loading — verify the `.pak` is in your Mods folder.
- Confirm "Compatible Bodies Tooltip" is in your active load order (BG3MM or `modsettings.lsx`).

### "Compatible Bodies" shows up on vanilla items but not on my modded armor

- You haven't run the sidecar yet, or the sidecar's cache file isn't in the Script Extender folder.
- Open Command Prompt and run:
  ```
  dir "%LocalAppData%\Larian Studios\Baldur's Gate 3\Script Extender" /s /b | findstr compat_cache.json
  ```
  If nothing is listed, run `refresh_cache.bat` from the sidecar folder.

### Sidecar fails with "divine.exe not found" or `WinError 193`

- `WinError 193: %1 is not a valid Win32 application` usually means divine.exe was corrupted by OneDrive or Dropbox file-on-demand dehydration. Two fixes:
  - **Move the whole `CompatibleBodiesTooltip-1.1.0` folder out of any cloud-sync folder.** A path like `C:\Mods\CompatibleBodiesTooltip-1.1.0\` is safe.
  - **Or place a fresh copy of the 4 Divine files at `C:\bg3-sidecar-work\tools\`** (the sidecar checks there first). Get them from LSLib's release zip at <https://github.com/Norbyte/lslib/releases> — the four files inside `Packed\Tools\` (Divine.exe, Divine.dll, Divine.dll.config, Divine.runtimeconfig.json).

### Sidecar fails with "You must install or update .NET to run this application"

- divine.exe needs the .NET runtime. Install it from <https://dotnet.microsoft.com/download> (pick "Run desktop apps" → ".NET Desktop Runtime", latest .NET 8). After install, re-run `refresh_cache.bat`.

### Sidecar fails with `pip` or `lxml` errors

- Make sure Python is installed and on PATH (`python --version` should work from a fresh Command Prompt).
- Run `pip install lxml` again. If that fails, try `python -m pip install lxml`.

### A specific item still doesn't show Compatible Bodies info

- See "Known limitations" in `README.md`. Most common reasons: the mod uses a format that supplies replacement assets without its own item entries, or it's a base-game item without any description text in its template.

## Uninstalling

1. Delete `CompatibleBodiesTooltip.pak` from your BG3 Mods folder.
2. Optionally delete the sidecar's cache file by removing the `AlanTooltipCompat` subfolder from your Script Extender folder.
3. Optionally delete `C:\bg3-sidecar-work\` to remove the sidecar's working files.

All tooltip changes are runtime-only — uninstalling immediately reverts to original tooltip text on next BG3 launch. No save-game effects.
