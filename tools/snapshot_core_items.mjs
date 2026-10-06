// Snapshot the 0.92.4 item documents the NPC builder embeds into actors, so building needs no system checkout.
//
//   git clone --depth 1 --branch v0.92.4 https://gitlab.com/cyberpunk-red-team/fvtt-cyberpunk-red-core.git <dir>
//   node tools/snapshot_core_items.mjs <dir>/src/packs
//
// Writes tools/cpr-0.92.4-items.json, one item per line so a refresh diffs readably. Each item's Active Effects
// live in their own files in the system source ("!items.effects!<itemId>.<effectId>"); they are folded back
// into the item's `effects`, which is where an embedded copy carries them.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "node_modules/@foundryvtt/foundryvtt-cli/package.json"));
const YAML = require("js-yaml");

const packs = process.argv[2];
if (!packs) throw new Error("usage: node tools/snapshot_core_items.mjs <cyberpunk-red-core checkout>/src/packs");

// "skills" and "coreCyberware" are what CPRActor.create adds to a new actor. "items" is every item pack the
// system ships (core, Black Chrome, and the free DLC), in that order, which is the order the NPC builder
// prefers when two packs share a name. Critical injuries never appear in a stat block.
const sub = (top) => fs.readdirSync(path.join(packs, top)).sort().map((d) => `${top}/${d}`)
  .filter((d) => !/critical-injuries/.test(d));
const SOURCES = {
  skills: ["internal/skills"],
  coreCyberware: ["internal/cyberware-core"],
  items: [...sub("core"), ...sub("black-chrome"), ...sub("dlc")],
};

function readFolder(rel) {
  const dir = path.join(packs, rel);
  const docs = fs.readdirSync(dir).filter((f) => f.endsWith(".yaml"))
    .map((f) => YAML.load(fs.readFileSync(path.join(dir, f), "utf8"))).filter(Boolean);
  const effects = docs.filter((d) => d._key?.startsWith("!items.effects!"));
  return docs.filter((d) => d._key?.startsWith("!items!")).map((item) => {
    delete item._key;
    delete item._stats;
    delete item.folder;
    delete item.flags?.["cyberpunk-red-core"]?._migration;
    item.effects = effects.filter((e) => e._key.startsWith(`!items.effects!${item._id}.`))
      .map(({ _key, _stats, ...e }) => e);
    return item;
  }).sort((a, b) => a.name.localeCompare(b.name) || a._id.localeCompare(b._id));
}

const out = ["{", ` "_source": "cyberpunk-red-core v0.92.4, src/packs (tools/snapshot_core_items.mjs)",`];
const keys = Object.keys(SOURCES);
keys.forEach((key, i) => {
  const items = SOURCES[key].flatMap((rel) => readFolder(rel).map((d) => ({ ...d, pack: rel })));
  out.push(` "${key}": [`);
  out.push(items.map((d) => "  " + JSON.stringify(d)).join(",\n"));
  out.push(i === keys.length - 1 ? " ]" : " ],");
  console.log(`${key}: ${items.length}`);
});
out.push("}");
fs.writeFileSync(path.join(root, "tools/cpr-0.92.4-items.json"), out.join("\n") + "\n");
