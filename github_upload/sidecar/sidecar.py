#!/usr/bin/env python3
"""
AlanTooltipCompat — Sidecar utility v0.1

Walks BG3 mod folders (unpacked .pak content), extracts armor/clothing items
and their EquipmentRace GUID compatibility lists, and produces two outputs:
  - compat_cache.json: per-item body-type compatibility info for the BG3SE Lua
  - AlanTooltipCompat.loca.xml: synthetic loca handles for runtime text update

Phase 1.0: works on UNPACKED mod folders only. Phase 1.5 will add .pak support
via LSLib's divine.exe.

Usage:
    python sidecar.py --mods-dir <path> --output-dir <path>

Expected layout under --mods-dir:
    <mods-dir>/
        <ModName1>/
            Public/<ModName1>/RootTemplates/*.lsf.lsx
                (either a single _merged.lsf.lsx, or one or more per-UUID
                 <uuid>.lsf.lsx files — both are supported as of v1.2)
            Public/<ModName1>/Stats/Generated/Data/<ModName1>_Stats.txt   (optional)
            ...
        <ModName2>/
            ...
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from lxml import etree

# ============================================================================
# EquipmentRace GUID → label map
# Source: Shared\Mods\SharedDev\EquipmentSettings\EquipmentRaces.lsx
# BG3 Patch 8, 24 entries, verified 2026-05-17
# ============================================================================

EQUIPMENT_RACES = {
    "7d73f501-f65e-46af-a13b-2cacf3985d05": "Human Male",
    "71180b76-5752-4a97-b71f-911a69197f58": "Human Female",
    "e39505f7-f576-4e70-a99e-8e29cd381a11": "Human Strong Male",
    "47c0315c-7dc6-4862-b39b-8bf3a10f8b54": "Human Strong Female",
    "7dd0aa66-5177-4f65-b7d7-187c02531b0b": "Elf/Drow Male",
    "ad21d837-2db5-4e46-8393-7d875dd71287": "Elf/Drow Female",
    "a0737289-ca84-4fde-bd52-25bae4fe8dea": "Half-Elf Male",
    "541473b3-0bf3-4e68-b1ab-d85894d96d3e": "Half-Elf Female",
    "6503c830-9200-409a-bd26-895738587a4a": "Tiefling Male",
    "cf421f4e-107b-4ae6-86aa-090419c624a5": "Tiefling Female",
    "f07faafa-0c6f-4f79-a049-70e96b23d51b": "Githyanki Male",
    "06aaae02-bb9e-4fa3-ac00-b08e13a5b0fa": "Githyanki Female",
    "abf674d2-2ea4-4a74-ade0-125429f69f83": "Dwarf Male",
    "b4a34ce7-41be-44d9-8486-938fe1472149": "Dwarf Female",
    "a933e2a8-aee1-4ecb-80d2-8f47b706f024": "Halfling Male",
    "8f00cf38-4588-433a-8175-8acdbbf33f33": "Halfling Female",
    "5640e766-aa53-428d-815b-6a0b4ef95aca": "Gnome Male",
    "c491d027-4332-4fda-948f-4a3df6772baa": "Gnome Female",
    "9a8bbeba-850c-402f-bac5-ff15696e6497": "Dragonborn Male",
    "6d38f246-15cb-48b5-9b85-378016a7a78e": "Dragonborn Female",
    "eb81b1de-985e-4e3a-8573-5717dc1fa15c": "Half-Orc Female",
    "6dd3db4f-e2db-4097-b82e-12f379f94c2e": "Half-Orc Male",
    "a5789cd3-ecd6-411b-a53a-368b659bc04a": "Tiefling Female Strong",
    "6326d417-315c-4605-964e-d0fad73d719b": "Tiefling Karlach",
    "f625476d-29ec-4a6d-9086-42209af0cf6f": "Tiefling Male Strong",
}

# ============================================================================
# Helpers
# ============================================================================

def synthetic_handle(stat_name: str) -> str:
    """
    Generate a deterministic synthetic loca handle for a given armor stat name.
    Format: h<8>g<4>g<4>g<4>g<12> — matches BG3's observed loca handle format.
    The same stat_name always produces the same handle (idempotent).
    """
    digest = hashlib.md5(("AlanTooltipCompat:" + stat_name).encode("utf-8")).hexdigest()
    return f"h{digest[0:8]}g{digest[8:12]}g{digest[12:16]}g{digest[16:20]}g{digest[20:32]}"


def get_attr(node, attr_id, default=None):
    """Find a child <attribute id="X" value="..."/> and return its value."""
    found = node.find(f'./attribute[@id="{attr_id}"]')
    if found is None:
        return default
    return found.get("value", default)


def get_child_node(node, child_id):
    """Find a child <node id="X"> under this node's <children>."""
    return node.find(f'./children/node[@id="{child_id}"]')


def iter_child_nodes(node, child_id):
    """Iterate every <node id="X"> directly under this node's <children>."""
    children = node.find("./children")
    if children is None:
        return []
    return children.findall(f'./node[@id="{child_id}"]')


# ============================================================================
# Core extraction
# ============================================================================

def _own_description_handle(go):
    """Read Description.handle off this GameObject node only (no inheritance)."""
    desc_node = go.find('./attribute[@id="Description"]')
    return desc_node.get("handle") if desc_node is not None else None


def _own_race_guids(go):
    """Read Equipment.Visuals.Object MapKey list off this node only."""
    equipment = get_child_node(go, "Equipment")
    if equipment is None:
        return []
    visuals = get_child_node(equipment, "Visuals")
    if visuals is None:
        return []
    return [g for g in (get_attr(o, "MapKey") for o in iter_child_nodes(visuals, "Object")) if g]


def extract_items_from_root_template(rt_path: Path):
    """
    Parse a RootTemplate .lsf.lsx file (either Larian's _merged.lsf.lsx form
    or a per-UUID <uuid>.lsf.lsx form — both have the same XML structure,
    just one-vs-many GameObjects inside). Yield dicts for each item that
    has an Equipment > Visuals block (i.e. wearable armor/clothing/accessory).

    Parent-walk (v1.1, 2026-05-20): when an item's own GameObject node
    lacks a Description handle or Equipment.Visuals.Object children, walk
    the ParentTemplateId chain WITHIN THIS FILE looking for inherited
    values. This rescues "stub template" items like ARM_Padded_2 (Padded
    Armour +1) which lack their own Equipment block and inherit it from
    parent ARM_Padded.

    Walks are in-file only — cross-file inheritance (mod-child → Shared-
    pak-parent) isn't supported in v1.1. Most stub-template cases ARE
    in-file because Larian keeps related templates in the same pak.

    Yields: {
        "map_key": str,
        "name": str,
        "stat_name": str|None,
        "race_guids": [str],
        "description_handle": str|None,
        "rescued_desc": bool,         # True if Description came from a parent
        "rescued_equip": bool,        # True if Equipment.Visuals came from a parent
    }
    """
    try:
        tree = etree.parse(str(rt_path))
    except etree.XMLSyntaxError as e:
        print(f"  ERROR parsing {rt_path}: {e}")
        return

    root = tree.getroot()
    templates_region = root.find('./region[@id="Templates"]')
    if templates_region is None:
        return
    templates_node = templates_region.find('./node[@id="Templates"]')
    if templates_node is None:
        return

    # ---- Pass 1: build {uuid -> GameObject node} for this file -----------
    # Required so we can look up parents during the inheritance walk.
    template_by_uuid = {}
    for go in iter_child_nodes(templates_node, "GameObjects"):
        uuid = get_attr(go, "MapKey")
        if uuid:
            template_by_uuid[uuid] = go

    MAX_DEPTH = 10  # plenty for any realistic BG3 chain (typical max is 4)

    def walk_for_description(go):
        """Return (handle, levels_walked). levels_walked=0 means own node."""
        cur = go
        for depth in range(MAX_DEPTH):
            h = _own_description_handle(cur)
            if h:
                return h, depth
            parent_id = get_attr(cur, "ParentTemplateId")
            if not parent_id:
                return None, depth
            cur = template_by_uuid.get(parent_id)
            if cur is None:
                # Parent is in a different file (cross-file walk not supported).
                return None, depth
        return None, MAX_DEPTH

    def walk_for_race_guids(go):
        """Return (guids, levels_walked). levels_walked=0 means own node."""
        cur = go
        for depth in range(MAX_DEPTH):
            guids = _own_race_guids(cur)
            if guids:
                return guids, depth
            parent_id = get_attr(cur, "ParentTemplateId")
            if not parent_id:
                return [], depth
            cur = template_by_uuid.get(parent_id)
            if cur is None:
                return [], depth
        return [], MAX_DEPTH

    # ---- Pass 2: iterate items, walking inheritance for missing fields ----
    for go in iter_child_nodes(templates_node, "GameObjects"):
        map_key = get_attr(go, "MapKey")
        if not map_key:
            continue

        # Only process items. Without this guard, parent-walk could
        # accidentally pull armor data into non-item templates (e.g., a
        # scenery node whose ancestry crosses an item somehow). Belt-and-
        # suspenders — the race_guids check would also filter these out,
        # but it's clearer to be explicit.
        if get_attr(go, "Type") != "item":
            continue

        name = get_attr(go, "Name", "<unnamed>")
        stat_name = get_attr(go, "Stats")

        desc_handle, desc_depth = walk_for_description(go)
        race_guids, equip_depth = walk_for_race_guids(go)

        if not race_guids:
            continue  # no EquipmentRace info anywhere in chain — not wearable

        yield {
            "map_key": map_key,
            "name": name,
            "stat_name": stat_name,
            "race_guids": race_guids,
            "description_handle": desc_handle,
            "rescued_desc": desc_handle is not None and desc_depth > 0,
            "rescued_equip": equip_depth > 0,
        }


def race_guids_to_labels(guids):
    """Map list of EquipmentRace GUIDs to deduped human-readable labels."""
    labels = []
    unknown = []
    seen = set()
    for g in guids:
        if g in EQUIPMENT_RACES:
            label = EQUIPMENT_RACES[g]
            if label not in seen:
                seen.add(label)
                labels.append(label)
        else:
            unknown.append(g)
    return labels, unknown


# ============================================================================
# Output
# ============================================================================

def _build_payload(items, bg3_patch_version: str):
    """Build the cache payload dict from extracted items."""
    cache_items = {}
    skipped_no_handle = 0

    for item in items:
        if not item.get("description_handle"):
            skipped_no_handle += 1
            continue
        # Key by MapKey (template UUID) — that's what
        # Ext.Template.GetTemplate would use too if we needed to.
        cache_items[item["map_key"]] = {
            "name": item["name"],
            "stat_name": item.get("stat_name") or "",
            "description_handle": item["description_handle"],
            "compat_text": ", ".join(item["labels"]),
        }

    payload = {
        "schema_version": 3,
        "bg3_patch_version": bg3_patch_version,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "items": cache_items,
    }
    return payload, skipped_no_handle


def _lua_escape(s: str) -> str:
    """Escape a Python string for a Lua single-quoted string literal."""
    return (s.replace("\\", "\\\\")
             .replace("'", "\\'")
             .replace("\n", "\\n")
             .replace("\r", "\\r")
             .replace("\t", "\\t"))


def _lua_value(v, indent: int = 0) -> str:
    """Serialize a Python value to Lua source. Supports str, int, float, bool, None, list, dict."""
    if v is None:
        return "nil"
    if isinstance(v, bool):  # bool BEFORE int (bool is subclass of int in Python)
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return "'" + _lua_escape(v) + "'"
    if isinstance(v, list):
        return "{" + ", ".join(_lua_value(x, indent + 1) for x in v) + "}"
    if isinstance(v, dict):
        pad = "  " * (indent + 1)
        close_pad = "  " * indent
        lines = []
        for k, val in v.items():
            # Lua table keys: identifier-safe names can be unquoted; everything else uses [key]=...
            if isinstance(k, str) and k.isidentifier():
                lines.append(f"{pad}{k} = {_lua_value(val, indent + 1)}")
            else:
                lines.append(f"{pad}[{_lua_value(k)}] = {_lua_value(val, indent + 1)}")
        return "{\n" + ",\n".join(lines) + f",\n{close_pad}" + "}"
    raise TypeError(f"Cannot Lua-encode {type(v).__name__}: {v!r}")


def write_cache_file(items, output_path: Path, output_format: str,
                     bg3_patch_version: str):
    """Write the cache file in either JSON or Lua format.

    JSON format is loaded at runtime via Ext.IO.LoadFile from the user's
    Script Extender folder (writable, regenerated by sidecar).

    Lua format is loaded at runtime via Ext.Require from inside the mod's
    own pak (read-only, pre-baked and bundled with the mod). Used for
    vanilla-cache distribution so end users don't need to unpack base-game
    paks themselves.
    """
    payload, skipped_no_handle = _build_payload(items, bg3_patch_version)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "lua":
        header = (
            "-- AlanTooltipCompat — auto-generated cache file. Do not edit by hand.\n"
            f"-- Source: {len(items)} item(s); bg3_patch_version={bg3_patch_version!r}\n"
            f"-- Generated: {payload['generated_utc']}\n"
            "-- Load via Ext.Require(\"<modname>\") from BootstrapClient.lua\n"
            "\n"
        )
        body = "return " + _lua_value(payload) + "\n"
        output_path.write_text(header + body, encoding="utf-8")
    else:  # json (default)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"  Wrote {output_path}")
    print(f"    items written: {len(payload['items'])}")
    print(f"    format:        {output_format}")
    print(f"    patch version: {bg3_patch_version}")
    if skipped_no_handle:
        print(f"    skipped (no Description handle): {skipped_no_handle}")


def write_loca_xml(items, output_path: Path):
    """Write Localization/English/<modname>.loca.xml with synthetic handles."""
    seen_handles = set()
    root = etree.Element("contentList")

    for item in items:
        stat_name = item["stat_name"]
        if not stat_name:
            continue
        handle = synthetic_handle(stat_name)
        if handle in seen_handles:
            continue
        seen_handles.add(handle)

        content = etree.SubElement(root, "content")
        content.set("contentuid", handle)
        content.set("version", "1")
        # Placeholder text — overwritten at runtime by Ext.Loca.UpdateTranslatedString
        content.text = "__placeholder__"

    tree = etree.ElementTree(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output_path), pretty_print=True, xml_declaration=True, encoding="utf-8")
    print(f"  Wrote {output_path} ({len(seen_handles)} handles)")


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="BG3 Tooltip Compatibility — Sidecar v0.1 (unpacked-mods mode)"
    )
    parser.add_argument(
        "--mods-dir", "-m", required=True,
        help="Folder containing unpacked mod directories. Each subfolder should "
             "have Public/<ModName>/RootTemplates/ containing either a "
             "_merged.lsf.lsx OR one or more per-UUID <uuid>.lsf.lsx files "
             "(v1.2+)."
    )
    parser.add_argument(
        "--output-dir", "-o", required=True,
        help="Folder to write the cache file and AlanTooltipCompat.loca.xml."
    )
    parser.add_argument(
        "--cache-name", default="compat_cache.json",
        help="Filename for the cache output (default: compat_cache.json). "
             "Use vanilla_cache.lua when generating the maintainer-bundled "
             "vanilla cache for the mod pak."
    )
    parser.add_argument(
        "--output-format", choices=["json", "lua"], default=None,
        help="Cache output format. Defaults to inferred-from-extension: .lua "
             "extension -> lua, anything else -> json."
    )
    parser.add_argument(
        "--bg3-patch-version", default="patch_8_hotfix_8",
        help="BG3 patch version label embedded in the cache for staleness "
             "detection at runtime."
    )
    parser.add_argument(
        "--skip-loca", action="store_true",
        help="Skip writing the .loca.xml file (vanilla-cache generation doesn't "
             "need it — synthetic loca handles are unused in v3 architecture)."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print every item found (default: per-mod summaries only)."
    )
    args = parser.parse_args()

    # Infer format from extension if not explicit
    if args.output_format is None:
        args.output_format = "lua" if args.cache_name.lower().endswith(".lua") else "json"

    mods_dir = Path(args.mods_dir)
    out_dir = Path(args.output_dir)

    if not mods_dir.is_dir():
        print(f"ERROR: mods directory not found: {mods_dir}", file=sys.stderr)
        return 1

    print(f"Scanning: {mods_dir}")
    print(f"Output:   {out_dir}")
    print()

    # v1.2: glob widened from "_merged.lsf.lsx" to "*.lsf.lsx" so per-UUID
    # RootTemplate files (Class F + G mods) are picked up alongside merged ones.
    # The per-UUID XML structure is identical to _merged form — same
    # <save>/<region id="Templates">/<node id="Templates">/<children>/<node id="GameObjects">
    # wrapping, just one GameObject inside instead of many. The existing parser
    # in extract_items_from_root_template handles both cases unchanged.
    rt_files = sorted(mods_dir.glob("*/Public/*/RootTemplates/*.lsf.lsx"))
    print(f"Found {len(rt_files)} RootTemplate file(s).\n")

    all_items = []
    unknown_guids_global = set()
    # v1.1 parent-walk stats (aggregated across all files)
    rescued_desc_total = 0
    rescued_equip_total = 0

    for rt in rt_files:
        # rt = <mod>/Public/<X>/RootTemplates/{_merged or <uuid>}.lsf.lsx
        # parents: RootTemplates -> <X> -> Public -> <mod>
        mod_folder = rt.parent.parent.parent.parent
        public_subname = rt.parent.parent.name  # the <X> after Public/
        print(f"[{mod_folder.name} / Public/{public_subname}]")
        count = 0
        rescued_desc_file = 0
        rescued_equip_file = 0

        for item in extract_items_from_root_template(rt):
            labels, unknown = race_guids_to_labels(item["race_guids"])
            if unknown:
                unknown_guids_global.update(unknown)
            if not labels:
                continue

            item["labels"] = labels
            item["mod_folder"] = mod_folder.name
            all_items.append(item)
            count += 1
            if item.get("rescued_desc"):
                rescued_desc_file += 1
            if item.get("rescued_equip"):
                rescued_equip_file += 1

            if args.verbose:
                desc_handle_short = (item.get("description_handle") or "<none>")[:20]
                stat = item["stat_name"] or "<no stats>"
                tags = []
                if item.get("rescued_desc"): tags.append("desc-from-parent")
                if item.get("rescued_equip"): tags.append("equip-from-parent")
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                print(f"  {item['name']} [{stat}] desc={desc_handle_short}: {', '.join(labels)}{tag_str}")

        rescued_desc_total += rescued_desc_file
        rescued_equip_total += rescued_equip_file
        summary = f"  -> {count} armor/clothing item(s)"
        if rescued_desc_file or rescued_equip_file:
            extras = []
            if rescued_desc_file:
                extras.append(f"{rescued_desc_file} desc-from-parent")
            if rescued_equip_file:
                extras.append(f"{rescued_equip_file} equip-from-parent")
            summary += f"  [parent-walk rescued: {', '.join(extras)}]"
        print(summary + "\n")

    print("=" * 60)
    print(f"Total items: {len(all_items)}")
    if rescued_desc_total or rescued_equip_total:
        print(f"Parent-walk rescue totals:")
        print(f"  description handle inherited from parent: {rescued_desc_total}")
        print(f"  Equipment.Visuals inherited from parent:  {rescued_equip_total}")
    if unknown_guids_global:
        print(f"\nUnknown EquipmentRace GUIDs (not in 24-entry map):")
        for g in sorted(unknown_guids_global):
            print(f"  {g}")

    if not all_items:
        print("\nNo items found — exiting without writing outputs.", file=sys.stderr)
        return 1

    print(f"\nWriting outputs...")
    write_cache_file(all_items, out_dir / args.cache_name,
                     args.output_format, args.bg3_patch_version)
    if not args.skip_loca:
        write_loca_xml(all_items, out_dir / "AlanTooltipCompat.loca.xml")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
