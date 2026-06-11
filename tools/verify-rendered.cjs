/**
 * verify-rendered.cjs — rendered-BEHAVIOR probes via headless Chrome + CDP.
 *
 * "It deployed" and "the HTML matches" prove bytes, not behavior. This tool
 * probes what actually painted (web translation of CLI-Anything's
 * frame-probing doctrine, adopted 2026-06-11):
 *
 *   1. hero paint variance — screenshot the viewport, compute luma stddev
 *      in-page (canvas over a data: URL, so no native deps). A flat block
 *      (unpainted WebGL canvas, broken hero image, blank reveal-gated
 *      section) reads as near-zero variance and FAILS.
 *   2. brand font loaded — the h1's first font-family must be loaded per
 *      document.fonts.check(); a fallback-rendered display face FAILS.
 *   3. optional theme-toggle probe (--toggle [selector], default .nav-theme)
 *      — click it, assert mean-brightness delta >= 10. This is the
 *      2026-06-01 "0/31 client pages had a working toggle" class: only a
 *      behavior probe can catch it. With --toggle given, a MISSING toggle
 *      is a FAIL (no graceful degradation).
 *
 * Usage:  node tools/verify-rendered.cjs [--toggle [selector]] <url> [...]
 * Exit 0 = all probes pass on every URL; 1 = probe failure; 2 = env error.
 * Motion-marker probes live in local-web-shot.cjs (one home per check).
 */
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const APP = path.join(__dirname, "..", "workspace", "projects", "local-web", "app");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9224;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// No graceful degradation: missing deps fail loudly with the fix.
let CRI;
try {
  CRI = require(path.join(APP, "node_modules", "chrome-remote-interface"));
} catch {
  console.error("FAIL: chrome-remote-interface not found. Fix: cd workspace/projects/local-web/app && npm install");
  process.exit(2);
}
if (!fs.existsSync(CHROME)) {
  console.error(`FAIL: Chrome not found at ${CHROME}. Fix: install Google Chrome (stable).`);
  process.exit(2);
}

// Runs IN PAGE over a data: URL of the screenshot; data: URLs do not taint
// the canvas, so getImageData works without any Node-side PNG decoding.
const STATS_FN = `(b64) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => {
    const w = 160, h = Math.max(1, Math.round(160 * img.height / img.width));
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    const ctx = cv.getContext('2d'); ctx.drawImage(img, 0, 0, w, h);
    const d = ctx.getImageData(0, 0, w, h).data;
    let sum = 0, sq = 0, n = d.length / 4;
    for (let i = 0; i < d.length; i += 4) {
      const y = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
      sum += y; sq += y * y;
    }
    const mean = sum / n;
    resolve({ mean, stddev: Math.sqrt(Math.max(0, sq / n - mean * mean)) });
  };
  img.onerror = () => reject(new Error('shot decode failed'));
  img.src = 'data:image/png;base64,' + b64;
})`;

async function lumaStats(Page, Runtime) {
  const shot = await Page.captureScreenshot({ format: "png" });
  const res = await Runtime.evaluate({
    expression: `(${STATS_FN})(${JSON.stringify(shot.data)})`,
    awaitPromise: true,
    returnByValue: true,
  });
  if (res.exceptionDetails) throw new Error("luma stats failed: " + JSON.stringify(res.exceptionDetails.text));
  return res.result.value;
}

async function main() {
  const args = process.argv.slice(2);
  let toggleSel = null;
  const urls = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--toggle") {
      toggleSel = args[i + 1] && !args[i + 1].startsWith("http") ? args[++i] : ".nav-theme";
    } else {
      urls.push(args[i]);
    }
  }
  if (urls.length === 0) {
    console.error("usage: node tools/verify-rendered.cjs [--toggle [selector]] <url> [...]");
    process.exit(2);
  }

  const chrome = spawn(CHROME, [
    "--headless=new",
    `--remote-debugging-port=${PORT}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-scrollbars",
    "--window-size=1366,900",
    "--user-data-dir=" + path.join(require("os").tmpdir(), "vr-chrome-" + Date.now()),
  ]);
  chrome.on("error", (e) => { console.error("chrome spawn error:", e.message); process.exit(2); });

  let client;
  for (let i = 0; i < 40; i++) {
    try { client = await CRI({ port: PORT }); break; } catch { await sleep(250); }
  }
  if (!client) { console.error("FAIL: no Chrome CDP endpoint"); chrome.kill(); process.exit(2); }

  const { Page, Runtime } = client;
  await Page.enable();

  let failures = 0;
  for (const url of urls) {
    await Page.navigate({ url });
    await Page.loadEventFired();
    await sleep(1500); // fonts, hero image, reveal observer

    const probes = [];

    // 1. hero paint variance
    const stats = await lumaStats(Page, Runtime);
    const painted = stats.stddev >= 8;
    probes.push({ probe: "hero-paint", pass: painted, detail: `luma stddev ${stats.stddev.toFixed(1)} (floor 8), mean ${stats.mean.toFixed(0)}` });

    // 2. brand font loaded
    const fontRes = await Runtime.evaluate({
      expression: `(() => {
        const h1 = document.querySelector('h1');
        if (!h1) return { ok: false, detail: 'no h1 on page' };
        const fam = getComputedStyle(h1).fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '');
        const generic = ['serif','sans-serif','monospace','system-ui','cursive','fantasy'];
        if (generic.includes(fam.toLowerCase())) return { ok: false, detail: 'h1 resolves to generic ' + fam };
        return { ok: document.fonts.check('16px "' + fam + '"'), detail: fam + ' loaded=' + document.fonts.check('16px "' + fam + '"') };
      })()`,
      returnByValue: true,
    });
    const font = fontRes.result.value;
    probes.push({ probe: "brand-font", pass: !!font.ok, detail: font.detail });

    // 3. optional theme-toggle behavior
    if (toggleSel) {
      const found = await Runtime.evaluate({
        expression: `(() => { const el = document.querySelector(${JSON.stringify(toggleSel)}); if (el) el.click(); return !!el; })()`,
        returnByValue: true,
      });
      if (!found.result.value) {
        probes.push({ probe: "theme-toggle", pass: false, detail: `no element matches ${toggleSel}` });
      } else {
        await sleep(400);
        const after = await lumaStats(Page, Runtime);
        const delta = Math.abs(after.mean - stats.mean);
        probes.push({ probe: "theme-toggle", pass: delta >= 10, detail: `brightness delta ${delta.toFixed(1)} (floor 10)` });
        await Runtime.evaluate({ expression: `(() => { const el = document.querySelector(${JSON.stringify(toggleSel)}); if (el) el.click(); })()` });
      }
    }

    const urlFailures = probes.filter((p) => !p.pass);
    failures += urlFailures.length;
    console.log(JSON.stringify({ url, pass: urlFailures.length === 0, probes }, null, 2));
  }

  await client.close();
  chrome.kill();
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((e) => { console.error("verify-rendered error:", e && e.message); process.exit(2); });
