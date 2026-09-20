"""Check that `npm run build:original` put each item's own entry text on that item, and nothing else's.

`build.py` already reports lookups that found no entry at all. This checks the harder question: that the
text an item *did* get is the right text. It works off the parsers' records rather than
original_text.py, so a heading-matching bug in the lookup can't hide itself - the two code paths would
have to be wrong in the same way.

Two checks per item:

- coverage: a distinctive line from the item's own entry appears in its description.
- contamination: no distinctive line from a *different* entry appears in it. This is what catches a
  parent entry swallowing its nested sub-entries (Gorilla Arm running on into Limiter Removal), which
  the item-by-item "did it find anything" report cannot see. Text shared on purpose - a group intro
  that siblings inherit, or one entry that several split items are built from - is not contamination.

Run after `npm run build:original`:  python3 tools/check_original.py [build/packs]
Exits non-zero if anything is wrong. Needs data/ (so it only runs where Corgo's document is present).
"""
import html, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import title_case
from build_upgrades import MAG_FAMILIES

ROOT = Path(__file__).resolve().parent.parent
PACKS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/packs"
MIN_WORDS = 8  # a line shorter than this is usually boilerplate shared across entries
# The capacity-chart magazine families are built one item per weapon row with generated, row-specific rules
# (see build_upgrades.MAG_FAMILIES), so they carry no entry text by design.
GENERATED = {f[0] for f in MAG_FAMILIES}


def norm(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s).replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def distinctive(lines, seen):
    """The longest line of an entry that no other entry also contains, normalized."""
    best = ""
    for line in lines:
        n = norm(line)
        if len(n.split()) < MIN_WORDS or seen.get(n, 0) > 1:
            continue
        if len(n) > len(best):
            best = n
    return best


def entries():
    """name -> {"id": entry id, "text": distinctive line, "kin": ids whose text may legitimately appear}

    `kin` covers text an entry is meant to inherit: the group intro above it, the entry a nested one
    hangs off, and (for a split) the single entry all its items come from.
    """
    out, raw = {}, {}

    cyber = json.load(open(ROOT / "text/cyberware.json", encoding="utf-8"))["items"]
    recs = json.load(open(ROOT / "data/cyberware.parsed.json", encoding="utf-8"))
    by_heading = {r["heading"]: r for r in recs}
    for r in recs:
        raw[("cw", r["heading"])] = r["lines"]
    for key, spec in cyber.items():
        heading = spec.get("heading", key)
        rec = by_heading[heading]
        kin = {("cw", rec["parent"])} if rec["parent"] else set()
        names = [v[0] for v in spec["split"]] if spec.get("split") else [spec.get("name") or title_case(key)]
        for n in names:
            out[n] = {"id": ("cw", heading), "kin": kin}

    up = json.load(open(ROOT / "data/upgrades.parsed.json", encoding="utf-8"))
    for group, records in up.items():
        for r in records:
            raw[("up", r["heading"])] = r.get("body", [])
    for f, group in (("text/attachments.json", "attachments"), ("text/mods.json", "mods"),
                     ("text/ammo.json", "ammo")):
        spec = json.load(open(ROOT / f, encoding="utf-8"))
        headings = {r["heading"] for r in up[group]}
        for key, s in spec.items():
            if key not in headings or title_case(key) in GENERATED:
                continue  # our own item, or a generated family: no entry text to carry over
            names = [v[0] for v in s["split"]] if s.get("split") else [s.get("name") or title_case(key)]
            for n in names:
                out[n] = {"id": ("up", key), "kin": set()}

    counts = {}
    for lines in raw.values():
        for line in lines:
            n = norm(line)
            counts[n] = counts.get(n, 0) + 1
    for meta in out.values():
        meta["text"] = distinctive(raw.get(meta["id"], []), counts)
    return out, {k: distinctive(v, counts) for k, v in raw.items()}


def main():
    if not (ROOT / "data/corgo-77-v3.md").exists():
        print("data/corgo-77-v3.md not present: nothing to check")
        return 0
    if not PACKS.exists():
        print(f"{PACKS} not found. Run `npm run build:original` first.")
        return 1

    known, by_id = entries()
    built = {}
    for f in PACKS.glob("*/*.json"):
        d = json.load(open(f, encoding="utf-8"))
        if d["_key"].startswith("!folders!") or "description" not in d.get("system", {}):
            continue
        built[norm(d["name"])] = (f.parent.name, norm(d["system"]["description"]["value"]))

    missing, wrong, dirty, checked = [], [], [], 0
    for name, meta in known.items():
        key = norm(name)
        # one entry can build a family of items, one per ammo variety or weapon row ("HVAP Ammunition
        # (Rifle)" and its siblings); every one of them has to carry the entry's text.
        targets = [built[key]] if key in built else [v for k, v in built.items() if k.startswith(key + " ")]
        if not targets:
            missing.append(name)
            continue
        if not meta["text"]:
            continue  # entry has no line long enough to fingerprint
        for pack, desc in targets:
            checked += 1
            if meta["text"] not in desc:
                wrong.append((pack, name))
            for other, text in by_id.items():
                if text and other != meta["id"] and other not in meta["kin"] and text in desc:
                    dirty.append((pack, name, other[1]))

    print(f"{checked} built items fingerprinted against the {len(known)} document entries they came from")
    for label, rows in (("not built", missing), ("own entry text missing", wrong),
                        ("carries another entry's text", dirty)):
        if rows:
            print(f"\n{label}: {len(rows)}")
            for r in rows[:20]:
                print("   ", r)
    if not (wrong or dirty):
        print("every fingerprinted item carries its own entry's text and no one else's")
    return 1 if (wrong or dirty) else 0


if __name__ == "__main__":
    sys.exit(main())
