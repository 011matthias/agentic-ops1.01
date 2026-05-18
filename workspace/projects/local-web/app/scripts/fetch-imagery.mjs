// Imagery pipeline (REBUILD-SPEC step 4).
//
// Curated stock per BRIEF art direction. No people, no fake teams, no
// headset-smiler stock. One consistent subject treatment per brand. Photos
// land in src/assets/{site}/{name}.jpg and are picked up automatically by
// Figure.astro. Attribution is recorded in src/sites/{site}/imagery.json.
//
// Usage:
//   PEXELS_API_KEY=... node scripts/fetch-imagery.mjs          # fill gaps
//   PEXELS_API_KEY=... node scripts/fetch-imagery.mjs --force   # refetch all
//
// The key is read from the environment or app/.env (gitignored). Images are
// committed to the repo so the Docker/Fly build is hermetic (no key needed
// at deploy time).

import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import { constants } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP = resolve(__dirname, "..");
const FORCE = process.argv.includes("--force");

// Per BRIEF.md art direction. orientation: landscape | portrait | square.
const SLOTS = [
  // praxis-uslu — calm editorial-clinical, warm, NOT medical-blue.
  { site: "praxis-uslu", name: "hero", orientation: "landscape",
    query: "calm modern medical practice waiting room daylight plants" },
  { site: "praxis-uslu", name: "signature", orientation: "portrait",
    query: "naturopathy herbal medicine acupuncture still life warm" },

  // coffee-boxx — warm independent-roaster editorial, no people.
  { site: "coffee-boxx", name: "hero", orientation: "landscape",
    query: "espresso pour coffee steam dark moody close up" },
  { site: "coffee-boxx", name: "gallery-1", orientation: "landscape",
    query: "espresso machine independent cafe interior warm" },
  { site: "coffee-boxx", name: "gallery-2", orientation: "portrait",
    query: "panini sandwich rustic wood board" },
  { site: "coffee-boxx", name: "gallery-3", orientation: "square",
    query: "cake slice pastry on plate coffee shop" },

  // pronto-pronto — appetite-first dark editorial, food only, no clipart.
  { site: "pronto-pronto", name: "hero", orientation: "landscape",
    query: "pizza margherita dark moody food photography overhead" },
  { site: "pronto-pronto", name: "dish-1", orientation: "landscape",
    query: "italian pasta tomato closeup dark background" },
  { site: "pronto-pronto", name: "dish-2", orientation: "landscape",
    query: "calzone folded pizza on dark surface" },
  { site: "pronto-pronto", name: "dish-3", orientation: "landscape",
    query: "wood fired pizza oven flame restaurant" },
];

async function loadKey() {
  if (process.env.PEXELS_API_KEY) return process.env.PEXELS_API_KEY.trim();
  try {
    const env = await readFile(resolve(APP, ".env"), "utf8");
    const m = env.match(/^PEXELS_API_KEY=(.+)$/m);
    if (m) return m[1].trim();
  } catch {}
  return null;
}

const exists = (p) =>
  access(p, constants.F_OK).then(() => true).catch(() => false);

async function pexelsSearch(key, query, orientation) {
  const url = new URL("https://api.pexels.com/v1/search");
  url.searchParams.set("query", query);
  url.searchParams.set("orientation", orientation);
  url.searchParams.set("per_page", "5");
  url.searchParams.set("size", "large");
  const res = await fetch(url, { headers: { Authorization: key } });
  if (!res.ok) throw new Error(`Pexels ${res.status} for "${query}"`);
  const data = await res.json();
  if (!data.photos?.length) throw new Error(`No results for "${query}"`);
  return data.photos[0];
}

async function download(src, dest) {
  const res = await fetch(src);
  if (!res.ok) throw new Error(`Download ${res.status}: ${src}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, buf);
  return buf.length;
}

const key = await loadKey();
if (!key) {
  console.error(
    "PEXELS_API_KEY not set (env or app/.env). " +
      "Pages will ship with honest designed slots until it is.",
  );
  process.exit(0);
}

const bySite = {};
let fetched = 0;
let skipped = 0;

for (const slot of SLOTS) {
  const dest = resolve(APP, "src/assets", slot.site, `${slot.name}.jpg`);
  (bySite[slot.site] ??= {});
  if (!FORCE && (await exists(dest))) {
    skipped++;
    continue;
  }
  try {
    const photo = await pexelsSearch(key, slot.query, slot.orientation);
    const bytes = await download(photo.src.large2x ?? photo.src.large, dest);
    bySite[slot.site][slot.name] = {
      alt: photo.alt || slot.query,
      photographer: photo.photographer,
      photographer_url: photo.photographer_url,
      pexels_url: photo.url,
      query: slot.query,
    };
    fetched++;
    console.log(
      `OK  ${slot.site}/${slot.name}  ${(bytes / 1024).toFixed(0)}KB  ` +
        `(${photo.photographer})`,
    );
  } catch (err) {
    console.error(`FAIL ${slot.site}/${slot.name}: ${err.message}`);
    process.exitCode = 1;
  }
}

// Merge attribution into per-site manifests (preserve entries for slots we
// skipped this run).
for (const [site, entries] of Object.entries(bySite)) {
  const manifestPath = resolve(APP, "src/sites", site, "imagery.json");
  let existing = {};
  try {
    existing = JSON.parse(await readFile(manifestPath, "utf8"));
  } catch {}
  const merged = { ...existing, ...entries };
  if (Object.keys(merged).length === 0) continue;
  await writeFile(manifestPath, JSON.stringify(merged, null, 2) + "\n");
}

console.log(`\nDone. fetched=${fetched} skipped=${skipped}`);
