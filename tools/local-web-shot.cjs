/**
 * local-web-shot.cjs — fresh-client rendered-state proof via headless Chrome.
 *
 * Settles "nothing changed" reports: a brand-new user-data-dir means zero
 * browser cache, so what this renders is exactly what a first-time visitor
 * sees. Captures a top screenshot, a post-scroll screenshot (proves the
 * scroll-reveal observer fired), and asserts the 4b motion markers are
 * actually present + computed in the live DOM (Ken Burns animation on the
 * hero figure, data-reveal elements transitioning to revealed).
 *
 * Usage: node tools/local-web-shot.cjs <url> <out-prefix>
 * Writes <out-prefix>-top.png, <out-prefix>-scrolled.png; prints a JSON
 * motion report. Exit 0 if motion markers present, 1 otherwise.
 */
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const APP = path.join(__dirname, "..", "workspace", "projects", "local-web", "app");
const CRI = require(path.join(APP, "node_modules", "chrome-remote-interface"));
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9223;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const [url, outPrefix] = process.argv.slice(2);
  if (!url || !outPrefix) {
    console.error("usage: node tools/local-web-shot.cjs <url> <out-prefix>");
    process.exit(2);
  }

  const chrome = spawn(CHROME, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-scrollbars",
    "--window-size=1280,2000",
    "--user-data-dir=" + path.join(require("os").tmpdir(), "shot-chrome-" + Date.now()),
  ]);
  chrome.on("error", (e) => { console.error("chrome spawn error:", e.message); process.exit(2); });

  let client;
  for (let i = 0; i < 40; i++) {
    try { client = await CRI({ port: PORT }); break; } catch { await sleep(250); }
  }
  if (!client) { console.error("no Chrome CDP"); chrome.kill(); process.exit(2); }

  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Emulation.setDeviceMetricsOverride({
    width: 1280, height: 1400, deviceScaleFactor: 1, mobile: false,
  });

  await Page.navigate({ url });
  await Page.loadEventFired();
  await sleep(800);

  // Pre-scroll motion probe: hero Ken Burns animation + reveal elements still hidden.
  const probe = await Runtime.evaluate({
    expression: `(() => {
      const figs = [...document.querySelectorAll('figure img, .kenburns, [class*="kenburns"], img')];
      const kb = figs.map(el => getComputedStyle(el).animationName).filter(n => n && n !== 'none');
      const reveal = [...document.querySelectorAll('[data-reveal]')];
      const hiddenBefore = reveal.filter(el => {
        const s = getComputedStyle(el);
        return parseFloat(s.opacity) < 0.95 || s.transform !== 'none';
      }).length;
      return JSON.stringify({
        revealCount: reveal.length,
        hiddenBeforeScroll: hiddenBefore,
        kenBurnsAnimations: [...new Set(kb)],
        title: document.title,
      });
    })()`,
    returnByValue: true,
  });
  const pre = JSON.parse(probe.result.value);

  const topShot = await Page.captureScreenshot({ format: "png" });
  fs.writeFileSync(outPrefix + "-top.png", Buffer.from(topShot.data, "base64"));

  // Scroll through the document to fire the IntersectionObserver reveals.
  await Runtime.evaluate({
    expression: `(async () => {
      const h = document.body.scrollHeight;
      for (let y = 0; y <= h; y += 600) { window.scrollTo(0, y); await new Promise(r=>setTimeout(r,120)); }
      window.scrollTo(0, 0);
    })()`,
    awaitPromise: true,
  });
  await sleep(1500);

  const postProbe = await Runtime.evaluate({
    expression: `(() => {
      const reveal = [...document.querySelectorAll('[data-reveal]')];
      const stillHidden = reveal.filter(el => {
        const s = getComputedStyle(el);
        return parseFloat(s.opacity) < 0.95;
      }).length;
      return JSON.stringify({ revealCount: reveal.length, stillHiddenAfterScroll: stillHidden });
    })()`,
    returnByValue: true,
  });
  const post = JSON.parse(postProbe.result.value);

  await Emulation.setDeviceMetricsOverride({ width: 1280, height: 1400, deviceScaleFactor: 1, mobile: false });
  const scrolledShot = await Page.captureScreenshot({ format: "png", captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: 1280, height: 1400, scale: 1 } });
  fs.writeFileSync(outPrefix + "-scrolled.png", Buffer.from(scrolledShot.data, "base64"));

  const report = {
    url, title: pre.title,
    kenBurnsAnimations: pre.kenBurnsAnimations,
    revealElements: pre.revealCount,
    hiddenBeforeScroll: pre.hiddenBeforeScroll,
    stillHiddenAfterScroll: post.stillHiddenAfterScroll,
    motionLive:
      pre.kenBurnsAnimations.length > 0 &&
      pre.revealCount > 0 &&
      post.stillHiddenAfterScroll < pre.revealCount,
  };
  console.log(JSON.stringify(report, null, 2));

  await client.close();
  chrome.kill();
  process.exit(report.motionLive ? 0 : 1);
}
main().catch((e) => { console.error("shot error:", e && e.message); process.exit(2); });
