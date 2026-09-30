"""Parse Corgo's Attachment Catalog, Mod Catalog and Ammunition sections into records."""
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


def clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()


def entries(block, stop_groups=()):
    """Split a catalog block into (group, title, lines) using ## groups and ### entries."""
    out, group = [], None
    parts = re.split(r"^(#{2,5}) (.+)$", block, flags=re.M)
    for i in range(1, len(parts), 3):
        level, title, body = parts[i], clean(parts[i + 1]), parts[i + 2]
        if level == "##":
            group = title
            continue
        lines = [clean(l) for l in body.splitlines() if clean(l)]
        out.append({"group": group, "level": len(level), "heading": title, "lines": lines})
    return out


def split_body(lines):
    """Separate stat lines, flavor (italic in source, already stripped) and rules paragraphs."""
    stats, rules = {}, []
    for l in lines:
        if l.startswith("(Art") or l.startswith("NOTE:"):
            continue
        m = re.match(r"^(Cost|Fits|Mods|Required Slots|Install|Availability):", l)
        if m:
            for part in re.split(r"\s*♦\s*", l):
                k, _, v = part.partition(":")
                stats[k.strip()] = v.strip()
            continue
        rules.append(l)
    return stats, rules


def main():
    text = SRC.read_text(encoding="utf-8")
    a = text.index("# **ATTACHMENT CATALOG")
    m = text.index("# **MOD CATALOG", a)
    t = text.index("# **THRONGLIN", m)
    am = text.index("# **AMMUNITION**", t)
    am_end = re.compile(r"^# ", re.M).search(text, am + 20).start()
    raw = {"attachments": text[a:m], "mods": text[m:t], "ammo": text[am:am_end]}
    out = {}
    for kind, block in raw.items():
        recs = []
        for e in entries(block):
            if e["heading"] in ("WHAT IS THIS?", "WEAPON MOD RULES"):
                continue
            stats, rules = split_body(e["lines"])
            recs.append({"group": e["group"], "level": e["level"], "heading": e["heading"], "stats": stats,
                         "body": rules})
        out[kind] = recs
    with open(ROOT / "data/upgrades.parsed.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for k, v in out.items():
        print(k, len(v), "entries;", sum(1 for r in v if "Cost" not in r["stats"]), "without a Cost line")


if __name__ == "__main__":
    main()
