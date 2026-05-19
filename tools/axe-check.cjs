/**
 * axe-check.cjs — authoritative WCAG2 A/AA check via headless Chrome + CDP.
 *
 * The Lighthouse CLI is unreliable in this Windows dev env (skil_web-build
 * section 6 note). axe-core is the same engine Lighthouse's a11y category
 * uses; run it directly over the live URL for ground truth.
 *
 * Usage:  node tools/axe-check.cjs <url> [<url> ...]
 * Exit 0 = zero violations on every URL; exit 1 = violations (printed).
 *
 * Resolves axe-core + chrome-remote-interface from the local-web app's
 * node_modules; Chrome path uses forward slashes (backslashes get mangled
 * through bash).
 */
const { spawn } = require("child_process");
const path = require("path");

const APP = path.join(__dirname, "..", "workspace", "projects", "local-web", "app");
const CRI = require(path.join(APP, "node_modules", "chrome-remote-interface"));
const axePath = path.join(APP, "node_modules", "axe-core", "axe.min.js");
const axeSource = require("fs").readFileSync(axePath, "utf8");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9222;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const urls = process.argv.slice(2);
  if (urls.length === 0) {
    console.error("usage: node tools/axe-check.cjs <url> [...]");
    process.exit(2);
  }

  const chrome = spawn(CHROME, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=" + path.join(require("os").tmpdir(), "axe-chrome-" + Date.now()),
  ]);
  chrome.on("error", (e) => {
    console.error("chrome spawn error:", e.message);
    process.exit(2);
  });

  // Wait for the debugging endpoint.
  let client;
  for (let i = 0; i < 40; i++) {
    try {
      client = await CRI({ port: PORT });
      break;
    } catch {
      await sleep(250);
    }
  }
  if (!client) {
    console.error("could not connect to Chrome CDP");
    chrome.kill();
    process.exit(2);
  }

  const { Page, Runtime } = client;
  await Page.enable();

  let totalViolations = 0;
  for (const url of urls) {
    await Page.navigate({ url });
    await Page.loadEventFired();
    await sleep(1200); // let the reveal observer settle
    await Runtime.evaluate({ expression: axeSource });
    const res = await Runtime.evaluate({
      expression: `axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}).then(r=>JSON.stringify(r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length,desc:v.description}))))`,
      awaitPromise: true,
    });
    const violations = JSON.parse(res.result.value);
    totalViolations += violations.length;
    if (violations.length === 0) {
      console.log(`PASS  ${url}  — 0 WCAG2 A/AA violations`);
    } else {
      console.log(`FAIL  ${url}  — ${violations.length} violation type(s):`);
      for (const v of violations) {
        console.log(`  [${v.impact}] ${v.id} (${v.nodes} node[s]): ${v.desc}`);
      }
    }
  }

  await client.close();
  chrome.kill();
  process.exit(totalViolations === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("axe-check error:", e && e.message);
  process.exit(2);
});
