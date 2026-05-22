# Compatible Bodies Tooltip

Adds a **Compatible Bodies** line to armor and clothing tooltips in Baldur's Gate 3. When you hover or examine a wearable item, a new line shows which races and body shapes that item is designed to fit.

```
Padded Armour +2
Rare Light Armour
Armour Class 13
...

A standard gambeson of quilted cloth. Good for catching blows,
but almost unbearably sweaty.

Compatible Bodies: Human Male, Human Female, Human Strong Male,
Human Strong Female, Githyanki Male, Githyanki Female,
Dwarf Male, Dwarf Female, Halfling Male, Halfling Female,
Gnome Male, Gnome Female, Dragonborn Male, Dragonborn Female
```

No more guessing whether a mod author shipped the visuals for your character's body type. The mod ships with a pre-baked cache of base-game armor, and an included one-click sidecar utility scans your installed armor mods to extend coverage to your modded items.

## Features

- Works on **base-game armor** (Adamantine, Bhaalist, Padded +1/+2, Splint, Plate, Chain Mail, Chain Shirt, Hide, Leather, robes, etc.) out of the box — no setup needed beyond installing the .pak.
- Works on **modded armor** after a one-time sidecar run that scans your Mods folder.
- Lists all 24 BG3 EquipmentRace body types: Human (Male/Female and Strong variants), Elf/Drow, Half-Elf, Tiefling (including Strong variants and Karlach), Githyanki, Dwarf, Halfling, Gnome, Dragonborn, Half-Orc.
- Compatible with common tooltip-extending mods — the Compatible Bodies line is appended to the existing description rather than replacing it, so other tooltip mods continue to render their additions normally.
- Refreshes automatically whenever you add or remove armor mods (re-run the included sidecar).
- Zero gameplay impact. Cosmetic / informational only.

**Scope.** In testing with over 4,900 modded wearable items, the mod covered the vast majority of the items that were not coded as assets only. Vanilla armor and clothing coverage is also the vast majority for items with a description. Additional mod-format coverage is planned for the next update.

## Requirements

- **Baldur's Gate 3**, Patch 8 or later.
- **BG3 Script Extender (BG3SE)** version 21 or later. Required.
- **Python 3.10+** on Windows — *only* if you want compat info for your modded armor. Vanilla armor works without Python.
- **.NET Runtime** (for the sidecar's pak-extraction tool). Most Windows 10/11 machines already have it; clean installs may need .NET 8 Desktop Runtime from <https://dotnet.microsoft.com/download>.

## Installation

See `INSTALL.md` for step-by-step instructions.

## How it works (brief technical overview)

The mod ships with a pre-baked cache of base-game armor items, bundled inside the `.pak` file. At game start, a Script Extender Lua script reads that cache plus an optional user-generated cache, and appends the Compatible Bodies line to each cached item's description text.

To cover armor mods you've installed, run the included sidecar utility. It unpacks every `.pak` in your BG3 Mods folder (briefly, into a TEMP directory it cleans up), reads the EquipmentRace data from each item's data files, and writes the result to a cache file in your Script Extender folder. The next BG3 launch picks it up.

The mod does not modify the game's save data and makes no permanent changes — all text additions are applied at runtime on each launch.

## Known limitations

- **Some armor mods aren't covered.** The most common cause is mods that supply replacement meshes and textures for items defined elsewhere — these mods don't expose their own item entries in the format the scanner reads. The scanner can only see items that are present as item-template definitions inside the mod's data files. If a piece of armor doesn't show a Compatible Bodies line in its tooltip, the source mod likely uses one of these formats.
- **Some unusual base-game items show no Compatible Bodies line.** A small number of base-game wearables (most visibly Ring Mail Armour and a few similar items) have no description text field at all in their template — there's no place for the Compatible Bodies line to be appended. These items also don't show a regular description in their normal tooltip.
- **First-time sidecar run takes 15-30 minutes** as it extracts every pak in your Mods folder. Subsequent runs are fast (about a minute) because results are cached and only new or changed paks need processing.
- **Additional mod-format coverage is planned** for the next update.

## Compatibility with other tooltip mods

The mod has been tested alongside common tooltip-enhancement mods. The Compatible Bodies line is added by appending text to each item's localization handle, which works alongside other tooltip mods (the additional line shows up regardless of which tooltip mod is rendering the tooltip). If you see unexpected interactions — for example, the Compatible Bodies line appearing twice, or not appearing at all on items where you'd expect it — please report which tooltip mods you have installed.

## FAQ

**Q: What is BG3 Script Extender?**
A: A required dependency. Install it from <https://bg3.community/> or NexusMods. The mod won't do anything without Script Extender loaded.

**Q: Does this work with BetterTooltips, EnhancedWorldTooltips, or similar?**
A: Yes. The Compatible Bodies line is appended to each item's description text directly, so it shows up regardless of which tooltip mod is rendering the tooltip.

**Q: What happens if I uninstall the mod?**
A: Tooltips return to their original text on next BG3 launch. The mod doesn't make permanent changes to your save data — all text modifications are applied at runtime.

**Q: Do I need to run the sidecar?**
A: Only if you want Compatible Bodies info on your *modded* armor. Vanilla armor works automatically. If you only use a few armor mods or don't need the info on them, you can skip the sidecar entirely.

**Q: How often do I need to re-run the sidecar?**
A: After installing new armor mods or removing existing ones. The cache file remembers what it scanned last time, so re-runs only do work for new or changed paks.

**Q: Why does the sidecar need divine.exe?**
A: BG3's `.pak` files are a custom archive format. LSLib's `divine.exe` is the canonical tool for reading them. A copy is bundled in the `sidecar/tools/` folder under LSLib's MIT license (see `LICENSE-THIRD-PARTY.md`).

**Q: Will this slow down my game?**
A: No. All work happens at game-start in under a second. Once the cache is loaded, tooltip rendering is unchanged.

**Q: Why is this specific item not showing the Compatible Bodies line?**
A: See "Known limitations" above. The most common reasons are mods that supply replacement assets without their own item entries, or unusual items without a description field anywhere in their template.

**Q: Why "Compatible Bodies" instead of "Body Types"?**
A: BG3's internal terminology is `EquipmentRace`, which combines body shape and race in a single category. "Compatible Bodies" reads more naturally than "compatible equipment-races."

## Credits

- **Author:** Serpentine (NexusMods: SerpentineShel)
- **BG3 Script Extender:** [Norbyte](https://github.com/Norbyte/bg3se) — without which none of this would be possible
- **LSLib / divine.exe:** [Norbyte](https://github.com/Norbyte/lslib), bundled under MIT license
- **Testing and feedback:** the BG3 modding community

## License

MIT. See `LICENSE`.

## Reporting issues

Drop a comment on the NexusMods listing or open an issue (if a GitHub repo is published). When reporting, please include:

- BG3 version and Script Extender version
- The Script Extender console log from your most recent game session
- The contents of your sidecar cache file (the first 50 lines is enough)
- Which item or mod is showing the w