"""Build Corgo's Iconic Weapons for CPR 0.92.4.

The Iconic stat block is the weapon catalog's, so this reuses build_weapons.build rather than repeating
it: `split_class` already reads the "Iconic" prefix (and treats it as Exotic, which is Corgo's own rule -
no Non-Basic Ammunition and no Attachment Slots unless an entry says otherwise), and `build` takes the
facts head, price and extra notes it needs for a chapter that prices by Category and Fabrication instead
of a Cost. Prices come from build_iconics.CATEGORY_PRICE, so an Iconic weapon and an Iconic implant of the
same tier agree.

Three kinds of document:

- the four Iconic Weapon Mods, as `itemUpgrade` of type "weapon" with an `Eligible` fact saying what they
  fit, since Corgo defines them by eligibility rather than by a named parent;
- the 89 Iconic weapons, one `weapon` each, foldered by class group;
- the 22 variant series members, each a `weapon` built from the parsed stats of the base weapon it names
  (a weapon this module already ships) plus the series' shared rule, the way build_weapons handles the
  Ironfake and Darkhound variants.

Authoring status is tracked by what text/iconic_weapons.json covers: a group with no rewritten text yet is
skipped with a count, so the build stays green while the chapter is written a group at a time.
"""
import json
from pathlib import Path
from common import folder_doc, title_case
import build_iconics, build_upgrades, build_weapons

ROOT = Path(__file__).resolve().parent.parent
SECTION = "Becoming Iconic > Iconic Weapons"
GROUP_FOLDERS = {
    "MELEE WEAPONS": "Melee Weapons", "PISTOLS": "Pistols", "SUBMACHINE GUNS (SMGs)": "SMGs",
    "SHOTGUNS": "Shotguns", "ASSAULT RIFLES": "Assault Rifles", "MACHINE GUNS": "Machine Guns",
    "SNIPER RIFLES": "Sniper Rifles",
}
ICONIC_NOTE = build_iconics.ICONIC_NOTE
# Corgo's chapter rule, worth repeating on every weapon since it changes what you can bolt on.
EXOTIC_NOTE = ("Iconic weapons follow the Exotic weapon rules: no Non-Basic Ammunition and no Attachment "
               "Slots unless this entry says otherwise.")


def facts_head(rec):
    out = [("Category", rec.get("category") or "N/A"),
           ("Fabrication", rec.get("fabrication") or "N/A")]
    if rec.get("eligible"):
        out.append(("Eligible", rec["eligible"]))
    return out


def notes_for(rec, price):
    notes = [ICONIC_NOTE]
    if price:
        cat = (rec.get("category") or "").split("(")[0].strip()
        notes.append(f"The price is the {cat} benchmark, for working out repairs and Tech Upgrades. "
                     f"Iconics can't be bought.")
    return notes


def build_all(plan):
    parsed = json.load(open(ROOT / "data/iconic_weapons.parsed.json", encoding="utf-8"))
    spec = json.load(open(ROOT / "text/iconic_weapons.json", encoding="utf-8"))
    base_records = {r["heading"]: r for r in
                    json.load(open(ROOT / "data/weapons.parsed.json", encoding="utf-8"))}
    docs, folders, skipped = [], {}, {}

    def folder(label):
        if label not in folders:
            f = folder_doc("iconic-weapons", label, len(folders))
            folders[label] = f["_id"]
            docs.append(f)
        return folders[label]

    for mod in parsed["mods"]:
        rules = spec["mods"].get(mod["heading"])
        if not rules:
            skipped["ICONIC WEAPON MODS"] = skipped.get("ICONIC WEAPON MODS", 0) + 1
            continue
        price = build_iconics.CATEGORY_PRICE.get((mod.get("category") or "").strip(), 0)
        d = build_upgrades.upgrade(f"iconic-mod:{mod['heading']}", title_case(mod["heading"]), {}, price, 0,
                                   facts_head(mod), rules, SECTION, folder("Weapon Mods"),
                                   notes=notes_for(mod, price), heading=mod["heading"],
                                   section_key="iconic-weapons")
        d["system"]["type"] = "weapon"
        docs.append(d)

    for rec in parsed["weapons"]:
        entry = spec["weapons"].get(rec["heading"])
        if entry is None:
            skipped[rec["group"]] = skipped.get(rec["group"], 0) + 1
            continue
        rules = entry if isinstance(entry, str) else entry.get("rules", "")
        over = {} if isinstance(entry, str) else entry
        price = build_iconics.CATEGORY_PRICE.get((rec.get("category") or "").strip(), 0)
        docs.append(build_weapons.build({**rec, **over.get("rec", {})}, rules,
                                        folder(GROUP_FOLDERS[rec["group"]]), plan,
                                        section_key="iconic-weapons", section_label=SECTION,
                                        facts_head=facts_head(rec), price=price,
                                        extra_notes=notes_for(rec, price), exotic_note=EXOTIC_NOTE))

    for v in parsed["variants"]:
        entry = spec["variants"].get(v["heading"])
        if entry is None:
            skipped["VARIANTS"] = skipped.get("VARIANTS", 0) + 1
            continue
        base = base_records.get(v["base"]) or next(
            (r for h, r in base_records.items() if v["base"] in h), None)
        if base is None and "rec" not in entry:
            raise ValueError(f"{v['heading']}: base weapon {v['base']!r} is not in the weapon catalog, so "
                             f"it needs its own stats under \"rec\" in text/iconic_weapons.json")
        rec = {**(base or {}), **entry.get("rec", {}), "heading": v["heading"],
               "category": v["category"], "fabrication": v["fabrication"]}
        price = build_iconics.CATEGORY_PRICE.get(v["category"].replace("V. ", "Very ").strip(), 0)
        head = facts_head(rec)
        head.insert(0, ("Variant of", title_case(v["base"])))
        docs.append(build_weapons.build(rec, entry["rules"], folder("Variants"), plan,
                                        section_key="iconic-weapons", section_label=SECTION,
                                        facts_head=head, price=price,
                                        extra_notes=notes_for(rec, price) +
                                        [spec["series"].get(v["series"], "")],
                                        exotic_note=EXOTIC_NOTE))

    if skipped:
        print("  iconic weapons still to write: " +
              ", ".join(f"{g} {n}" for g, n in sorted(skipped.items())))
    return {"iconic-weapons": docs}
