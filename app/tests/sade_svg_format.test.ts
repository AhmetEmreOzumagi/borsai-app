// @vitest-environment jsdom
// Sade görünüm için render/format.ts ve render/svg.ts eklemeleri (yalnız ekleme; K-UI-2): biçimlendirme ve piksel
// koordinatı. Değer üretmezler: girdi Rust çıktısıdır, çıktı metin/SVG'dir.
import { describe, expect, it } from "vitest";

import { SADE } from "../src/i18n/tr";
import { clockTr, countTr, dateTr, price2, readableCount, readableDate, signed4 } from "../src/render/format";
import { calcCurve, corridorChart, distBars, fillPct, intervalBar, progressPct, returnDots, sparkline, survivalCurve, tradeBar } from "../src/render/svg";
import { dom } from "./helpers";

describe("format.ts eklemeleri", () => {
  it("tarih ve tarih-saat", () => {
    expect(dateTr("2026-09-17")).toBe("17.09.2026");
    expect(dateTr("2026-09-22T15:19:36+03:00")).toBe("22.09.2026 15:19");
    expect(dateTr("2026-10-02T16:17:30Z")).toBe("02.10.2026 16:17 UTC");
    expect(dateTr(null)).toBe("—");
    expect(dateTr("bilinmiyor")).toBe("bilinmiyor");
    expect(readableDate("2026-09-17", SADE.months)).toBe("17 Eylül 2026");
    expect(readableDate("2026-13-01", SADE.months)).toBe("—");
  });

  it("okunur sayı (birimler tr.ts'ten), işaretli 4 ondalık, fiyat 2 ondalık", () => {
    expect(readableCount("312500000", SADE.units)).toBe(`312.5 ${SADE.units.million}`);
    expect(readableCount("87500000", SADE.units)).toBe(`87.5 ${SADE.units.million}`);
    expect(readableCount("2233000000", SADE.units)).toBe(`2.233 ${SADE.units.billion}`);
    expect(readableCount("25000", SADE.units)).toBe(`25 ${SADE.units.thousand}`);
    expect(readableCount("0", SADE.units)).toBe("0");
    expect(readableCount(null, SADE.units)).toBe("—");
    expect(signed4(0.9866556408087268)).toBe("+0.9867");
    expect(signed4(-1.0006869243500793)).toBe("-1.0007");
    expect(price2("25.52")).toBe("25.52");
    expect(price2("16.29")).toBe("16.29");
    expect(clockTr(new Date(2026, 9, 3, 13, 5))).toBe("03.10.2026 13:05");
  });

  // FAZ9_UI_FIX K-FIX-4: işlem sayısı binlik ayırıcıyla (tr-TR); yoksa tire
  it("işlem sayısı binlik ayırıcıyla", () => {
    expect(countTr("17885")).toBe("17.885");
    expect(countTr("28445")).toBe("28.445");
    expect(countTr("241603")).toBe("241.603");
    expect(countTr("3205")).toBe("3.205");
    expect(countTr("999")).toBe("999");
    expect(countTr(null)).toBe("—");
    expect(countTr("")).toBe("—");
    expect(countTr("x")).toBe("—");
  });
});

describe("svg.ts eklemeleri (yalnız koordinat)", () => {
  it("fillPct ve progressPct 0..100'e kırpılır", () => {
    expect(fillPct(0.5)).toBe("50.0%");
    expect(fillPct(2)).toBe("100.0%");
    expect(fillPct(null)).toBe("0%");
    expect(fillPct(1, 0)).toBe("0%");
    expect(progressPct(1, 30)).toBe("3.3%");
    expect(progressPct(45, 30)).toBe("100.0%");
  });

  it("kıvılcım: eksik gün çizgiyi atlamaz, referans çizgisi, NaN yok", () => {
    const s = dom(sparkline([28.06, 30.86, null, 30.56], { w: 88, h: 30, ref: 25.52, cls: "down" }));
    expect(s.querySelector("svg.spark.down path.spark-line")?.getAttribute("d")?.split("L").length).toBe(3);
    expect(s.querySelector("line.spark-ref")).not.toBeNull();
    expect(s.innerHTML).not.toContain("NaN");
    expect(dom(sparkline([], { w: 10, h: 10 })).querySelector("path")).toBeNull();
  });

  it("dağılım çubukları: 11 çubuk, vurgulu ve halkalı indeks", () => {
    const b = dom(distBars([0.1, 0.2, 0.3, 0.4, 0, 0, 0, 0, 0, 0, 0], { w: 300, h: 120, highlight: 3, ring: 2, titles: [] }));
    expect(b.querySelectorAll("rect.bar").length).toBe(11);
    expect(b.querySelectorAll("rect.bar-hi").length).toBe(1);
    expect(b.querySelectorAll("rect.bar-ring").length).toBe(1);
    expect(b.innerHTML).not.toContain("NaN");
  });

  it("hesaplayıcı eğrisi: koşullu eğri j'de 1'den başlar; geçmiş günler gölgeli; yarın noktası", () => {
    const S = [0.8, 0.7, 0.6, 0.4, 0.27, 0.18, 0.12, 0.08, 0.05, 0.036];
    const cond = [null, null, null, 0.67, 0.45, 0.3, 0.2, 0.13, 0.09, 0.06];
    const c = dom(survivalCurve(S, cond, 3, { w: 420, h: 230, tip: "t" }));
    expect(c.querySelector("rect.past")).not.toBeNull();
    const d = c.querySelector("path.curve-cond")?.getAttribute("d") ?? "";
    expect(d.split("L").length).toBe(8);
    expect(c.querySelector("circle.curve-dot")).not.toBeNull();
    const c0 = dom(survivalCurve(S, null, 0, { w: 420, h: 230, tip: "t" }));
    expect(c0.querySelector("rect.past")).toBeNull();
    expect(c0.querySelector("path.curve-cond")).toBeNull();
  });

  it("koridor: kapanış işaretleri tavan/değil, üst limit çentiği, model noktaları, kırılma çizgisi", () => {
    const k = dom(
      corridorChart(
        {
          closes: [28.06, 30.86, 33.94, 30.56, null, null, null, null, null, null],
          uppers: [28.06, 30.86, 33.94, 37.32, null, null, null, null, null, null],
          ceilings: [1, 1, 1, 0, null, null, null, null, null, null],
          ipo: 25.52,
          model: [[1, 27.48], [3, 30.23], [5, 32.03], [10, 32.11]],
          breakDay: 4,
          xLabels: ["arz", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"],
          ipoLabel: "arz 25.52",
          breakLabel: "4. gün kırılma",
          lastLabel: "30.56",
        },
        { w: 760, h: 300 },
      ),
    );
    expect(k.querySelectorAll("rect.pt-up").length).toBe(3);
    expect(k.querySelectorAll("rect.pt-down").length).toBe(1);
    expect(k.querySelectorAll("line.upper-tick").length).toBe(4);
    expect(k.querySelectorAll("rect.model-pt").length).toBe(4);
    expect(k.querySelector("line.break-line")).not.toBeNull();
    expect(k.innerHTML).not.toContain("NaN");
  });

  // FAZ9_UI_FIX: işlem sayısı çubuğu (K-FIX-4) ve kural eğrili hesaplayıcı eğrisi (K-FIX-3) yalnız koordinat
  it("işlem sayısı çubuğu: oran → piksel; 1 tam yükseklik, 0.5 yarım, yoksa çubuk yok", () => {
    const full = dom(tradeBar(1, { w: 36, h: 26, title: "241.603" }));
    expect(full.querySelector("rect.trade-bar")?.getAttribute("height")).toBe("24.0");
    expect(full.querySelector("rect.trade-bar")?.getAttribute("y")).toBe("2.0");
    expect(full.querySelector("title")?.textContent).toBe("241.603");
    expect(dom(tradeBar(0.5, { w: 36, h: 26, title: "" })).querySelector("rect.trade-bar")?.getAttribute("height")).toBe("12.0");
    expect(dom(tradeBar(0, { w: 36, h: 26, title: "" })).querySelector("rect.trade-bar")?.getAttribute("height")).toBe("1.0");
    expect(dom(tradeBar(null, { w: 36, h: 26, title: "" })).querySelector("rect")).toBeNull();
    expect(dom(tradeBar(1, { w: 36, h: 26, title: "" })).innerHTML).not.toContain("NaN");
  });

  it("hesaplayıcı eğrisi + kural eğrisi: kural kesikli gri çizgi j'de 1'den başlar; kural yoksa çizilmez", () => {
    const S = [0.8, 0.7, 0.6, 0.4, 0.27, 0.18, 0.12, 0.08, 0.05, 0.036];
    const cond = [null, null, null, 0.67, 0.45, 0.3, 0.2, 0.13, 0.09, 0.06];
    const rule = [null, null, null, 0.8, 0.62, 0.5, 0.41, 0.32, 0.26, 0.21];
    const c = dom(calcCurve(S, cond, rule, 3, { w: 420, h: 230, tip: "t" }));
    expect(c.querySelector("rect.past")).not.toBeNull();
    expect(c.querySelector("path.curve-cond")?.getAttribute("d")?.split("L").length).toBe(8);
    expect(c.querySelector("path.curve-rule")?.getAttribute("d")?.split("L").length).toBe(8);
    expect(c.querySelector("path.curve-rule")?.getAttribute("d")?.startsWith(c.querySelector("path.curve-cond")?.getAttribute("d")?.split("L")[0] ?? "x")).toBe(true);
    expect(c.querySelector("circle.curve-dot")).not.toBeNull();
    expect(c.innerHTML).not.toContain("NaN");
    const none = dom(calcCurve(S, cond, null, 3, { w: 420, h: 230, tip: "t" }));
    expect(none.querySelector("path.curve-rule")).toBeNull();
    expect(dom(calcCurve(S, cond, [], 3, { w: 420, h: 230, tip: "t" })).querySelector("path.curve-rule")).toBeNull();
    expect(dom(calcCurve(S, null, null, 0, { w: 420, h: 230, tip: "t" })).querySelector("path.curve-cond")).toBeNull();
  });

  it("aralık çubuğu ve getiri noktaları", () => {
    const iv = dom(intervalBar(-0.05, [-0.075, -0.022], { w: 220, h: 26, min: -0.25, max: 0.05, cls: "iv-pass" }));
    expect(iv.querySelector("svg.iv.iv-pass line.iv-line")).not.toBeNull();
    expect(iv.querySelector("circle.iv-dot")).not.toBeNull();
    expect(dom(intervalBar(null, null, { w: 220, h: 26, min: -1, max: 1, cls: "x" })).querySelector("circle")).toBeNull();
    const r = dom(returnDots([{ label: "D1", forecast: 0.077, realized: 0.0995 }, { label: "D5", forecast: 0.255, realized: null }], { w: 460, h: 220 }));
    expect(r.querySelectorAll("circle.ret-fc").length).toBe(2);
    expect(r.querySelectorAll("circle.ret-real").length).toBe(1);
    expect(r.querySelectorAll("line.ret-link").length).toBe(1);
  });
});
