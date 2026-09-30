"""Build every pack source under src/packs/. Run `node tools/compile.mjs` afterwards (npm run build does both)."""
import json, re, shutil
from pathlib import Path
import argparse
import build_weapons, build_upgrades, build_armor, build_gear, build_cyberware, build_iconics, \
    build_iconic_weapons, dvtables, original_text
from common import doc_id, MODULE_ID

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "src/packs"
# Corgo's document. He gave permission for this conversion and for his text to ship, so when the
# export is present his wording is what gets built.
DOC = ROOT / "data/corgo-77-v3.md"


def write_pack(name, docs):
    out = PACKS / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for d in docs:
        slug = re.sub(r"[^a-z0-9]+", "-", d["name"].lower()).strip("-")
        json.dump(d, open(out / f"{slug}.{d['_id']}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{name}: {len(docs)} documents")


MACROS = {
    "Use Corgo's 77 DV Tables": f'''// Point Cyberpunk RED - Core's DV ruler at this module's DV tables
// (Solo of Fortune 2045 range tables plus the core table names). World setting; GM only.
if (!game.user.isGM) return ui.notifications.warn("Only a GM can change the DV table compendium.");
const pack = "{MODULE_ID}.dv-tables";
if (!game.packs.get(pack)) return ui.notifications.error(`Compendium ${{pack}} not found. Is the module enabled?`);
await game.settings.set("cyberpunk-red-core", "dvRollTableCompendium", pack);
ui.notifications.info("DV tables now come from Corgo's 77 Collection (Solo of Fortune 2045).");''',
    "Restore Core DV Tables": '''// Point Cyberpunk RED - Core's DV ruler back at the system's own DV tables. GM only.
if (!game.user.isGM) return ui.notifications.warn("Only a GM can change the DV table compendium.");
const setting = game.settings.settings.get("cyberpunk-red-core.dvRollTableCompendium");
await game.settings.set("cyberpunk-red-core", "dvRollTableCompendium", setting.default);
ui.notifications.info("DV tables restored to the Cyberpunk RED - Core defaults.");''',
}


def macro_docs():
    docs = []
    for name, command in MACROS.items():
        _id = doc_id("macro", name)
        docs.append({"_id": _id, "_key": f"!macros!{_id}", "name": name, "type": "script", "scope": "global",
                     "command": command, "img": "icons/svg/dice-target.svg", "folder": None, "sort": 0,
                     "ownership": {"default": 0}, "flags": {}})
    return docs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-text", default=str(DOC) if DOC.exists() else None,
                    help="export of Corgo's doc; his wording is used in descriptions "
                         "(default: data/corgo-77-v3.md when present)")
    ap.add_argument("--out", default=str(PACKS), help="where to write pack sources (default src/packs)")
    args = ap.parse_args()
    PACKS = Path(args.out).resolve()
    if args.original_text:
        original_text.enable(args.original_text)
    plan = dvtables.DvPlan()
    write_pack("weapons", build_weapons.build_pack(plan))
    for name, docs in build_gear.build_all(plan).items():  # before the DV tables: its weapons use the plan
        write_pack(name, docs)
    compat = json.load(open(ROOT / "tools/compat/schism-sof45.json", encoding="utf-8"))
    recs = dvtables.register_compat(plan, compat)
    json.dump({k: {"recommended": v[0], "current": v[1]} for k, v in recs.items()},
              open(ROOT / "tools/compat/schism-dv-recommendations.json", "w", encoding="utf-8"), indent=1)
    for k, (rec, cur) in sorted(recs.items()):
        if rec != cur:
            print(f"  Schism weapon needs DV table change: {k}: {cur or '(none)'} -> {rec}")
    write_pack("macros", macro_docs())
    # Every builder that takes the plan runs before the DV tables are written, or a table only its weapons
    # need is registered after the pack has already been built (that is what "DV Long-Barrel Pistol [SMG]"
    # for Archangel was). Build first, write the tables, then write the packs.
    packs = {**build_upgrades.build_all(), **build_armor.build_all(),
             **build_cyberware.build_all(), **build_iconics.build_all(),
             **build_iconic_weapons.build_all(plan)}
    write_pack("dv-tables", dvtables.build_docs(plan))
    for name, docs in packs.items():
        write_pack(name, docs)
    if not original_text.enabled():
        print(f"note: {DOC.relative_to(ROOT)} not present, so descriptions fall back to the "
              "rewritten text in text/*.json")
    if original_text.enabled():
        print(f"original text used for {len(original_text.FOUND)} items; kept rewritten text for "
              f"{len(original_text.MISSING)} lookups with no matching entry:")
        for m in original_text.MISSING:
            print("   ", m)
