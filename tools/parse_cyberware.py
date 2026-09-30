"""Parse Corgo's Cyberware, Operating Systems and Cyberware Alternatives chapters into records.

Writes data/cyberware.parsed.json. Each record is {chapter, group, level, heading, parent, stats, lines}:

- `chapter` is "cyberware", "operating-systems" or "cyberware-alternatives" (matches
  original_text.SECTIONS, so the builder can hand the heading straight to original_text.lookup).
- `group` is the "## " subsection (FASHIONWARE, NEURALWARE, CYBERARMS, ...) and becomes the pack folder.
- `parent` is the "### " entry a nested "#### " enhancement hangs off (Gorilla Arm -> Limiter Removal),
  which is how we know a nested entry enhances the entry above it rather than standing alone.
- `stats` holds the Cost / Install / Humanity Loss / Availability line values as written.

Only stats are parsed; the rules text itself lives in text/cyberware.json, rewritten in our own words
(`npm run build:original` substitutes Corgo's wording at build time instead). Full Body Conversions,
the Militech Centaur Exo, and the Corpochrome variants are deliberately not parsed: see SKIP and
DEVELOPING.md.
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
OUT = ROOT / "data/cyberware.parsed.json"

# chapter key -> (start marker, end marker). The doc repeats some chapters in a "Copy of" tab, so we
# take the first occurrence of each, like original_text._section does.
CHAPTERS = {
    "cyberware": ("# **CYBERWARE**", "# **OPERATING SYSTEMS"),
    "operating-systems": ("# **OPERATING SYSTEMS", "# **CYBERWARE ALTERNATIVES"),
    "cyberware-alternatives": ("# **CYBERWARE ALTERNATIVES", "# **2070s FULL BODY CONVERSIONS"),
}
# Subsections and entries deliberately not built. 2070s Full Body Conversions is excluded by the
# chapter ranges above; these two sit inside chapters that are built.
SKIP_GROUPS = {"VARIANTS",     # Corpochrome: documented as a rule in module/README.md, not built as items
               "CYBERCHAIRS"}  # Militech Centaur Exo: skipped
SKIP_HEADINGS = {"CYBERWARE UPDATES"}  # chapter preamble, not an item

HEADING = re.compile(r"^(#{1,6}) (.+)$")
STAT_LABELS = ("Cost", "Install", "Humanity Loss", "Availability")


def clean(s):
    """Strip Docs-export markdown: links, escapes, bold/italic markers, runs of whitespace."""
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()


def parse_stats(line, stats):
    """'Cost: 5,000eb (Luxury) ♦ Install: Clinic' -> {'Cost': '5,000eb (Luxury)', 'Install': 'Clinic'}

    The export sometimes splits a label across bold runs ('**I****nstall:**'), which clean() rejoins,
    and separates fields with either of two bullet characters. An entry can also state a label twice on
    separate lines (Para Bellum prices two SP brackets); both are kept, joined with " / ".
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
                if group in SKIP_GROUPS or title in SKIP_HEADINGS:
                    cur = None
                    continue
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


if __name__ == "__main__":
    recs = parse(SRC.read_text(encoding="utf-8"))
    json.dump(recs, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    by_chapter = {}
    for r in recs:
        by_chapter.setdefault(r["chapter"], []).append(r)
    for chapter, rs in by_chapter.items():
        print(f"{chapter}: {len(rs)} entries")
        groups = {}
        for r in rs:
            groups[r["group"]] = groups.get(r["group"], 0) + 1
        for g, n in groups.items():
            print(f"    {g}: {n}")
