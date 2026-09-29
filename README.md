# Corgo's 77 Collection for Cyberpunk RED - Core (Foundry VTT)

Unofficial Foundry VTT module that adds compendiums for **Corgo's 77 Collection V3** by Corgopolis to the
Cyberpunk RED - Core system (v0.92.4, Foundry 12), without modifying the system. See
[`module/README.md`](module/README.md) for what's in it and how to install and use it.

## Building

On a fresh clone, `./setup.sh` does all of the below: it checks for Node 18+ and Python 3, installs the
dependencies, regenerates the git-ignored parser output, builds the module, and runs the validator and tests.
By hand:

    npm ci
    npm run parse       # data/corgo-77-v3.md -> data/*.parsed.json (git-ignored, so needed once per clone)
    npm run build       # src/packs/*.json -> dist/corgo-77-collection (the installable module)
    npm run validate    # checks the built packs against CPR 0.92.4 and the Solo of Fortune 2045 module
    npm test            # original-text regression checks

`npm run build:original` builds the module with Corgo's own item text instead of the rewritten rules; it needs
your export of his doc at `data/corgo-77-v3.md` (see [`DEVELOPING.md`](DEVELOPING.md)).

`src/packs/` holds every item as JSON and is the source of truth for the module. To regenerate it from
Corgo's document instead, put a text export of the doc at `data/corgo-77-v3.md` and run
`npm run parse && npm run build`. `data/` and `reference/` are git-ignored because they hold other
people's work (Corgo's full text; a copy of Schism989's module). See [`DEVELOPING.md`](DEVELOPING.md).

## Releasing

Users install the module from a manifest URL, which points at the latest GitHub Release:

    https://github.com/aky9/corgo-77-module/releases/latest/download/module.json

Releases are built by [`.github/workflows/release.yml`](.github/workflows/release.yml), so nothing built is
committed. To publish a version, bump `"version"` in `module/module.json`, commit, then tag and push:

    git tag v0.8.1
    git push origin v0.8.1

The workflow refuses a tag that does not match the manifest's version. It runs `./setup.sh` (install, parse,
build, validate, test), pins the manifest's `download` field to that tag's zip, and attaches `module.zip` and
`module.json` to a release named after the tag. The zip has `module.json` at its root, which is what Foundry
expects. `main` is for development; a release is only ever a tag.

Corgo's 77 Collection V3 is unofficial content provided under the Homebrew Content Policy of R. Talsorian
Games and is not approved or endorsed by RTG. This content references materials that are the property of
R. Talsorian Games and its licensees.
