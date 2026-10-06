"""Parse Corgo's 77 Collection Mooks (data/npcs/*.md, one Google Docs markdown export per faction) into records.

Every stat block is a `### TITLE` section holding one table. Two layouts occur:

- **COM#** (nearly all): HP, DS, REPUTATION / FACEDOWN, then COM#, INIT, COOL, and MOVE in place of STATs,
  with Skill Bases (STAT + level) for the rest.
- **Full** (the named bosses): NAME / REP / SERIOUSLY WOUNDED / HP, ROLE / DEATH SAVE, all ten STATs, a
  six-column weapon table, a located armor table, and separate GEAR and CYBERWARE lines.

The parser records what the block says, as text where the text is the data: matching gear names to items
is the builder's job (tools/build_npcs.py, through text/npc_aliases.json). Gear lists are parsed into a tree:
"Neuroport (w/ Pain Editor [w/ Painducer], Self-ICE x2)" is a Neuroport with two children, and any other
bracketed text ("(Head-Mounted)", "[3 Total]") is kept as that node's gloss.
"""
import json, re, sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # Windows consoles; see tools/common.py
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/npcs"
OUT = ROOT / "data/npcs.parsed.json"

STATS = ["int", "ref", "dex", "tech", "cool", "will", "luck", "move", "body", "emp"]
ROLES = ["Solo", "Netrunner", "Nomad", "Tech", "Fixer", "Medtech", "Media", "Lawman", "Exec", "Rockerboy",
         "Enforcer"]
OPEN, CLOSE = "([{", ")]}"


def clean(s):
    s = re.sub(r"\\(.)", r"\1", s).replace("*", "")
    return re.sub(r"\s+", " ", s).strip()


def cells(line):
    return [clean(c) for c in line.strip().strip("|").split("|") if c.strip()]


def split_top(s, seps):
    """Split on any separator that sits outside brackets."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        if s[i] in OPEN:
            depth += 1
        elif s[i] in CLOSE:
            depth = max(0, depth - 1)
        sep = next((p for p in seps if depth == 0 and s.startswith(p, i)), None)
        if sep:
            out.append(cur)
            cur, i = "", i + len(sep)
            continue
        cur += s[i]
        i += 1
    out.append(cur)
    return [p.strip() for p in out if p.strip()]


def groups(s):
    """The text outside top-level brackets, and the bracketed groups as (open, inner) pairs."""
    outside, found, depth, start = "", [], 0, 0
    for i, ch in enumerate(s):
        if ch in OPEN:
            if depth == 0:
                start = i
            depth += 1
        elif ch in CLOSE and depth:
            depth -= 1
            if depth == 0:
                found.append((s[start], s[start + 1:i].strip()))
                continue
        if depth == 0 and ch not in CLOSE:
            outside += ch
    return re.sub(r"\s+", " ", outside).strip(), found


def item_node(s):
    """One gear entry as {name, qty, gloss, children}."""
    name, found = groups(s)
    node = {"raw": s, "name": name, "qty": 1, "gloss": [], "children": []}
    for _, inner in found:
        if re.match(r"w/\s", inner):
            node["children"] += [item_node(c) for c in split_top(inner[2:].strip(), [", & ", ", ", " & "])]
        else:
            node["gloss"].append(inner)
    m = re.match(r"^x(\d+)\s+(.*)$", node["name"]) or re.match(r"^(.*?)\s+x(\d+)$", node["name"])
    if m:
        a, b = m.groups()
        node["qty"], node["name"] = (int(a), b) if a.isdigit() else (int(b), a)
    return node


def gear_line(s):
    """A GEAR line: the item tree, plus any Enforcer or Programs text the export ran onto the same line."""
    extra = {}
    for label in ("Enforcer", "Programs"):
        m = re.search(rf"(?:^|\s)({label}:\s.*?)(?=\s(?:Enforcer|Programs):\s|$)", s)
        while m:
            extra.setdefault(label.lower(), []).append(m.group(1).split(":", 1)[1].strip())
            s = (s[:m.start()] + s[m.end():]).strip()
            m = re.search(rf"(?:^|\s)({label}:\s.*?)(?=\s(?:Enforcer|Programs):\s|$)", s)
    return [item_node(g) for g in split_top(s, ["⦁"])], extra


def skill_line(s):
    """'Athletics 13 (11) ⦁ Local Expert (Badlands) 8 Education 6' -> [{name, base, alt}]. The export drops the
    separator where the document wrapped a line ("Streetslang) 8Local Expert"), so a skill also ends where its
    number meets a capital.

    `alt` is the bracketed value as written: the base with a gear or role bonus or a gear penalty applied,
    sometimes several ("15/16") or with the source named ("20/25 [w/ Poser Chip]")."""
    out = []
    for m in re.finditer(r"\s*(?:⦁\s*)?(.+?)\s+(\d+)(?:\s*\(([\d/]+(?:\s*\[[^\]]*\])?)\))?(?=\s*⦁|\s*[A-Z]|\s*$)",
                         s):
        out.append({"name": m.group(1).strip(), "base": int(m.group(2)), "alt": m.group(3)})
    return out


def role_line(s):
    """'Solo: Combat Awareness 4 Enforcer: Officer 2 (Authority 2)' -> [{role, ability, rank, detail}]."""
    if s in ("N/A", ""):
        return []
    starts = [m.start() for m in re.finditer(rf"\b(?:{'|'.join(ROLES)}):", s)]
    out = []
    for a, b in zip(starts, starts[1:] + [len(s)]):
        part = s[a:b].strip()
        m = re.match(r"(\w+):\s*(.+?)\s+(\d+)\s*(?:\((.*)\))?$", part)
        if not m:
            raise ValueError(f"role {part!r}")
        out.append({"role": m.group(1), "ability": m.group(2), "rank": int(m.group(3)), "detail": m.group(4)})
    return out


def sp(s):
    return int(re.sub(r"\D", "", s) or 0)


def parse_com(rec, rows):
    section = None
    for r in rows:
        head = r[0]
        if len(r) == 3 and r[1] == "HP":
            rec["name"], rec["hp"] = head, int(r[2])
        elif len(r) == 3 and r[1] == "DS":
            rec["roles"], rec["ds"] = role_line(head), int(r[2])
        elif head.startswith("REPUTATION"):
            rec["rep"] = int(re.search(r"REPUTATION:\s*(\d+)", head).group(1))
            rec["facedown"] = int(re.search(r"FACEDOWN #:\s*(\d+)", head).group(1))
        elif head == "COM#":
            kv = dict(zip(r[0::2], r[1::2]))
            rec.update(com=int(kv["COM#"]), init=int(kv["INIT"]), cool=int(kv["COOL"]), move=int(kv["MOVE"]))
        elif head.startswith("WEAPONS"):
            section, rec["weapon_choice"] = "weapons", (re.search(r"\((.*)\)", head) or [None, None])[1]
        elif head in ("SKILL BASES", "ARMOR (HEAD/BODY)", "GEAR & CYBERWARE"):
            section = head
        elif head in ("STATS", "ATTACKS", "TYPE"):
            continue
        elif section == "SKILL BASES":
            rec["skills"] = skill_line(head)
        elif section == "weapons" and head.startswith("↪"):
            rec["weapons"][-1]["notes"] = r[1]
        elif section == "weapons":
            rec["weapons"].append({"name": head, "rof": r[1], "damage": r[2]})
        elif section == "ARMOR (HEAD/BODY)":
            names = split_top(head, [" / "])
            basic, melee = r[1].split("/"), r[2].split("/")
            for loc, name, b, m in zip(("head", "body"), names, basic, melee):
                rec["armor"][loc] = {"name": name, "sp": sp(b), "half": sp(m)}
        elif section == "GEAR & CYBERWARE":
            rec["gear"], extra = gear_line(head)
            rec["enforcer"] += extra.get("enforcer", [])
            rec["programs"] += extra.get("programs", [])
        else:
            raise ValueError(f"unplaced row {r}")


def parse_full(rec, rows):
    section = None
    for r in rows:
        head = r[0]
        if head == "NAME":
            kv = dict(zip(r[0::2], r[1::2]))
            rec.update(name=kv["NAME"], rep=int(kv["REP"]), hp=int(kv["HP"]))
        elif head == "ROLE":
            rec["roles"], rec["ds"] = role_line(r[1]), int(r[3])
        elif head.upper() in [s.upper() for s in STATS] and section == "STATS":
            for k, v in zip(r[0::2], r[1::2]):
                # "EMP 3 / 8" is current / max; LUCK "N/A" is none.
                cur, _, top = v.partition("/")
                rec["stats"][k.lower()] = {"value": sp(cur), "max": sp(top) if top else sp(cur)}
        elif head in ("STATS", "ATTACKS", "ARMOR", "GEAR", "CYBERWARE"):
            section = head
        elif head == "SKILL BASES":
            section = head
            if len(r) > 1:
                rec["com"] = sp(r[1])  # "OPTIONAL: COMBAT# 18"
        elif head in ("WEAPON", "LOCATION"):
            continue
        elif section == "ATTACKS":
            w = dict(zip(["name", "skill", "rof", "damage", "ammo", "notes"], r))
            rec["weapons"].append(w)
        elif section == "ARMOR":
            loc, name, full, half, notes = (r + [""] * 5)[:5]
            rec["armor"][loc.lower()] = {"name": name, "sp": sp(full), "half": sp(half),
                                         "notes": None if notes == "None" else notes}
        elif section == "SKILL BASES":
            rec["skills"] = skill_line(head)
        elif section in ("GEAR", "CYBERWARE"):
            items, extra = gear_line(head)
            rec["gear"] += items
            rec["enforcer"] += extra.get("enforcer", [])
            rec["programs"] += extra.get("programs", [])
        else:
            raise ValueError(f"unplaced row {r}")


def parse_file(path):
    text = path.read_text(encoding="utf-8")
    faction = clean(re.search(r"^## (.+)$", text, re.M).group(1))
    out = []
    for sec in re.split(r"^### ", text, flags=re.M)[1:]:
        title, body = sec.split("\n", 1)
        # split("\n"), not splitlines(): the export puts soft line breaks (\x0b) inside table cells, and
        # splitlines() would cut a row there.
        rows = [cells(l) for l in body.split("\n") if l.startswith("|")]
        rows = [r for r in rows if r and not set(r[0]) <= set("-: ")]
        bg = re.search(r"\*\*Background:\*\*\s*(.+)", body)
        rec = {"file": path.name, "faction": faction, "title": clean(title), "level": None,
               "background": clean(bg.group(1)) if bg else "", "roles": [], "skills": [], "weapons": [],
               "weapon_choice": None, "armor": {}, "gear": [], "enforcer": [], "programs": [], "stats": {}}
        if not rows or not rows[0][0].startswith("LEVEL:"):
            raise ValueError(f"{path.name}: {rec['title']}: no LEVEL row")
        rec["level"] = rows[0][0].split(":", 1)[1].strip()
        try:
            if rows[1][0] == "NAME":
                rec["layout"] = "full"
                parse_full(rec, rows[1:])
            else:
                rec["layout"] = "com"
                parse_com(rec, rows[1:])
        except (ValueError, KeyError, IndexError) as e:
            raise ValueError(f"{path.name}: {rec['title']}: {e!r}") from e
        out.append(rec)
    return out


def main():
    records = [r for p in sorted(SRC.glob("*.md")) for r in parse_file(p)]
    required = {"com": ["name", "hp", "ds", "rep", "com", "init", "cool", "move"],
                "full": ["name", "hp", "ds", "rep"]}
    for r in records:
        missing = [k for k in required[r["layout"]] if k not in r]
        if r["layout"] == "full" and len(r["stats"]) != 10:
            missing.append("stats")
        if missing:
            sys.exit(f"{r['file']}: {r['title']}: missing {missing}")
    OUT.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"npcs: {len(records)} stat blocks from {len(list(SRC.glob('*.md')))} files -> {OUT.name}")


if __name__ == "__main__":
    main()
