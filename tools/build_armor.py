"""Build Corgo's armor, iconic armor, Gun Shields, and armor/shield upgrades for CPR 0.92.4.

CPR applies one Armor Penalty to REF, DEX, and MOVE, and only the worst penalty among worn pieces counts.
Corgo sometimes gives different penalties per stat (e.g. -1 REF, -2 DEX/MOVE). The item's penalty is set to
the worst of the three and the description gives the exact split. Per-stat Active Effects were rejected:
they would stack across worn pieces (e.g. Max-Helm + Max-Vest), which CPR's penalty rule doesn't.
"""
import copy, json
from pathlib import Path
from common import doc_id, title_case, parse_cost, description_html, folder_doc, SOURCE_BOOK
import build_upgrades, original_text

ROOT = Path(__file__).resolve().parent.parent
ICONS = "systems/cyberpunk-red-core/icons/compendium/"
ARMOR_TEMPLATE = {  # key set of CPR 0.92.4 core armor (Flak (Body))
    "bodyLocation": {"ablation": 0, "sp": 0}, "brand": "", "concealable": {"concealable": False, "isConcealed": False},
    "description": {"value": ""}, "equipped": "owned", "favorite": False, "headLocation": {"ablation": 0, "sp": 0},
    "installedItems": {"allowed": True, "allowedTypes": ["itemUpgrade"], "list": [], "slots": 3, "usedSlots": 0},
    "isBodyLocation": False, "isElectronic": False, "isHeadLocation": False, "isShield": False, "penalty": 0,
    "price": {"market": 0}, "providesHardening": False, "revealed": True, "shieldHitPoints": {"max": 0, "value": 0},
    "source": {"book": SOURCE_BOOK, "page": 0}, "usage": "equipped",
}
STATS = ("REF", "DEX", "MOVE")


def icon(spec, loc):
    stem = spec.get("icon")
    if stem == "bodyweight_suit":
        return ICONS + "armor/bodyweight_suit.svg"
    if stem:
        return f"{ICONS}armor/{stem}_{loc}.svg"
    return ICONS + ("default/Default_Armor_Head.svg" if loc == "head" else "default/Default_Armor.svg")


def effect(item_id, item_name, img, key, value, idx):
    eid = doc_id("effect", f"{item_id}:{key}:{idx}")
    return {"_id": eid, "_key": f"!items.effects!{item_id}.{eid}", "name": item_name, "img": img,
            "changes": [{"key": key, "mode": 2, "priority": None, "value": str(value)}], "description": "",
            "disabled": False, "duration": {k: None for k in ("combat", "rounds", "seconds", "startRound",
                                                               "startTime", "startTurn", "turns")},
            "flags": {"cyberpunk-red-core": {"changes": {"cats": {"0": "skill"},
                                                         "situational": {"0": {"isSituational": False,
                                                                               "onByDefault": False}}}}},
            "statuses": [], "system": {}, "transfer": True, "type": "base"}


def penalty_text(p):
    if not any(p):
        return "none"
    if len(set(p)) == 1:
        return f"-{p[0]} to REF, DEX, and MOVE"
    return ", ".join(f"-{v} {s}" for v, s in zip(p, STATS))


def armor_item(spec, loc, name, folder, section, section_key="armor"):
    s = copy.deepcopy(ARMOR_TEMPLATE)
    price = spec.get("price") or parse_cost(spec["cost"])[0]
    s["price"]["market"] = price
    s["isElectronic"] = bool(spec.get("electronic"))
    if loc in ("body", "both"):
        s["isBodyLocation"], s["bodyLocation"]["sp"] = True, spec["sp"]
    if loc in ("head", "both"):
        s["isHeadLocation"], s["headLocation"]["sp"] = True, spec["sp"]
    p = spec["penalty"]
    s["penalty"] = max(p)
    notes = []
    if len(set(p)) > 1:
        notes.append(f"Corgo's penalty is {penalty_text(p)}. The sheet applies one penalty to all three stats, so it "
                     f"uses -{max(p)}; add the difference back by hand for the lighter stat(s).")
    where = {"body": "Body", "head": "Head", "both": "Body and Head (one piece)"}[loc]
    facts = [("Cost", spec["cost"]), ("Covers", where), ("SP", str(spec["sp"])), ("Armor Penalty", penalty_text(p))]
    img = icon(spec, "head" if loc == "head" else "body")
    s["description"]["value"] = description_html(facts=facts, rules=spec["rules"], notes=notes, section=section,
                                                 original=original_text.lookup(section_key, spec["key"]))
    _id = doc_id("armor", f"{spec['key']}:{loc}")
    effects = [effect(_id, name, img, k, v, i) for i, (k, v) in enumerate(spec.get("effects", []))]
    return {"_id": _id, "_key": f"!items!{_id}", "name": name, "type": "armor", "img": img, "system": s,
            "effects": effects, "folder": folder, "sort": 0, "ownership": {"default": 0}, "flags": {}}


def build_armor_pack(spec):
    docs, folders = [], {}
    for label in ("Armor", "Iconic Armor", "Gun Shields"):
        f = folder_doc("armor", label, len(folders))
        folders[label] = f["_id"]
        docs.append(f)
    for a in spec["armor"]:
        base = a.get("name") or title_case(a["key"])
        section = "Armor & Fashion > Armor Catalog"
        if a["loc"] == "pair":
            for loc in ("body", "head"):
                docs.append(armor_item(a, loc, f"{base} ({loc.title()})", folders["Armor"], section))
        else:
            docs.append(armor_item(a, a["loc"], base, folders["Armor"], section))
    for a in spec["iconic"]:
        docs.append(armor_item(a, a["loc"], a["name"], folders["Iconic Armor"], "Iconics > Iconic Armor", "iconic-armor"))
    for g in spec["gun_shields"]:
        s = copy.deepcopy(ARMOR_TEMPLATE)
        s.update(isShield=True, price={"market": g["price"]}, shieldHitPoints={"max": g["hp"], "value": g["hp"]})
        s["description"]["value"] = description_html(
            facts=[("Cost", g["cost"]), ("Shield HP", str(g["hp"]))], rules=spec["gun_shield_rules"] + g["extra"],
            notes=[], section="Weapons > Attachment Catalog > Rails & Mounts > Gun Shield Mount")
        _id = doc_id("armor", g["name"])
        docs.append({"_id": _id, "_key": f"!items!{_id}", "name": g["name"], "type": "armor",
                     "img": ICONS + "armor/bullet_proof_shield.svg", "system": s, "effects": [],
                     "folder": folders["Gun Shields"], "sort": 0, "ownership": {"default": 0}, "flags": {}})
    return docs


def build_upgrade_pack(spec):
    docs, folders = [], {}
    groups = [("Armor Enhancements & Kits", spec["enhancements"], spec["enhancement_rules"],
               "Armor & Fashion > Armor Enhancements & Kits"),
              ("Shield Attachments & Enhancements", spec["shield_upgrades"], spec["shield_rules"],
               "Armor & Fashion > Shields")]
    for label, entries, group_rule, section in groups:
        f = folder_doc("armor-upgrades", label, len(folders))
        folders[label] = f["_id"]
        docs.append(f)
        for e in entries:
            name = title_case(e["key"])
            variants = e.get("split") or [[name, e.get("price", parse_cost(e["cost"])[0]), ""]]
            for sub_name, price, sub_rule in variants:
                facts = [("Cost", e["cost"] if not e.get("split") else f"{price:,}eb"), ("Type", e["kind"]),
                         ("Attachment slots", "0")]
                rules = " ".join(x for x in (e["rules"], sub_rule) if x)
                d = build_upgrades.upgrade(f"armor:{e['key']}:{sub_name}", sub_name, {"mods": e.get("mods", {})},
                                           price, 0, facts, rules, section, folders[label],
                                           notes=[group_rule], heading=e["key"],
                                           section_key="shields" if "Shield" in label else "armor")
                d["system"]["type"] = e.get("type", "armor")
                d["img"] = ICONS + ("armor/bullet_proof_shield.svg" if "Shield" in label else "default/Default_Armor.svg")
                docs.append(d)
    return docs


def build_all():
    spec = json.load(open(ROOT / "text/armor.json", encoding="utf-8"))
    return {"armor": build_armor_pack(spec), "armor-upgrades": build_upgrade_pack(spec)}
