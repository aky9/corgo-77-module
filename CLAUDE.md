# Developing the Corgo's 77 Collection module

This guide explains how the module is built from Corgo's document, where each part lives, the rules to
follow when adding or changing content, and the conventions taken from the Cyberpunk RED - Core 0.92.4
source. Read it before changing anything under `tools/`, `text/`, or `src/packs/`.

The module is a Foundry conversion of Corgo's 77 Collection V3 by Corgopolis. His document, exported to
`data/corgo-77-v3.md`, is the source: the parsers read every stat block from it, and every item's
description is its entry from it. This repository adds the automation data and the Foundry notes.

## Requirements and commands

You need Python 3 (standard library only) and Node 18 or newer. On a fresh clone, `./setup.sh` runs
everything below and stops at the first failure. By hand:

    npm ci
    npm run parse            # data/corgo-77-v3.md -> data/*.parsed.json (git-ignored, so run once per clone)
    npm run build            # parsed data + text/*.json + the document -> src/packs -> dist/corgo-77-collection
    npm run validate         # checks the built packs against CPR 0.92.4 and the Solo of Fortune 2045 module
    npm run check:entries    # per-item check that each description carries its own entry's text
    npm test                 # entry lookup checks against the placeholder document in tests/fixtures/

To build from a newer export of the document, replace `data/corgo-77-v3.md` and run `npm run parse` and
`npm run build` again. `tools/build.py --doc <path> --out <dir>` reads the entry text from another export
and writes the packs elsewhere, which is how the tests build from their placeholder document; the stat
blocks still come from the parsed data, and `tools/compat/schism-dv-recommendations.json` is refreshed
either way.

Run every command from the repository root. All file I/O is explicit UTF-8, so the build behaves the same
on Windows, macOS, and Linux. Item names include characters a legacy Windows console cannot show ("Ć",
curly quotes, "♦"); the tools request UTF-8 output and fall back to replacement characters where the console
cannot encode them. To test a change against such a console, run with `PYTHONIOENCODING=cp437`
(`$env:PYTHONIOENCODING="cp437"` in PowerShell).

## How the build works

The build is a pipeline of four steps, each reading the previous step's output:

1. **Parse.** `npm run parse` runs the five parsers in `tools/parse_*.py`. Each reads one or more chapters
   of `data/corgo-77-v3.md` and writes the stat blocks it finds to `data/*.parsed.json`. These files are
   git-ignored because they are derived; regenerate them whenever the document changes.
2. **Build.** `tools/build.py` runs every pack builder in `tools/build_*.py`. A builder joins the parsed
   stats with the automation data in `text/*.json`, looks up the item's entry in Corgo's document through
   `tools/entry_text.py`, and writes one JSON document per item or folder to `src/packs/<pack>/`. The
   build fails if the document is missing or if any item's entry cannot be found.
3. **Compile.** `tools/compile.mjs` compiles each `src/packs/<pack>/` into a LevelDB pack under
   `dist/corgo-77-collection/packs/` with the Foundry CLI, and copies `module/` in beside them.
4. **Validate.** `tools/validate.mjs` reads the compiled packs back and checks them against a snapshot of
   the 0.92.4 system and the Solo of Fortune 2045 compatibility file.

`src/packs/` is committed and is the source of truth for what ships. Item IDs are stable: `tools/common.py`
derives each document's ID from its name and pack, so rebuilding never changes an ID and never breaks a
world that already holds the item.

## Layout

- `data/corgo-77-v3.md`: text export of Corgo's document (snapshot of Sept 12, 2026). The parsers and
  `entry_text.py` read it; nothing copies it into `dist/`.
- `module/`: `module.json` and the end-user README. Copied into `dist/` as-is, so the manifest version and
  the README's pack list are edited here.
- `src/packs/<pack>/`: one JSON file per document, as the compiler expects.
- `tools/common.py`: stable IDs, name casing, cost parsing, the description template, and folder documents.
- `tools/parse_weapons.py`: the Weapon Catalog stat blocks.
- `tools/parse_upgrades.py`: the Attachment Catalog, Mod Catalog, and Ammunition.
- `tools/parse_cyberware.py`: the Cyberware, Operating Systems, and Cyberware Alternatives chapters. Records
  which parent a nested `####` entry belongs to. `SKIP_GROUPS` and `SKIP_HEADINGS` name what is left out.
- `tools/parse_iconics.py`, `tools/parse_iconic_weapons.py`: the Iconic Cyberware, Iconic Gear, and Iconic
  Weapons chapters.
- `tools/build_weapons.py`: maps Corgo's stats onto the 0.92.4 weapon schema. The class, range-table, and
  skill mapping tables are at the top of the file.
- `tools/build_upgrades.py`: attachments (including the Capacity Chart magazines), mods, and ammo.
- `tools/build_armor.py`: armor, iconic armor, Gun Shields, and armor and shield upgrades.
- `tools/build_gear.py`: general gear, External Linear Frames (the SPECTER's weapons are built with the
  weapon builder), poisons, pharmaceuticals, and street drugs.
- `tools/build_cyberware.py`: cyberware, enhancements, operating systems, and cyberdecks. Its docstring
  documents the schema conventions.
- `tools/build_iconics.py`, `tools/build_iconic_weapons.py`: the Iconic packs. They reuse the builders above
  rather than repeating their conventions.
- `tools/dvtables.py`: builds the DV Tables pack and decides each weapon's DV table. Its docstring explains
  how 0.92.4 matches Autofire tables by name.
- `tools/entry_text.py`: finds an item's entry in the document by heading, within the right section, and
  converts it to HTML. Its docstring lists the items that have no entry.
- `tools/check_entries.py`: the `check:entries` command.
- `tools/cpr-0.92.4-reference.json`: a snapshot of 0.92.4's allowed values, field sets, and item names, so
  building and validating need no system checkout. The cyberware field sets and enums come from the
  0.92.4 `CyberwareDataModel` and its mixins, checked against all 186 cyberware items the system ships.
- `tools/compat/schism-sof45.json`: table names, weapon DV tables, and item names from Schism989's Solo of
  Fortune 2045 module (v1.1.0). Refresh it if that module updates.
- `tools/compat/schism-dv-recommendations.json`: generated by the build; the DV table each of Schism989's
  weapons should use.
- `text/*.json`: per-pack automation data and Foundry notes (see the next section).
- `text/dv_tables_sof45.json`, `text/dv_tables_core.json`: the Solo of Fortune 2045 DV tables, transcribed
  from Interface RED Vol. 5, and the two core tables that are copied.
- `text/enhance_targets.json`: the enhancement parents 0.92.4 has no item for, each with the reason.
- `tests/`: the `npm test` checks and the placeholder document they build from.
- `.github/workflows/`: `ci.yml` runs `./setup.sh` on every push and pull request; `release.yml` publishes a
  tagged release.
- `reference/` (git-ignored): a pinned copy of Schism989's module, used only to refresh `tools/compat/`.

## Item text and what to put where

**Every item carries its entry from Corgo's document**, in full (flavor, stats, and rules), then the
module's Foundry notes, then a link to the source. `description_html` adds only the facts the entry does
not state itself, such as "Enhances", which the sheet and the validator both need.

Follow these rules when adding or changing content:

- **Foundry guidance goes in `notes`.** A spec's `notes` list renders as the item's "Foundry notes"
  bullets. Every builder reads `spec.get("notes", [])` and appends it to the notes it works out itself.
  Do not restate the entry: the item already carries it.
- **The rest of a spec is automation data** with no equivalent in the document: `attack` and `damage` as
  `[value, situational]`, `slots`, `magazine`, `rof_override`, `secondary`, `split`, and so on.
- **Items with no entry in the document** are never looked up and carry the module's own text through the
  `rules` argument of `description_html`. `entry_text.py` lists them: the Capacity Chart magazines, the Gun
  Shields, and the armor half of Nano-Plating. Any other item whose lookup finds no entry fails the build.
- **Entries with nested `####` sub-entries** need `intro_only=True` in the lookup, or the parent's text runs
  on into its children's. `build_cyberware` passes it for Gorilla Arm, Mantis Blade, the Popup leg weapon,
  and Exoglove; `build_upgrades.nested_parents()` supplies it for Long Scope, Short Scope, and Laser Sight.
  `check:entries` catches any new case.

R. Talsorian's material ships under RTG's Homebrew Content Policy. Schism989's module has no license file:
never copy his items into this module; `reference/` stays git-ignored and users install his module
alongside.

### Export quirks the converter handles

`entry_text._to_html` corrects these artifacts of the Google Docs export. When you add a handler, run
`npm run check:entries` over all items and then scan the generated HTML for leftovers.

- A link broken across two lines ("[text" on one, "](url)" on the next). The emphasis markers either side of
  the break are dropped at the seam.
- A URL containing escaped parentheses, which a naive link regex stops short of at the first ")".
- An escaped marker pair (`\*\*text\*\*`), which the export produces wherever bold is nested inside bold or
  any formatting sits in a table. Treat these as formatting. A lone `\*` stays a literal asterisk.
- A heading's `#` markers inside a table cell, and lines of nothing but emphasis markers.

## Deliberately not built

These are left out on purpose. Do not build them without deciding the conventions first.

- The **2070s Full Body Conversions**, the **Militech Centaur Exo** cyberchair, and the **Corpochrome**
  variants, including the 14 named branded options with their own costs, Humanity Loss, and slot counts.
  Corpochrome is documented as a rule in the user guide. `parse_cyberware.SKIP_GROUPS` is where this is
  enforced.
- **Vehicles**, the **Vehicle Catalog**, and **Iconic Vehicles**. The 0.92.4 `vehicle` field set is
  untouched; settle it once, for both chapters, before building either.
- **Drones**, **Drone-related Gear**, and the **Drone Catalog**.
- **Role Tweaks**, **Netrunning**, and **Deep Diving 101**. These are rules rather than items. Journal
  entries are the likely home if they are ever added.

## Conventions taken from the 0.92.4 source

These were settled by reading the system's code. Do not re-derive them; the file each cites is where to
look if a system update changes the behaviour.

**Cyberware.**

- Corgo's cyberware is built as three document types, the way the core models the same things: `cyberware`
  for anything installed in or worn on the body, `itemUpgrade` of type `cyberware` for his "X Cyberware
  Enhancement" entries and the Operating Systems, and `cyberdeck` for the five decks the Cyberdeck Port
  OSes come with. A piece whose slot costs cross categories is typed where its slots are usable (Advanced
  Neural Link, Integrated Netstation).
- `size` is compared against free slots only when an item is installed into another **item**, never when a
  foundational piece goes onto an actor (`cpr-container.js installItems`). Core ships foundational cyberware
  at both size 0 and size 1, so the validator checks neither.
- Non-foundational cyberware can only be installed when a foundational piece of the **same** `type` is
  already installed (`cpr-actor.js installCyberware`). The nested-container search it does is what makes a
  Chipware Socket or an Advanced Neural Link a usable install target.
- Passive ware is `usage: "installed"` with a plain effect, so it applies exactly while installed.
  Activated ware is `usage: "toggled"` with the change flagged situational, so it shows as a toggle in the
  roll dialog, matching the core's Sandevistan.
- Enhancements carry no Active Effects. An upgrade's effects apply from the inventory whether or not it is
  installed, so an enhancement's bonus is described in its text with a note naming the parent to put the
  effect on.
- `humanityLoss.roll` must be a plain dice formula or a number. The system reads
  `roll.terms[0].results`, which only a DiceTerm has, so `ceil(4d6/2)` throws and shows nothing. `parse_hl`
  turns "Nd6/2 [Round Up]" into the halved dice (4d6 becomes 2d6: same range and mean) and the item says so.
- An enhancement's `enhances` target must be a real item. `validate.mjs` resolves it against the 0.92.4
  item names in the reference snapshot, the module's own built names, and the allowlist in
  `text/enhance_targets.json`, which names the parents the system lacks (Monowire, Self-ICE, the Neuroport
  Cyberdeck Port, all from Corgo's required paid content) with the reason. Matching is exact per
  "or"-separated part after stripping a parenthetical gloss. Do not loosen it: a prefix match lets a
  renamed parent pass silently, which is the breakage the check exists to catch. Corgo's Neuroport is the
  core's Neural Link, his Personal Link is Interface Plugs, and "Implanted Linear Frame (any)" maps to the
  real "Implanted Linear Frame β (Beta)". After any change here, repeat two negative tests: a typo in a
  target must fail, and a dropped allowlist entry must fail.

**Armor.**

- The system applies one penalty to REF, DEX, and MOVE and counts only the worst among worn armor. Specs
  give the penalty per stat as `[REF, DEX, MOVE]`; the item uses the worst and its description gives the
  split.
- Armor covering body and head is one item (the diving suit, Nano-Plating's armor half), matching the
  core's Subdermal Armor. The equip handler tests `isHeadLocation` before `isBodyLocation` and tracks only
  the first match, so such an item registers in the head SP slot.

**Weapons and DV tables.**

- The system picks a weapon's Autofire table by name. Weapons that share a range table but use a different
  Autofire type point at a tagged copy such as `DV Carbine [SMG]`, whose distances are identical.
  `tools/dvtables.py` decides the table for each weapon, and the validator replays the system's lookup for
  every weapon.
- The DV compendium carries every table name the core system uses, so core weapons keep working after the
  setup macro switches the DV ruler to it, and every name Schism989's module uses, so the two modules can
  run together.

**Descriptions.**

- Every block-level tag needs whitespace on one side of it. Foundry strips tags to build item-list
  summaries, tooltips, and chat previews, and without the whitespace the words either side weld together
  ("Cost: 2,000eb (Very Expensive)Type: Neuralware"). `description_html` and `entry_text._to_html` put a
  newline after each boundary tag, and the validator enforces it. Inline tags (strong, em, a) are exempt:
  the export splits words across bold runs, so dropping an inline tag with no space is the correct reading.

**Iconics and drugs.**

- Iconics carry a Category and a Fabrication cost instead of a price. `build_iconics.CATEGORY_PRICE` maps
  the category to that tier's eurodollar benchmark so repair and Tech Upgrade maths work, and every item
  says so.
- Drugs follow the core's Primary and Addiction effect pattern, plus an "Addicted Primary" effect where
  Corgo suspends the addiction penalty while the drug is active.

## Checks

Run all of these before tagging a release. The release workflow runs them too and refuses to publish if
any fails.

- `npm run validate` reads the compiled packs back and checks schema values against the 0.92.4 snapshot,
  replays every weapon's Autofire lookup, resolves every enhancement target, checks description whitespace,
  parses the macros, and confirms the DV compendium still covers Schism989's table names with no item-name
  collisions.
- `npm run check:entries` fingerprints each item's entry with its longest unique line, taken from the
  parsers' records rather than from `entry_text.py`, so a heading-matching bug cannot hide itself. It
  fails if an item carries another entry's text, which is how a parent running on into its nested
  sub-entries is caught. It reads `src/packs`, so run it after `npm run build`.
- `npm test` builds from the placeholder document in `tests/fixtures/` and checks the entry lookup and
  its HTML conversion. The placeholder covers only a few dozen headings, so that build passes
  `--allow-missing-entries`; the real build never does.

## Known gaps

Things not yet verified in Foundry, and the check that would close each one:

- The stat caps (Mechatronic Core at TECH 7 should give 8, not 9), the three enhancement slot modifiers,
  and whether Advanced Neural Link's four Neuralware slots are reachable. That last one is the typing
  decision most likely to be wrong.
- Whether body SP comes out right for a single item covering body and head, given the head-first equip
  handler described above.
- Dependencies stated in prose. `validate.mjs` resolves `enhances`, but most Iconic Cyberware is a
  `cyberware` item whose requirement sits in its rules text ("Requires Reflex Tuner") and nothing checks
  those names. A structured `requires` field on those specs, shown as a fact and resolved the same way,
  would close it.
- Two Iconic Weapons carry stats that are not Corgo's own numbers. Chaos (Royce's Pistol) ships at the
  default he states (3d6, 20 rounds, 1 SP ablation); its per-reload rerolls, 2-round single shot, and 1d12
  Critical Injury roll cannot be automated and are noted on the item. Baseball Bat X-MOD2 uses the
  0.92.4 generic Two-Handed Very Heavy Melee Weapon line because Corgo names the category but gives no
  stats.
