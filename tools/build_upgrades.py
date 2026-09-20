"""Build Corgo's weapon attachments, mods, capacity-chart magazines and ammunition as CPR 0.92.4 items.

Attachments and mods are `itemUpgrade` items (type "weapon"). Corgo's Required Slots become the upgrade's
`size`; Weapon Mods and Invented Tech Upgrades take no slots (size 0). Only bonuses the core can apply are
automated: flat attack bonuses (situational ones show as toggles in the roll dialog), flat damage, extra
Attachment Slots, magazine size, ROF, and underbarrel secondary weapons. Everything else is rules text.
"""
import copy, json, re
from pathlib import Path
import original_text
from common import doc_id, title_case, parse_cost, description_html, folder_doc, SOURCE_BOOK

ROOT = Path(__file__).resolve().parent.parent
ICONS = "systems/cyberpunk-red-core/icons/compendium/"
ICON = {  # all exist at the same path in CPR 0.92.4 and 0.93
    None: ICONS + "default/Default_Gear.svg", "mag": ICONS + "upgrades/generic_extended_magazine.svg",
    "drum": ICONS + "upgrades/generic_drum_magazine.svg", "scope": ICONS + "upgrades/sniping_scope.svg",
    "smart": ICONS + "upgrades/smartgun_link.svg", "underbarrel": ICONS + "upgrades/grenade_launcher_underbarrel.svg",
    "bayonet": ICONS + "upgrades/bayonet.svg", "lock": ICONS + "upgrades/dna_lock.svg",
    "ammo": ICONS + "default/Default_Ammo.svg",
}
ELECTRONIC = {"LASER SIGHT", "IR/UV LASER SIGHT", "SMART SCOPE", "SONAR SENSOR", "TACTICAL LIGHT", "RANGEFINDER SCOPE",
              "GAKI SNIPING SCOPE", "SAIKA LONG SCOPE", "KANETSUGU SHORT SCOPE", "JUE LONG SCOPE", "BIOMETRIC LOCK",
              "AIRBURST LINK", "MICROWAVER UNDERBARREL", "SHRIEKER UNDERBARREL", "STUN GUN UNDERBARREL"}
NAME_FIX = {"IR/UV LASER SIGHT": "IR/UV Laser Sight", "HVAP AMMUNITION": "HVAP Ammunition",
            "IMPROVED EMP AMMUNITION": "Improved EMP Ammunition"}

# Corgo's Capacity Chart (Weapons in the 2070s > Attachment Updates). Values ADD to base capacity.
CAPACITY = {  # weapon row: Extended, Drum, Belt Box, Backpack
    "Pistol": (6, 18, 38, 76), "SMG": (10, 20, 40, 80), "Crossbow": (5, 11, 19, 39), "Shotgun": (4, 12, 24, 48),
    "Assault Rifle": (10, 25, 50, 100), "Machine Gun": (20, 40, 80, 160), "Sniper Rifle": (4, 8, 16, 32),
    "Grenade Launcher": (2, 4, 8, 16), "Rocket Launcher": (1, 2, 4, 8),
}
# (family, column, price, category, slots, icon). Extended/Drum price and slots are the core system's.
MAG_FAMILIES = [("Extended Magazine", 0, 100, "Premium", 1, "mag"), ("Drum Magazine", 1, 500, "Expensive", 1, "drum"),
                ("Belt Box", 2, 750, "Expensive", 2, "drum"), ("Backpack Magazine", 3, 1000, "Very Expensive", 1, "drum")]
MAG_RULE = ("Adds +{n} to capacity for {row} weapons (Corgo's Capacity Chart, added to the base capacity; the "
            "sheet applies it automatically). Only one Capacity attachment at a time.")
CROSSBOW_RULE = (" On a crossbow the magazine holds a single arrow type; other arrows can still be loaded by hand, "
                 "without an Action, if you have a free hand.")

MOD_KEYS = ["Wardrobe & Style", "attackmod", "bodySp", "cool", "damage", "headSp", "magazine", "rof", "sdp", "seats",
            "shieldHp", "slots"]
UPGRADE_TEMPLATE = {  # key set of CPR 0.92.4 core upgrades (e.g. Bayonet)
    "ammoVariety": [], "attackmod": 0, "brand": "", "canIgnoreArmor": False,
    "concealable": {"concealable": False, "isConcealed": False}, "damage": "0", "description": {"value": ""},
    "dvTable": "", "favorite": False, "fireModes": {"autoFire": 0, "suppressiveFire": False}, "handsReq": 0,
    "ignoreArmorPercent": 0, "installLocation": "mall",
    "installedItems": {"allowed": False, "allowedTypes": ["itemUpgrade"], "list": [], "slots": 0, "usedSlots": 0},
    "isElectronic": False, "isRanged": False, "magazine": {"ammoData": None, "max": 0, "value": 0},
    "modifiers": {**{k: {"type": "modifier", "value": None, "isSituational": False, "onByDefault": False}
                     for k in MOD_KEYS}, "secondaryWeapon": {"configured": False}},
    "price": {"market": 0}, "providesHardening": False, "rof": 1, "size": 1,
    "source": {"book": SOURCE_BOOK, "page": 0}, "type": "weapon", "unarmedAutomaticCalculation": True,
    "usesType": "magazine", "weaponSkill": "Handgun", "weaponType": "heavyPistol",
}
AMMO_TEMPLATE = {  # key set of CPR 0.92.4 core ammo (e.g. Arrow (Armor-Piercing))
    "ablationValue": 1, "amount": 10, "brand": "", "concealable": {"concealable": True, "isConcealed": False},
    "description": {"value": ""}, "favorite": False,
    "overrides": {"autofire": {"minimum": 3, "mode": "none", "value": -1},
                  "damage": {"minimum": "1d6", "mode": "none", "value": "3d6"}},
    "price": {"market": 0}, "source": {"book": SOURCE_BOOK, "page": 0}, "type": "basic", "variety": "custom",
}
VARIETY_LABEL = {"medPistol": "Medium Pistol", "heavyPistol": "Heavy Pistol", "vHeavyPistol": "Very Heavy Pistol",
                 "rifle": "Rifle", "shotgunSlug": "Slug", "shotgunShell": "Shell", "arrow": "Arrow",
                 "grenade": "Grenade", "rocket": "Rocket"}


def cost_of(raw):
    raw = re.sub(r"(\d)\.(\d{3})", r"\1,\2", raw or "")  # "1.000eb" typo in the source
    return parse_cost(raw)


def item(kind, key, name, itype, img, system, folder):
    _id = doc_id(kind, key)
    return {"_id": _id, "_key": f"!items!{_id}", "name": name, "type": itype, "img": img, "system": system,
            "effects": [], "folder": folder, "sort": 0, "ownership": {"default": 0}, "flags": {}}


def upgrade(key, name, spec, price, size, facts, rules, section, folder, notes=(), heading=None,
            section_key=None, intro_only=False):
    s = copy.deepcopy(UPGRADE_TEMPLATE)
    s["price"]["market"] = price
    s["size"] = size
    s["isElectronic"] = key in ELECTRONIC
    mods = s["modifiers"]
    for field, mod_key in (("attack", "attackmod"), ("damage", "damage")):
        if field in spec:
            value, situational = spec[field]
            mods[mod_key].update(value=value, isSituational=situational, onByDefault=False)
    for mod_key, value in spec.get("mods", {}).items():  # bodySp, headSp, shieldHp, ...
        mods[mod_key]["value"] = value
    if "slots" in spec:
        mods["slots"]["value"] = spec["slots"]
    if "magazine" in spec:
        mods["magazine"]["value"] = spec["magazine"]
    if "rof_override" in spec:
        mods["rof"].update(type="override", value=spec["rof_override"])
    if "secondary" in spec:
        w = spec["secondary"]
        mods["secondaryWeapon"]["configured"] = True
        s.update(damage=w["damage"], rof=w["rof"], weaponType=w["weaponType"], weaponSkill=w["weaponSkill"],
                 isRanged=w["isRanged"], dvTable=w.get("dvTable", ""), ammoVariety=w.get("ammo", []))
        s["magazine"]["max"] = w.get("magazine", 0)
        if w.get("ammo"):
            s["installedItems"].update(allowed=True, allowedTypes=["ammo"])
    s["description"]["value"] = description_html(facts=facts, rules=rules, notes=list(notes), section=section,
                                                 original=(original_text.lookup(section_key, heading, intro_only=intro_only)
                                                           if section_key else None))
    return item("upgrade", key, name, "itemUpgrade", ICON[spec.get("icon")], s, folder)


def nested_parents(parsed):
    """Headings that have deeper "#### " entries under them (Long Scope -> Jue Long Scope, and so on).

    Their original-text lookup has to stop at the first sub-heading, or the parent's description runs on
    into its variants' text - which is how the plain Long Scope ended up carrying the Jue and Saika rules.
    """
    return {r["heading"] for i, r in enumerate(parsed)
            if i + 1 < len(parsed) and parsed[i + 1]["level"] > r["level"]}


def build_attachments(parsed, spec):
    docs, folders = [], {}

    def folder(label):
        if label not in folders:
            f = folder_doc("attachments", label, len(folders))
            folders[label] = f["_id"]
            docs.append(f)
        return folders[label]

    parents = nested_parents(parsed)
    for rec in parsed:
        sp = spec[rec["heading"]]
        if "magazine_family" in sp:
            continue  # generated per weapon type below
        group = title_case(rec["group"]).replace(" And ", " & ")
        price, cat = cost_of(rec["stats"].get("Cost"))
        size = int(rec["stats"].get("Required Slots", "1"))
        facts = [("Cost", rec["stats"].get("Cost", "")), ("Attachment slots", str(size)),
                 ("Fits", rec["stats"].get("Fits", ""))]
        name = sp.get("name") or NAME_FIX.get(rec["heading"]) or title_case(rec["heading"])
        notes = [sp["price_note"]] if sp.get("price_note") else []
        section = f"Weapons > Attachment Catalog > {group}"
        if "split" in sp:
            for sub_name, sub_price, sub_rule in sp["split"]:
                f = [("Cost", f"{sub_price:,}eb"), *facts[1:]]
                docs.append(upgrade(f"{rec['heading']}:{sub_name}", sub_name, sp, sub_price, size, f,
                                    f"{sp['rules']} {sub_rule}", section, folder(group), notes,
                                    heading=rec["heading"], section_key="attachments",
                                    intro_only=rec["heading"] in parents))
            continue
        docs.append(upgrade(rec["heading"], name, sp, sp.get("price", price), size, facts, sp["rules"], section,
                            folder(group), notes, heading=rec["heading"], section_key="attachments",
                            intro_only=rec["heading"] in parents))

    for fam, col, price, cat, size, icon in MAG_FAMILIES:
        base_rules = spec.get(fam.upper(), {}).get("rules", "")
        extra = base_rules.split("only one Capacity attachment at a time.", 1)[-1].strip() if base_rules else ""
        for row, values in CAPACITY.items():
            n = values[col]
            rules = MAG_RULE.format(n=n, row=row) + (" " + extra if extra else "")
            if row == "Crossbow":
                rules += CROSSBOW_RULE
            if fam in ("Extended Magazine", "Drum Magazine"):
                rules += (" Otherwise works like the core system's " + fam + ", which replaces capacity instead of "
                          "adding to it; don't install both.")
            sp = {"magazine": n, "icon": icon}
            facts = [("Cost", f"{price:,}eb ({cat})"), ("Attachment slots", str(size)), ("Fits", f"{row} weapons")]
            docs.append(upgrade(f"mag:{fam}:{row}", f"{fam} ({row})", sp, price, size, facts, rules,
                                "Weapons > Weapons in the 2070s > Capacity Chart", folder("Magazines (Capacity Chart)")))
    return docs


def build_mods(parsed, spec):
    docs, folders = [], {}
    parents = nested_parents(parsed)
    for rec in parsed:
        sp = spec[rec["heading"]]
        group = {"ATTACHMENT MODS": "Attachment Mods", "WEAPON MODS": "Weapon Mods"}.get(
            rec["group"], "Invented Weapon Upgrades")
        if group not in folders:
            f = folder_doc("mods", group, len(folders))
            folders[group] = f["_id"]
            docs.append(f)
        section = f"Weapons > Mod Catalog > {group}"
        name = sp.get("name") or title_case(rec["heading"])
        notes = [sp["price_note"]] if sp.get("price_note") else []
        if "invented" in sp:
            dv, material = sp["invented"]
            facts = [("Invented Tech Upgrade", f"Upgrade {dv}; total material cost: {material}")]
            notes.append("Price is 0 because a Tech builds this; the material cost depends on the item upgraded.")
            docs.append(upgrade(rec["heading"], name, sp, 0, 0, facts, sp["rules"], section, folders[group], notes,
                                heading=rec["heading"], section_key="mods",
                                intro_only=rec["heading"] in parents))
            continue
        price, cat = cost_of(rec["stats"].get("Cost"))
        facts = [("Cost", rec["stats"].get("Cost", "")), ("Attachment slots", "0 (Weapon Mod)"),
                 ("Mods", rec["stats"].get("Mods", ""))]
        if "split" in sp:
            for sub_name, sub_price, sub_rule in sp["split"]:
                f = [("Cost", f"{sub_price:,}eb"), *facts[1:]]
                docs.append(upgrade(f"{rec['heading']}:{sub_name}", sub_name, sp, sub_price, 0, f,
                                    f"{sp['rules']} {sub_rule}", section, folders[group], notes,
                                    heading=rec["heading"], section_key="mods",
                                intro_only=rec["heading"] in parents))
            continue
        docs.append(upgrade(rec["heading"], name, sp, sp.get("price", price), 0, facts, sp["rules"], section,
                            folders[group], notes, heading=rec["heading"], section_key="mods",
                            intro_only=rec["heading"] in parents))
    return docs


def build_ammo(parsed, spec):
    docs, folders = [], {}
    for label in ("Ammunition", "Adapter Kits & Casings"):
        f = folder_doc("ammo", label, len(folders))
        folders[label] = f["_id"]
        docs.append(f)
    for rec in parsed:
        sp = spec[rec["heading"]]
        base = sp.get("name") or NAME_FIX.get(rec["heading"]) or title_case(rec["heading"])
        section = "Weapons > Ammunition"
        variants = []
        if sp.get("kind") == "kit":
            for sub_name, sub_price, sub_rule in (sp.get("split") or [[base, sp["price"], ""]]):
                variants.append((sub_name, "custom", "special", 1, sub_price, 10 if "Casings" in sub_name else 1,
                                 (sp["rules"] + " " + sub_rule).strip(), "Adapter Kits & Casings"))
        else:
            multi = len(sp["variety"]) > 1
            for v in sp["variety"]:
                n = f"{base} ({VARIETY_LABEL[v]})" if multi else base
                variants.append((n, v, sp["type"], sp.get("ablation", 1), sp["price"], sp["amount"], sp["rules"],
                                 "Ammunition"))
        for name, variety, atype, ablation, price, amount, rules, fold in variants:
            s = copy.deepcopy(AMMO_TEMPLATE)
            s.update(variety=variety, type=atype, ablationValue=ablation, amount=amount)
            s["price"]["market"] = price
            facts = [("Cost", rec["stats"].get("Cost", "")), ("Stack", f"{amount}")]
            notes = []
            if variety == "custom":
                notes.append("Not loadable ammo: an adapter you apply to other rounds or grenades.")
            s["description"]["value"] = description_html(facts=facts, rules=rules, notes=notes, section=section,
                                                         original=original_text.lookup("ammo", rec["heading"]))
            docs.append(item("ammo", f"{rec['heading']}:{name}", name, "ammo", ICON["ammo"], s, folders[fold]))
    return docs


def build_all():
    parsed = json.load(open(ROOT / "data/upgrades.parsed.json", encoding="utf-8"))
    att = build_attachments(parsed["attachments"], json.load(open(ROOT / "text/attachments.json", encoding="utf-8")))
    mods = build_mods(parsed["mods"], json.load(open(ROOT / "text/mods.json", encoding="utf-8")))
    ammo = build_ammo(parsed["ammo"], json.load(open(ROOT / "text/ammo.json", encoding="utf-8")))
    return {"weapon-attachments": att, "weapon-mods": mods, "ammo": ammo}
