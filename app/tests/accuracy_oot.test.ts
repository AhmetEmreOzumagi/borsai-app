// @vitest-environment jsdom
// "Zaman-dışı test (eski kohort)" paneli (SPEC_APP EK 3 §7; U71–U75; K-P3-1, K-P3-2, K-P3-3). Görünümler Rust'ın gerçek
// okuyucusundan (`src-tauri/tests/oot_panel.rs` → fixtures/ui/scores_oot_panel_{synth,real}.json); burada yalnız render
// sınanır. Kasa (SEALED) kodu hiçbir yerde basılmaz: gerçek dosya testi kohort dosyasının SEALED kodlarını yalnız sayar.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { ACCURACY, VERDICT, VERDICT_OOT_SUFFIX } from "../src/i18n/tr";
import { renderAccuracy, type AccuracyView } from "../src/render/accuracy";
import { renderOotPanel, type OotPanelVM } from "../src/render/accuracy_oot";
import type { ModelInfo, OotModelDetail, OotPanelView, PathParamsInfo } from "../src/types";
import { APP_DIR, dom, fx, scoresView, split } from "./helpers";

const T = ACCURACY.oot;

interface Bundle {
  view: OotPanelView;
  details?: Record<string, OotModelDetail>;
}

const SYNTH = fx<Record<string, Bundle>>("scores_oot_panel_synth.json");

/** Fixture'daki görünüm + her blokta ayrıntısı fixture'da olan (yoksa birincil hücresi olan ilk) model; ekranın seçimi gibi. */
function vmOf(b: Bundle): OotPanelVM {
  const selected: Record<string, string> = {};
  const details: Record<string, OotModelDetail | null> = {};
  for (const blk of b.view.blocks) {
    const m = blk.models.find((x) => b.details?.[`${blk.key}/${x.model_id}`] !== undefined && x.primary !== null)
      ?? blk.models.find((x) => x.primary !== null) ?? blk.models[0];
    if (!m) continue;
    selected[blk.key] = m.model_id;
    details[blk.key] = b.details?.[`${blk.key}/${m.model_id}`] ?? null;
  }
  return { view: b.view, selected, details };
}

function panel(name: string): HTMLElement {
  return dom(renderOotPanel(vmOf(SYNTH[name])));
}

const text = (e: Element | null | undefined) => (e?.textContent ?? "").trim();

describe("U71: üç terazi ayrı; zaman-dışı bölüm model bloklarının içinde değil", () => {
  const av: AccuracyView = {
    scores: scoresView("n35"),
    models: fx<ModelInfo[]>("app_models.json"),
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    hidden: [],
    open: [],
    oot: vmOf(SYNTH.ok),
  };
  const root = dom(renderAccuracy(av));

  it("üç sınıf var ve hiçbir öğe ikisini birden taşımaz; .panel-oot model bloğunun içinde değil", () => {
    for (const c of [".panel-backtest", ".panel-live", ".panel-oot"]) expect(root.querySelectorAll(c).length, c).toBeGreaterThan(0);
    for (const pair of [".panel-backtest.panel-live", ".panel-backtest.panel-oot", ".panel-live.panel-oot"]) {
      expect(root.querySelectorAll(pair).length, pair).toBe(0);
    }
    const oot = root.querySelector(".panel-oot");
    expect(oot?.closest(".model-block")).toBeNull();
    expect(oot?.querySelector(".panel-backtest, .panel-live")).toBeNull();
    expect(root.querySelector(".model-block .panel-oot")).toBeNull();
  });

  it("her zaman-dışı hücre satırı yalnız .panel-oot içinde (data-scale = oot)", () => {
    const rows = [...root.querySelectorAll<HTMLElement>('tr[data-scale="oot"]')];
    expect(rows.length).toBeGreaterThan(0);
    for (const r of rows) expect(r.closest(".panel-oot")).not.toBeNull();
    for (const r of root.querySelectorAll<HTMLElement>("tr.cell-row")) {
      if (r.dataset.scale !== "oot") expect(r.closest(".panel-oot")).toBeNull();
    }
  });

  it("scalesNote üç teraziyi sayar", () => {
    expect(ACCURACY.scalesNote).toContain("geçmiş veri testi");
    expect(ACCURACY.scalesNote).toContain("zaman-dışı test (eski kohort)");
    expect(ACCURACY.scalesNote).toContain("canlı sicil");
    expect(ACCURACY.scalesNote).toContain("hiçbir yerde toplanmaz");
    expect(text(root.querySelector(".scales-note"))).toBe(ACCURACY.scalesNote);
  });

  it("model bloğunda kart (CardVM aynı): gömülü sha, 'ne yapar'; dosya sha taşımıyor notu; canlı alan —", () => {
    const card = root.querySelector('.panel-oot .model-block-oot[data-model="ceiling_hazard_v0"] table.model-card');
    expect(card).not.toBeNull();
    const info = av.models.find((m) => m.model_id === "ceiling_hazard_v0");
    expect(card?.textContent).toContain((info?.params_sha256 ?? "?").slice(0, 8));
    expect(card?.textContent).toContain(info?.description ?? "?");
    expect(text(root.querySelector('.panel-oot .model-block-oot[data-model="ceiling_hazard_v0"] summary'))).toContain(T.noShaNote);
  });

  it("statik: zaman-dışı render backtest/canlı listelerini okumaz ve birleştirmez", () => {
    const { code } = split(readFileSync(join(APP_DIR, "src", "render", "accuracy_oot.ts"), "utf-8"));
    expect(/concat\s*\(/.test(code)).toBe(false);
    expect(/\b(backtest|live)\b/.test(code)).toBe(false);
    expect(/ScoresView|ScoreModel\b/.test(code)).toBe(false);
    const acc = split(readFileSync(join(APP_DIR, "src", "render", "accuracy.ts"), "utf-8")).code;
    expect(/\[[^\]]*\b(backtest|live)\b[^\]]*\boot\b[^\]]*\]/.test(acc)).toBe(false);
  });
});

describe("U72: hüküm eki ve renk; kırılımlarda küçük n", () => {
  const root = panel("ok");
  const open = root.querySelector('.oot-block[data-block="oot_pre_h99"]');
  const verdictOf = (rule: string) => open?.querySelector(`tr.cell-row[data-rule="${rule}"] td.verdict`);

  it("geçiyor / geçemiyor / ayırt edilemiyor + (zaman-dışı terazide); renk yalnız ilk ikisinde", () => {
    expect(text(verdictOf("base_km_expanding"))).toBe(`${VERDICT.pass}${VERDICT_OOT_SUFFIX}`);
    expect(verdictOf("base_km_expanding")?.classList.contains("win")).toBe(true);
    expect(text(verdictOf("ceiling_hazard_v0@INF"))).toBe(`${VERDICT.fail}${VERDICT_OOT_SUFFIX}`);
    expect(verdictOf("ceiling_hazard_v0@INF")?.classList.contains("lose")).toBe(true);
    const und = verdictOf("base_km_last10");
    expect(text(und)).toBe(`${VERDICT.undecided}${VERDICT_OOT_SUFFIX}`);
    expect(und?.classList.contains("win") || und?.classList.contains("lose")).toBe(false);
    expect(open?.querySelector("tr.cell-row.primary")?.getAttribute("data-rule")).toBe("base_km_expanding");
  });

  it("by_year n = 26 → 'yetersiz örnek' (ek yok, renk yok); n = 1 → 'metrik yok (n < 10)'", () => {
    const y21 = open?.querySelector('.by-year tr[data-subset="2021"] td.verdict');
    expect(text(y21)).toBe("yetersiz örnek");
    expect(y21?.className).toBe("verdict");
    expect(text(open?.querySelector('.by-year tr[data-subset="2020"]'))).toContain(T.noMetric);
    expect(text(open?.querySelector('.by-regime tr[data-subset="ALLOC_REGIME=PRE_20211111"] td.verdict'))).toBe(`${VERDICT.undecided}${VERDICT_OOT_SUFFIX}`);
  });

  it("ek 'geçiyor' içermez; panelde her 'geçiyor' bir hüküm hücresinden", () => {
    expect(VERDICT_OOT_SUFFIX).not.toContain(VERDICT.pass);
    const inVerdict = [...root.querySelectorAll<HTMLElement>("td.verdict")].filter((td) => td.dataset.verdict === VERDICT.pass).length;
    expect((root.textContent ?? "").split(VERDICT.pass).length - 1).toBe(inVerdict);
  });
});

describe("U73 + K-P3-1: fail-closed ve kod görünürlüğü", () => {
  it("satır tablosu yalnız açık küme bloğunda ve yalnız açık kodlarla; kasa / toplam / D1 sonrası bloklarında kod yok", () => {
    const root = panel("ok");
    const tickers = [...root.querySelectorAll<HTMLElement>("[data-ticker]")].map((e) => e.dataset.ticker);
    expect(tickers).toEqual(["SNTO1", "SNTO2"]);
    for (const e of root.querySelectorAll("[data-ticker]")) expect(e.closest(".oot-block")?.getAttribute("data-block")).toBe("oot_pre_h99");
    for (const b of ["oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"]) {
      const sec = root.querySelector(`.oot-block[data-block="${b}"]`);
      expect(sec, b).not.toBeNull();
      expect(sec?.querySelector(".oot-rows, [data-ticker]"), b).toBeNull();
    }
    const body = root.textContent ?? "";
    expect(["SNTS1", "SNTP1", "SNTX1", "SNTZ9"].filter((c) => body.includes(c)).length).toBe(0);
    // satır özeti Rust alanlarından: S_1 %90 · S_5 %50 · S_10 %10; ret satırında kod
    expect(text(root.querySelector('tr[data-ticker="SNTO1"] td.pred'))).toBe(T.predS("%90", "%50", "%10"));
    expect(text(root.querySelector('tr[data-ticker="SNTO2"] td.pred'))).toBe(ACCURACY.refusedPrediction("F3_MISSING"));
  });

  it("RETRO yalnız açık satırda geçen kodla; geçmeyen yalnız sayı", () => {
    const root = panel("ok");
    const li = root.querySelector('.oot-retro li[data-model="ceiling_hazard_v1_clip"]');
    expect(text(li)).toBe(T.retroLine("ceiling_hazard_v1_clip", 2, "SNTO1"));
    expect(text(root.querySelector(".retro-not-drawn"))).toBe(T.retroNotDrawn(1));
  });

  it("ihlaller panel yerine kural metni; blok ve kod yok", () => {
    for (const [name, rule] of [
      ["integrity_row_not_open", "OOT_ROW_NOT_OPEN"],
      ["integrity_min_n", "OOT_CELLS_BELOW_MIN_N"],
      ["integrity_verdict_n20", "VERDICT_WITHOUT_INTERVAL"],
      ["integrity_live", "OOT_LIVE_COUNTS_NONZERO"],
    ]) {
      const root = panel(name);
      const box = root.querySelector(".oot-integrity");
      expect(box?.getAttribute("data-rule"), name).toBe(rule);
      expect(text(box?.querySelector("strong"))).toBe(T.integrityTitle(T.integrityRule[rule]));
      expect(root.querySelector(".oot-block"), name).toBeNull();
      expect(root.querySelector("[data-ticker]"), name).toBeNull();
    }
    const nr = panel("integrity_row_not_open");
    expect(nr.textContent).not.toContain("SNTZ9");
    expect(text(nr.querySelector(".oot-integrity p.mono"))).toContain("1 satır açık küme değil");
  });

  it("sürüm 2, dosya yok, repo modu yok", () => {
    expect(text(panel("unsupported").querySelector(".oot-version"))).toBe(T.unsupported("borsai.scores_oot/2"));
    expect(text(panel("no_file").querySelector(".oot-no-file"))).toBe(T.noFile);
    expect(text(panel("repo_only").querySelector(".oot-repo-only"))).toBe(T.repoOnly);
  });

  it("bağımsız mod (gömülü satırsız kopya): satır tablosu ve RETRO repo modu ister", () => {
    const root = panel("embedded");
    expect(text(root.querySelector(".rows-repo-only"))).toBe(T.rowsRepoOnly);
    expect(text(root.querySelector(".oot-retro p"))).toBe(T.retroRepoOnly);
    expect(root.querySelector("[data-ticker]")).toBeNull();
  });
});

describe("U74: kasa alt bölümleri", () => {
  it("kasa açık: iki ek alt bölüm, kendi alt küme etiketleriyle; 'kasa: açıldı — …'; toplam satırı yok", () => {
    const root = panel("ok");
    expect(text(root.querySelector(".vault-line"))).toBe(T.vaultOpen("2030-01-01T00:00:00Z"));
    const heads = [...root.querySelectorAll(".oot-block > h4")].map((h) => text(h));
    expect(heads.slice(0, 3)).toEqual([T.openTitle, T.sealedTitle, T.allTitle]);
    const subsets = [...root.querySelectorAll<HTMLElement>(".oot-block")].map((b) => b.dataset.block);
    expect(subsets).toEqual(["oot_pre_h99", "oot_pre_h99_sealed", "oot_pre_h99_all", "post_d1", "post_d1_sealed", "post_d1_all"]);
    for (const b of root.querySelectorAll<HTMLElement>(".oot-block")) {
      expect(text(b.querySelector(".subset-label")), b.dataset.block).toBe(T.subsetLabel(b.dataset.subset ?? ""));
    }
    expect(root.querySelector("tr.total, tr.sum, .combined-verdict")).toBeNull();
    expect(text(root.querySelector('.oot-block[data-block="oot_pre_h99_all"] .excluded-models li'))).toContain("ceiling_hazard_v1_clip");
    expect(text(root.querySelector('.oot-block[data-block="post_d1"] .exposure'))).toBe(T.exposure("MACHINE_SEQUENCED"));
  });

  it("kasa kapalı: 'kasa: kapalı — …' ve kasa / toplam alt bölümü yok", () => {
    const root = panel("closed");
    expect(text(root.querySelector(".vault-line"))).toBe(T.vaultClosed);
    expect(root.querySelector('.oot-block[data-block="oot_pre_h99_sealed"], .oot-block[data-block="oot_pre_h99_all"]')).toBeNull();
  });
});

// ---------------------------------------------------------------- U75: gerçek dosya (K-P3-3)

const REAL = fx<Bundle>("scores_oot_panel_real.json");

/** SCORES_OOT.md'deki bir bölümün birincil hücre tablosu: model → [n (blok), model, karşılaştırılan, fark, aralık, k/k/e, hüküm]. */
function mdPrimary(heading: string): Map<string, string[]> {
  const md = readFileSync(join(APP_DIR, "..", "docs", "SCORES_OOT.md"), "utf-8").split("\n");
  const start = md.findIndex((l) => l.startsWith(heading));
  expect(start, heading).toBeGreaterThanOrEqual(0);
  const out = new Map<string, string[]>();
  let i = start + 1;
  while (i < md.length && !md[i].startsWith("| Model | Hücre")) i += 1;
  for (i += 2; i < md.length && md[i].startsWith("| `"); i += 1) {
    const cols = md[i].split("|").slice(1, -1).map((c) => c.trim());
    if (cols[3] === "0") continue; // OOT_RETRO satırı (bu alt küme bu model için test değil)
    out.set(cols[0].replace(/`/g, ""), cols.slice(3));
  }
  return out;
}

const num = (s: string) => Number(s.replace("+", ""));
const base = (v: string) => v.replace(VERDICT_OOT_SUFFIX, "");

function sealedCodes(): string[] {
  const lines = readFileSync(join(APP_DIR, "..", "registry", "oot", "cohort_pre_h99.csv"), "utf-8").split("\n");
  const head = lines[0].split(",");
  const [ct, cv] = [head.indexOf("ticker"), head.indexOf("vault")];
  return lines.slice(1).map((l) => l.split(",")).filter((c) => c[cv] === "SEALED").map((c) => c[ct]);
}

describe("U75: gerçek scores_oot.json ile render (K-P3-3)", () => {
  const root = dom(renderOotPanel(vmOf(REAL)));
  const block = (k: string) => REAL.view.blocks.find((b) => b.key === k);

  it("açık küme 27 / 8, kasa 27 / 14, toplam 19 / 8; D1 sonrası üç alt bölüm; kasa: açıldı — üretim zamanı", () => {
    const counts = REAL.view.blocks.map((b) => [b.key, b.models.length, b.models.filter((m) => m.primary !== null).length]);
    expect(counts).toEqual([
      ["oot_pre_h99", 27, 8], ["oot_pre_h99_sealed", 27, 14], ["oot_pre_h99_all", 19, 8],
      ["post_d1", 1, 1], ["post_d1_sealed", 1, 1], ["post_d1_all", 1, 1],
    ]);
    for (const [k, n] of [["oot_pre_h99", 8], ["oot_pre_h99_sealed", 14], ["oot_pre_h99_all", 8]] as const) {
      expect(root.querySelectorAll(`.oot-block[data-block="${k}"] tr.primary-row`).length, k).toBe(n);
    }
    expect(root.querySelectorAll(".oot-post-d1 .oot-block").length).toBe(3);
    expect(text(root.querySelector(".vault-line"))).toBe(T.vaultOpen(REAL.view.generated_at_utc ?? ""));
    expect(text(root.querySelector(".oot-title"))).toBe(block("oot_pre_h99")?.title);
  });

  it("birincil hücre değerleri SCORES_OOT.md §2, §8.1, §9.1, §6, §10, §11 ile aynı (4 ondalık; biçim farkı hariç)", () => {
    for (const [key, heading] of [
      ["oot_pre_h99", "## 2. Birincil hücreler"], ["oot_pre_h99_sealed", "### 8.1 Birincil hücreler"],
      ["oot_pre_h99_all", "### 9.1 Birincil hücreler"], ["post_d1", "## 6. Zaman-dışı test, D1 sonrası"],
      ["post_d1_sealed", "## 10. Zaman-dışı test, D1 sonrası, kasa"], ["post_d1_all", "## 11. Zaman-dışı test, D1 sonrası, toplam"],
    ] as const) {
      const md = mdPrimary(heading);
      const models = block(key)?.models.filter((m) => m.primary !== null) ?? [];
      expect(md.size, key).toBe(models.length);
      for (const m of models) {
        const row = md.get(m.model_id);
        expect(row, `${key}/${m.model_id}`).toBeDefined();
        if (!row) continue;
        const c = m.primary!;
        const [nb, mv, rv, diff, ci, w, verdict] = row;
        expect(nb, m.model_id).toBe(`${c.n} (${c.n_blocks})`);
        const ci95 = ci.replace(/[[\]]/g, "").split(",").map(num);
        const near = (a: number, b: unknown) => Math.abs(a - Number(b)) <= 5.1e-5;
        expect([near(num(mv), c.model_value), near(num(rv), c.rule_value), near(num(diff), c.diff)], m.model_id).toEqual([true, true, true]);
        expect([near(ci95[0], c.ci95?.[0]), near(ci95[1], c.ci95?.[1])], m.model_id).toEqual([true, true]);
        expect(w, m.model_id).toBe(`${c.wins} / ${c.losses} / ${c.ties}`);
        expect(base(verdict), m.model_id).toBe(c.verdict);
        const td = root.querySelector(`.oot-block[data-block="${key}"] tr.primary-row[data-model="${m.model_id}"] td.verdict`);
        expect(text(td), m.model_id).toBe(`${c.verdict}${VERDICT_OOT_SUFFIX}`);
      }
    }
    // D1 sonrası açık küme birincil hücresi: n = 59, geçiyor (zaman-dışı terazide)
    expect(text(root.querySelector('.oot-block[data-block="post_d1"] tr.primary-row td.verdict'))).toBe(`${VERDICT.pass}${VERDICT_OOT_SUFFIX}`);
  });

  it("DOM'da yalnız açık satırların kodları (71) ve kasa kodu yok (yalnız sayı)", () => {
    const tickers = new Set([...root.querySelectorAll<HTMLElement>("[data-ticker]")].map((e) => e.dataset.ticker));
    expect(tickers.size).toBe(71);
    for (const e of root.querySelectorAll("[data-ticker]")) expect(e.closest(".oot-block")?.getAttribute("data-block")).toBe("oot_pre_h99");
    const sealed = sealedCodes();
    expect(sealed.length).toBe(64);
    const body = root.innerHTML;
    const hits = sealed.filter((c) => new RegExp(`\\b${c}\\b`).test(body)).length;
    expect(hits).toBe(0);
    const fixtureText = readFileSync(join(APP_DIR, "tests", "fixtures", "ui", "scores_oot_panel_real.json"), "utf-8");
    expect(sealed.filter((c) => fixtureText.includes(`"${c}"`)).length).toBe(0);
    // RETRO: 568 çift, hepsi açık satırda geçen kodlarla
    expect(root.querySelector(".oot-retro")?.getAttribute("data-n")).toBe("568");
    expect(root.querySelector(".retro-not-drawn")).toBeNull();
  });
});
