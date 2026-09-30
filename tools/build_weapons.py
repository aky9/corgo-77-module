"""Generate Foundry Item documents (CPR Core 0.92.4 schema) for Corgo's 77 Collection weapons.

Inputs:  data/weapons.parsed.json      (from parse_weapons.py)
         data/corgo-77-v3.md           (each weapon's entry, through entry_text.lookup)
         text/weapon_variants.json     (Ironfake / Darkhound variants)
Output:  src/packs/weapons/*.json      (one file per document, compiled by tools/compile.mjs)
"""
import re
from pathlib import Path
from common import doc_id, title_case, parse_cost, description_html, folder_doc, load_json, SOURCE_BOOK
from dvtables import DvPlan, CORE_TABLE_NAMES
import entry_text

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = "systems/cyberpunk-red-core/icons/compendium/weapons/"

# ---- mapping tables ----------------------------------------------------------

# Corgo class name -> (CPR weaponType, icon stem, default ammo)
CLASS_MAP = {
    "Medium Pistol":     ("medPistol",      "mediumPistol",    ["medPistol"]),
    "Heavy Pistol":      ("heavyPistol",    "heavyPistol",     ["heavyPistol"]),
    "Very Heavy Pistol": ("vHeavyPistol",   "veryHeavyPistol", ["vHeavyPistol"]),
    "SMG":               ("smg",            "SMG",             ["medPistol"]),
    "Heavy SMG":         ("heavySmg",       "heavySMG",        ["heavyPistol"]),
    "Shotgun":           ("shotgun",        "Shotgun",         ["shotgunShell", "shotgunSlug"]),
    "Assault Rifle":     ("assaultRifle",   "AssaultRifle",    ["rifle"]),
    # CPR 0.92.4 has no machine-gun type; assaultRifle keeps rifle ammo and Autofire enabled.
    "Machine Gun":       ("assaultRifle",   "AssaultRifle",    ["rifle"]),
    "Sniper Rifle":      ("sniperRifle",    "SniperRifle",     ["rifle"]),
    "Bow":               ("bow",            "Bow",             ["arrow"]),
    "Crossbow":          ("bow",            "Crossbow",        ["arrow"]),
    "Grenade Launcher":  ("grenadeLauncher", "GrenadeLauncher", ["grenade"]),
    "Rocket Launcher":   ("rocketLauncher", "RocketLauncher",  ["rocket"]),
    "Medium Melee":      ("medMelee",       "Crowbar",         []),
    "Heavy Melee":       ("heavyMelee",     "Machete",         []),
    "Very Heavy Melee":  ("vHeavyMelee",    "Sword",           []),
}
MELEE_ICON_BY_NAME = {  # nicer icons for specific melee weapons
    "KANABO": "BaseballBat", "CLAW": "CombatKnife", "PUNKNIFE": "CombatKnife",
    "NEUROTOXIN KNIFE": "CombatKnife", "TOMAHAWK": "Tomahawk", "ELECTRIC BATON": "StunBaton",
    "REPURPOSED SLEDGEHAMMER": "Sledgehammer", "BUDGET ARMS CUT-O-MATIC": "Chainsaw",
}
QUALITY_PREFIX = [("Excellent Quality ", "excellent"), ("EQ ", "excellent"),
                  ("Poor Quality ", "poor"), ("PQ ", "poor")]

SKILL_MAP = {"Melee Weapons": "Melee Weapon", "Melee": "Melee Weapon",
             "N/A": "Heavy Weapons"}  # N/A = Autofire-only machine guns

GROUP_FOLDERS = {
    "PISTOLS": "Pistols", "SUBMACHINE GUNS (SMGs)": "SMGs", "SHOTGUNS": "Shotguns",
    "ASSAULT RIFLES": "Assault Rifles", "MACHINE GUNS": "Machine Guns", "SNIPER RIFLES": "Sniper Rifles",
    "BOWS & CROSSBOWS": "Bows & Crossbows", "GRENADE LAUNCHERS": "Grenade Launchers",
    "ROCKET LAUNCHERS": "Rocket Launchers", "MELEE WEAPONS": "Melee Weapons",
    "Ironfake": "Variants: Ironfakes", "Darkhound": "Variants: Darkhounds",
}

# Per-weapon automation the core supports that isn't expressible in the stat line.
SPECIAL_SYSTEM = {
    "ARASAKA KSJR-23 AKA-ASHI": {"canIgnoreArmor": True, "ignoreBelowSP": 9},
}
AMMO_OVERRIDE = {"ARASAKA HOICHI AIRGUN": ["arrow"]}


def split_class(cls):
    """'Exotic PQ Very Heavy Pistol' -> ('poor', True, 'Very Heavy Pistol')

    "Iconic" counts as Exotic: the Iconic Weapons chapter says Iconics use the Exotic base rules, so they
    load no Non-Basic Ammunition and have no Attachment Slots unless an entry says otherwise.
    """
    exotic = False
    rest = cls
    for prefix in ("Exotic ", "Iconic "):
        if rest.startswith(prefix):
            exotic = True
            rest = rest[len(prefix):]
    quality = "standard"
    for prefix, q in QUALITY_PREFIX:
        if rest.startswith(prefix):
            quality, rest = q, rest[len(prefix):]
            break
    return quality, exotic, rest


def parse_damage(raw, notes):
    """Return a formula CPR 0.92.4 can roll (Xd6), adding a note when Corgo's rule can't be automated."""
    if raw in (None, "N/A"):
        return None
    m = re.match(r"(\d+)d6", raw)
    base = f"{m.group(1)}d6"
    if "/" in raw:
        notes.append(f"Listed damage is {raw}; the sheet uses the first value.")
    if "drop" in raw.lower():
        drop = re.search(r"Drop (\d+) Lowest", raw, re.I)
        n = int(drop.group(1)) if drop else 1
        notes.append(f"Damage is {base}, dropping the {'lowest die' if n == 1 else f'{n} lowest dice'}. "
                     "CPR 0.92.4 can't drop dice automatically, so drop them by hand from the damage roll.")
    return base


def build(rec, folder_id, plan, variant=None, section_key="weapons", section_label=None,
          facts_head=None, price=None, extra_notes=(), exotic_note="Exotic weapon."):
    notes = []
    name = rec.get("name") or title_case(rec["heading"])
    quality, exotic, kind = split_class(rec["class"])
    weapon_type, icon, ammo = CLASS_MAP[kind]
    is_melee = weapon_type.endswith("Melee")

    # damage
    damage = parse_damage(rec["damage"], notes)
    cap_raw = rec["capacity"] or "N/A"
    shell_only = "Shell Only" in cap_raw
    if damage is None:
        if kind == "Machine Gun":
            damage = "2d6"
            notes.append("Autofire and Suppressive Fire only; 2d6 is the standard Autofire damage.")
        elif kind == "Shotgun":
            damage = "3d6"  # shotgun shells
        else:
            damage = "0"

    # capacity
    cap_num = re.match(r"(\d+)(?:/(\d+))?", cap_raw)
    magazine = 0
    if cap_num:
        magazine = max(int(g) for g in cap_num.groups() if g)
    if "/" in cap_raw and "Shell" not in cap_raw:
        notes.append(f"Listed capacity is {cap_raw}; the sheet tracks {magazine}.")

    # ammo
    ammo = AMMO_OVERRIDE.get(rec["heading"], ammo)
    alt = rec["alt_modes"] or "None"
    if shell_only:
        ammo = ["shotgunShell"]
    elif "Shotgun Shell" in alt and "shotgunShell" not in ammo:
        ammo = ammo + ["shotgunShell"]

    # fire modes
    af = re.search(r"Autofire \(([A-Za-z ]+?) ?(\d)\)", alt)
    autofire = int(af.group(2)) if af else 0
    af_type = af.group(1).strip() if af else None
    suppressive = "Suppressive Fire" in alt
    if autofire and not suppressive and weapon_type not in ("smg", "heavySmg", "assaultRifle"):
        notes.append("CPR 0.92.4 shows a \"weapon doesn't support this mode\" warning when a pistol Autofires; "
                     "it's only a warning and the roll still works.")

    # range / DV table (Solo of Fortune 2045 tables, shipped in this module's DV Tables compendium)
    rng = rec.get("range") or "N/A"
    if is_melee or rng in ("Melee", "4m/yds"):
        dv_table = ""
    else:
        dv_table, _row = plan.weapon_table(rng, af_type)
        if dv_table.endswith("(Autofire)"):
            notes.append("Autofire only, so its DV table is the Autofire table.")
        if rng == "Carbine / Battle Rifle":
            notes.append("Uses DV Carbine; change the item's DV table to DV Battle Rifle while the Battle Barrel is selected.")
        tables_used = [dv_table] + ([f"{dv_table} (Autofire)"] if af_type and not dv_table.endswith("(Autofire)") else [])
        if any(t not in CORE_TABLE_NAMES for t in tables_used):
            notes.append("Its range tables come from this module's DV Tables compendium; run the module's "
                         "\"Use Corgo's 77 DV Tables\" macro once per world (see the module README).")

    skill = SKILL_MAP.get(rec["skill"], rec["skill"] or "Handgun")
    slots_raw = rec["slots"] or "0"
    slots = int(slots_raw) if slots_raw.isdigit() else 0
    price = price if price is not None else parse_cost(rec["cost"])[0]
    concealable = (rec["concealable"] or "No").startswith("Yes")

    if exotic and exotic_note:
        notes.append(exotic_note)
    notes.extend(extra_notes)
    img_stem = MELEE_ICON_BY_NAME.get(rec["heading"], icon)
    suffix = {"excellent": "_excellent", "poor": "_poor"}.get(quality, "")
    if img_stem == "Bow" and suffix == "_excellent":
        suffix = "_exellent"  # the core's file name has this typo
    if img_stem in ("StunBaton",):
        suffix = ""
    img = f"{ICON_DIR}{img_stem}{suffix}.svg"

    system = {
        "ammoVariety": ammo,
        "attackmod": 0,
        "brand": "",
        "canIgnoreArmor": False,
        "concealable": {"concealable": concealable, "isConcealed": False},
        "critFailEffect": "jammed",
        "damage": damage,
        "description": {"value": ""},
        "dvTable": dv_table,
        "equipped": "owned",
        "favorite": False,
        "fireModes": {"autoFire": autofire, "suppressiveFire": suppressive},
        "handsReq": int(rec["hands"] or 1),
        "ignoreArmorPercent": 0,
        "ignoreBelowSP": 0,
        "installedItems": {
            "allowed": True,
            "allowedTypes": ["itemUpgrade"] if is_melee else ["itemUpgrade", "ammo"],
            "list": [],
            "slots": slots,
            "usedSlots": 0,
        },
        "isRanged": not is_melee,
        "magazine": {"ammoData": None, "max": magazine, "value": 0},
        "price": {"market": price},
        "quality": quality,
        "revealed": True,
        "rof": max(int(x) for x in re.findall(r"\d", rec["rof"] or "1")),
        "source": {"book": SOURCE_BOOK, "page": 0},
        "unarmedAutomaticCalculation": True,
        "usage": "equipped",
        "usesType": "magazine",
        "weaponSkill": skill,
        "weaponType": weapon_type,
    }
    system.update(SPECIAL_SYSTEM.get(rec["heading"], {}))

    facts = list(facts_head) if facts_head else [("Cost", rec["cost"])]
    facts += [("Class", rec["class"]), ("Range", rng)]
    if rec.get("attachments") and rec["attachments"] != "None":
        facts.append(("Pre-installed", rec["attachments"] + " (effects already included in these stats)"))
    if rec.get("mods") and rec["mods"] != "None":
        facts.append(("Mods", rec["mods"]))
    if alt != "None":
        facts.append(("Alt. fire", alt))
    if variant:
        facts.insert(0, ("Variant of", title_case(variant["base"])))
    system["description"]["value"] = description_html(
        entry=entry_text.lookup(section_key, rec["heading"], variant and (variant["group"].upper() + "S")),
        facts=facts,
        notes=notes,
        section=section_label or ("Weapons > Weapon Catalog" + (" > Variants" if variant else "")),
    )

    _id = doc_id("weapon", rec["heading"])
    return {
        "_id": _id, "_key": f"!items!{_id}", "name": name, "type": "weapon", "img": img,
        "system": system, "effects": [], "folder": folder_id, "sort": 0,
        "ownership": {"default": 0}, "flags": {},
    }


def build_pack(plan):
    parsed = load_json(ROOT / "data/weapons.parsed.json")
    variants = load_json(ROOT / "text/weapon_variants.json")
    by_heading = {r["heading"]: r for r in parsed}

    folders, folder_docs = {}, []
    for sort, (key, label) in enumerate(GROUP_FOLDERS.items()):
        f = folder_doc("weapons", label, sort)
        folders[key] = f["_id"]
        folder_docs.append(f)

    docs = [build(r, folders[r["group"]], plan) for r in parsed]

    for v in variants["variants"]:
        base = dict(by_heading[v["base"]])
        rec = {**base, **{k: v[k] for k in ("heading", "cost", "class", "capacity", "alt_modes",
                                              "skill", "concealable", "attachments", "range") if k in v}}
        rec["mods"] = "None"
        docs.append(build(rec, folders[v["group"]], plan, variant=v))

    ids = [d["_id"] for d in docs]
    assert len(ids) == len(set(ids)), "duplicate ids"
    return folder_docs + docs

if __name__ == "__main__":
    print(len(build_pack(DvPlan())), "weapon documents")
