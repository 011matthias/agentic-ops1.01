#!/usr/bin/env node
// One-command spell-gate fixer. Scans the exact glob + config the CI "Spell
// check" job uses, collects every word cspell flags as unknown, and appends
// them (deduped case-insensitively, sorted among themselves) to the `words`
// allowlist in cspell.config.json.
//
// The gate stays strict on purpose: this just turns "CI red -> hand-edit JSON
// -> guess the word" into one command. A flagged token is usually a new proper
// noun (person, company, city) that belongs in the allowlist -- but a real
// prose typo will ALSO show up here, so review the additions before committing
// and fix typos in the source instead of whitelisting them.
//
// Usage (from platform/):  npm run spell:fix
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const platform = dirname(here); // platform/
const configPath = join(platform, "cspell.config.json");
const GLOB = "src/**/*.{tsx,ts,md}"; // mirror the CI spell job exactly

// cspell exits non-zero whenever it finds issues; --words-only prints just the
// unknown tokens (one per line), --unique dedupes, --no-summary keeps stdout to
// words only. Capture stdout regardless of exit code.
let out = "";
try {
  out = execSync(
    `npx cspell "${GLOB}" --config cspell.config.json --words-only --unique --no-progress --no-summary`,
    { cwd: platform, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  );
} catch (e) {
  out = e.stdout ? e.stdout.toString() : "";
}

const found = [
  ...new Set(
    out
      .split(/\r?\n/)
      .map((w) => w.trim())
      .filter(Boolean),
  ),
];

const config = JSON.parse(readFileSync(configPath, "utf8"));
const existing = new Set((config.words || []).map((w) => w.toLowerCase()));
const toAdd = found
  .filter((w) => !existing.has(w.toLowerCase()))
  .sort((a, b) => a.localeCompare(b));

if (toAdd.length === 0) {
  console.log("[spell:fix] no unknown words; the allowlist already covers the tree.");
  process.exit(0);
}

config.words = [...(config.words || []), ...toAdd];
writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n", "utf8");

console.log(`[spell:fix] added ${toAdd.length} word(s) to cspell.config.json:`);
for (const w of toAdd) console.log(`  + ${w}`);
console.log(
  "[spell:fix] review these, then commit. Real typos belong fixed in the source, not added here.",
);
