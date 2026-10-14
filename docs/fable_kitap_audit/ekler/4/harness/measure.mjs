import * as F from "./mod/format.ts";
import * as G from "./mod/svg.ts";
import { readFileSync } from "node:fs";
const out = [];
const log = (...a) => { const s = a.join(" "); out.push(s); console.log(s); };
// ---------- (2) ROUNDING
const roundHalfAway = (x) => Math.sign(x) * Math.floor(Math.abs(x) + 0.5); // Rust f64::round
log("## pct0"); for (const v of [0.665, 0.675, 0.125, 0.145, 0.5, 0.505]) log(`pct0(${v}) = ${F.pct0(v)}   | v*100 = ${(v*100).toPrecision(20)} | exact-dec of v*100 = ${(v*100).toFixed(20)} | Rust round(v*100) = ${roundHalfAway(v*100)}`);
log("## pctSigned1"); for (const v of [0.00665, -0.00005, 0.0005]) log(`pctSigned1(${v}) = ${F.pctSigned1(v)}   | |v|*100 = ${(Math.abs(v)*100).toFixed(20)}`);
log("## fixed1"); for (const v of [3.25, 3.35]) log(`fixed1(${v}) = ${F.fixed1(v)}   | exact = ${v.toFixed(20)}`);
log("## points1"); for (const v of [0.00045]) log(`points1(${v}) = ${F.points1(v)}   | v*100 = ${(v*100).toFixed(20)}`);
log("## metric4"); for (const v of [0.12345]) log(`metric4(${v}) = ${F.metric4(v)}   | exact = ${v.toFixed(20)}`);
log("## tl2/price2"); for (const v of [1.005, 2.675, 27.485]) log(`tl2(${v}) = ${F.tl2(v)} price2=${F.price2(v)} | exact = ${v.toFixed(20)}`);
log("## readableCount"); for (const v of [312500000, 9999.5, 10000, 1234567.8915, 999999.9996]) log(`readableCount(${v}) = ${F.readableCount(v,{thousand:"bin",million:"milyon",billion:"milyar"})}`);
log("## short"); for (const v of [1234567.891, 0.000123456789]) log(`short(${v}) = ${F.short(v)}`);
// pct0(p_up) vs Rust fall card pct_up = 100 - round(100*(1-p_up))
log("## pct0(p_up) vs Rust fall.rs pct_up (100 - round(100*(1-p_up)))");
let mism = 0, ex = [];
for (let i = 0; i <= 100000; i++) { const p = i / 100000; const k = roundHalfAway((1 - p) * 100); const up = 100 - k; const s = F.pct0(p); if (s !== `%${up}`) { mism++; if (ex.length < 8) ex.push(`p_up=${p}: pct0→${s}, fall.rs pct_up→%${up} (p_fall=${(1-p).toPrecision(17)}, ×100=${((1-p)*100).toPrecision(17)})`); } }
log(`grid 0..1 step 1e-5: ${mism} mismatches of 100001`); ex.forEach((e) => log("  " + e));
// Math.round vs toFixed(0) for tick labels (svg.ts uses both)
log("## JS toFixed(0) vs Math.round on negative halves"); for (const v of [-0.5, -1.5, -2.5, 0.5, 1.5, 2.5]) log(`v=${v}: toFixed(0)=${v.toFixed(0)} Math.round=${Math.round(v)} Rust round=${roundHalfAway(v)}`);
// ---------- (3) distBars redraw
const fx = JSON.parse(readFileSync("/Users/ahmet/Desktop/BorsAi/app/tests/fixtures/ui/sade_record_ceiling_netgl_j3.json", "utf-8"));
const row = fx.display.rows[0];
const P = row.P_L; const w = 300, h = 120; // analiz.ts call
const svg = G.distBars(P, { w, h, highlight: row.mode_l, ring: 3, titles: P.map((p, l) => `P(L = ${l}) ${F.pct0(p)}`) });
const rects = [...svg.matchAll(/<rect class="bar[^"]*"[^>]*x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/g)].map((m) => m.slice(1).map(Number));
const max = Math.max(...P); const n = P.length; const gap = 4, labelH = 18; const bw = (w - gap * (n + 1)) / n; const ih = h - labelH;
let maxd = 0; log(`## distBars redraw (w=${w},h=${h}, n=${n}, max=P_L[${P.indexOf(max)}]=${max}, bw=${bw.toFixed(3)}, ih=${ih})`);
log("l\tP_L\t\texp_h\t\tgot_h\t\texp_y\t\tgot_y\t\texp_x\tgot_x");
P.forEach((p, i) => { const eh = (p / max) * (ih - 4); const ex_ = gap + i * (bw + gap); const [gx, gy, gw, gh] = rects[i]; const d = Math.max(Math.abs(eh - gh), Math.abs((ih - eh) - gy), Math.abs(ex_ - gx)); maxd = Math.max(maxd, d); log(`${i}\t${p.toFixed(6)}\t${eh.toFixed(3)}\t\t${gh}\t\t${(ih - eh).toFixed(3)}\t\t${gy}\t\t${ex_.toFixed(1)}\t${gx}`); });
log(`max |discrepancy| (after toFixed(1) in svg.ts) = ${maxd.toFixed(3)} px; rects parsed = ${rects.length}`);
const heights = rects.map((r) => r[3]); const order = P.map((p, i) => i).sort((a, b) => P[a] - P[b]); const monotone = order.every((idx, k) => k === 0 || heights[order[k - 1]] <= heights[idx]);
log(`monotone (P_L order == height order, non-strict): ${monotone}; tallest bar height = ${Math.max(...heights)} = ih-4 = ${ih - 4}; sum P_L = ${P.reduce((a, b) => a + b, 0)}`);
log(`ratio check: h[0]/h[3] = ${(heights[0] / heights[3]).toFixed(4)} vs P[0]/P[3] = ${(P[0] / P[3]).toFixed(4)}`);
log(`y-axis text in svg? ${/<text[^>]*>%/.test(svg)} ; tick-hi index: ${svg.match(/tick tick-hi[^>]*>(\d+)</)?.[1]} ; ring present: ${/bar-ring/.test(svg)}`);
// ---------- corridorChart redraw on sade_arz fixture
const arz = JSON.parse(readFileSync("/Users/ahmet/Desktop/BorsAi/app/tests/fixtures/ui/sade_arz_netgl.json", "utf-8")).row;
const closes = arz.days.map((d) => F.toNum(d.close_raw)), uppers = arz.days.map((d) => F.toNum(d.upper_limit_raw)), ipo = F.toNum(arz.ipo_price);
const model = arz.returns.rows.map((x) => [x.h, x.price]);
const cw = 760, ch = 300; const c = G.corridorChart({ closes, uppers, ceilings: arz.days.map((d) => d.ceiling_close), ipo, model, breakDay: arz.break_info?.b ?? null, xLabels: ["Arz", ...Array.from({ length: 10 }, (_, i) => `D${i + 1}`)], ipoLabel: "arz", breakLabel: "kırılma", lastLabel: "son" }, { w: cw, h: ch });
const pad = { l: 40, r: 16, t: 16, b: 28 }; const iw = cw - pad.l - pad.r, ihh = ch - pad.t - pad.b;
const all = [...closes, ...uppers, ipo, ...model.map((m) => m[1])].filter(Number.isFinite); const lo0 = Math.min(...all), hi0 = Math.max(...all); const padY = (hi0 - lo0) * 0.08 || 1; const lo = lo0 - padY, hi = hi0 + padY;
const sx = (k) => pad.l + (k / 10) * iw, sy = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * ihh;
const pts = [...c.matchAll(/<rect class="(pt-up|pt-down|pt-none) fade" x="([\d.]+)" y="([\d.]+)"/g)].map((m) => [m[1], +m[2], +m[3]]);
let cmax = 0; log(`## corridorChart redraw: domain lo=${lo.toFixed(4)} hi=${hi.toFixed(4)} (data ${lo0}..${hi0}, pad ${padY.toFixed(4)}); zero NOT in domain`);
closes.forEach((v, i) => { const [cls, gx, gy] = pts[i]; const dx = Math.abs(sx(i + 1) - 4 - gx), dy = Math.abs(sy(v) - 4 - gy); cmax = Math.max(cmax, dx, dy); log(`D${i + 1} close=${v} ${cls} exp(x,y)=(${(sx(i + 1) - 4).toFixed(1)},${(sy(v) - 4).toFixed(1)}) got=(${gx},${gy})`); });
log(`corridor max |discrepancy| = ${cmax.toFixed(3)} px`);
const ticks = [...c.matchAll(/<text class="tick" x="34" y="[\d.]+" text-anchor="end">([^<]+)</g)].map((m) => m[1]); const tickVals = [0, 1, 2, 3, 4].map((t) => lo + ((hi - lo) * t) / 4);
log(`corridor y tick labels: ${ticks.join(", ")} | exact grid values: ${tickVals.map((v) => v.toFixed(3)).join(", ")}`);
// low-priced example for duplicate labels
const c2 = G.corridorChart({ closes: [10.5, 11, 11.5, 11.2, null, null, null, null, null, null], uppers: [10.5, 11.55, 12.1, 12.65, null, null, null, null, null, null], ceilings: [1, 0, 0, 0, null, null, null, null, null, null], ipo: 10, model: [[1, 10.4]], breakDay: null, xLabels: [], ipoLabel: "", breakLabel: "", lastLabel: "" }, { w: 760, h: 300 });
log(`corridor low-price (10..12.65) tick labels: ${[...c2.matchAll(/text-anchor="end">([^<]+)</g)].map((m) => m[1]).join(", ")}`);
// returnDots tick labels example
const rd = G.returnDots([{ label: "D1", forecast: 0.077, realized: 0.1 }, { label: "D5", forecast: 0.12, realized: 0.05 }], { w: 460, h: 220 });
log(`returnDots ticks (data 0..0.12): ${[...rd.matchAll(/text-anchor="end">([^<]+)</g)].map((m) => m[1]).join(", ")}`);
// fanChart tick labels
const fan = G.fanChart([{ id: "a", label: "a", color: "#000", q10: [0.01, 0.02], q50: [0.05, 0.06], q90: [0.1, 0.11], rho: [0.1, 0.21] }], { xMin: 1, xMax: 2, xLabel: "", yLabel: "", cls: "" });
log(`fanChart ticks (data 0..0.21): ${[...fan.matchAll(/text-anchor="end" class="tick">([^<]+)</g)].map((m) => m[1]).join(", ")}`);
// intervalBar clamp
const ib = G.intervalBar(0.05, [-0.01, 0.2], { w: 220, h: 26, min: -0.02, max: 0.1, cls: "" }); log(`intervalBar with ci beyond max: ${ib.match(/iv-line[^>]*/)[0]}`);
// fillPct
log(`fillPct(0.5)=${G.fillPct(0.5)} fillPct(3,2)=${G.fillPct(3, 2)} fillPct(-1,2)=${G.fillPct(-1, 2)} progressPct(3,7)=${G.progressPct(3, 7)} progressPct(null,0)=${G.progressPct(null, 0)}`);
// sparkline domain
const sp = G.sparkline([25, 26, 27.5, null, 24], { w: 88, h: 30, ref: 20 }); log(`sparkline ref=20 included in domain → ref line y: ${sp.match(/spark-ref[^/]*/)[0]}`);
import { writeFileSync } from "node:fs"; writeFileSync("/tmp/borsai_kitap_audit_4/agentA/measure_out.txt", out.join("\n"));
