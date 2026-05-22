# Security & Antivirus Notes

## Reported detection: `MaxSecureTrojan.Malware.300983.susgen`

NexusMods has indicated that MaxSecure's antivirus engine flagged the published distribution bundle as `Trojan.Malware.300983.susgen`. This document explains the context of that detection.

### What the detection name means

The `susgen` suffix in MaxSecure detection IDs is widely documented (in third-party security write-ups) as standing for "Suspicious Generic" — that is, a **heuristic detection based on behavior**, not a signature match against any known malware family. The numeric portion (`300983`) is a generic detection class, not a specific malware identifier.

This same detection ID is reported by multiple sources to be commonly produced as a false positive against legitimate software, particularly installer-style files (`Setup.exe`, `Setup.msi`) and tools that perform file packing, file extraction, or scripted file copying.

### Why a BG3 mod build would trip a generic heuristic

The published distribution bundle for end users includes:

1. **`divine.exe` and supporting DLLs** — Norbyte's [LSLib](https://github.com/Norbyte/lslib) — an unsigned, third-party .NET binary that packs and unpacks Larian Studios `.pak` archives. This is the standard tool used across the entire BG3 modding community. **It is not bundled in this repository.** Source: https://github.com/Norbyte/lslib
2. **`.bat` and PowerShell orchestrators** — plain-text scripts that invoke `divine.exe`, copy generated files into the game's mod folder, and update a JSON cache. None of these scripts make network calls, modify the registry, or run as administrator.
3. **Python sidecar (`sidecar.py`, `run_all.py`, `unpack_paks.py`, etc.)** — plain-text Python that reads unpacked BG3 data and produces a `.lua` cache.
4. **`.pak` mod artifact** — a Larian-format archive containing BG3 Script Extender Lua and XML metadata. Opaque to AV engines because it is a Larian-proprietary container.

Each of these signals (unsigned exe + scripted exe invocation + file copying into a game directory) is part of the behavioral fingerprint heuristic AV engines use, regardless of whether the activity is malicious or benign.

### What this repository contains

**Only source code.** Every file in this repository is plain text and can be reviewed line-by-line: Lua, Python, `.bat`, PowerShell, XML, JSON, Markdown. No `.exe`, no `.dll`, no compiled binary of any kind.

If you are auditing this mod in response to an antivirus report, this repository is the right place to do it.

### What is *not* in this repository

- **`divine.exe` and LSLib DLLs** — please review them upstream at https://github.com/Norbyte/lslib.
- **Built `.pak` files** — these are build artifacts, not source. They are produced by running `sidecar/build_pak.bat` against the source in `mod/`.
- **BG3 Script Extender** — a separate project. Source: https://github.com/Norbyte/bg3se.

### Reporting a real security concern

If you find anything in this repository that looks malicious, please open a GitHub issue describing what file and what line concerns you. Real-world code review is welcomed.

---

## Third-party detection write-ups for `Trojan.Malware.300983.susgen`

These third-party sources describe the detection ID as commonly false-positive:

- [HackerDose — Trojan.Malware.300983.susgen False Positive Threat Detection](https://hackerdose.com/malware/trojan-malware-300983-susgen-false-positive/)
- [Trojan-Killer — Trojan.Malware.300983.Susgen False Positives Detection](https://trojan-killer.net/maxsecure-trojan-malware-300983-susgen-guide/)
- [Sahasi Bloggers — Trojan.Malware.300983.Susgen: What It Means and How to Handle It Safely](https://sahasibloggers.com/trojan-malware-300983-susgen/)
- [HowToFix Guide — Trojan.Malware.300983.Susgen Trojan Virus](https://howtofix.guide/trojan-malware-300983-susgen/)
- [HowToRemove Guide — Trojan.Malware.300983.susgen Removal Report](https://howtoremove.guide/trojan-malware-300983-susgen/)

These are secondary sources. No primary MaxSecure publication describing the detection rule itself was found in a public search.
