# Corgo's 77 Collection V3 for Cyberpunk RED - Core (Unofficial)

An unofficial Foundry VTT conversion of **Corgo's 77 Collection V3** by
**Corgopolis**, a 2070s-era homebrew supplement for Cyberpunk RED. This module
only adds compendiums. It does not modify the Cyberpunk RED - Core system.

- Original document:
  <https://docs.google.com/document/d/13EnSAoiLDsC7zmL-Jr1RqIh_EnuVuFnExqiipDVquMk/edit>
- Support Corgopolis: <https://patreon.com/Corgopolis>

## Requirements

- Foundry VTT v12
- Cyberpunk RED - Core system v0.92.4

## Installing

1. In Foundry's Setup screen open **Add-on Modules**, click **Install Module**,
   paste this into **Manifest URL**, and click **Install**:

       https://github.com/aky9/corgo-77-module/releases/latest/download/module.json

   Foundry will offer updates from the same place. If you were handed a
   `module.zip` instead, unzip it so the folder `corgo-77-collection` sits
   inside your Foundry `Data/modules/` folder (it should contain `module.json`).
2. Launch your world and enable **Corgo's 77 Collection V3** under
   **Manage Modules**.
3. The compendiums appear in the Compendium tab, in the
   **Corgo's 77 Collection** folder.
4. **One-time setup per world (GM):** open **Corgo's 77: Setup Macros** and
   run **Use Corgo's 77 DV Tables**. This points the system's DV ruler at the
   module's range tables. **Restore Core DV Tables** switches it back. Neither
   macro changes the system itself; they only change which compendium the
   system's DV table setting uses.

## What's included

- **Weapons** (151): the full Weapon Catalog plus the Ironfake and Darkhound
  variants, sorted into folders by weapon type.
- **Weapon Attachments** (109): Corgo's Attachment Catalog, plus Extended,
  Drum, Belt Box, and Backpack magazines for each row of Corgo's Capacity
  Chart (36 items).
- **Weapon Mods** (66): Attachment Mods, Weapon Mods (Bladesmith and the
  Conversion Kits split into one item per version), and Invented Weapon
  Upgrades.
- **Armor & Shields** (20): Corgo's Armor Catalog (generic armor comes as
  separate Body and Head pieces, like the core's), the Iconic "Kagami"
  Neo-Kabuto, and the Light, Medium, and Heavy Gun Shields for the Gun
  Shield Mount attachment.
- **Armor & Shield Upgrades** (23): Armor Enhancements and Kits (Nanoweave
  Rebuild split into its three versions) and Shield Attachments and
  Enhancements.
- **Gear, Frames & Drugs** (23): General Gear, the Wolfpack and SPECTER
  External Linear Frames (with the SPECTER's IronWind and EarthBreaker
  weapons), the Neurotoxin poison, two Pharmaceuticals, and 13 Street Drugs.
- **Cyberware** (85): the Cyberware chapter's Fashionware, Neuralware,
  Cyberoptics, Internal and External Body Cyberware, Cyberarms, Cyberlegs,
  and Borgware, sorted into folders, plus the Battle/Smart Gloves and Smart
  Optics from Cyberware Alternatives. Includes the armor item for
  Nano-Plating's SP 12.
- **Cyberware Enhancements** (39): Corgo's "X Cyberware Enhancement"
  entries, as upgrades you install into the cyberware they enhance.
- **Operating Systems** (18): the Berserk, Cyberdeck Port, and Sandevistan
  Operating Systems, plus the five Cyberdecks the Cyberdeck Port ones come
  with.
- **Iconic Cyberware** (20): the Iconic Neuralware, Cyberoptics, Internal and
  External Body Cyberware, Cyberlimbs, and both Relic Biochips.
- **Iconic Gear** (5): the two Iconic Cyberdecks and three Iconic Drugs.
- **Iconic Weapons** (115): the Iconic Weapons chapter, including its nested
  variants and the four Iconic weapon mods.
- **Ammunition** (27): Corgo's ammo, one item per caliber it comes in, plus
  the Combo Casings and the Homing and Sticky adapter kits.
- **DV Tables** (51): the *Solo of Fortune 2045* single-shot and Autofire
  range tables, plus every table name the core system uses, so core weapons
  keep working after the switch.
- **Setup Macros** (2): switch the DV ruler to these tables and back.

## How the items work

- Stats are Corgo's finished stat lines. Pre-installed attachments are
  listed in each description and their effects are already in the stats.
  Corgo's rule: pre-installed attachments can only be swapped for an
  equivalent one, and pre-installed mods can't be removed.
- Rules the system can't automate are summarized in each item's description.
  Each description links to Corgo's document for the exact wording.
- **Range tables:** weapons use the *Solo of Fortune 2045* range tables
  (Interface RED Vol. 5). In this system, DV tables drive the DV ruler, not
  hit rolls. After running the setup macro, the core table names also use the
  *Solo of Fortune 2045* numbers. Two differ from the core system: Pistol at
  101-200 m/yds (35) and Long-Barrel Pistol.
- **Autofire tables:** the system picks a weapon's Autofire table by name, so
  weapons that share a range table but use a different Autofire type point at
  a tagged copy, such as `DV Carbine [SMG]`. The distances are identical.
- **Drop-lowest damage:** CPR 0.92.4 can't drop dice automatically. Those
  weapons say so in their description; drop the die by hand.

## Attachments and mods

- Install them like any upgrade. An attachment uses its Attachment Slots, and
  Weapon Mods and Invented Tech Upgrades use none. A mod for an attachment,
  such as Critochet for a Power Rebuild, goes on the same weapon.
- **Automated:** flat attack bonuses, extra Attachment Slots (Magrail Kit,
  Variable Scope Mount, Flared Magwell, Modular Rails), magazine size, Rapid
  Fire's ROF and penalty, and the underbarrel weapons, which appear as
  secondary weapons. Conditional bonuses, like a scope's range band or a
  Foregrip's two-handed grip, are **situational**: tick them in the roll
  dialog when they apply.
- **Not enforced by the sheet:** what an attachment fits, incompatibilities,
  one Weapon Mod per weapon, and restrictions on bonus slots (Magrail Kit
  slots only take small attachments, for example). Extra damage dice are also
  not automated, because the system only adds flat damage from upgrades.
- **Magazines:** Corgo's magazines add to the weapon's base capacity. The
  core system's Extended and Drum Magazines replace capacity instead, so
  don't install both kinds on one weapon.

## Armor notes

- **Armor Penalty:** the system applies one penalty to REF, DEX, and MOVE,
  and only the worst penalty among your worn armor counts. Where Corgo gives
  different penalties per stat (the Max-Helm is -1 REF, -2 DEX/MOVE), the item
  uses the worst one and its description gives the exact split.
- **Automated:** SP, penalties, shield HP, SP and shield-HP upgrades (Carbon
  Plated, Reactive Armor Panels, Superheavy Plates, Superdense Layer, Better
  Coverage, Brawler Style), and the skill bonuses on the Neo-Kabuto,
  "Kagami", and Aviation T.O.P., which apply while the helmet is equipped.
  Disable a helmet's effect if the wearer doesn't meet its skill requirement.
- **Not automated:** reduced ablation, self-repair, built-in gear (Smart
  Glasses and their options, Smart Ears, and so on), and penalty changes from
  enhancements (Combat Weave, Ultralight Rebuild, Superheavy Plates' penalty,
  Tower Style). These are in the descriptions.

## Gear and drug notes

- **Drugs** work like the core system's (e.g. Synthcoke). Using a drug turns
  on its "Primary" effect. While a character is addicted, switch on its
  "Addiction" effect. Many of Corgo's drugs suspend the addiction penalty
  while the drug is active; for those, an addicted character uses the
  "Addicted Primary" effect instead, which cancels that penalty for the
  duration. Only stat and skill changes are automated; caps (like
  Jellytricity's DEX 8), durations, and Humanity Loss are applied by hand.
- **Militech SPECTER:** while equipped, BODY becomes at least 14 and MOVE at
  least 6. Corgo says the BODY boost doesn't change HP or Death Save; if the
  sheet recalculates them, correct them by hand. Its weapons only work
  mounted in the frame.
- **Crime Scene Hologram Projector:** toggle it on, then tick its +2 in the
  Deduction or Criminology roll dialog when studying a crime scene.

## Cyberware notes

- **Foundational pieces first.** Cyberpunk RED - Core only lets you install
  an option when a foundational piece of the *same* kind is already in: a
  Neuralware option needs a Neural Link, a Cyberarm option needs a Cyberarm,
  and so on. Chipware (Combat Software, Kairos 6-M) goes into a Chipware
  Socket, so install the socket first and then install the chip into it.
- **Two items share a name with the core system's:** Corgo's **Kerenzikov**
  and **Sandevistan**. His versions are meant to replace other sources', so
  use these and leave the core ones alone.
- **Enhancements** are upgrades: drag one onto the cyberware it enhances.
  They use no Option Slots. Extra Option Slots (Kiroshi Premier Cybereye,
  ICE-Silo) and extra capacity (Launch Capacity Override) are applied
  automatically. Skill and stat bonuses from an enhancement are **not**: an
  upgrade's effects would apply from your inventory whether or not it was
  installed, so those bonuses are described in the item instead, usually with
  a note saying which parent item to put an effect on.
- **Automated on cyberware:** stat changes and their caps (Mechatronic Core's
  TECH, Leeroy Ligament System's and Adrenaline Convertor's MOVE), skill
  bonuses (Syn-Lungs, Infovisor, Lynx Paws, Shock Absorber, and others),
  Option Slots provided and consumed, Humanity Loss, and the weapon stats of
  cyberweapons (Gorilla Arm, Mantis Blade, Medtool Cyberfinger, Porcupine
  Hands, the Popup leg weapons).
- **Passive vs activated.** Passive cyberware is set to "installed", so its
  effect applies exactly while it is installed. Activated cyberware
  (Sandevistan, Berserk, Adrenaline Convertor, Optical Camo, and so on) is
  "toggled", and its bonus shows as a tickbox in the roll dialog, matching how
  the core system's own Sandevistan works. Durations and cooldowns are tracked
  by hand.
- **Not automated:** Maximum Humanity Loss for anything that "counts as
  Borgware", conditional bonuses with a skill or BODY requirement (Stabber,
  Remote Sync, Needle Leg's MOVE penalty, Dense Marrow's penalty), penalties
  that land on *other* people's checks (Cyber-Mask, KERS, Masking Ink), and
  armor SP changes from enhancements (Neofiber, Para Bellum). Each item says
  so in its own description.
- **Nano-Plating** comes as two items, the cyberware piece and an armor piece
  ("Nano-Plating (Armor)") for its SP 12, because cyberware items carry no SP.
  This is how the core system splits Subdermal Armor. Equip both.
- **Launch Capacity Override** enhances what Corgo calls a Projectile Launch
  System. Cyberpunk RED - Core 0.92.4 ships no item by that name; its **Popup
  Grenade Launcher** is the same thing, so install the enhancement into that.
- **Gorilla Arm**'s Humanity Loss is 4d6 halved rounding up, which the sheet
  can't roll, so the rolled option is 2d6 - same range, same average. The
  static 7 is there if you'd rather not roll.
- **Paired items** (Oracle Cybereyes, Hausstock-W Arms, Blazing Fury
  Cyberhands, Porcupine Hands) are one item for the pair, as Corgo prices and
  installs them that way. Their slot count is the count for one limb or eye.
- **Corpochrome** is a rule rather than an item, so there is nothing to
  install: a Corpochrome variant of a piece of cyberware costs double, its
  price category goes up one tier, and it gains the benefit of a single
  non-invented Tech Upgrade (CP:R, p. 148). That benefit doesn't count as a
  Tech Upgrade for the Maker Role Ability, so the piece can still be Tech
  Upgraded normally, and it can take the same benefit twice. To use it, copy
  the item in your world and edit the price and the upgraded value by hand.
  Corgo's document also lists 14 specific branded Corpochrome options; those
  aren't in this module.
- **Not included from this chapter:** the 2070s Full Body Conversions and the
  Militech Centaur Exo cyberchair.

## Iconics

Iconics are Corgo's optional item class: found through play rather than bought,
and not destroyed unless you agree to it. Nothing in Cyberpunk RED - Core marks
an item as Iconic, so they live in their own compendiums and each one carries
those rules in its notes.

- **They have no purchase price.** Corgo lists a **Category** (the price tier,
  which is what repairs and Tech Upgrades are worked out from) and a
  **Fabrication** cost in DV, materials, and time. The price on the item is
  that tier's benchmark - Very Expensive 1,000eb, Luxury 5,000eb, Super Luxury
  10,000eb - so repair and upgrade maths work. It is not a shop price.
- **Iconic Cyberware Options take no Option Slot**, per the chapter's own rule,
  except where an entry says otherwise: Quantum Tuner, Isometric Stabilizer,
  the Behavioral Imprint-Synced Faceplate, Chitin, and the Higurashi blades.
- **Several are enhancements to ordinary chrome from the Cyberware chapter.**
  Adreno-Trigger wants an Adrenaline Convertor, Revulsor a Reflex Tuner, RAM
  Reallocator a RAM Manager, Isometric Stabilizer Clutch Padding, Peripheral
  Inverse a Proxishield, Immovable Force a Shock Absorber. Where an Iconic
  raises a bonus the parent item automates, the Iconic's notes say which effect
  to edit.
- **Relic Biochip 2.0** replaces EMP with Stability (STAB) and runs a weekly
  decay with its own thirteen-step chart. Stability isn't a Cyberpunk RED stat,
  so none of it is automated - track STAB by hand. The chart itself is in the
  item text.
- **The Iconic Drugs** last a month. Their Primary and Addiction effects are
  built as toggles, like the Street Drugs; switch the addiction off while the
  Primary Effect is running, since that cancels it.

## Using this with Schism's "Solo of Fortune 2045" module

[Cyberpunk RED - Solo of Fortune 2045](https://github.com/Schism989/cpred-solo-of-fortune-2045)
(v1.1.0) works alongside this module. They complement each other: it has
Solo of Fortune attachments and ammo that Corgo's items refer to (Pistol
Autosear, SMG Cyclic Internals, High Precision ammo, and so on), and no item
names overlap between the two.

- **Use this module's DV tables.** Only one DV compendium can be active.
  This one contains every table name the other module uses (same names,
  such as `DV Short-Barrel Shotgun` and `DV Anti-materiel Rifle`), plus the
  Autofire tables both modules' weapons need. The other module's compendium
  lacks tables that 11 of Corgo's weapons use.
- A few values in the other module's DV tables differ from the Solo of
  Fortune table this module uses: Pistol at 101-200 m/yds (30 vs 35) and
  Sniper Rifle at 101-200 m/yds (15 vs 16). Its SMG and Rocket Launcher
  tables are also missing some distance bands.
- **Four of its weapons need their DV Table changed** to get the right range
  or Autofire DVs from this module's tables (checked against Interface RED
  Vol. 5, pp. 116-118). Module compendiums are locked, so change it on the
  copies in your world (in the Items sidebar or on a character):

  | Weapon | DV Table it has | Set it to | Why |
  | --- | --- | --- | --- |
  | MK.27 LMG | DV Assault Rifle | DV Assault Rifle [MG] | Machine Gun Autofire |
  | Helix (Citrus Edition) | DV Carbine | DV Carbine [MP] | Machine Pistol Autofire |
  | Mountain Goat Rifle | DV Scout Rifle | DV Battle Rifle [AR] | Battle Rifle table, Assault Rifle Autofire |
  | Chaingun "Victoria" | (none) | DV Battle Rifle | Battle Rifle table, Machine Gun Autofire |

  The tagged tables have the same distances as the untagged ones; only the
  Autofire table they lead to differs. The other six weapons on those pages
  already work as they are.
- **Similar weapon:** its *Midnight Assault HB* and Corgo's *Midnight Arms
  MA70 HB* look like the same gun in different eras. Corgo intends his
  version to replace other sources' versions, so pick one for your game.

## Legal

Corgo's rules text appears in these items with Corgopolis's permission.
Please support him at <https://patreon.com/Corgopolis>.

Corgo's 77 Collection V3 is unofficial content provided under the Homebrew
Content Policy of R. Talsorian Games and is not approved or endorsed by RTG.
This content references materials that are the property of R. Talsorian Games
and its licensees. Item icons are the Cyberpunk RED - Core system's own
icons, referenced from the installed system rather than copied.
