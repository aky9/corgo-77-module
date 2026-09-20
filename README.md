
# Corgo's 77 Collection for Cyberpunk RED - Core (Foundry VTT)

Unofficial Foundry VTT module that adds compendiums for **Corgo's 77 Collection V3** by Corgopolis to the
Cyberpunk RED - Core system (v0.92.4, Foundry 12), without modifying the system. See
[`module/README.md`](module/README.md) for what's in it and how to install and use it.

## Building

    npm ci
    npm run compile     # src/packs/*.json -> dist/corgo-77-collection (the installable module)
    npm run validate    # checks the built packs against CPR 0.92.4 and the Solo of Fortune 2045 module

`npm run build:original` builds the module with Corgo's own item text instead of the rewritten rules; it needs
your export of his doc at `data/corgo-77-v3.md` (see [`DEVELOPING.md`](DEVELOPING.md)).

`src/packs/` holds every item as JSON and is the source of truth for the module. To regenerate it from
Corgo's document instead, put a text export of the doc at `data/corgo-77-v3.md` and run
`npm run parse && npm run build`. `data/` and `reference/` are git-ignored because they hold other
people's work (Corgo's full text; a copy of Schism989's module). See [`DEVELOPING.md`](DEVELOPING.md).

Corgo's 77 Collection V3 is unofficial content provided under the Homebrew Content Policy of R. Talsorian
Games and is not approved or endorsed by RTG. This content references materials that are the property of
R. Talsorian Games and its licensees.

# corgo-77-module

