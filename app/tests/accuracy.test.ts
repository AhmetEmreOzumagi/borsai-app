// @vitest-environment jsdom
// Doğruluk paneli (SPEC_APP §3d, §5.3 tablo T-1): U13–U26, U35'in scores kısmı ve EK 2 §5 / U51.
// Başlık alanları ve §2.3/§2.5 kararları Rust okuyucusundan gelir (src-tauri/tests/stage4.rs ->
// fixtures/ui/scores_views.json); burada yalnız render sınanır.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { ACCURACY, CARD, RESULTS, VERDICT } from "../src/i18n/tr";
import { renderAccuracy, type AccuracyView } from "../src/render/accuracy";
import { metric4, points1 } from "../src/render/format";
import type { ModelInfo, PathParamsInfo, ScoreCell, ScoresDoc, ScoresView } from "../src/types";
import { APP_DIR, dom, fx, repoScoresDoc, scoresView, split } from "./helpers";

const MODELS = fx<ModelInfo[]>("app_models.json");
const PATH_PARAMS = fx<PathParamsInfo[]>("path_params.json");

function av(name: string, extra: Partial<AccuracyView> = {}): AccuracyView {
  return { scores: scoresView(name), models: MODELS, pathParams: PATH_PARAMS, hidden: [], open: [], ...extra };
}

function render(name: string, extra: Partial<AccuracyView> = {}): HTMLElement {
  return dom(renderAccuracy(av(name, extra)));
}

/** Gerçek `scores/scores.json` (salt okuma); başlık alanları dosyadan, karar yok. */
function realView(): AccuracyView {
  const doc = repoScoresDoc<ScoresDoc>();
  const scores: ScoresView = {
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
  return { scores, models: MODELS, pathParams: PATH_PARAMS, hidden: [], open: [] };
}

function text(el: Element | null): string {
  return el?.textContent ?? "";
}

function liveText(root: HTMLElement): string {
  return [...root.querySelectorAll(".panel-live")].map((p) => p.textContent ?? "").join(" ");
}

describe("U13: başlıklar ve n alt satırı", () => {
  const root = render("n7");

  it("backtest başlığı aynen; canlı başlıkta n ve atlanan; n_live/n_late alt satırı", () => {
    expect(text(root.querySelector(".panel-backtest h4"))).toBe("Geçmiş veri testi (retrospektif, tasarıma maruz)");
    const head = text(root.querySelector(".panel-live h4"));
    expect(head).toContain("Canlı sicil (prospektif)");
    expect(head).toContain("n = 7; atlanan = 1");
    const brk = text(root.querySelector(".panel-live .breakdown"));
    expect(brk).toContain("n_live = 4 (LIVE)");
    expect(brk).toContain("n_late = 3 (LATE_RECORD)");
    expect(brk).toContain("ret = 1");
  });

  it("kaynak satırı: kaynak, üretim, as-of, sha ilk 12", () => {
    const src = text(root.querySelector(".scores-source"));
    const v = scoresView("n7");
    expect(src).toContain("REPO");
    expect(src).toContain(v.generated_at_utc ?? "");
    expect(src).toContain(v.as_of_session ?? "");
    expect(src).toContain(v.sha12);
    expect(v.sha12.length).toBe(12);
    expect(root.querySelector(".index-mismatch")).not.toBeNull();
  });
});

describe("U14: iki terazi ayrı; hiçbir yerde toplanmaz", () => {
  const root = render("n35");

  it("iki ayrı renk sınıfı var ve hiçbir öğe ikisini birden taşımaz", () => {
    expect(root.querySelectorAll(".panel-backtest").length).toBeGreaterThan(0);
    expect(root.querySelectorAll(".panel-live").length).toBeGreaterThan(0);
    expect(root.querySelectorAll(".panel-backtest.panel-live").length).toBe(0);
    for (const p of root.querySelectorAll(".panel-backtest")) expect(p.querySelector(".panel-live")).toBeNull();
    for (const p of root.querySelectorAll(".panel-live")) expect(p.querySelector(".panel-backtest")).toBeNull();
  });

  it("her hücre satırı tek bir terazide (data-scale) ve terazi dışında hüküm hücresi yok", () => {
    const scales = new Set([...root.querySelectorAll<HTMLElement>("tr.cell-row")].map((r) => r.dataset.scale));
    expect(scales).toEqual(new Set(["backtest", "live"]));
    for (const r of root.querySelectorAll<HTMLElement>("tr.cell-row")) {
      const scale = r.dataset.scale === "backtest" ? ".panel-backtest" : ".panel-live";
      expect(r.closest(scale), r.dataset.scale).not.toBeNull();
    }
    expect(root.querySelectorAll("tr.cell-row:not([data-scale])").length).toBe(0);
  });

  it("kaynakta iki listeyi birleştiren ifade yok (koşullu j'ler de dahil)", () => {
    const { code } = split(readFileSync(join(APP_DIR, "src", "render", "accuracy.ts"), "utf-8"));
    expect(/concat\s*\(/.test(code)).toBe(false);
    expect(/\[[^\]]*\bbacktest\b[^\]]*\blive\b[^\]]*\]/.test(code)).toBe(false);
    expect(/\.\.\.\s*\w*(by_j|conditional)/.test(code)).toBe(false);
    // Her j kendi bloğunda: `cond-j` öğeleri arasında ortak hücre tablosu yok.
    expect(/by_j[^;]*flatMap/.test(code)).toBe(false);
  });

  it("panelde toplam/ortalama satırı yok", () => {
    expect(root.querySelector("tr.total, tr.sum, .combined-verdict")).toBeNull();
    expect(text(root.querySelector(".scales-note"))).toContain("hiçbir yerde toplanmaz");
  });
});

describe("U15: metrik satırının alanları ve puan birimi", () => {
  const root = render("n35");
  const doc = scoresView("n35").doc as ScoresDoc;

  it("model · kural · kural değeri · fark · aralık · n · kazanç/kayıp/eşit", () => {
    const cell = doc.models[0].live.cells[0];
    const row = root.querySelector<HTMLElement>(`.panel-live tr.cell-row[data-rule="${cell.rule_id}"]`);
    expect(row).not.toBeNull();
    expect(text(row?.querySelector("td.metric") ?? null)).toBe(points1(cell.model_value));
    expect(text(row?.querySelector("td.diff") ?? null)).toBe(points1(cell.diff));
    expect(text(row?.querySelector("td.n") ?? null)).toBe(String(cell.n));
    expect(text(row?.querySelector("td.wlt") ?? null)).toBe(`${cell.wins} / ${cell.losses} / ${cell.ties}`);
    expect(text(row ?? null)).toContain(cell.rule_id);
  });

  it("getiri hataları puan (0.0046 → 0.5 puan), Brier 4 ondalık", () => {
    expect(points1(0.0046)).toBe("0.5 puan");
    const bt = scoresView("n7").doc as ScoresDoc;
    const d1 = bt.models[0].backtest.cells.find((c) => c.rule_id === "base_train_median" && c.metric === "MAE" && c.horizon_or_k === "D1");
    const bd = dom(renderAccuracy(av("n7")));
    const row = bd.querySelector<HTMLElement>('.panel-backtest tr.cell-row[data-rule="base_train_median"][data-metric="MAE"][data-h="D1"]');
    expect(text(row?.querySelector("td.diff") ?? null)).toBe(points1(d1?.diff ?? null));
    expect(text(row?.querySelector("td.diff") ?? null)).toBe("0.5 puan");
    const brier = bt.models[0].backtest.cells.find((c) => c.metric === "Brier");
    const brow = bd.querySelector<HTMLElement>('.panel-backtest tr.cell-row[data-metric="Brier"]');
    expect(text(brow?.querySelector("td.metric") ?? null)).toBe(metric4(brier?.model_value ?? null));
  });
});

describe("U16: n < 10 → yalnız satır tablosu", () => {
  const root = render("n7");
  const live = root.querySelector<HTMLElement>(".panel-live");

  it("canlı bölümde satır tablosu var, hücre/metrik/hüküm yok", () => {
    expect(live?.querySelectorAll("table.rows tbody tr").length).toBe(8); // 7 skorlanan + 1 RET satırı
    expect(live?.querySelectorAll("td.metric").length).toBe(0);
    expect(live?.querySelectorAll("tr.cell-row").length).toBe(0);
    expect(live?.querySelectorAll("td.verdict").length).toBe(0);
    expect(live?.querySelectorAll(".win, .lose").length).toBe(0);
    expect(text(live?.querySelector(".rows-only") ?? null)).toContain("n < 10: metrik hesaplanmaz");
  });

  it("canlı bölümde hüküm dizeleri geçmez (backtest terazisi ayrıdır)", () => {
    const t = liveText(root);
    for (const w of [VERDICT.pass, VERDICT.fail, VERDICT.undecided, VERDICT.insufficient]) expect(t).not.toContain(w);
  });

  it("satırlarda arz, D1, sınıf, kayıt, zaman kanıtı, tahmin, gerçekleşen, kural tahminleri", () => {
    const first = live?.querySelector<HTMLElement>("table.rows tbody tr");
    expect(first?.dataset.ticker).toBe("SNT01");
    expect(text(first)).toContain("2027-01-02");
    expect(text(first)).toContain("LATE_RECORD");
    expect(text(first)).toContain("20270101T000000Z_5feceb66ffc8.json");
    expect(text(first?.querySelector("td.proof") ?? null)).toContain("git+push");
    expect(first?.querySelectorAll("td.rule-pred").length).toBe(2);
    // ret satırı: tahmin yerine ret kodu
    const refused = live?.querySelector<HTMLElement>('table.rows tbody tr[data-status="REFUSED"]');
    expect(text(refused?.querySelector("td.pred") ?? null)).toBe(ACCURACY.refusedPrediction("F3_MISSING"));
  });
});

describe("U17: 10 ≤ n < 30 → yetersiz örnek", () => {
  const root = render("n12");
  const live = root.querySelector<HTMLElement>(".panel-live");

  it("hücreler var; her satırda 'yetersiz örnek' rozeti; kazanan rengi yok", () => {
    const rows = live?.querySelectorAll<HTMLElement>("tr.cell-row") ?? [];
    expect(rows.length).toBe(2);
    for (const r of rows) expect(text(r.querySelector(".badge-small-n"))).toBe(VERDICT.insufficient);
    expect(live?.querySelectorAll(".win, .lose").length).toBe(0);
  });

  it("ci95 null satırında 'aralık için yetersiz'", () => {
    const row = live?.querySelector<HTMLElement>('tr.cell-row[data-rule="base_train_mean"]');
    expect(text(row?.querySelector("td.ci") ?? null)).toBe(VERDICT.noInterval);
    const withCi = live?.querySelector<HTMLElement>('tr.cell-row[data-rule="base_train_median"]');
    expect(text(withCi?.querySelector("td.ci") ?? null)).toContain("puan");
  });

  it("hüküm metni dosyadaki verdict alanındandır", () => {
    const doc = scoresView("n12").doc as ScoresDoc;
    for (const c of doc.models[0].live.cells) {
      const row = live?.querySelector<HTMLElement>(`tr.cell-row[data-rule="${c.rule_id}"]`);
      expect(row?.querySelector("td.verdict")?.getAttribute("data-verdict")).toBe(c.verdict);
      expect(text(row?.querySelector("td.verdict") ?? null)).toContain(c.verdict ?? "");
    }
  });
});

describe("U18: n ≥ 30 → hüküm ve renk", () => {
  const root = render("n35");
  const live = root.querySelector<HTMLElement>(".panel-live");
  const cell = (rule: string) => live?.querySelector<HTMLElement>(`tr.cell-row[data-rule="${rule}"] td.verdict`);

  it("geçiyor / geçemiyor / ayırt edilemiyor doğru renkte ve metin verdict'ten", () => {
    expect(cell("base_train_mean")?.textContent?.trim()).toBe(VERDICT.pass);
    expect(cell("base_train_mean")?.classList.contains("win")).toBe(true);
    expect(cell("base_train_median")?.textContent?.trim()).toBe(VERDICT.fail);
    expect(cell("base_train_median")?.classList.contains("lose")).toBe(true);
    expect(cell("base_zero")?.textContent?.trim()).toBe(VERDICT.undecided);
    expect(cell("base_zero")?.classList.contains("win")).toBe(false);
    expect(cell("base_zero")?.classList.contains("lose")).toBe(false);
    expect(live?.querySelectorAll(".badge-small-n").length).toBe(0);
  });

  it("aralıklar dosyadaki uçlarla", () => {
    const row = live?.querySelector<HTMLElement>('tr.cell-row[data-rule="base_train_mean"]');
    expect(text(row?.querySelector("td.ci") ?? null)).toBe(`[-0.9, -0.1] ${ACCURACY.pointsUnit}`);
  });
});

describe("U19: 'geçiyor' yalnız verdict eşlemesinde ve verdict alanından", () => {
  it("kaynak ağacında (ön uç) yalnız tr.ts'teki VERDICT eşlemesi", () => {
    const src = join(APP_DIR, "src");
    const walk = (dir: string): string[] =>
      readdirSync(dir).flatMap((n) => {
        const p = join(dir, n);
        return statSync(p).isDirectory() ? walk(p) : p.endsWith(".ts") ? [p] : [];
      });
    let found = 0;
    for (const f of walk(src)) {
      const { strings } = split(readFileSync(f, "utf-8"));
      const hits = strings.filter((s) => s.includes(VERDICT.pass));
      if (f.endsWith(join("i18n", "tr.ts"))) {
        found = hits.length;
        continue;
      }
      expect(hits, f).toEqual([]);
    }
    expect(found).toBe(1);
    expect(VERDICT.pass).toBe("geçiyor");
  });

  it("Rust tarafında yalnız §2.3 denetiminin sabitlerinde", () => {
    const rust = join(APP_DIR, "src-tauri", "src");
    const walk = (dir: string): string[] =>
      readdirSync(dir).flatMap((n) => {
        const p = join(dir, n);
        return statSync(p).isDirectory() ? walk(p) : p.endsWith(".rs") ? [p] : [];
      });
    for (const f of walk(rust)) {
      const lines = readFileSync(f, "utf-8").split("\n").filter((l) => l.includes(VERDICT.pass) && !l.trimStart().startsWith("//"));
      const allowed = f.endsWith(join("commands", "scores.rs")) ? ['pub const VERDICT_PASS: &str = "geçiyor";'] : [];
      expect(lines.map((l) => l.trim()), f).toEqual(allowed);
    }
  });

  it("panelde her 'geçiyor' bir verdict hücresinden gelir", () => {
    for (const name of ["n7", "n12", "n35"]) {
      const root = render(name);
      const inVerdict = [...root.querySelectorAll<HTMLElement>("td.verdict")].filter((td) => td.dataset.verdict === VERDICT.pass).length;
      const all = (root.textContent ?? "").split(VERDICT.pass).length - 1;
      expect(all, name).toBe(inVerdict);
    }
    expect(liveText(render("n12"))).not.toContain(VERDICT.pass);
  });
});

describe("U20: isabet oranı tek başına gösterilmez", () => {
  it("rule_value dolu → satır var; null → satır gizlenir ve not düşülür", () => {
    const ok = render("n7");
    expect(ok.querySelector('.panel-backtest tr.cell-row[data-metric="accuracy"]')).not.toBeNull();
    expect(ok.querySelector(".accuracy-hidden")).toBeNull();
    const hidden = render("n7_accuracy_rule_null");
    expect(hidden.querySelector('tr.cell-row[data-metric="accuracy"]')).toBeNull();
    expect(text(hidden.querySelector(".accuracy-hidden"))).toBe(ACCURACY.accuracyHidden);
  });
});

describe("U21: model kartı", () => {
  it("model_id, eğitim n, kesim, sha ilk 8, varyant sayısı", () => {
    const card = render("n7").querySelector<HTMLElement>(".model-card");
    expect(card?.dataset.model).toBe("v1_5_h99");
    const t = text(card);
    expect(t).toContain("99 / 2026-08-19");
    expect(t).toContain("bf809859");
    expect(t).toContain(CARD.variants);
    expect(card?.querySelectorAll("tr")[4]?.textContent).toContain("2");
    expect(t).toContain("D5");
    expect(t).toContain("base_train_median");
  });
});

describe("U22: birincil hücre vurgusu", () => {
  const root = render("n7");

  it("primary_cell satırı .primary ve 'birincil (önceden ilan)'; ötekiler 'keşif'", () => {
    const primary = root.querySelectorAll<HTMLElement>(".panel-backtest tr.cell-row.primary");
    expect(primary.length).toBe(1);
    expect(primary[0].dataset.h).toBe("D5");
    expect(primary[0].dataset.rule).toBe("base_train_median");
    expect(primary[0].dataset.metric).toBe("MAE");
    expect(text(primary[0])).toContain(ACCURACY.primaryBadge);
    const others = [...root.querySelectorAll<HTMLElement>(".panel-backtest tr.cell-row:not(.primary)")];
    expect(others.length).toBeGreaterThan(0);
    for (const r of others) expect(text(r)).toContain(ACCURACY.exploratoryBadge);
  });
});

describe("U23: rejim uyarısı panelin üstünde", () => {
  it("sabit metinle", () => {
    expect(text(render("n7").querySelector("[data-role=regime]"))).toBe(RESULTS.regime);
  });
});

describe("U24: fail-closed bütünlük denetimi", () => {
  const cases: [string, string][] = [
    ["bad_live_cells", "LIVE_CELLS_BELOW_MIN_N"],
    ["bad_descriptive", "LIVE_DESCRIPTIVE_BELOW_MIN_N"],
    ["bad_self_cells", "SELF_REPORTED_CELLS_BELOW_MIN_N"],
    ["bad_split", "LIVE_N_SPLIT"],
    ["bad_verdict_small_n", "VERDICT_WITHOUT_INTERVAL"],
    ["bad_verdict_ci_zero", "VERDICT_WITHOUT_INTERVAL"],
  ];

  it("her ihlalde panel yerine kural metni ve ham ayrıntı", () => {
    for (const [name, rule] of cases) {
      const root = render(name);
      const box = root.querySelector<HTMLElement>(".integrity-error");
      expect(box, name).not.toBeNull();
      expect(box?.dataset.rule, name).toBe(rule);
      expect(text(box), name).toContain(ACCURACY.integrityRule[rule]);
      expect(root.querySelector(".panel-backtest"), name).toBeNull();
      expect(root.querySelector(".panel-live"), name).toBeNull();
      expect(root.querySelector("tr.cell-row"), name).toBeNull();
    }
  });
});

describe("U25: uygulama skor hesaplamaz", () => {
  it("fixture'daki her model_value ve kural değeri DOM'da (biçimlendirilmiş)", () => {
    for (const name of ["n7", "n12", "n35"]) {
      const root = render(name);
      const doc = scoresView(name).doc as ScoresDoc;
      const m = doc.models[0];
      const cells: ScoreCell[] = [...m.backtest.cells, ...m.live.cells];
      const body = root.textContent ?? "";
      for (const c of cells) {
        const point = c.metric === "MAE" || c.metric === "MedAE";
        for (const x of [c.model_value, c.rule_value]) {
          if (x === null || x === undefined) continue;
          expect(body, `${name} ${c.output} ${c.horizon_or_k} ${c.metric} ${c.rule_id}`).toContain(point ? points1(x) : metric4(x));
        }
      }
    }
  });

  it("render dosyasında metrik hesabı yok (yalnız biçimlendirme çağrısı)", () => {
    const { code } = split(readFileSync(join(APP_DIR, "src", "render", "accuracy.ts"), "utf-8"));
    for (const b of [/bootstrap/i, /percentile/i, /\bmean\s*\(/, /\bsum\s*\(/, /\.reduce\s*\(/, /Math\./, /\*\*/]) {
      expect(b.test(code), String(b)).toBe(false);
    }
  });
});

describe("U26: self-reported ikincil, RETRO ayrı; canlı n'e girmez", () => {
  const root = render("n12");

  it("self-reported ayrı bölümde ve kendi n'iyle", () => {
    const sec = root.querySelector<HTMLElement>(".self-reported");
    expect(sec).not.toBeNull();
    expect(text(sec)).toContain(ACCURACY.selfReportedTitle);
    expect(sec?.querySelectorAll("table.self-rows tbody tr").length).toBe(2);
    expect(text(sec)).toContain(ACCURACY.selfReportedNote("2"));
    // canlı n değişmedi
    expect(text(root.querySelector(".panel-live h4"))).toContain("n = 12");
    expect(root.querySelector<HTMLElement>(".panel-live")?.dataset.n).toBe("12");
    // kendi n'i < 10 olduğu için self-reported hücre yok
    expect(sec?.querySelectorAll("tr.cell-row").length).toBe(0);
  });

  it("RETRO model başına gruplu, gri ve ayrı; hiçbir n'e girmez", () => {
    const retro = root.querySelector<HTMLElement>(".retro");
    expect(text(retro)).toContain(ACCURACY.retroTitle);
    const items = retro?.querySelectorAll<HTMLElement>("li") ?? [];
    expect([...items].map((i) => i.dataset.model)).toEqual(["v1_5_h99", "snt_other_v0"]);
    expect(text(items[0])).toContain("SNT20, SNT21");
    expect(text(items[0])).toContain("(2)");
    expect(items[0].getAttribute("title")).toContain("MODEL_FROZEN_AFTER_OUTCOME_NO_RECORD");
    expect(retro?.closest(".panel-live")).toBeNull();
  });

  it("ayrı modeller (INDEX dışı) panelin sonunda, metriksiz", () => {
    const sep = root.querySelector<HTMLElement>(".separate-models");
    expect(text(sep)).toContain(ACCURACY.separateTitle);
    expect(sep?.querySelector<HTMLElement>(".separate-model")?.dataset.model).toBe("snt_full20");
    expect(sep?.querySelectorAll("tr.cell-row").length).toBe(0);
    expect(text(sep)).toContain("AYRI model");
  });
});

describe("SPEC_DEVIATIONS satır 83'ün ek alanları (görev kararı)", () => {
  it("geçersiz kullanım ayrı, gri, katlanır; note aynen", () => {
    const box = render("n7").querySelector<HTMLElement>(".invalid-use");
    expect(box?.tagName).toBe("DETAILS");
    expect(text(box?.querySelector("summary") ?? null)).toBe(ACCURACY.invalidUseTitle);
    expect(text(box)).toContain("geçersiz kullanım, hiçbir metriğe ve n'e girmez");
    expect(box?.querySelectorAll("tbody tr").length).toBe(1);
  });

  it("iptal edilen kayıtlar canlı bölümde listelenir", () => {
    const box = render("n7").querySelector<HTMLElement>(".cancelled");
    expect(text(box)).toContain(ACCURACY.cancelledTitle);
    expect(text(box)).toContain("20270101T000000Z_aaaaaaaaaaaa.json");
    expect(text(box)).toContain("kurgusal: girdi belgesi yanlış kaynaktan");
  });

  it("betimleyici ölçüler ayrı alt tabloda, aralıksız ve hükümsüz", () => {
    const box = render("n35").querySelector<HTMLElement>(".descriptive");
    expect(text(box?.querySelector("summary") ?? null)).toBe(ACCURACY.descriptiveTitle);
    expect(box?.querySelectorAll("td.verdict").length).toBe(0);
    expect(box?.querySelectorAll("td.ci").length).toBe(0);
    expect(text(box)).toContain("MedAE");
    expect(text(box)).toContain(points1(0.0271));
  });
});

describe("U35 (scores): sürüm uyumsuzluğu", () => {
  it("panel kapalı, kısmi gösterim yok", () => {
    const root = render("bad_schema_version");
    expect(text(root.querySelector(".version-error"))).toBe(ACCURACY.unsupportedVersion("borsai.scores/2"));
    expect(root.querySelector(".panel-backtest")).toBeNull();
    expect(root.querySelector(".panel-live")).toBeNull();
    expect(root.querySelector("table")).toBeNull();
  });

  it("dosya yok → kapalı hâl metni", () => {
    const root = dom(renderAccuracy({ scores: null, models: MODELS, hidden: [], open: [] }));
    expect(text(root.querySelector(".no-scores"))).toBe(ACCURACY.noFile);
  });
});

describe("U51: Faz 4 blokları ve koşullu skorlar", () => {
  it("kind = ceiling_path bloğu getiri/p_up modeli gibi okunur", () => {
    const root = dom(renderAccuracy(realView()));
    const block = root.querySelector<HTMLElement>('.model-block[data-model="ceiling_path_v0"]');
    expect(block?.dataset.kind).toBe("ceiling_path");
    const outs = new Set([...block?.querySelectorAll<HTMLElement>(".panel-backtest tr.cell-row") ?? []].map((r) => r.dataset.output));
    expect(outs).toEqual(new Set(["return", "p_up"]));
  });

  it("backtest hücresi olmayan blokta 'hücre yok' metni", () => {
    const root = dom(renderAccuracy(realView()));
    const empty = root.querySelector<HTMLElement>('.model-block[data-model="base_always_ceiling"] .panel-backtest .no-cells');
    expect(text(empty)).toBe(ACCURACY.noBacktestCells);
  });

  it("conditional yoksa 'henüz koşullu skor yok'", () => {
    expect(text(render("n35").querySelector(".cond-none"))).toBe(ACCURACY.condNone);
  });

  it("sentetik koşullu blok: j = 1 (n = 4) satır tablosu, j = 3 (n = 12) yetersiz örnek", () => {
    const root = render("conditional");
    const j1 = root.querySelector<HTMLElement>('.cond-j[data-j="1"]');
    expect(j1?.dataset.n).toBe("4");
    expect(j1?.querySelectorAll("tr.cell-row").length).toBe(0);
    expect(j1?.querySelectorAll("table.cond-rows tbody tr").length).toBe(4);
    // koşullu satırlar kendi şemasıyla (EK 2 §5), koşulsuz satır tablosuna karışmaz
    const cols = text(j1?.querySelector("table.cond-rows thead") ?? null);
    expect(cols).toContain("RPS");
    expect(cols).toContain("Brier");
    expect(cols).not.toContain(ACCURACY.colPrediction);
    expect(j1?.querySelector("table.rows")).toBeNull();
    expect(text(j1?.querySelector(".rows-only") ?? null)).toContain("n < 10");
    const j3 = root.querySelector<HTMLElement>('.cond-j[data-j="3"]');
    expect(j3?.dataset.n).toBe("12");
    const rows = j3?.querySelectorAll<HTMLElement>("tr.cell-row") ?? [];
    expect(rows.length).toBe(2);
    for (const r of rows) {
      expect(text(r.querySelector(".badge-small-n"))).toBe(VERDICT.insufficient);
      expect(r.dataset.scale).toBe("live_conditional");
    }
    expect(j3?.querySelectorAll(".win, .lose").length).toBe(0);
    expect(text(root.querySelector(".cond-scores"))).toContain(ACCURACY.condNote);
  });

  it("koşullu blok sürümü desteklenmiyorsa blok gösterilmez", () => {
    const root = render("conditional_bad_version");
    expect(text(root.querySelector(".cond-unsupported"))).toBe(ACCURACY.condUnsupported("borsai.scores_conditional/2"));
    expect(root.querySelector(".cond-j")).toBeNull();
    // panel açık kalır
    expect(root.querySelector(".panel-live")).not.toBeNull();
  });
});

describe("gerçek scores/scores.json ile render", () => {
  const root = dom(renderAccuracy(realView()));
  const doc = repoScoresDoc<ScoresDoc>();

  it("27 model bloğu; canlıda hiçbir hücre ve hüküm yok, satır tabloları var", () => {
    expect(root.querySelectorAll(".model-block").length).toBe(27);
    expect(root.querySelectorAll(".panel-live tr.cell-row").length).toBe(0);
    expect(root.querySelectorAll(".panel-live td.verdict").length).toBe(0);
    expect(liveText(root)).not.toContain(VERDICT.pass);
    for (const m of doc.models) {
      const live = root.querySelector<HTMLElement>(`.panel-live[data-model="${m.model_id}"]`);
      expect(live?.dataset.n, m.model_id).toBe(String(m.live.n_scored));
      const rows = live?.querySelectorAll("table.rows tbody tr").length ?? 0;
      expect(rows, m.model_id).toBe(m.live.rows.length);
      if (m.live.rows.length === 0) expect(text(live?.querySelector(".live-none") ?? null)).toBe(ACCURACY.liveNone);
    }
  });

  it("ceiling_path_v0 birincil hücresi: D5 MAE vs base_train_median, n = 85, hüküm verdict'ten", () => {
    const row = root.querySelector<HTMLElement>('.model-block[data-model="ceiling_path_v0"] tr.cell-row.primary');
    expect(row?.dataset.h).toBe("D5");
    expect(row?.dataset.metric).toBe("MAE");
    expect(row?.dataset.rule).toBe("base_train_median");
    expect(text(row?.querySelector("td.n") ?? null)).toBe("85");
    expect(text(row?.querySelector("td.diff") ?? null)).toBe(points1(-0.11584504217482987));
    expect(text(row?.querySelector("td.ci") ?? null)).toBe(`[-16.1, -7.4] ${ACCURACY.pointsUnit}`);
    const verdict = row?.querySelector<HTMLElement>("td.verdict");
    const cell = doc.models.find((m) => m.model_id === "ceiling_path_v0")?.backtest.cells.find((c) => c.label === "birincil");
    expect(verdict?.dataset.verdict).toBe(cell?.verdict);
    expect(verdict?.textContent?.trim()).toBe(cell?.verdict);
    expect(verdict?.classList.contains("win")).toBe(true);
    expect(text(row)).toContain(ACCURACY.primaryBadge);
  });

  it("RETRO 77 satır, model başına gruplu; atlanan listesi 19 satır", () => {
    const items = root.querySelectorAll<HTMLElement>(".retro li");
    expect(items.length).toBe(11);
    expect([...items].map((i) => i.dataset.model)).toEqual(["ceiling_path_v0", "ceiling_path_v0@INF", "pb_ceiling_path_v0",
      "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF",
      "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"]);
    for (const i of items) expect(text(i)).toContain("(7)");
    expect(root.querySelectorAll(".skipped tbody tr").length).toBe(19);
    expect(root.querySelector<HTMLElement>(".separate-models .separate-model")?.dataset.model).toBe("v1_5_full20");
  });

  it("gizlenen model bloğu çizilmez ama seçicide kalır", () => {
    const v = realView();
    const root2 = dom(renderAccuracy({ ...v, hidden: ["pb_v0"] }));
    expect(root2.querySelector('.model-block[data-model="pb_v0"]')).toBeNull();
    expect(root2.querySelector<HTMLInputElement>('.selector input[data-model="pb_v0"]')?.checked).toBe(false);
    expect(root2.querySelectorAll(".model-block").length).toBe(26);
  });
});
