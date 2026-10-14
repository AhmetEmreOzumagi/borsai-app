// @vitest-environment jsdom
// Aşama 5 (SPEC_APP §3 genel çerçeve, §3d, §3f): ekran başına mod bandı, payda bölümü, tek model
// kartı ve rejim metni. A5-1…A5-5, A5-7 burada; A5-6 cargo tarafındadır
// (`commands::scenario::tests::export_all_scenarios_array_and_guard`).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { ACCURACY, CARD, KIND_TEXT, REGISTRY, RESULTS, SCENARIOS, TR, type ScreenId } from "../src/i18n/tr";
import { renderAccuracy, type AccuracyView } from "../src/render/accuracy";
import { renderModelCard, type CardVM } from "../src/render/card";
import { proofLine, renderRecordPage, renderRegistryList, type RecordPageVM } from "../src/render/registry";
import { renderResults, type ResultsView } from "../src/render/results";
import { bandFor, bandText, renderBand, type BandVM } from "../src/render/shell";
import { renderScenarioList } from "../src/screens/scenarios";
import type {
  ModelInfo,
  PathParamsInfo,
  RecordRow,
  RegistryView,
  ScenarioSummary,
  ScoreHints,
  ScoresDoc,
  ScoresView,
} from "../src/types";
import { APP_DIR, dom, fx, repoScoresDoc } from "./helpers";

const MODELS = fx<ModelInfo[]>("app_models.json");
const PATH_PARAMS = fx<PathParamsInfo[]>("path_params.json");

function vm(extra: Partial<BandVM> = {}): BandVM {
  return {
    screen: "inputs",
    registryMode: "list",
    recordFile: null,
    recordProof: null,
    ticker: null,
    repoMode: false,
    repoRoot: null,
    ...extra,
  };
}

// ---------------------------------------------------------------- A5-1

describe("A5-1: mod bandı ekran ve hâl başına (§3 tablosu)", () => {
  const cases: [string, BandVM, string, string][] = [
    ["Girdi", vm({ screen: "inputs" }), "mode-scenario", `${TR.modeScenario} · ${TR.modeScenarioNote}`],
    ["Sonuç", vm({ screen: "results" }), "mode-scenario", `${TR.modeScenario} · ${TR.modeScenarioNote}`],
    ["Kişisel kayıtlar", vm({ screen: "scenarios" }), "mode-scenario", `${TR.modeScenario} · ${TR.modeScenarioNote}`],
    [
      "Sicil · liste",
      vm({ screen: "registry", registryMode: "list" }),
      "mode-official",
      `${TR.modeOfficial} · ${TR.modeOfficialList}`,
    ],
    [
      "Sicil · arz sayfası, kayıt seçili",
      vm({ screen: "registry", registryMode: "record", ticker: "SNTA1", recordFile: "kayit.json", recordProof: "kanıt dizesi" }),
      "mode-official",
      `${TR.modeOfficial} · kayit.json · kanıt dizesi`,
    ],
    [
      "Sicil · arz sayfası, kayıt yok",
      vm({ screen: "registry", registryMode: "record", ticker: "SNTA1" }),
      "mode-official",
      `${TR.modeOfficial} · SNTA1 · ${TR.modeOfficialNoRecord}`,
    ],
    [
      "Sicil · dondur sihirbazı",
      vm({ screen: "registry", registryMode: "wizard" }),
      "mode-official",
      `${TR.modeOfficial} · ${TR.modeOfficialWizard}`,
    ],
    ["Doğruluk", vm({ screen: "accuracy" }), "mode-neutral", `${TR.modeAccuracy} · ${TR.modeAccuracyNote}`],
    ["Ayarlar", vm({ screen: "settings" }), "mode-neutral", ""],
    ["Hakkında", vm({ screen: "about" }), "mode-neutral", ""],
  ];

  for (const [name, v, cls, text] of cases) {
    it(`${name}: sınıf ve metin birebir`, () => {
      const b = bandFor(v);
      expect(b.cls).toBe(cls);
      expect(bandText(b)).toBe(text);
      const el = dom(renderBand(v)).querySelector<HTMLElement>("header.mode-band");
      expect(el?.classList.contains(cls)).toBe(true);
      // metin, sağdaki repo modu göstergesi hariç
      el?.querySelector(".repo-mode")?.remove();
      expect(el?.textContent).toBe(text);
    });
  }

  it("Ayarlar ve Hakkında bandında mod sözcüğü yok", () => {
    for (const s of ["settings", "about"] as ScreenId[]) {
      const b = bandFor(vm({ screen: s }));
      expect(b.head).toBe("");
      expect(b.note).toBe("");
    }
  });

  it("repo modu göstergesi her bantta aynen kalır", () => {
    for (const s of ["inputs", "registry", "accuracy", "settings"] as ScreenId[]) {
      const on = dom(renderBand(vm({ screen: s, repoMode: true, repoRoot: "/tmp/repo" })));
      expect(on.querySelector(".repo-mode")?.textContent).toBe(TR.repoMode("/tmp/repo"));
      expect(on.querySelector(".repo-mode")?.classList.contains("repo-on")).toBe(true);
      const off = dom(renderBand(vm({ screen: s })));
      expect(off.querySelector(".repo-mode")?.textContent).toBe(TR.standaloneMode);
    }
  });
});

// ---------------------------------------------------------------- A5-2

function recordPage(extra: Partial<RecordPageVM> = {}): RecordPageVM {
  const v = fx<RegistryView>("registry_synthetic.json");
  return {
    ticker: v.tickers[0],
    selected: 0,
    ceiling: null,
    streak: null,
    jSelected: 0,
    tab: "ceiling",
    hidden: [],
    declared: Array<boolean>(10).fill(false),
    declDropped: false,
    pathDisplay: [],
    pathParams: PATH_PARAMS,
    pathCond: [],
    models: MODELS,
    hints: null,
    raw: null,
    cancelReason: "",
    cancelDone: null,
    today: v.today_istanbul,
    ...extra,
  };
}

function realScores(): ScoresView {
  const doc = repoScoresDoc<ScoresDoc>();
  return {
    source: "REPO",
    unsupported_version: null,
    generated_at_utc: doc.generated_at_utc ?? null,
    as_of_session: doc.as_of_session ?? null,
    sha12: "gerçek dosya",
    index_mismatch: false,
    synthetic: false,
    integrity: null,
    doc,
  };
}

function accuracyView(extra: Partial<AccuracyView> = {}): AccuracyView {
  return { scores: realScores(), models: MODELS, pathParams: PATH_PARAMS, hidden: [], open: [], ...extra };
}

function resultsView(extra: Partial<ResultsView> = {}): ResultsView {
  return {
    runs: fx<ResultsView["runs"]>("runs_veyas.json"),
    pathDisplay: [],
    pathParams: PATH_PARAMS,
    ceiling: null,
    hints: null,
    models: MODELS,
    hidden: [],
    scenario: null,
    f6: null,
    openCard: null,
    openWarnings: null,
    savedId: null,
    canSave: false,
    repoMode: false,
    ...extra,
  };
}

const scenarioRows: ScenarioSummary[] = [
  {
    scenario_id: "01ARYZ6S41ABCDEFGHJKMNPQRS",
    status: "OK",
    title: "kurgusal senaryo",
    created_at_local: "2026-09-23T10:00:00+03:00",
    stage: "POST_BOOKBUILD_PRE_LISTING",
    ticker_label: "SNTA1",
    app_version: "0.1.0",
    models_index_sha256: "aaaaaaaabbbbbbbb",
    same_index: true,
    schema_version: "borsai.app_scenario/1",
  },
];

describe("A5-2: senaryo metni yalnız senaryo ekranlarında", () => {
  const forbidden = [TR.modeScenario, TR.modeScenarioNote];

  const neutralOrOfficial: [string, BandVM, string][] = [
    ["Doğruluk", vm({ screen: "accuracy" }), renderAccuracy(accuracyView())],
    ["Sicil · liste", vm({ screen: "registry", registryMode: "list" }), renderRegistryList(fx<RegistryView>("registry_synthetic.json"))],
    ["Sicil · arz sayfası, kayıt seçili", vm({ screen: "registry", registryMode: "record", ticker: "SNTA1", recordFile: "k.json", recordProof: "x" }), renderRecordPage(recordPage())],
    ["Sicil · arz sayfası, kayıt yok", vm({ screen: "registry", registryMode: "record", ticker: "SNTB2" }), renderRecordPage(recordPage({ ticker: { ...fx<RegistryView>("registry_synthetic.json").tickers[0], records: [] } }))],
    ["Sicil · sihirbaz", vm({ screen: "registry", registryMode: "wizard" }), ""],
    ["Ayarlar", vm({ screen: "settings" }), ""],
    ["Hakkında", vm({ screen: "about" }), ""],
  ];

  for (const [name, v, body] of neutralOrOfficial) {
    it(`${name}: SENARYO bandı ve notu hiç geçmez`, () => {
      const html = renderBand(v) + body;
      for (const w of forbidden) expect(html, `${name}: ${w}`).not.toContain(w);
    });
  }

  it("Ayarlar ve Hakkında ekran kodu senaryo metnine hiç dokunmaz", () => {
    for (const f of ["src/screens/settings.ts", "src/screens/about.ts"]) {
      const src = readFileSync(join(APP_DIR, f), "utf-8");
      expect(src, f).not.toContain("modeScenario");
    }
  });

  it("Girdi, Sonuç ve Kişisel kayıtlar bandında geçer", () => {
    for (const s of ["inputs", "results", "scenarios"] as ScreenId[]) {
      const html = renderBand(vm({ screen: s }));
      for (const w of forbidden) expect(html, `${s}: ${w}`).toContain(w);
    }
    // sonuç ekranının "SENARYO" filigranı resmi görünümde yoktur, senaryoda vardır
    expect(renderResults(resultsView())).toContain(RESULTS.watermark);
    expect(dom(renderScenarioList(scenarioRows, null)).textContent).toContain(SCENARIOS.banner);
  });
});

// ---------------------------------------------------------------- A5-3

describe("A5-3: arz sayfası bandındaki zaman kanıtı dizesi sayfadakiyle aynı", () => {
  function withProof(proof: RecordRow["push_proof"]): { row: RecordRow; page: RecordPageVM } {
    const v = fx<RegistryView>("registry_synthetic.json");
    const row: RecordRow = { ...v.tickers[0].records[0], push_proof: proof };
    const ticker = { ...v.tickers[0], records: [row, ...v.tickers[0].records.slice(1)] };
    return { row, page: recordPage({ ticker, selected: 0 }) };
  }

  it("kanıt dosyası varken bant ve sayfa aynı dizeyi taşır", () => {
    const { row, page } = withProof({ sha: "0123456789abcdef0123456789abcdef01234567", created_at: "2030-01-06T09:00:00+03:00" });
    const line = proofLine(row);
    expect(line).toBe(REGISTRY.proofFound("0123456789ab", "2030-01-06T09:00:00+03:00"));
    const band = bandFor(vm({ screen: "registry", registryMode: "record", ticker: row.file, recordFile: row.file, recordProof: line }));
    expect(bandText(band)).toBe(`${TR.modeOfficial} · ${row.file} · ${line}`);
    expect(dom(renderRecordPage(page)).querySelector(".proof")?.textContent).toBe(line);
  });

  it("kanıt yokken de aynı dize (sınıf hesaplanmaz)", () => {
    const { row, page } = withProof(null);
    const line = proofLine(row);
    expect(line).toBe(REGISTRY.proofMissing);
    // B12: gösterge yalnız kaydı ekleyen commit'in kanıtına bakar; torun commit kanıtını skorlama sayar
    // (SPEC_SCORING §5), gösterge bunu "bulunamadı" diye yanlış anlatmaz.
    expect(line).toBe("bu kaydı ekleyen commit için kanıt dosyası yok; torun commit kanıtı skorlamada değerlendirilir");
    const band = bandFor(vm({ screen: "registry", registryMode: "record", ticker: row.file, recordFile: row.file, recordProof: line }));
    expect(bandText(band)).toContain(line);
    expect(dom(renderRecordPage(page)).querySelector(".proof")?.textContent).toBe(line);
  });
});

// ---------------------------------------------------------------- A5-4

describe("A5-4: model özetinde çift ayraç yok; payda iki alt tabloda", () => {
  const root = dom(renderAccuracy(accuracyView()));

  it("model bloğu özeti '· ·' içermez; sayı parçası dosyadaki n ile", () => {
    const doc = repoScoresDoc<ScoresDoc>();
    const summaries = [...root.querySelectorAll<HTMLElement>(".model-block")];
    expect(summaries.length).toBe(doc.models.length);
    for (const block of summaries) {
      const m = doc.models.find((x) => x.model_id === block.dataset.model);
      const t = block.querySelector("summary")?.textContent ?? "";
      expect(t, t).not.toContain("· ·");
      expect(t).toBe(`${m?.model_id} · ${KIND_TEXT[m?.kind ?? ""]} · ${ACCURACY.liveCount(m?.live.n_scored ?? -1, m?.live.n_skipped ?? -1)}`);
    }
    expect(renderAccuracy(accuracyView())).not.toContain("· ·");
  });

  it("gerçek scores.json: SKIPPED alt tablosu 'yok', OUT_OF_SCOPE 19 satır", () => {
    const doc = repoScoresDoc<ScoresDoc>();
    const rows = doc.skipped ?? [];
    const oos = rows.filter((r) => r.status === "OUT_OF_SCOPE");
    const skipped = rows.filter((r) => r.status === "SKIPPED");
    expect([skipped.length, oos.length]).toEqual([0, 19]);
    const box = root.querySelector(".skipped");
    expect(box?.querySelector("summary")?.textContent).toBe(ACCURACY.denomTitle(rows.length));
    expect(box?.textContent).toContain(ACCURACY.denomSkipped(0));
    expect(box?.textContent).toContain(ACCURACY.denomOutOfScope(19));
    expect(box?.querySelector('.denom-empty[data-group="skipped"]')?.textContent).toBe(ACCURACY.none);
    expect(box?.querySelectorAll(".denom-out-of-scope tbody tr").length).toBe(19);
    expect(box?.querySelector(".denom-note")?.textContent).toBe(ACCURACY.denomNote);
  });

  it("'atlanan = 0' ile payda satır sayısı karıştırılmaz", () => {
    const live = root.querySelector('.model-block[data-model="v1_5_h99"] .panel-live h4')?.textContent ?? "";
    expect(live).toContain(ACCURACY.liveCount(6, 0));
    expect(live).not.toContain("atlanan = 19");
  });
});

// ---------------------------------------------------------------- A5-5

describe("A5-5: iki ekran aynı kart fonksiyonunu, aynı alan sırasıyla kullanır", () => {
  const labels = [CARD.what, CARD.kind, CARD.training, CARD.sha, CARD.variants, CARD.primary, CARD.prospective];

  function cardOf(root: HTMLElement, model: string): HTMLElement | null {
    return root.querySelector<HTMLElement>(`.model-card[data-model="${model}"]`);
  }

  function rowLabels(card: HTMLElement | null): string[] {
    return [...(card?.querySelectorAll("tr th") ?? [])].map((x) => x.textContent ?? "");
  }

  it("doğruluk paneli ve sonuç ekranı kartında alan kümesi ve sırası aynı", () => {
    const hints = fx<ScoreHints>("score_hints.json");
    const panel = cardOf(dom(renderAccuracy(accuracyView({ open: ["v1_5_h99"] }))), "v1_5_h99");
    const results = cardOf(dom(renderResults(resultsView({ hints, openCard: "v1_5_h99" }))), "v1_5_h99");
    expect(rowLabels(panel)).toEqual(labels);
    expect(rowLabels(results)).toEqual(labels);
  });

  it("tavan yolu modelinde iki ekranda da 'seri modeli' satırı vardır", () => {
    const withSurvival = [CARD.what, CARD.kind, CARD.survival, CARD.training, CARD.sha, CARD.variants, CARD.primary, CARD.prospective];
    const panel = cardOf(dom(renderAccuracy(accuracyView({ open: ["ceiling_path_v0"] }))), "ceiling_path_v0");
    const results = cardOf(dom(renderResults(resultsView({ openCard: "ceiling_path_v0" }))), "ceiling_path_v0");
    expect(rowLabels(panel)).toEqual(withSurvival);
    expect(rowLabels(results)).toEqual(withSurvival);
    const sid = PATH_PARAMS.find((p) => p.model_id === "ceiling_path_v0")?.survival_model_id ?? "";
    expect(panel?.textContent).toContain(sid);
    expect(results?.textContent).toContain(sid);
  });

  it("U21: model_id, eğitim n, kesim, sha ilk 8, varyant sayısı iki ekranda da kartta", () => {
    const hints = fx<ScoreHints>("score_hints.json");
    const panel = cardOf(dom(renderAccuracy(accuracyView({ open: ["v1_5_h99"] }))), "v1_5_h99");
    const results = cardOf(dom(renderResults(resultsView({ hints, openCard: "v1_5_h99" }))), "v1_5_h99");
    for (const card of [panel, results]) {
      const t = card?.textContent ?? "";
      expect(t).toContain("99 / 2026-08-19");
      expect(t).toContain("bf809859");
      expect(t).toContain(CARD.variants);
    }
    expect(panel?.dataset.model).toBe("v1_5_h99");
    expect(results?.dataset.model).toBe("v1_5_h99");
  });

  it("prospektif durum: n < 10 metni, n ≥ 10'da yalnız dosyadaki verdict", () => {
    const base: CardVM = {
      modelId: "m",
      description: null,
      kind: null,
      survival: null,
      trainingN: null,
      trainingCutoff: null,
      sha: null,
      shaCompare: null,
      variants: null,
      primary: null,
      liveN: 6,
      liveVerdict: null,
    };
    expect(dom(renderModelCard(base, CARD.caption)).textContent).toContain(CARD.liveNoVerdict("6"));
    const scored = dom(renderModelCard({ ...base, liveN: 31, liveVerdict: "geçiyor" }, CARD.caption));
    expect(scored.textContent).toContain("geçiyor");
    const none = dom(renderModelCard({ ...base, liveN: 31, liveVerdict: null }, CARD.caption));
    expect(none.textContent).not.toContain("geçiyor");
  });

  it("sha uyuşmazlığında sarı uyarı; eşitken ve tek kaynak biliniyorken yok", () => {
    const base: CardVM = {
      modelId: "v1_5_h99",
      description: null,
      kind: null,
      survival: null,
      trainingN: null,
      trainingCutoff: null,
      sha: "bf809859aaaa",
      shaCompare: "bf809859bbbb",
      variants: null,
      primary: null,
      liveN: null,
      liveVerdict: null,
    };
    expect(dom(renderModelCard(base, CARD.caption)).querySelector(".sha-scores-mismatch")).toBeNull();
    const bad = dom(renderModelCard({ ...base, shaCompare: "deadbeefcccc" }, CARD.caption));
    expect(bad.querySelector(".sha-scores-mismatch")?.textContent).toBe(CARD.shaMismatch);
    expect(dom(renderModelCard({ ...base, shaCompare: null }, CARD.caption)).querySelector(".sha-scores-mismatch")).toBeNull();
  });

  it("doğruluk panelinde sha uyuşmazlığı fixture'ı sarı uyarı çıkarır", () => {
    const v = accuracyView({ open: ["v1_5_h99"] });
    const doc = JSON.parse(JSON.stringify(v.scores?.doc)) as ScoresDoc;
    const m = doc.models.find((x) => x.model_id === "v1_5_h99");
    if (m?.card) m.card.params_sha256_8 = "deadbeef";
    const root = dom(renderAccuracy({ ...v, scores: { ...(v.scores as ScoresView), doc } }));
    const warn = root.querySelector<HTMLElement>('.sha-scores-mismatch[data-model="v1_5_h99"]');
    expect(warn?.textContent).toBe(CARD.shaMismatch);
    // gerçek dosyada uyuşmazlık yoktur
    expect(dom(renderAccuracy(v)).querySelector(".sha-scores-mismatch")).toBeNull();
  });
});

// ---------------------------------------------------------------- A5-7

describe("A5-7: rejim metni veri dosyasıyla eşleşir", () => {
  /** `data/training_table.csv`'den yıllık D1 tavan oranı; hesap TESTTE serbesttir, src/'de değil. */
  function yearly(): { year: string; k: number; n: number; pct: number }[] {
    const text = readFileSync(join(APP_DIR, "..", "data", "training_table.csv"), "utf-8").trim().split("\n");
    const head = text[0].split(",");
    const iDate = head.indexOf("first_trading_date");
    const iD1 = head.indexOf("ceiling_close_D1");
    const acc = new Map<string, { k: number; n: number }>();
    for (const line of text.slice(1)) {
      const cols = line.split(",");
      const year = cols[iDate].slice(0, 4);
      const cur = acc.get(year) ?? { k: 0, n: 0 };
      cur.n += 1;
      if (cols[iD1] === "1") cur.k += 1;
      acc.set(year, cur);
    }
    return [...acc.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([year, { k, n }]) => ({ year, k, n, pct: Math.round((100 * k) / n) }));
  }

  it("yıllık oran ve n metindekilerle birebir", () => {
    const rows = yearly();
    expect(rows.map((r) => r.year)).toEqual(["2023", "2024", "2025", "2026"]);
    expect(rows.reduce((a, r) => a + r.n, 0)).toBe(99);
    const parts = rows.map((r, i) => (i === 0 ? `%${r.pct} (${r.k}/${r.n}; 2023 Eyl–Ara)` : `%${r.pct} (${r.k}/${r.n})`));
    expect(RESULTS.regime).toContain(parts.join(" → "));
  });

  it("2023 yalnız Eylül–Aralık; kaynak etiketi veri dosyası", () => {
    const text = readFileSync(join(APP_DIR, "..", "data", "training_table.csv"), "utf-8").trim().split("\n");
    const head = text[0].split(",");
    const iDate = head.indexOf("first_trading_date");
    const dates = text.slice(1).map((l) => l.split(",")[iDate]).filter((d) => d.startsWith("2023")).sort();
    expect(dates[0].slice(5, 7)).toBe("09");
    expect(dates[dates.length - 1].slice(5, 7)).toBe("12");
    expect(RESULTS.regime).toContain("data/training_table.csv");
    expect(RESULTS.regime).not.toContain("AUDIT");
  });

  it("rejim metni sonuç ve doğruluk ekranında (U23)", () => {
    expect(dom(renderResults(resultsView())).querySelector('[data-role="regime"]')?.textContent).toBe(RESULTS.regime);
    expect(dom(renderAccuracy(accuracyView())).querySelector('[data-role="regime"]')?.textContent).toBe(RESULTS.regime);
  });
});
