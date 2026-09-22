"""Parse Corgo's Iconic Weapons chapter into records.

Writes data/iconic_weapons.parsed.json with three lists:

- `mods`: the four Iconic Weapon Mods, which carry Category, Fabrication and an `Eligible` line saying
  which weapons they fit, rather than a weapon stat block.
- `weapons`: the 89 Iconic weapons across the eight class groups. Their stat block is the weapon
  catalog's, so parse_weapons.parse_entry does the work; only the price fields differ (Category and
  Fabrication in place of Cost), which it takes as parameters.
- `variants`: the three variant series (Barghest P.U.Ps, the Svarog series, X-Mod2) and their named
  members. Each member is a single heading carrying its own name, Category, Fabrication and the base
  weapon it is built from, e.g.

      #### **'FOXHOUND'** \\[Super Luxury | DV29 - 10,000eb - 1 Month\\] {Nekomata}

  so the base weapon is a weapon we have already built, and the series text holds the shared rule. That
  mirrors how text/weapon_variants.json handles the Ironfake and Darkhound variants.
"""
import json, re, sys
from pathlib import Path

from parse_weapons import ICONIC_KEYS, ICONIC_LABELS, clean, parse_entry, section

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/corgo-77-v3.md"
OUT = ROOT / "data/iconic_weapons.parsed.json"

# "'FOXHOUND' [Super Luxury | DV29 - 10,000eb - 1 Month] {Nekomata}"
VARIANT = re.compile(r"^[‘'\"]?(?P<name>[^’'\"\[]+?)[’'\"]?\s*\[(?P<category>[^|\]]+)"
                     r"(?:\|(?P<fab>[^\]]+))?\]\s*\{(?P<base>[^}]+)\}$")


def parse(text):
    chapter = section(text, "# **ICONIC WEAPONS**", "# **ICONIC VEHICLES**")
    mods, weapons, variants, series = [], [], [], []
    group, in_variants, cur_series = None, False, None

    parts = re.split(r"^(#{2,5}) (.+)$", chapter, flags=re.M)
    for i in range(1, len(parts), 3):
        level, title, body = parts[i], clean(parts[i + 1]), parts[i + 2]
        if level == "##":
            group, in_variants = title, title.upper() == "VARIANTS"
            cur_series = None
            continue
        if group is None:
            continue

        if in_variants:
            if level == "###":  # a series: its body is the shared rule
                cur_series = {"heading": title,
                              "lines": [clean(l) for l in body.splitlines() if clean(l)]}
                series.append(cur_series)
            else:  # a member of the series
                if title.upper().startswith("KNOWN"):  # the list's own sub-heading
                    continue
                m = VARIANT.match(title)
                if not m:
                    print(f"  unparsed variant heading: {title}")
                    continue
                variants.append({"heading": m.group("name").strip().upper(),
                                 "series": cur_series["heading"] if cur_series else None,
                                 "category": m.group("category").strip(),
                                 "fabrication": (m.group("fab") or "").strip(),
                                 "base": clean(m.group("base")).upper(),
                                 "lines": [clean(l) for l in body.splitlines() if clean(l)]})
            continue

        if group.upper() == "ICONIC WEAPON MODS":
            # A mod has no weapon stat block, so the label parser would run the Eligible value on into
            # the flavour and rules text. Take its three labelled lines and keep the rest as prose.
            rec = {"heading": title, "group": group, "lines": []}
            for line in (clean(l) for l in body.splitlines()):
                if not line:
                    continue
                k, sep, v = line.partition(":")
                if sep and k.strip() in ("Category", "Fabrication", "Eligible"):
                    rec[k.strip().lower()] = v.strip()
                else:
                    rec["lines"].append(line)
            mods.append(rec)
            continue

        rec = parse_entry(title, body, ICONIC_LABELS, ICONIC_KEYS, anchor="Category:")
        rec["group"] = group
        weapons.append(rec)
    return {"mods": mods, "weapons": weapons, "series": series, "variants": variants}


if __name__ == "__main__":
    data = parse(SRC.read_text(encoding="utf-8"))
    json.dump(data, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(data['mods'])} mods, {len(data['weapons'])} weapons, "
          f"{len(data['series'])} variant series with {len(data['variants'])} members")
    groups = {}
    for w in data["weapons"]:
        groups[w["group"]] = groups.get(w["group"], 0) + 1
    for g, n in groups.items():
        print(f"    {g}: {n}")
    bad = [w["heading"] for w in data["weapons"] if not (w["category"] and w["class"] and w["damage"])]
    print("incomplete:", bad)
