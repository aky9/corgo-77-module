// Compile src/packs/<pack>/*.json into LevelDB packs and assemble dist/<module-id>/ for each module this
// repository ships: module/ (Corgo's 77 Collection, the items) and npcs-module/ (the NPCs, released
// separately). Each folder holds a module.json and its README, copied into dist/ as-is.
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packSrc = path.resolve(process.argv[2] || path.join(root, "src/packs"));  // or a --out dir from tools/build.py
const MODULES = ["module", "npcs-module"];

for (const folder of MODULES) {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, folder, "module.json"), "utf8"));
  const dist = path.join(root, "dist", manifest.id);
  fs.rmSync(dist, { recursive: true, force: true });
  fs.mkdirSync(dist, { recursive: true });
  for (const f of fs.readdirSync(path.join(root, folder))) {
    fs.cpSync(path.join(root, folder, f), path.join(dist, f), { recursive: true });
  }
  for (const pack of manifest.packs) {
    const src = path.join(packSrc, pack.name);
    if (!fs.existsSync(src)) throw new Error(`No source for pack ${pack.name}`);
    await compilePack(src, path.join(dist, pack.path), { log: false });
    console.log(`${manifest.id}: compiled ${pack.name}: ${fs.readdirSync(src).length} documents`);
  }
}
