# Corgo's 77 Collection for Cyberpunk RED - Core (Foundry VTT)

An unofficial Foundry VTT module that brings **Corgo's 77 Collection V3** by Corgopolis, a 2070s-era
homebrew supplement for Cyberpunk RED, into the Cyberpunk RED - Core system as compendiums. It adds
754 items across 15 packs and changes nothing in the system itself. Corgo's NPC stat blocks ship as a
separate module, **Corgo's 77 Collection: NPCs** (128 mook actors), built from the same repository.

- Corgo's document: <https://docs.google.com/document/d/13EnSAoiLDsC7zmL-Jr1RqIh_EnuVuFnExqiipDVquMk/edit>
- Corgo's NPC stat blocks: <https://docs.google.com/document/d/1gdiAH9cuuy43O5IN2V4BdV45gm-j0GAO_TrBtNm6T-o/edit>
- Support Corgopolis: <https://patreon.com/Corgopolis>
- Requires Foundry VTT v12 and Cyberpunk RED - Core v0.92.4

## Installing

In Foundry's Setup screen, open **Add-on Modules**, click **Install Module**, and paste this manifest URL:

    https://github.com/aky9/corgo-77-module/releases/latest/download/module.json

Foundry offers updates from the same URL. Once the module is enabled, run the **Use Corgo's 77 DV Tables**
macro once per world. [`module/README.md`](module/README.md) is the full user guide: what each pack
automates, what is left to apply by hand, and how to run it alongside Schism989's Solo of Fortune 2045
module.

## What's in it

Every item carries its entry from Corgo's document, plus notes on what the character sheet automates
for it and a link back to the document.

| Pack | Items | What it holds |
| --- | ---: | --- |
| Weapons | 151 | The Weapon Catalog and the Ironfake and Darkhound variants, in folders by weapon type |
| Iconic Weapons | 115 | The Iconic Weapons chapter, including its nested variants and the four Iconic mods |
| Weapon Attachments | 109 | The Attachment Catalog, plus Extended, Drum, Belt Box, and Backpack magazines for every row of the Capacity Chart |
| Weapon Mods | 66 | Attachment Mods, Weapon Mods, and Invented Weapon Upgrades, with multi-version items split one per version |
| Cyberware | 85 | Fashionware, Neuralware, Cyberoptics, Internal and External Body, Cyberarms, Cyberlegs, Borgware, and the Cyberware Alternatives |
| Cyberware Enhancements | 39 | Corgo's "X Cyberware Enhancement" entries, as upgrades installed into the piece they enhance |
| Ammunition | 27 | One item per caliber each ammo comes in, the Combo Casings, and the Homing and Sticky adapter kits |
| Armor & Shield Upgrades | 23 | Armor Enhancements and Kits, Shield Attachments and Enhancements |
| Gear, Frames & Drugs | 23 | General Gear, the Wolfpack and SPECTER External Linear Frames, Neurotoxin, the Pharmaceuticals, and 13 Street Drugs |
| Armor & Shields | 20 | The Armor Catalog as Body and Head pieces, the Iconic "Kagami" Neo-Kabuto, and the three Gun Shields |
| Iconic Cyberware | 20 | Iconic Neuralware, Cyberoptics, Body Cyberware, Cyberlimbs, and both Relic Biochips |
| Operating Systems | 18 | The Berserk, Cyberdeck Port, and Sandevistan Operating Systems and the five Cyberdecks they come with |
| Iconic Gear | 5 | The two Iconic Cyberdecks and three Iconic Drugs |
| DV Tables | 51 | The Solo of Fortune 2045 single-shot and Autofire range tables, covering every table name the core system uses |
| Setup Macros | 2 | Switch the DV ruler to these tables, and back |

**How the items behave.** Stats are Corgo's finished stat lines. What the system can automate is
automated: flat attack and damage bonuses, attachment slots, magazine sizes, armor SP and penalties,
cyberware stat and skill effects, Humanity Loss, and drug effects as toggles. What it cannot, such as
conditional bonuses, drop-lowest damage, or effects that land on other people's rolls, is called out in
the item's description so nothing has to be looked up mid-session. Weapons use the Solo of Fortune 2045
range tables, and the DV compendium also carries every core table name so the core weapons keep working
after the switch.

**Iconics** are Corgo's optional item class, found rather than bought. They live in their own packs, carry
the shared Iconic rules in their notes, and are priced at their Category's benchmark so repair and Tech
Upgrade maths work.

**The NPC module** holds Corgo's NPC stat blocks, included with his permission, as 128 mook actors that
carry real copies of their gear and cyberware, so it works without the items module. Most use his quick
format (COM#, INIT, COOL, MOVE, and skill bases), built so every listed skill rolls exactly the printed
number; [`npcs-module/README.md`](npcs-module/README.md) explains how. Install it from
`https://github.com/aky9/corgo-77-module/releases/download/npcs-latest/module.json`.

## Not converted

- **Vehicles**, the **Vehicle Catalog**, and **Iconic Vehicles**.
- **Drones** and the **Drone Catalog**.
- The **2070s Full Body Conversions**, the **Militech Centaur Exo**, and the 14 named **Corpochrome**
  options. Corpochrome itself is written up as a rule in the user guide.
- **Role Tweaks**, **Netrunning**, and **Deep Diving 101**, which are rules rather than items.

## Building from source

Corgo's document, exported to `data/corgo-77-v3.md`, is the source. The parsers read the stat blocks from
it, the builders join them with the automation data in `text/` and each item's entry, and the compiler
turns the result into the LevelDB packs Foundry reads. `src/packs/` holds every built item as JSON and is
what ships. On a fresh clone, `./setup.sh` installs the toolchain, parses, builds, validates, and runs the
tests, and the CI workflow runs the same on every push. [`CLAUDE.md`](CLAUDE.md) covers the commands, the
layout, and the conventions settled against the 0.92.4 source.

## Releasing

A release is a git tag. Bump `"version"` in `module/module.json`, commit, tag the commit `vX.Y.Z`, and
push the tag; [`.github/workflows/release.yml`](.github/workflows/release.yml) builds the module and
attaches `module.zip` and `module.json` to a GitHub Release, which is where the manifest URL above
points. The workflow refuses a tag that does not match the manifest's version.

## Credits

Corgo's 77 Collection V3 is by Corgopolis (<https://patreon.com/Corgopolis>); every item is his text and
his stats. The DV tables are transcribed from Interface RED Vol. 5 (Solo of Fortune 2045). This module is
built to run alongside Schism989's [Cyberpunk RED - Solo of Fortune 2045](https://github.com/Schism989/cpred-solo-of-fortune-2045)
module, which supplies the Solo of Fortune attachments and ammo Corgo's items refer to. To make the two
fit together, `tools/compat/` records the names of his DV tables and items (nothing else from his module):
this module's DV compendium uses the same table names so his weapons keep working after the DV ruler is
switched to it, and the build refuses any item name that would collide with one of his. None of his
content is copied into this module.

## Legal

Corgo's 77 Collection V3 is unofficial content provided under the Homebrew Content Policy of R. Talsorian
Games and is not approved or endorsed by RTG. This content references materials that are the property of
R. Talsorian Games and its licensees.
