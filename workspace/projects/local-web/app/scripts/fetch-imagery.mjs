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
  // Editorial-split hero: tall right-column photo (portrait), real warm
  // EMPTY interior (no people — kills the masked-pandemic stock tell).
  { site: "praxis-uslu", name: "hero", orientation: "portrait",
    query: "empty sunlit waiting room wooden bench potted plants warm daylight interior no people" },
  { site: "praxis-uslu", name: "signature", orientation: "portrait",
    query: "acupuncture needles dried herbs warm linen still life soft window light" },

  // meinzer-maler — Werkstatt-warm trades, real work, no people/no headset stock.
  { site: "meinzer-maler", name: "hero", orientation: "landscape",
    query: "freshly painted house facade renovation warm daylight" },

  // helmle-physio — calm hands-on therapy, warm daylight, no headset-smiler stock.
  { site: "helmle-physio", name: "hero", orientation: "landscape",
    query: "physiotherapist hands treating patient back warm daylight calm" },
  { site: "helmle-physio", name: "signature", orientation: "portrait",
    query: "manual therapy hands on knee close warm natural light" },

  // beauty-lounge — warm tactile beauty, no garish stock, no hair.
  { site: "beauty-lounge", name: "hero-gesicht", orientation: "portrait",
    query: "facial skincare treatment warm soft light spa close up" },
  { site: "beauty-lounge", name: "hero-nageldesign", orientation: "portrait",
    query: "manicure nail detail elegant hands warm tactile neutral" },
  { site: "beauty-lounge", name: "hero-wellness", orientation: "portrait",
    query: "hot stone massage warm stones linen calm spa still life" },
  { site: "beauty-lounge", name: "signature", orientation: "portrait",
    query: "warm tactile beauty studio interior lamplight neutral elegant" },

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
