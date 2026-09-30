"""Regression test for the entry lookup and its HTML conversion, built from the placeholder document in
tests/fixtures/ (no content from Corgo's document), so it runs anywhere.
Run: python3 tests/test_entry_text.py"""
import glob, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(tempfile.gettempdir()) / "c77-entry-test"
# The fixture covers a few dozen headings, so the build has to be told that the rest have no entry.
build = subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "--doc",
                        str(ROOT / "tests/fixtures/sample-doc.md"), "--out", str(OUT), "--allow-missing-entries"],
                       capture_output=True, text=True, errors="replace")
if build.returncode:
    # Show what the build actually said. A bare CalledProcessError here hides the real failure, which is
    # the one thing you need to see.
    print("the fixture build failed:\n")
    print(build.stdout or "", build.stderr or "", sep="\n")
    sys.exit(1)


def desc(pack, name):
    for f in glob.glob(str(OUT / pack / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("name") == name:
            return d["system"]["description"]["value"]
    return ""


CHECKS = [
    ("weapons", "Arasaka HJKE-11 Yukimura", ["<em>Placeholder Yukimura flavor.</em>", "Placeholder Yukimura special"]),
    ("weapons", "Ara-Sake Mama-Yuri", ["Placeholder Ironfake group intro", "Placeholder Mama-Yuri text"]),
    ("weapon-attachments", "Foregrip", ["<li>First placeholder option</li>", "with a link and an escaped * asterisk"]),
    ("weapon-attachments", "Burst Mod Internals (Fixed)", ["<td>Placeholder A</td>"]),
    ("armor-upgrades", "Nanoweave Rebuild (Padded)", ["This deeper heading should still belong"]),
    ("armor", 'Arasaka "Kagami" Neo-Kabuto', ["Placeholder Kagami text"]),
    ("gear", "MaxDoc Inhaler", ["Placeholder inhaler text"]),
    ("gear", "Militech SPECTER", ["Placeholder frame intro"]),
    ("gear", "Militech EX-75 IronWind", ["Placeholder ironwind text"]),
    ("gear", "Vial of Neurotoxin", ["Placeholder poison group rule", "Placeholder neurotoxin text"]),
    ("gear", "Ol' Donkey", ["Placeholder donkey text", "Addicted Primary"]),
    ("cyberware", "Superchrome Skin", ["Placeholder superchrome text."]),
    ("cyberware", "Sandevistan", ["Placeholder sandevistan text."]),
    ("cyberware-upgrades", "Defenzikov", ["Placeholder defenzikov text."]),          # enhancement (itemUpgrade)
    ("cyberware", "Gorilla Arm", ["Placeholder gorilla arm text."]),
    ("cyberware-upgrades", "Modified Plating (Thermal)", ["Placeholder modified plating text."]),
    ("cyberware", "Popup Ranged Weapon (Cyberleg)", ["Placeholder popup leg weapon text."]),
    ("operating-systems", "Militech 'Falcon' OS", ["Placeholder falcon OS text."]),
    ("cyberware", "Ocuset", ["Placeholder ocuset text."]),                            # cyberware-alternatives
    ("weapon-attachments", "Extended Magazine (Pistol)", ["Adds +6 to capacity"]),    # no entry: the module's own text
    ("armor", "Gun Shield (Light)", ["Fits a weapon's Gun Shield Mount"]),           # no entry: the module's own text
]
failed = [(p, n, [x for x in need if x not in desc(p, n)]) for p, n, need in CHECKS]
failed = [f for f in failed if f[2]]
if "Placeholder ironwind text" in desc("gear", "Militech SPECTER"):
    failed.append(("gear", "Militech SPECTER", ["frame description should stop before its weapons"]))
# An entry with nested "#### " entries must not swallow their text: Gorilla Arm owns neither Modified
# Plating's wording nor a literal markdown heading.
ga = desc("cyberware", "Gorilla Arm")
if "Placeholder modified plating text" in ga or "####" in ga:
    failed.append(("cyberware", "Gorilla Arm", ["must stop before its nested enhancements"]))
y = desc("weapons", "Arasaka HJKE-11 Yukimura")
if "(Art" in y or "**" in y or "13EnSAoiLDsC7zmL" not in y:
    failed.append(("weapons", "Yukimura", ["art credit removed, no markdown left, source link kept"]))
shutil.rmtree(OUT, ignore_errors=True)
print("FAILED:", failed) if failed else print(f"fixture build: all {len(CHECKS) + 3} checks passed")
sys.exit(1 if failed else 0)
