"""DV (range) tables for the module's RollTable compendium.

CPR Core 0.92.4 reads DV tables from ONE compendium (world setting `dvRollTableCompendium`), so the
module's pack holds a complete set: the core table names (so core weapons keep working) plus the
Solo of Fortune 2045 (Interface RED Vol. 5) tables Corgo's weapons use.

How 0.92.4 finds a weapon's Autofire table (actor sheet, autofire toggle): it takes the weapon's
DV table name, strips " (Autofire)", and picks the first table (sorted by name) whose name contains
that name and the word "Autofire". So the Autofire table must be named "<single-shot table> (Autofire)".
When weapons sharing a single-shot table use different Autofire types, the minority get a tagged copy,
e.g. "DV Carbine [SMG]" + "DV Carbine [SMG] (Autofire)". "(" sorts before "[", so the untagged
"DV Carbine (Autofire)" is still the first match for plain "DV Carbine" weapons.
"""
import json
from pathlib import Path
from common import doc_id

ROOT = Path(__file__).resolve().parent.parent
SOF = json.load(open(ROOT / "text/dv_tables_sof45.json", encoding="utf-8"))
CORE_DV = json.load(open(ROOT / "text/dv_tables_core.json", encoding="utf-8"))  # copied from CPR v0.92.4
ICON = "systems/cyberpunk-red-core/icons/compendium/default/Default_DV_Table.svg"

# Corgo's range label -> Solo of Fortune 2045 table row
RANGE_ALIASES = {
    "Gren. Launcher": "Grenade Launcher", "Mis. Launcher": "Missile Launcher",
    "Anti-Material Rifle": "Anti-Materiel Rifle", "Anti-Matieral Rifle": "Anti-Materiel Rifle",
    "Shotgun Long Barrel": "Long Barrel Shotgun",
    "Carbine / Battle Rifle": "Carbine",  # DA11 Equinox; description explains the swap
    "Grenade Launcher / Missile Launcher": "Grenade Launcher",  # SPECTER EX-76 EarthBreaker
}
# SOF45 row -> table name. Rows that exist in the core keep the core's name so core items still resolve.
CORE_NAMES = {
    "Pistol": "DV Pistol", "Long Barrel Pistol": "DV Long-Barrel Pistol", "SMG": "DV SMG",
    "Shotgun": "DV Shotgun (Slug)", "Assault Rifle": "DV Assault Rifle", "Sniper Rifle": "DV Sniper Rifle",
    "Bow": "DV Bows & Crossbows", "Grenade Launcher": "DV Grenade Launcher",
    "Rocket Launcher": "DV Rocket Launcher",
}
# Match the table names used by Schism989's "Cyberpunk RED - Solo of Fortune 2045" module (v1.1.0), so one
# DV compendium serves both modules' weapons. See tools/compat/schism-sof45.json.
SHARED_NAMES = {"Short Barrel Shotgun": "DV Short-Barrel Shotgun", "Long Barrel Shotgun": "DV Long-Barrel Shotgun",
                "Anti-Materiel Rifle": "DV Anti-materiel Rifle"}
CORE_TABLE_NAMES = set(CORE_NAMES.values()) | {"DV SMG (Autofire)", "DV Assault Rifle (Autofire)",
                                               "DV Generic", "DV Thrown Weapon"}
# Autofire type that "<table> (Autofire)" represents; weapons with a different type get a tagged copy.
CANONICAL_AUTOFIRE = {
    "Pistol": "Machine Pistol", "Snubnose Pistol": "Machine Pistol", "Long Barrel Pistol": "Machine Pistol",
    "Short Barrel Shotgun": "Machine Pistol", "Long Barrel Shotgun": "Machine Pistol",
    "SMG": "SMG", "Subcompact SMG": "SMG", "Assault Rifle": "Assault Rifle", "Carbine": "Assault Rifle",
    "Battle Rifle": "Machine Gun", "Marksman Rifle": "Machine Gun",
}
TAG = {"Machine Pistol": "MP", "SMG": "SMG", "Assault Rifle": "AR", "Machine Gun": "MG"}


def table_name(row):
    return CORE_NAMES.get(row) or SHARED_NAMES.get(row) or f"DV {row}"


class DvPlan:
    """Collects which tables the weapons need, and answers which DV table a weapon should use."""

    def __init__(self):
        self.single = {}    # table name -> SOF row (single-shot values)
        self.autofire = {}  # table name -> autofire type

    def weapon_table(self, corgo_range, autofire_type):
        """Return (dvTable name, sof_row) for a ranged weapon, registering the tables it needs."""
        if corgo_range == "N/A":
            if not autofire_type:
                return "", None
            name = f"DV {autofire_type} (Autofire)"  # autofire-only weapon
            self.autofire[name] = autofire_type
            return name, None
        row = RANGE_ALIASES.get(corgo_range, corgo_range)
        if row not in SOF["single"]:
            raise KeyError(f"No Solo of Fortune range table for {corgo_range!r}")
        name = table_name(row)
        if autofire_type and CANONICAL_AUTOFIRE.get(row, autofire_type) != autofire_type:
            name = f"{name} [{TAG[autofire_type]}]"
        self.single[name] = row
        if autofire_type:
            self.autofire[f"{name} (Autofire)"] = autofire_type
        return name, row

    def all_tables(self):
        """Every table the pack ships: all SOF rows, core-named autofire tables, plus what weapons need."""
        single = {table_name(r): r for r in SOF["single"]}
        single.update(self.single)
        autofire = {"DV SMG (Autofire)": "SMG", "DV Assault Rifle (Autofire)": "Assault Rifle"}
        autofire.update(self.autofire)
        return single, autofire


def _results(table_id, values, key_prefix):
    out = []
    for (lo, hi), dv in zip(SOF["bands"], values):
        rid = doc_id("dv-result", f"{key_prefix}:{lo}")
        out.append({"_id": rid, "_key": f"!tables.results!{table_id}.{rid}", "type": "text",
                    "text": "N/A" if dv is None else str(dv), "range": [lo, hi], "weight": 1,
                    "drawn": False, "documentId": None, "img": ICON})
    return out


def _table(name, values, description):
    tid = doc_id("dv-table", name)
    return {"_id": tid, "_key": f"!tables!{tid}", "name": name, "img": ICON, "description": description,
            "formula": "", "replacement": False, "displayRoll": False, "results": _results(tid, values, name)}


def _core_copy(name):
    """Tables SOF45 doesn't replace (DV Generic, DV Thrown Weapon), copied unchanged from CPR 0.92.4."""
    t = CORE_DV[name]
    return _table(name, t["values"], t["description"])


def build_docs(plan):
    single, autofire = plan.all_tables()
    sof = "<p>Solo of Fortune 2045, Interface RED Vol. 5.{}</p>"
    docs = []
    for name, row in sorted(single.items()):
        extra = ""
        if "[" in name:
            extra = f" Same distances as {table_name(row)}; this copy exists so its weapons get the right Autofire table."
        docs.append(_table(name, SOF["single"][row], sof.format(extra)))
    for name, af_type in sorted(autofire.items()):
        docs.append(_table(name, SOF["autofire"][af_type], sof.format(f" {af_type} Autofire DVs.")))
    docs.append(_core_copy("DV Generic"))
    docs.append(_core_copy("DV Thrown Weapon"))
    names = [d["name"] for d in docs]
    assert len(names) == len(set(names)), "duplicate DV table names"
    return docs


def register_compat(plan, compat):
    """Make sure the tables that Schism's weapons need (per the book) exist, and return the DV table each of
    his weapons should use: {weapon name: (recommended dvTable, dvTable his item currently has)}."""
    current = {w["name"]: w["dvTable"] for w in compat["weapons"]}
    out = {}
    for name, b in compat["book"].items():
        table, _row = plan.weapon_table(b["range"], b["autofire"])
        out[name] = (table, current.get(name, ""))
    return out
