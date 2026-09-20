"""Build Corgo's Cyberware, Operating Systems and Cyberware Alternatives for CPR 0.92.4.

Three document types come out of this chapter, matching how the core system models the same things:

- `cyberware` items for anything installed in (or, for the Alternatives, worn on) the body. Core's
  convention, which we follow: a foundational piece has `isFoundational: true`, `size: 0` and
  `installedItems.slots` = the Option Slots it provides; an option has `isFoundational: false` and
  `size` = the Option Slots it consumes. 0.92.4 only offers install targets whose cyberware `type`
  matches the option being installed (`cpr-actor.js installCyberware`), so a piece whose Corgo slot
  costs cross categories is typed where its slots have to be usable, and the item's Foundry notes say
  so - see Advanced Neural Link and Integrated Netstation in text/cyberware.json.
- `itemUpgrade` items of type "cyberware" for Corgo's "X Cyberware Enhancement" entries and for the
  Operating Systems, which he says work identically to enhancements. `size` is 0: enhancements take no
  Option Slot. These carry no Active Effects, only `modifiers`: `usage: "installed"` is not a legal
  usage for an itemUpgrade, so an effect on one would apply from inside the user's inventory, whether or
  not it was installed. Bonuses a modifier can't express (extra slots and magazine capacity can) stay in
  the rules text, with a note pointing at the parent item.
- `cyberdeck` items for the five decks the Cyberdeck Port Operating Systems come with, since the OS is
  no use without the deck it restricts the port to.

Active Effects on cyberware items follow the core's split: passive ware is `usage: "installed"` with a
plain effect, so it applies exactly while installed (core's Kerenzikov, Pain Editor); activated ware is
`usage: "toggled"` with the change flagged situational, so it shows as a toggle in the roll dialog
(core's Sandevistan).

Not built, at Kane's direction: 2070s Full Body Conversions, the Militech Centaur Exo, and the
Corpochrome variants - Corpochrome is written up as a rule in module/README.md instead.
"""
import copy, json, re
from pathlib import Path
from common import doc_id, title_case, parse_cost, description_html, folder_doc, SOURCE_BOOK
import build_upgrades, original_text

ROOT = Path(__file__).resolve().parent.parent
ICONS = "systems/cyberpunk-red-core/icons/compendium/"
DEFAULT_ICON = "default/Default_Cyberware.svg"

CYBERWARE_TEMPLATE = {  # key set of CPR 0.92.4 core cyberware (e.g. Cyberarm, Big Knucks)
    "ammoVariety": [], "attackmod": 0, "brand": "", "canIgnoreArmor": True,
    "concealable": {"concealable": False, "isConcealed": False}, "core": False, "critFailEffect": "jammed",
    "damage": "1d6", "description": {"value": ""}, "dvTable": "", "favorite": False,
    "fireModes": {"autoFire": 0, "suppressiveFire": False}, "humanityLoss": {"roll": "1d6", "static": 3},
    "ignoreArmorPercent": 50, "ignoreBelowSP": 0, "installLocation": "mall",
    "installedItems": {"allowed": False, "allowedTypes": ["itemUpgrade"], "list": [], "slots": 0, "usedSlots": 0},
    "isElectronic": True, "isFoundational": False, "isRanged": False, "isWeapon": False,
    "magazine": {"ammoData": None, "max": 0, "value": 0}, "price": {"market": 0}, "providesHardening": False,
    "revealed": True, "rof": 1, "size": 1, "source": {"book": SOURCE_BOOK, "page": 0}, "type": "cyberwareInternal",
    "unarmedAutomaticCalculation": True, "usage": "installed", "usesType": "magazine", "weaponSkill": "Archery",
    "weaponType": "assaultRifle",
}
CYBERDECK_TEMPLATE = {  # key set of CPR 0.92.4 core cyberdecks
    "brand": "", "concealable": {"concealable": False, "isConcealed": False}, "description": {"value": ""},
    "equipped": "owned", "favorite": False, "installLocation": "mall",
    "installedItems": {"allowed": True, "allowedTypes": ["itemUpgrade", "program"], "list": [], "slots": 7,
                       "usedSlots": 0},
    "isElectronic": True, "price": {"market": 0}, "providesHardening": False, "quality": "standard", "size": 1,
    "source": {"book": SOURCE_BOOK, "page": 0},
}
ARMOR_TEMPLATE = {  # cyberware that armors the wearer needs an armor item too; see NANO-PLATING
    "bodyLocation": {"ablation": 0, "sp": 0}, "brand": "",
    "concealable": {"concealable": False, "isConcealed": False}, "description": {"value": ""}, "equipped": "owned",
    "favorite": False, "headLocation": {"ablation": 0, "sp": 0},
    "installedItems": {"allowed": False, "allowedTypes": ["itemUpgrade"], "list": [], "slots": 0, "usedSlots": 0},
    "isBodyLocation": True, "isElectronic": False, "isHeadLocation": True, "isShield": False, "penalty": 0,
    "price": {"market": 0}, "providesHardening": False, "revealed": True, "shieldHitPoints": {"max": 0, "value": 0},
    "source": {"book": SOURCE_BOOK, "page": 0}, "usage": "equipped",
}

# Chapter and "## " subsection -> (pack, folder label, section label for the description footer).
SECTION_LABELS = {
    "FASHIONWARE": "Cyberware > Fashionware",
    "NEURALWARE": "Cyberware > Neuralware",
    "CYBEROPTICS": "Cyberware > Cyberoptics",
    "INTERNAL BODY CYBERWARE": "Cyberware > Internal Body Cyberware",
    "EXTERNAL BODY CYBERWARE": "Cyberware > External Body Cyberware",
    "CYBERARMS": "Cyberware > Cyberarms",
    "CYBERLEGS": "Cyberware > Cyberlegs",
    "BORGWARE": "Cyberware > Borgware",
    "BERSERK OPERATING SYSTEMS": "Operating Systems > Berserk Operating Systems",
    "CYBERDECK PORT OPERATING SYSTEMS": "Operating Systems > Cyberdeck Port Operating Systems",
    "SANDEVISTAN OPERATING SYSTEMS": "Operating Systems > Sandevistan Operating Systems",
    "BATTLE/SMART GLOVES": "Cyberware Alternatives > Battle/Smart Gloves",
    "SMART OPTICS": "Cyberware Alternatives > Smart Optics",
}
FOLDERS = {  # folder label per subsection, in the order the folders should sort
    "FASHIONWARE": "Fashionware", "NEURALWARE": "Neuralware", "CYBEROPTICS": "Cyberoptics",
    "INTERNAL BODY CYBERWARE": "Internal Body Cyberware", "EXTERNAL BODY CYBERWARE": "External Body Cyberware",
    "CYBERARMS": "Cyberarms", "CYBERLEGS": "Cyberlegs", "BORGWARE": "Borgware",
    "BERSERK OPERATING SYSTEMS": "Berserk Operating Systems",
    "CYBERDECK PORT OPERATING SYSTEMS": "Cyberdeck Port Operating Systems",
    "SANDEVISTAN OPERATING SYSTEMS": "Sandevistan Operating Systems",
    "BATTLE/SMART GLOVES": "Battle & Smart Gloves", "SMART OPTICS": "Smart Optics",
}
TYPE_LABEL = {"fashionware": "Fashionware", "neuralWare": "Neuralware", "cyberEye": "Cybereye",
              "cyberAudioSuite": "Cyberaudio Suite", "cyberArm": "Cyberarm", "cyberLeg": "Cyberleg",
              "cyberwareInternal": "Internal Body Cyberware", "cyberwareExternal": "External Body Cyberware",
              "borgware": "Borgware"}
INSTALL_LABEL = {"mall": "Mall", "clinic": "Clinic", "hospital": "Hospital", "notApplicable": "N/A"}
# Active Effect key -> the category flag CPR stores alongside the change (see CPR.activeEffectKeys).
COMBAT_KEYS = {"bonuses.initiative", "bonuses.maxHp", "bonuses.maxHumanity", "bonuses.deathSavePenalty",
               "bonuses.aimedShot", "bonuses.singleShot", "bonuses.melee", "bonuses.ranged", "bonuses.autofire",
               "bonuses.suppressive", "bonuses.hands", "bonuses.run", "bonuses.walk",
               "bonuses.universalAttack", "bonuses.universalDamage", "bonuses.universalDamageReduction"}


def icon_path(stem):
    if not stem:
        return ICONS + DEFAULT_ICON
    return ICONS + (stem if "/" in stem else f"cyberware/{stem}") + ".svg"


def _key(k):
    return k if "." in k else f"system.stats.{k}.value"


def effect(item_id, name, img, changes, situational=False, on_by_default=False):
    """changes: [key, value] or [key, value, mode] (2 = add, 3 = cap at, 4 = raise to at least, 5 = set)."""
    eid = doc_id("effect", f"{item_id}:{name}")
    cats, sit, out = {}, {}, []
    for i, ch in enumerate(changes):
        key, value, mode = _key(ch[0]), ch[1], (ch[2] if len(ch) > 2 else 2)
        out.append({"key": key, "mode": mode, "priority": None, "value": str(value)})
        cats[str(i)] = "stat" if key.startswith("system.stats.") else "combat" if key in COMBAT_KEYS else "skill"
        sit[str(i)] = {"isSituational": situational, "onByDefault": on_by_default}
    return {"_id": eid, "_key": f"!items.effects!{item_id}.{eid}", "name": name, "img": img, "changes": out,
            "description": "", "disabled": False,
            "duration": {k: None for k in ("combat", "rounds", "seconds", "startRound", "startTime", "startTurn",
                                           "turns")},
            "flags": {"cyberpunk-red-core": {"changes": {"cats": cats, "situational": sit}}},
            "statuses": [], "system": {}, "transfer": True, "type": "base"}


def _doc(kind, key, name, itype, img, system, folder, effects=()):
    _id = doc_id(kind, key)
    return {"_id": _id, "_key": f"!items!{_id}", "name": name, "type": itype, "img": img, "system": system,
            "effects": [e(_id) for e in effects], "folder": folder, "sort": 0, "ownership": {"default": 0},
            "flags": {}}


def parse_hl(raw):
    """'14 (4d6)' -> (14, '4d6'); '7 (4d6/2 [Round Up])' -> (7, '2d6'); 'N/A' -> (0, '0')

    The static value is what Corgo prints. The roll has to be a plain dice formula: CPR builds its
    humanity-loss roll card from `roll.terms[0].results`, which only exists on a DiceTerm, so a function
    like ceil() throws and shows no card (core only ever uses 0, 1d3, 1d6, 2d6 and 4d6). "4d6/2 round up"
    therefore becomes 2d6 - same minimum, maximum and mean, a flatter spread - and the item says so.
    Items whose line is missing or N/A are given an explicit 0 in text/cyberware.json.
    """
    if not raw:
        return None
    raw = raw.replace("hi", "").strip()  # a stray typo on Dancer Optics in the source document
    static, _, rest = raw.partition("(")
    roll = rest.rstrip(")").strip()
    if "Round Up" in roll:
        dice = roll.split("[")[0].strip()
        m = re.fullmatch(r"(\d+)d(\d+)/(\d+)", dice)
        if m and int(m.group(1)) % int(m.group(3)) == 0:
            roll = f"{int(m.group(1)) // int(m.group(3))}d{m.group(2)}"
        else:
            roll = dice
    try:
        static = int(static.strip())
    except ValueError:
        return None
    return static, (roll or str(static))


def cyberware_item(key, spec, rec, folder, section, intro_only=False):
    s = copy.deepcopy(CYBERWARE_TEMPLATE)
    stats = rec["stats"]
    price = spec.get("price", parse_cost(stats.get("Cost"))[0])
    hl = spec.get("hl") or parse_hl(stats.get("Humanity Loss")) or (0, "0")
    s["price"]["market"] = price
    s["humanityLoss"] = {"static": hl[0], "roll": str(hl[1])}
    s["type"] = spec["type"]
    s["size"] = spec.get("size", 1)
    s["isFoundational"] = spec.get("foundational", False)
    s["installLocation"] = spec.get("install") or (stats.get("Install", "mall") or "mall").lower()
    s["usage"] = spec.get("usage", "installed")
    s["isElectronic"] = spec.get("electronic", True)
    s["providesHardening"] = spec.get("hardening", False)
    s["concealable"]["concealable"] = spec.get("concealable", False)
    s["installedItems"]["slots"] = spec.get("slots", 0)
    s["installedItems"]["allowed"] = spec.get("install_allowed", False)
    s["installedItems"]["allowedTypes"] = spec.get("allowed_types", ["itemUpgrade"])
    w = spec.get("weapon")
    if w:
        s["isWeapon"] = True
        s.update(damage=w["damage"], rof=w["rof"], weaponType=w["weaponType"], weaponSkill=w["weaponSkill"],
                 isRanged=w.get("ranged", False), dvTable=w.get("dv_table", ""), ammoVariety=w.get("ammo", []))
        s["fireModes"]["autoFire"] = w.get("autofire", 0)
        s["magazine"]["max"] = w.get("magazine", 0)
        if w.get("ammo"):
            s["installedItems"].update(allowed=True, allowedTypes=["ammo"])

    facts = [("Cost", stats.get("Cost", ""))]
    if spec["type"] in TYPE_LABEL:
        facts.append(("Type", TYPE_LABEL[spec["type"]] + (" (Foundational)" if s["isFoundational"] else "")))
    facts.append(("Install", INSTALL_LABEL[s["installLocation"]]))
    facts.append(("Humanity Loss", f"{hl[0]} ({hl[1]})" if hl[0] else "None"))
    facts.append(("Option Slots", f"uses {s['size']}" + (f", provides {spec['slots']}" if spec.get("slots") else "")))
    notes = list(spec.get("notes", []))
    name = spec.get("name") or title_case(key)
    img = icon_path(spec.get("icon"))
    effects = [lambda iid, e=e: effect(iid, e.get("name", name), img, e["changes"],
                                       situational=e.get("situational", False),
                                       on_by_default=e.get("on_by_default", False))
               for e in spec.get("effects", [])]

    docs = []
    variants = spec.get("split") or [[name, price, ""]]
    for sub_name, sub_price, sub_rule in variants:
        sub_price = price if sub_price is None else sub_price
        sub = copy.deepcopy(s)
        sub["price"]["market"] = sub_price
        f = [("Cost", f"{sub_price:,}eb" if spec.get("split") else stats.get("Cost", "")), *facts[1:]]
        sub["description"]["value"] = description_html(
            facts=f, rules=" ".join(x for x in (spec["rules"], sub_rule) if x), notes=notes, section=section,
            original=original_text.lookup(rec["chapter"], spec.get("heading", key), intro_only=intro_only))
        docs.append(_doc("cyberware", f"{key}:{sub_name}", sub_name, "cyberware", img, sub, folder, effects))

    armor = spec.get("armor")
    if armor:  # the SP half of a piece of cyberware that armors the wearer
        a = copy.deepcopy(ARMOR_TEMPLATE)
        a["bodyLocation"]["sp"] = a["headLocation"]["sp"] = armor["sp"]
        a["description"]["value"] = description_html(
            facts=[("Covers", "Body and Head"), ("SP", str(armor["sp"])), ("Armor Penalty", "none")],
            rules=f"The armor provided by {name}. Equip this alongside the cyberware item.",
            notes=["Ablation this armor takes is reduced by 1 (minimum 0), and it repairs 1 lost SP at the end of "
                   "any day it loses none. Both are applied by hand."],
            section=section)
        docs.append(_doc("armor", f"{key}:armor", armor["name"], "armor", img, a, folder))
    return docs


def enhancement_item(key, spec, rec, folder, section, group_rule=None, intro_only=False):
    """An "X Cyberware Enhancement" or an Operating System: an itemUpgrade of type "cyberware", size 0."""
    stats = rec["stats"]
    price = spec.get("price", parse_cost(stats.get("Cost"))[0])
    name = spec.get("name") or title_case(key)
    notes = list(spec.get("notes", []))
    if group_rule:
        notes.append(group_rule)
    docs = []
    variants = spec.get("split") or [[name, price, ""]]
    for sub_name, sub_price, sub_rule in variants:
        sub_price = price if sub_price is None else sub_price
        facts = [("Cost", f"{sub_price:,}eb" if spec.get("split") else stats.get("Cost", "")),
                 ("Enhances", spec["enhances"]), ("Option Slots", "0 (Cyberware Enhancement)")]
        d = build_upgrades.upgrade(f"cyberware:{key}:{sub_name}", sub_name,
                                   {"mods": spec.get("mods", {})}, sub_price, 0, facts,
                                   " ".join(x for x in (spec["rules"], sub_rule) if x), section, folder,
                                   notes=notes, heading=spec.get("heading", key), section_key=rec["chapter"],
                                   intro_only=intro_only)
        d["system"]["type"] = "cyberware"
        d["system"]["isElectronic"] = spec.get("electronic", False)
        d["img"] = icon_path(spec.get("icon"))
        docs.append(d)
    return docs


def cyberdeck_item(key, spec, rec, folder, section):
    s = copy.deepcopy(CYBERDECK_TEMPLATE)
    s["price"]["market"] = spec.get("price", 0)
    s["installedItems"]["slots"] = spec["slots"]
    name = spec.get("name") or title_case(key)
    notes = list(spec.get("notes", []))
    notes.append("Comes with the Operating System that requires it, so its price is 0 here.")
    s["description"]["value"] = description_html(
        facts=[("Cost", "Provided with the Operating System"), ("Slots", str(spec["slots"]))],
        rules=spec["rules"], notes=notes, section=section,
        original=original_text.lookup(rec["chapter"], spec.get("heading", key)))
    return [_doc("cyberdeck", key, name, "cyberdeck", ICONS + "default/Default_Cyberdeck.svg", s, folder)]


def build_all():
    spec = json.load(open(ROOT / "text/cyberware.json", encoding="utf-8"))
    records = json.load(open(ROOT / "data/cyberware.parsed.json", encoding="utf-8"))
    parsed = {r["heading"]: r for r in records}
    # An entry with nested "#### " entries under it (Gorilla Arm -> Limiter Removal, and so on) must stop at
    # the first sub-heading when we pull Corgo's wording, or the parent would swallow its children's text.
    has_children = {r["parent"] for r in records if r["parent"]}
    packs = {"cyberware": [], "cyberware-upgrades": [], "operating-systems": []}
    folders = {}

    def folder(pack, label):
        if (pack, label) not in folders:
            f = folder_doc(pack, label, len([1 for p, _ in folders if p == pack]))
            folders[(pack, label)] = f["_id"]
            packs[pack].append(f)
        return folders[(pack, label)]

    for key, sp in spec["items"].items():
        rec = parsed[sp.get("heading", key)]
        group = rec["group"]
        section = SECTION_LABELS[group]
        label = FOLDERS[group]
        intro_only = rec["heading"] in has_children
        if sp["kind"] == "enhancement":
            pack = "operating-systems" if rec["chapter"] == "operating-systems" else "cyberware-upgrades"
            rule = spec["os_group_rule"] if rec["chapter"] == "operating-systems" else None
            docs = enhancement_item(key, sp, rec, folder(pack, label), section, group_rule=rule,
                                    intro_only=intro_only)
        elif sp["kind"] == "cyberdeck":
            pack = "operating-systems"
            docs = cyberdeck_item(key, sp, rec, folder(pack, "Cyberdecks (from an OS)"), section)
        else:
            pack = "cyberware"
            docs = cyberware_item(key, sp, rec, folder(pack, label), section, intro_only=intro_only)
        packs[pack] += docs
    return packs
