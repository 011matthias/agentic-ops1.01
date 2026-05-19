/**
 * depth-live.cjs — fresh-profile live visual proof of the 4b WebGL depth
 * hero + pointer parallax. Uses the full-page captureBeyondViewport path
 * (reliable in this Windows env; avoids the CDP clip-coordinate trap).
 *
 * Per URL: zero-cache profile, desktop (fine pointer, no reduced-motion,
 * >768px so 4b guardrails permit init). Neutralizes scroll-reveal so a
 * static capture shows the hero. Screenshot A (pointer top-left of hero),
 * then B (pointer bottom-right) — A vs B must differ = parallax live.
 *
 * Usage: node tools/depth-live.cjs <out-dir> <url> [<url> ...]
 */
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const APP = path.join(__dirname, "..", "workspace", "projects", "local-web", "app");
const CRI = require(path.join(APP, "node_modules", "chrome-remote-interface"));
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9225;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const [outDir, ...urls] = process.argv.slice(2);
  if (!outDir || !urls.length) { console.error("usage: depth-live.cjs <out> <url>..."); process.exit(2); }
  fs.mkdirSync(outDir, { recursive: true });

  const chrome = spawn(CHROME, [
    "--headless=new", `--remote-debugging-port=${PORT}`,
    "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
    "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
    "--user-data-dir=" + path.join(require("os").tmpdir(), "depthlive-" + Date.now()),
  ]);
  chrome.on("error", (e) => { console.error("chrome:", e.message); process.exit(2); });
  let client;
  for (let i = 0; i < 50; i++) { try { client = await CRI({ port: PORT }); break; } catch { await sleep(250); } }
  if (!client) { console.error("no CDP"); chrome.kill(); process.exit(2); }

  const { Page, Runtime, Input, Emulation } = client;
  await Page.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });

  for (const url of urls) {
    const slug = (url.split("/").filter(Boolean).pop() || "p").replace(/[^a-z0-9-]/gi, "_");
    await Page.navigate({ url });
    await Page.loadEventFired();

    // wait for the canvas to fade in (idle + IO + 2 textures), max ~10s
    let st = {};
    for (let i = 0; i < 50; i++) {
      await sleep(200);
      const r = await Runtime.evaluate({
        expression: `(()=>{const d=document.querySelector('.depthhero');const c=d&&d.querySelector('canvas.depthhero__gl');
          return JSON.stringify({on:!!(d&&d.classList.contains('is-on')),cw:c?c.width:0,
          y:d?Math.round(d.getBoundingClientRect().top+scrollY):-1});})()`,
        returnByValue: true });
      st = JSON.parse(r.result.value);
      if (st.on && st.cw > 0) break;
    }
    // make the hero statically visible regardless of scroll-reveal timing
    await Runtime.evaluate({ expression:
      `document.querySelectorAll('[data-reveal]').forEach(e=>{e.style.opacity=1;e.style.transform='none';e.style.transition='none';});
       window.scrollTo(0, Math.max(0, ${st.y} - 120));` });
    await sleep(700);

    const shoot = async (tag) => {
      const { data } = await Page.captureScreenshot({ format: "png", captureBeyondViewport: true,
        clip: { x: 0, y: Math.max(0, st.y - 120), width: 1366, height: 760, scale: 1 } });
      fs.writeFileSync(path.join(outDir, `${slug}-${tag}.png`), Buffer.from(data, "base64"));
    };
    await Input.dispatchMouseEvent({ type: "mouseMoved", x: 240, y: 230 });
    await sleep(800); await shoot("A");
    await Input.dispatchMouseEvent({ type: "mouseMoved", x: 1150, y: 560 });
    await sleep(1000); await shoot("B");
    console.log(`${slug}: is-on=${st.on} canvasW=${st.cw} -> ${slug}-A.png / ${slug}-B.png`);
  }
  await client.close(); chrome.kill(); process.exit(0);
}
main().catch((e) => { console.error("depth-live:", e && e.message); process.exit(2); });
