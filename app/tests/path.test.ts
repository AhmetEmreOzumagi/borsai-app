// @vitest-environment jsdom
// U48 (Grup A tavan yolu sütunları + Grup C) ve U49 ("Getiri (koşullu)" sekmesi), SPEC_APP EK 2 §4.
// Bütün sayılar Rust komutlarının gerçek çıktısıdır (fixture'ları src-tauri/tests/stage2.rs ve
// stage3.rs üretir); bu dosyada elle yazılmış model sayısı yoktur.
import { describe, expect, it } from "vitest";

import { COND, PATH, PATH_COND, REGISTRY } from "../src/i18n/tr";
import { renderConditional, type ConditionalVM, type PathCondVM } from "../src/render/ceiling";
import { pct0, pctSigned1, pyRepr } from "../src/render/format";
import { renderRecordPage, type RecordPageVM } from "../src/render/registry";
import { groupA, renderGroupC, renderResults, type ResultsView } from "../src/render/results";
import type {
  CeilingDisplay,
  ModelInfo,
  ModelRun,
  PathConditional,
  PathHorizon,
  PathDisplayRow,
  PathParamsInfo,
  RecordCeiling,
  RegistryView,
  StreakView,
} from "../src/types";
import { dom, fx } from "./helpers";

const params = () => fx<PathParamsInfo[]>("path_params.json");

function view(runsFile: string, dispFile: string, extra: Partial<ResultsView> = {}): ResultsView {
  return {
    runs: fx<ModelRun[]>(runsFile),
    pathDisplay: fx<PathDisplayRow[]>(dispFile),
    pathParams: params(),
    ceiling: null,
    hints: null,
    models: fx<ModelInfo[]>("app_models.json"),
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

// ---------------------------------------------------------------- U48

describe("U48: Grup A tavan yolu sütunları", () => {
  const v = view("runs_veyas.json", "path_display_veyas.json");
  const root = dom(renderResults(v));
  const disp = fx<PathDisplayRow[]>("path_display_veyas.json");

  it("sütun sırası: doğrusal/PB/market20 → tavan yolu (INDEX sırası) → basit kurallar", () => {
    const ids = groupA(v.runs).map((r) => r.model_id);
    const kinds = groupA(v.runs).map((r) => r.kind);
    const firstPath = kinds.indexOf("ceiling_path");
    const lastPath = kinds.lastIndexOf("ceiling_path");
    const firstRule = kinds.indexOf("rule");
    expect(firstPath).toBeGreaterThan(0);
    expect(lastPath).toBeLessThan(firstRule);
    expect(kinds.slice(firstPath, lastPath + 1).every((k) => k === "ceiling_path")).toBe(true);
    expect(ids.slice(firstPath, lastPath + 1)).toEqual(["ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0"]);
  });

  it("hücre: medyan + rozet, %10–%90 bandı, p_up + yön oku, S_h", () => {
    const run = v.runs.find((r) => r.model_id === "ceiling_path_v0@INF");
    const c = (run?.output as unknown as Record<string, PathHorizon>).D1;
    const cell = root.querySelector<HTMLElement>('td.cell[data-model="ceiling_path_v0@INF"][data-h="D1"]');
    expect(cell?.querySelector(".ret")?.textContent).toContain(pctSigned1(c.return));
    expect(cell?.querySelector(".ret")?.textContent).toContain(PATH.medianBadge);
    expect(cell?.querySelector(".band")?.textContent).toBe(PATH.bandLabel(pctSigned1(c.q10), pctSigned1(c.q90)));
    expect(cell?.querySelector(".pup")?.textContent).toBe(`${pct0(c.p_up)} ↑`);
    expect(cell?.querySelector(".s-h")?.textContent).toBe(`S_1 ${pct0(c.S_h)}`);
    // tooltip ham değerler (pyRepr): return, p_up, mean, q10, q90, S_h, n_atoms
    expect(cell?.title).toContain(`n_atoms=${c.n_atoms}`);
    expect(cell?.title).toContain(`mean=${pyRepr(c.mean)}`);
  });

  it("fiyat kuralı: medyan limit atomuysa C_h metni + 'limit yolu', değilse '≈'", () => {
    const d = disp.find((x) => x.model_id === "ceiling_path_v0@INF");
    const onPath = d?.cells[0];
    const off = d?.cells.find((x) => !x.on_limit_path && x.approx_price !== null);
    expect(onPath?.on_limit_path).toBe(true);
    const cell = root.querySelector<HTMLElement>('td.cell[data-model="ceiling_path_v0@INF"][data-h="D1"] .price-row');
    expect(cell?.textContent).toContain(`${onPath?.c_text} TL`);
    expect(cell?.textContent).toContain(PATH.limitBadge);
    // h = 5'te medyan limit atomu değil: yaklaşık fiyat, gri ve tooltip'li
    const off5 = root.querySelector<HTMLElement>('td.cell[data-model="ceiling_path_v0@INF"][data-h="D5"] .price-row .approx');
    expect(off5?.textContent).toContain("≈");
    expect(off5?.title).toBe(PATH.approxTooltip);
    expect(off).toBeDefined();
  });

  it("RET bloğu: VEYAS'ta ceiling_path_v0 · F3_MISSING", () => {
    const block = root.querySelector<HTMLElement>('.refusal[data-model="ceiling_path_v0"]');
    expect(block?.dataset.code).toBe("F3_MISSING");
    expect(block?.textContent).toContain("RET · F3_MISSING");
    expect(block?.textContent).not.toMatch(/%\d/);
  });

  it("sütun başlığında 'S: <seri modeli> ile aynı' notu (Grup B'de çizilmez)", () => {
    const p = params().find((x) => x.model_id === "ceiling_path_v0@INF");
    const th = root.querySelector<HTMLElement>('th.model-col[data-model="ceiling_path_v0@INF"] .survival-note');
    expect(th?.textContent).toBe(PATH.survivalNote(p?.survival_model_id ?? ""));
    expect(root.querySelector('td.cell.s[data-model="ceiling_path_v0@INF"]')).toBeNull();
  });
});

describe("U48: Grup C — tavan yolu getiri dağılımı", () => {
  const v = view("runs_netgl.json", "path_display_netgl.json");
  const root = dom(renderGroupC(v));
  const disp = fx<PathDisplayRow[]>("path_display_netgl.json");

  it("tablo 10 satır (h = 1..10) ve sütun başına tavan yolu modeli", () => {
    const rows = [...root.querySelectorAll(".path-table tbody tr")];
    expect(rows.length).toBe(10);
    const heads = [...root.querySelectorAll<HTMLElement>(".path-table th.model-col")].map((x) => x.dataset.model);
    expect(heads).toEqual(v.runs.filter((r) => r.kind === "ceiling_path").map((r) => r.model_id));
    const cell = root.querySelector<HTMLElement>('.path-table td.cell[data-model="ceiling_path_v0"][data-h="D3"]');
    const c = (v.runs.find((r) => r.model_id === "ceiling_path_v0")?.output as unknown as Record<string, PathHorizon>).D3;
    expect(cell?.textContent).toContain(pctSigned1(c.return));
    expect(cell?.textContent).toContain(String(c.n_atoms));
  });

  it("yelpaze grafiği: model başına band + q50 + rho (limit yolu kesikli)", () => {
    const svg = root.querySelector("svg.fan-chart");
    expect(svg).not.toBeNull();
    const n = v.runs.filter((r) => r.kind === "ceiling_path" && r.status === "PREDICTED").length;
    expect(svg?.querySelectorAll("polygon[data-band]").length).toBe(n);
    expect(svg?.querySelectorAll('path[data-role="q50"]').length).toBe(n);
    const rho = [...(svg?.querySelectorAll('path[data-role="rho"]') ?? [])];
    expect(rho.length).toBe(n);
    expect(rho[0].getAttribute("stroke-dasharray")).toBe("5 4");
  });

  it("limit yolu satırı: arz fiyatı, D1 baz fiyatı, adım ve C_1..C_10 metinleri AYNEN", () => {
    const d = disp.find((x) => x.model_id === "ceiling_path_v0");
    const box = root.querySelector<HTMLElement>('.limit-path[data-model="ceiling_path_v0"]');
    expect(box?.textContent).toContain(PATH.limitPrice(d?.ipo_price ?? ""));
    expect(box?.textContent).toContain(PATH.limitTick(d?.tick ?? ""));
    const items = [...(box?.querySelectorAll(".c-list li") ?? [])].map((x) => x.textContent);
    expect(items.length).toBe(10);
    d?.c.forEach((c, i) => expect(items[i]).toContain(`${c} TL`));
  });

  it("hücre notu: kırılma sonrası hücreler, kesim ve N_MIN", () => {
    const p = params().find((x) => x.model_id === "ceiling_path_v0");
    const details = root.querySelector<HTMLElement>('.post-break-cells[data-model="ceiling_path_v0"]');
    expect(details?.querySelector(".cells-note")?.textContent).toBe(
      PATH.cellsNote(String(p?.n_ipo), p?.cutoff_date ?? "", p?.n_min ?? 0),
    );
    expect((details?.querySelectorAll("li").length ?? 0) > 10).toBe(true);
  });

  it("POST_BREAK_INSUFFICIENT: hücre '—' ve T-2 metni tooltip'te", () => {
    const iv = view("runs_path_insufficient.json", "path_display_insufficient.json");
    const r = dom(renderGroupC(iv));
    const cells = [...r.querySelectorAll<HTMLElement>(".path-table td.cell")];
    expect(cells.length).toBe(10);
    expect(cells.every((c) => c.textContent === "—")).toBe(true);
    expect(cells[0].title).toBe(PATH.insufficient);
    expect(r.querySelector(".path-table")?.textContent).not.toMatch(/%\d/);
  });

  it("INDEX'te tavan yolu modeli yoksa bölüm çizilmez", () => {
    expect(renderGroupC({ ...view("runs_netgl.json", "path_display_netgl.json"), runs: [] })).toBe("");
  });
});

// ---------------------------------------------------------------- U49

function condVM(extra: Partial<ConditionalVM> = {}): ConditionalVM {
  return {
    streak: fx<StreakView>("streak_pending.json"),
    cond: fx<CeilingDisplay>("ceiling_netgl_j3.json"),
    jSelected: 3,
    tab: "return",
    hidden: [],
    declared: Array<boolean>(10).fill(false),
    declDropped: false,
    pathAvailable: true,
    pathCond: [],
    pathParams: params(),
    recordWithoutPath: false,
    ...extra,
  };
}

const cond = (name: string): PathCondVM => ({ model_id: "ceiling_path_v0", result: fx<PathConditional>(name), error: null });

describe("U49: 'Getiri (koşullu)' sekmesi", () => {
  it("durum 1 (j = 3): gerçekleşen günler + koşullu satırlar; S_cond kayıttaki S'ten (0.5^(k−j))", () => {
    const c = cond("path_cond_record_j3.json");
    const root = dom(renderConditional(condVM({ pathCond: [c] })));
    const card = root.querySelector<HTMLElement>('.path-cond[data-model="ceiling_path_v0"]');
    expect(card?.dataset.state).toBe("STREAK_ONGOING");
    expect(card?.querySelector(".cond-state")?.textContent).toContain(PATH_COND.stateOngoing(3));
    expect(card?.querySelector(".hypo")).toBeNull();
    const rows = [...(card?.querySelectorAll<HTMLElement>(".cond-return-table tr") ?? [])];
    expect(rows.length).toBe(10);
    expect(rows.filter((r) => r.classList.contains("realized")).length).toBe(3);
    // S_h sütunu = S_cond: D4 %50, D5 %25 … (kayıtta S = 0.5^k)
    expect(rows[3].querySelector(".s-h")?.textContent).toBe("%50");
    expect(rows[4].querySelector(".s-h")?.textContent).toBe("%25");
    expect(card?.querySelector(".s-j")?.textContent).toContain(PATH_COND.sJ(3));
    // gerçekleşen getiri kapanıştan (kayıt değil): D1 satırı "gerçekleşti" rozetiyle
    expect(rows[0].textContent).toContain(PATH_COND.realized);
    expect(rows[0].querySelector(".realized-cell")?.textContent).toContain("+%10.0");
  });

  it("kullanılan kapanışlar listelenir: dosyadan gelen h'ler ve seans tarihi", () => {
    const c = cond("path_cond_record_j3.json");
    const root = dom(renderConditional(condVM({ pathCond: [c] })));
    const items = [...root.querySelectorAll<HTMLElement>(".cond-closes li")];
    expect(items.length).toBe(3);
    expect(items.every((x) => x.dataset.origin === "FILE")).toBe(true);
    const first = c.result?.closes[0];
    expect(items[0].textContent).toBe(PATH_COND.closeFile(1, first?.close ?? "", first?.session_date ?? ""));
  });

  it("varsayımsal j > resmi j: 'varsayımsal j' etiketi ve limit yolu kapanış varsayımı", () => {
    const c = cond("path_cond_hypothetical_j5.json");
    const root = dom(renderConditional(condVM({ jSelected: 5, pathCond: [c] })));
    expect(root.querySelector(".path-cond .hypo")?.textContent).toBe(PATH_COND.hypothetical);
    const assumed = [...root.querySelectorAll<HTMLElement>('.cond-closes li[data-origin="LIMIT_PATH"]')];
    expect(assumed.length).toBe(2);
    expect(assumed[0].textContent).toBe(PATH_COND.closeAssumed(4, c.result?.closes[3].close ?? ""));
  });

  it("durum 2 (t = 2): kırılma sonrası notu, S_h yok, D_{t+2}… koşullanmaz", () => {
    const broken = fx<StreakView>("streak_broken.json");
    const c = cond("path_cond_break_t2.json");
    const root = dom(renderConditional(condVM({ streak: broken, jSelected: 2, pathCond: [c] })));
    const card = root.querySelector<HTMLElement>(".path-cond");
    expect(card?.dataset.state).toBe("AFTER_BREAK");
    expect(card?.querySelector(".cond-state")?.textContent).toContain(PATH_COND.stateBreak(2));
    expect(card?.querySelector(".after-break-note")?.textContent).toBe(c.result?.result.note);
    expect(card?.querySelector(".s-j")).toBeNull();
    expect(card?.querySelectorAll(".cond-return-table .s-h").length).toBe(0);
  });

  it("limit yolundan sapan kapanış: sarı kutu, hesap yine gösterilir", () => {
    const c = cond("path_cond_mismatch.json");
    const root = dom(renderConditional(condVM({ pathCond: [c] })));
    const box = root.querySelector<HTMLElement>(".limit-mismatch");
    const m = c.result?.mismatch;
    expect(box?.dataset.t).toBe(String(m?.t));
    expect(box?.textContent).toContain(PATH_COND.mismatch(m?.t ?? 0, m?.close ?? "", m?.c ?? ""));
    expect(root.querySelectorAll(".cond-return-table tr").length).toBe(10);
  });

  it("beyan resmi verinin önündeyse kart boş: 'resmi kapanış bekleniyor' (U52)", () => {
    const declared = [false, false, false, true, false, false, false, false, false, false];
    const root = dom(renderConditional(condVM({ declared, pathCond: [cond("path_cond_record_j3.json")] })));
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    expect(root.querySelector(".path-cond")).toBeNull();
    expect(root.textContent).not.toMatch(/%\d/);
  });

  it("INDEX'te tavan yolu modeli yoksa 'henüz yok' metni kalır", () => {
    const root = dom(renderConditional(condVM({ pathAvailable: false, pathParams: [] })));
    expect(root.querySelector(".return-none")?.textContent).toBe(COND.returnNone);
  });

  it("kayıt Faz 4 modellerini içermiyorsa uyarı yazılır", () => {
    const root = dom(renderConditional(condVM({ recordWithoutPath: true })));
    expect(root.querySelector(".record-no-path")?.textContent).toBe(PATH_COND.noRecordModels);
    expect(root.querySelector(".path-cond")).toBeNull();
  });

  it("kayıt farklı parametreyle yazılmışsa hata kutusu (model yeniden çalıştırılmaz)", () => {
    const err = { model_id: "ceiling_path_v0", result: null, error: { code: "PATH_PARAMS_SHA_MISMATCH", message: "x", detail: "kayıt sha … ≠ gömülü sha …" } };
    const root = dom(renderConditional(condVM({ pathCond: [err] })));
    expect(root.querySelector<HTMLElement>(".error-box")?.dataset.code).toBe("PATH_PARAMS_SHA_MISMATCH");
    expect(root.querySelector(".cond-return-table")).toBeNull();
  });

  it("ret eden modelde koşullu getiri de yok", () => {
    const root = dom(renderConditional(condVM({ pathCond: [{ model_id: "ceiling_path_v0", result: null, error: null }] })));
    expect(root.querySelector(".cond-refused")?.textContent).toBe(COND.returnRefused);
  });
});

describe("U49: resmi arz sayfası (kayıt kaynağı)", () => {
  function page(ceiling: RecordCeiling | null, extra: Partial<RecordPageVM> = {}): RecordPageVM {
    const v = fx<RegistryView>("registry_synthetic.json");
    return {
      ticker: v.tickers[0],
      selected: 0,
      ceiling,
      streak: fx<StreakView>("streak_pending.json"),
      jSelected: 3,
      tab: "return",
      hidden: [],
      declared: Array<boolean>(10).fill(false),
      declDropped: false,
      pathDisplay: fx<PathDisplayRow[]>("path_display_record.json"),
      pathParams: params(),
      pathCond: [cond("path_cond_record_j3.json")],
      models: fx<ModelInfo[]>("app_models.json"),
      hints: null,
      raw: null,
      cancelReason: "",
      cancelDone: null,
      today: v.today_istanbul,
      ...extra,
    };
  }

  it("kayıttaki tavan yolu modelleri Grup A/C ile aynı render; kaynak satırı kayıt dosyası", () => {
    const rc = fx<RecordCeiling>("record_ceiling_path_j3.json");
    const root = dom(renderRecordPage(page(rc)));
    expect(root.querySelector(".record-path")).not.toBeNull();
    expect(root.querySelectorAll(".record-path .group-a").length).toBe(1);
    expect(root.querySelectorAll(".record-path .group-c .path-table tbody tr").length).toBe(10);
    expect(root.querySelector(".sha-mismatch")).toBeNull();
    // resmi görünüm: "SENARYO" filigranı ve senaryo tooltip'i yok (§3c)
    expect(root.querySelector(".record-path .watermark")).toBeNull();
    const cell = root.querySelector<HTMLElement>('.record-path td.cell.path-cell');
    expect(cell?.title).not.toContain("senaryo");
    const c = fx<PathConditional>("path_cond_record_j3.json");
    expect(root.querySelector(".path-cond .source-line")?.textContent).toBe(
      PATH_COND.sourceRecord(c.source_file ?? "", c.params_sha256.slice(0, 8)),
    );
  });

  it("16 modelli kayıt: 'kayıt Faz 4 modellerini içermiyor'", () => {
    const rc = fx<RecordCeiling>("record_ceiling_j3.json");
    expect(rc.path_models.length).toBe(0);
    const root = dom(renderRecordPage(page(rc, { pathCond: [] })));
    expect(root.querySelector(".record-path")).toBeNull();
    expect(root.querySelector(".record-no-path")?.textContent).toBe(REGISTRY.pathMissing);
  });
});
