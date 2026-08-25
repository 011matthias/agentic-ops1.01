// Brisken TreasuryCentral demo deck - dark cockpit system, identical treatment to
// build-mdh.js / build-smart-trading.js (same colours, fonts, primitives).
// Parameterised per prospect: node build-treasurycentral.js <sanofi|zalando>
// Content sourced from: TreasuryCentral homepage (onepilot-site), the module decks
// (MDH/Smart Trading/Digital Co-Worker), and Dirk's Rome outreach wording. No invented claims.
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const A = "C:/Users/neuma_p1qrsic/Repo/agentic-ops1/.scratch";
const LOGO = A + "/brisken-logo-light.png";
const CUBE = A + "/logo/favicon.png";
const IC = n => A + "/icons/" + n + ".png";
const LOGODIR = A + "/deckgen/logos/";

const C = { bg:"0B0E14", bg2:"0E121B", panel:"141A25", panel2:"1B2330", border:"36414F",
  ink:"F3F6FB", mut:"AAB6C7", dim:"7C8A9B", cyan:"3BE3E0", green:"46D9A0", amber:"FFC96B" };
const F = { hero:"Segoe UI Semibold", head:"Segoe UI Semibold", body:"Segoe UI", light:"Segoe UI Light" };
const M=0.62, W=13.333, H=7.5, CW=W-2*M;
const PROD = "TreasuryCentral";
const TOTAL = 10;

// ---- per-prospect config (only the tailored slides differ; the product story is shared) ----
const PROSPECTS = {
  sanofi: {
    stem: "brisken-treasurycentral-sanofi",
    company: "Sanofi",
    contact: "Ian Haegemans",
    problemHead: [{text:"A global treasury runs one process.\n",options:{}},
                  {text:"The data behind it lives in a dozen places.",options:{color:C.cyan}}],
    proofExtra: "Standardise the process once, governed and analytics-ready, and run it the same way across the whole group.",
    closeEmphasis: "the process, the analytics and the governance, end to end",
  },
  zalando: {
    stem: "brisken-treasurycentral-zalando",
    company: "Zalando",
    contact: "Lokesh Doggala",
    problemHead: [{text:"Treasury is expected to deliver on SAP, fast.\n",options:{}},
                  {text:"The data behind it lives in a dozen places.",options:{color:C.cyan}}],
    proofExtra: "An S/4HANA move is the moment these feeds get decided; TreasuryCentral is decided once and moves with you.",
    closeEmphasis: "the cockpit, the connectivity and the AI, end to end",
  },
};

const KEY = (process.argv[2] || "").toLowerCase();
const cfg = PROSPECTS[KEY];
if (!cfg) { console.error("Usage: node build-treasurycentral.js <sanofi|zalando>"); process.exit(1); }

const p = new pptxgen();
p.defineLayout({ name:"W", width:13.333, height:7.5 }); p.layout="W";
p.author="Brisken"; p.company="Brisken";
const OUT = (process.env.TC_OUT_DIR || (A + "/deckgen")) + "/" + cfg.stem + ".pptx";

// ---------- shared primitives (verbatim from build-mdh.js) ----------
function pngSize(pth){ const b=fs.readFileSync(pth); return { w:b.readUInt32BE(16), h:b.readUInt32BE(20) }; }
function logoChip(s,key,x,y,w,h){
  s.addShape(p.ShapeType.roundRect,{ x,y,w,h, rectRadius:0.14, fill:{color:"FFFFFF"}, line:{color:C.border, width:0.75} });
  const boxW=w*0.82, boxH=h*0.66;
  const d=pngSize(LOGODIR+key+".png"), ar=d.w/d.h;
  let iw=boxW, ih=iw/ar;
  if(ih>boxH){ ih=boxH; iw=ih*ar; }
  s.addImage({ path:LOGODIR+key+".png", x:x+(w-iw)/2, y:y+(h-ih)/2, w:iw, h:ih });
}
function logoStrip(s,keys,x,y,w,chipH,gap){
  const n=keys.length, cw=(w-(n-1)*gap)/n;
  keys.forEach((k,i)=> logoChip(s,k,x+i*(cw+gap),y,cw,chipH));
}
function bg(s,alt){ s.background={ color: alt?C.bg2:C.bg }; }
function glow(s,cx,cy,base){ [[6.6,93],[3.6,88]].forEach(([d,t]) =>
  s.addShape(p.ShapeType.ellipse,{ x:cx-d/2, y:cy-d/2, w:d, h:d, fill:{color:base||C.cyan, transparency:t}, line:{width:0} })); }
function eyebrow(s,txt,x,y){
  s.addShape(p.ShapeType.rect,{ x, y:y+0.02, w:0.05, h:0.24, fill:{color:C.cyan}, line:{width:0} });
  s.addText(txt.toUpperCase(),{ x:x+0.16, y:y-0.06, w:9, h:0.36, fontFace:F.head, fontSize:12, color:C.cyan, charSpacing:2, bold:true, align:"left", valign:"middle" });
}
let FN = 1;
function footer(s){
  FN++;
  s.addText([{text:"Brisken",options:{color:C.mut,bold:true}},{text:"   "+PROD+", powered by OnePilot",options:{color:C.dim}}],
    { x:M, y:H-0.5, w:9, h:0.3, fontFace:F.body, fontSize:9, align:"left", valign:"middle" });
  s.addText(String(FN).padStart(2,"0")+" / "+TOTAL,{ x:W-M-1.2, y:H-0.5, w:1.2, h:0.3, fontFace:F.body, fontSize:9, color:C.mut, align:"right", valign:"middle" });
  s.addShape(p.ShapeType.line,{ x:M, y:H-0.58, w:CW, h:0, line:{color:C.border, width:0.75} });
}
function cube(s,x,y,sz){ s.addImage({ path:CUBE, x, y, w:sz||0.34, h:sz||0.34 }); }
function panel(s,x,y,w,h,fill){ s.addShape(p.ShapeType.roundRect,{ x,y,w,h, rectRadius:0.09, fill:{color:fill||C.panel}, line:{color:C.border, width:1.1} }); }
function iconBox(s,name,x,y,box,accent){
  s.addShape(p.ShapeType.roundRect,{ x, y, w:box, h:box, rectRadius:0.11, fill:{color:C.panel2}, line:{color:accent||C.cyan, width:1.2} });
  const pad=box*0.24; s.addImage({ path:IC(name), x:x+pad, y:y+pad, w:box-2*pad, h:box-2*pad });
}

// ---------- 1 · COVER ----------
(() => { const s=p.addSlide(); bg(s);
  glow(s, 10.9, 2.1, C.cyan); glow(s, 1.4, 6.6, "5A6BFF");
  s.addImage({ path:LOGO, x:M, y:0.6, w:1.55, h:0.34 });
  // tailoring: prepared-for chip, top-right
  s.addShape(p.ShapeType.roundRect,{ x:W-M-3.9, y:0.55, w:3.9, h:0.46, rectRadius:0.23, fill:{color:C.panel}, line:{color:C.border, width:1} });
  s.addText([{text:"Prepared for  ",options:{color:C.dim}},{text:cfg.company+"  ·  "+cfg.contact,options:{color:C.ink,bold:true}}],
    { x:W-M-3.9, y:0.55, w:3.9, h:0.46, fontFace:F.body, fontSize:11, align:"center", valign:"middle" });
  eyebrow(s, "OnePilot · TreasuryCentral", M, 2.75);
  s.addText("TreasuryCentral",{ x:M-0.03, y:3.05, w:12.4, h:1.4, fontFace:F.hero, fontSize:66, color:C.ink, bold:true });
  s.addText([{text:"One cockpit for the whole treasury, on your live SAP data. ",options:{color:C.mut}},
             {text:"Market data, trading and AI, in one governed layer.",options:{color:C.cyan}}],
    { x:M, y:4.55, w:11.4, h:0.9, fontFace:F.body, fontSize:20, valign:"top", lineSpacingMultiple:1.15 });
  const fy=6.05;
  iconBox(s,"database",M,fy,0.62); s.addText("Your live SAP data",{ x:M+0.75, y:fy, w:2.7, h:0.62, fontFace:F.body, fontSize:13, color:C.ink, valign:"middle" });
  s.addShape(p.ShapeType.line,{ x:M+3.35, y:fy+0.31, w:0.7, h:0, line:{color:C.cyan, width:2, endArrowType:"triangle"} });
  s.addText("TreasuryCentral",{ x:M+4.15, y:fy, w:2.3, h:0.62, fontFace:F.body, fontSize:12, color:C.cyan, align:"center", valign:"middle", italic:true });
  s.addShape(p.ShapeType.line,{ x:M+6.5, y:fy+0.31, w:0.7, h:0, line:{color:C.cyan, width:2, endArrowType:"triangle"} });
  iconBox(s,"gauge",M+7.35,fy,0.62); s.addText("Every treasury decision",{ x:M+8.1, y:fy, w:3.4, h:0.62, fontFace:F.body, fontSize:13, color:C.ink, valign:"middle" });
})();

// ---------- 2 · THE PROBLEM (tailored head) ----------
(() => { const s=p.addSlide(); bg(s); eyebrow(s,"The problem",M,0.62);
  s.addText(cfg.problemHead,{ x:M, y:1.05, w:11.9, h:1.6, fontFace:F.head, fontSize:33, color:C.ink, bold:true, lineSpacingMultiple:1.05 });
  const y=3.55, h=2.05, w1=3.55, gw=4.0;
  panel(s,M,y,w1,h); iconBox(s,"venue",M+0.3,y+0.35,0.66);
  s.addText("Your sources",{ x:M+0.3, y:y+1.2, w:w1-0.6, h:0.4, fontFace:F.head, fontSize:15, color:C.ink, bold:true });
  s.addText("Banks, market data, trading venues, internal systems",{ x:M+0.3, y:y+1.55, w:w1-0.6, h:0.5, fontFace:F.body, fontSize:12, color:C.mut });
  const gx=M+w1+0.5;
  s.addShape(p.ShapeType.roundRect,{ x:gx, y, w:gw, h, rectRadius:0.09, fill:{color:"24190E"}, line:{color:C.amber, width:1.4, dashType:"dash"} });
  s.addImage({ path:IC("gap"), x:gx+gw/2-0.33, y:y+0.32, w:0.66, h:0.66 });
  s.addText("The manual middle",{ x:gx, y:y+1.12, w:gw, h:0.4, fontFace:F.head, fontSize:15, color:C.amber, bold:true, align:"center" });
  s.addText("re-keying rates, reconciling positions, chasing bad values, posting by hand",{ x:gx+0.35, y:y+1.5, w:gw-0.7, h:0.5, fontFace:F.body, fontSize:12, color:C.ink, align:"center", lineSpacingMultiple:1.05 });
  const sx=gx+gw+0.5, sw=W-M-sx;
  panel(s,sx,y,sw,h); iconBox(s,"database",sx+0.3,y+0.35,0.66);
  s.addText("Your systems",{ x:sx+0.3, y:y+1.2, w:sw-0.6, h:0.4, fontFace:F.head, fontSize:15, color:C.ink, bold:true });
  s.addText("SAP S/4HANA, TRM, analytics, non-SAP apps",{ x:sx+0.3, y:y+1.55, w:sw-0.6, h:0.5, fontFace:F.body, fontSize:12, color:C.mut });
  s.addShape(p.ShapeType.line,{ x:M+w1, y:y+h/2, w:0.5, h:0, line:{color:C.amber, width:2, endArrowType:"triangle"} });
  s.addShape(p.ShapeType.line,{ x:gx+gw, y:y+h/2, w:0.5, h:0, line:{color:C.amber, width:2, endArrowType:"triangle"} });
  s.addText("TreasuryCentral is that middle, so one clean, governed set of data drives every treasury decision on its own.",
    { x:M, y:6.05, w:CW, h:0.5, fontFace:F.body, fontSize:16, color:C.cyan, valign:"middle" });
  footer(s);
})();

// ---------- 3 · THE COCKPIT (solution, Dirk's own line) ----------
(() => { const s=p.addSlide(); bg(s); eyebrow(s,"The solution",M,0.62);
  s.addText("One cockpit for the whole treasury.",{ x:M, y:1.05, w:12, h:0.8, fontFace:F.head, fontSize:30, color:C.ink, bold:true });
  s.addText([{text:"The command center your team runs treasury from, on live SAP data, with market data, trading, and AI automation and orchestration around it. ",options:{color:C.mut}},
             {text:"All live with customers today, not on a roadmap.",options:{color:C.cyan}}],
    { x:M, y:1.95, w:11.9, h:1.05, fontFace:F.body, fontSize:16.5, valign:"top", lineSpacingMultiple:1.28 });
  // three pillar chips on a live-SAP-data base
  const py=3.5, ph=1.9, gap=0.4, pw=(CW-2*gap)/3;
  const pillars=[["link","Market data","Every rate and reference, curated once"],
                 ["merge","Trading","From capture to the deal in SAP"],
                 ["spark","AI automation","Digital co-workers on your SAP data"]];
  pillars.forEach((c,i)=>{ const x=M+i*(pw+gap);
    panel(s,x,py,pw,ph);
    iconBox(s,c[0],x+0.3,py+0.32,0.66);
    s.addText(c[1],{ x:x+1.1, y:py+0.34, w:pw-1.3, h:0.62, fontFace:F.head, fontSize:17, color:C.ink, bold:true, valign:"middle" });
    s.addText(c[2],{ x:x+0.3, y:py+1.12, w:pw-0.6, h:0.65, fontFace:F.body, fontSize:12.5, color:C.mut, valign:"top", lineSpacingMultiple:1.12 });
  });
  const by=py+ph+0.3;
  s.addShape(p.ShapeType.roundRect,{ x:M, y:by, w:CW, h:0.82, rectRadius:0.08, fill:{color:"10222A"}, line:{color:C.cyan, width:1.3} });
  cube(s, M+0.32, by+0.24, 0.34);
  s.addText([{text:"All of it runs on ",options:{color:C.mut}},{text:"OnePilot",options:{color:C.cyan,bold:true}},{text:", on your own live SAP data (S/4HANA, ECC, TRM), checked and logged on every value.",options:{color:C.ink}}],
    { x:M+0.9, y:by, w:CW-1.2, h:0.82, fontFace:F.body, fontSize:14, valign:"middle", lineSpacingMultiple:1.1 });
  footer(s);
})();

// ---------- 4 · WHAT RUNS IN IT (three engines) ----------
(() => { const s=p.addSlide(); bg(s,true); eyebrow(s,"What runs in it",M,0.62);
  s.addText("Three engines, one governed layer.",{ x:M, y:1.05, w:12, h:0.8, fontFace:F.head, fontSize:29, color:C.ink, bold:true });
  const cards=[
    ["link","Market Data Hub","Every rate and reference you rely on, from any source to every system. Curated once, governed end to end.","sources"],
    ["merge","Smart Trading","The manual middle between your trading venues and SAP, closed. From capture through to the deal in SAP.","flow"],
    ["spark","AI automation & orchestration","Digital co-workers that read, decide and post on your own SAP data: remittance advice, intercompany funding, and more.","ai"],
  ];
  const cw=(CW-2*0.35)/3, y=2.35, h=3.25;
  cards.forEach((c,i)=>{ const x=M+i*(cw+0.35);
    panel(s,x,y,cw,h);
    iconBox(s,c[0],x+0.3,y+0.34,0.78);
    s.addText(c[1],{ x:x+0.3, y:y+1.28, w:cw-0.6, h:0.72, fontFace:F.head, fontSize:18, color:C.ink, bold:true, valign:"top" });
    s.addText(c[2],{ x:x+0.3, y:y+2.02, w:cw-0.6, h:1.1, fontFace:F.body, fontSize:13, color:C.mut, valign:"top", lineSpacingMultiple:1.2 });
    if(c[3]==="sources") logoStrip(s,["bloomberg","lseg","ice","cme"], x+0.3, y+h-0.66, cw-0.6, 0.44, 0.12);
  });
  footer(s);
})();

// ---------- 5 · ARCHITECTURE ----------
(() => { const s=p.addSlide(); bg(s); eyebrow(s,"How it fits together",M,0.62);
  s.addText("One layer between your sources and SAP. Both ways.",{ x:M, y:1.05, w:11.9, h:0.8, fontFace:F.head, fontSize:28, color:C.ink, bold:true });
  const y=2.35, h=2.75;
  panel(s,M,y,3.35,h); iconBox(s,"venue",M+0.3,y+0.3,0.6);
  s.addText("Sources & feeds",{ x:M+1.05, y:y+0.3, w:2.1, h:0.6, fontFace:F.head, fontSize:13.5, color:C.ink, bold:true, valign:"middle" });
  s.addText("Banks, market data,\ntrading venues, central\nbanks, websites, internal",{ x:M+0.3, y:y+1.15, w:2.85, h:1.5, fontFace:F.body, fontSize:13, color:C.mut, lineSpacingMultiple:1.25 });
  const mx=M+3.35+0.5, mw=3.9;
  s.addShape(p.ShapeType.roundRect,{ x:mx, y, w:mw, h, rectRadius:0.09, fill:{color:"10222A"}, line:{color:C.cyan, width:1.5} });
  cube(s, mx+mw/2-0.24, y+0.4, 0.48);
  s.addText("TreasuryCentral",{ x:mx, y:y+1.0, w:mw, h:0.45, fontFace:F.head, fontSize:20, color:C.ink, bold:true, align:"center" });
  s.addText("on OnePilot",{ x:mx, y:y+1.42, w:mw, h:0.35, fontFace:F.body, fontSize:13.5, color:C.cyan, align:"center" });
  s.addText("runs inside your SAP landscape,\nchecks and logs every value",{ x:mx, y:y+1.82, w:mw, h:0.75, fontFace:F.body, fontSize:12, color:C.mut, align:"center", lineSpacingMultiple:1.1 });
  const rx=mx+mw+0.5, rw=W-M-rx;
  panel(s,rx,y,rw,h); iconBox(s,"database",rx+0.3,y+0.3,0.6);
  s.addText("Systems & analytics",{ x:rx+1.05, y:y+0.3, w:rw-1.3, h:0.6, fontFace:F.head, fontSize:13.5, color:C.ink, bold:true, valign:"middle" });
  s.addText("SAP ECC, S/4HANA, TRM,\nnon-SAP apps, databases,\nAnalytics Cloud",{ x:rx+0.3, y:y+1.15, w:rw-0.55, h:1.5, fontFace:F.body, fontSize:13, color:C.mut, lineSpacingMultiple:1.25 });
  s.addShape(p.ShapeType.line,{ x:M+3.35, y:y+h/2, w:0.5, h:0, line:{color:C.cyan, width:1.5, beginArrowType:"triangle", endArrowType:"triangle"} });
  s.addShape(p.ShapeType.line,{ x:mx+mw, y:y+h/2, w:0.5, h:0, line:{color:C.cyan, width:1.5, beginArrowType:"triangle", endArrowType:"triangle"} });
  const gy=y+h+0.32;
  s.addShape(p.ShapeType.roundRect,{ x:M, y:gy, w:CW, h:1.0, rectRadius:0.08, fill:{color:C.panel}, line:{color:C.border, width:1.1} });
  s.addImage({ path:IC("shield"), x:M+0.3, y:gy+0.28, w:0.44, h:0.44 });
  s.addText("Every value is validated, checked for anomalies and logged: a full audit trail, segregation of duty, no-code rules, ISO 27001 and SOC 1.",
    { x:M+0.95, y:gy, w:CW-1.25, h:1.0, fontFace:F.body, fontSize:13.5, color:C.ink, valign:"middle", lineSpacingMultiple:1.1 });
  footer(s);
})();

// ---------- 6 · GOVERNANCE ----------
(() => { const s=p.addSlide(); bg(s); eyebrow(s,"Why it is safe to automate",M,0.62);
  s.addText("The controls are built in, not bolted on.",{ x:M, y:1.05, w:11.8, h:0.8, fontFace:F.head, fontSize:28, color:C.ink, bold:true });
  const items=[
    ["list","A full audit trail","Every value and every change is recorded, end to end."],
    ["shield","Segregation of duty","The changes that matter need a second person."],
    ["eye","Automatic checks","Odd or bad data is caught before it reaches a system."],
    ["bell","Alerts on exceptions","You hear about the odd one out; the rest just runs."],
    ["blocks","No code to change it","Your rules, changed by your team, no IT project."],
    ["lock","ISO 27001 and SOC 1","The security controls your auditors already expect."],
  ];
  const cw=(CW-0.4)/2, rh=1.3;
  items.forEach((it,i)=>{ const c=i%2, r=Math.floor(i/2); const x=M+c*(cw+0.4), y=2.4+r*(rh+0.18);
    s.addShape(p.ShapeType.roundRect,{ x, y, w:cw, h:rh, rectRadius:0.08, fill:{color:C.panel}, line:{color:C.border, width:1.1} });
    iconBox(s,it[0],x+0.28,y+0.33,0.62);
    s.addText(it[1],{ x:x+1.1, y:y+0.24, w:cw-1.35, h:0.42, fontFace:F.head, fontSize:16.5, color:C.ink, bold:true });
    s.addText(it[2],{ x:x+1.1, y:y+0.66, w:cw-1.35, h:0.5, fontFace:F.body, fontSize:12.5, color:C.mut });
  });
  footer(s);
})();

// ---------- 7 · ONEPILOT ----------
(() => { const s=p.addSlide(); bg(s,true); eyebrow(s,"What it runs on",M,0.62);
  s.addText([{text:"TreasuryCentral is powered by ",options:{color:C.ink}},{text:"OnePilot",options:{color:C.cyan}},{text:".",options:{color:C.ink}}],
    { x:M, y:1.05, w:11.8, h:0.8, fontFace:F.head, fontSize:29, bold:true });
  s.addText("OnePilot is the layer underneath. It moves your data cleanly between systems, both ways, across SAP and everything else, with the checks and the AI built in. One way to connect to all of it:",
    { x:M, y:2.0, w:11.6, h:1.05, fontFace:F.body, fontSize:16, color:C.mut, lineSpacingMultiple:1.3 });
  const conn=[["database","SAP systems"],["sheet","Spreadsheets & files"],["mail","Email"],["globe","Web & APIs"],["spark","AI"]];
  const n=5, gap=0.3, cw=(CW-(n-1)*gap)/n, y=3.5, h=1.7;
  conn.forEach((c,i)=>{ const x=M+i*(cw+gap);
    s.addShape(p.ShapeType.roundRect,{ x, y, w:cw, h, rectRadius:0.1, fill:{color:C.panel}, line:{color:C.border, width:1.1} });
    s.addImage({ path:IC(c[0]), x:x+cw/2-0.34, y:y+0.32, w:0.68, h:0.68 });
    s.addText(c[1],{ x:x+0.08, y:y+1.08, w:cw-0.16, h:0.5, fontFace:F.body, fontSize:13, color:C.ink, align:"center", valign:"middle" });
  });
  s.addText([{text:"Live in weeks, not a rebuild. ",options:{color:C.cyan,bold:true}},{text:"It sits inside your SAP landscape, not beside it.",options:{color:C.mut}}],
    { x:M, y:5.6, w:CW, h:0.5, fontFace:F.body, fontSize:15 });
  footer(s);
})();

// ---------- 8 · PROOF (tailored extra line) ----------
(() => { const s=p.addSlide(); bg(s); cube(s, W-M-0.34, 0.55); eyebrow(s,"Proven where it counts",M,0.62);
  s.addText("Live with customers today, not on a roadmap.",{ x:M, y:1.05, w:11.9, h:0.8, fontFace:F.head, fontSize:29, color:C.ink, bold:true });
  s.addText("Teams like Evonik and RWZ build on OnePilot directly, SAP and non-SAP, on-prem included, and move at the speed of their own ideas rather than a vendor roadmap.",
    { x:M, y:1.98, w:11.7, h:1.1, fontFace:F.body, fontSize:16, color:C.mut, lineSpacingMultiple:1.28 });
  const y=3.4, h=1.45;
  panel(s,M,y,CW,h);
  s.addImage({ path:IC("target"), x:M+0.34, y:y+0.5, w:0.46, h:0.46 });
  s.addText(cfg.proofExtra,{ x:M+1.05, y:y, w:CW-1.35, h:h, fontFace:F.body, fontSize:15.5, color:C.ink, valign:"middle", lineSpacingMultiple:1.18 });
  // SAP co-innovation + evonik proof chips
  const cy=y+h+0.35, chH=0.72;
  logoChip(s,"sap", M, cy, 1.7, chH);
  logoChip(s,"evonik", M+1.9, cy, 1.7, chH);
  s.addText("An SAP co-innovation partner. The cockpit runs on SAP's own cloud, so it sits inside your landscape.",
    { x:M+3.95, y:cy, w:CW-3.95, h:chH, fontFace:F.body, fontSize:13, color:C.mut, valign:"middle", lineSpacingMultiple:1.12 });
  footer(s);
})();

// ---------- 9 · WHO WE ARE ----------
(() => { const s=p.addSlide(); bg(s); cube(s, W-M-0.34, 0.55); eyebrow(s,"Who we are",M,0.62);
  s.addText("We build the data and AI layer for SAP treasury.",{ x:M, y:1.05, w:11.9, h:0.9, fontFace:F.head, fontSize:30, color:C.ink, bold:true });
  const cards=[
    ["shield","Built into SAP","An SAP co-innovation partner. The cockpit runs on SAP's own cloud, so it sits inside your landscape, not beside it."],
    ["globe","Any source, any system","Provider and target agnostic. Pull from any feed, push to any system, SAP or not, and change your sources any time."],
    ["blocks","The whole treasury layer","Market data, trading and AI automation, governed in one place, with no code to run it."],
  ];
  const cw=(CW-2*0.35)/3, cy=2.35, ch=3.05;
  cards.forEach((c,i)=>{ const x=M+i*(cw+0.35);
    panel(s,x,cy,cw,ch);
    iconBox(s,c[0],x+0.3,cy+0.32,0.68);
    s.addText(c[1],{ x:x+0.3, y:cy+1.14, w:cw-0.6, h:0.5, fontFace:F.head, fontSize:18.5, color:C.ink, bold:true });
    s.addText(c[2],{ x:x+0.3, y:cy+1.62, w:cw-0.6, h:ch-1.8, fontFace:F.body, fontSize:13, color:C.mut, valign:"top", lineSpacingMultiple:1.16 });
  });
  const stats=[["1","cockpit for the whole treasury"],["0","code to run it"],["360°","audit on every change"]];
  const sw=(CW-2*0.35)/3, sy=5.85;
  stats.forEach((st,i)=>{ const x=M+i*(sw+0.35);
    s.addText(st[0],{ x, y:sy, w:1.5, h:0.85, fontFace:F.hero, fontSize:38, color:C.cyan, bold:true, valign:"middle" });
    s.addText(st[1],{ x:x+1.45, y:sy, w:sw-1.45, h:0.85, fontFace:F.body, fontSize:12.5, color:C.mut, valign:"middle" });
  });
  footer(s);
})();

// ---------- 10 · CLOSE (tailored emphasis) ----------
(() => { const s=p.addSlide(); bg(s); glow(s, 6.66, 3.3, C.cyan);
  s.addImage({ path:LOGO, x:6.66-0.85, y:1.5, w:1.7, h:0.37 });
  s.addText("Built to stay done.",{ x:1, y:2.7, w:11.33, h:1.1, fontFace:F.hero, fontSize:52, color:C.ink, bold:true, align:"center" });
  s.addText("When we talk, we will show TreasuryCentral live on your SAP data: "+cfg.closeEmphasis+".",
    { x:1.8, y:3.9, w:9.73, h:0.95, fontFace:F.body, fontSize:17, color:"C4CEDA", align:"center", lineSpacingMultiple:1.25 });
  s.addShape(p.ShapeType.roundRect,{ x:6.66-2.75, y:5.2, w:5.5, h:0.72, rectRadius:0.36, fill:{color:C.cyan}, line:{width:0} });
  s.addText("Dirk Neumann   ·   dirk.neumann@brisken.com",{ x:6.66-2.75, y:5.2, w:5.5, h:0.72, fontFace:F.body, fontSize:15, color:"07222A", bold:true, align:"center", valign:"middle" });
  s.addText("brisken.com   ·   Houston, TX",{ x:1, y:6.15, w:11.33, h:0.4, fontFace:F.body, fontSize:11.5, color:C.mut, align:"center" });
})();

p.writeFile({ fileName: OUT }).then(f => console.log("WROTE", cfg.stem, "->", f)).catch(e => { console.error("ERR", e); process.exit(1); });
