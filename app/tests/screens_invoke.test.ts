// @vitest-environment jsdom
// B2 (FAZ3_APP_AUDIT): ekran mantığı (`screens/results.ts` derive + pathConditional,
// `screens/registry.ts` loadRecord + recordPathConditional) sahte `invoke` ile gerçek `mount` ve
// gerçek tıklamalarla koşturulur; Rust'a giden her komut ve argümanı yakalanır (gerçek sayaç).
//
// Fixture: kurgusal SNTB1 (`tests/fixtures/outcomes/sntb1/`: D1–D2 OK-tavan, D3 PENDING → resmi
// j = 2; `ui/streak_sntb1.json` bu dosyanın Rust `streak_view` çıktısıdır, stage2.rs üretir) +
// beyan "D3 seri sürüyor" (beyanlı j = 3). Beklenen (U52-5, U38, U49): koşullu komutlara giden j
// resmi j'dir (ya da kullanıcının açıkça SEÇTİĞİ varsayımsal j), beyan hiçbir komuta geçmez,
// `streak_view` tek argümanlıdır, sicil akışında `predict_all` hiç çağrılmaz.
import { beforeEach, describe, expect, it, vi } from "vitest";

type Call = { cmd: string; args: Record<string, unknown> };
const h = vi.hoisted(() => ({
  calls: [] as { cmd: string; args: Record<string, unknown> }[],
  respond: (_cmd: string, _args: Record<string, unknown>): unknown => {
    throw new Error("respond atanmadı");
  },
}));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string, args: Record<string, unknown> = {}) => {
    h.calls.push({ cmd, args: structuredClone(args) });
    return h.respond(cmd, args);
  }),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn(async () => null), save: vi.fn(async () => null) }));

import { mount as mountRegistry } from "../src/screens/registry";
import { mount as mountResults } from "../src/screens/results";
import { store } from "../src/state";
import type { ConfigView, ModelRun, RecordCeiling, RegistryView, StreakView } from "../src/types";
import { fx } from "./helpers";

const STREAK = fx<StreakView>("streak_sntb1.json");
const OFFICIAL_J = 2;
const DECL_WORDS = ["declared", "declDropped", "observed_streak_user", "userDays"];

/** Komut → Rust'ın gerçek çıktısından üretilmiş fixture (içerik değil, argüman sınanıyor). */
function respond(cmd: string, args: Record<string, unknown>): unknown {
  switch (cmd) {
    case "streak_view":
      return { ...STREAK, ticker: args.ticker ?? null };
    case "ceiling_display": {
      const j = args.j as number;
      return fx(`ceiling_netgl_j${[0, 2, 3, 10].includes(j) ? j : 2}.json`);
    }
    case "path_display":
      return fx("path_display_netgl.json");
    case "path_params":
      return fx("path_params.json");
    case "path_conditional":
      return fx((args.source as { kind: string }).kind === "RECORD" ? "path_cond_record_j2.json" : "path_cond_output_j3.json");
    case "registry_view":
      return fx("registry_synthetic.json");
    case "record_ceiling":
      return fx<RecordCeiling>("record_ceiling_path_j3.json");
    case "predict_all":
      return fx("runs_netgl.json");
    // Tavan serisi kartı (EK 3 §5): beyan parametresi yok; j resmi ya da seçilen j (U52-5 karta genişler)
    case "ceiling_summary":
      return fx((args.j as number) === 0 ? "summary_closed_netgl_j0.json" : "summary_closed_netgl_j2.json");
    case "record_summary":
      return fx("summary_record_j2.json");
    default:
      throw new Error(`beklenmeyen komut: ${cmd}`);
  }
}

async function settle(): Promise<void> {
  for (let i = 0; i < 30; i += 1) await new Promise((r) => setTimeout(r, 0));
}

function of(cmd: string): Call[] {
  return h.calls.filter((c) => c.cmd === cmd);
}

/** Argümanların hiçbir derinliğinde beyan alanı adı geçmez. */
function declKeys(v: unknown, path = ""): string[] {
  if (Array.isArray(v)) return v.flatMap((x, i) => declKeys(x, `${path}[${i}]`));
  if (v && typeof v === "object") {
    return Object.entries(v).flatMap(([k, x]) => [
      ...(DECL_WORDS.includes(k) ? [`${path}.${k}`] : []),
      ...declKeys(x, `${path}.${k}`),
    ]);
  }
  return [];
}

function click(root: HTMLElement, selector: string): void {
  const el = root.querySelector<HTMLElement>(selector);
  expect(el, selector).not.toBeNull();
  el?.click();
}

const ctx = { navigate: vi.fn(), refreshShell: vi.fn() };
const D3 = [false, false, true, false, false, false, false, false, false, false];

beforeEach(() => {
  h.calls.length = 0;
  h.respond = respond;
  store.info = null;
  store.hints = null;
  store.config = { repo_mode: true } as ConfigView;
});

describe("fixture: resmi j", () => {
  it("SNTB1 şeridinde resmi j = 2, D3 PENDING (beyan bu j'yi değiştirmez)", () => {
    expect(STREAK.j_observed).toBe(OFFICIAL_J);
    expect(STREAK.days[2].file).toBe("PENDING");
  });
});

/** Koşullu komutlara giden j: tavan eğrisi (`ceiling_display`/`record_ceiling`) ve getiri sekmesi açıksa
 * `path_conditional`. Hepsi `j`'ye eşit olmalı. */
function expectJ(ceilingCmd: "ceiling_display" | "record_ceiling", j: number, withPath: boolean): void {
  const ceil = of(ceilingCmd).filter((c) => ceilingCmd === "record_ceiling" || c.args.j !== 0);
  expect(ceil.length, `${ceilingCmd} çağrısı`).toBeGreaterThan(0);
  expect(ceil.map((c) => c.args.j), `${ceilingCmd} j`).toEqual(ceil.map(() => j));
  const pc = of("path_conditional");
  if (!withPath) {
    expect(pc.length, "tavan sekmesinde path_conditional çağrılmaz").toBe(0);
    return;
  }
  expect(pc.length, "path_conditional çağrısı").toBeGreaterThan(0);
  expect(pc.map((c) => c.args.jOrT), "path_conditional jOrT").toEqual(pc.map(() => j));
}

/** Tıkla, yenilemeyi bekle; yalnız bu adımın çağrıları kalır. */
async function step(root: HTMLElement, selector: string): Promise<void> {
  h.calls.length = 0;
  click(root, selector);
  await settle();
}

async function selectJ(root: HTMLElement, j: number): Promise<void> {
  const sel = root.querySelector<HTMLSelectElement>("[data-action=select-j]");
  expect(sel, "j seçici").not.toBeNull();
  if (!sel) return;
  h.calls.length = 0;
  sel.value = String(j);
  sel.dispatchEvent(new Event("change", { bubbles: true }));
  await settle();
}

function noDeclInArgs(): void {
  expect(h.calls.flatMap((c) => declKeys(c.args).map((k) => `${c.cmd}${k}`))).toEqual([]);
  for (const c of of("streak_view")) expect(Object.keys(c.args), "streak_view tek argüman").toEqual(["ticker"]);
}

const DECLARE = (d: number) => `[data-action=declare][data-h='${d}']`;
const CLEAR = "[data-action=clear-declarations]";
const TAB_RETURN = "[data-action=cond-tab][data-tab=return]";
const TAB_CEILING = "[data-action=cond-tab][data-tab=ceiling]";

describe("sonuç ekranı (screens/results.ts: derive, pathConditional)", () => {
  function setup(): HTMLElement {
    store.results = {
      runs: fx<ModelRun[]>("runs_netgl.json"),
      inputs: { ipo_price_tl: "25.52" },
      inputDates: {},
      stage: "POST_BOOKBUILD_PRE_LISTING",
      tickerLabel: "SNTB1",
      f6: { value: null, refusal: null, origin: "NONE", S0_date: null, S20_date: null, xu100_sha256: null, ref_date: null },
      source: "FORM",
      scenario: null,
      savedId: null,
    };
    store.view = { hidden: [], openCard: null, openWarnings: null, declared: [...D3], declDropped: false, jSelected: null, tab: "ceiling" };
    const root = document.createElement("div");
    mountResults(root, ctx);
    return root;
  }

  it("açılış (D3 beyanlı): koşulsuz j = 0, koşullu ceiling_display resmi j; streak_view tek argüman", async () => {
    setup();
    await settle();
    expect(of("ceiling_display")[0].args.j, "koşulsuz görünüm").toBe(0);
    expectJ("ceiling_display", OFFICIAL_J, false);
    expect(store.view.declared[2]).toBe(true);
    noDeclInArgs();
  });

  it("beyan aç/kapa (D4, D3), getiri sekmesi, temizle: her yenilemede j resmi j", async () => {
    const root = setup();
    await settle();
    await step(root, DECLARE(4));
    expectJ("ceiling_display", OFFICIAL_J, false);
    await step(root, DECLARE(3));
    expectJ("ceiling_display", OFFICIAL_J, false);
    await step(root, DECLARE(3));
    expectJ("ceiling_display", OFFICIAL_J, false);
    await step(root, TAB_RETURN);
    expect(store.view.declared.filter((x) => x).length).toBe(2);
    expectJ("ceiling_display", OFFICIAL_J, true);
    // OUTPUT kaynağı: çıktı ve parametre sha'sı çalıştırılan modelden (B8 ile zorunlu)
    const runs = store.results?.runs ?? [];
    for (const c of of("path_conditional")) {
      const src = c.args.source as { kind: string; params_sha256: string | null };
      expect(src.kind).toBe("OUTPUT");
      expect(src.params_sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(src.params_sha256).toBe(runs.find((r) => r.model_id === c.args.modelId)?.params_sha256);
    }
    noDeclInArgs();
    await step(root, TAB_CEILING);
    await step(root, CLEAR);
    expectJ("ceiling_display", OFFICIAL_J, false);
    noDeclInArgs();
  });

  it("SEÇİLEN varsayımsal j (5) komuta aynen gider; sonra girilen beyan eklenmez", async () => {
    const root = setup();
    await settle();
    await step(root, CLEAR);
    await selectJ(root, 5);
    expectJ("ceiling_display", 5, false);
    await step(root, DECLARE(3));
    expectJ("ceiling_display", 5, false);
    await step(root, TAB_RETURN);
    expectJ("ceiling_display", 5, true);
    noDeclInArgs();
  });
});

describe("sicil ekranı / arz sayfası (screens/registry.ts: loadRecord, recordPathConditional)", () => {
  function setup(): HTMLElement {
    const view = fx<RegistryView>("registry_synthetic.json");
    const t = view.tickers[0];
    expect(t.records[0].record_type).toBe("PREDICTION");
    Object.assign(store.registry, {
      mode: "record",
      view: null,
      ticker: t.ticker,
      selected: 0,
      ceiling: null,
      streak: null,
      pathDisplay: [],
      pathParams: [],
      pathCond: [],
      jSelected: null,
      tab: "ceiling",
      declared: [...D3],
      declDropped: false,
      raw: null,
      cancelReason: "",
      cancelDone: null,
      error: null,
    });
    const root = document.createElement("div");
    mountRegistry(root, ctx);
    return root;
  }

  function recordSource(): void {
    for (const c of of("path_conditional")) {
      const src = c.args.source as { kind: string; output: unknown; params_sha256: unknown };
      expect([src.kind, src.output, src.params_sha256]).toEqual(["RECORD", null, null]);
    }
  }

  it("arz sayfası açılışı (D3 beyanlı): record_ceiling resmi j; predict_all 0 çağrı", async () => {
    setup();
    await settle();
    expect(of("registry_view").length).toBe(1);
    expectJ("record_ceiling", OFFICIAL_J, false);
    expect(of("predict_all").length, "predict_all çağrı sayısı (U38/U49)").toBe(0);
    noDeclInArgs();
  });

  it("beyan aç/kapa, getiri sekmesi, temizle: j resmi j, predict_all her adımda 0", async () => {
    const root = setup();
    await settle();
    for (const [sel, withPath] of [
      [DECLARE(4), false],
      [DECLARE(3), false],
      [DECLARE(3), false],
      [TAB_RETURN, true],
      [TAB_CEILING, false],
      [CLEAR, false],
    ] as [string, boolean][]) {
      await step(root, sel);
      expectJ("record_ceiling", OFFICIAL_J, withPath);
      recordSource();
      expect(of("predict_all").length, `${sel}: predict_all`).toBe(0);
      noDeclInArgs();
    }
  });

  it("SEÇİLEN varsayımsal j (5) aynen gider; sonra girilen beyan eklenmez; predict_all 0", async () => {
    const root = setup();
    await settle();
    await step(root, CLEAR);
    await selectJ(root, 5);
    expectJ("record_ceiling", 5, false);
    await step(root, DECLARE(3));
    expectJ("record_ceiling", 5, false);
    await step(root, TAB_RETURN);
    expectJ("record_ceiling", 5, true);
    recordSource();
    expect(of("predict_all").length).toBe(0);
    noDeclInArgs();
  });
});
