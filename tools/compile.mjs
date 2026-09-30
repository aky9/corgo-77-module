// Compile src/packs/<pack>/*.json into LevelDB packs and assemble dist/<module-id>/.
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "module/module.json"), "utf8"));
const dist = path.join(root, "dist", manifest.id);
const packSrc = path.resolve(process.argv[2] || path.join(root, "src/packs"));  // or a --out dir from tools/build.py

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });
for (const f of fs.readdirSync(path.join(root, "module"))) {
  fs.cpSync(path.join(root, "module", f), path.join(dist, f), { recursive: true });
}
for (const pack of manifest.packs) {
  const src = path.join(packSrc, pack.name);
  if (!fs.existsSync(src)) throw new Error(`No source for pack ${pack.name}`);
  await compilePack(src, path.join(dist, pack.path), { log: false });
  console.log(`compiled ${pack.name}: ${fs.readdirSync(src).length} documents`);
}
