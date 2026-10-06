"""Build the NPC pack: one 0.92.4 `mook` actor per stat block in Corgo's 77 Collection Mooks (data/npcs/).

Reads data/npcs.parsed.json (tools/parse_npcs.py), the item documents this module builds, and the 0.92.4
item snapshot in tools/cpr-0.92.4-items.json. Each actor embeds copies of real items, so its weapons, armor,
and cyberware behave exactly like the compendium ones.

How a COM# stat block becomes an actor (the full-layout bosses give all ten STATs and skip the first two):

- REF = INIT, COOL and MOVE as printed, BODY = DS (a Death Save is rolled against BODY). Every STAT the
  block does not give is 0, so a skill's level carries its whole printed base and the sheet rolls exactly the
  block's number.
- COM# is the base of every attack skill the block does not list itself. A listed skill (Brawling, a
  Martial Art) keeps its own number.
- Printed values win: weapon damage and ROF, armor SP, Brawling and Martial Arts damage. Where the printed
  number differs from the item's, the embedded copy is changed to match.
- A skill's bracketed value ("Athletics 13 (11)") is the base with a gear or role bonus or a gear penalty
  applied. The level comes from the printed base; the system applies worn armor's penalty itself, and the
  bracketed values are listed in the actor's notes.
- What has no Foundry item (Self-ICE, a "GM's Choice" weapon, Melee SP, Enforcer abilities) goes in the
  notes. Every gear name must either resolve to an item or be named in text/npc_aliases.json "unbuilt" with
  the reason; anything else fails the build.

A compendium actor gets none of what CPRActor.create gives a new one, so every actor carries all 63 core
skills and the three core cyberware containers, installed, itself (see CLAUDE.md, "NPCs").
"""
import copy, re
from pathlib import Path
from common import doc_id, html_escape, load_json
from parse_npcs import item_node as parse_node

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "data/npcs.parsed.json"
CORE = ROOT / "tools/cpr-0.92.4-items.json"
ALIASES = ROOT / "text/npc_aliases.json"
PACK = "npcs"

NPC_SOURCE_URL = "https://docs.google.com/document/d/1gdiAH9cuuy43O5IN2V4BdV45gm-j0GAO_TrBtNm6T-o/edit"
NPC_SOURCE_BOOK = "Corgo's 77 Collection: Mooks"
MOOK_IMG = "systems/cyberpunk-red-core/icons/compendium/default/Default_Mook.svg"

STATS = ["int", "ref", "dex", "tech", "cool", "will", "luck", "move", "body", "emp"]
ATTACK_SKILLS = ["Archery", "Autofire", "Brawling", "Handgun", "Heavy Weapons", "Melee Weapon", "Shoulder Arms"]
CORE_ROLES = {"Solo", "Netrunner", "Nomad", "Tech", "Fixer", "Medtech", "Media", "Lawman", "Exec", "Rockerboy"}
UNARMED_DAMAGE = [(4, "1d6"), (6, "2d6"), (10, "3d6")]  # BODY ceiling -> damage; above 10 is 4d6
# A weapon class named in a block's gloss ("Combat Knife (EQ Medium Melee)") -> the core generic weapon.
WEAPON_CLASSES = [
    (r"\b(?:Very Heavy|VH) Melee", "Very Heavy Melee"), (r"\bHeavy Melee", "Heavy Melee"),
    (r"\bMedium Melee", "Medium Melee"), (r"\bLight Melee", "Light Melee"),
    (r"\bVery Heavy Pistol", "Very Heavy Pistol"), (r"\bHeavy Pistol", "Heavy Pistol"),
    (r"\bMedium Pistol", "Medium Pistol"), (r"\bHeavy SMG", "Heavy SMG"), (r"\bSMG", "SMG"),
    (r"\bAssault Rifle", "Assault Rifle"), (r"\bSniper Rifle", "Sniper Rifle"), (r"\bShotgun", "Shotgun"),
]
GENERIC_WEAPONS = {c for _, c in WEAPON_CLASSES}
# Core items whose name is shared across packs: which pack a stat block means in each slot.
PACK_PREFERENCE = {
    "armor": ["armor", "cyberware"],
    "gear": ["gear", "clothing", "ammo", "drugs", "programs", "cyberware", "upgrades", "weapons", "armor"],
    "child": ["cyberware", "upgrades", "gear", "programs"],
    "weapon": ["weapons", "weapons-branded", "cyberware", "upgrades"],
}


def norm(s):
    s = re.sub(r"[®™‘’“”'\"]", "", s.replace("–", "-"))
    return re.sub(r"\s+", " ", s).strip().lower()


class Catalog:
    """Every item an NPC can carry: this module's packs first (Corgo's document is the NPCs' source too),
    then the 0.92.4 snapshot."""

    def __init__(self, module_packs, core, aliases):
        self.core = core
        self.aliases = {norm(k): v for k, v in aliases["aliases"].items()}
        self.unbuilt = {norm(k): v for k, v in aliases["unbuilt"].items()}
        self.skill_aliases = aliases["skills"]
        self.by_name = {}
        for pack, docs in module_packs.items():
            for d in docs:
                if d.get("_key", "").startswith("!items!"):
                    self.by_name.setdefault(norm(d["name"]), []).append((f"module:{pack}", d))
        for d in core["items"]:
            self.by_name.setdefault(norm(d["name"]), []).append((d["pack"], d))
        self.unresolved = {}   # name -> where it was seen
        self.used_unbuilt = set()

    def pick(self, name, slot):
        hits = self.by_name.get(norm(name), [])
        if not hits:
            return None
        module = [d for p, d in hits if p.startswith("module:")]
        if module:
            return module[0]
        # Within the snapshot: the slot's pack kinds first, then core before Black Chrome before the DLC.
        order, tops = PACK_PREFERENCE[slot], ["core", "black-chrome", "dlc"]

        def rank(hit):
            top, kind = hit[0].split("/", 1)
            kind = re.sub(r"^.*?(weapons-branded|weapons|armor|cyberware|gear|clothing|ammo|drugs|programs|"
                          r"upgrades)$", r"\1", kind)
            return (order.index(kind) if kind in order else len(order), tops.index(top))
        return min(hits, key=rank)[1]

    def alias(self, name, parent=None):
        """-> (target name, note). An alias is a name, {"name", "note"}, or {"by_parent": {parent: name}} for a
        part whose item depends on what it is installed in ("Hardened Shielding" in a Cyberarm or a leg)."""
        a = self.aliases.get(norm(name), name)
        if isinstance(a, dict) and "by_parent" in a:
            a = {norm(k): v for k, v in a["by_parent"].items()}.get(norm(parent or ""), name)
        if isinstance(a, dict):
            return a["name"], a.get("note")
        return a, None

    def resolve(self, name, slot, where, parent=None, gloss=()):
        """-> (item or None, reason it has no item or None, alias note or None). A gloss that names a variant
        ("Militech M221 Saratoga (Civilian)") is tried first. Records anything neither resolved nor unbuilt."""
        if norm(name) in self.unbuilt:
            self.used_unbuilt.add(norm(name))
            return None, self.unbuilt[norm(name)], None
        target, note = self.alias(name, parent)
        if norm(target) in self.unbuilt:
            self.used_unbuilt.add(norm(target))
            return None, self.unbuilt[norm(target)], None
        item = next((self.pick(f"{target} ({g})", slot) for g in gloss if self.pick(f"{target} ({g})", slot)),
                    None) or self.pick(target, slot)
        if item is None:
            self.unresolved.setdefault(name, where)
        return item, None, note


class Actor:
    def __init__(self, rec, cat):
        self.rec, self.cat = rec, cat
        self.id = doc_id("npc", f"{rec['faction']}:{rec['name']}")
        self.items, self.notes, self.installed = [], {}, []
        self.cyberware = []     # cyberware not installed in a parent yet; install_cyberware places it
        self.cyberweapons = []  # weapon rows that are cyberware; build_cyberweapons places them
        self.seen = {}
        self.where = f"{rec['file']}: {rec['name']}"

    def note(self, section, text):
        self.notes.setdefault(section, []).append(text)

    def embed(self, src, rename=None, **system):
        item = copy.deepcopy(src)
        item.pop("pack", None)
        name = rename or item["name"]
        key = f"{item['type']}:{name}"
        self.seen[key] = self.seen.get(key, 0) + 1
        iid = doc_id("npc-item", f"{self.id}:{key}:{self.seen[key]}")
        item.update(_id=iid, _key=f"!actors.items!{self.id}.{iid}", name=name, folder=None, sort=0,
                    ownership={"default": 0})
        item.setdefault("flags", {})
        item["system"].update(system)
        if "installedItems" in item["system"]:
            item["system"]["installedItems"]["list"] = []
        effects = []
        for e in item.get("effects", []):
            e = copy.deepcopy(e)
            eid = doc_id("npc-effect", f"{iid}:{e['_id']}")
            e.update(_id=eid, _key=f"!actors.items.effects!{self.id}.{iid}.{eid}")
            e["origin"] = None
            effects.append(e)
        item["effects"] = effects
        self.items.append(item)
        return item

    def has(self, name):
        return any(norm(i["name"]) == norm(name) for i in self.items)


def install(parent, child):
    parent["system"]["installedItems"]["list"].append(child["_id"])


def first_dice(s):
    m = re.search(r"\d+d6", s or "")
    return m.group(0) if m else None


def quality_of(node):
    text = " ".join([node["name"]] + node["gloss"])
    if re.search(r"(^|\W)PQ(\W|$)", text):
        return "poor"
    if re.search(r"(^|\W)EQ(\W|$)", text):
        return "excellent"
    return None


def strip_prefixes(name):
    """'TUp Kanabo' -> ('Kanabo', ['Tech Upgrade']); 'PQ Medium Melee' -> ('Medium Melee', [])."""
    tags = []
    if re.match(r"TUp\b", name):
        tags.append("Tech Upgrade")
        name = re.sub(r"^TUp\s*", "", name)
    name = re.sub(r"^(?:PQ|EQ)\s+", "", name)
    return name.strip(), tags


# ---------------------------------------------------------------- the parts of an actor

def build_skills(a, stats):
    rec, core = a.rec, a.cat.core
    listed = {}
    for s in rec["skills"]:
        name = a.cat.skill_aliases.get(s["name"], s["name"])
        listed[name] = s
        if s["alt"]:
            a.note("Situational skill values", f"{name} {s['base']} ({s['alt']})")
    bases = {n: s["base"] for n, s in listed.items()}
    if rec["layout"] == "com":
        for name in ATTACK_SKILLS:
            bases.setdefault(name, rec["com"])
    srcs = {d["name"]: d for d in core["skills"]}
    extra = {d["name"]: d for d in core["items"] if d["type"] == "skill"}
    template = {"Local Expert": srcs.get("Local Expert (Your Home)"), "Language": extra["Language (Japanese)"],
                "Martial Arts": extra["Martial Arts (Karate)"]}
    # A specialty skill the block lists replaces the core placeholder ("Local Expert (Your Home)").
    order = [n for n in srcs if n != "Local Expert (Your Home)"] + [n for n in bases if n not in srcs]
    if not any(n.startswith("Local Expert") for n in bases):
        order.append("Local Expert (Your Home)")
    for name in order:
        src = srcs.get(name) or extra.get(name) or template.get(name.split(" (")[0])
        if src is None:
            a.cat.unresolved.setdefault(f"skill {name}", a.where)
            continue
        stat = src["system"]["stat"]
        level = bases.get(name, stats[stat]) - stats[stat]
        if level < 0:
            a.note("Build warnings", f"{name}: printed base is below its STAT; level set to 0")
            level = 0
        a.embed(src, rename=name, level=level)


def build_roles(a):
    for r in a.rec["roles"]:
        detail = f" ({r['detail']})" if r["detail"] else ""
        if r["role"] not in CORE_ROLES:
            a.note("Role abilities", f"{r['role']}: {r['ability']} {r['rank']}{detail}. No Foundry item; "
                                     f"see the Lawman / Enforcer Role Tweak in Corgo's document.")
            continue
        src = next(d for d in a.cat.core["items"] if d["type"] == "role" and d["name"] == r["role"])
        a.embed(src, rank=r["rank"])
        if detail:
            a.note("Role abilities", f"{r['role']}: {r['ability']} {r['rank']}{detail}")
    for t in a.rec["enforcer"]:
        a.note("Role abilities", f"Enforcer: {t}")


UNARMED = re.compile(r"(Braw\w*|Martial Arts)\b.*?\bBODY (\d+)")   # "Brawing (BODY 6)" occurs once


def build_unarmed(a, w, stats):
    m = UNARMED.match(w["name"])
    body = int(m.group(2))
    kind = "Martial Arts" if m.group(1) == "Martial Arts" else "Unarmed"
    if body != stats["body"]:
        a.note("Build warnings", f"{w['name']}: BODY {body}, but DS gives BODY {stats['body']}")
    table = next((d for top, d in UNARMED_DAMAGE if body <= top), "4d6")
    printed = first_dice(w["damage"])
    fields = {"equipped": "equipped"}
    if printed and printed != table:
        fields.update(unarmedAutomaticCalculation=False, damage=printed)
        a.note("Build warnings", f"{kind}: printed {printed}; the BODY table gives {table}. The printed value "
                                 "is used.")
    src = next(d for d in a.cat.core["items"] if d["type"] == "weapon" and d["name"] == kind)
    a.embed(src, **fields)


def weapon_line(w):
    return f"ROF {(w['rof'] or '').replace('ROF ', '')}, {w['damage']}"


def build_weapon(a, w):
    name = w["name"]
    if name.startswith(("GM’s Choice", "GM's Choice")):
        a.note("Weapons", f"{name}: {weapon_line(w)}")
        return
    if name.startswith("Martial Arts ("):       # full layout: the style's attack row, damage from BODY
        build_unarmed(a, {**w, "name": f"Martial Arts (BODY {a.stats['body']})"}, a.stats)
        if w.get("notes"):
            a.note("Weapons", f"{name}: {w['notes']}")
        return
    node = parse_node(re.sub(r"^OPTIONAL:\s*", "", name))
    base, tags = strip_prefixes(node["name"])
    item, reason, alias_note = a.cat.resolve(base, "weapon", a.where, gloss=node["gloss"])
    rename = None
    if item is None and reason is None:
        # A named weapon with no item of its own: the core generic of the class its gloss names.
        cls = next((c for pat, c in WEAPON_CLASSES for g in [base] + node["gloss"] if re.search(pat, g)), None)
        if cls:
            a.cat.unresolved.pop(base, None)
            item = a.cat.pick(cls, "weapon")
    if item is not None and item["name"] in GENERIC_WEAPONS and norm(base) != norm(item["name"]):
        rename = base                        # keep the printed name on a generic stand-in
    if item is None:
        a.note("Weapons", f"{name}: {weapon_line(w)}" + (f" (not built: {reason})" if reason else ""))
        return
    if item["type"] == "cyberware":
        # A cyberweapon row ("Spring-Loaded Dual Mantis Blades"): the cyberware line normally lists the piece;
        # embed it only if that line does not.
        a.cyberweapons.append((item, name, w))
        return
    if item["type"] == "itemUpgrade":
        # An underbarrel weapon row: install it in the weapon listed above it.
        host = next((i for i in reversed(a.items) if i["type"] == "weapon" and i["system"].get("installedItems")),
                    None)
        up = a.embed(item)
        if host:
            install(host, up)
        a.note("Weapons", f"{up['name']}: {weapon_line(w)}" + (f" (installed in {host['name']})" if host else ""))
        return
    fields = {"equipped": "equipped"}
    quality = quality_of(node)
    if quality and "quality" in item["system"]:
        fields["quality"] = quality
    dice, rof = first_dice(w["damage"]), re.search(r"\d+", w["rof"] or "")
    if dice and item["system"].get("damage") != dice:
        fields["damage"] = dice
    if rof and item["system"].get("rof") != int(rof.group(0)):
        fields["rof"] = int(rof.group(0))
    weapon = a.embed(item, rename=rename, **fields)
    extra = "; ".join(filter(None, [", ".join(tags), ", ".join(node["gloss"]), alias_note, w.get("notes")]))
    if rename or extra or "&" in (w["damage"] or "") or w["damage"].count("d6") > 1:
        a.note("Weapons", f"{weapon['name']}: {weapon_line(w)}" + (f". {extra}" if extra else "")
                          + (f" (built on the core {item['name']})" if rename else ""))
    if w.get("ammo") and w["ammo"] != "N/A":
        a.note("Weapons", f"{weapon['name']} ammunition: {w['ammo']}")
    for child in node["children"]:
        build_child(a, weapon, child)


def build_child(a, parent, node, printed_parent=None):
    """Something installed in a weapon, armor, or cyberware: installed if the parent takes it, else carried."""
    base, tags = strip_prefixes(node["name"])
    item, reason, alias_note = a.cat.resolve(base, "child", a.where, parent=printed_parent or parent["name"],
                                             gloss=node["gloss"])
    if item is None:
        a.note("Not built", f"{node['raw']} (in {parent['name']})" + (f": {reason}" if reason else ""))
        return
    inside = parent["system"].get("installedItems", {}).get("list", [])
    if any(i["_id"] in inside and i["name"] == item["name"] for i in a.items):
        return                               # listed twice (armor table and gear line)
    # Cyberware listed inside a foundational piece of another type (Corgo's Integrated Netstation sits in a
    # Cyberarm but is neuralware here) goes where installCyberware would put it, not into the listed parent.
    mismatched = (item["type"] == "cyberware" and parent["type"] == "cyberware"
                  and parent["system"].get("isFoundational") and item["system"]["type"] != parent["system"]["type"])
    if mismatched:
        a.note("Gear details", f"{item['name']}: listed in {parent['name']}; installed with the other "
                               f"{item['system']['type']} cyberware instead")
    for _ in range(node["qty"]):
        child = a.embed(item)
        slots = parent["system"].get("installedItems")
        if slots and child["type"] in slots.get("allowedTypes", []) and not mismatched:
            install(parent, child)
        elif child["type"] == "cyberware":
            a.cyberware.append(child)
        for grandchild in node["children"]:
            build_child(a, child, grandchild, base)
    detail = tags + node["gloss"] + ([alias_note] if alias_note else [])
    if detail:
        a.note("Gear details", f"{item['name']}: {'; '.join(detail)}")


def build_armor(a):
    external = {}
    armor = a.rec["armor"]
    melee = []
    done = {}
    for loc in ("head", "body"):
        slot = armor.get(loc)
        if not slot:
            continue
        melee.append(str(slot["half"]))
        if norm(slot["name"]) in ("none", "n/a", ""):
            continue
        node = parse_node(re.sub(r"\s*\((?:Both have|Attached to)[^)]*\)", "", slot["name"]))
        base, tags = strip_prefixes(node["name"])
        both = re.search(r"\((Both have[^)]*)\)", slot["name"])
        if both:
            a.note("Armor", f"{both.group(1)}.")
        if norm(base) in done:          # the same piece covers both locations
            item = done[norm(base)]
            item["system"][f"{loc}Location"]["sp"] = slot["sp"]
            item["system"][f"is{loc.title()}Location"] = True
            external[f"currentArmor{loc.title()}"] = {"id": item["_id"], "value": slot["sp"], "max": slot["sp"]}
            for child in node["children"]:
                build_child(a, item, child, base)
            continue
        located = f"{a.cat.alias(base)[0]} ({loc.title()})"   # core armor is one item per location
        src, reason, alias_note = a.cat.resolve(located if a.cat.pick(located, "armor") else base, "armor",
                                                a.where)
        if src is None:
            a.note("Armor", f"{loc.title()}: {slot['name']}, SP {slot['sp']}"
                            + (f" (not built: {reason})" if reason else ""))
            continue
        if src["type"] != "armor":
            a.note("Armor", f"{loc.title()}: {src['name']}, SP {slot['sp']} (not an armor item in Foundry; "
                            "track its SP by hand)")
            a.embed(src, equipped="equipped")
            continue
        fields = {"equipped": "equipped", f"is{loc.title()}Location": True,
                  f"is{('Body' if loc == 'head' else 'Head')}Location": False}
        item = a.embed(src, **fields)
        item["system"][f"{loc}Location"]["sp"] = slot["sp"]
        detail = "; ".join(filter(None, [", ".join(tags), alias_note]))
        if slot["sp"] != src["system"][f"{loc}Location"]["sp"] or detail:
            a.note("Armor", f"{item['name']}: SP {slot['sp']} as printed"
                            + (f" (the item is SP {src['system'][f'{loc}Location']['sp']})"
                               if slot["sp"] != src["system"][f"{loc}Location"]["sp"] else "")
                            + (f"; {detail}" if detail else ""))
        if slot.get("notes"):
            a.note("Armor", f"{item['name']}: {slot['notes']}")
        done[norm(base)] = item
        external[f"currentArmor{loc.title()}"] = {"id": item["_id"], "value": slot["sp"], "max": slot["sp"]}
        for child in node["children"]:
            build_child(a, item, child, base)
    if melee:
        a.note("Armor", f"Melee SP (head/body): {'/'.join(melee)}")
    return external


def build_gear(a, node):
    base, tags = strip_prefixes(node["name"])
    item, reason, alias_note = a.cat.resolve(base, "gear", a.where, gloss=node["gloss"])
    if item is None:
        a.note("Not built", node["raw"] + (f": {reason}" if reason else ""))
        return
    worn = next((i for i in a.items if i["type"] == "armor" and norm(i["name"]) == norm(item["name"])), None)
    if worn:                                 # already worn from the armor table
        for child in node["children"]:
            build_child(a, worn, child, base)
        return
    detail = tags + node["gloss"] + ([alias_note] if alias_note else [])
    if detail:
        a.note("Gear details", f"{item['name']}: {'; '.join(detail)}")
    stack = "amount" in item["system"]
    for _ in range(1 if stack else node["qty"]):
        fields = {"amount": node["qty"]} if stack else {}
        if item["type"] in ("gear", "clothing", "armor", "weapon") and "equipped" in item["system"]:
            fields["equipped"] = "equipped" if item["type"] in ("armor", "weapon") else "carried"
        parent = a.embed(item, **fields)
        if parent["type"] == "cyberware":
            a.cyberware.append(parent)
        for child in node["children"]:
            build_child(a, parent, child, base)


def build_cyberweapons(a):
    for item, name, w in a.cyberweapons:
        if not a.has(item["name"]):
            a.cyberware.append(a.embed(item))
        a.note("Weapons", f"{name}: {weapon_line(w)} ({item['name']})")


def install_cyberware(a):
    """Foundational pieces into the actor; anything else not already in a parent goes into the first installed
    foundational piece of its own type, as cpr-actor.js installCyberware requires."""
    nested = {i for it in a.items for i in it["system"].get("installedItems", {}).get("list", [])}
    pending = [c for c in a.cyberware if c["_id"] not in nested]
    for c in pending:
        if c["system"].get("isFoundational"):
            a.installed.append(c["_id"])
    for c in pending:
        if c["system"].get("isFoundational"):
            continue
        hosts = [i for i in a.items if i["_id"] in a.installed and i["type"] == "cyberware"
                 and i["system"].get("isFoundational") and i["system"]["type"] == c["system"]["type"]]
        if hosts:
            install(hosts[0], c)
        else:
            a.note("Build warnings", f"{c['name']}: no foundational {c['system']['type']} to install it in; "
                                     "carried, not installed")


def build_programs(a):
    for line in a.rec["programs"]:
        for name in [p.strip() for p in line.split(",")]:
            m = re.match(r"(.*?)\s*(?:x(\d+)|\[x(\d+)\])$", name)
            name, qty = (m.group(1), int(m.group(2) or m.group(3))) if m else (name, 1)
            item, reason, _ = a.cat.resolve(name, "gear", a.where)
            if item is None:
                a.note("Programs", name + (f": {reason}" if reason else ""))
                continue
            for _ in range(qty):
                a.embed(item)


def notes_html(a):
    order = ["Weapons", "Armor", "Role abilities", "Situational skill values", "Gear details", "Programs",
             "Not built", "Build warnings"]
    rec = a.rec
    head = [f"<p><strong>Threat level:</strong> {html_escape(rec['level'])}<br>",
            f"<strong>Facedown #:</strong> {rec.get('facedown', rec['rep'] + a.cool)}"
            + (f"<br>\n<strong>COM#:</strong> {rec['com']}" if rec.get("com") else "")
            + (f"<br>\n<strong>Weapons:</strong> {html_escape(rec['weapon_choice'])}" if rec.get("weapon_choice") else "")
            + "</p>"]
    body = []
    for sec in order:
        if sec in a.notes:
            body.append(f"<p><strong>{sec}:</strong></p>\n<ul>\n"
                        + "\n".join(f"<li>{html_escape(t)}</li>" for t in a.notes[sec]) + "\n</ul>")
    return "\n".join(head + body)


def build_actor(rec, cat, folder_id):
    a = Actor(rec, cat)
    if rec["layout"] == "full":
        stats = {s: rec["stats"][s]["value"] for s in STATS}
        maxes = {s: rec["stats"][s]["max"] for s in STATS}
    else:
        stats = {s: 0 for s in STATS}
        stats.update(ref=rec["init"], cool=rec["cool"], move=rec["move"], body=rec["ds"])
        maxes = dict(stats)
    a.cool, a.stats = stats["cool"], stats

    build_skills(a, stats)
    build_roles(a)
    for src in cat.core["coreCyberware"]:
        a.installed.append(a.embed(src)["_id"])
    for w in rec["weapons"]:
        if UNARMED.match(w["name"]):
            build_unarmed(a, w, stats)
        else:
            build_weapon(a, w)
    external = build_armor(a)
    for node in rec["gear"]:
        build_gear(a, node)
    build_cyberweapons(a)
    build_programs(a)
    install_cyberware(a)

    emp = (stats["emp"], maxes["emp"])
    humanity = (emp[0] * 10, emp[1] * 10) if rec["layout"] == "full" else (60, 60)
    system = {
        "stats": {s: ({"value": stats[s], "max": maxes[s]} if s in ("luck", "emp") else {"value": stats[s]})
                  for s in STATS},
        "derivedStats": {"hp": {"value": rec["hp"], "max": rec["hp"], "transactions": []},
                         "humanity": {"value": humanity[0], "max": humanity[1], "transactions": []},
                         "walk": {"value": stats["move"] * 2}, "run": {"value": stats["move"] * 4},
                         "seriouslyWounded": -(-rec["hp"] // 2),
                         "deathSave": {"basePenalty": 0, "penalty": 0, "value": 0},
                         "currentWoundState": "notWounded"},
        "externalData": {k: external.get(k, {"id": "", "value": 0, "max": 0})
                         for k in ("currentArmorBody", "currentArmorHead", "currentArmorShield", "currentWeapon")},
        "information": {
            "alias": "",
            "description": (f"<p>{html_escape(rec['background'])}</p>\n" if rec["background"] else "")
                           + f'<p><em>From <a href="{NPC_SOURCE_URL}">{html_escape(NPC_SOURCE_BOOK)}</a> by '
                             f"Corgopolis ({html_escape(rec['faction'].title())}).</em></p>",
            "history": "",
            "notes": notes_html(a)},
        "reputation": {"value": rec["rep"], "transactions": []},
        "roleInfo": {"activeRole": next((r["role"] for r in rec["roles"] if r["role"] in CORE_ROLES), ""),
                     "activeNetRole": ""},
        "installedItems": {"allowed": True, "allowedTypes": ["cyberware"], "list": a.installed},
        "weapons": {},
    }
    return {"_id": a.id, "_key": f"!actors!{a.id}", "name": rec["name"], "type": "mook", "img": MOOK_IMG,
            "system": system, "items": a.items, "effects": [], "folder": folder_id, "sort": 0,
            "ownership": {"default": 0}, "flags": {},
            "prototypeToken": {"name": rec["name"], "actorLink": False, "disposition": -1,
                               "bar1": {"attribute": "derivedStats.hp"}}}


def build_all(module_packs):
    records = load_json(PARSED)
    cat = Catalog(module_packs, load_json(CORE), load_json(ALIASES))
    docs, folders, names = [], {}, set()
    for rec in records:
        # Two blocks in a faction can share the table's name (ASSAULT SPECIALIST and ELITE ASSAULT SPECIALIST
        # are both "Arasaka Assault Specialist"); the later one is named from its section title instead.
        if (rec["faction"], rec["name"]) in names:
            rec["name"] = f"{rec['faction'].title()} {rec['title'].title()}"
        names.add((rec["faction"], rec["name"]))
        faction = rec["faction"].title()
        if faction not in folders:
            fid = doc_id(f"folder:{PACK}", faction)
            folders[faction] = fid
            docs.append({"_id": fid, "_key": f"!folders!{fid}", "name": faction, "type": "Actor", "folder": None,
                         "sorting": "a", "sort": len(folders) * 100000, "color": None, "description": "",
                         "flags": {}})
        docs.append(build_actor(rec, cat, folders[faction]))
    if cat.unresolved:
        lines = "\n".join(f"    {n!r}  ({w})" for n, w in sorted(cat.unresolved.items()))
        raise SystemExit(f"{len(cat.unresolved)} NPC names match no item; add each to text/npc_aliases.json "
                         f"(aliases, or unbuilt with the reason):\n{lines}")
    stale = set(cat.unbuilt) - cat.used_unbuilt
    if stale:
        raise SystemExit(f"text/npc_aliases.json 'unbuilt' names no stat block uses: {sorted(stale)}")
    return {PACK: docs}
