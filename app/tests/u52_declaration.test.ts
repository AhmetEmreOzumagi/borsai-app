// @vitest-environment jsdom
// U52 (SPEC_APP §5.6; proje sahibi kararı 2026-09-23): beyandan türetilmiş sayı arayüzde YOK.
// Fixture: kurgusal data/outcomes/SNTB1.csv (D1–D2 OK-tavan, D3 PENDING → resmi j = 2) + beyan
// "D3 seri sürüyor" (beyanlı j = 3). Değer kümesi aynı Rust fonksiyonlarından (ceiling_display /
// record_ceiling, j = 3 fixture'ı) gelir ve arayüzün biçimlendiricisiyle metne çevrilir.
//
// Faz 4 (tavan-yolu) koşullu getiri sayıları da aynı kurala girer (Aşama P2, EK 2 §4.3): beyanlı j
// ile çıkacak medyan/p_up/q10/q90 metinleri kümeye eklenir ve kartın boş kaldığı sınanır.
import { readdirSync, statSync } from "node:fs";
import { join, sep } from "node:path";
import { describe, expect, it } from "vitest";

import { CEILING, COND } from "../src/i18n/tr";
import { declarationState, renderConditional, type ConditionalVM, type PathCondVM } from "../src/render/ceiling";
import { fixed1, pct0, pctSigned1, pyRepr } from "../src/render/format";
import { renderRecordPage, type RecordPageVM } from "../src/render/registry";
import { renderResults, type ResultsView } from "../src/render/results";
import { declaredDays, resetView, store } from "../src/state";
import type { CeilingDisplay, ModelInfo, ModelRun, RecordCeiling, RegistryView, StreakView } from "../src/types";
import { DECL_IDS, declFlowViolations } from "./decl_flow";
import { APP_DIR, dom, fx, readText, split } from "./helpers";

const NO_DECL = Array<boolean>(10).fill(false);
/** D3'e "seri sürüyor" beyanı: dosyada PENDING olduğu için beyan resmi verinin ÖNÜNDEDİR. */
const DECL_D3 = [false, false, true, false, false, false, false, false, false, false];

// ---------------------------------------------------------------- değer kümesi ve DOM taraması

/**
 * Seçilen j'deki `ceiling_display`'den arayüzün basacağı bütün metinler: koşullu S yüzdeleri
 * (ve tooltip'teki ham binary64), "yarın bozulma", koşullu beklenen/kalan/medyan L.
 * `render/ceiling.ts: condCurve` ile aynı biçimlendiriciler.
 */
function valueTexts(d: CeilingDisplay): string[] {
  const out: string[] = [];
  for (const r of d.rows) {
    const c = r.cond;
    if (!c) continue;
    for (let k = d.j + 1; k <= 10; k += 1) {
      const x = c.S_cond[k - 1];
      if (x === null) continue;
      out.push(pct0(x));
      out.push(pyRepr(x));
    }
    out.push(pct0(c.p_break_next));
    out.push(CEILING.days(fixed1(c.expected_l)));
    out.push(CEILING.days(fixed1(c.expected_remaining)));
    out.push(CEILING.days(String(c.median_l)));
  }
  return [...new Set(out)];
}

/**
 * Tavan yolu koşullu getirisinin arayüzde basılacak metinleri: medyan, %10–%90, p_up, S_h, atom
 * sayısı ve tooltip'teki ham binary64 (`render/ceiling.ts: condRow`/`condRaw` ile aynı biçimlendirici).
 */
function pathTexts(c: PathConditional): string[] {
  const out: string[] = [];
  for (let h = 1; h <= 10; h += 1) {
    const cell = (c.result as unknown as Record<string, PathHorizon | undefined>)[`D${h}`];
    if (!cell || cell.status !== "OK" || cell.return === null) continue;
    out.push(pctSigned1(cell.return), pctSigned1(cell.q10), pctSigned1(cell.q90));
    out.push(pct0(cell.p_up), pct0(cell.S_h), String(cell.n_atoms));
    out.push(pyRepr(cell.return), pyRepr(cell.q10), pyRepr(cell.q90), pyRepr(cell.p_up), pyRepr(cell.S_h));
  }
  return [...new Set(out)];
}

/** Metin düğümleri + bütün öznitelikler (title / aria-label / data-*) + SVG <text>/<title> içeriği. */
function allText(root: HTMLElement): string {
  const parts: string[] = [root.textContent ?? ""];
  for (const el of root.querySelectorAll("*")) {
    for (const a of el.attributes) parts.push(a.value);
  }
  return parts.join("");
}

// ---------------------------------------------------------------- üç görünüm

const streakPending = () => fx<StreakView>("streak_sntb1.json"); // resmi j = 2
const streakOk = () => fx<StreakView>("streak_sntb1_ok.json"); // pozitif kontrol: resmi j = 3

function condVM(
  cond: CeilingDisplay,
  j: number,
  streak: StreakView,
  declared: boolean[],
  tab: "ceiling" | "return" = "ceiling",
  pathCond: PathCondVM[] = [],
): ConditionalVM {
  return {
    streak,
    cond,
    jSelected: j,
    tab,
    hidden: [],
    declared,
    declDropped: false,
    pathAvailable: true,
    pathCond,
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    recordWithoutPath: false,
  };
}

/** 2. görünüm: sonuç ekranı (screens/results.ts paint(): renderResults + renderConditional). */
function resultsHtml(vm: ConditionalVM, scenario: ResultsView["scenario"] = null): string {
  const view: ResultsView = {
    runs: fx<ModelRun[]>("runs_netgl.json"),
    pathDisplay: fx<PathDisplayRow[]>("path_display_netgl.json"),
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    ceiling: fx<CeilingDisplay>("ceiling_netgl_j0.json"),
    hints: null,
    models: fx<ModelInfo[]>("app_models.json"),
    hidden: [],
    scenario,
    f6: null,
    openCard: null,
    openWarnings: null,
    savedId: null,
    canSave: true,
    repoMode: false,
  };
  return renderResults(view) + renderConditional(vm);
}

/** 1. görünüm: resmi sicil (arz sayfası; değerler yalnız dondurulmuş kayıttan, U38). */
function recordHtml(ceiling: RecordCeiling, j: number, streak: StreakView, declared: boolean[]): string {
  const v = fx<RegistryView>("registry_synthetic.json");
  const vm: RecordPageVM = {
    ticker: v.tickers[0],
    selected: 0,
    ceiling,
    streak,
    jSelected: j,
    tab: "ceiling",
    hidden: [],
    declared,
    declDropped: false,
    pathDisplay: fx<PathDisplayRow[]>("path_display_record.json"),
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    pathCond: [],
    models: fx<ModelInfo[]>("app_models.json"),
    hints: null,
    raw: null,
    cancelReason: "",
    cancelDone: null,
    today: v.today_istanbul,
  };
  return renderRecordPage(vm);
}

/**
 * Beyanlı j ile çıkacak metin kümesi; aynı ekranda BAŞKA bir kaynaktan da üretilen metinler
 * (beyansız, resmi j ile render edilen ekranın tamamı) kümeden çıkarılır ve döndürülür.
 */
function forbiddenSet(jDeclared: CeilingDisplay, baseline: string): { forbidden: string[]; removed: string[] } {
  const all = valueTexts(jDeclared);
  const base = allText(dom(baseline));
  return { forbidden: all.filter((t) => !base.includes(t)), removed: all.filter((t) => base.includes(t)) };
}

// ---------------------------------------------------------------- testler

describe("U52-1/2/4: beyanlı j'nin değerleri hiçbir görünümde geçmez", () => {
  const j2 = fx<CeilingDisplay>("ceiling_netgl_j2.json");
  const j3 = fx<CeilingDisplay>("ceiling_netgl_j3.json");
  const rec2 = fx<RecordCeiling>("record_ceiling_u52_j2.json");
  const rec3 = fx<RecordCeiling>("record_ceiling_u52_j3.json");

  it("arama kümesi boş değil (sonuç ekranı ve resmi sicil)", () => {
    const a = forbiddenSet(j3, resultsHtml(condVM(j2, 2, streakPending(), NO_DECL)));
    const b = forbiddenSet(rec3.display, recordHtml(rec2, 2, streakPending(), NO_DECL));
    expect(a.forbidden.length).toBeGreaterThanOrEqual(10);
    expect(b.forbidden.length).toBeGreaterThanOrEqual(10);
    // aynı ekranda başka kaynaktan da üretilen metinler (listeleme; kümeden çıkarıldılar)
    expect(Array.isArray(a.removed)).toBe(true);
    expect(Array.isArray(b.removed)).toBe(true);
  });

  it("1. görünüm — resmi sicil: beyanlı j'nin hiçbir metni DOM'da yok", () => {
    const { forbidden } = forbiddenSet(rec3.display, recordHtml(rec2, 2, streakPending(), NO_DECL));
    const text = allText(dom(recordHtml(rec2, 2, streakPending(), DECL_D3)));
    for (const t of forbidden) expect(text, t).not.toContain(t);
  });

  it("2. görünüm — sonuç ekranı: beyanlı j'nin hiçbir metni DOM'da yok", () => {
    const { forbidden } = forbiddenSet(j3, resultsHtml(condVM(j2, 2, streakPending(), NO_DECL)));
    const text = allText(dom(resultsHtml(condVM(j2, 2, streakPending(), DECL_D3))));
    for (const t of forbidden) expect(text, t).not.toContain(t);
  });

  it("3. görünüm — senaryo: beyanlı j'nin hiçbir metni DOM'da yok", () => {
    const head = { title: "SNTB1 senaryo", created_at_local: "2030-01-09T10:00:00+03:00", same_index: true };
    const { forbidden } = forbiddenSet(j3, resultsHtml(condVM(j2, 2, streakPending(), NO_DECL), head));
    const text = allText(dom(resultsHtml(condVM(j2, 2, streakPending(), DECL_D3), head)));
    for (const t of forbidden) expect(text, t).not.toContain(t);
  });

  it("U52-4 pozitif kontrol: D3 resmen OK-tavan olunca (resmi j = 3) aynı küme ekranda görünür", () => {
    const { forbidden } = forbiddenSet(j3, resultsHtml(condVM(j2, 2, streakPending(), NO_DECL)));
    const text = allText(dom(resultsHtml(condVM(j3, 3, streakOk(), NO_DECL))));
    for (const t of forbidden) expect(text, t).toContain(t);

    const rb = forbiddenSet(rec3.display, recordHtml(rec2, 2, streakPending(), NO_DECL));
    const rtext = allText(dom(recordHtml(rec3, 3, streakOk(), NO_DECL)));
    for (const t of rb.forbidden) expect(rtext, t).toContain(t);
  });
});

describe("U52-3: koşullu bölüm ve koşullu getiri kartı boş, 'resmi kapanış bekleniyor'", () => {
  const j2 = fx<CeilingDisplay>("ceiling_netgl_j2.json");

  it("koşullu olasılık bölümünde sayı hücresi yok, uyarı var; şeritte turuncu beyan etiketi", () => {
    const root = dom(renderConditional(condVM(j2, 2, streakPending(), DECL_D3)));
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    expect(root.querySelector(".cond-table")).toBeNull();
    expect(root.querySelector("svg.cond-curve")).toBeNull();
    expect(root.querySelectorAll("td.cell").length).toBe(0);
    const d3 = root.querySelector<HTMLElement>('.day[data-h="3"]');
    expect(d3?.classList.contains("declared")).toBe(true);
    expect(d3?.textContent).toContain(COND.userBadge);
    expect(root.querySelector(".user-badge")?.textContent).toBe(COND.userBadge);
    expect(root.textContent).toContain(COND.declaredNotCounted(3));
  });

  it("koşullu getiri kartı da boş kalır ve aynı uyarıyı yazar", () => {
    const root = dom(renderConditional(condVM(j2, 2, streakPending(), DECL_D3, "return")));
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    expect(root.querySelector(".return-none")).toBeNull();
    expect(root.textContent).not.toMatch(/%\d/);
  });

  // Aşama P2: tavan yolu modellerinin koşullu getirisi de aynı kurala girer (EK 2 §4.3, U49).
  describe("P2: tavan-yolu modellerinin koşullu medyan/p_up/q10/q90 değerleri de kümeye girer", () => {
    const j2: PathCondVM = { model_id: "ceiling_path_v0", result: fx<PathConditional>("path_cond_record_j2.json"), error: null };
    const j3: PathCondVM = { model_id: "ceiling_path_v0", result: fx<PathConditional>("path_cond_record_j3.json"), error: null };
    const ret = (streak: StreakView, declared: boolean[], pathCond: PathCondVM[], j: number) =>
      allText(dom(renderConditional(condVM(fx<CeilingDisplay>("ceiling_netgl_j3.json"), j, streak, declared, "return", pathCond))));

    /** Beyanlı j = 3'te çıkacak metinler; resmi j = 2 ekranında geçenler kümeden düşer. */
    const forbidden = () => {
      const base = ret(streakPending(), NO_DECL, [j2], 2);
      return pathTexts(j3.result as PathConditional).filter((t) => !base.includes(t));
    };

    it("arama kümesi boş değil", () => {
      expect(forbidden().length).toBeGreaterThanOrEqual(10);
    });

    it("beyan resmi verinin önündeyken hiçbiri DOM'da yok (kart boş, uyarı var)", () => {
      const text = ret(streakPending(), DECL_D3, [j3], 2);
      for (const t of forbidden()) expect(text, t).not.toContain(t);
      expect(text).toContain(COND.officialPending);
    });

    it("pozitif kontrol: D3 resmen tavan olunca (resmi j = 3) aynı küme ekranda görünür", () => {
      const text = ret(streakOk(), NO_DECL, [j3], 3);
      for (const t of forbidden()) expect(text, t).toContain(t);
    });
  });

  it("beyan resmi veriyle çelişirse gösterilmez, uyarı çıkar", () => {
    // streak_broken: D3 dosyada 'tavan değil'; aynı güne "seri sürüyor" beyanı çelişkidir
    const broken = fx<StreakView>("streak_broken.json");
    const root = dom(renderConditional(condVM(j2, 2, broken, DECL_D3)));
    expect(root.querySelector(".decl-conflict")?.textContent).toBe(COND.declarationConflict);
    expect(root.querySelector<HTMLElement>('.day[data-h="3"]')?.classList.contains("declared")).toBe(false);
    expect(root.querySelector(".official-pending")).toBeNull();
  });

  it("resmi kapanış gelince beyan etiketi kalkar (hesap resmi veriyle)", () => {
    const root = dom(renderConditional(condVM(j2, 2, streakOk(), DECL_D3)));
    expect(root.querySelector(".user-badge")).toBeNull();
    expect(root.querySelector(".official-pending")).toBeNull();
    expect(root.querySelector(".cond-table")).not.toBeNull();
  });
});

describe("U52-6: şeritte tek beyan seçeneği 'seri sürüyor'", () => {
  it("beyan metni ve yardım satırı tek türü anlatır", () => {
    expect(COND.declareOption).toBe("seri sürüyor");
    expect(COND.userBadge).toContain("seri sürüyor");
    expect(COND.stripHelp).toContain(COND.declareOption);
    for (const w of ["tavan değil", "bekliyor"]) expect(COND.stripHelp).not.toContain(w);
  });

  it("beyan durumu üç değerden birine eşlenir: AHEAD / CONFLICT / SUPERSEDED", () => {
    expect(declarationState(null, false)).toBeNull();
    expect(declarationState("PENDING", true)).toBe("AHEAD");
    expect(declarationState(null, true)).toBe("AHEAD");
    expect(declarationState("NO_LABEL", true)).toBe("AHEAD");
    expect(declarationState("NOT_CEILING", true)).toBe("CONFLICT");
    expect(declarationState("CEILING", true)).toBe("SUPERSEDED");
  });
});

describe("U52-2 (şema): eski beyan türleri yüklemede yok sayılır, sarı not düşer", () => {
  it("resetView yalnız CEILING'i alır; ötekiler düşünce declDropped", () => {
    resetView(["CEILING", "NOT_CEILING", "PENDING", null]);
    expect(store.view.declared.slice(0, 4)).toEqual([true, false, false, false]);
    expect(store.view.declDropped).toBe(true);
    expect(declaredDays(store.view.declared).slice(0, 2)).toEqual(["CEILING", null]);
    resetView(["CEILING", null]);
    expect(store.view.declDropped).toBe(false);
  });

  it("sarı not şeritte görünür", () => {
    const root = dom(renderConditional({ ...condVM(fx<CeilingDisplay>("ceiling_netgl_j2.json"), 2, streakPending(), DECL_D3), declDropped: true }));
    expect(root.querySelector(".decl-dropped")?.textContent).toBe(COND.declarationDropped);
  });
});

describe("U52-5: beyan hiçbir Rust komutuna geçmez (ön uç tarafı)", () => {
  const SRC = join(APP_DIR, "src");
  const walk = (d: string): string[] =>
    readdirSync(d).flatMap((n) => {
      const p = join(d, n);
      return statSync(p).isDirectory() ? walk(p) : p.endsWith(".ts") ? [p] : [];
    });
  // Tam sözcük: tr.ts'teki `declaredNotCounted` gibi metin anahtarları eşleşmez.
  const DECL_WORDS = [/\bdeclared\b/, /\bdeclDropped\b/, /\bobserved_streak_user\b/, /\buserDays\b/];

  it("api çağrılarının hiçbirinde beyan alanı yok", () => {
    for (const f of walk(SRC)) {
      const rel = f.slice(SRC.length + 1).split(sep).join("/"); // Windows: ayırıcı '/' (FAZ9_WINDOWS)
      const { code } = split(readText(`src/${rel}`));
      for (const l of code.split("\n").filter((x) => x.includes("api."))) {
        for (const w of DECL_WORDS) expect(w.test(l), `${rel}: ${l.trim()}`).toBe(false);
      }
    }
  });

  it("streakView çağrısı tek argüman alır (beyan Rust'a geçmez)", () => {
    expect(readText("src/api.ts")).toContain('streakView: (ticker: string | null) =>');
    for (const rel of ["screens/results.ts", "screens/registry.ts"]) {
      const { code } = split(readText(`src/${rel}`));
      expect(/streakView\([^)]*,/.test(code), rel).toBe(false);
    }
  });

  it("beyan durumu yalnız şerit etiketi render'ında ve kişisel kayıt yolunda geçer", () => {
    const allowed = new Set([
      "types.ts", // tür
      "state.ts", // bellek + kişisel kayıt biçimine çevirme
      "api.ts", // senaryo kaydı isteğinin türü
      "render/ceiling.ts", // şerit etiketi render'ı
      "render/registry.ts", // aynı render'a taşıma
      "render/summary.ts", // Tavan serisi kartı: "önde mi" etiketi (EK 3 U62)
      "screens/results.ts", // şerit tıklaması + senaryo kaydı
      "screens/registry.ts", // şerit tıklaması
      "screens/inputs.ts", // form yenilenince beyanı koru
      "screens/scenarios.ts", // kişisel kayıt yükleme
    ]);
    const hits: string[] = [];
    for (const f of walk(SRC)) {
      const rel = f.slice(SRC.length + 1).split(sep).join("/"); // Windows: ayırıcı '/' (FAZ9_WINDOWS)
      const { code } = split(readText(`src/${rel}`));
      if (DECL_WORDS.some((w) => w.test(code))) hits.push(rel);
    }
    expect(hits.filter((h) => !allowed.has(h))).toEqual([]);
    expect(hits).toContain("render/ceiling.ts");
  });
});

describe("U52-5 (veri akışı): screens/*.ts'de beyan yalnız işleyicide, kaydetmede, resetView'da ve etiket render'ında", () => {
  const SCREENS = join(APP_DIR, "src", "screens");
  const files = readdirSync(SCREENS).filter((n) => n.endsWith(".ts")).sort();
  const text = (n: string) => readText(`src/screens/${n}`);

  it("bütün ekran dosyalarında beyan akışı yalnız izinli havuzlarda biter", () => {
    const v = files.flatMap((n) => declFlowViolations(`screens/${n}`, text(n)));
    expect(v.map((x) => `${x.file}:${x.line}: ${x.text}  [${x.why}]`)).toEqual([]);
    // tarama gerçekten beyan geçişlerini görüyor (boş küme değil)
    const seen = files.filter((n) => [...DECL_IDS].some((w) => new RegExp(`\\b${w}\\b`).test(text(n))));
    expect(seen).toEqual(["inputs.ts", "registry.ts", "results.ts", "scenarios.ts"]);
  });

  // Pozitif kontrol: denetimin mutasyonları ve benzerleri bellekte uygulanır; tarama hepsini yakalar.
  const mutations: [string, string, string, string][] = [
    ["(e2) sonuç: j beyandan bir satır önce türetilir", "results.ts",
      "const j = store.view.jSelected ?? streak.j_observed ?? 0;",
      "const j = (store.view.jSelected ?? streak.j_observed ?? 0) + store.view.declared.filter((x) => x).length;"],
    ["(e1) sonuç: beyan doğrudan api satırında", "results.ts",
      "await api.pathConditional(run.model_id, source, jOrT, stateName)",
      "await api.pathConditional(run.model_id, source, jOrT + store.view.declared.filter((x) => x).length, stateName)"],
    ["sonuç: beyan işleyicisi j'yi değiştirir", "results.ts",
      "store.view.declared[h - 1] = !store.view.declared[h - 1];",
      "store.view.declared[h - 1] = !store.view.declared[h - 1];\n        store.view.jSelected = store.view.declared.lastIndexOf(true) + 1;"],
    ["sonuç: beyan ara değişkenle komuta", "results.ts",
      "const sv = sVectors(r.runs);",
      "const sv = sVectors(r.runs);\n    const extra = store.view.declared.filter(Boolean).length;\n    const jj = extra;\n    await api.ceilingDisplay(sv, jj, null);"],
    ["sicil: j beyandan türetilir", "registry.ts",
      "const j = s.jSelected ?? s.streak.j_observed ?? 0;",
      "const j = (s.jSelected ?? s.streak.j_observed ?? 0) + s.declared.filter(Boolean).length;"],
    ["sicil: render'a hesaplanmış beyan", "registry.ts",
      "declared: s.declared,",
      "declared: s.declared.map((x, i) => x || i < 2),"],
  ];
  for (const [name, file, from, to] of mutations) {
    it(`pozitif kontrol: ${name} → kırmızı`, () => {
      const src = text(file);
      expect(src, `${file} içinde mutasyon noktası`).toContain(from);
      expect(declFlowViolations(`screens/${file}`, src)).toEqual([]);
      const v = declFlowViolations(`screens/${file}`, src.replace(from, to));
      expect(v.length, name).toBeGreaterThan(0);
    });
  }
});
