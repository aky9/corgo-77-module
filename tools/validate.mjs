// Read the compiled LevelDB back and check every weapon against the CPR 0.92.4 schema's
// field set and allowed values (taken from the 0.92.4 source, not guessed).
import { ClassicLevel } from "classic-level";
import fs from "node:fs";

// Checks the built modules against a snapshot of CPR 0.92.4 facts (tools/cpr-0.92.4-reference.json),
// so no CPR checkout is needed.
// Usage: node tools/validate.mjs dist/corgo-77-collection dist/corgo-77-npcs
const DIST = process.argv[2];
const NPC_DIST = process.argv[3];
if (!DIST || !NPC_DIST) throw new Error("usage: node tools/validate.mjs <items module dist> <NPC module dist>");
const REF = JSON.parse(fs.readFileSync(new URL("./cpr-0.92.4-reference.json", import.meta.url)));
const COMPAT = JSON.parse(fs.readFileSync(new URL("./compat/schism-sof45.json", import.meta.url)));
const compatNames = new Set(COMPAT.itemNames.map((n) => n.toLowerCase()));
async function readPack(dir) {
  const db = new ClassicLevel(dir, { valueEncoding: "json" });
  const out = [];
  for await (const [k, v] of db.iterator()) out.push([k, v]);
  await db.close();
  return out;
}
const docs = [...await readPack(`${DIST}/packs/weapons`),
              // Iconic weapons are weapon documents from the same builder, so the same checks apply. The
              // pack's Iconic Weapon Mods are itemUpgrades and are checked with the other upgrades.
              ...(await readPack(`${DIST}/packs/iconic-weapons`))
                .filter(([k, d]) => !k.startsWith("!items!") || d.type === "weapon")];
const dvDocs = await readPack(`${DIST}/packs/dv-tables`);
const macroDocs = await readPack(`${DIST}/packs/macros`);

const allowed = { weaponType: REF.weaponTypes, quality: REF.itemQuality, critFailEffect: REF.critFailEffects, ammo: REF.ammoVarieties };
const coreDvTables = REF.coreDvTables;
const skills = new Set(REF.skills);
const flat = (o, p = "") => Object.entries(o).flatMap(([k, v]) => k === "description" ? [] :
  v && typeof v === "object" && !Array.isArray(v) && Object.keys(v).length && k !== "ammoData" ? flat(v, `${p}${k}.`) : [p + k]);
const refKeys = new Set(REF.weaponKeys);
// Module DV tables: rebuild each table from its LevelDB entries and sanity-check the results.
const errors = [];
const tables = new Map();
for (const [k, v] of dvDocs) if (k.startsWith("!tables!")) tables.set(v._id, { ...v, res: [] });
for (const [k, v] of dvDocs) if (k.startsWith("!tables.results!")) tables.get(k.split("!")[2].split(".")[0]).res.push(v);
const dvByName = new Map();
for (const t of tables.values()) {
  t.res.sort((a, b) => a.range[0] - b.range[0]);
  const bands = t.res.map((r) => r.range.join("-")).join(",");
  if (bands !== "0-6,7-12,13-25,26-50,51-100,101-200,201-400,401-800") errors.push(`${t.name}: bands ${bands}`);
  if (t.results.length !== t.res.length) errors.push(`${t.name}: result ids don't match entries`);
  if (!t.name.startsWith("DV ")) errors.push(`${t.name}: must start with "DV "`);
  for (const r of t.res) if (!/^(\d+|N\/A|)$/.test(r.text) || r.type !== "text" || r.weight !== 1) errors.push(`${t.name}: bad result ${JSON.stringify(r)}`);
  dvByName.set(t.name, t.res.map((r) => r.text).join(","));
}
for (const n of coreDvTables) if (!dvByName.has(n)) errors.push(`module DV pack lacks core table ${n}`);
const dvTables = [...coreDvTables, ...dvByName.keys()];
const sortedNames = [...dvByName.keys()].sort((a, b) => (a > b ? 1 : -1));   // same sort as CPR GetDvTables
const AF = { "Machine Pistol": dvByName.get("DV Machine Pistol (Autofire)"), SMG: dvByName.get("DV SMG (Autofire)"),
  "Assault Rifle": dvByName.get("DV Assault Rifle (Autofire)"), "Machine Gun": dvByName.get("DV Machine Gun (Autofire)") };
let afChecked = 0;

let items = 0, folders = 0;
for (const [key, d] of docs) {
  if (key.startsWith("!folders!")) { folders++; continue; }
  items++;
  const s = d.system, e = (m) => errors.push(`${d.name}: ${m}`);
  const keys = new Set(flat(s));
  for (const k of refKeys) if (!keys.has(k)) e(`missing ${k}`);
  for (const k of keys) if (!refKeys.has(k)) e(`unexpected field ${k}`);
  if (!allowed.weaponType.includes(s.weaponType)) e(`weaponType ${s.weaponType}`);
  if (!allowed.quality.includes(s.quality)) e(`quality ${s.quality}`);
  if (!allowed.critFailEffect.includes(s.critFailEffect)) e(`critFailEffect ${s.critFailEffect}`);
  for (const a of s.ammoVariety) if (!allowed.ammo.includes(a)) e(`ammo ${a}`);
  if (s.dvTable && !dvTables.includes(s.dvTable)) e(`dvTable ${s.dvTable}`);
  if (!skills.has(s.weaponSkill)) e(`skill ${s.weaponSkill}`);
  if (!/^\d+d6$|^0$/.test(s.damage)) e(`damage ${s.damage}`);
  for (const n of [s.rof, s.handsReq, s.magazine.max, s.installedItems.slots, s.price.market])
    if (!Number.isInteger(n) || n < 0) e(`bad number ${n}`);
  if (key !== `!items!${d._id}`) e(`key mismatch ${key}`);
  if (compatNames.has(d.name.toLowerCase())) e(`compat: name also in Schism's module`);
  // Replay 0.92.4's Autofire table lookup (cpr-actor-sheet.js) and check it lands on the right DVs.
  const m = s.description.value.match(/Autofire \(([A-Za-z ]+?) \d\)/);
  if (m && s.dvTable) {
    const base = s.dvTable.replace(" (Autofire)", "");
    const hit = sortedNames.filter((n) => n.includes(base) && n.includes("Autofire"))[0];
    if (!hit) e(`no Autofire table found for ${s.dvTable}`);
    else if (dvByName.get(hit) !== AF[m[1]]) e(`Autofire lookup ${s.dvTable} -> ${hit}, expected ${m[1]} values`);
    afChecked++;
  }
}
for (const [k, m] of macroDocs) {
  if (m.type !== "script" || !m.command.includes("dvRollTableCompendium")) errors.push(`macro ${m.name} malformed`);
  try { new Function(`return (async () => {${m.command}\n})`); } catch (err) { errors.push(`macro ${m.name}: ${err.message}`); }
}
// Compatibility with Schism989's Solo of Fortune 2045 module: every table name it ships and every weapon's
// DV table must exist in our compendium, and no item names may collide.
for (const n of COMPAT.dvTables) if (!dvByName.has(n)) errors.push(`compat: missing Schism DV table name ${n}`);
for (const w of COMPAT.weapons) {
  if (w.dvTable && !dvByName.has(w.dvTable)) errors.push(`compat: Schism weapon ${w.name} DV table ${w.dvTable} not found`);
}
// For each of Schism's weapons checked against the book, the recommended DV table must exist and its
// Autofire lookup must land on the book's Autofire type.
const RECS = JSON.parse(fs.readFileSync(new URL("./compat/schism-dv-recommendations.json", import.meta.url)));
for (const [name, b] of Object.entries(COMPAT.book)) {
  const table = RECS[name].recommended;
  if (!dvByName.has(table)) { errors.push(`compat: recommended table ${table} for ${name} missing`); continue; }
  if (b.autofire) {
    const base = table.replace(" (Autofire)", "");
    const hit = sortedNames.filter((n) => n.includes(base) && n.includes("Autofire"))[0];
    if (dvByName.get(hit) !== AF[b.autofire]) errors.push(`compat: ${name} via ${table} -> ${hit}, expected ${b.autofire}`);
  }
}

// Attachments, mods, ammo
const upRef = new Set(REF.upgradeKeys), ammoRef = new Set(REF.ammoKeys);
const counts = {};
for (const pack of ["weapon-attachments", "weapon-mods", "ammo", "armor-upgrades"]) {
  for (const [key, d] of await readPack(`${DIST}/packs/${pack}`)) {
    if (key.startsWith("!folders!")) continue;
    counts[pack] = (counts[pack] || 0) + 1;
    if (compatNames.has(d.name.toLowerCase())) errors.push(`compat: item name ${d.name} also in Schism's module`);
    const s = d.system, e = (m) => errors.push(`${pack}/${d.name}: ${m}`);
    const keys = new Set(flat(s)), ref = d.type === "ammo" ? ammoRef : upRef;
    for (const k of ref) if (!keys.has(k)) e(`missing ${k}`);
    for (const k of keys) if (!ref.has(k)) e(`unexpected field ${k}`);
    if (key !== `!items!${d._id}`) e(`key mismatch`);
    if (!Number.isInteger(s.price.market) || s.price.market < 0) e(`price ${s.price.market}`);
    if (d.type === "ammo") {
      if (!REF.ammoVarieties.includes(s.variety)) e(`variety ${s.variety}`);
      if (!REF.ammoTypes.includes(s.type)) e(`ammo type ${s.type}`);
      continue;
    }
    const upType = pack === "armor-upgrades" ? ["armor", "clothing"] : ["weapon"];
    if (d.type !== "itemUpgrade" || !upType.includes(s.type)) e(`type ${d.type}/${s.type}`);
    if (!Number.isInteger(s.size) || s.size < 0) e(`size ${s.size}`);
    for (const [k, m] of Object.entries(s.modifiers)) {
      if (k === "secondaryWeapon") continue;
      if (!["modifier", "override"].includes(m.type)) e(`modifier ${k} type ${m.type}`);
      if (m.value !== null && !Number.isInteger(m.value)) e(`modifier ${k} value ${m.value}`);
    }
    if (s.modifiers.secondaryWeapon.configured) {
      if (!allowed.weaponType.includes(s.weaponType)) e(`secondary weaponType ${s.weaponType}`);
      if (!skills.has(s.weaponSkill)) e(`secondary skill ${s.weaponSkill}`);
      if (s.dvTable && !dvTables.includes(s.dvTable)) e(`secondary dvTable ${s.dvTable}`);
      for (const a of s.ammoVariety) if (!allowed.ammo.includes(a)) e(`secondary ammo ${a}`);
      if (!/^\d+d6$|^0$/.test(s.damage)) e(`secondary damage ${s.damage}`);
    }
  }
}
console.log(`compat with ${COMPAT.module_id}: ${COMPAT.dvTables.length} table names, ${COMPAT.weapons.length} weapons, ${COMPAT.itemNames.length} item names checked`);
// Armor, shields: field set, locations, penalty, and embedded Active Effects.
const armorRef = new Set(REF.armorKeys), bonusKeys = new Set(REF.bonusKeys);
const armorDocs = await readPack(`${DIST}/packs/armor`);
const effectsById = new Map(armorDocs.filter(([k]) => k.startsWith("!items.effects!")).map(([k, v]) => [k, v]));
let armorCount = 0, effectCount = 0;
for (const [key, d] of armorDocs) {
  if (!key.startsWith("!items!")) continue;
  armorCount++;
  const s = d.system, e = (m) => errors.push(`armor/${d.name}: ${m}`);
  const keys = new Set(flat(s));
  for (const k of armorRef) if (!keys.has(k)) e(`missing ${k}`);
  for (const k of keys) if (!armorRef.has(k)) e(`unexpected field ${k}`);
  if (d.type !== "armor") e(`type ${d.type}`);
  if (compatNames.has(d.name.toLowerCase())) e(`compat: name also in Schism's module`);
  if (!Number.isInteger(s.penalty) || s.penalty < 0) e(`penalty ${s.penalty}`);
  if (s.isShield ? (s.isBodyLocation || s.isHeadLocation || s.shieldHitPoints.max <= 0) : !(s.isBodyLocation || s.isHeadLocation)) e(`location flags`);
  if (s.isBodyLocation !== s.bodyLocation.sp > 0 || s.isHeadLocation !== s.headLocation.sp > 0) e(`SP doesn't match covered locations`);
  for (const eid of d.effects) {
    const ef = effectsById.get(`!items.effects!${d._id}.${eid}`);
    if (!ef) { e(`effect ${eid} not stored`); continue; }
    effectCount++;
    for (const k of REF.effectKeys) if (!(k in ef) && k !== "_key") e(`effect missing ${k}`);
    ef.changes.forEach((c, i) => {
      if (!bonusKeys.has(c.key) && !/^system\.stats\.\w+\.value$/.test(c.key)) e(`effect key ${c.key}`);
      if (!ef.flags["cyberpunk-red-core"]?.changes?.cats?.[i]) e(`effect change ${i} has no category`);
    });
  }
}
console.log(`armor checked: ${armorCount} items, ${effectCount} effects`);

// Gear pack: gear, drugs, and the SPECTER's weapons; embedded Active Effects; drug consumed-effect names.
const gearRef = new Set(REF.gearKeys), drugRef = new Set(REF.drugKeys);
const gearDocs = await readPack(`${DIST}/packs/gear`);
const gearEffects = new Map(gearDocs.filter(([k]) => k.startsWith("!items.effects!")).map(([k, v]) => [k, v]));
const gearCounts = {};
for (const [key, d] of gearDocs) {
  if (!key.startsWith("!items!")) continue;
  gearCounts[d.type] = (gearCounts[d.type] || 0) + 1;
  const s = d.system, e = (m) => errors.push(`gear/${d.name}: ${m}`);
  const ref = d.type === "gear" ? gearRef : d.type === "drug" ? drugRef : d.type === "weapon" ? refKeys : null;
  if (!ref) { e(`unexpected type ${d.type}`); continue; }
  const keys = new Set(flat(s));
  for (const k of ref) if (!keys.has(k)) e(`missing ${k}`);
  for (const k of keys) if (!ref.has(k)) e(`unexpected field ${k}`);
  if (compatNames.has(d.name.toLowerCase())) e(`compat: name also in Schism's module`);
  if (d.type === "weapon") {
    if (!allowed.weaponType.includes(s.weaponType) || !skills.has(s.weaponSkill)) e(`weapon type/skill`);
    if (s.dvTable && !dvByName.has(s.dvTable)) e(`dvTable ${s.dvTable}`);
    continue;
  }
  if (!REF.usages.includes(s.usage)) e(`usage ${s.usage}`);
  const names = [];
  for (const eid of d.effects) {
    const ef = gearEffects.get(`!items.effects!${d._id}.${eid}`);
    if (!ef) { e(`effect ${eid} not stored`); continue; }
    names.push(ef.name);
    ef.changes.forEach((c, i) => {
      if (!bonusKeys.has(c.key) && !/^system\.stats\.(int|ref|dex|tech|cool|will|luck|move|body|emp)\.value$/.test(c.key)) e(`effect key ${c.key}`);
      if (![2, 4, 5].includes(c.mode) || Number.isNaN(Number(c.value))) e(`effect change ${c.key} mode/value`);
      if (!ef.flags["cyberpunk-red-core"]?.changes?.cats?.[i]) e(`effect change ${i} has no category`);
    });
  }
  if (d.type === "drug" && s.consumed !== "None" && !names.includes(s.consumed)) e(`consumed effect ${s.consumed} missing`);
}
console.log(`gear checked: ${JSON.stringify(gearCounts)}`);

// Foundry strips tags to build item-list summaries, tooltips and chat previews, and a block-level tag
// with no whitespace around it welds the words either side of it ("(Very Expensive)Type: Neuralware").
// Inline tags are exempt: the document's export splits words across bold runs ("**I****nstall:**"), where
// dropping the tag without a space is the correct reading.
const BLOCK_TAG = /<\/?(?:br|p|div|ul|ol|li|table|thead|tbody|tr|td|th|h[1-6])\b[^>]*>/gi;
function weldedText(html) {
  const out = [];
  for (const m of html.matchAll(BLOCK_TAG)) {
    const before = html[m.index - 1] ?? " ";
    const after = html[m.index + m[0].length] ?? " ";
    if (!/\s/.test(before) && !/\s/.test(after)) out.push(`${before}${m[0]}${after}`);
  }
  return out;
}
const packNames = JSON.parse(fs.readFileSync(`${DIST}/module.json`)).packs.filter((p) => p.type === "Item")
  .map((p) => p.name);
for (const pack of packNames) {
  for (const [key, d] of await readPack(`${DIST}/packs/${pack}`)) {
    if (!key.startsWith("!items!") || !d.system?.description) continue;
    const welds = weldedText(d.system.description.value);
    if (welds.length) errors.push(`${pack}/${d.name}: text welds when tags are stripped: ${welds[0]}`);
  }
}
console.log(`descriptions checked for stripped-tag welding across ${packNames.length} packs`);


// Cyberware, cyberware enhancements, operating systems and the OS cyberdecks. Cyberware carries the
// chapter's Active Effects; the enhancements are itemUpgrades of type "cyberware" and carry none, because
// an itemUpgrade has no "installed" usage and its effects would apply from inventory (see build_cyberware).
const cwRef = new Set(REF.cyberwareKeys), deckRef = new Set(REF.cyberdeckKeys);
const cwCounts = {};
// The Iconic packs hold the same document types (plus drugs), so they go through the same checks.
for (const pack of ["cyberware", "cyberware-upgrades", "operating-systems",
                    "iconic-cyberware", "iconic-gear"]) {
  const packDocs = await readPack(`${DIST}/packs/${pack}`);
  const packEffects = new Map(packDocs.filter(([k]) => k.startsWith("!items.effects!")).map(([k, v]) => [k, v]));
  for (const [key, d] of packDocs) {
    if (!key.startsWith("!items!")) continue;
    cwCounts[d.type] = (cwCounts[d.type] || 0) + 1;
    const s = d.system, e = (m) => errors.push(`${pack}/${d.name}: ${m}`);
    const ref = d.type === "cyberware" ? cwRef : d.type === "cyberdeck" ? deckRef
      : d.type === "itemUpgrade" ? upRef : d.type === "armor" ? armorRef
      : d.type === "drug" ? drugRef : null;
    if (!ref) { e(`unexpected type ${d.type}`); continue; }
    const keys = new Set(flat(s));
    for (const k of ref) if (!keys.has(k)) e(`missing ${k}`);
    for (const k of keys) if (!ref.has(k)) e(`unexpected field ${k}`);
    if (key !== `!items!${d._id}`) e(`key mismatch`);
    if (compatNames.has(d.name.toLowerCase())) e(`compat: name also in Schism's module`);
    if (!Number.isInteger(s.price.market) || s.price.market < 0) e(`price ${s.price.market}`);
    if (d.type === "itemUpgrade") {
      if (s.type !== "cyberware") e(`upgrade type ${s.type}`);
      if (s.size !== 0) e(`enhancement size ${s.size} (should take no Option Slot)`);
      if (d.effects.length) e(`enhancements must not carry Active Effects`);
      continue;
    }
    if (d.type === "drug") {
      // cpr-effects.js getAllowedUsage: a drug takes always/toggled/snorted, plus carried/equipped from
      // the physical mixin. "snorted" is CPR's generic dosed state, whatever the delivery method.
      if (!["always", "toggled", "snorted", "carried", "equipped"].includes(s.usage))
        e(`usage ${s.usage} is not allowed on a drug`);
      continue;
    }
    if (d.type === "cyberdeck" || d.type === "armor") {
      if (!Number.isInteger(s.installedItems?.slots ?? 0)) e(`slots`);
      continue;
    }
    // cyberware proper
    if (!REF.cyberwareTypes.includes(s.type)) e(`cyberware type ${s.type}`);
    if (!REF.cyberwareInstallList.includes(s.installLocation)) e(`installLocation ${s.installLocation}`);
    if (!REF.usages.includes(s.usage) || !["always", "toggled", "installed"].includes(s.usage))
      e(`usage ${s.usage} (cyberware allows always/toggled/installed)`);
    if (!allowed.critFailEffect.includes(s.critFailEffect)) e(`critFailEffect ${s.critFailEffect}`);
    // No check on `size` vs `isFoundational`: 0.92.4 only compares an item's size against free slots when
    // installing into another Item, never when a foundational piece goes onto the actor (see the comment in
    // cpr-container.js installItems), and core's own items use both size 0 and size 1 for foundational ware.
    if (s.installedItems.slots > 0 && !s.installedItems.allowed) e(`provides slots but installs are not allowed`);
    // Anything we give slots to has to accept the kind of item those slots are for, or they're unusable.
    if (s.installedItems.allowed && !s.installedItems.allowedTypes.length) e(`installs allowed but no allowed types`);
    for (const n of [s.size, s.installedItems.slots, s.humanityLoss.static])
      if (!Number.isInteger(n) || n < 0) e(`bad number ${n}`);
    // A plain dice formula or a number only: CPR reads roll.terms[0].results to draw the humanity-loss
    // roll card, and a function term (ceil(), floor()) has no .results and throws.
    if (!/^(\d+|\d*d\d+)$/.test(s.humanityLoss.roll)) e(`HL roll ${s.humanityLoss.roll} is not a plain dice formula`);
    if (s.isWeapon) {
      if (!allowed.weaponType.includes(s.weaponType)) e(`weaponType ${s.weaponType}`);
      if (!skills.has(s.weaponSkill)) e(`skill ${s.weaponSkill}`);
      if (!/^\d+d6$/.test(s.damage)) e(`damage ${s.damage}`);
      if (s.dvTable && !dvTables.includes(s.dvTable)) e(`dvTable ${s.dvTable}`);
      for (const a of s.ammoVariety) if (!allowed.ammo.includes(a)) e(`ammo ${a}`);
    }
    for (const eid of d.effects) {
      const ef = packEffects.get(`!items.effects!${d._id}.${eid}`);
      if (!ef) { e(`effect ${eid} not stored`); continue; }
      for (const k of REF.effectKeys) if (!(k in ef) && k !== "_key") e(`effect missing ${k}`);
      ef.changes.forEach((c, i) => {
        if (!bonusKeys.has(c.key) && !/^system\.stats\.\w+\.value$/.test(c.key)) e(`effect key ${c.key}`);
        if (![2, 3, 4, 5].includes(c.mode) || Number.isNaN(Number(c.value))) e(`effect change ${c.key} mode/value`);
        if (!ef.flags["cyberpunk-red-core"]?.changes?.cats?.[i]) e(`effect change ${i} has no category`);
      });
      // A permanent effect must apply exactly while the item is installed; an activated one is a toggle.
      const sit = Object.values(ef.flags["cyberpunk-red-core"]?.changes?.situational ?? {});
      if (s.usage === "toggled" && !sit.every((x) => x.isSituational))
        e(`toggled cyberware's effect should be situational`);
    }
  }
}
console.log(`cyberware checked: ${JSON.stringify(cwCounts)}`);
// Every enhancement names the item it enhances, and that fact reaches the player as "Enhances: X". Check
// X is something they can actually install: a name from 0.92.4, one of our own items, or a target listed
// in text/enhance_targets.json as absent from the system (with the reason, and the item says so too).
// This is what a rename breaks silently otherwise - six Iconic enhancements point at our own cyberware.
const absent = new Set(Object.keys(JSON.parse(
  fs.readFileSync(new URL("../text/enhance_targets.json", import.meta.url))).absent));
const allNames = [];
for (const pack of packNames) {
  for (const [key, d] of await readPack(`${DIST}/packs/${pack}`)) {
    if (key.startsWith("!items!")) allNames.push(d.name);
  }
}
const itemNames = new Set([...REF.itemNames, ...allNames].map((n) => n.toLowerCase()));
function resolves(target) {
  // The phrasings we use: "A or B", a trailing "(any)" or parenthetical gloss, singular/plural.
  if (absent.has(target)) return true;
  const bare = target.replace(/\s*\((?:any|Corgo's[^)]*)\)/gi, "").trim();
  for (const part of bare.split(/\s+or\s+/).map((x) => x.trim())) {
    if (absent.has(part)) return true;
    const forms = [part, part.replace(/s$/, ""), part.replace(/\s*\([^)]*\)/g, "").trim()];
    if (forms.some((f) => itemNames.has(f.toLowerCase()))) return true;
  }
  return false;
}
let enhCount = 0;
for (const pack of ["cyberware-upgrades", "operating-systems", "iconic-cyberware", "iconic-gear"]) {
  for (const [key, d] of await readPack(`${DIST}/packs/${pack}`)) {
    if (!key.startsWith("!items!") || d.type !== "itemUpgrade") continue;
    const m = /<strong>Enhances:<\/strong>\s*([^<]+)/.exec(d.system.description.value);
    if (!m) { errors.push(`${pack}/${d.name}: no "Enhances" fact on an enhancement`); continue; }
    const target = m[1].trim();
    enhCount += 1;
    if (!resolves(target)) errors.push(`${pack}/${d.name}: enhances "${target}", which is not an item in ` +
      `0.92.4 or in this module, and is not listed in text/enhance_targets.json`);
  }
}
console.log(`${enhCount} enhancement targets resolved`);

// NPC pack: mook actors with embedded items. Each actor's system data must match the 0.92.4 MookDataModel
// field set; it must carry every core skill (a compendium actor gets none for free); every installed id
// must name one of its own items, installed once; cyberware must sit where cpr-actor.js installCyberware
// would put it; and tracked armor must be an equipped armor item.
const npcDocs = await readPack(`${NPC_DIST}/packs/npcs`);
const mookRef = new Set(REF.mookKeys);
const npcItems = new Map();
for (const [k, v] of npcDocs) {
  if (!k.startsWith("!actors.items!")) continue;
  const aid = k.split("!")[2].split(".")[0];
  if (!npcItems.has(aid)) npcItems.set(aid, new Map());
  npcItems.get(aid).set(v._id, v);
}
let npcCount = 0, npcItemCount = 0;
for (const [key, d] of npcDocs) {
  if (!key.startsWith("!actors!")) continue;
  npcCount++;
  const s = d.system, e = (m) => errors.push(`npcs/${d.name}: ${m}`);
  const own = npcItems.get(d._id) ?? new Map();
  npcItemCount += own.size;
  if (d.type !== "mook") e(`type ${d.type}`);
  const keys = new Set(flat(s));
  for (const k of mookRef) if (!keys.has(k)) e(`missing ${k}`);
  for (const k of keys) if (!mookRef.has(k)) e(`unexpected field ${k}`);
  if (d.items.length !== own.size || d.items.some((id) => !own.has(id))) e("items list does not match stored items");
  const skillNames = new Set([...own.values()].filter((i) => i.type === "skill").map((i) => i.name));
  for (const n of REF.skills) if (n !== "Local Expert (Your Home)" && !skillNames.has(n)) e(`lacks core skill ${n}`);
  for (const i of own.values()) {
    if (i.type === "skill" && (!Number.isInteger(i.system.level) || i.system.level < 0)) e(`${i.name}: level ${i.system.level}`);
    if (i.type === "weapon" && !allowed.quality.includes(i.system.quality)) e(`${i.name}: quality ${i.system.quality}`);
    if (i.type === "weapon" && !/^\d+d6$|^0$/.test(i.system.damage)) e(`${i.name}: damage ${i.system.damage}`);
  }
  const host = new Map();
  const place = (parent, list) => list.forEach((id) => {
    if (!own.has(id)) e(`${parent} installs ${id}, which is not one of its items`);
    else if (host.has(id)) e(`${own.get(id).name} is installed twice`);
    else host.set(id, parent);
  });
  place("the actor", s.installedItems.list);
  for (const i of own.values()) if (i.system.installedItems) place(i._id, i.system.installedItems.list);
  for (const i of own.values()) {
    if (i.type !== "cyberware" || !host.has(i._id)) continue;
    const h = host.get(i._id);
    if (h === "the actor" && !i.system.isFoundational) e(`${i.name} is installed in the actor but is not foundational`);
    if (h !== "the actor" && own.get(h).type === "cyberware" && own.get(h).system.isFoundational
        && own.get(h).system.type !== i.system.type) e(`${i.name} (${i.system.type}) is in ${own.get(h).name} (${own.get(h).system.type})`);
  }
  for (const [slot, ref] of Object.entries(s.externalData)) {
    if (!ref.id) continue;
    const i = own.get(ref.id);
    if (!i || i.type !== "armor" || i.system.equipped !== "equipped") e(`${slot} tracks ${ref.id}, which is not equipped armor`);
  }
  // A portrait or token from npcs-module/art/ must have shipped with the module.
  for (const [what, src] of [["portrait", d.img], ["token", d.prototypeToken?.texture?.src]]) {
    const m = /^modules\/corgo-77-npcs\/(.+)$/.exec(src ?? "");
    if (m && !fs.existsSync(`${NPC_DIST}/${m[1]}`)) e(`${what} ${src} is not in the module`);
  }
  for (const html of [s.information.description, s.information.notes]) {
    const welds = weldedText(html);
    if (welds.length) e(`text welds when tags are stripped: ${welds[0]}`);
  }
}
console.log(`npcs checked: ${npcCount} actors, ${npcItemCount} embedded items`);

console.log(`attachments/mods/ammo checked: ${JSON.stringify(counts)}`);
console.log(`${items} items, ${folders} folders read back from LevelDB`);
console.log(`checked against 0.92.4: ${allowed.weaponType.length} weapon types, ${skills.size} skills; ${tables.size} module DV tables; ${afChecked} Autofire lookups replayed; ${macroDocs.length} macros parsed`);
console.log(errors.length ? errors.join("\n") : "no schema problems found");
process.exit(errors.length ? 1 : 0);
