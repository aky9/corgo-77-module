"""Regression test for the opt-in original-text build, using placeholder text (no content from Corgo's doc).
Run: python3 tests/test_original_text.py"""
import glob, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(tempfile.gettempdir()) / "c77-original-test"
build = subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "--original-text",
                        str(ROOT / "tests/fixtures/original-sample.md"), "--out", str(OUT)],
                       capture_output=True, text=True, errors="replace")
if build.returncode:
    # Show what the build actually said. A bare CalledProcessError here hides the real failure, which is
    # the one thing you need to see.
    print("the original-text build failed:\n")
    print(build.stdout or "", build.stderr or "", sep="\n")
    sys.exit(1)


def desc(pack, name):
    for f in glob.glob(str(OUT / pack / "*.json")):
        d = json.load(open(f, encoding="utf-8"))
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
    ("weapons", "Arasaka Tamayura", ["Proprietary Armor-Piercing ammo costs 20eb"]),        # not in fixture: rewritten
    ("weapon-attachments", "Extended Magazine (Pistol)", ["Adds +6 to capacity"]),          # no Corgo entry: rewritten
    ("cyberware", "Exoglove", ["A fingerless Smart Glove"]),                                # not in fixture: rewritten
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
print("FAILED:", failed) if failed else print(f"original-text build: all {len(CHECKS) + 2} checks passed")
sys.exit(1 if failed else 0)
