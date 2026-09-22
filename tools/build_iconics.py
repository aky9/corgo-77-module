"""Build Corgo's Iconic Cyberware and Iconic Gear for CPR 0.92.4.

Iconics are an optional item class of Corgo's own: they can't be bought, can't be destroyed without the
player's say-so, and are found through play rather than shopping. CPR has no flag for any of that, so an
Iconic is an ordinary item of its type, kept in its own pack, carrying the chapter's rules in its notes.

Two facts replace Cost. `Category` is the price tier, which is what CP:R uses for repairs and Tech Upgrades,
so `price.market` gets that tier's eurodollar benchmark (CATEGORY_PRICE below) and every item says in its
notes that the figure is a benchmark rather than a purchase price. `Fabrication` (DV, materials, time) is
shown as written.

Everything else follows the conventions in build_cyberware: cyberware items for what is installed in the
body, `itemUpgrade` of type "cyberware" for the entries Corgo labels a Cyberware Enhancement (Rara Avis) or
an Operating System (Militech 'Apogee'), `cyberdeck` items for the two Iconic decks, and `drug` items for
the three Iconic drugs, whose Primary and Addiction effects are built the way build_gear builds a street
drug. The chapter states that Iconic Cyberware Options take no Option Slot unless an entry says otherwise,
so size defaults to 0; Quantum Tuner, Isometric Stabilizer, the faceplate, Chitin and the Higurashi blades
say otherwise and are given theirs in text/iconics.json.

Not built here: Iconic Armor, which is one item and already in text/armor.json's "iconic" list; Iconic
Weapons, which is its own chapter and its own pass; and Iconic Vehicles, which waits for the vehicle
chapters, since the `vehicle` field set is untouched.
"""
import copy, json
from pathlib import Path
from common import doc_id, title_case, description_html, folder_doc
import build_cyberware, build_gear, build_upgrades, original_text

ROOT = Path(__file__).resolve().parent.parent
# CP:R price tiers. Iconics can't be bought; this is the benchmark the tier implies, which is what repair
# and Tech Upgrade costs are worked out from.
CATEGORY_PRICE = {"Cheap": 10, "Everyday": 20, "Costly": 50, "Premium": 100, "Expensive": 500,
                  "Very Expensive": 1000, "Luxury": 5000, "Super Luxury": 10000}
FOLDERS = {"NEURALWARE": "Neuralware", "CYBEROPTICS": "Cyberoptics",
           "INTERNAL BODY CYBERWARE": "Internal Body Cyberware",
           "EXTERNAL BODY CYBERWARE": "External Body Cyberware", "CYBERLIMBS": "Cyberlimbs",
           "OTHER/MISC": "Other", "ICONIC CYBERDECKS": "Cyberdecks", "ICONIC DRUGS": "Drugs"}
SECTIONS = {"iconic-cyberware": "Becoming Iconic > Iconic Cyberware",
            "iconic-gear": "Becoming Iconic > Iconic Gear"}
# The two chapter rules every Iconic needs in front of the GM, short enough to sit in the notes.
ICONIC_NOTE = ("Iconic: it can't be bought or sourced on the street, can't be fabricated without its "
               "Blueprint, can't be taken during Character Generation, and once acquired can't be destroyed "
               "unless the player agrees to it beforehand.")


def price_of(stats, spec):
    if "price" in spec:
        return spec["price"]
    cat = (stats.get("Category") or "").split("(")[0].strip()
    return CATEGORY_PRICE.get(cat, 0)


def facts_for(stats, extra=()):
    out = [("Category", stats.get("Category", "N/A")),
           ("Fabrication", stats.get("Fabrication", "N/A"))]
    out += [f for f in extra if f[1]]
    return out


def notes_for(spec, price, stats):
    notes = [ICONIC_NOTE]
    if price:
        cat = (stats.get("Category") or "").split("(")[0].strip()
        notes.append(f"The price is the {cat} benchmark, for working out repairs and Tech Upgrades. Iconics "
                     f"can't be bought.")
    return notes + list(spec.get("notes", []))


def build_all():
    spec = json.load(open(ROOT / "text/iconics.json", encoding="utf-8"))["items"]
    data = json.load(open(ROOT / "data/iconics.parsed.json", encoding="utf-8"))
    parsed = {r["heading"]: r for r in data["entries"]}
    # An entry with nested "#### " entries under it (Relic Biochip 1.0 -> 2.0) must stop at the first
    # sub-heading when we pull Corgo's wording, or the parent swallows its child's text.
    has_children = {r["parent"] for r in data["entries"] if r["parent"]}

    packs = {"iconic-cyberware": [], "iconic-gear": []}
    folders = {}

    def folder(pack, label):
        if (pack, label) not in folders:
            f = folder_doc(pack, label, len([1 for p, _ in folders if p == pack]))
            folders[(pack, label)] = f["_id"]
            packs[pack].append(f)
        return folders[(pack, label)]

    for key, sp in spec.items():
        rec = parsed[sp.get("heading", key)]
        stats, section = rec["stats"], SECTIONS[rec["chapter"]]
        pack = rec["chapter"]
        label = FOLDERS[rec["group"]]
        price = price_of(stats, sp)
        notes = notes_for(sp, price, stats)
        name = sp.get("name") or title_case(key)
        intro_only = rec["heading"] in has_children
        heading = sp.get("heading", key)
        original = original_text.lookup(rec["chapter"], heading, intro_only=intro_only)

        if sp["kind"] == "enhancement":
            f = facts_for(stats, [("Enhances", sp["enhances"]), ("Option Slots", "0 (Cyberware Enhancement)")])
            d = build_upgrades.upgrade(f"iconic:{key}", name, {"mods": sp.get("mods", {})}, price, 0, f,
                                       sp["rules"], section, folder(pack, label), notes=notes,
                                       heading=heading, section_key=rec["chapter"], intro_only=intro_only)
            d["system"]["type"] = "cyberware"
            d["system"]["isElectronic"] = sp.get("electronic", False)
            d["img"] = build_cyberware.icon_path(sp.get("icon"))
            packs[pack].append(d)
            continue

        if sp["kind"] == "cyberware":
            # Reuse the cyberware builder's document shape, then swap in the Iconic facts and notes: an
            # Iconic lists Category and Fabrication where ordinary cyberware lists a Cost.
            sub = dict(sp, price=price, notes=[])
            docs = build_cyberware.cyberware_item(key, sub, rec, folder(pack, label), section,
                                                  intro_only=intro_only)
            hl = sp.get("hl") or build_cyberware.parse_hl(stats.get("Humanity Loss")) or (0, "0")
            for d in docs:
                s = d["system"]
                extra = [("Type", build_cyberware.TYPE_LABEL.get(s["type"], "")),
                         ("Install", build_cyberware.INSTALL_LABEL[s["installLocation"]]),
                         ("Humanity Loss", f"{hl[0]} ({hl[1]})" if hl[0] else "None"),
                         ("Option Slots", f"uses {s['size']}"
                          + (f", provides {sp['slots']}" if sp.get("slots") else ""))]
                s["description"]["value"] = description_html(
                    facts=facts_for(stats, extra), rules=sp["rules"], notes=notes, section=section,
                    original=original)
            packs[pack] += docs
            continue

        if sp["kind"] == "cyberdeck":
            s = copy.deepcopy(build_cyberware.CYBERDECK_TEMPLATE)
            s["price"]["market"] = price
            s["installedItems"]["slots"] = sp["slots"]
            s["description"]["value"] = description_html(
                facts=facts_for(stats, [("Slots", str(sp["slots"]))]), rules=sp["rules"], notes=notes,
                section=section, original=original)
            img = build_cyberware.ICONS + "default/Default_Cyberdeck.svg"
            packs[pack].append(build_cyberware._doc("cyberdeck", f"iconic:{key}", name, "cyberdeck", img, s,
                                                    folder(pack, label)))
            continue

        if sp["kind"] == "drug":
            s = copy.deepcopy(build_gear.DRUG_TEMPLATE)
            s["price"]["market"] = price
            s["usage"] = sp.get("usage", "snorted")
            img = build_cyberware.ICONS + "gear/generic_pharmaceuticals.svg"
            primary, addiction = sp.get("primary", []), sp.get("addiction", [])
            effects, dnotes = [], list(notes)
            if primary:
                effects.append(lambda iid: build_gear.effect(iid, f"{name} Primary", img, primary,
                                                             disabled=True))
                s["consumed"] = f"{name} Primary"
            if addiction:
                effects.append(lambda iid: build_gear.effect(iid, f"{name} Addiction", img, addiction,
                                                             disabled=True))
                dnotes.append(f'While addicted, switch on the "{name} Addiction" effect; switch it off again '
                              f"while the Primary Effect is running, which cancels it.")
            if primary or addiction:
                dnotes.append("Stat and skill changes are automated; the month-long duration, caps, minimums "
                              "and everything else are not.")
            s["description"]["value"] = description_html(
                facts=facts_for(stats, [("Type", "Iconic Drug")]), rules=sp["rules"], notes=dnotes,
                section=section, original=original)
            packs[pack].append(build_cyberware._doc("drug", f"iconic:{key}", name, "drug", img, s,
                                                    folder(pack, label), effects))
            continue

        raise ValueError(f"{key}: unknown kind {sp['kind']}")
    return packs
