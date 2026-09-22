# Building the Corgo's 77 Collection module

See `HANDOFF.md` for where the project stands, what's next, and the commands to run.

Requirements: Python 3, Node 18+.

    npm install
    npm run build        # regenerates src/packs/* and compiles dist/corgo-77-collection (Python 3 + PyYAML not needed)
    node tools/validate.mjs dist/corgo-77-collection

## Corgo's text

Corgo gave permission for this conversion and for his wording to ship, so `data/corgo-77-v3.md` is tracked
here and **his text is what `npm run build` uses**. An item with an entry in his doc gets his full text
(flavor, stats, and rules) plus our Foundry notes and the source link; `description_html` keeps only the
facts he does not state himself, since his entry opens with his own stat line but "Enhances" is ours and
both the sheet and `validate.mjs` need it. The Capacity Chart magazines and Gun Shields have no single
entry, so they keep the rewritten text.

Foundry guidance - what the sheet automates for an item and what you apply by hand - belongs in an
entry's `notes` list, never inside its `rules` string. `rules` is a rewrite of Corgo's own rules and is
dropped whenever his text is present, so guidance buried in it disappears from the shipped item; `notes`
survives both paths and renders as the item's "Foundry notes" bullets. Every builder reads
`spec.get("notes", [])` and appends it to the notes it works out itself. 52 sentences were moved out of
`rules` for this reason.

**`rules` is frozen.** It is a rewrite of Corgo's own rules, written back when his text could not ship, and
`description_html` discards it whenever his text is present: 356 of the 361 rules strings no longer reach any
shipped item. It is kept only as an escape hatch - `--original-text ""` still builds a complete module with
no text of his in it, which is worth having if the permission ever has to be unwound - so do not extend it.
New content needs stats and `notes`, not a restatement of Corgo. The Iconic Weapons chapter sat unfinished
for 85 items because they were gated on prose this build throws away.

If the export is missing the build says so and falls back to `text/*.json` for everything. That fallback is
the only thing those files' `rules` strings are still for; the rest of them (`attack`/`damage`/`slots`/
`magazine`/`rof_override`/`secondary`/`split`) is automation data with no equivalent in Corgo's prose, and
is needed either way. `npm run build:original` now only means "use an export somewhere other than the
default path". `npm test` exercises the same code path with placeholder text in `tests/fixtures/`.

**What his permission does not cover:** R. Talsorian's material (this module ships under RTG's Homebrew
Content Policy regardless) and Schism989's module, whose repo has no license file, so `reference/` stays
git-ignored.

Layout:

- `data/corgo-77-v3.md` - text export of Corgo's doc (snapshot of Sept 12, 2026), tracked here with his
  permission and read by the parsers and by `original_text.py`. Not copied into `dist/`.
- `tools/parse_weapons.py` - reads the weapon catalog stat blocks into `data/weapons.parsed.json`.
- `text/weapons_rules.json`, `text/weapon_variants.json` - rules text rewritten for the item descriptions.
- `tools/build_weapons.py` - maps Corgo's stats onto the CPR 0.92.4 weapon schema. The
  class, range-table, and skill mapping tables are at the top of this file.
- `tools/common.py` - stable IDs (same item always gets the same ID), naming, description template.
- `tools/compile.mjs` - compiles `src/packs/*` into LevelDB with @foundryvtt/foundryvtt-cli 1.1.0.
- `module/` - module.json and the end-user README, copied into dist as-is.
- `text/dv_tables_sof45.json` - Solo of Fortune 2045 DV tables, transcribed from Interface RED Vol. 5.
- `tools/dvtables.py` - builds the DV Tables pack and decides each weapon's DV table (see its docstring
  for how 0.92.4 matches Autofire tables by name).
- `tools/parse_upgrades.py` - reads the Attachment Catalog, Mod Catalog, and Ammunition into `data/upgrades.parsed.json`.
- `text/attachments.json`, `text/mods.json`, `text/ammo.json` - rules text plus what each item automates
  (`attack`/`damage` as [value, situational], `slots`, `magazine`, `rof_override`, `secondary`, `split`).
- `tools/build_upgrades.py` - builds attachments (incl. the Capacity Chart magazines), mods, and ammo.
- `text/dv_tables_core.json`, `tools/cpr-0.92.4-reference.json` - the two copied core DV tables and a
  snapshot of CPR 0.92.4's allowed values and field sets, so building and validating need no CPR checkout.
  The cyberware field set (`cyberwareKeys`, `cyberdeckKeys`) and the `cyberwareTypes` /
  `cyberwareInstallList` enums were taken from the 0.92.4 `CyberwareDataModel` and its mixins, checked
  against the union of the fields on all 186 cyberware items the system ships.
- `text/armor.json`, `tools/build_armor.py` - armor, iconic armor, Gun Shields, and armor/shield upgrades
  (penalty given per stat as [REF, DEX, MOVE]; the item uses the worst, see the builder's docstring for why).
- `text/gear.json`, `tools/build_gear.py` - general gear, External Linear Frames (plus the SPECTER's weapons,
  built with the weapon builder), poisons, pharmaceuticals, and street drugs. Drug effects follow the core's
  Primary / Addiction pattern, plus "Addicted Primary" where Corgo suspends the addiction penalty while dosed.
- `tools/build.py` - runs every pack builder (weapons, DV tables, macros). The validator replays the
  system's Autofire table lookup for every weapon.
- `tools/compat/schism-dv-recommendations.json` - generated by the build: the DV table each of Schism's weapons should use.
- `tools/compat/schism-sof45.json` - table names, weapon DV tables, and item names from Schism989's Solo of
  Fortune 2045 module (v1.1.0). The validator fails if our DV compendium stops covering them or an item name
  collides. Refresh it if that module updates.
- `reference/schism-sof45/` - pinned copy (commit bceb8fa) of Schism989's module, used only to produce
  `tools/compat/schism-sof45.json`. Not shipped. His repo has no license file, so don't copy its items into
  this module; have users install his module alongside instead.
- `tools/original_text.py` - finds each item's entry in the export by heading (within the right section) and
  converts it to HTML for the opt-in `build:original`. Pass `intro_only=True` for an entry that has nested
  `####` sub-entries (Gorilla Arm, Mantis Blade, the Popup leg weapon, Exoglove), or the parent's text runs
  on into its children's.
- `tools/parse_cyberware.py` - reads the Cyberware, Operating Systems and Cyberware Alternatives chapters
  into `data/cyberware.parsed.json` (stat lines and the `##` subsection only; it also records which entry a
  nested `####` entry hangs off). Skips the Corpochrome variants, the Militech Centaur Exo, and the 2070s
  Full Body Conversions.
- `tools/parse_iconics.py`, `text/iconics.json`, `tools/build_iconics.py` - the Iconic Cyberware and
  Iconic Gear chapters, plus the shared Iconic rules from Becoming Iconic. Iconics carry `Category` and
  `Fabrication` instead of a Cost, so the builder maps the category to that tier's eurodollar benchmark
  (`CATEGORY_PRICE`) for repair and Tech Upgrade maths and says so on every item. Document types and all
  other conventions come from build_cyberware and build_gear, which this reuses rather than repeats.
  Iconic Armor is one item and already in `text/armor.json`'s "iconic" list. Iconic Weapons (2,245 lines,
  4 mods + 89 weapons + 25 nested variants) is its own pass. Iconic Vehicles waits for the VEHICLES and
  VEHICLE CATALOG chapters, so the `vehicle` field set gets settled once rather than twice.
- `text/cyberware.json`, `tools/build_cyberware.py` - the cyberware chapter, in three document types, the
  way the core system models the same things: `cyberware` items for anything installed in or worn on the
  body, `itemUpgrade` items of type `cyberware` for Corgo's "X Cyberware Enhancement" entries and the
  Operating Systems (which he says work identically), and `cyberdeck` items for the five decks the
  Cyberdeck Port OSes come with. See the builder's docstring for the schema conventions, why enhancements
  carry no Active Effects, and why a piece whose slot costs cross categories is typed where its slots are
  usable (Advanced Neural Link, Integrated Netstation).

Not built from the Cyberware chapter, at Kane's direction: the **2070s Full Body Conversions**, the
**Militech Centaur Exo** cyberchair, and the **Corpochrome** variants. Corpochrome is written up as a rule in
`module/README.md` instead; note that its subsection also lists 14 named branded options (Arasaka Kohama MZ,
Jinguji Superarm, Moore Tech Liskamm-C and so on) with their own costs, Humanity Loss, and slot counts, which
are not built either.

Two things the 0.92.4 source settled, worth not re-deriving:

- `size` is only compared against free slots when an item is installed into another **Item**, never when a
  foundational piece goes onto an actor (see the comment in `cpr-container.js installItems`), so `size` on a
  foundational piece does nothing. Core itself ships foundational cyberware at both size 0 (Cyberarm, Neural
  Link) and size 1 (Smart Glasses, Battleglove, Romanova Cyberlegs), and ten non-foundational items at size 0
  (the Coverings, Standard Hand). The validator therefore checks neither.
- Non-foundational cyberware can only be installed when a foundational piece of the **same** `type` is
  already installed (`cpr-actor.js installCyberware`), and the nested-container search it does is what makes
  a Chipware Socket or an Advanced Neural Link a usable install target.

`npm run check:original` builds with Corgo's wording and then verifies, per item, that the text it carried
is its *own* entry's text and no one else's (`tools/check_original.py`). It fingerprints each entry with its
longest unique line taken from the parsers' records, not from `original_text.py`, so a heading-matching bug
in the lookup can't hide itself. The contamination half of that check is what catches a parent entry running
on into its nested `####` sub-entries; it found Long Scope carrying the Jue and Saika rules, Short Scope
carrying Kanetsugu's, and Laser Sight carrying IR/UV's, all of which had been shipping since the attachments
chapter. `build_upgrades.nested_parents()` now supplies `intro_only` for those, the way `build_cyberware`
does. It needs `data/`, so it only runs where the document is present.

Markdown quirks in the export that `original_text.py` now handles, each found by running the check above
over all 521 items and then scanning the HTML for leftovers:

- a link broken across two lines ("[text" on one, "](url)" on the next), which left both the link text and
  the raw URL visible (XtremSight, Superjet). The emphasis markers either side of the break are stranded by
  the join, so they are dropped at the seam.
- a URL containing escaped parentheses, which the old link regex stopped short of at the first ")".
- an escaped marker *pair* (`\*\*text\*\*`), which the export produces wherever Corgo nests bold inside
  bold or puts any formatting in a table. Those are formatting, not literal asterisks, and used to show as
  raw `**` in 10 mod and attachment tables and bullets. A lone `\*` is still a literal asterisk.
- a heading's `#` markers inside a table cell, and lines of nothing but emphasis markers, which produced
  an empty `<p>`.

The tools print item names, and some of those carry characters a legacy Windows console can't encode ("Ć",
curly quotes, "♦"). Python raises `UnicodeEncodeError` rather than mangling them, which killed
`npm run build` and `npm test` mid-print on a cp437/cp1252 console. `tools/common.py` and the three parsers
now ask for UTF-8 output and fall back to replacing what the console can't show. To check a change against
that, run with `PYTHONIOENCODING=cp437` (or `$env:PYTHONIOENCODING="cp437"` in PowerShell).

Two things found by playing v0.6.0 in Foundry, both now enforced by the validator:

- `humanityLoss.roll` has to be a plain dice formula or a number. CPR draws its humanity-loss roll card
  from `roll.terms[0].results`, which only a DiceTerm has, so `ceil(4d6/2)` throws and shows nothing; core
  only ever uses 0, 1d3, 1d6, 2d6 and 4d6. `parse_hl` turns "Nd6/2 [Round Up]" into the halved dice
  (4d6 -> 2d6: same range and mean, flatter spread) and the item says so.
- Armor covering body and head stays a single item (the diving suit, Nano-Plating's armor half), matching
  core's Subdermal Armor. Worth knowing when reading that code: CPR's equip handler tests
  `isHeadLocation` before `isBodyLocation` and tracks only the first match, so such an item registers in
  the head SP slot. Whether body SP still comes out right has not been checked in play; a reported problem
  here turned out to be something else, so this was left alone rather than split on a theory.
- An enhancement's `enhances` target has to be a real item. Corgo's Projectile Launch System doesn't
  exist in 0.92.4 under that name (its Popup Grenade Launcher is the same thing), which left Launch
  Capacity Override pointing at nothing findable. The `enhances` strings are still free text; resolving
  them against the reference and our own packs is the check worth adding next.

Foundry strips tags to build item-list summaries, tooltips and chat previews, so every block-level tag in
a description needs whitespace on one side of it: without it the words either side weld together
("Cost: 2,000eb (Very Expensive)Type: Neuralware"). That affected 2,071 boundaries across every pack -
the `<br>` between facts, the `</p><ul><li>` before the Foundry notes, each `</li><li>` between them, and
every table cell in the original-text build. `description_html` and `original_text._to_html` now put a
newline after each boundary tag, and the validator checks it. Inline tags (strong, em, a) are exempt: the
export splits words across bold runs ("**I****nstall:**"), where dropping the tag with no space is the
correct reading.

`validate.mjs` resolves every enhancement's "Enhances" fact against `REF.itemNames` (a snapshot of all 1,100
item names 0.92.4 ships), our own built item names, and `text/enhance_targets.json`, which lists the parents
the system has no item for at all, each with the reason. That last file keeps the check green and
self-documenting instead of switched off, and those items' own notes tell the GM the parent has to be made
by hand. Anything else has to match a real name, so a typo or a rename fails the build.

It found six unresolved targets when first run. Three were names: Corgo's Neuroport is the core system's
Neural Link, his Personal Link is Interface Plugs, and "Implanted Linear Frame (any)" needed the real
"Implanted Linear Frame β (Beta)". Three are genuinely absent from 0.92.4 - Monowire, Self-ICE, and the
Neuroport Cyberdeck Port, all from Corgo's required content (the Edgerunners Mission Kit and Interface RED)
rather than from the free system - and are in the allowlist.

Matching is deliberately exact per "or"-separated part, after stripping a parenthetical gloss. An earlier
prefix rule made the check useless: "Reflex Tuner" resolved happily against a renamed "Reflex Tuner Mk.II",
which is the exact silent breakage the check exists to catch. Both failure modes have negative tests worth
repeating after any change here: a typo in a target, and a dropped allowlist entry.

Not covered: the dependencies stated in prose rather than in `enhances`. Most Iconic Cyberware is a
cyberware item that "Requires Reflex Tuner" or similar in its rules text, and nothing checks those names.
A structured `requires` field on those specs, shown as a fact and resolved the same way, would close it.
