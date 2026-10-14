// İki basit SVG üreticisi (SPEC_APP §1.1: grafik kütüphanesi yok). Yalnız çizim: değerler Rust
// komutlarından gelir; buradaki aritmetik piksel koordinatıdır.
import { esc } from "../dom";

export interface Series {
  id: string;
  label: string;
  color: string;
  /** [x, y]; y null ise çizgi o noktada kesilir. */
  points: [number, number | null][];
  dashed?: boolean;
}

const W = 560;
const H = 250;
const PAD = { l: 44, r: 12, t: 14, b: 34 };

export function lineChart(series: Series[], o: { xMin: number; xMax: number; xLabel: string; yLabel: string; cls: string }): string {
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const span = Math.max(o.xMax - o.xMin, 1);
  const sx = (x: number) => PAD.l + ((x - o.xMin) / span) * iw;
  const sy = (y: number) => PAD.t + (1 - y) * ih;
  const parts: string[] = [];
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    parts.push(`<line x1="${PAD.l}" x2="${W - PAD.r}" y1="${sy(t)}" y2="${sy(t)}" class="grid-line"/>`);
    parts.push(`<text x="${PAD.l - 6}" y="${sy(t) + 4}" text-anchor="end" class="tick">%${Math.round(t * 100)}</text>`);
  }
  for (let x = o.xMin; x <= o.xMax; x += 1) {
    parts.push(`<text x="${sx(x)}" y="${H - PAD.b + 14}" text-anchor="middle" class="tick">${x}</text>`);
  }
  for (const s of series) {
    let d = "";
    let pen = false;
    for (const [x, y] of s.points) {
      if (y === null || !Number.isFinite(y)) {
        pen = false;
        continue;
      }
      d += `${pen ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`;
      pen = true;
    }
    const dash = s.dashed ? ` stroke-dasharray="5 4"` : "";
    parts.push(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"${dash} data-series="${esc(s.id)}"><title>${esc(s.label)}</title></path>`);
    for (const [x, y] of s.points) {
      if (y !== null && Number.isFinite(y)) parts.push(`<circle cx="${sx(x).toFixed(1)}" cy="${sy(y).toFixed(1)}" r="2.5" fill="${s.color}"/>`);
    }
  }
  parts.push(`<text x="${PAD.l + iw / 2}" y="${H - 4}" text-anchor="middle" class="axis-label">${esc(o.xLabel)}</text>`);
  parts.push(`<text x="12" y="${PAD.t + ih / 2}" text-anchor="middle" transform="rotate(-90 12 ${PAD.t + ih / 2})" class="axis-label">${esc(o.yLabel)}</text>`);
  return `<svg class="chart ${o.cls}" viewBox="0 0 ${W} ${H}" role="img">${parts.join("")}</svg>`;
}

export function barChart(
  values: (number | null)[],
  o: { color: string; title: string; tooltip: string; labels: string[]; ticks?: string[] },
): string {
  const bw = 16;
  const gap = 4;
  const h = 90;
  const w = values.length * (bw + gap) + gap;
  const bars = values.map((v, i) => {
    const y = v === null || !Number.isFinite(v) ? 0 : Math.max(0, Math.min(1, v));
    const bh = y * h;
    const x = gap + i * (bw + gap);
    return `<rect x="${x}" y="${h - bh + 4}" width="${bw}" height="${bh}" fill="${o.color}"><title>${esc(o.labels[i] ?? "")}</title></rect>` +
      `<text x="${x + bw / 2}" y="${h + 16}" text-anchor="middle" class="tick">${esc(o.ticks?.[i] ?? String(i))}</text>`;
  });
  return `<figure class="bars"><figcaption title="${esc(o.tooltip)}">${esc(o.title)}</figcaption><svg viewBox="0 0 ${w} ${h + 20}" width="${w}" height="${h + 20}" role="img">${bars.join("")}</svg></figure>`;
}

/** Yelpaze grafiği serisi: q10–q90 bandı, q50 çizgisi ve limit yolu (rho_h) kesikli. */
export interface FanSeries {
  id: string;
  label: string;
  color: string;
  q10: (number | null)[];
  q50: (number | null)[];
  q90: (number | null)[];
  rho: (number | null)[];
}

/**
 * Getiri yelpazesi (EK 2 §4.2). Bütün değerler Rust çıktısıdır; burada YALNIZ piksel koordinatı
 * hesaplanır (U25): y ekseni verinin en küçük/en büyük değerine oturur.
 */
export function fanChart(series: FanSeries[], o: { xMin: number; xMax: number; xLabel: string; yLabel: string; cls: string }): string {
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const all: number[] = [];
  for (const s of series) {
    for (const v of [...s.q10, ...s.q50, ...s.q90, ...s.rho]) {
      if (v !== null && Number.isFinite(v)) all.push(v);
    }
  }
  const lo = all.length ? Math.min(0, ...all) : 0;
  const hi = all.length ? Math.max(0, ...all) : 1;
  const span = hi - lo === 0 ? 1 : hi - lo;
  const xSpan = Math.max(o.xMax - o.xMin, 1);
  const sx = (x: number) => PAD.l + ((x - o.xMin) / xSpan) * iw;
  const sy = (y: number) => PAD.t + (1 - (y - lo) / span) * ih;
  const parts: string[] = [];
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    const v = lo + t * span;
    parts.push(`<line x1="${PAD.l}" x2="${W - PAD.r}" y1="${sy(v)}" y2="${sy(v)}" class="grid-line"/>`);
    parts.push(`<text x="${PAD.l - 6}" y="${sy(v) + 4}" text-anchor="end" class="tick">%${(v * 100).toFixed(0)}</text>`);
  }
  for (let x = o.xMin; x <= o.xMax; x += 1) {
    parts.push(`<text x="${sx(x)}" y="${H - PAD.b + 14}" text-anchor="middle" class="tick">${x}</text>`);
  }
  const at = (xs: (number | null)[], i: number) => {
    const v = xs[i];
    return v !== null && v !== undefined && Number.isFinite(v) ? v : null;
  };
  for (const s of series) {
    const top: string[] = [];
    const bottom: string[] = [];
    for (let i = 0; i < s.q90.length; i += 1) {
      const a = at(s.q90, i);
      const b = at(s.q10, i);
      if (a === null || b === null) continue;
      const x = sx(o.xMin + i).toFixed(1);
      top.push(`${x},${sy(a).toFixed(1)}`);
      bottom.unshift(`${x},${sy(b).toFixed(1)}`);
    }
    if (top.length) {
      parts.push(`<polygon points="${[...top, ...bottom].join(" ")}" fill="${s.color}" fill-opacity="0.18" data-band="${esc(s.id)}"><title>${esc(s.label)}</title></polygon>`);
    }
    const line = (xs: (number | null)[], dashed: boolean, role: string) => {
      let d = "";
      let pen = false;
      for (let i = 0; i < xs.length; i += 1) {
        const v = at(xs, i);
        if (v === null) {
          pen = false;
          continue;
        }
        d += `${pen ? "L" : "M"}${sx(o.xMin + i).toFixed(1)},${sy(v).toFixed(1)}`;
        pen = true;
      }
      if (d === "") return;
      parts.push(
        `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"${dashed ? ` stroke-dasharray="5 4"` : ""}` +
          ` data-series="${esc(s.id)}" data-role="${role}"><title>${esc(s.label)}</title></path>`,
      );
    };
    line(s.q50, false, "q50");
    line(s.rho, true, "rho");
  }
  parts.push(`<text x="${PAD.l + iw / 2}" y="${H - 4}" text-anchor="middle" class="axis-label">${esc(o.xLabel)}</text>`);
  parts.push(`<text x="12" y="${PAD.t + ih / 2}" text-anchor="middle" transform="rotate(-90 12 ${PAD.t + ih / 2})" class="axis-label">${esc(o.yLabel)}</text>`);
  return `<svg class="chart ${o.cls}" viewBox="0 0 ${W} ${H}" role="img">${parts.join("")}</svg>`;
}

export function legend(series: Series[]): string {
  return `<div class="legend">${series.map((s) => `<span class="legend-item"><i style="background:${s.color}"></i>${esc(s.label)}</span>`).join("")}</div>`;
}

// ---------------------------------------------------------------- sade görünüm koordinatları (FAZ9_APP_UI; yalnız ekleme)
// Bütün değerler Rust komutlarından gelir; burada YALNIZ piksel koordinatı ve CSS genişliği hesaplanır (U25). Sınıflar
// (`draw`, `grow`, `fade`) sade.css'teki tek açılış hareketidir (K-UI-10; prefers-reduced-motion'da oynamaz).

const finiteOr = (v: number | null | undefined): v is number => v !== null && v !== undefined && Number.isFinite(v);

/** CSS genişliği: 0..max aralığında değer → "%" dizesi (0..100'e kırpılır). */
export function fillPct(v: number | null | undefined, max = 1): string {
  if (!finiteOr(v) || max <= 0) return "0%";
  return `${Math.max(0, Math.min(100, (v / max) * 100)).toFixed(1)}%`;
}

/** Sayım çubuğu: n / of → "%" dizesi (canlı sicil ilerlemesi). */
export function progressPct(n: number | null | undefined, of: number): string {
  return fillPct(n ?? 0, of);
}

/** Satır içi kıvılcım çizgisi: kapanışlar (null = gün yok), isteğe bağlı referans çizgisi (arz fiyatı). */
export function sparkline(values: (number | null)[], o: { w: number; h: number; ref?: number | null; cls?: string; title?: string }): string {
  const pts = values.map((v, i) => [i, v] as [number, number | null]).filter((p): p is [number, number] => finiteOr(p[1]));
  const all = pts.map((p) => p[1]);
  if (finiteOr(o.ref)) all.push(o.ref);
  if (!pts.length) return `<svg class="spark ${o.cls ?? ""}" viewBox="0 0 ${o.w} ${o.h}" width="${o.w}" height="${o.h}" aria-hidden="true"></svg>`;
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const span = hi - lo === 0 ? 1 : hi - lo;
  const n = Math.max(values.length - 1, 1);
  const pad = 2;
  const sx = (i: number) => pad + (i / n) * (o.w - pad * 2);
  const sy = (v: number) => pad + (1 - (v - lo) / span) * (o.h - pad * 2);
  const line = pts.map((p, k) => `${k === 0 ? "M" : "L"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
  const first = pts[0];
  const last = pts[pts.length - 1];
  const area = `${line}L${sx(last[0]).toFixed(1)},${o.h}L${sx(first[0]).toFixed(1)},${o.h}Z`;
  const ref = finiteOr(o.ref) ? `<line class="spark-ref" x1="0" x2="${o.w}" y1="${sy(o.ref).toFixed(1)}" y2="${sy(o.ref).toFixed(1)}"/>` : "";
  const title = o.title ? `<title>${esc(o.title)}</title>` : "";
  return `<svg class="spark ${o.cls ?? ""}" viewBox="0 0 ${o.w} ${o.h}" width="${o.w}" height="${o.h}" role="img">${title}${ref}` +
    `<path class="spark-area fade" d="${area}"/><path class="spark-line draw" pathLength="1" d="${line}"/></svg>`;
}

/** P(L = l) çubukları (l = 0..10): en olası çubuk vurgulu, gerçekleşen l halkalı. */
export function distBars(values: (number | null)[], o: { w: number; h: number; highlight: number | null; ring: number | null; titles: string[] }): string {
  const max = Math.max(...values.filter(finiteOr), 0) || 1;
  const n = values.length;
  const gap = 4;
  const labelH = 18;
  const bw = (o.w - gap * (n + 1)) / n;
  const ih = o.h - labelH;
  const parts = values.map((v, i) => {
    const x = gap + i * (bw + gap);
    const bh = finiteOr(v) ? (v / max) * (ih - 4) : 0;
    const cls = i === o.highlight ? "bar bar-hi grow" : "bar grow";
    const ring = i === o.ring ? `<rect class="bar-ring" x="${(x - 2).toFixed(1)}" y="${(ih - bh - 2).toFixed(1)}" width="${(bw + 4).toFixed(1)}" height="${(bh + 2).toFixed(1)}" rx="3"/>` : "";
    return `${ring}<rect class="${cls}" style="animation-delay:${(0.3 + i * 0.05).toFixed(2)}s" x="${x.toFixed(1)}" y="${(ih - bh).toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="2"><title>${esc(o.titles[i] ?? "")}</title></rect>` +
      `<text class="tick${i === o.highlight ? " tick-hi" : ""}" x="${(x + bw / 2).toFixed(1)}" y="${o.h - 4}" text-anchor="middle">${i}</text>`;
  });
  return `<svg class="dist" viewBox="0 0 ${o.w} ${o.h}" role="img"><line class="axis" x1="0" x2="${o.w}" y1="${ih}" y2="${ih}"/>${parts.join("")}</svg>`;
}

/**
 * Seri hesaplayıcı eğrisi (K-UI-8): koşulsuz S_k (S_0 = 1) ve seçilen j'ye koşullu P(L ≥ k | L ≥ j) (k = j'de 1). Değerler
 * Rust'tan (`ceiling_display` S ve cond.S_cond); burada yalnız piksel. Geçmiş günler (0..j) gölgeli; yarın noktası vurgulu.
 */
export function survivalCurve(uncond: (number | null)[], cond: (number | null)[] | null, j: number, o: { w: number; h: number; tip: string }): string {
  const pad = { l: 34, r: 12, t: 12, b: 26 };
  const iw = o.w - pad.l - pad.r;
  const ih = o.h - pad.t - pad.b;
  const sx = (k: number) => pad.l + (k / 10) * iw;
  const sy = (v: number) => pad.t + (1 - v) * ih;
  const parts: string[] = [];
  if (j > 0) parts.push(`<rect class="past" x="${sx(0)}" y="${pad.t}" width="${(sx(j) - sx(0)).toFixed(1)}" height="${ih}"/>`);
  for (const t of [0, 0.5, 1]) {
    parts.push(`<line class="grid-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(t)}" y2="${sy(t)}"/>`);
    parts.push(`<text class="tick" x="${pad.l - 6}" y="${sy(t) + 4}" text-anchor="end">%${Math.round(t * 100)}</text>`);
  }
  for (let k = 0; k <= 10; k += 1) parts.push(`<text class="tick" x="${sx(k)}" y="${o.h - 8}" text-anchor="middle">${k}</text>`);
  const path = (pts: [number, number][]) => pts.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
  const u: [number, number][] = [[0, 1]];
  uncond.forEach((v, i) => {
    if (finiteOr(v)) u.push([i + 1, v]);
  });
  parts.push(`<path class="curve-uncond draw" pathLength="1" d="${path(u)}"/>`);
  if (cond) {
    const c: [number, number][] = [[j, 1]];
    cond.forEach((v, i) => {
      if (i + 1 > j && finiteOr(v)) c.push([i + 1, v]);
    });
    parts.push(`<path class="curve-cond draw" pathLength="1" d="${path(c)}"/>`);
    const next = cond[j];
    if (finiteOr(next)) parts.push(`<circle class="curve-dot fade" cx="${sx(j + 1).toFixed(1)}" cy="${sy(next).toFixed(1)}" r="5"/>`);
  }
  return `<svg class="curve" viewBox="0 0 ${o.w} ${o.h}" role="img"><title>${esc(o.tip)}</title>${parts.join("")}</svg>`;
}

export interface CorridorInput {
  /** h = 1..10 kapanışlar, üst limitler ve tavan bayrağı (dosyadan). */
  closes: (number | null)[];
  uppers: (number | null)[];
  ceilings: (number | null)[];
  ipo: number | null;
  /** Getiri modelinin fiyatları (kayıttan): [h, fiyat]. */
  model: [number, number | null][];
  breakDay: number | null;
  xLabels: string[];
  ipoLabel: string;
  breakLabel: string;
  lastLabel: string;
}

/** Fiyat koridoru (Analiz): kapanış çizgisi, tavan/değil işaretleri, üst limit çentiği, arz çizgisi, model beklentisi, kırılma. */
export function corridorChart(c: CorridorInput, o: { w: number; h: number }): string {
  const pad = { l: 40, r: 16, t: 16, b: 28 };
  const iw = o.w - pad.l - pad.r;
  const ih = o.h - pad.t - pad.b;
  const all: number[] = [];
  for (const v of [...c.closes, ...c.uppers, c.ipo, ...c.model.map((m) => m[1])]) if (finiteOr(v)) all.push(v);
  if (!all.length) return "";
  const lo0 = Math.min(...all);
  const hi0 = Math.max(...all);
  const padY = (hi0 - lo0) * 0.08 || 1;
  const lo = lo0 - padY;
  const hi = hi0 + padY;
  const sx = (h: number) => pad.l + (h / 10) * iw;
  const sy = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * ih;
  const parts: string[] = [];
  for (let t = 0; t <= 4; t += 1) {
    const v = lo + ((hi - lo) * t) / 4;
    parts.push(`<line class="grid-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}"/>`);
    parts.push(`<text class="tick" x="${pad.l - 6}" y="${(sy(v) + 4).toFixed(1)}" text-anchor="end">${v.toFixed(0)}</text>`);
  }
  c.xLabels.forEach((l, i) => parts.push(`<text class="tick" x="${sx(i).toFixed(1)}" y="${o.h - 8}" text-anchor="middle">${esc(l)}</text>`));
  if (finiteOr(c.ipo)) {
    parts.push(`<line class="ipo-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(c.ipo).toFixed(1)}" y2="${sy(c.ipo).toFixed(1)}"/>`);
    parts.push(`<text class="tick" x="${o.w - pad.r}" y="${(sy(c.ipo) - 5).toFixed(1)}" text-anchor="end">${esc(c.ipoLabel)}</text>`);
  }
  if (finiteOr(c.breakDay)) {
    parts.push(`<line class="break-line" x1="${sx(c.breakDay).toFixed(1)}" x2="${sx(c.breakDay).toFixed(1)}" y1="${pad.t}" y2="${pad.t + ih}"/>`);
    parts.push(`<text class="break-label" x="${(sx(c.breakDay) + 4).toFixed(1)}" y="${pad.t + 10}">${esc(c.breakLabel)}</text>`);
  }
  const pts: [number, number][] = [];
  if (finiteOr(c.ipo)) pts.push([0, c.ipo]);
  c.closes.forEach((v, i) => {
    if (finiteOr(v)) pts.push([i + 1, v]);
  });
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
  const mpts: [number, number][] = [];
  if (finiteOr(c.ipo)) mpts.push([0, c.ipo]);
  for (const [h, p] of c.model) if (finiteOr(p)) mpts.push([h, p]);
  if (mpts.length > 1) {
    const md = mpts.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
    parts.push(`<path class="model-line draw" pathLength="1" d="${md}"/>`);
    for (const [h, p] of mpts.slice(1)) parts.push(`<rect class="model-pt fade" x="${(sx(h) - 4).toFixed(1)}" y="${(sy(p) - 4).toFixed(1)}" width="8" height="8" transform="rotate(45 ${sx(h).toFixed(1)} ${sy(p).toFixed(1)})"/>`);
  }
  parts.push(`<path class="close-line draw" pathLength="1" d="${d}"/>`);
  c.uppers.forEach((u, i) => {
    if (finiteOr(u)) parts.push(`<line class="upper-tick" x1="${(sx(i + 1) - 7).toFixed(1)}" x2="${(sx(i + 1) + 7).toFixed(1)}" y1="${sy(u).toFixed(1)}" y2="${sy(u).toFixed(1)}"/>`);
  });
  c.closes.forEach((v, i) => {
    if (!finiteOr(v)) return;
    const cls = c.ceilings[i] === 1 ? "pt-up" : c.ceilings[i] === 0 ? "pt-down" : "pt-none";
    parts.push(`<rect class="${cls} fade" x="${(sx(i + 1) - 4).toFixed(1)}" y="${(sy(v) - 4).toFixed(1)}" width="8" height="8" rx="1"/>`);
  });
  let lastI = -1;
  c.closes.forEach((v, i) => {
    if (finiteOr(v)) lastI = i;
  });
  if (lastI >= 0) {
    const v = c.closes[lastI] as number;
    parts.push(`<text class="last-label" x="${sx(lastI + 1).toFixed(1)}" y="${(sy(v) + 18).toFixed(1)}" text-anchor="middle">${esc(c.lastLabel)}</text>`);
  }
  if (finiteOr(c.ipo)) parts.push(`<circle class="ipo-dot" cx="${sx(0)}" cy="${sy(c.ipo).toFixed(1)}" r="3.5"/>`);
  return `<svg class="corridor" viewBox="0 0 ${o.w} ${o.h}" role="img">${parts.join("")}</svg>`;
}

/** Aralık çubuğu (Model performansı): sıfır çizgisi, %95 aralık çizgisi ve ortalama fark noktası; ölçek [min, max]. */
export function intervalBar(diff: number | null, ci: [number, number] | null, o: { w: number; h: number; min: number; max: number; cls: string }): string {
  const sx = (v: number) => ((Math.max(o.min, Math.min(o.max, v)) - o.min) / (o.max - o.min)) * o.w;
  const y = o.h / 2;
  const parts = [`<line class="iv-zero" x1="${sx(0).toFixed(1)}" x2="${sx(0).toFixed(1)}" y1="0" y2="${o.h}"/>`];
  if (ci && finiteOr(ci[0]) && finiteOr(ci[1])) {
    parts.push(`<line class="iv-line growx" x1="${sx(ci[0]).toFixed(1)}" x2="${sx(ci[1]).toFixed(1)}" y1="${y}" y2="${y}"/>`);
  }
  if (finiteOr(diff)) parts.push(`<circle class="iv-dot fade" cx="${sx(diff).toFixed(1)}" cy="${y}" r="5"/>`);
  return `<svg class="iv ${o.cls}" viewBox="0 0 ${o.w} ${o.h}" width="${o.w}" height="${o.h}" role="img">${parts.join("")}</svg>`;
}

/** Aralık ekseni çentikleri (başlık satırı): [değer, x] → piksel. */
export function intervalTicks(values: number[], o: { w: number; min: number; max: number }): [number, string][] {
  return values.map((v) => [v, (((v - o.min) / (o.max - o.min)) * o.w).toFixed(1)]);
}

/** Getiri noktaları (Analiz): ufuk başına tahmin (halka) ve gerçekleşen (dolu), sıfır çizgisi; değerler oran (0.25 = %25). */
export function returnDots(rows: { label: string; forecast: number | null; realized: number | null }[], o: { w: number; h: number }): string {
  const pad = { l: 44, r: 16, t: 14, b: 28 };
  const iw = o.w - pad.l - pad.r;
  const ih = o.h - pad.t - pad.b;
  const all: number[] = [0];
  for (const r of rows) for (const v of [r.forecast, r.realized]) if (finiteOr(v)) all.push(v);
  const lo0 = Math.min(...all);
  const hi0 = Math.max(...all);
  const padY = (hi0 - lo0) * 0.1 || 0.1;
  const lo = lo0 - padY;
  const hi = hi0 + padY;
  const sx = (i: number) => pad.l + ((i + 0.5) / rows.length) * iw;
  const sy = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * ih;
  const parts: string[] = [];
  for (let t = 0; t <= 4; t += 1) {
    const v = lo + ((hi - lo) * t) / 4;
    parts.push(`<line class="grid-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}"/>`);
    parts.push(`<text class="tick" x="${pad.l - 6}" y="${(sy(v) + 4).toFixed(1)}" text-anchor="end">${v < 0 ? "-" : "+"}%${Math.abs(v * 100).toFixed(0)}</text>`);
  }
  parts.push(`<line class="zero-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(0).toFixed(1)}" y2="${sy(0).toFixed(1)}"/>`);
  rows.forEach((r, i) => {
    const x = sx(i).toFixed(1);
    if (finiteOr(r.forecast) && finiteOr(r.realized)) {
      parts.push(`<line class="ret-link" x1="${x}" x2="${x}" y1="${sy(r.forecast).toFixed(1)}" y2="${sy(r.realized).toFixed(1)}"/>`);
    }
    if (finiteOr(r.realized)) parts.push(`<circle class="ret-real fade" cx="${x}" cy="${sy(r.realized).toFixed(1)}" r="5"/>`);
    if (finiteOr(r.forecast)) parts.push(`<circle class="ret-fc fade" cx="${x}" cy="${sy(r.forecast).toFixed(1)}" r="7"/>`);
    parts.push(`<text class="tick" x="${x}" y="${o.h - 8}" text-anchor="middle">${esc(r.label)}</text>`);
  });
  return `<svg class="ret-dots" viewBox="0 0 ${o.w} ${o.h}" role="img">${parts.join("")}</svg>`;
}

// ---------------------------------------------------------------- FAZ9_UI_FIX (yalnız ekleme)

/** İşlem sayısı çubuğu (Analiz, K-FIX-4): Rust'ın verdiği 0–1 oran → piksel yüksekliği; oran yoksa boş svg (çubuk çizilmez). */
export function tradeBar(rel: number | null | undefined, o: { w: number; h: number; title: string }): string {
  if (!finiteOr(rel)) return `<svg class="trade" viewBox="0 0 ${o.w} ${o.h}" width="${o.w}" height="${o.h}" aria-hidden="true"></svg>`;
  const bh = Math.max(1, Math.min(1, Math.max(0, rel)) * (o.h - 2));
  return `<svg class="trade" viewBox="0 0 ${o.w} ${o.h}" width="${o.w}" height="${o.h}" role="img"><title>${esc(o.title)}</title>` +
    `<rect class="trade-bar grow" x="0" y="${(o.h - bh).toFixed(1)}" width="${o.w}" height="${bh.toFixed(1)}" rx="1"/></svg>`;
}

/**
 * Seri hesaplayıcı eğrisi + kuralın koşullu eğrisi (K-FIX-3): `survivalCurve` ile aynı çizim; `rule` (kuralın cond.S_cond,
 * Rust'tan) ince gri kesikli çizgi olarak eklenir. Değerler Rust'tan; burada yalnız piksel.
 */
export function calcCurve(
  uncond: (number | null)[],
  cond: (number | null)[] | null,
  rule: (number | null)[] | null,
  j: number,
  o: { w: number; h: number; tip: string },
): string {
  const pad = { l: 34, r: 12, t: 12, b: 26 };
  const iw = o.w - pad.l - pad.r;
  const ih = o.h - pad.t - pad.b;
  const sx = (k: number) => pad.l + (k / 10) * iw;
  const sy = (v: number) => pad.t + (1 - v) * ih;
  const parts: string[] = [];
  if (j > 0) parts.push(`<rect class="past" x="${sx(0)}" y="${pad.t}" width="${(sx(j) - sx(0)).toFixed(1)}" height="${ih}"/>`);
  for (const t of [0, 0.5, 1]) {
    parts.push(`<line class="grid-line" x1="${pad.l}" x2="${o.w - pad.r}" y1="${sy(t)}" y2="${sy(t)}"/>`);
    parts.push(`<text class="tick" x="${pad.l - 6}" y="${sy(t) + 4}" text-anchor="end">%${Math.round(t * 100)}</text>`);
  }
  for (let k = 0; k <= 10; k += 1) parts.push(`<text class="tick" x="${sx(k)}" y="${o.h - 8}" text-anchor="middle">${k}</text>`);
  const path = (pts: [number, number][]) => pts.map((p, i) => `${i === 0 ? "M" : "L"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
  const condPts = (v: (number | null)[]): [number, number][] => {
    const c: [number, number][] = [[j, 1]];
    v.forEach((x, i) => {
      if (i + 1 > j && finiteOr(x)) c.push([i + 1, x]);
    });
    return c;
  };
  const u: [number, number][] = [[0, 1]];
  uncond.forEach((v, i) => {
    if (finiteOr(v)) u.push([i + 1, v]);
  });
  parts.push(`<path class="curve-uncond draw" pathLength="1" d="${path(u)}"/>`);
  if (rule && rule.some(finiteOr)) parts.push(`<path class="curve-rule" d="${path(condPts(rule))}"/>`);
  if (cond) {
    parts.push(`<path class="curve-cond draw" pathLength="1" d="${path(condPts(cond))}"/>`);
    const next = cond[j];
    if (finiteOr(next)) parts.push(`<circle class="curve-dot fade" cx="${sx(j + 1).toFixed(1)}" cy="${sy(next).toFixed(1)}" r="5"/>`);
  }
  return `<svg class="curve" viewBox="0 0 ${o.w} ${o.h}" role="img"><title>${esc(o.tip)}</title>${parts.join("")}</svg>`;
}
