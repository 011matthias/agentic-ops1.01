/* cl1pmaxxers channel art: one Vice-City-at-dusk scene drawn as SVG.
   Original artwork. No Rockstar or GTA logos, typefaces, characters or screenshots. */
(function () {
  const NS = 'http://www.w3.org/2000/svg';

  function rng(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function linear(defs, id, stops, attrs) {
    const g = el('linearGradient', Object.assign({ id, x1: 0, y1: 0, x2: 0, y2: 1 }, attrs || {}), defs);
    stops.forEach(([o, c, a]) => el('stop', { offset: o, 'stop-color': c, 'stop-opacity': a == null ? 1 : a }, g));
    return g;
  }

  function quad(p0, p1, p2, t) {
    const u = 1 - t;
    return [u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]];
  }

  function tangent(p0, p1, p2, t) {
    const dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]);
    const dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1]);
    const l = Math.hypot(dx, dy) || 1;
    return [dx / l, dy / l];
  }

  const f = (v) => v.toFixed(1);

  function filters(defs, scale) {
    const big = el('filter', { id: 'blurBig', x: '-60%', y: '-60%', width: '220%', height: '220%' }, defs);
    el('feGaussianBlur', { stdDeviation: 60 * scale }, big);
    const soft = el('filter', { id: 'blurSoft', x: '-20%', y: '-200%', width: '140%', height: '500%' }, defs);
    el('feGaussianBlur', { stdDeviation: 3 * scale }, soft);
    const neon = el('filter', { id: 'neon', x: '-30%', y: '-60%', width: '160%', height: '220%' }, defs);
    el('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: 7 * scale, result: 'b1' }, neon);
    el('feGaussianBlur', { in: 'SourceGraphic', stdDeviation: 18 * scale, result: 'b2' }, neon);
    const m = el('feMerge', {}, neon);
    ['b2', 'b1', 'b1', 'SourceGraphic'].forEach((i) => el('feMergeNode', { in: i }, m));
    const grain = el('filter', { id: 'grain', x: 0, y: 0, width: '100%', height: '100%' }, defs);
    el('feTurbulence', { type: 'fractalNoise', baseFrequency: 0.85, numOctaves: 2, stitchTiles: 'stitch' }, grain);
    el('feColorMatrix', { type: 'saturate', values: 0 }, grain);
  }

  function sky(svg, defs, o, r) {
    linear(defs, 'sky', [[0, '#06021a'], [0.3, '#1a0838'], [0.58, '#541463'], [0.8, '#c42470'], [1, '#ff7b3a']],
      { gradientUnits: 'userSpaceOnUse', x1: 0, y1: 0, x2: 0, y2: o.horizon });
    el('rect', { x: 0, y: 0, width: o.w, height: o.horizon, fill: 'url(#sky)' }, svg);
    const stars = el('g', { fill: '#ffffff' }, svg);
    for (let i = 0; i < (o.stars || 0); i++) {
      el('circle', {
        cx: f(r() * o.w), cy: f(Math.pow(r(), 1.6) * o.horizon * 0.55),
        r: f((0.5 + r() * 1.4) * o.s), opacity: (0.25 + r() * 0.7).toFixed(2),
      }, stars);
    }
  }

  function sun(svg, defs, o) {
    const { cx, cy, r } = o.sun;
    linear(defs, 'sunG', [[0, '#fff4a8'], [0.42, '#ffb547'], [0.72, '#ff5a8c'], [1, '#d8127c']],
      { gradientUnits: 'userSpaceOnUse', x1: 0, y1: cy - r, x2: 0, y2: cy + r });
    const mask = el('mask', { id: 'sunMask', maskUnits: 'userSpaceOnUse', x: 0, y: 0, width: o.w, height: o.h }, defs);
    el('rect', { x: 0, y: 0, width: o.w, height: o.h, fill: 'black' }, mask);
    el('circle', { cx, cy, r, fill: 'white' }, mask);
    let y = cy + r * 0.02;
    for (let k = 0; y < cy + r; k++) {
      const th = r * (0.016 + k * 0.011);
      el('rect', { x: cx - r, y: f(y), width: 2 * r, height: f(th), fill: 'black' }, mask);
      y += th + r * Math.max(0.05, 0.1 - k * 0.006);
    }
    el('circle', { cx, cy, r: r * 1.3, fill: '#ff4f9e', opacity: 0.55, filter: 'url(#blurBig)' }, svg);
    el('circle', { cx, cy, r, fill: 'url(#sunG)', mask: 'url(#sunMask)' }, svg);
  }

  function skyline(svg, o, r, x0, x1) {
    const g = el('g', {}, svg);
    const lit = el('g', { fill: '#ffcf7a' }, svg);
    let x = x0;
    while (x < x1) {
      const bw = (0.012 + r() * 0.026) * o.w;
      const mid = 1 - Math.abs((x - (x0 + x1) / 2) / ((x1 - x0) / 2));
      const bh = (0.03 + r() * 0.07 + mid * 0.09 * r()) * o.h;
      el('rect', { x: f(x), y: f(o.horizon - bh), width: f(bw), height: f(bh + 1), fill: '#190630' }, g);
      if (r() < 0.3) {
        el('rect', { x: f(x + bw / 2 - o.s), y: f(o.horizon - bh - 0.02 * o.h), width: f(2 * o.s), height: f(0.02 * o.h), fill: '#190630' }, g);
      }
      const ws = 0.0032 * o.w;
      for (let wy = o.horizon - bh + ws * 2; wy < o.horizon - ws * 2; wy += ws * 2.4) {
        for (let wx = x + ws; wx < x + bw - ws * 1.5; wx += ws * 2) {
          if (r() < 0.16) el('rect', { x: f(wx), y: f(wy), width: f(ws), height: f(ws * 1.3), opacity: (0.35 + r() * 0.5).toFixed(2) }, lit);
        }
      }
      x += bw + r() * 0.003 * o.w;
    }
  }

  function sea(svg, defs, o, r) {
    linear(defs, 'sea', [[0, '#3c0f52'], [1, '#08021a']],
      { gradientUnits: 'userSpaceOnUse', x1: 0, y1: o.horizon, x2: 0, y2: o.h });
    el('rect', { x: 0, y: o.horizon, width: o.w, height: o.h - o.horizon, fill: 'url(#sea)' }, svg);
    const { cx, r: sr } = o.sun;
    const n = 16;
    for (let i = 0; i < n; i++) {
      const t = i / n;
      const y = o.horizon + (o.h - o.horizon) * Math.pow(t, 1.35) + 2 * o.s;
      const w = sr * 2 * (1 - 0.045 * i) * (0.55 + 0.45 * r());
      const hgt = (o.h - o.horizon) * 0.011 * (1 + i * 0.18);
      el('rect', {
        x: f(cx - w / 2 + (r() - 0.5) * sr * 0.2), y: f(y), width: f(w), height: f(hgt), rx: f(hgt / 2),
        fill: i % 3 === 0 ? '#ffb35a' : '#ff5fa2', opacity: Math.max(0.08, 0.8 - i * 0.05).toFixed(2),
      }, svg);
    }
    el('rect', { x: 0, y: o.horizon - 1.5 * o.s, width: o.w, height: 3 * o.s, fill: '#ffd3ea', opacity: 0.85, filter: 'url(#blurSoft)' }, svg);
  }

  function palm(parent, o, r) {
    const g = el('g', { fill: o.color || '#11031c' }, parent);
    const foot = [o.x, o.base];
    const crown = [o.x + o.lean, o.base - o.height];
    const ctrl = [o.x + o.lean * 0.1, o.base - o.height * 0.55];
    const w0 = o.height * 0.03, w1 = o.height * 0.013;
    const left = [], right = [];
    for (let i = 0; i <= 30; i++) {
      const t = i / 30, p = quad(foot, ctrl, crown, t), d = tangent(foot, ctrl, crown, t);
      const n = [-d[1], d[0]], w = w0 + (w1 - w0) * t;
      left.push([p[0] + n[0] * w, p[1] + n[1] * w]);
      right.push([p[0] - n[0] * w, p[1] - n[1] * w]);
    }
    el('polygon', { points: left.concat(right.reverse()).map((p) => f(p[0]) + ',' + f(p[1])).join(' ') }, g);

    const L = o.height * (o.frondLen || 0.4);
    const n = o.fronds || 12;
    let leaves = '';
    for (let i = 0; i < n; i++) {
      const deg = -178 + (176 * i) / (n - 1) + (r() - 0.5) * 16;
      const a = (deg * Math.PI) / 180;
      const dir = [Math.cos(a), Math.sin(a)];
      const len = L * (0.8 + r() * 0.35);
      const droop = len * (0.2 + 0.6 * Math.abs(dir[0]));
      const c = [crown[0] + dir[0] * len * 0.5, crown[1] + dir[1] * len * 0.5 - len * 0.22];
      const tip = [crown[0] + dir[0] * len, crown[1] + dir[1] * len + droop];
      let rib = `M${f(crown[0])},${f(crown[1])} Q${f(c[0])},${f(c[1])} ${f(tip[0])},${f(tip[1])}`;
      el('path', { d: rib, fill: 'none', stroke: o.color || '#11031c', 'stroke-width': f(len * 0.022), 'stroke-linecap': 'round' }, g);
      for (let t = 0.06; t < 0.98; t += 0.032) {
        const p = quad(crown, c, tip, t), d = tangent(crown, c, tip, t);
        const nrm = [-d[1], d[0]];
        const ll = len * 0.24 * Math.pow(Math.sin(Math.PI * Math.min(1, t * 1.15)), 0.7);
        for (const s of [-1, 1]) {
          let v = [nrm[0] * s * 0.55 + d[0] * 0.45, nrm[1] * s * 0.55 + d[1] * 0.45 + 0.75];
          const vl = Math.hypot(v[0], v[1]); v = [v[0] / vl, v[1] / vl];
          const b = len * 0.011;
          leaves += `M${f(p[0] - d[0] * b)},${f(p[1] - d[1] * b)}L${f(p[0] + d[0] * b * 2.2)},${f(p[1] + d[1] * b * 2.2)}L${f(p[0] + v[0] * ll)},${f(p[1] + v[1] * ll)}Z`;
        }
      }
    }
    el('path', { d: leaves }, g);
    for (let i = 0; i < 3; i++) {
      el('circle', { cx: f(crown[0] + (i - 1) * L * 0.045), cy: f(crown[1] + L * 0.05), r: f(L * 0.035) }, g);
    }
  }

  function grain(svg, o, opacity) {
    el('rect', { x: 0, y: 0, width: o.w, height: o.h, filter: 'url(#grain)', opacity, style: 'mix-blend-mode:overlay' }, svg);
  }

  /* Wordmark: chrome block "CL1P" + neon script "maxxers", fitted into a box once fonts load. */
  function wordmark(svg, defs, o, box, withScript) {
    const outer = el('g', {}, svg);
    const inner = el('g', {}, outer);
    const size = 300;
    linear(defs, 'chrome', [[0, '#f5fbff'], [0.4, '#93d6ff'], [0.49, '#ffffff'], [0.51, '#26104d'], [0.72, '#7a3ed4'], [1, '#f0c4ff']],
      { gradientUnits: 'userSpaceOnUse', x1: 0, y1: -size * 0.74, x2: 0, y2: 0 });
    const sk = el('g', { transform: 'skewX(-9)' }, inner);
    const font = "'Anton', 'Impact', sans-serif";
    el('text', { x: size * 0.035, y: size * 0.05, 'text-anchor': 'middle', 'font-family': font, 'font-size': size, fill: '#12021f', 'letter-spacing': size * 0.02 }, sk).textContent = 'CL1P';
    el('text', { x: 0, y: 0, 'text-anchor': 'middle', 'font-family': font, 'font-size': size, fill: 'url(#chrome)', stroke: '#ffffff', 'stroke-width': size * 0.012, 'letter-spacing': size * 0.02 }, sk).textContent = 'CL1P';
    if (withScript) {
      const sg = el('g', { transform: `translate(${size * 0.62},${size * 0.18}) rotate(-8)`, filter: 'url(#neon)' }, inner);
      el('text', { x: 0, y: 0, 'text-anchor': 'middle', 'font-family': "'Mr Dafoe', cursive", 'font-size': size * 0.78, fill: '#ff3fae', stroke: '#ffe0f3', 'stroke-width': size * 0.006 }, sg).textContent = 'maxxers';
    }
    return function fit() {
      const bb = inner.getBBox();
      const k = Math.min(box.w / bb.width, box.h / bb.height);
      outer.setAttribute('transform', `translate(${box.cx},${box.cy}) scale(${k}) translate(${-(bb.x + bb.width / 2)},${-(bb.y + bb.height / 2)})`);
    };
  }

  function tagline(svg, o, text, cx, cy, size) {
    const g = el('g', {}, svg);
    const t = el('text', { x: cx, y: cy, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-family': "'Bebas Neue', 'Impact', sans-serif", 'font-size': size, fill: '#ffe6f2', 'letter-spacing': size * 0.32 }, g);
    t.textContent = text;
    return function fit() {
      const bb = t.getBBox();
      const gap = size * 0.6, line = size * 2.2;
      el('rect', { x: f(bb.x - gap - line), y: f(cy - size * 0.04), width: f(line), height: f(size * 0.08), fill: '#ff5fa2' }, g);
      el('rect', { x: f(bb.x + bb.width + gap - size * 0.32), y: f(cy - size * 0.04), width: f(line), height: f(size * 0.08), fill: '#ff5fa2' }, g);
    };
  }

  function whenFonts(fns) {
    const loads = ["100px 'Anton'", "100px 'Mr Dafoe'", "100px 'Bebas Neue'"].map((s) => document.fonts.load(s));
    Promise.all(loads).then(() => document.fonts.ready).then(() => {
      fns.forEach((fn) => fn());
      document.body.setAttribute('data-ready', '1');
    });
  }

  function base(svg, w, h) {
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    const defs = el('defs', {}, svg);
    return defs;
  }

  /* YouTube banner 2048x1152; everything that matters sits in the 1235x338 safe area. */
  function banner(svg, opts) {
    const w = 2048, h = 1152, r = rng(1987);
    const o = { w, h, s: 1, horizon: 690, stars: 220, sun: { cx: 1024, cy: 640, r: 228 } };
    const defs = base(svg, w, h);
    filters(defs, 1);
    sky(svg, defs, o, r);
    sun(svg, defs, o);
    skyline(svg, o, r, 300, 812);
    skyline(svg, o, r, 1236, 1750);
    sea(svg, defs, o, r);
    const palms = el('g', {}, svg);
    palm(palms, { x: 60, base: 1240, height: 640, lean: -10, frondLen: 0.42 }, r);
    palm(palms, { x: 150, base: 1300, height: 900, lean: 190, frondLen: 0.4 }, r);
    palm(palms, { x: 1988, base: 1240, height: 640, lean: 10, frondLen: 0.42 }, r);
    palm(palms, { x: 1898, base: 1300, height: 900, lean: -190, frondLen: 0.4 }, r);
    const fits = [
      wordmark(svg, defs, o, { cx: 1024, cy: 546, w: 1080, h: 262 }, true),
      tagline(svg, o, opts.tagline || 'GTA 6 STREAM HIGHLIGHTS', 1024, 718, 40),
    ];
    grain(svg, o, 0.07);
    if (opts.guides) {
      el('rect', { x: (w - 1235) / 2, y: (h - 338) / 2, width: 1235, height: 338, fill: 'none', stroke: '#00ff88', 'stroke-width': 3, 'stroke-dasharray': '12 8' }, svg);
      el('rect', { x: 0, y: (h - 423) / 2, width: w, height: 423, fill: 'none', stroke: '#00d0ff', 'stroke-width': 3 }, svg);
    }
    whenFonts(fits);
  }

  /* Profile picture 800x800; YouTube and TikTok crop it to a circle. */
  function profile(svg, opts) {
    const w = 800, h = 800, r = rng(2026);
    const o = { w, h, s: 0.6, horizon: 585, stars: 70, sun: { cx: 400, cy: 470, r: 255 } };
    const defs = base(svg, w, h);
    filters(defs, 0.55);
    sky(svg, defs, o, r);
    sun(svg, defs, o);
    sea(svg, defs, o, r);
    const palms = el('g', {}, svg);
    palm(palms, { x: 30, base: 900, height: 640, lean: 75, frondLen: 0.29, fronds: 11 }, r);
    palm(palms, { x: 770, base: 900, height: 640, lean: -75, frondLen: 0.29, fronds: 11 }, r);
    const fits = [];
    if (opts.text) fits.push(wordmark(svg, defs, o, { cx: 400, cy: 470, w: 520, h: 200 }, false));
    grain(svg, o, 0.06);
    if (opts.guides) el('circle', { cx: 400, cy: 400, r: 400, fill: 'none', stroke: '#00ff88', 'stroke-width': 3 }, svg);
    whenFonts(fits);
  }

  /* Video watermark 150x150, transparent outside the badge. */
  function watermark(svg) {
    const w = 150, h = 150, r = rng(7);
    const o = { w, h, s: 0.12, horizon: 104, stars: 8, sun: { cx: 75, cy: 88, r: 44 } };
    const defs = base(svg, w, h);
    filters(defs, 0.12);
    const clip = el('clipPath', { id: 'badge' }, defs);
    el('circle', { cx: 75, cy: 75, r: 70 }, clip);
    const g = el('g', { 'clip-path': 'url(#badge)' }, svg);
    sky(g, defs, o, r);
    sun(g, defs, o);
    sea(g, defs, o, r);
    palm(g, { x: 18, base: 170, height: 132, lean: 20, frondLen: 0.36, fronds: 9 }, r);
    el('circle', { cx: 75, cy: 75, r: 70, fill: 'none', stroke: '#ffffff', 'stroke-width': 4 }, svg);
    whenFonts([]);
  }

  window.ClipArt = { banner, profile, watermark };
})();
