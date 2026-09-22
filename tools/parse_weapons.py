"""Parse Corgo's 77 Collection V3 weapon catalog (Google Docs markdown export) into records."""
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
OUT = ROOT / "data/weapons.parsed.json"

def clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)   # drop links, keep text
    s = s.replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()

def section(text, start_heading, end_heading):
    a = text.index(start_heading)
    b = text.index(end_heading, a + 1)
    return text[a:b]

def field(block, label, stop=r"(?:•|♦|$)"):
    m = re.search(rf"{label}:\s*(.*?)\s*{stop}", block, re.M)
    return m.group(1).strip() if m else None

STAT_LABELS = ["Class", "Skill", "Range", "Damage", "Capacity", "ROF", "Hands",
               "Alt. Firing Modes", "Concealable", "Slots", "Attachments", "Mods", "Special Features"]
STAT_KEYS = ["class", "skill", "range", "damage", "capacity", "rof", "hands",
             "alt_modes", "concealable", "slots", "attachments", "mods", "special"]
LABELS = ["Cost"] + STAT_LABELS
KEYS = ["cost"] + STAT_KEYS
# The Iconic Weapons chapter uses the same stat block but prices items by Category and Fabrication
# instead of a Cost, so parse_iconic_weapons.py passes these in (see parse_entry).
ICONIC_LABELS = ["Category", "Fabrication", "Eligible"] + STAT_LABELS
ICONIC_KEYS = ["category", "fabrication", "eligible"] + STAT_KEYS


def parse_entry(title, body, labels=None, keys=None, anchor="Cost:"):
    labels, keys = labels or LABELS, keys or KEYS
    lines = [clean(l) for l in body.splitlines() if clean(l)]
    # stat text starts at the anchor label; flavor text / art credits come before it
    start = next((i for i, l in enumerate(lines) if l.startswith(anchor)), None)
    stat_lines = [l for l in lines[start:] if not l.startswith("NOTE:")] if start is not None else []
    stat = " ".join(stat_lines)
    # Docs export sometimes glues the next label onto the previous value ("NoSlots: 2")
    stat = re.sub(r"(?<=[a-z)])(Slots|Attachments|Mods|Special Features|Concealable):", r" \1:", stat)
    pat = re.compile(r"(?:^|(?<=[\s•♦]))(" + "|".join(re.escape(l) for l in labels) + r"):")
    hits = list(pat.finditer(stat))
    rec = {"heading": clean(title)}
    for k in keys:
        rec[k] = None
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(stat)
        val = stat[m.end():end].strip().strip("•♦").strip()
        key = keys[labels.index(m.group(1))]
        if rec[key] is None:
            rec[key] = val
    rec["special"] = rec["special"] or ""
    rec["notes"] = [l for l in lines if l.startswith("NOTE:")]
    return rec

def main():
    text = open(SRC, encoding="utf-8").read()
    # first WEAPONS tab only (the "Copy of WEAPONS" tab is a duplicate)
    cat = section(text, "# **WEAPON CATALOG**", "# **AMMUNITION**")
    main_part, variants_part = cat.split("## **VARIANTS**", 1)
    records, group = [], None
    parts = re.split(r"^(#{2,3}) (.+)$", main_part, flags=re.M)
    for i in range(1, len(parts), 3):
        level, title, body = parts[i], parts[i + 1], parts[i + 2]
        if level == "##":
            group = clean(title)
            continue
        if group in (None, "WEAPON LISTING CLARIFICATIONS"):
            continue
        r = parse_entry(title, body)
        r["group"] = group
        records.append(r)
    json.dump(records, open(OUT, "w", encoding="utf-8"), indent=1)
    print(len(records), "weapons parsed")
    bad = [r["heading"] for r in records if not (r["cost"] and r["class"] and r["damage"])]
    print("incomplete:", bad)

if __name__ == "__main__":
    main()
