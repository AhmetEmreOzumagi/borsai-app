// @vitest-environment jsdom
// Sade görünüm (FAZ9_APP_UI) saf render testleri. Fixture'lar Rust komutlarının GERÇEK repo dosyalarıyla ürettiği
// çıktıdır (`src-tauri/tests/sade.rs`; BORSAI_UPDATE_UI_FIXTURES=1). Beklenen sayılar görev dosyasındakilerdir
// (biçim SPEC_APP §4: olasılık %0 ondalık, getiri %1 ondalık, fiyat 2 ondalık, gün 1 ondalık).
import { describe, expect, it } from "vitest";

import { COND, DISCLAIMER, ERROR_TEXT, SADE, TR, VERDICT, VERDICT_PLAIN } from "../src/i18n/tr";
import { pct0 } from "../src/render/format";
import { renderAnaliz, renderAnalizPick, type AnalizVM } from "../src/sade/render/analiz";
import { renderAyarlar } from "../src/sade/render/ayarlar";
import { renderCalc } from "../src/sade/render/calc";
import { closedScreen, gated, notPrimaryLabel, renderFooter, verdictCell } from "../src/sade/render/common";
import { readback, renderGiris } from "../src/sade/render/giris";
import { renderKayitlarim } from "../src/sade/render/kayitlarim";
import { eventText, renderMonitor } from "../src/sade/render/monitor";
import { renderPerf } from "../src/sade/render/perf";
import { activeTab, bandOf, legacyScreenOf, renderTopBar, type TopBarVM } from "../src/sade/render/shell";
import { renderSicil } from "../src/sade/render/sicil";
import { renderSonuc, type SonucVM } from "../src/sade/render/sonuc";
import { sadeScreenOf } from "../src/sade/app";
import { dataSource } from "../src/sade/state";
import type { ArzView, BreakView, GateEntry, HeadlineGate, MonitorView, PerfView } from "../src/sade/types";
import type { ResultsState, FormState } from "../src/state";
import type { CeilingDisplay, CeilingSummary, ConfigView, ModelRun, RecordCeiling, RegistryView, ScenarioSummary, SnapshotInfo, StreakView } from "../src/types";
import { dom, fx } from "./helpers";

const MONITOR = fx<MonitorView>("sade_monitor.json");
const GATE = fx<HeadlineGate>("sade_gate.json");
const PERF = fx<PerfView>("sade_perf.json");
const ARZ = fx<ArzView>("sade_arz_netgl.json");
const BREAK = fx<BreakView>("sade_break_netgl.json");
const BREAK_TKNKA = fx<BreakView>("sade_break_tknka.json");
const STREAK = fx<StreakView>("sade_streak_netgl.json");
const RUNS = fx<ModelRun[]>("sade_runs_netgl.json");
const C0 = fx<CeilingDisplay>("sade_ceiling_netgl_j0.json");
const C3 = fx<CeilingDisplay>("sade_ceiling_netgl_j3.json");
const S0 = fx<CeilingSummary>("sade_summary_netgl_j0.json");
const RS3 = fx<CeilingSummary>("sade_record_summary_netgl_j3.json");
const RC3 = fx<RecordCeiling>("sade_record_ceiling_netgl_j3.json");
const RC0 = fx<RecordCeiling>("sade_record_ceiling_netgl_j0.json");
const RC6 = fx<RecordCeiling>("sade_record_ceiling_netgl_j6.json");
/** Takipteki arzlar (monitör satırlarından): Analiz listesi ve değiştirici (K-FIX-1). */
const PICK = MONITOR.rows.map((r) => ({ ticker: r.ticker, company: r.company, first_trading_date: r.first_trading_date }));

const text = (e: Element | null | undefined) => (e?.textContent ?? "").replace(/\s+/g, " ").trim();

/** Kapının bir girdisini değiştirilmiş kopya (öne çıkma kararı yalnız Rust'tan; burada render davranışı sınanır). */
function gateWith(model: string, output: string, h: string | null, featured: boolean): HeadlineGate {
  return {
    ...GATE,
    entries: GATE.entries.map((e) => (e.model_id === model && e.output === output && e.horizon_or_k === h ? { ...e, featured } : e)),
  };
}

/** Panelde her VERDICT.pass bir hüküm hücresinden gelir (U19'un sade karşılığı). */
function passOnlyInVerdictCells(root: HTMLElement): void {
  const all = (root.textContent ?? "").split(VERDICT.pass).length - 1;
  const inCells = [...root.querySelectorAll<HTMLElement>(".verdict")].filter((v) => v.dataset.verdict === VERDICT.pass).length;
  expect(all).toBe(inCells);
}

function noForbiddenWords(root: HTMLElement): void {
  const t = (root.textContent ?? "").toLocaleLowerCase("tr");
  for (const w of ["kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal"]) expect(t, w).not.toContain(w);
  expect(/doğruluk %\d/.test(t)).toBe(false);
}

// ---------------------------------------------------------------- kabuk

describe("sade kabuk (K-UI-1, K-UI-12)", () => {
  const vm = (screen: TopBarVM["screen"], extra: Partial<TopBarVM> = {}): TopBarVM => ({
    screen,
    registryMode: "list",
    ticker: null,
    repoMode: true,
    repoRoot: "/r",
    dataDate: "2026-09-30",
    clock: "03.10.2026 13:00",
    searchMsg: null,
    ...extra,
  });

  it("mod göstergesi eski bantla aynı kaynaktan (bandFor): senaryo, resmi kayıt, doğruluk, nötr", () => {
    expect(bandOf(vm("giris")).head).toBe(TR.modeScenario);
    expect(bandOf(vm("sonuc")).cls).toBe("mode-scenario");
    expect(bandOf(vm("kayitlarim")).head).toBe(TR.modeScenario);
    expect(bandOf(vm("sicil")).head).toBe(TR.modeOfficial);
    expect(bandOf(vm("analiz")).note).toBe(TR.modeOfficialList);
    expect(bandOf(vm("sihirbaz", { registryMode: "wizard" })).note).toBe(TR.modeOfficialWizard);
    expect(bandOf(vm("perf")).head).toBe(TR.modeAccuracy);
    expect(bandOf(vm("monitor")).head).toBe("");
    const top = dom(renderTopBar(vm("giris")));
    expect(top.querySelector(".s-mode")?.textContent).toBe(TR.modeScenario);
    expect(top.querySelector(".s-mode")?.getAttribute("title")).toContain(TR.modeScenarioNote);
    expect(dom(renderTopBar(vm("monitor"))).querySelector(".s-mode")).toBeNull();
  });

  it("sekmeler, veri tarihi, Yeni arz gir, Ayarlar; bağımsız modda gösterge", () => {
    const top = dom(renderTopBar(vm("sihirbaz", { registryMode: "wizard" })));
    expect([...top.querySelectorAll(".s-nav button")].map((b) => b.textContent)).toEqual(SADE_NAV_LABELS);
    expect(top.querySelector(".s-nav button.active")?.getAttribute("data-go")).toBe("sicil");
    expect(text(top)).toContain(SADE.dataDate("30.09.2026"));
    expect(top.querySelector('[data-go="giris"]')?.textContent).toBe(SADE.newIpo);
    expect(top.querySelector('[data-go="ayarlar"]')).not.toBeNull();
    expect(top.querySelector(".s-standalone")).toBeNull();
    expect(dom(renderTopBar(vm("monitor", { repoMode: false }))).querySelector(".s-standalone")?.getAttribute("title")).toBe(TR.standaloneMode);
    expect(activeTab("giris")).toBeNull();
    expect(activeTab("analiz")).toBe("analiz");
  });

  it("eski ekran ↔ sade ekran eşlemesi (ayrıntılı görünüm bağlantıları ve sihirbaz gezinmesi)", () => {
    expect(legacyScreenOf("giris")).toBe("inputs");
    expect(legacyScreenOf("sonuc")).toBe("results");
    expect(legacyScreenOf("perf")).toBe("accuracy");
    expect(legacyScreenOf("kayitlarim")).toBe("scenarios");
    expect(sadeScreenOf("inputs")).toBe("giris");
    expect(sadeScreenOf("results")).toBe("sonuc");
    expect(sadeScreenOf("scenarios")).toBe("kayitlarim");
    expect(sadeScreenOf("about")).toBe("ayarlar");
    expect(sadeScreenOf("accuracy")).toBe("perf");
  });

  it("her ekranın altında DISCLAIMER ve sürüm", () => {
    const f = dom(renderFooter("0.1.0"));
    expect(f.querySelector(".s-disclaimer")?.textContent).toBe(DISCLAIMER);
    expect(text(f)).toContain(SADE.version("0.1.0"));
  });
});

const SADE_NAV_LABELS = ["Monitör", "Analiz", "Model performansı", "Sicil", "Kayıtlarım"];

/** FAZ9_WINDOWS K-TXT-1: öne çıkmayan ufkun "Geçmiş test" hücresi "· birincil değil"; satırda hüküm sözcüğü ve "≈ fark net değil" yok. */
function notPrimaryRows(r: HTMLElement, horizons: string[]): void {
  for (const h of horizons) {
    const row = r.querySelector(`.returns tr[data-h="${h}"]`);
    expect(text(row?.querySelector(".not-primary")), h).toBe(`${SADE.notPrimaryMark} ${SADE.notPrimaryText}`);
    expect(row?.querySelector(".verdict, .approx-label"), h).toBeNull();
    for (const v of [...Object.values(VERDICT), SADE.approxText]) expect(text(row), `${h}: ${v}`).not.toContain(v);
  }
}

// ---------------------------------------------------------------- ortak: kapı ve hüküm

describe("ana ekran kapısı ve hüküm hücresi (K-UI-4, K-UI-5, U19)", () => {
  it("öne çıkan altın; öne çıkmayan aynı değer + ≈", () => {
    const e = GATE.entries.find((x) => x.model_id === "ceiling_hazard_v0") as GateEntry;
    expect(e.featured).toBe(true);
    expect(dom(gated(e, "3.3")).querySelector(".gold")?.textContent).toBe("3.3");
    const d10 = GATE.entries.find((x) => x.model_id === "v1_5_h99" && x.output === "p_up" && x.horizon_or_k === "D10") as GateEntry;
    expect(d10.featured).toBe(false);
    const g = dom(gated(d10, "%60"));
    expect(g.querySelector(".gold")).toBeNull();
    expect(text(g)).toBe(`%60 ${SADE.approxMark}`);
    expect(text(dom(notPrimaryLabel()))).toBe(`${SADE.notPrimaryMark} ${SADE.notPrimaryText}`);
  });

  it("hüküm hücresi dosyadaki verdict aynen; sade açıklama ayrı dize", () => {
    const c = dom(verdictCell(VERDICT.pass));
    expect(c.querySelector(".verdict")?.getAttribute("data-verdict")).toBe(VERDICT.pass);
    expect(text(c)).toBe(`✓ ${VERDICT.pass}`);
    expect(VERDICT_PLAIN[VERDICT.pass]).not.toContain(VERDICT.pass);
    expect(text(dom(verdictCell(VERDICT.undecided)))).toBe(`≈ ${VERDICT.undecided}`);
  });

  it("bugünkü dosyalarla kapı: ceiling ve D5 getirisi ve kırılma F1 öne çıkar; D10 p_up ve post_d1 çıkmaz", () => {
    const f = (m: string, o: string, h: string | null) => GATE.entries.find((x) => x.model_id === m && x.output === o && x.horizon_or_k === h)?.featured;
    expect(f("ceiling_hazard_v0", "S", null)).toBe(true);
    expect(f("v1_5_h99", "return", "D5")).toBe(true);
    expect(f("v1_5_h99", "p_up", "D10")).toBe(false);
    expect(f("post_d1_hazard_v0", "S_cond", null)).toBe(false);
    expect(f("break_floor_v0", "p_floor", "F1")).toBe(true);
    expect(GATE.entries.filter((e) => e.featured).length).toBe(3);
  });
});

// ---------------------------------------------------------------- Monitör

describe("Monitör (monitor_view; görev beklenen sayıları)", () => {
  const root = dom(renderMonitor({ view: MONITOR, gate: GATE, perf: PERF, selected: null, filter: "ALL" }));
  const row = (t: string) => root.querySelector<HTMLElement>(`tr[data-ticker="${t}"]`);
  const col = (t: string, c: string) => text(row(t)?.querySelector(`[data-col="${c}"]`));

  it("7 arz D1 azalan; seride 0; D10'da arz altında 2 / 7; tabanda kırılma 3 / 7; üretimde 4", () => {
    expect([...root.querySelectorAll<HTMLElement>("tr[data-ticker]")].map((r) => r.dataset.ticker)).toEqual(["NETGL", "BKRGY", "INTET", "KPEKS", "TKNKA", "VEYAS", "CITAS"]);
    expect(text(root.querySelector(".strip-ipos .s-strip-value"))).toBe("7");
    expect(text(root.querySelector(".strip-streak .s-strip-value"))).toBe("0");
    expect(text(root.querySelector(".strip-below .s-strip-value"))).toBe("2 / 7");
    expect(text(root.querySelector(".strip-below .s-strip-sub"))).toBe("NETGL, BKRGY");
    expect(text(root.querySelector(".strip-floor .s-strip-value"))).toBe("3 / 7");
    expect(text(root.querySelector(".strip-models .s-strip-value"))).toBe("4");
    expect(text(root.querySelector(".strip-models .s-strip-sub"))).toBe("kendi sorusunda ölçülen"); // K-TXT-2: perf ekranıyla aynı
    expect(SADE.monitor.stripModelsSub).toBe(SADE.perf.stripProdSub);
    expect(text(root.querySelector(".monitor-summary"))).toContain(SADE.monitor.summary(7, 0));
  });

  it("NETGL satırı: arza göre −%36.2, seri 3, beklenen 3.3 / 3 ve 5+ gün %27 (altın), 4. gün taban, ertesi gün taban %50; kayıt: geç kayıt, getiri canlı", () => {
    expect(col("NETGL", "vs-ipo")).toBe("-%36.2");
    expect(col("NETGL", "streak")).toBe("3");
    expect(col("NETGL", "expected")).toBe("3.3 / 3");
    expect(row("NETGL")?.querySelector('[data-col="expected"] .gold')).not.toBeNull();
    expect(col("NETGL", "ge5")).toBe("%27");
    expect(col("NETGL", "break")).toBe(SADE.monitor.breakFloor(4));
    expect(text(row("NETGL")?.querySelector('[data-col="next-floor"] .gold'))).toBe("%50");
    expect(row("NETGL")?.querySelector('[data-model="ceiling_hazard_v0"]')?.textContent).toBe(SADE.classText.LATE_RECORD);
    const ret = row("NETGL")?.querySelector<HTMLElement>('[data-model="v1_5_h99"]');
    expect(ret?.textContent).toBe(SADE.monitor.recordReturn(SADE.classText.LIVE));
    expect(ret?.classList.contains("chip-live")).toBe(true);
    // BKRGY: getiri sınıfı tavanla aynı → tek satır
    expect(row("BKRGY")?.querySelector('[data-model="v1_5_h99"]')).toBeNull();
  });

  it("ertesi gün taban F1 tablosu, TKNKA yapısal sıfır rozeti, VEYAS girdi eksik", () => {
    const expected: Record<string, number> = { BKRGY: 0.5433, KPEKS: 0.5389, NETGL: 0.4991, INTET: 0.1418, CITAS: 0.1383, TKNKA: 0.1382, VEYAS: 0.1376 };
    for (const [t, p] of Object.entries(expected)) expect(text(row(t)?.querySelector('[data-col="next-floor"] .gold')), t).toBe(pct0(p));
    expect(text(row("TKNKA")?.querySelector(".chip-impossible"))).toBe(SADE.monitor.impossibleBadge);
    expect(root.querySelectorAll(".chip-impossible").length).toBe(1);
    expect(text(row("VEYAS"))).toContain(SADE.refusedShort("F3_MISSING"));
    expect(col("BKRGY", "break")).toBe(SADE.monitor.breakFloor(1));
    expect(col("KPEKS", "break")).toBe(SADE.monitor.breakFloor(6));
    expect(col("INTET", "break")).toBe(SADE.monitor.breakAbove(5));
  });

  it("rejim şeridi (FON_KRIZI_2026), seçili arz paneli, üretimdeki modeller, olay akışı", () => {
    expect(root.querySelector('.s-stripe[data-regime="FON_KRIZI_2026"]')).not.toBeNull();
    expect(text(root.querySelector(".s-stripe"))).toContain(SADE.regimeStripe("16.09.2026"));
    const sel = root.querySelector(".selected-ipo");
    expect(sel?.getAttribute("data-ticker")).toBe("NETGL");
    expect(text(sel)).toContain("16.29");
    expect(text(sel)).toContain(SADE.monitor.selStreakVal("3", "3"));
    expect(text(sel)).toContain("+%25.5");
    const prod = [...root.querySelectorAll<HTMLElement>(".production tr[data-model]")];
    expect(prod.map((r) => r.dataset.model)).toEqual(["ceiling_hazard_v0", "v1_5_h99", "post_d1_hazard_v0", "break_floor_v0"]);
    expect(prod[0].querySelector(".verdict")?.getAttribute("data-verdict")).toBe(VERDICT.pass);
    expect(text(prod[1].querySelector("td:last-child"))).toBe("1");
    expect(prod[3].querySelector(".promotion-label")?.getAttribute("data-promoted")).toBe("1");
    const ev = MONITOR.events;
    expect(text(root.querySelector(".events .f-text"))).toBe(eventText(ev[0]));
    expect(ev.find((e) => e.kind === "MACHINE")?.tickers.length).toBe(7);
    expect(text(root.querySelector(".events"))).toContain(SADE.event.MACHINE(7, SADE.classText.RETRO));
    passOnlyInVerdictCells(root);
    noForbiddenWords(root);
  });

  it("öne çıkmayan tavan modeli altın değil, ≈ işaretli (kapı Rust'tan)", () => {
    const r = dom(renderMonitor({ view: MONITOR, gate: gateWith("ceiling_hazard_v0", "S", null, false), perf: PERF, selected: null, filter: "ALL" }));
    const cell = r.querySelector('tr[data-ticker="NETGL"] [data-col="expected"]');
    expect(cell?.querySelector(".gold")).toBeNull();
    expect(text(cell)).toContain(SADE.approxMark);
  });

  it("süzgeç 'Seride' boş liste; seçim paneli seçilen arzı gösterir", () => {
    const r = dom(renderMonitor({ view: MONITOR, gate: GATE, perf: PERF, selected: "TKNKA", filter: "STREAK" }));
    expect(r.querySelectorAll("tr[data-ticker]").length).toBe(0);
    expect(r.querySelector(".selected-ipo")?.getAttribute("data-ticker")).toBe("TKNKA");
  });
});

// ---------------------------------------------------------------- hesaplayıcı

describe("seri hesaplayıcı (K-UI-8; NETGL beklenen sayılar)", () => {
  const row = (d: CeilingDisplay) => d.rows.find((r) => r.model_id === "ceiling_hazard_v0") ?? null;
  const g = GATE.entries.find((x) => x.model_id === "ceiling_hazard_v0") ?? null;
  const reading = (root: HTMLElement, k: string) => text(root.querySelector(`[data-reading="${k}"] .s-reading-value`));

  it("senaryo j = 0: yarın tavan %82 (S_1 = 0.8176), bozulma %18; geçmiş arzlarda %82 (99 arzdan 81)", () => {
    const r = dom(renderCalc({ mode: "SCENARIO", j: 0, row: row(C0), modelId: "ceiling_hazard_v0", gate: g, streak: null, calc: C0.calc ?? null, postD1Html: "" }));
    expect(reading(r, "tomorrow")).toBe("%82");
    expect(text(r.querySelector('[data-reading="tomorrow"] .s-history .s-reading-value'))).toBe("%82");
    expect(text(r.querySelector(".s-history .history-count"))).toBe(SADE.calc.historyCount(0, "99", "81", 1));
    expect(text(r.querySelector('[data-reading="tomorrow"] .s-reading-sub'))).toBe(SADE.calc.breakProb("%18"));
    expect(text(r.querySelector(".calc-lead"))).toBe(SADE.calc.day0("%82"));
    expect(r.querySelector('[data-action="calc-j"].active')?.getAttribute("data-j")).toBe("0");
    expect(r.querySelectorAll('[data-action="calc-j"]').length).toBe(10);
  });

  it("senaryo j = 3: yarın bozulma %33, beklenen kalan 1.9, koşullu medyan 4, P(≥5 | ≥3) %45, P(10 | ≥3) %6; şerit 3 tavan + yarın; geçmiş %80", () => {
    const r = dom(renderCalc({ mode: "SCENARIO", j: 3, row: row(C3), modelId: "ceiling_hazard_v0", gate: g, streak: null, calc: C3.calc ?? null, postD1Html: "" }));
    expect(reading(r, "tomorrow")).toBe("%67");
    expect(text(r.querySelector(".s-history .s-reading-value"))).toBe("%80");
    expect(text(r.querySelector(".s-history .history-count"))).toBe(SADE.calc.historyCount(3, "66", "53", 4));
    expect(r.querySelector(".s-history .gold")).toBeNull();
    expect(r.querySelector("svg.curve path.curve-rule")).not.toBeNull();
    expect(text(r.querySelector(".lg-rule"))).toBe(SADE.calc.legendRule);
    expect(text(r.querySelector('[data-reading="tomorrow"] .s-reading-sub'))).toBe(SADE.calc.breakProb("%33"));
    expect(reading(r, "remaining")).toBe("1.9");
    expect(text(r.querySelector('[data-reading="remaining"] .s-reading-sub'))).toBe(SADE.calc.condMedian("4"));
    expect(reading(r, "ge5")).toBe("%45");
    expect(reading(r, "all10")).toBe("%6");
    expect([...r.querySelectorAll(".day-strip .d-cell")].map((c) => c.className.replace("d-cell", "").trim())).toEqual(["ceil", "ceil", "ceil", "tomorrow", "", "", "", "", "", ""]);
    expect(r.querySelector("svg.curve path.curve-cond")).not.toBeNull();
    expect(r.querySelector("svg.curve path.curve-uncond")).not.toBeNull();
    expect(r.querySelector(".gold")).not.toBeNull();
  });

  it("resmi görünüm: gözlenen j = 3, seri D4'te bozuldu (L = 3); j ≠ gözlenen → 'Gözlenene dön'", () => {
    const disp = RC3.display;
    const r3 = dom(renderCalc({ mode: "OFFICIAL", j: 3, row: row(disp), modelId: "ceiling_hazard_v0", gate: g, streak: STREAK, calc: disp.calc ?? null, postD1Html: "" }));
    expect(r3.querySelector(".s-observed")?.getAttribute("data-observed")).toBe("3");
    expect(text(r3.querySelector(".s-observed"))).toContain(COND.broken(4, 3));
    expect(r3.querySelector('[data-action="calc-observed"]')).toBeNull();
    expect(r3.querySelector('[data-action="calc-j"].observed')?.getAttribute("data-j")).toBe("3");
    expect(reading(r3, "tomorrow")).toBe("%67");
    const r0 = dom(renderCalc({ mode: "OFFICIAL", j: 0, row: row(RC0.display), modelId: "ceiling_hazard_v0", gate: g, streak: STREAK, calc: RC0.display.calc ?? null, postD1Html: "" }));
    expect(r0.querySelector('[data-action="calc-observed"]')?.textContent).toBe(SADE.calc.backToObserved);
    expect(reading(r0, "tomorrow")).toBe("%82");
  });

  it("tanımsız j (cond null) → not; değer yok", () => {
    const base = row(C3);
    const r = dom(renderCalc({ mode: "SCENARIO", j: 3, row: base ? { ...base, cond: null } : null, modelId: "m", gate: g, streak: null, calc: null, postD1Html: "" }));
    expect(text(r.querySelector(".calc-undefined"))).toBe(SADE.calc.undefinedAll);
    expect(r.querySelectorAll("[data-reading]").length).toBe(0);
  });

  // FAZ9_UI_FIX K-FIX-3: model 3. günden sonra sabit (gün grupları), geçmiş arzlarda gün gün değişir; not model dosyasından
  it("j = 6: model yine %67, geçmiş arzlarda %82 (27 arzdan 22 değil: 33 arzdan 27); gün grupları notu dosyadan", () => {
    const r = dom(renderCalc({ mode: "OFFICIAL", j: 6, row: row(RC6.display), modelId: "ceiling_hazard_v0", gate: g, streak: STREAK, calc: RC6.display.calc ?? null, postD1Html: "" }));
    expect(reading(r, "tomorrow")).toBe("%67");
    expect(text(r.querySelector(".s-history .s-reading-value"))).toBe("%82");
    expect(text(r.querySelector(".s-history .history-count"))).toBe(SADE.calc.historyCount(6, "33", "27", 7));
    expect(text(r.querySelector(".s-history .s-reading-label"))).toContain(SADE.calc.historyLabel);
    expect(text(r.querySelector(".s-history .s-reading-label"))).toContain(SADE.calc.historySub);
    const note = text(r.querySelector(".calc-groups"));
    expect(note).toBe(SADE.calc.groupsNote("üç", "1. gün · 2–3. gün · 4–10. gün", 3));
    expect(note).toContain("4–10");
    expect(r.querySelector(".calc-groups")?.getAttribute("data-model")).toBe("ceiling_hazard_v0");
    // gruplar fixture'dan (model dosyası), metinde sabit değil
    expect(RC6.display.calc?.day_groups.find((x) => x.model_id === "ceiling_hazard_v0")?.groups).toEqual([[1], [2, 3], [4, 5, 6, 7, 8, 9, 10]]);
  });

  it("ek yoksa ya da kural satırı yoksa geçmiş satırı ve not çizilmez; sayım Rust vermediyse yalnız oran", () => {
    const base = row(C3);
    const none = dom(renderCalc({ mode: "SCENARIO", j: 3, row: base, modelId: "ceiling_hazard_v0", gate: g, streak: null, calc: null, postD1Html: "" }));
    expect(none.querySelector(".s-history")).toBeNull();
    expect(none.querySelector(".calc-groups")).toBeNull();
    expect(none.querySelector("svg.curve path.curve-rule")).toBeNull();
    const calc = C3.calc as NonNullable<typeof C3.calc>;
    const noRule = dom(renderCalc({ mode: "SCENARIO", j: 3, row: base, modelId: "ceiling_hazard_v0", gate: g, streak: null, calc: { ...calc, history: { ...calc.history, in_rows: false } }, postD1Html: "" }));
    expect(noRule.querySelector(".s-history")).toBeNull();
    expect(noRule.querySelector(".calc-groups")).not.toBeNull();
    const noCount = dom(renderCalc({ mode: "SCENARIO", j: 3, row: base, modelId: "ceiling_hazard_v0", gate: g, streak: null, calc: { ...calc, history: { ...calc.history, n_at_j: null, n_next: null } }, postD1Html: "" }));
    expect(text(noCount.querySelector(".s-history .s-reading-value"))).toBe("%80");
    expect(noCount.querySelector(".history-count")).toBeNull();
    // gün grubu taşımayan model: not yok
    const other = dom(renderCalc({ mode: "SCENARIO", j: 3, row: base, modelId: "base_km_expanding", gate: g, streak: null, calc, postD1Html: "" }));
    expect(other.querySelector(".calc-groups")).toBeNull();
  });
});

// ---------------------------------------------------------------- Tahmin sonucu

function results(): ResultsState {
  return {
    runs: RUNS,
    inputs: { ipo_price_tl: "25.52" },
    inputDates: { first_trading_date: "2026-09-17" },
    stage: "POST_BOOKBUILD_PRE_LISTING",
    tickerLabel: "NETGL",
    f6: { value: "-0.0924", refusal: null, origin: "REPO_PYTHON", S0_date: null, S20_date: null, xu100_sha256: null, ref_date: null },
    source: "FORM",
    scenario: null,
    savedId: null,
  };
}

describe("Tahmin sonucu (senaryo)", () => {
  const vm = (extra: Partial<SonucVM> = {}): SonucVM => ({
    results: results(),
    summary: S0,
    disp0: C0,
    dispJ: C3,
    j: 3,
    gate: GATE,
    perf: PERF,
    hints: null,
    integrityOk: true,
    repoMode: true,
    savedId: null,
    errorHtml: "",
    ...extra,
  });

  it("manşet yalnız öne çıkan çıktılardan: beklenen 3.3 gün, 3 gün tavan ve 4. gün bozulma, D5 +%25.5", () => {
    const r = dom(renderSonuc(vm()));
    expect(text(r.querySelector(".sonuc-headline"))).toBe(SADE.sonuc.headCeiling("3.3", 3, 4) + SADE.sonuc.headReturn("+%25.5"));
    expect(text(r.querySelector("h1"))).toBe(SADE.sonuc.title("NETGL"));
    const noD5 = dom(renderSonuc(vm({ gate: gateWith("v1_5_h99", "return", "D5", false) })));
    expect(text(noD5.querySelector(".sonuc-headline"))).toBe(SADE.sonuc.headCeiling("3.3", 3, 4));
    const none = dom(renderSonuc(vm({ gate: gateWith("ceiling_hazard_v0", "S", null, false) })));
    expect(text(none.querySelector(".sonuc-headline"))).toBe(SADE.sonuc.headReturn("+%25.5").trim());
  });

  it("Kaç gün tavan: 11 çubuk (en olası l = 3 vurgulu), model ve basit kural satırları, geçmiş test iki değer + dosyadaki hüküm", () => {
    const r = dom(renderSonuc(vm()));
    const kac = r.querySelector(".kac");
    expect(kac?.querySelectorAll("svg.dist rect.bar").length).toBe(11);
    expect(kac?.querySelector("svg.dist rect.bar-hi + text, svg.dist text.tick-hi")?.textContent).toBe("3");
    expect(text(kac?.querySelector('tr[data-row="ceiling_hazard_v0"]'))).toContain("3.3");
    expect(text(kac?.querySelector('tr[data-row="base_km_last10"]'))).toContain("2.2");
    const bt = text(kac?.querySelector(".backtest-line"));
    expect(bt).toContain("0.1503");
    expect(bt).toContain("0.1999");
    expect(bt).not.toContain("%25");
    expect(kac?.querySelector(".verdict")?.getAttribute("data-verdict")).toBe(VERDICT.pass);
  });

  it("getiri tablosu: D5 öne çıkan (birincil + dosyadaki hüküm), öbür ufuklar · birincil değil (hüküm sözcüğü yok); p_up hep ≈", () => {
    const r = dom(renderSonuc(vm()));
    const d5 = r.querySelector('.returns tr[data-h="D5"]');
    expect(d5?.querySelector("td.num .gold")?.textContent).toBe("+%25.5");
    expect(d5?.querySelector(".verdict")?.getAttribute("data-verdict")).toBe(VERDICT.pass);
    notPrimaryRows(r, ["D1", "D3", "D10"]);
    expect(text(r.querySelector('.returns tr[data-h="D10"]'))).toContain("%60");
    expect(text(r.querySelector('.returns tr[data-h="D5"]'))).toContain("32.03");
    passOnlyInVerdictCells(r);
    noForbiddenWords(r);
  });

  it("hesaplayıcı senaryoda; D1 sonrası notu; rejim uyarısı; kişisel kayıt; DISCLAIMER kabukta", () => {
    const r = dom(renderSonuc(vm()));
    expect(r.querySelector('.calc[data-mode="SCENARIO"][data-j="3"]')).not.toBeNull();
    expect(text(r.querySelector(".post-d1-line"))).toBe(SADE.calc.postD1Scenario);
    expect(r.querySelector('[data-action="save"]')).not.toBeNull();
    expect(r.querySelector('[data-detailed="results"]')).not.toBeNull();
    const standalone = dom(renderSonuc(vm({ repoMode: false })));
    expect(standalone.querySelector('[data-action="official"]')).toBeNull();
  });

  it("sonuç yoksa boş durum; bütünlük bozuksa bant", () => {
    expect(text(dom(renderSonuc(vm({ results: null }))))).toContain(SADE.sonuc.empty);
    expect(dom(renderSonuc(vm({ integrityOk: false }))).querySelector(".band-error")).not.toBeNull();
  });
});

// ---------------------------------------------------------------- Analiz

describe("Analiz (arz_view, break_view, record_summary, record_ceiling)", () => {
  const vm = (extra: Partial<AnalizVM> = {}): AnalizVM => ({
    arz: ARZ,
    brk: BREAK,
    streak: STREAK,
    summary: RS3,
    ceiling: RC3,
    postD1: null,
    j: 3,
    gate: GATE,
    tickers: PICK,
    ...extra,
  });
  const r = dom(renderAnaliz(vm()));

  // FAZ9_UI_FIX K-FIX-1: yol, "Tüm arzlar", değiştirici (en yeni ilk işlem günü üstte); K-FIX-4: işlem sayısı çubukları
  it("yol 'Analiz › NETGL', 'Tüm arzlar' ve arz değiştirici (7 arz, en yeni üstte, NETGL seçili)", () => {
    const crumb = r.querySelector(".arz-crumb");
    expect(text(crumb)).toContain(`${SADE.analiz.title} › NETGL`);
    expect(crumb?.querySelector('.s-link[data-go="analiz"]')?.textContent).toBe(SADE.analiz.title);
    expect(crumb?.querySelector('[data-role="all-ipos"]')?.getAttribute("data-go")).toBe("analiz");
    expect(crumb?.querySelector('[data-role="all-ipos"]')?.textContent).toBe(SADE.analiz.allIpos);
    const opts = [...(crumb?.querySelectorAll<HTMLOptionElement>("[data-role=arz-switch] option") ?? [])];
    expect(opts.map((o) => o.value)).toEqual(["NETGL", "BKRGY", "INTET", "KPEKS", "TKNKA", "VEYAS", "CITAS"]);
    expect(opts.find((o) => o.selected)?.value).toBe("NETGL");
    expect(dom(renderAnaliz(vm({ tickers: [] }))).querySelector("[data-role=arz-switch]")).toBeNull();
  });

  it("işlem sayısı: D1 17.885, D2 28.445 binlik ayırıcıyla; 10 çubuk; en büyük gün (D9) tam yükseklik; sayı yoksa tire ve çubuk yok", () => {
    const cells = [...r.querySelectorAll<HTMLElement>(".trade-row .trade-cell")];
    expect(cells.length).toBe(10);
    expect(text(cells[0].querySelector(".trade-num"))).toBe("17.885");
    expect(text(cells[1].querySelector(".trade-num"))).toBe("28.445");
    expect(text(cells[8].querySelector(".trade-num"))).toBe("241.603");
    expect(r.querySelectorAll(".trade-row svg.trade rect.trade-bar").length).toBe(10);
    expect(cells[8].querySelector("rect.trade-bar")?.getAttribute("height")).toBe("24.0");
    expect(text(r.querySelector(".trade-title"))).toBe(SADE.analiz.tradeTitle);
    const days = ARZ.row.days.map((d, i) => (i === 9 ? { ...d, trade_count_raw: null, trade_count_rel: null } : d));
    const miss = dom(renderAnaliz(vm({ arz: { ...ARZ, row: { ...ARZ.row, days } } })));
    const last = miss.querySelector<HTMLElement>('.trade-row .trade-cell[data-h="10"]');
    expect(text(last?.querySelector(".trade-num"))).toBe(SADE.dash);
    expect(last?.querySelector("rect.trade-bar")).toBeNull();
    expect(miss.querySelectorAll(".trade-row rect.trade-bar").length).toBe(9);
  });

  it("hesaplayıcı resmi görünümde geçmiş arzlar satırı (%80, 66 arzdan 53) ve gün grupları notu", () => {
    expect(text(r.querySelector('.calc [data-reading="tomorrow"] .s-history .s-reading-value'))).toBe("%80");
    expect(text(r.querySelector(".calc .history-count"))).toBe(SADE.calc.historyCount(3, "66", "53", 4));
    expect(text(r.querySelector(".calc .calc-groups"))).toContain("1. gün · 2–3. gün · 4–10. gün");
  });

  it("başlık: arz fiyatı 25.52, D10 16.29, arza göre −%36.2, ilk işlem 17.09.2026, seri 3 gün, arz adedi 87.5 milyon", () => {
    const head = text(r.querySelector(".arz-head"));
    for (const s of ["25.52", "16.29", "-%36.2", "17.09.2026", SADE.analiz.streakDays("3"), `87.5 ${SADE.units.million}`]) expect(head, s).toContain(s);
    expect(r.querySelector('.s-stripe[data-regime="FON_KRIZI_2026"]')).not.toBeNull();
  });

  it("zaman çizelgesi 4 adım; koridor; model tavan kapanış olasılıkları ve gerçekleşen kapanışlar", () => {
    expect(r.querySelectorAll(".tl-step").length).toBe(4);
    expect(text(r.querySelector(".tl-break"))).toContain(SADE.analiz.tlBreakVal("%50"));
    expect(r.querySelector("svg.corridor path.close-line")).not.toBeNull();
    expect(r.querySelectorAll("svg.corridor rect.pt-up").length).toBe(3);
    expect(r.querySelectorAll("svg.corridor rect.pt-down").length).toBe(7);
    expect(r.querySelectorAll("svg.corridor .model-pt").length).toBe(4);
    expect(text(r.querySelector(".p-close-row .d-cell"))).toBe("%82");
    expect([...r.querySelectorAll(".realized-row .d-cell")].map((c) => c.textContent)).toEqual([
      ...Array(3).fill(SADE.analiz.ceiling),
      ...Array(7).fill(SADE.analiz.notCeiling),
    ]);
  });

  it("Kaç gün tavan kayıttan; gerçekleşen L = 3 halkalı; hesaplayıcı resmi görünüm j = 3", () => {
    expect(r.querySelector(".kac svg.dist rect.bar-ring")).not.toBeNull();
    expect(r.querySelector('.calc[data-mode="OFFICIAL"][data-j="3"]')).not.toBeNull();
    expect(text(r.querySelector('.calc [data-reading="tomorrow"] .s-reading-value'))).toBe("%67");
    expect(text(r.querySelector(".post-d1-line"))).toBe(SADE.calc.postD1None);
  });

  it("kırılma kartı: F1 %50, F2 %30 (≈), taban kırılması sınıf oranı %54, @ZERO %30, ürün yok; katsayılar ve kırpma notu; ön eleme etiketi", () => {
    const b = r.querySelector('.break-card[data-status="OK"]');
    expect(b).not.toBeNull();
    const t = text(b);
    expect(b?.querySelector(".s-big .gold")?.textContent).toBe("%50");
    expect(text(b?.querySelector(".s-mid"))).toBe(`%30 ${SADE.approxMark}`);
    const bars = Object.fromEntries([...(b?.querySelectorAll(".s-hbar") ?? [])].map((x) => [x.firstElementChild?.textContent ?? "", x.lastElementChild?.textContent ?? ""]));
    expect(bars).toEqual({
      [SADE.analiz.breakModel]: "%50",
      [SADE.analiz.breakByTypeFloor]: "%54",
      [SADE.analiz.breakZero]: "%30",
      [SADE.analiz.breakProduct]: SADE.analiz.breakProductNone,
    });
    for (const s of ["30.56 = 30.56", "+0.9867", "-2.1789*", "+0.0629", "-1.0007"]) expect(t, s).toContain(s);
    expect(t).toContain(SADE.analiz.clippedNote("-2.2666", "82", "25"));
    expect(t).toContain(SADE.analiz.structural("16.29", "25.52"));
    expect(t).toContain("ön eleme (yakın dönem backtest'i, tasarıma maruz); canlı n = 0");
    expect(t).toContain(SADE.analiz.breakClass(SADE.classText.RETRO));
    passOnlyInVerdictCells(r);
    noForbiddenWords(r);
  });

  it("kırılma kartı kapalı: sha uyuşmazlığı / dosya yok / kayıt yok; TKNKA yapısal sıfır", () => {
    const closed = dom(renderAnaliz(vm({ brk: { ...BREAK, status: "SHA_MISMATCH", features: [], heads: [], p_f1: null, card: null } })));
    expect(text(closed.querySelector(".break-card"))).toContain(SADE.analiz.breakClosed);
    expect(closed.querySelector(".break-card .s-big")).toBeNull();
    expect(text(dom(renderAnaliz(vm({ brk: null }))).querySelector(".break-card"))).toContain(SADE.analiz.breakNone);
    const tk = dom(renderAnaliz(vm({ brk: BREAK_TKNKA })));
    expect(text(tk.querySelector(".break-card"))).toContain(SADE.analiz.impossible);
    expect(text(tk.querySelector(".break-card"))).toContain(SADE.analiz.breakByTypeAbove);
  });

  it("getiri paneli: D5 öne çıkan; gerçekleşenler R_h metninden; günlük eskiden yeniye", () => {
    expect(text(r.querySelector('.returns tr[data-h="D5"]'))).toContain("+%7.8");
    notPrimaryRows(r, ["D1", "D3", "D10"]);
    expect(text(r.querySelector('.returns tr[data-h="D10"]'))).toContain("-%36.2");
    expect(r.querySelectorAll("svg.ret-dots circle.ret-fc").length).toBe(4);
    const rows = [...r.querySelectorAll(".events .f-at")].map((x) => x.textContent ?? "");
    expect(rows.length).toBe(ARZ.log.length);
  });

  it("arz seçilmemişken takipteki arzların tablosu: kod, şirket, ilk işlem günü; en yeni üstte; boşsa not", () => {
    const p = dom(renderAnalizPick([...PICK].reverse()));
    const rows = [...p.querySelectorAll<HTMLElement>('tr[data-action="pick"]')];
    expect(rows.map((x) => x.dataset.ticker)).toEqual(["NETGL", "BKRGY", "INTET", "KPEKS", "TKNKA", "VEYAS", "CITAS"]);
    expect(text(rows[0].querySelector(".t-ticker"))).toBe("NETGL");
    expect(text(rows[0].querySelector(".t-company"))).toBe(PICK[0].company ?? "");
    expect(text(rows[0].querySelector("td.num"))).toBe("17.09.2026");
    expect(rows[0].querySelector('button[data-action="pick"][data-ticker="NETGL"]')?.textContent).toBe(SADE.analiz.open);
    expect(text(p.querySelector("h1"))).toBe(SADE.analiz.title);
    expect(text(p)).toContain(SADE.analiz.pickNote);
    expect(text(dom(renderAnalizPick([])))).toContain(SADE.monitor.emptyRows);
  });
});

// ---------------------------------------------------------------- Model performansı

describe("Model performansı (perf_view; görev tablosu)", () => {
  const r = dom(renderPerf({ perf: PERF, gate: GATE, repoMode: true }));
  const rows = [...r.querySelectorAll<HTMLElement>("tr.perf-row")];

  it("dört scores.json satırı + iki kırılma satırı; fark, aralık, n ve kazanç/kayıp/eşit dosyadaki gibi", () => {
    expect(rows.map((x) => `${x.dataset.model}|${x.dataset.rule}`)).toEqual([
      "ceiling_hazard_v0|base_km_last10",
      "ceiling_hazard_v0|base_km_expanding",
      "v1_5_h99|base_train_median",
      "v1_5_h99|base_rate",
      "break_floor_v0|PRODUCT_BREAK_FLOOR",
      "break_floor_v0|break_floor_v0@ZERO",
    ]);
    const t = rows.map((x) => text(x));
    for (const s of ["-0.0496", "[-0.0751, -0.0219]", "52 / 87", "kazanç 52 · kayıp 35 · eşit 0"]) expect(t[0], s).toContain(s);
    for (const s of ["-0.0569", "[-0.0833, -0.0286]", "59 / 87"]) expect(t[1], s).toContain(s);
    for (const s of ["-8.4 puan", "[-13.4, -3.2] puan", "58 / 87"]) expect(t[2], s).toContain(s);
    for (const s of ["-0.0391", "[-0.0756, 0.0023]", "52 / 81"]) expect(t[3], s).toContain(s);
    for (const s of ["-0.1904", "[-0.2520, -0.1247]", SADE.perf.nOnly("69", "21")]) expect(t[4], s).toContain(s);
    for (const s of ["-0.0281", "[-0.0453, -0.0074]"]) expect(t[5], s).toContain(s);
  });

  it("hüküm hücresi dosyadaki verdict + sade açıklama; kırılma satırlarında hüküm alanı yok, ön eleme etiketi", () => {
    expect(rows.slice(0, 3).map((x) => x.querySelector(".verdict")?.getAttribute("data-verdict"))).toEqual([VERDICT.pass, VERDICT.pass, VERDICT.pass]);
    expect(rows[3].querySelector(".verdict")?.getAttribute("data-verdict")).toBe(VERDICT.undecided);
    expect(text(rows[0].querySelector(".verdict-plain"))).toBe(VERDICT_PLAIN[VERDICT.pass]);
    expect(text(rows[3].querySelector(".verdict-plain"))).toBe(VERDICT_PLAIN[VERDICT.undecided]);
    expect(rows[4].querySelector(".verdict")).toBeNull();
    expect(text(rows[4])).toContain(SADE.perf.noVerdict);
    expect(rows[4].querySelector(".promotion-label")).not.toBeNull();
    passOnlyInVerdictCells(r);
    noForbiddenWords(r);
  });

  it("okuma rehberi aynen (nokta, çizgi, sıfır); aralık çizimi her satırda; oran metni yok", () => {
    const g = text(r.querySelector(".s-guide"));
    for (const s of [SADE.perf.guideDot, SADE.perf.guideLine, SADE.perf.guideZero]) expect(g).toContain(s);
    expect(r.querySelectorAll("svg.iv").length).toBe(6);
    expect(r.querySelectorAll("svg.iv.iv-pass").length).toBe(5);
    expect(text(r)).not.toContain("daha düşük");
  });

  it("üç terazi ayrı (asla toplanmaz): geçmiş test, eski dönem (zaman-dışı), canlı sicil; canlı ilerleme", () => {
    const sc = [...r.querySelectorAll<HTMLElement>(".perf-scales tr[data-model]")];
    expect(sc.map((x) => x.dataset.model)).toEqual(["ceiling_hazard_v0", "v1_5_h99", "post_d1_hazard_v0", "break_floor_v0"]);
    expect(text(sc[0])).toContain(SADE.perf.oldN("130"));
    expect(text(sc[2])).toContain(SADE.perf.oldN("104"));
    expect(text(sc[1])).toContain(SADE.perf.liveLine("1", "5"));
    expect(text(sc[3])).toContain(SADE.monitor.noTest);
    expect(text(r.querySelector('.live-stage[data-model="v1_5_h99"]'))).toContain("1 / 30");
    expect(text(r.querySelector('.live-stage[data-model="ceiling_hazard_v0"]'))).toContain("0 / 30");
    expect(r.querySelectorAll(".live-rows tr[data-ticker]").length).toBe(7);
    expect(text(r.querySelector('.live-rows tr[data-ticker="NETGL"]'))).toContain(SADE.classText.LIVE);
    expect(r.querySelector('[data-detailed="accuracy"]')).not.toBeNull();
  });

  // FAZ9_UI_FIX K-FIX-5: "ayırt edilemiyor" ile "geçemiyor" ayrı; sıfır olan parça yazılmaz
  it("sayım cümlesi: 3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz; parçalar ayrı, sıfır yazılmaz", () => {
    expect(PERF.counts).toEqual({ n_rows: 6, n_pass: 3, n_undecided: 1, n_fail: 0, n_other: 0, n_no_verdict: 2 });
    const sentence = SADE.perf.stripRowsSub(PERF.counts);
    expect(sentence).toBe("3 satırda model daha iyi · 1 satırda fark net değil · 2 satır hükümsüz");
    expect(text(r.querySelector(".perf-diff .s-panel-head .s-note"))).toBe(sentence);
    expect(text(r)).toContain(sentence);
    expect(text(r)).not.toContain("satırda değil");
    expect(SADE.perf.stripRowsSub({ n_pass: 0, n_undecided: 0, n_fail: 2, n_other: 1, n_no_verdict: 0 })).toBe("2 satırda kural daha iyi · 1 satır yetersiz örnek");
    expect(SADE.perf.stripRowsSub({ n_pass: 4, n_undecided: 0, n_fail: 0, n_other: 0, n_no_verdict: 0 })).toBe("4 satırda model daha iyi");
    expect(SADE.perf.stripRowsSub({ n_pass: 0, n_undecided: 0, n_fail: 0, n_other: 0, n_no_verdict: 0 })).toBe("");
  });

  it("bütünlük ihlali → panel kapalı (fail-closed); bağımsız modda not", () => {
    const bad = dom(renderPerf({ perf: { ...PERF, scores_integrity: { rule: "LIVE_N_SPLIT", model_id: null, detail: "x" } }, gate: GATE, repoMode: true }));
    expect(bad.querySelector("tr.perf-row")).toBeNull();
    expect(text(bad)).toContain(SADE.perf.integrity("LIVE_N_SPLIT"));
    expect(text(dom(renderPerf({ perf: PERF, gate: GATE, repoMode: false })))).toContain(SADE.perf.repoOnlyPart);
  });
});

// ---------------------------------------------------------------- Sicil, Kayıtlarım, Ayarlar, Giriş

describe("Sicil", () => {
  const reg = fx<RegistryView>("registry_synthetic.json");
  it("şerit sayımları monitor_view'dan; tablo ve künye sekmeleri; sihirbaz ve iptal eski ekrana", () => {
    const r = dom(renderSicil({ registry: reg, monitor: MONITOR, ticker: reg.tickers[0].ticker, tab: "PRE", brk: BREAK, post: [], raw: null }));
    const strip = text(r.querySelector(".s-strip"));
    expect(strip).toContain(SADE.sicil.paydaSub(7, 19));
    expect(strip).toContain(SADE.sicil.repoClean);
    expect(r.querySelectorAll(".sicil-table tr[data-ticker]").length).toBe(reg.tickers.length);
    expect(r.querySelectorAll(".s-tabs .s-tab").length).toBe(3);
    expect(r.querySelector('[data-action="pd1-wizard"]')).not.toBeNull();
    expect(r.querySelector('[data-action="legacy-record"]')).not.toBeNull();
    const b = dom(renderSicil({ registry: reg, monitor: MONITOR, ticker: reg.tickers[0].ticker, tab: "BREAK", brk: BREAK, post: [], raw: null }));
    expect(text(b.querySelector(".sicil-kv"))).toContain(BREAK.record_file ?? "x");
  });
});

// ---------------------------------------------------------------- FAZ9_SNAPSHOT K-SNAP-3: kişisel modda kaynak metinleri

describe("gömülü sicil anlık görüntüsü (K-SNAP-3)", () => {
  const SNAP: SnapshotInfo = {
    status: "READY", code: null, detail: null, build_sha7: "e6c2e07", build_dirty: false,
    manifest_sha256: "0".repeat(64), n_files: 63, bytes: 627365, last_session: "2026-09-30",
  };
  const reg = fx<RegistryView>("registry_synthetic.json");

  it("repo modu: şerit ve künye metinleri aynen (kaynak satırı yok; fikstürde künye alanı yok)", () => {
    expect("snapshot" in MONITOR).toBe(false);
    expect("snapshot" in reg).toBe(false);
    const m = dom(renderMonitor({ view: MONITOR, gate: GATE, perf: PERF, selected: null, filter: "ALL" }));
    expect(m.querySelector(".snap-source")).toBeNull();
    const r = dom(renderSicil({ registry: reg, monitor: MONITOR, ticker: reg.tickers[0].ticker, tab: "PRE", brk: BREAK, post: [], raw: null }));
    expect(text(r.querySelector(".s-strip"))).toContain(SADE.sicil.repoClean);
    expect(r.querySelector(".sicil-source, .snap-source")).toBeNull();
    expect(text(r.querySelector(".s-lead"))).toBe(SADE.sicil.intro);
    expect(text(dom(renderPerf({ perf: PERF, gate: GATE, repoMode: true })))).not.toContain(SADE.snapshot.sourceVal);
  });

  it("Monitör veri şeridi: kaynak, derleme ve son sonuç (Rust'tan); kirli derlemede ek not", () => {
    const m = dom(renderMonitor({ view: { ...MONITOR, snapshot: SNAP }, gate: GATE, perf: PERF, selected: null, filter: "ALL" }));
    expect(text(m.querySelector(".snap-source"))).toBe("Veri: gömülü anlık görüntü · derleme e6c2e07 · son sonuç 30.09.2026");
    expect(m.querySelectorAll("tr[data-ticker]").length).toBe(7);
    const d = dom(renderMonitor({ view: { ...MONITOR, snapshot: { ...SNAP, build_dirty: true } }, gate: GATE, perf: PERF, selected: null, filter: "ALL" }));
    expect(text(d.querySelector(".snap-source"))).toContain("derlemede commit bekleyen değişiklik vardı");
  });

  it("Sicil: şeritte repo durumu yerine kaynak; künyede kaynak satırı", () => {
    const r = dom(renderSicil({ registry: { ...reg, snapshot: SNAP }, monitor: MONITOR, ticker: reg.tickers[0].ticker, tab: "PRE", brk: BREAK, post: [], raw: null }));
    const item = r.querySelector(".s-strip .snap-source");
    expect(text(item?.querySelector(".s-strip-label"))).toBe(SADE.snapshot.source);
    expect(text(item?.querySelector(".s-strip-value"))).toBe(SADE.snapshot.sourceVal);
    expect(text(item?.querySelector(".s-strip-sub"))).toBe("derleme e6c2e07");
    expect(text(r.querySelector(".s-strip"))).not.toContain(SADE.sicil.repoClean);
    expect(text(r.querySelector(".sicil-card .sicil-source"))).toBe("Kaynak: gömülü anlık görüntü · derleme e6c2e07");
    expect(text(r.querySelector(".s-lead"))).toBe(SADE.sicil.introSnapshot);
  });

  it("Performans: kişisel modda 'repo modu ister' notu yerine kaynak; anlık görüntü yoksa not aynen", () => {
    const p = dom(renderPerf({ perf: PERF, gate: GATE, repoMode: false, snapshot: SNAP }));
    expect(p.querySelector(".repo-only")).toBeNull();
    expect(text(p.querySelector(".snap-source"))).toContain(SADE.snapshot.sourceVal);
    expect(text(dom(renderPerf({ perf: PERF, gate: GATE, repoMode: false })))).toContain(SADE.perf.repoOnlyPart);
  });

  it("kapı: veri yoksa 'repo modu gerekli'; doğrulanamadıysa bütünlük kutusu; veri varsa açık", () => {
    expect(closedScreen("NONE", null)).toContain("repo-required");
    const failed = dom(closedScreen("FAILED", { ...SNAP, status: "FAILED", code: "SNAPSHOT_INTEGRITY_FAILED", detail: "x" }) ?? "");
    expect(failed.querySelector('[data-code="SNAPSHOT_INTEGRITY_FAILED"]')).not.toBeNull();
    expect(text(failed)).toContain(ERROR_TEXT.SNAPSHOT_INTEGRITY_FAILED);
    expect(closedScreen("SNAPSHOT", SNAP)).toBeNull();
    expect(closedScreen("REPO", null)).toBeNull();
    const cv = (o: Partial<ConfigView>): ConfigView => ({ config: { schema_version: "borsai.app_config/1", repo_root: null, python_path: null, scores_source: "REPO", ui_view: "SADE" }, config_note: null, repo: null, repo_mode: false, data_dir: "/d", suggested_repo_root: null, ...o });
    expect(dataSource(cv({}))).toBe("NONE");
    expect(dataSource(cv({ snapshot: SNAP }))).toBe("SNAPSHOT");
    expect(dataSource(cv({ snapshot: { ...SNAP, status: "PENDING" } }))).toBe("SNAPSHOT");
    expect(dataSource(cv({ snapshot: { ...SNAP, status: "NONE" } }))).toBe("NONE");
    expect(dataSource(cv({ snapshot: { ...SNAP, status: "FAILED" } }))).toBe("FAILED");
    expect(dataSource(cv({ repo_mode: true, snapshot: { ...SNAP, status: "FAILED" } }))).toBe("REPO");
    expect(dataSource(null)).toBe("NONE");
  });
});

describe("Kayıtlarım", () => {
  it("boş durum; liste satırları (Aç, Dışa aktar, Sil; eski küme işareti)", () => {
    expect(text(dom(renderKayitlarim([], "", null)))).toContain(SADE.kayitlarim.emptyTitle);
    const list: ScenarioSummary[] = [
      { scenario_id: "A", status: "OK", title: "NETGL, talep sonrası", created_at_local: "2026-10-03T14:00:00+03:00", stage: "POST_BOOKBUILD_PRE_LISTING", ticker_label: "NETGL", app_version: "0.1.0", models_index_sha256: "x", same_index: true, schema_version: "borsai.app_scenario/1" },
      { scenario_id: "B", status: "OLD_VERSION", title: "eski", created_at_local: null, stage: null, ticker_label: null, app_version: null, models_index_sha256: null, same_index: false, schema_version: null },
    ];
    const r = dom(renderKayitlarim(list, "", null));
    expect(r.querySelectorAll('[data-action="open"]').length).toBe(1);
    expect(r.querySelectorAll('[data-action="export"]').length).toBe(2);
    expect(text(r.querySelector('tr[data-id="B"]'))).toContain(SADE.kayitlarim.oldSet);
  });
});

describe("Ayarlar ve Hakkında (K-UI-1)", () => {
  const view = (ui: "SADE" | "AYRINTILI"): ConfigView => ({
    config: { schema_version: "borsai.app_config/1", repo_root: "/r", python_path: null, scores_source: "REPO", ui_view: ui },
    config_note: null,
    repo: null,
    repo_mode: false,
    data_dir: "/d",
    suggested_repo_root: null,
  });
  it("görünüm seçimi config'teki ui_view'dan; yoksa sade", () => {
    const r = dom(renderAyarlar({ view: view("AYRINTILI"), draft: view("AYRINTILI").config, check: null, info: null, msg: null, errorHtml: "" }));
    expect(r.querySelector<HTMLInputElement>('input[name=ui_view][value="AYRINTILI"]')?.checked).toBe(true);
    const s = dom(renderAyarlar({ view: null, draft: view("SADE").config, check: null, info: null, msg: null, errorHtml: "" }));
    expect(s.querySelector<HTMLInputElement>('input[name=ui_view][value="SADE"]')?.checked).toBe(true);
    expect(text(s)).toContain(SADE.ayarlar.viewDetailedSub);
  });
});

describe("Yeni arz girişi", () => {
  const form = (extra: Partial<FormState> = {}): FormState => ({
    stage: "POST_BOOKBUILD_PRE_LISTING",
    fields: { planned_post_ipo_capital: "312500000", planned_pre_ipo_capital: "250000000", planned_capital_increase_shares: "62500000", first_trading_date: "2026-09-17", ipo_price_tl: "25.52", ipo_size_tl: "2233000000" },
    tickerLabel: "NETGL",
    check: null,
    tickers: ["NETGL"],
    prefillTicker: "NETGL",
    prefillMsg: null,
    missingReasons: {},
    f6: { mode: "NONE", manual: "", market20: null, market20ForT: null, busy: false, error: null },
    busy: false,
    error: null,
    ...extra,
  });

  it("üç belge grubu (8 + 8 + 4 alan), okunur tekrar, aşama düğmeleri", () => {
    const r = dom(renderGiris({ form: form(), repoMode: true, hasResults: false }));
    expect(r.querySelectorAll(".group-spk .s-field").length).toBe(8);
    expect(r.querySelectorAll(".group-kap .s-field").length).toBe(8);
    expect(r.querySelectorAll(".group-bist .s-field").length).toBe(4);
    expect(text(r.querySelector('[data-readback="planned_post_ipo_capital"]'))).toContain(`312.5 ${SADE.units.million} pay`);
    expect(text(r.querySelector('[data-readback="first_trading_date"]'))).toContain("17 Eylül 2026");
    expect(text(r.querySelector('[data-readback="ipo_size_tl"]'))).toContain(`2.233 ${SADE.units.billion} TL`);
    expect(r.querySelector('[data-action="stage"].active')?.getAttribute("data-stage")).toBe("POST_BOOKBUILD_PRE_LISTING");
    expect(r.querySelector('[data-detailed="inputs"]')).not.toBeNull();
    expect(readback("total_demand_multiple", "2.84")).toBe("2.84 kat");
  });

  it("özdeşlik durumu yalnız Rust notundan: PB_IDENTITY ID-A → tutmuyor; not yok → tutuyor", () => {
    const f = form();
    const normalized = { ...f.fields } as Record<string, string | null>;
    const ok = dom(renderGiris({ form: { ...f, check: { stage: f.stage, normalized, notes: [], suggestions: {}, requirements: {}, model_inputs: {} } }, repoMode: true, hasResults: false }));
    expect(text(ok.querySelector('[data-identity="ID-A"]'))).toContain(SADE.giris.identityOk);
    const bad = dom(renderGiris({ form: { ...f, check: { stage: f.stage, normalized, notes: [{ field: "planned_post_ipo_capital", code: "PB_IDENTITY", level: "error", name: "ID-A", value: "1" }], suggestions: {}, requirements: {}, model_inputs: {} } }, repoMode: true, hasResults: false }));
    expect(text(bad.querySelector('[data-identity="ID-A"]'))).toContain(SADE.giris.identityBad);
    expect(bad.querySelector('[data-name="planned_post_ipo_capital"]')?.classList.contains("has-error")).toBe(true);
    const idb = text(bad.querySelector('[data-identity="ID-B"]'));
    expect(idb).toContain(SADE.dash);
    expect(idb).not.toContain(SADE.giris.identityOk);
    expect(bad.querySelector('[data-identity="ID-A"] .mark-fail')).not.toBeNull();
  });

  it("K-TXT-3: SUM tutmazsa uyarı (sarı ⚠, kırmızı × değil); not ID-A/B/C durdurur, SUM durdurmaz der", () => {
    const f = form();
    const sums = { shares_offered: "70000000", capital_increase_shares: "62500000", existing_share_sale_shares: "0", additional_sale_shares: "0" };
    const normalized = { ...f.fields, ...sums } as Record<string, string | null>;
    const note = { field: "shares_offered", code: "SHARES_SUM_MISMATCH", level: "warn", value: "62500000" };
    const r = dom(renderGiris({ form: { ...f, check: { stage: f.stage, normalized, notes: [note], suggestions: {}, requirements: {}, model_inputs: {} } }, repoMode: true, hasResults: false }));
    const sum = r.querySelector('[data-identity="SUM"]');
    expect(text(sum?.querySelector(".mark-warn"))).toBe(`${SADE.giris.identityWarnMark} ${SADE.giris.identityWarn}`);
    expect(sum?.querySelector(".mark-fail")).toBeNull();
    expect(text(sum)).not.toContain(`× ${SADE.giris.identityBad}`);
    expect(text(r.querySelector('[data-identity="ID-A"]'))).toContain(SADE.giris.identityOk);
    expect(text(r.querySelector(".check-panel"))).toContain("ID-A, ID-B, ID-C tutmazsa PB modelleri durur; SUM tutmazsa yalnız uyarıdır, model durmaz.");
  });

  it("aşama seçilmeden alanlar kapalı; bağımsız modda resmi kayıt ve hesapla kapalı", () => {
    const r = dom(renderGiris({ form: form({ stage: null }), repoMode: false, hasResults: false }));
    expect(r.querySelector<HTMLInputElement>('[data-field="ipo_price_tl"]')?.disabled).toBe(true);
    expect(r.querySelector<HTMLButtonElement>('[data-action="predict"]')?.disabled).toBe(true);
    expect(r.querySelector<HTMLButtonElement>('[data-action="f6-mode"][data-mode="REPO_PYTHON"]')?.disabled).toBe(true);
    expect(r.querySelector('[data-action="official"]')).toBeNull();
  });
});
