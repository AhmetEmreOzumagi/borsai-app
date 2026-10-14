// @vitest-environment jsdom
// D1 sonrası (SPEC_APP EK 3 §6.5, §10.2): U68 "D1 sonrası" satırı, K-P2-3 kart satırının terazi sütunları, U70 Doğruluk
// bölümü. Görünümler Rust'ın gerçek çıktısıdır (src-tauri/tests/stage3.rs: post_d1_records_reader,
// official_summary_post_d1_row; stage4.rs: scores_post_d1_reader); burada yalnız render sınanır, ön uçta hesap yok.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { ACCURACY, COND, PATH_COND, SUMMARY, VERDICT } from "../src/i18n/tr";
import { renderAccuracy, type AccuracyView } from "../src/render/accuracy";
import { renderConditional, type ConditionalVM } from "../src/render/ceiling";
import { pct0 } from "../src/render/format";
import type { PostD1VM } from "../src/render/post_d1";
import { renderCeilingSummary } from "../src/render/summary";
import type {
  CeilingDisplay,
  CeilingSummary,
  ModelInfo,
  PathConditional,
  PathParamsInfo,
  PostD1View,
  ScoresPostD1Doc,
  ScoresPostD1View,
  StreakView,
} from "../src/types";
import { APP_DIR, dom, fx, readText, scoresDoc, split } from "./helpers";

const POST = "post_d1_hazard_v0";
const NO_DECL = Array<boolean>(10).fill(false);

function official(view: string): PostD1VM {
  return { mode: "OFFICIAL", view: fx<PostD1View>(view), error: null };
}

function vm(cond: string, j: number, postD1: PostD1VM | null, extra: Partial<ConditionalVM> = {}): ConditionalVM {
  return {
    streak: fx<StreakView>("streak_pending.json"),
    cond: fx<CeilingDisplay>(cond),
    jSelected: j,
    tab: "ceiling",
    hidden: [],
    declared: NO_DECL,
    declDropped: false,
    pathAvailable: true,
    pathCond: [],
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    recordWithoutPath: false,
    postD1,
    ...extra,
  };
}

const postCells = (root: HTMLElement) => [...root.querySelectorAll<HTMLElement>(`.cond-table td[data-model="${POST}"]`)];

describe("U68: koşullu sekmede \"D1 sonrası\" satırı (yalnız kayıttan, yalnız j ≥ 1)", () => {
  it("j = 0: satır yok, not \"D1 sonrası model j ≥ 1'de tanımlı\"", () => {
    const root = dom(renderConditional(vm("ceiling_netgl_j0.json", 0, official("post_d1_view_j0.json"))));
    expect(postCells(root)).toHaveLength(0);
    expect(root.querySelector(".post-d1-j0")?.textContent).toBe(COND.postD1J0);
    expect(root.querySelector(".cond-table")?.textContent).not.toContain(COND.postD1Row);
  });

  it("j = 2: satır S_cond = 0.6^(k − 2) (kaydın S'inden, Rust `ceiling_display`); yarın bozulma %40; kaynak satırı", () => {
    const v = fx<PostD1View>("post_d1_view_j2.json");
    const root = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, official("post_d1_view_j2.json"))));
    const head = [...root.querySelectorAll(".cond-table thead th")].map((th) => th.textContent);
    expect(head).toContain(COND.postD1Row);
    const cells = postCells(root);
    // k = 3..10 hücreleri ve 4 istatistik satırı
    const ks = cells.slice(0, 8).map((c) => c.textContent);
    expect(ks).toEqual([3, 4, 5, 6, 7, 8, 9, 10].map((k) => pct0(v.row?.cond?.S_cond[k - 1] ?? null)));
    expect(ks[0]).toBe(pct0(0.6));
    expect(cells[8].textContent).toBe(pct0(0.4));
    const src = root.querySelector(".post-d1-source")?.textContent ?? "";
    expect(src).toBe(COND.postD1Source("registry/post_d1/SNTA1/20300107T180000Z_aaaaaaaaaaaa.json", "3f764026", "2030-01-07", "aaaaaaaa", "bbbbbbbb"));
    expect(src).toContain("bültenler sha aaaaaaaa / bbbbbbbb");
    // tek etkin kayıt: sekme ve "birincil seçim" etiketi yok; push kanıtı göstergesi var
    expect(root.querySelector(".post-d1-tabs")).toBeNull();
    expect(root.querySelector(".post-d1-proof")).not.toBeNull();
    // eğri: ek seri
    expect(root.querySelector(".cond-curve")).not.toBeNull();
  });

  it("RET ve kapsam dışı metinleri; kayıt yok notu", () => {
    const refused = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, { ...official("post_d1_view_refused.json") })));
    // görünüm j = 1'de üretildi: j uyuşmazken satır yine çizilmez, durum metni gösterilir
    expect(refused.querySelector(".post-d1-refused")?.textContent).toBe(COND.postD1Refused("D1_LIMIT_NA"));
    expect(postCells(refused)).toHaveLength(0);
    const na = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, official("post_d1_view_na.json"))));
    expect(na.querySelector(".post-d1-na")?.textContent).toBe(COND.postD1NotApplicable);
    const none = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, official("post_d1_view_none.json"))));
    expect(none.querySelector(".post-d1-none")?.textContent).toBe(COND.postD1None);
    expect(postCells(none)).toHaveLength(0);
  });

  it("iki etkin kayıt: en erken varsayılan, sekmeler ve \"birincil seçim skorlamada\" etiketi", () => {
    const v = fx<PostD1View>("post_d1_view_two.json");
    const root = dom(renderConditional(vm("ceiling_netgl_j0.json", 1, { mode: "OFFICIAL", view: v, error: null })));
    const tabs = [...root.querySelectorAll<HTMLElement>("[data-action=post-d1-tab]")];
    expect(tabs.map((t) => t.dataset.file)).toEqual(v.active);
    expect(root.querySelector(".post-d1-tabs .tab.active")?.getAttribute("data-file")).toBe(v.active[0]);
    expect(root.querySelector(".post-d1-primary")?.textContent).toBe(COND.postD1Primary);
  });

  it("senaryoda satır yok: yalnız not (elle D1 girdisi yok)", () => {
    const view = fx<PostD1View>("post_d1_view_j2.json");
    const root = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, { mode: "SCENARIO", view, error: null })));
    expect(postCells(root)).toHaveLength(0);
    expect(root.querySelector(".post-d1-scenario")?.textContent).toBe(COND.postD1Scenario);
  });

  it("U52: beyan resmi verinin önündeyse D1 sonrası satırı yok (yalnız \"resmi kapanış bekleniyor\")", () => {
    const declared = [...NO_DECL];
    declared[3] = true; // D4: şeritte PENDING → beyan önde
    const root = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, official("post_d1_view_j2.json"), { declared })));
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    expect(postCells(root)).toHaveLength(0);
    expect(root.textContent).not.toContain(COND.postD1Row);
  });

  it("\"Getiri (koşullu)\" ek kartı: kayıttaki path_conditional, kaynak \"D1 sonrası kayıt\" (hesap yok)", () => {
    const v = fx<PostD1View>("post_d1_view_j2.json");
    const pc = fx<PathConditional>("path_cond_record_j2.json");
    const card: PathConditional = { ...pc, model_id: POST, j_or_t: 1, source_kind: "RECORD_POST_D1", source_file: v.selected,
      params_sha256: "3f7640267cd0f6b114ec88cf29e811587daa18c191866f9fa2d6910bc949e5dc" };
    const withCard: PostD1VM = { mode: "OFFICIAL", view: { ...v, path_card: card }, error: null };
    const root = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, withCard, { tab: "return" })));
    const box = root.querySelector(".post-d1-path");
    expect(box?.querySelector("h4")?.textContent).toBe(COND.postD1PathCard);
    expect(box?.textContent).toContain(PATH_COND.sourceRecordPostD1(v.selected ?? "", "3f764026"));
    // senaryoda ek kart yok
    const sc = dom(renderConditional(vm("ceiling_netgl_j2.json", 2, { ...withCard, mode: "SCENARIO" }, { tab: "return" })));
    expect(sc.querySelector(".post-d1-path")).toBeNull();
  });
});

describe("K-P2-3: kartta D1 sonrası satırı (sentetik kayıt + gerçek scores_oot.json / scores_post_d1.json)", () => {
  const s = fx<CeilingSummary>("summary_post_d1_j2.json");
  const root = dom(renderCeilingSummary({ summary: s, streak: null, declared: NO_DECL }));
  const row = root.querySelector<HTMLElement>(`tr[data-role="POST_D1"]`);

  it("satır öne çıkanın hemen altında; adı \"D1 sonrası (post_d1_hazard_v0)\"; değerler kaydın S'inden", () => {
    expect(row).not.toBeNull();
    expect(row?.previousElementSibling?.getAttribute("data-role")).toBe("FEATURED");
    expect(row?.querySelector("th")?.textContent).toBe(COND.postD1Row);
    expect(row?.querySelector(".p-ge3")?.textContent).toBe(pct0(0.6 ** 3));
    expect(row?.querySelector(".p-break")?.textContent).toBe(pct0(0.4));
  });

  it("zaman-dışı: \"ayırt edilemiyor (zaman-dışı terazide)\" ve görünür \"karşılaştırıcı: ceiling_hazard_v0\"", () => {
    const vault = row?.querySelector<HTMLElement>("td.vault");
    expect(vault?.dataset.verdict).toBe(VERDICT.undecided);
    expect(vault?.textContent).toContain(`${VERDICT.undecided}${SUMMARY.vaultSuffix}`);
    expect(vault?.textContent).toContain("ayırt edilemiyor (zaman-dışı terazide)");
    expect(vault?.querySelector(".comparator")?.textContent).toContain(SUMMARY.comparator("ceiling_hazard_v0"));
    expect(vault?.textContent).toContain("karşılaştırıcı: ceiling_hazard_v0");
    // renk yalnız geçiyor/geçemiyor'da
    expect(vault?.classList.contains("win") || vault?.classList.contains("lose")).toBe(false);
  });

  it("yakın dönem \"—\"; canlı \"n = 0: hüküm yok\" (scores_post_d1.json n_live)", () => {
    expect(row?.querySelector("td.near-era")?.textContent).toBe("—");
    expect(row?.querySelector("td.near-era")?.getAttribute("title")).toBe(SUMMARY.postD1NearEraTip);
    expect(row?.querySelector("td.live")?.textContent).toBe(SUMMARY.liveNoVerdict("0"));
  });

  it("kapsam dışı kayıt: satır var, sayı yok, metin \"D1 tavanda kapanmadı\"", () => {
    const na = dom(renderCeilingSummary({ summary: fx<CeilingSummary>("summary_post_d1_na_j1.json"), streak: null, declared: NO_DECL }));
    const r = na.querySelector(`tr[data-role="POST_D1"]`);
    expect(r?.querySelector(".post-d1-na")?.textContent).toBe(COND.postD1NotApplicable);
    expect(r?.querySelector(".p-ge3")).toBeNull();
  });

  it("öteki satırlar değişmez: tek POST_D1 satırı, terazi sütunları üç ayrı sınıf", () => {
    expect(root.querySelectorAll(`tr[data-role="POST_D1"]`)).toHaveLength(1);
    for (const cls of ["scale-backtest", "scale-oot", "scale-live"]) expect(row?.querySelectorAll(`td.${cls}`)).toHaveLength(1);
  });
});

// ---------------------------------------------------------------- U70: Doğruluk sekmesi, scores_post_d1.json

const MODELS = fx<ModelInfo[]>("app_models.json");
const PATH_PARAMS = fx<PathParamsInfo[]>("path_params.json");

function postView(name: string): ScoresPostD1View {
  const all = fx<Record<string, ScoresPostD1View & { doc_file: string | null }>>("scores_post_d1_views.json");
  const { doc_file: file, ...rest } = all[name];
  return { ...rest, doc: file === null ? null : scoresDoc<ScoresPostD1Doc>(file) } as ScoresPostD1View;
}

function realPostView(): ScoresPostD1View {
  const doc = JSON.parse(readFileSync(join(APP_DIR, "..", "scores", "scores_post_d1.json"), "utf-8")) as ScoresPostD1Doc;
  return { status: "REPO", path: "scores/scores_post_d1.json", sha12: "gerçek dosya", generated_at_utc: doc.generated_at_utc ?? null,
    as_of_session: doc.as_of_session ?? null, unsupported_version: null, integrity: null, doc };
}

function section(postD1: ScoresPostD1View | null): HTMLElement {
  const v: AccuracyView = { scores: null, models: MODELS, pathParams: PATH_PARAMS, hidden: [], open: [], postD1 };
  const root = dom(renderAccuracy(v));
  const sec = root.querySelector<HTMLElement>(".panel-post-d1");
  if (!sec) throw new Error("bölüm yok");
  return sec;
}

describe("U70: Doğruluk sekmesinde D1 sonrası bölümü", () => {
  it("gerçek dosya: hücre yok, n = 0, RETRO 7 satır n'e girmez, kart H43 alanları, \"kesim\" sözcüğü yok", () => {
    const sec = section(realPostView());
    expect(sec.dataset.scale).toBe("live_post_d1");
    expect(sec.querySelector("h4")?.textContent).toBe("D1 sonrası güncelleme (canlı POST_D1, j = 1)");
    expect(sec.querySelector("table.cells")).toBeNull();
    expect(sec.querySelector(".post-d1-counts")?.getAttribute("data-n")).toBe("0");
    const retro = sec.querySelector<HTMLElement>(".post-d1-retro");
    expect(retro?.dataset.n).toBe("7");
    expect(retro?.querySelectorAll("li")).toHaveLength(7);
    expect(retro?.textContent).toContain(ACCURACY.postD1.retro(7));
    const card = sec.querySelector(".post-d1-card")?.textContent ?? "";
    expect(card).toContain(ACCURACY.postD1.lastSession);
    expect(card).toContain("2026-08-13");
    expect(card).toContain(ACCURACY.postD1.specCutoff);
    expect(card).toContain("2026-08-19");
    expect(card).toContain(ACCURACY.postD1.lastSessionMeaning);
    expect((sec.textContent ?? "").toLocaleLowerCase("tr")).not.toContain("kesim");
    // ayrı ölçek: koşulsuz panellerin içinde değil
    expect(sec.closest(".panel-live, .panel-backtest")).toBeNull();
  });

  it("sentetik n = 12: \"yetersiz örnek\", renk yok, satır tablosu", () => {
    const sec = section(postView("post_d1_n12"));
    expect(sec.querySelector(".insufficient-note")?.textContent).toBe(ACCURACY.insufficientNote);
    expect(sec.querySelectorAll(".badge-small-n").length).toBeGreaterThan(0);
    expect(sec.querySelectorAll("td.verdict.win, td.verdict.lose")).toHaveLength(0);
    expect(sec.querySelectorAll(".cond-rows tbody tr")).toHaveLength(12);
    expect(sec.querySelector(".synthetic")).not.toBeNull();
  });

  it("sentetik n = 35: dosyadaki hükümler ve renkler; birincil hücre işaretli", () => {
    const sec = section(postView("post_d1_n35"));
    const verdicts = [...sec.querySelectorAll<HTMLElement>("td.verdict")].map((td) => td.dataset.verdict);
    expect(verdicts).toEqual([VERDICT.pass, VERDICT.fail, VERDICT.undecided, VERDICT.undecided]);
    expect(sec.querySelectorAll("td.verdict.win")).toHaveLength(1);
    expect(sec.querySelectorAll("td.verdict.lose")).toHaveLength(1);
    const primary = sec.querySelector<HTMLElement>("tr.cell-row.primary");
    expect(primary?.dataset.rule).toBe("ceiling_hazard_v0");
    expect(primary?.dataset.scale).toBe("live_post_d1");
  });

  it("fail-closed ve durumlar: n = 8 iken hücre → kural metni; sürüm 2; repo modu değil; dosya yok", () => {
    const bad = section(postView("post_d1_bad_cells"));
    expect(bad.querySelector(".post-d1-integrity")?.getAttribute("data-rule")).toBe("CONDITIONAL_CELLS_BELOW_MIN_N");
    expect(bad.querySelector("table.cells")).toBeNull();
    expect(section(postView("post_d1_bad_verdict")).querySelector(".post-d1-integrity")?.getAttribute("data-rule")).toBe("VERDICT_WITHOUT_INTERVAL");
    expect(section(postView("post_d1_bad_version")).querySelector(".post-d1-version")?.textContent).toBe(ACCURACY.postD1.unsupported("borsai.scores_post_d1/2"));
    const none = (status: "NO_REPO" | "NO_FILE") => section({ status, path: null, sha12: null, generated_at_utc: null, as_of_session: null,
      unsupported_version: null, integrity: null, doc: null });
    expect(none("NO_REPO").querySelector(".post-d1-repo-only")?.textContent).toBe(ACCURACY.postD1.repoOnly);
    expect(none("NO_FILE").querySelector(".post-d1-no-file")?.textContent).toBe(ACCURACY.postD1.noFile);
  });
});

describe("ön uçta hesap yok (no_frontend_math genişlemesi, P2)", () => {
  it("render/post_d1.ts ve D1 sonrası bölümleri çarpma/bölme/üs içermez; S yalnız okunur", () => {
    for (const f of ["src/render/post_d1.ts", "src/render/ceiling.ts", "src/render/summary.ts", "src/render/accuracy.ts"]) {
      const { code } = split(readText(f));
      const bad = code.split("\n").filter((l) => /[^/*]\s*[*/%]\s*[^/*=]/.test(l) && !/^\s*import /.test(l));
      expect(bad, f).toEqual([]);
      expect(/\*\*|Math\.|\.reduce\s*\(/.test(code), f).toBe(false);
    }
    const { code } = split(readText("src/render/post_d1.ts"));
    expect(/S_cond\s*\[[^\]]*\]\s*[-+*/]/.test(code)).toBe(false);
  });
});
