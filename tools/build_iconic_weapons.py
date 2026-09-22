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

An entry builds when Corgo's own text is available for its heading, or when text/iconic_weapons.json
carries a rewrite. His wording is what the description uses when both exist (see common.description_html),
so a rewrite is only needed for the fallback build and for entries that also supply data - stat overrides
under "rec", or a series rule. Anything that has neither is skipped with a count, so the build stays green.
"""
import json
import re
from pathlib import Path
from common import folder_doc, title_case
import build_iconics, build_upgrades, build_weapons, original_text

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


def _has_original(heading):
    """True when Corgo's document carries an entry for this heading, so the item can be built
    from it even with no rewrite in text/iconic_weapons.json."""
    return bool(original_text.enabled() and original_text.lookup("iconic-weapons", heading))


def _has_stat_line(rec):
    """False only when Corgo's damage is something build_weapons cannot read at all.

    "N/A" is fine and common: build() already turns it into the Machine Gun's 2d6 Autofire damage or the
    Shotgun's 3d6 shell damage, which is how the eight N/A weapons in the main catalog are built. What it
    cannot parse is a non-numeric formula - Chaos's "?d6", which is random by design - so that one needs
    an entry supplying a damage under "rec".
    """
    d = rec.get("damage")
    return d in (None, "", "N/A") or bool(re.match(r"\s*\d+d6", str(d)))


def build_all(plan):
    parsed = json.load(open(ROOT / "data/iconic_weapons.parsed.json", encoding="utf-8"))
    spec = json.load(open(ROOT / "text/iconic_weapons.json", encoding="utf-8"))
    base_records = {r["heading"]: r for r in
                    json.load(open(ROOT / "data/weapons.parsed.json", encoding="utf-8"))}
    docs, folders, skipped, needs_stats = [], {}, {}, []

    def folder(label):
        if label not in folders:
            f = folder_doc("iconic-weapons", label, len(folders))
            folders[label] = f["_id"]
            docs.append(f)
        return folders[label]

    for mod in parsed["mods"]:
        rules = spec["mods"].get(mod["heading"])
        if not rules and not _has_original(mod["heading"]):
            skipped["ICONIC WEAPON MODS"] = skipped.get("ICONIC WEAPON MODS", 0) + 1
            continue
        rules = rules or ""
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
            if not _has_original(rec["heading"]):
                skipped[rec["group"]] = skipped.get(rec["group"], 0) + 1
                continue
            entry = {}
        if not _has_stat_line({**rec, **(entry.get("rec", {}) if isinstance(entry, dict) else {})}):
            needs_stats.append(title_case(rec["heading"]))
            continue
        rules = entry if isinstance(entry, str) else entry.get("rules", "")
        over = {} if isinstance(entry, str) else entry
        price = build_iconics.CATEGORY_PRICE.get((rec.get("category") or "").strip(), 0)
        docs.append(build_weapons.build({**rec, **over.get("rec", {})}, rules,
                                        folder(GROUP_FOLDERS[rec["group"]]), plan,
                                        section_key="iconic-weapons", section_label=SECTION,
                                        facts_head=facts_head(rec), price=price,
                                        extra_notes=notes_for(rec, price) + list(over.get("notes", [])),
                                        exotic_note=EXOTIC_NOTE))

    for v in parsed["variants"]:
        entry = spec["variants"].get(v["heading"])
        if entry is None:
            if not _has_original(v["heading"]):
                skipped["VARIANTS"] = skipped.get("VARIANTS", 0) + 1
                continue
            entry = {}
        base = base_records.get(v["base"]) or next(
            (r for h, r in base_records.items() if v["base"] in h), None)
        if base is None and "rec" not in entry:
            if not entry:  # nothing written yet: Corgo's text alone can't supply the stat line
                skipped["VARIANTS (need stats)"] = skipped.get("VARIANTS (need stats)", 0) + 1
                continue
            raise ValueError(f"{v['heading']}: base weapon {v['base']!r} is not in the weapon catalog, so "
                             f"it needs its own stats under \"rec\" in text/iconic_weapons.json")
        rec = {**(base or {}), **entry.get("rec", {}), "heading": v["heading"],
               "category": v["category"], "fabrication": v["fabrication"]}
        price = build_iconics.CATEGORY_PRICE.get(v["category"].replace("V. ", "Very ").strip(), 0)
        head = facts_head(rec)
        head.insert(0, ("Variant of", title_case(v["base"])))
        docs.append(build_weapons.build(rec, entry.get("rules", ""), folder("Variants"), plan,
                                        section_key="iconic-weapons", section_label=SECTION,
                                        facts_head=head, price=price,
                                        extra_notes=notes_for(rec, price) + list(entry.get("notes", []))
                                        # an unwritten series rule is "", which would render as an empty bullet
                                        + [r for r in [spec["series"].get(v["series"], "")] if r],
                                        exotic_note=EXOTIC_NOTE))

    if skipped:
        print("  iconic weapons still to write: " +
              ", ".join(f"{g} {n}" for g, n in sorted(skipped.items())))
    if needs_stats:
        print("  iconic weapons needing a damage stat decided (Corgo gives none): " +
              ", ".join(sorted(needs_stats)))
    return {"iconic-weapons": docs}
