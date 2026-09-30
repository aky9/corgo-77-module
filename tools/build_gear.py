"""Build Corgo's general gear, External Linear Frames (and the SPECTER's two weapons), poisons,
pharmaceuticals, and street drugs for CPR 0.92.4.

Drugs follow the core system's pattern (see its Synthcoke): the item's `consumed` effect ("X Primary") turns on
when a character uses the drug, and "X Addiction" is switched on by hand while addicted. Corgo often suspends
the addiction penalty while the drug is active; for those, "X Addicted Primary" is the primary effect plus a
cancellation of that penalty, to use instead of "X Primary" when an addicted character doses.
"""
import copy
from pathlib import Path
from common import doc_id, title_case, parse_cost, description_html, folder_doc, load_json, SOURCE_BOOK
import build_weapons, entry_text

ROOT = Path(__file__).resolve().parent.parent
ICONS = "systems/cyberpunk-red-core/icons/compendium/"
GEAR_TEMPLATE = {  # key set of CPR 0.92.4 core gear (Airhypo)
    "amount": 1, "brand": "", "concealable": {"concealable": False, "isConcealed": False},
    "description": {"value": ""}, "equipped": "owned", "favorite": False,
    "installedItems": {"allowed": False, "allowedTypes": ["itemUpgrade"], "list": [], "slots": 0, "usedSlots": 0},
    "isElectronic": False, "price": {"market": 0}, "providesHardening": False, "revealed": True,
    "source": {"book": SOURCE_BOOK, "page": 0}, "usage": "toggled",
}
DRUG_TEMPLATE = {  # key set of CPR 0.92.4 core drugs (Synthcoke)
    "amount": 1, "brand": "", "concealable": {"concealable": False, "isConcealed": False}, "consumed": "None",
    "description": {"value": ""}, "equipped": "owned", "favorite": False, "price": {"market": 0}, "revealed": True,
    "source": {"book": SOURCE_BOOK, "page": 0}, "usage": "snorted",
}
SECTION = "Gear, Drugs, & Frames"


def _key(k):
    return k if "." in k else f"system.stats.{k}.value"


def effect(item_id, name, img, changes, disabled=False, situational=False):
    """changes: [key, value] or [key, value, mode] (mode 2 = add, 4 = raise to at least)."""
    eid = doc_id("effect", f"{item_id}:{name}")
    cats, sit, out = {}, {}, []
    for i, ch in enumerate(changes):
        key, value, mode = _key(ch[0]), ch[1], (ch[2] if len(ch) > 2 else 2)
        out.append({"key": key, "mode": mode, "priority": None, "value": str(value)})
        cats[str(i)] = ("stat" if key.startswith("system.stats.") else
                        "combat" if key == "bonuses.deathSavePenalty" else "skill")
        sit[str(i)] = {"isSituational": situational, "onByDefault": False}
    return {"_id": eid, "_key": f"!items.effects!{item_id}.{eid}", "name": name, "img": img, "changes": out,
            "description": "", "disabled": disabled,
            "duration": {k: None for k in ("combat", "rounds", "seconds", "startRound", "startTime", "startTurn",
                                           "turns")},
            "flags": {"cyberpunk-red-core": {"changes": {"cats": cats, "situational": sit}}},
            "statuses": [], "system": {}, "transfer": True, "type": "base"}


def _doc(kind, key, name, itype, img, system, folder, effects=()):
    _id = doc_id(kind, key)
    effs = [e(_id) for e in effects]
    return {"_id": _id, "_key": f"!items!{_id}", "name": name, "type": itype, "img": img, "system": system,
            "effects": effs, "folder": folder, "sort": 0, "ownership": {"default": 0}, "flags": {}}


def gear_item(g, folder, sub, group_heading=None, extra_notes=()):
    s = copy.deepcopy(GEAR_TEMPLATE)
    s["usage"] = g.get("usage", "toggled")
    s["price"]["market"] = g.get("price", parse_cost(g["cost"])[0])
    name = g.get("name") or title_case(g["key"])
    img = ICONS + g.get("icon", "default/Default_Gear.svg")
    notes = list(extra_notes) + list(g.get("notes", []))
    if g.get("price") is not None and "eb" not in g["cost"].split("(")[0]:
        notes.append("Corgo lists no exact price; see Cost.")
    s["description"]["value"] = description_html(
        facts=[("Cost", g["cost"])], notes=notes, section=f"{SECTION} > {sub}",
        entry=entry_text.lookup("gear", g["key"], group_heading, intro_only=g.get("intro_only", False)))
    effects = [lambda iid, e=e: effect(iid, e["name"], img, e["changes"], situational=e.get("situational", False))
               for e in g.get("effects", [])]
    return _doc("gear", g["key"], name, "gear", img, s, folder, effects)


def drug_item(d, folder, sub, kind="Street Drug"):
    s = copy.deepcopy(DRUG_TEMPLATE)
    s["price"]["market"] = d.get("price", parse_cost(d["cost"])[0])
    name = d.get("name") or title_case(d["key"])
    street = kind == "Street Drug"
    img = ICONS + ("gear/generic_street_drugs.svg" if street else "gear/generic_pharmaceuticals.svg")
    primary, addiction, withdrawal = d.get("primary", []), d.get("addiction", []), d.get("withdrawal", [])
    effects, notes = [], list(d.get("notes", []))
    if primary:
        effects.append(lambda iid: effect(iid, f"{name} Primary", img, primary, disabled=True))
        s["consumed"] = f"{name} Primary"
    if addiction or withdrawal:
        effects.append(lambda iid: effect(iid, f"{name} Addiction", img, addiction + withdrawal, disabled=True))
        notes.append(f"While addicted, switch on the \"{name} Addiction\" effect.")
    if withdrawal:
        cancel = [[k, -v] + rest for k, v, *rest in withdrawal]
        effects.append(lambda iid: effect(iid, f"{name} Addicted Primary", img, primary + cancel, disabled=True))
        notes.append(f"When an addicted character doses, use \"{name} Addicted Primary\" instead of the normal "
                     "primary effect; it cancels the withdrawal penalties for the duration.")
    if primary or addiction or withdrawal:
        notes.append("Stat and skill changes are automated; caps, minimums, durations, and everything else are not.")
    s["description"]["value"] = description_html(
        facts=[("Cost", d["cost"]), ("Type", kind)], notes=notes, section=f"{SECTION} > {sub}",
        entry=entry_text.lookup("gear", d["key"]))
    return _doc("drug", d["key"], name, "drug", img, s, folder, effects)


def build_all(plan):
    spec = load_json(ROOT / "text/gear.json")
    docs, folders = [], {}
    for label in ("General Gear", "External Linear Frames", "Poisons", "Pharmaceuticals", "Street Drugs"):
        f = folder_doc("gear", label, len(folders))
        folders[label] = f["_id"]
        docs.append(f)
    for g in spec["general_gear"]:
        docs.append(gear_item(g, folders["General Gear"], "General Gear"))
    for g in spec["frames"]:
        docs.append(gear_item(g, folders["External Linear Frames"], "External Linear Frames"))
    for w in spec["frame_weapons"]:
        rec = {**w, "special": "", "notes": [], "group": "External Linear Frames"}
        doc = build_weapons.build(rec, folders["External Linear Frames"], plan,
                                  section_key="gear", section_label=f"{SECTION} > External Linear Frames",
                                  extra_notes=w.get("notes", ()))
        doc["system"]["price"]["market"] = w.get("price", 0)
        docs.append(doc)
    for p in spec["poisons"]:
        docs.append(gear_item({**p, "usage": "carried"}, folders["Poisons"], "Consumables > Poisons",
                              group_heading="POISONS"))
    for p in spec["pharmaceuticals"]:
        docs.append(drug_item(p, folders["Pharmaceuticals"], "Consumables > Pharmaceuticals", "Pharmaceutical"))
    for d in spec["street_drugs"]:
        docs.append(drug_item(d, folders["Street Drugs"], "Consumables > Street Drugs"))
    return {"gear": docs}
