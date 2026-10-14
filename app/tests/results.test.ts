// @vitest-environment jsdom
// Sonuç ekranı render: U7 → U63 → P4 (10 RET + 17 dolu; EK 3 §10.1), U9 (f6 yok/bayat), U10 (kırpma),
// U11 (uyarılar gizlemez), rejim uyarısı, senaryo filigranı ve tooltip'i, model kartı.
// Girdiler Rust'ın gerçek çıktısı (fixture).
import { describe, expect, it } from "vitest";

import { CARD, CEILING, RESULTS, VERDICT } from "../src/i18n/tr";
import { renderResults, type ResultsView } from "../src/render/results";
import type { CeilingDisplay, ModelInfo, ModelRun, ScoreHints } from "../src/types";
import { dom, fx } from "./helpers";

function view(runs: ModelRun[], extra: Partial<ResultsView> = {}): ResultsView {
  return {
    runs,
    pathDisplay: fx<PathDisplayRow[]>("path_display_netgl.json"),
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    ceiling: null,
    hints: null,
    models: fx<ModelInfo[]>("app_models.json"),
    hidden: [],
    scenario: null,
    f6: null,
    openCard: null,
    openWarnings: null,
    savedId: null,
    canSave: true,
    ...extra,
  };
}

/** Sayı gösteren model sütunları (data-model'i olan dolu hücreler) ve RET blokları. */
function columns(root: HTMLElement): { filled: Set<string>; refused: Map<string, string> } {
  const filled = new Set<string>();
  root.querySelectorAll<HTMLElement>("td.cell[data-model]").forEach((c) => filled.add(c.dataset.model ?? ""));
  const refused = new Map<string, string>();
  root.querySelectorAll<HTMLElement>(".refusal").forEach((r) => refused.set(r.dataset.model ?? "", r.dataset.code ?? ""));
  return { filled, refused };
}

describe("U7: VEYAS girdileri (f3 boş)", () => {
  const runs = fx<ModelRun[]>("runs_veyas.json");
  const root = dom(
    renderResults(
      view(runs, { ceiling: fx<CeilingDisplay>("ceiling_veyas_j0.json"), pathDisplay: fx<PathDisplayRow[]>("path_display_veyas.json") }),
    ),
  );

  it("10 RET bloğu (F3_MISSING) ve 17 dolu sütun; 27 model sütunu da görünür", () => {
    const { filled, refused } = columns(root);
    expect([...refused.keys()].sort()).toEqual([
      "ceiling_hazard_v0",
      "ceiling_hazard_v1_clip",
      "ceiling_hazard_v1_pooled",
      "ceiling_hazard_v1_real",
      "ceiling_path_v0",
      "fall_d10_v0_h99",
      "fall_d10_v0_pooled",
      "v1_5_h99",
      "v1_5_market20_v0",
      "v1_6_h99",
    ]);
    expect(new Set(refused.values())).toEqual(new Set(["F3_MISSING"]));
    expect(filled.size).toBe(17);
    for (const id of refused.keys()) expect(filled.has(id)).toBe(false);
    const headers = new Set([...root.querySelectorAll<HTMLElement>("th.model-col[data-model]")].map((h) => h.dataset.model));
    expect(headers.size).toBe(27);
  });

  it("RET bloğu kod + alan + Türkçe neden; sayı göstermez", () => {
    const block = root.querySelector<HTMLElement>('.refusal[data-model="v1_5_h99"]');
    expect(block?.textContent).toContain("RET · F3_MISSING");
    expect(block?.textContent).toContain("total_demand_multiple");
    expect(block?.textContent).toContain("f3'süz tahmin PB sütunlarındadır");
    expect(block?.textContent).not.toMatch(/%\d/);
  });

  it("PB sütunları dolu: pb_v0 D1 getiri, fiyat ve P(kapanış > arz)", () => {
    const cell = root.querySelector<HTMLElement>('td.cell[data-model="pb_v0"][data-h="D1"]');
    const d1 = runs.find((r) => r.model_id === "pb_v0")?.output?.D1;
    expect(cell?.querySelector(".ret")?.textContent).toMatch(/^[+-]%\d+\.\d$/);
    expect(cell?.querySelector(".price")?.textContent).toBe(`${(d1?.price as number).toFixed(2)} TL`);
    expect(cell?.querySelector(".pup")?.textContent).toMatch(/^%\d+ [↑↓]$/);
  });

  it("kural sütunlarında olmayan çıktı '—'; base_always_ceiling fiyatı 'yaklaşık'", () => {
    const med = root.querySelector<HTMLElement>('td.cell[data-model="base_train_median"][data-h="D1"] .pup');
    expect(med?.textContent).toBe("—");
    const rate = root.querySelector<HTMLElement>('td.cell[data-model="base_rate"][data-h="D1"] .ret');
    expect(rate?.textContent).toBe("—");
    const always = root.querySelector<HTMLElement>('td.cell[data-model="base_always_ceiling"][data-h="D1"] .price');
    expect(always?.textContent).toContain("≈");
    expect(always?.textContent).toContain(RESULTS.approx);
  });

  it("tavan grubu: S_k, beklenen/medyan L, 'her zaman tavan' sabiti, fiyat eşlemesi", () => {
    expect(root.querySelector('td.cell.s[data-model="pb_ceiling_v0"][data-k="1"]')?.textContent).toMatch(/^%\d+$/);
    expect(root.textContent).toContain(CEILING.always);
    expect(root.textContent).toContain(CEILING.expectedL);
    expect(root.querySelector("svg.s-curve")).not.toBeNull();
    expect(root.textContent).toContain("k = 10: ≈");
  });

  it("senaryo filigranı, tooltip ve rejim uyarısı (U23 metni)", () => {
    // 27 model sütunu (Grup A tavan yolu ve (C) dahil + Grup B) + Grup C'de üç tavan yolu sütunu
    expect(root.querySelectorAll(".watermark").length).toBe(30);
    const cell = root.querySelector<HTMLElement>('td.cell[data-model="pb_v0"][data-h="D1"]');
    expect(cell?.title).toContain(RESULTS.scenarioTooltip);
    expect(cell?.title).toContain("return=");
    expect(root.querySelector("[data-role=regime]")?.textContent).toBe(RESULTS.regime);
  });
});

describe("U9: f6 yok / bayat", () => {
  for (const [file, code, why] of [
    ["runs_f6_missing.json", "MARKET20_NOT_PROVIDED", "f6 verilmedi"],
    ["runs_f6_stale.json", "MARKET20_STALE_S0", "pinli XU100 dosyası bayat"],
  ] as const) {
    it(`${code}: neden açıklamasıyla RET; diğer 26 model dolu`, () => {
      const root = dom(renderResults(view(fx<ModelRun[]>(file))));
      const { filled, refused } = columns(root);
      expect([...refused.entries()]).toEqual([["v1_5_market20_v0", code]]);
      expect(filled.size).toBe(26);
      const text = root.querySelector('.refusal[data-model="v1_5_market20_v0"]')?.textContent ?? "";
      expect(text).toContain("f6_market20");
      expect(text).toContain(why);
    });
  }
});

describe("U10: kırpma", () => {
  const runs = fx<ModelRun[]>("runs_clipped.json");
  const root = dom(renderResults(view(runs)));

  it("sınıra kırpılan hücrede ⌐ ve ham değer tooltip'i; gösterilen getiri sınırda", () => {
    const d1 = runs.find((r) => r.model_id === "v1_5_h99")?.output?.D1;
    expect(d1?.return_clipped).toBe("UPPER");
    const cell = root.querySelector<HTMLElement>('td.cell[data-model="v1_5_h99"][data-h="D1"]');
    const clip = cell?.querySelector<HTMLElement>(".clip");
    expect(clip?.textContent).toBe("⌐");
    expect(clip?.dataset.clipped).toBe("UPPER");
    const raw = ((d1?.return_unclipped as number) * 100).toFixed(1);
    expect(clip?.title).toBe(`fiziksel sınıra kırpıldı; ham değer +%${raw}`);
    expect(cell?.querySelector(".ret")?.textContent).toBe("+%10.0⌐");
  });

  it("kırpılmayan hücrede işaret yok", () => {
    const d10 = runs.find((r) => r.model_id === "v1_5_h99")?.output?.D10;
    expect(d10?.return_clipped).toBeNull();
    expect(root.querySelector('td.cell[data-model="v1_5_h99"][data-h="D10"] .clip')).toBeNull();
  });
});

describe("U11: uyarılar hiçbir hücreyi gizlemez", () => {
  const runs = fx<ModelRun[]>("runs_warnings.json");
  const root = dom(renderResults(view(runs)));

  it("27 sütunun hepsi dolu, RET yok", () => {
    const { filled, refused } = columns(root);
    expect(refused.size).toBe(0);
    expect(filled.size).toBe(27);
  });

  it("rozet sayıları uyarı listesi uzunluğuna eşit; üç uyarı kodu da var", () => {
    const codes = new Set<string>();
    for (const r of runs) {
      const badge = root.querySelector<HTMLElement>(`button[data-action="warnings"][data-model="${r.model_id}"]`);
      expect(badge?.dataset.count, r.model_id).toBe(String(r.output?.warnings.length));
      expect(badge?.textContent).toBe(`⚠ ${r.output?.warnings.length}`);
      r.output?.warnings.forEach((w) => codes.add(w.code));
    }
    for (const c of ["OUT_OF_TRAINING_RANGE", "F4_ZERO_NO_TRAINING_EXAMPLE", "PB4_ADDITIONAL_SALE_CEILING"]) expect(codes).toContain(c);
  });

  it("uyarı paneli listeler; hücreler yine görünür", () => {
    const r2 = dom(renderResults(view(runs, { openWarnings: "v1_5_h99" })));
    const items = r2.querySelectorAll(".warnings-panel li");
    expect(items.length).toBe(runs.find((r) => r.model_id === "v1_5_h99")?.output?.warnings.length);
    expect(r2.querySelector(".warnings-panel")?.textContent).toContain("eğitim aralığı");
    expect(columns(r2).filled.size).toBe(27);
  });
});

describe("model kartı, gizleme, backtest tipik hata", () => {
  const runs = fx<ModelRun[]>("runs_warnings.json");
  const hints = fx<ScoreHints>("score_hints.json");

  it("kart: model_id, ne yapar, eğitim n/kesim, sha ilk 8, varyant sayısı, prospektif durum", () => {
    const root = dom(renderResults(view(runs, { hints, openCard: "v1_5_h99" })));
    const card = root.querySelector(".card-panel")?.textContent ?? "";
    expect(card).toContain("v1_5_h99");
    expect(card).toContain("bf809859");
    expect(card).toContain("99 / 2026-08-19");
    expect(card).toContain(String(hints.models.v1_5_h99.card?.n_variants_same_data));
    expect(card).toContain("V1.5");
  });

  it("MAE satırı scores.json'daki model_value'dan (puan)", () => {
    const root = dom(renderResults(view(runs, { hints })));
    const mae = hints.models.v1_5_h99.mae.D1;
    const want = RESULTS.maeLine(String(mae.n), `${((mae.model_value as number) * 100).toFixed(1)} puan`);
    expect(root.querySelector('td.cell[data-model="v1_5_h99"][data-h="D1"] .mae')?.textContent).toBe(want);
    expect(dom(renderResults(view(runs))).querySelector(".mae")).toBeNull();
  });

  // U19 (aşama 4 denetimi): kartta hüküm metni yalnız scores.json'daki `verdict` alanından gelir;
  // arayüzde hüküm üreten başka kaynak yoktur.
  it("birincil hücrenin prospektif hükmü verdict alanından; n < 10'da hüküm yok", () => {
    const low = dom(renderResults(view(runs, { hints, openCard: "v1_5_h99" }))).querySelector(".card-panel")?.textContent ?? "";
    expect(low).toContain(CARD.liveNoVerdict(String(hints.models.v1_5_h99.live_n_scored)));
    expect(low).not.toContain(VERDICT.pass);
    const scored: ScoreHints = {
      ...hints,
      models: { ...hints.models, v1_5_h99: { ...hints.models.v1_5_h99, live_n_scored: 31, live_primary_verdict: VERDICT.pass } },
    };
    const card = dom(renderResults(view(runs, { hints: scored, openCard: "v1_5_h99" }))).querySelector(".card-panel")?.textContent ?? "";
    expect(card).toContain(VERDICT.pass);
    const none: ScoreHints = {
      ...hints,
      models: { ...hints.models, v1_5_h99: { ...hints.models.v1_5_h99, live_n_scored: 31, live_primary_verdict: null } },
    };
    const dash = dom(renderResults(view(runs, { hints: none, openCard: "v1_5_h99" }))).querySelector(".card-panel")?.textContent ?? "";
    expect(dash).not.toContain(VERDICT.pass);
  });

  it("gizlenen model sütunu görünmez ama seçicide kalır", () => {
    const root = dom(renderResults(view(runs, { hidden: ["pb_v0", "base_km_last10"] })));
    expect(root.querySelector('th.model-col[data-model="pb_v0"]')).toBeNull();
    expect(root.querySelector('th.model-col[data-model="base_km_last10"]')).toBeNull();
    expect(root.querySelector<HTMLInputElement>('input[data-model="pb_v0"]')?.checked).toBe(false);
  });

  it("boş hâl", () => {
    expect(dom(renderResults(view([]))).textContent).toContain(RESULTS.empty);
  });
});
