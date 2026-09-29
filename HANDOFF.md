# Handoff — where this project stands

Written at **v0.8.0**. Read `DEVELOPING.md` next: it holds the per-tool detail, the CPR 0.92.4 facts that
were expensive to work out, and the reasoning behind every convention below. This file is the map.

## What the module is

A Foundry VTT module, `corgo-77-collection`, converting **Corgo's 77 Collection V3** (Cyberpunk RED
homebrew) for **Cyberpunk RED - Core v0.92.4** on Foundry 12, without modifying the core system.

Fixed constraints, unchanged since the start:

- The 0.92.4 source comes from the GitHub mirror `davidkan1996/fvtt-cyberpunk-red-core`, tag `v0.92.4`
  (GitLab is blocked in the sandbox). `tools/cpr-0.92.4-reference.json` is a snapshot of its facts so the
  build and validator need no checkout.
- The build uses **Corgo's own wording**. He gave permission for this conversion and for his text to ship,
  so `data/corgo-77-v3.md` is tracked and `npm run build` reads it. Every builder passes the item heading to
  `original_text.lookup`. The rewritten text in `text/*.json` is now only the fallback for a build with no
  document, and for the handful of items his doc has no single entry for.
- Keep compatibility with Schism989's Solo of Fortune module (`tools/compat/`).
- Built on Windows: all file I/O is explicit UTF-8, and stdout too (see the encoding note in
  `DEVELOPING.md`).
- Delivery is a GitHub Release: push a `v*` tag matching `module/module.json`'s version and
  `.github/workflows/release.yml` builds and attaches `module.zip` and `module.json`. Users install from the
  manifest URL in `README.md`. The repo carries the document, so it is the build project; only `reference/`
  (Schism989's module, which has no license file) stays outside it.

## Current state: 754 items across 15 packs

| Pack | Items | Status |
| --- | --- | --- |
| weapons | 151 | done |
| weapon-attachments | 109 | done |
| weapon-mods | 66 | done |
| ammo | 27 | done |
| armor | 20 | done |
| armor-upgrades | 23 | done |
| gear | 23 | done (gear, frames, poisons, pharmaceuticals, street drugs) |
| cyberware | 85 | done |
| cyberware-upgrades | 39 | done (Cyberware Enhancements) |
| operating-systems | 18 | done (13 OSes + the 5 cyberdecks they come with) |
| iconic-cyberware | 20 | done |
| iconic-gear | 5 | done (2 cyberdecks, 3 drugs) |
| iconic-weapons | 115 | done (2 items carry guessed stats, see below) |
| dv-tables | 51 | done |
| macros | 2 | done |

## Next task: confirm the guessed stats in Foundry

The Iconic Weapons chapter is complete (115 items). Two of them carry stats that are not Corgo's own
numbers and want checking in play:

- **Chaos (Royce's Pistol)** ships at 3d6 / 20 rounds / 1 SP Ablation, which is the default Corgo states
  himself. It re-rolls all three on every Reload (1d20, 1d8, 1d4), which the sheet cannot do, so those are
  edited by hand. Its Single Shot also expends 2 rounds and its Critical Injury roll is 1d12, neither
  automated.
- **Baseball Bat X-MOD2** uses CPR 0.92.4's generic Two-Handed Very Heavy Melee Weapon line (4d6, ROF 2,
  two-handed), because Corgo names the category but gives no stats.

Dezerter, Guts and Wild Dog needed nothing: `build_weapons` already turns a Machine Gun's "N/A" damage
into the standard 2d6 Autofire and a Shotgun's into 3d6 shells, the way the eight N/A weapons in the main
catalog are built.

## After that

- **2070s Full Body Conversions** (185 lines, 7 chassis builds) — deliberately skipped earlier; Kane's call.
- **Militech Centaur Exo** cyberchair, and the **14 named Corpochrome options** — also skipped; Corpochrome
  itself is documented as a rule in `module/README.md`.
- **Vehicles** — VEHICLES (492 lines) plus VEHICLE CATALOG (2,608). The `vehicle` field set is untouched.
  **Iconic Vehicles** (36 entries, 1,219 lines) is blocked on this deliberately, so the conventions get
  settled once. It is the only Iconic chapter with nothing built.
- **Drones** — DRONES, DRONE-RELATED GEAR, DRONE CATALOG (981 lines together).
- **Role Tweaks** (85 lines), **Netrunning** and **Deep Diving 101** (92 lines) — rules rather than items;
  may belong in journal entries rather than compendium items, which is an open question.

## Commands

Run everything from the `c77` directory (the one with `package.json`). Paths resolve relative to it.

```
npm install              # once per checkout; the zips ship no node_modules
npm run parse            # re-read the document into data/*.parsed.json (only if the doc changed)
npm run build            # default build -> src/packs, then dist/corgo-77-collection
npm run validate         # schema and rules checks against 0.92.4
npm test                 # 24 original-text regression checks (uses a placeholder fixture)
npm run check:original   # builds with Corgo's wording, checks each item carries its own entry's text
npm run build:original   # explicit path to an export somewhere other than data/corgo-77-v3.md
```

`npm run build` already uses Corgo's wording, so `build:original` is only for pointing at a different
export. It and `check:original` write to `build/packs`, so **re-run `npm run build` before packaging** to
put `dist/` back.

## Conventions settled so far

Do not re-derive these; `DEVELOPING.md` cites the 0.92.4 source for each.

- **Cyberware**: options are `cyberware` with `isFoundational: false` and `size` = slots consumed;
  foundational pieces provide `installedItems.slots`. Non-foundational cyberware only installs when a
  foundational piece of the **same** `type` is present, which is why Advanced Neural Link and Integrated
  Netstation are typed where their slots are reachable rather than by Corgo's category.
- **Enhancements and Operating Systems** are `itemUpgrade` of type `cyberware`, `size` 0, and carry **no
  Active Effects** (an itemUpgrade has no "installed" usage, so effects would apply from inventory). They
  use `modifiers` only; other bonuses are described with a note naming the parent item to edit.
- **Passive vs activated cyberware**: passive is `usage: "installed"` with a plain effect; activated is
  `usage: "toggled"` with the change flagged situational, so it appears as a roll-dialog toggle.
- **Iconics** carry `Category` and `Fabrication` instead of a Cost. `price.market` is the category's
  eurodollar benchmark (`build_iconics.CATEGORY_PRICE`) for repair and Tech Upgrade maths, and every item
  says it can't be bought. Iconic Cyberware Options are `size` 0 unless an entry says otherwise.
- **Iconic weapons follow the Exotic rules** (Corgo's own chapter rule), so `split_class` treats the Iconic
  prefix as Exotic: no Non-Basic Ammunition, no attachment slots unless stated.
- **Humanity Loss rolls must be a plain dice formula**; CPR builds its roll card from `terms[0].results`, so
  `ceil(4d6/2)` throws. "4d6/2 round up" becomes `2d6` (same range and mean) with the item saying so.
- **Descriptions need whitespace around block-level tags** — Foundry strips tags for list summaries, and a
  bare `<br>` welds words together. Enforced by the validator.

## Things known to be unfinished or unverified

- **Nothing has been tested in Foundry beyond what Kane reported.** Still unverified: the stat caps
  (Mechatronic Core at TECH 7 should give 8, not 9), the three enhancement slot modifiers, and whether
  Advanced Neural Link's 4 Neuralware slots are reachable — that last one is the typing decision most
  likely to be wrong. Confirmed working by Kane: most things, plus the Gorilla Arm HL fix and the
  Projectile Launch System naming.
- **Prose dependencies are unchecked.** `validate.mjs` resolves every enhancement's `enhances` target, but
  most Iconic Cyberware is a `cyberware` item whose requirement sits in rules prose ("Requires Reflex
  Tuner"). A structured `requires` field on roughly 20 specs, shown as a fact and resolved the same way,
  would close it.
- **Three enhancement parents don't exist in 0.92.4** — Monowire, Self-ICE, the Neuroport Cyberdeck Port —
  because they come from Corgo's required content (Edgerunners Mission Kit, Interface RED) rather than the
  free system. Listed with reasons in `text/enhance_targets.json`; the affected items tell the GM to build
  the parent by hand.
- **Armor covering body and head is one item** (the diving suit, Nano-Plating's armor half), matching core's
  Subdermal Armor. CPR's equip handler checks `isHeadLocation` first and tracks only the first match, so
  such an item registers in the head SP slot; whether body SP still comes out right is **unverified**. A
  reported problem here turned out to be something else, so it was left alone rather than split on a theory.
