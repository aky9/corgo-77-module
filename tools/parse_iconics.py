"""Parse Corgo's Becoming Iconic, Iconic Cyberware and Iconic Gear chapters into records.

Writes data/iconics.parsed.json: {chapter, group, level, heading, parent, stats, lines} per entry, the same
shape parse_cyberware.py produces, so build_iconics.py can hand a heading straight to original_text.lookup
and knows which nested entry hangs off which parent (Relic Biochip 2.0 under 1.0).

Iconics list no Cost. Instead they carry `Category` (the price tier, which drives repairs and Tech Upgrades)
and `Fabrication` (DV, materials, time), plus the usual Humanity Loss and Install for cyberware. They can't
be bought at all - see the Iconic rules, which this also captures as `_rules` so the builder can put them on
every item.

Iconic Armor is a single entry already built by build_armor (the "iconic" list in text/armor.json). Iconic
Weapons is its own chapter and its own pass. Iconic Vehicles waits for the vehicle chapters, since the
`vehicle` field set is untouched.
"""
import json, re, sys
from pathlib import Path

# Windows consoles can raise UnicodeEncodeError on the names printed below; see tools/common.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/corgo-77-v3.md"
OUT = ROOT / "data/iconics.parsed.json"

CHAPTERS = {
    "iconic-cyberware": ("# **ICONIC CYBERWARE", "# **ICONIC GEAR"),
    "iconic-gear": ("# **ICONIC GEAR", "# **ICONIC WEAPONS"),
}
RULES = ("# **BECOMING ICONIC", "# **ICONIC ARMOR")
HEADING = re.compile(r"^(#{1,6}) (.+)$")
STAT_LABELS = ("Category", "Fabrication", "Humanity Loss", "Install")


def clean(s):
    """Strip Docs-export markdown: links, escapes, bold/italic markers, runs of whitespace."""
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()


def parse_stats(line, stats):
    """'Category: Luxury ♦ Fabrication: DV29 - 5,000eb - 1 Month' -> both values as written.

    Corgo separates the two with a bullet on one line for most entries and splits them across two lines
    for others, and uses either "-" or "|" inside the Fabrication value; all of that is kept verbatim.
    """
    for part in re.split(r"\s*[♦•]\s*", line):
        k, _, v = part.partition(":")
        k, v = k.strip(), v.strip()
        if k in STAT_LABELS:
            stats[k] = f"{stats[k]} / {v}" if k in stats else v
    return stats


def parse(text):
    records = []
    for chapter, (start, end) in CHAPTERS.items():
        a = text.find(start)
        b = text.index(end, a + 1)
        group, parent, cur = None, None, None
        for line in text[a:b].splitlines():
            m = HEADING.match(line)
            if m:
                level, title = len(m.group(1)), clean(m.group(2)).upper()
                if level <= 2:
                    group = title if level == 2 else group
                    parent, cur = None, None
                    continue
                if level == 3:
                    parent = title
                cur = {"chapter": chapter, "group": group, "level": level, "heading": title,
                       "parent": parent if level > 3 else None, "stats": {}, "lines": []}
                records.append(cur)
                continue
            if cur is None:
                continue
            body = clean(line)
            if not body:
                continue
            if any(body.startswith(f"{lbl}:") for lbl in STAT_LABELS):
                parse_stats(body, cur["stats"])
                continue
            cur["lines"].append(body)
    return records


def parse_rules(text):
    """The bullet list under "ICONIC RULES" - what being Iconic means, put on every Iconic item."""
    a = text.index(RULES[0])
    b = text.index(RULES[1], a + 1)
    out, seen = [], False
    for line in text[a:b].splitlines():
        if line.startswith("#"):  # any heading ends the list: "### HOW TO USE ICONICS" follows it
            seen = line.startswith("## ") and "ICONIC RULES" in line.upper()
            continue
        if seen and line.strip().startswith("- "):
            out.append(clean(line.strip()[2:]))
    return out


if __name__ == "__main__":
    text = SRC.read_text(encoding="utf-8")
    recs = parse(text)
    json.dump({"rules": parse_rules(text), "entries": recs}, open(OUT, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    groups = {}
    for r in recs:
        groups.setdefault((r["chapter"], r["group"]), []).append(r["heading"])
    for (chapter, group), heads in groups.items():
        print(f"{chapter} / {group}: {len(heads)}")
    print(f"{len(parse_rules(text))} shared Iconic rules")
