// @vitest-environment jsdom
// "Tavan serisi — kaç gün tavan?" kartı (SPEC_APP EK 3 §5; U60, U62; K-P1-2, K-P1-4). Fixture'lar Rust'ın gerçek
// çıktısıdır (`src-tauri/tests/stage2.rs: ceiling_summary_fixtures`, `stage3.rs: official_summary_uses_record_only`);
// burada yalnız render sınanır: değerler fixture'daki alanların biçimlendirilmiş hâliyle birebir, ön uçta hesap yok.
import { describe, expect, it } from "vitest";

import { CEILING, COND, RESULTS, SUMMARY, TUFE, VERDICT } from "../src/i18n/tr";
import { fixed1, pct0, pctInt, pyRepr } from "../src/render/format";
import { renderResults, type ResultsView } from "../src/render/results";
import { renderCeilingSummary, renderFallSummary } from "../src/render/summary";
import type { CeilingDisplay, CeilingSummary, FallRow, FallSummary, ModelRun, StreakView, SummaryRow } from "../src/types";
import { dom, fx, readText, split } from "./helpers";

const NO_DECL = Array<boolean>(10).fill(false);

function card(s: CeilingSummary, streak: StreakView | null = null, declared: boolean[] = NO_DECL): HTMLElement {
  return dom(renderCeilingSummary({ summary: s, streak, declared }));
}

function cellText(root: HTMLElement, id: string, cls: string): string | undefined {
  return root.querySelector(`tr[data-model="${id}"] td.${cls}`)?.textContent ?? undefined;
}

function rowOf(s: CeilingSummary, id: string): SummaryRow {
  const r = s.rows.find((x) => x.model_id === id);
  if (!r) throw new Error(id);
  return r;
}

describe("U60: kasa kapalı (sentetik skorlar), j = 0", () => {
  const s = fx<CeilingSummary>("summary_closed_netgl_j0.json");
  const root = card(s);

  it("öne çıkan ceiling_hazard_v0, neden VAULT_CLOSED_V0_DEFAULT; başlık ve mod rozeti", () => {
    const sec = root.querySelector<HTMLElement>("section.summary-ceiling");
    expect(sec?.dataset.featured).toBe("ceiling_hazard_v0");
    expect(sec?.dataset.reason).toBe("VAULT_CLOSED_V0_DEFAULT");
    expect(root.querySelector("h3")?.textContent).toBe(SUMMARY.ceilingTitle);
    expect(root.querySelector(".featured-line")?.textContent).toBe(
      SUMMARY.featured("ceiling_hazard_v0", SUMMARY.featuredWhy.VAULT_CLOSED_V0_DEFAULT),
    );
    expect(root.querySelector(".mode-badge.scenario")).not.toBeNull();
  });

  it("değerler ceiling_display satırlarıyla birebir: S[2], S[4], S[9], beklenen, medyan", () => {
    const disp = fx<CeilingDisplay>("ceiling_netgl_j0.json");
    let n = 0;
    for (const r of s.rows.filter((x) => x.role !== "CONSTANT" && x.p_ge3 !== null)) {
      const c = disp.rows.find((x) => x.model_id === r.model_id);
      expect(c, r.model_id).toBeDefined();
      if (!c) continue;
      expect(cellText(root, r.model_id, "p-ge3"), r.model_id).toBe(pct0(c.S[2]));
      expect(cellText(root, r.model_id, "p-ge5"), r.model_id).toBe(pct0(c.S[4]));
      expect(cellText(root, r.model_id, "p-10"), r.model_id).toBe(pct0(c.S[9]));
      expect(cellText(root, r.model_id, "expected"), r.model_id).toBe(fixed1(c.expected_l));
      expect(cellText(root, r.model_id, "median"), r.model_id).toBe(String(c.median_l));
      n += 1;
    }
    expect(n).toBeGreaterThanOrEqual(9);
    const f = rowOf(s, "ceiling_hazard_v0");
    const head = root.querySelector(".summary-headline")?.textContent ?? "";
    expect(head).toContain(SUMMARY.expected(fixed1(f.expected_l)));
    expect(head).toContain(SUMMARY.medianDays(String(f.median_l)));
    expect(root.querySelector(".summary-probs")?.textContent).toBe(
      `${SUMMARY.pGe(3, pct0(f.p_ge3))} · ${SUMMARY.pGe(5, pct0(f.p_ge5))} · ${SUMMARY.p10(pct0(f.p_10))}`,
    );
  });

  it("j = 0: koşullu satır ve 'yarın' sütunu yok", () => {
    expect(root.querySelector(".summary-cond")).toBeNull();
    expect(root.querySelector("td.p-break")).toBeNull();
  });

  it("üç terazi üç sınıf ve 'toplanmaz' satırı; kasa: bekliyor; yakın dönem dosyadaki etiket", () => {
    const head = [...root.querySelectorAll<HTMLElement>(".summary-table:not(.pb-table) thead th")];
    expect(head.filter((h) => h.classList.contains("scale-backtest")).map((h) => h.textContent)).toEqual([SUMMARY.colNearEra]);
    expect(head.filter((h) => h.classList.contains("scale-oot")).map((h) => h.textContent)).toEqual([SUMMARY.colVault]);
    expect(head.filter((h) => h.classList.contains("scale-live")).map((h) => h.textContent)).toEqual([SUMMARY.colLive]);
    expect(root.querySelector(".scales-line")?.textContent).toContain(SUMMARY.scalesLine);
    for (const r of s.rows.filter((x) => x.role !== "CONSTANT" && x.role !== "PB")) {
      expect(cellText(root, r.model_id, "vault"), r.model_id).toBe(SUMMARY.vaultClosed);
    }
    expect(cellText(root, "ceiling_hazard_v1_clip", "near-era")).toBe("tolerans içinde");
    expect(cellText(root, "ceiling_hazard_v1_real", "near-era")).toBe("bozuyor");
    expect(cellText(root, "ceiling_hazard_v1_pooled", "near-era")).toBe("bozuyor");
    expect(cellText(root, "ceiling_hazard_v0", "near-era")).toBe("—");
    expect(cellText(root, "ceiling_hazard_v1_clip", "live")).toBe(SUMMARY.liveNoVerdict("0"));
  });

  it("satır sırası: öne çıkan → v1 adayları → kurallar → PB aynası (f3 dolu: katlı) → her zaman tavan", () => {
    const ids = [...root.querySelectorAll<HTMLElement>(".summary-table:not(.pb-table) tbody tr")].map((r) => r.dataset.model);
    expect(ids).toEqual([
      "ceiling_hazard_v0", "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled",
      "ceiling_hazard_v1_pooled@INF", "ceiling_hazard_v0@INF", "base_km_expanding", "base_km_last10", "ALWAYS_CEILING",
    ]);
    const pb = root.querySelector<HTMLDetailsElement>("details.pb-mirror");
    expect(pb?.open).toBe(false);
    expect(pb?.querySelector("summary")?.textContent).toContain(SUMMARY.pbMirror);
    expect(cellText(root, "ALWAYS_CEILING", "vault")).toBe("—");
  });

  it("TÜFE satırı (T = 2026-09-17 → 2026-07 = 132.31, gömülü tablo, pin ✓)", () => {
    expect(root.querySelector(".tufe-line")?.textContent).toBe(
      TUFE.line("2026-07", "132.31", "2026-08-03", TUFE.sourceText.EMBEDDED, TUFE.pinOk),
    );
  });
});

describe("U60: j = 2 (varsayımsal)", () => {
  const s = fx<CeilingSummary>("summary_closed_netgl_j2.json");
  const root = card(s);
  it("koşullu satır Rust cond alanlarından; 'yarın' sütunu", () => {
    const c = rowOf(s, "ceiling_hazard_v0").cond;
    expect(c).not.toBeNull();
    if (!c) return;
    expect(root.querySelector(".summary-cond")?.textContent).toBe(
      SUMMARY.condLine(2, SUMMARY.jHypothetical, pct0(c.p_break_next), fixed1(c.expected_remaining), pct0(c.s_cond_5), pct0(c.s_cond_10)),
    );
    expect(cellText(root, "ceiling_hazard_v0", "p-break")).toBe(pct0(c.p_break_next));
  });
});

describe("U60: en olası bozulma günü üç dal (sentetik S)", () => {
  const s = fx<CeilingSummary>("summary_mode_branches.json");
  const featuring = (id: string): CeilingSummary => ({
    ...s,
    rows: s.rows.map((r) => ({ ...r, role: r.model_id === id ? "FEATURED" : r.role === "FEATURED" ? "CANDIDATE" : r.role })),
  });
  it("l = 0 · orta · 10", () => {
    const m0 = rowOf(s, "ceiling_hazard_v0");
    expect(card(s).querySelector(".summary-mode")?.textContent).toBe(`${SUMMARY.modeLabel}: ${SUMMARY.modeNone(pct0(m0.p_mode))}`);
    const mid = rowOf(s, "ceiling_hazard_v0@INF");
    expect(mid.mode_l).toBe(2);
    expect(card(featuring("ceiling_hazard_v0@INF")).querySelector(".summary-mode")?.textContent).toBe(
      `${SUMMARY.modeLabel}: ${SUMMARY.modeDay(3, 2, pct0(mid.p_mode))}`,
    );
    const top = rowOf(s, "base_km_expanding");
    expect(top.mode_l).toBe(10);
    expect(card(featuring("base_km_expanding")).querySelector(".summary-mode")?.textContent).toBe(
      `${SUMMARY.modeLabel}: ${SUMMARY.modeCensored(pct0(top.p_mode))}`,
    );
  });
});

describe("K3: gerçek scores.json + scores_oot.json (kasa açıldı)", () => {
  const s = fx<CeilingSummary>("summary_real_netgl_j0.json");
  const root = card(s);

  it("öne çıkan ceiling_hazard_v0, neden RULE_5_5_NONE_ELIGIBLE_V0; K-P1-2 metni", () => {
    expect(s.featured.model_id).toBe("ceiling_hazard_v0");
    expect(s.featured.reason).toBe("RULE_5_5_NONE_ELIGIBLE_V0");
    expect(root.querySelector(".featured-line")?.textContent).toBe("öne çıkan: ceiling_hazard_v0 (kasa sonrası kural: uygun v1 adayı yok)");
    const k = s.featured.candidates.map((c) => [c.model_id, c.k1, c.k2, c.k3, c.eligible]);
    expect(k).toEqual([
      ["ceiling_hazard_v1_clip", false, true, true, false],
      ["ceiling_hazard_v1_real", false, true, false, false],
      ["ceiling_hazard_v1_pooled", true, true, false, false],
    ]);
  });

  it("zaman-dışı (kasa) sütunu dosyadaki verdict + terazi eki; renk yalnız geçiyor/geçemiyor", () => {
    const undecided = `${VERDICT.undecided}${SUMMARY.vaultSuffix}`;
    for (const id of ["ceiling_hazard_v0", "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real"]) {
      expect(cellText(root, id, "vault"), id).toBe(undecided);
    }
    expect(cellText(root, "ceiling_hazard_v1_pooled", "vault")).toBe(`${VERDICT.pass}${SUMMARY.vaultSuffix}`);
    expect(root.querySelector('tr[data-model="ceiling_hazard_v1_pooled"] td.vault')?.classList.contains("win")).toBe(true);
    expect(root.querySelector('tr[data-model="ceiling_hazard_v1_clip"] td.vault')?.classList.contains("win")).toBe(false);
    for (const id of ["base_km_expanding", "base_km_last10", "ceiling_hazard_v0@INF", "ceiling_hazard_v1_pooled@INF"]) {
      expect(cellText(root, id, "vault"), `${id}: birincil hücresi yok`).toBe("—");
    }
  });

  it("yakın dönem: clip tolerans içinde, real/pooled bozuyor, pooled@INF bozuyor; v0 ve KM —", () => {
    expect(cellText(root, "ceiling_hazard_v1_clip", "near-era")).toBe("tolerans içinde");
    for (const id of ["ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"]) {
      expect(cellText(root, id, "near-era"), id).toBe("bozuyor");
    }
    for (const id of ["ceiling_hazard_v0", "base_km_expanding", "base_km_last10"]) {
      expect(cellText(root, id, "near-era"), id).toBe("—");
    }
    expect(root.querySelector(".scales-line")?.textContent).toContain(SUMMARY.nearEraFoot("78", "22"));
  });

  it("canlı sicil: n < 10 → hüküm yok (dosyadaki n)", () => {
    const v0 = rowOf(s, "ceiling_hazard_v0");
    expect(cellText(root, "ceiling_hazard_v0", "live")).toBe(SUMMARY.liveNoVerdict(String(v0.live.n_scored)));
    expect(cellText(root, "ceiling_hazard_v1_pooled", "live")).toBe(SUMMARY.liveNoVerdict("0"));
  });

  it("VEYAS (f3 boş): öne çıkan RET · F3_MISSING, v1 üçü RET, PB aynası açık", () => {
    const v = fx<CeilingSummary>("summary_real_veyas_j0.json");
    const r = card(v);
    expect(r.querySelector(".summary-headline.refused")?.textContent).toContain(SUMMARY.refused("F3_MISSING"));
    for (const id of ["ceiling_hazard_v0", "ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled"]) {
      expect(cellText(r, id, "refused-cell"), id).toBe(SUMMARY.refused("F3_MISSING"));
      expect(cellText(r, id, "vault"), `${id}: sütun kaybolmaz`).toBeDefined();
    }
    expect(r.querySelector<HTMLDetailsElement>("details.pb-mirror")?.open).toBe(true);
    expect(cellText(r, "ceiling_hazard_v1_pooled@INF", "p-ge3")).toBe(pct0(rowOf(v, "ceiling_hazard_v1_pooled@INF").p_ge3));
  });
});

describe("Grup B katlanır ayrıntı (EK 3 §5.1)", () => {
  it("kart Grup A'dan önce; Grup B <details> içinde ve varsayılan kapalı", () => {
    const runs = fx<ModelRun[]>("runs_netgl.json");
    const v: ResultsView = {
      runs, pathDisplay: [], pathParams: [], ceiling: fx<CeilingDisplay>("ceiling_netgl_j0.json"), hints: null, models: [],
      hidden: [], scenario: null, f6: null, openCard: null, openWarnings: null, savedId: null, canSave: false, repoMode: false,
      summaryHtml: renderCeilingSummary({ summary: fx<CeilingSummary>("summary_closed_netgl_j0.json"), streak: null, declared: NO_DECL }),
    };
    const root = dom(renderResults(v));
    const html = root.innerHTML;
    expect(html.indexOf("summary-ceiling")).toBeLessThan(html.indexOf("group-a"));
    const det = root.querySelector<HTMLDetailsElement>("details.group-b-details");
    expect(det?.open).toBe(false);
    expect(det?.querySelector("section.group-b")).not.toBeNull();
    expect(det?.querySelector("summary")?.textContent).toBe(SUMMARY.detailGroupB);
    expect(root.querySelector("[data-action=open-group-b]")).not.toBeNull();
  });
});

describe("U62: resmi görünümde kart yalnız kayıttan", () => {
  it("S = 0.5^k kaydı: P(≥ 3) = %13, koşullu 0.5^(k − j); RESMİ KAYIT ve kaynak satırı", () => {
    const s = fx<CeilingSummary>("summary_record_j2.json");
    const root = card(s);
    expect(root.querySelector(".mode-badge.official")).not.toBeNull();
    expect(root.textContent).toContain(SUMMARY.officialSource(s.record_file ?? "", (s.featured_params_sha256 ?? "").slice(0, 8)));
    expect(cellText(root, "ceiling_hazard_v0", "p-ge3")).toBe(pct0(0.125));
    expect(root.querySelector(".summary-cond")?.textContent).toBe(
      SUMMARY.condLine(2, SUMMARY.jObserved, pct0(0.5), fixed1(rowOf(s, "ceiling_hazard_v0").cond?.expected_remaining ?? null), pct0(0.125), pct0(0.5 ** 8)),
    );
    expect(root.querySelector(".tufe-line")?.textContent).toBe(TUFE.line("2026-08", "134.75", "2026-09-03", "RECORD", TUFE.pinOk));
  });

  it("16 modelli kayıt: v1 satırları 'kayıt bu modeli içermiyor', listeden kalkmaz (K4)", () => {
    const root = card(fx<CeilingSummary>("summary_record16_j0.json"));
    for (const id of ["ceiling_hazard_v1_clip", "ceiling_hazard_v1_real", "ceiling_hazard_v1_pooled", "ceiling_hazard_v1_pooled@INF"]) {
      expect(cellText(root, id, "not-in-record"), id).toBe(SUMMARY.recordWithoutModel);
    }
  });

  it("U52 karta genişler: beyan resmi verinin önündeyse koşullu satır yalnız 'resmi kapanış bekleniyor'", () => {
    const s = fx<CeilingSummary>("summary_closed_netgl_j2.json");
    const streak = fx<StreakView>("streak_sntb1.json"); // D1–D2 resmi tavan, D3 bekliyor
    const decl = [false, false, true, false, false, false, false, false, false, false];
    const root = card(s, streak, decl);
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    const c = rowOf(s, "ceiling_hazard_v0").cond;
    const cond = root.querySelector(".summary-cond");
    expect(cond?.classList.contains("official-pending")).toBe(true);
    expect(cond?.textContent).not.toContain(pct0(c?.s_cond_5 ?? null));
    // beyan resmi veriyle aynı günde (D1: dosyada tavan) → etiket kalkar, koşullu satır normal
    const same = card(s, streak, [true, false, false, false, false, false, false, false, false, false]);
    expect(same.querySelector(".official-pending")).toBeNull();
  });
});

describe("ön uçta hesap yok: summary.ts yalnız biçimlendirir (U25 genişlemesi)", () => {
  it("S indekslenmez, gün numarası ya da olasılık türetilmez; Math/aritmetik yok", () => {
    const { code } = split(readText("src/render/summary.ts"));
    expect(/\bS\s*\[/.test(code)).toBe(false);
    expect(/Math\./.test(code)).toBe(false);
    expect(/\+\s*1\b|-\s*1\b/.test(code)).toBe(false);
    expect(/\.(reduce|sort)\s*\(/.test(code)).toBe(false);
    expect(/\bP_L\b/.test(code)).toBe(false);
    // kartın sayıları yalnız Rust alanlarından: p_ge3, p_ge5, p_10, expected_l, median_l, mode_l, cond
    for (const f of ["p_ge3", "p_ge5", "p_10", "expected_l", "median_l", "mode_break_day", "p_break_next", "s_cond_5"]) {
      expect(code, f).toContain(f);
    }
    expect(RESULTS.watermark).toBe("SENARYO");
    expect(CEILING.always).toBe("her zaman tavan");
  });
});

// ---------------------------------------------------------------- "Düşüş (D10)" kartı (EK 3 §8.4; U79, K-P4-1, K-P4-2)

function fallCard(f: FallSummary): HTMLElement {
  return dom(renderFallSummary(f));
}

function fallRow(f: FallSummary, id: string): FallRow {
  const r = f.rows.find((x) => x.model_id === id);
  if (!r) throw new Error(id);
  return r;
}

describe("U79: düşüş kartı, kasa kapalı (sentetik)", () => {
  const f = fx<FallSummary>("summary_fall_closed_netgl.json");
  const root = fallCard(f);

  it("başlık, mod rozeti, öne çıkan yok — kasa: bekliyor; büyük satır yok, V1.5 notu", () => {
    const sec = root.querySelector<HTMLElement>("section.summary-fall");
    expect(sec?.dataset.reason).toBe("VAULT_CLOSED");
    expect(sec?.dataset.featured).toBe("");
    expect(root.querySelector("h3")?.textContent).toBe(SUMMARY.fallTitle);
    expect(root.querySelector(".featured-line")?.textContent).toBe(SUMMARY.fallVaultClosed);
    expect(root.querySelector(".mode-badge.scenario")).not.toBeNull();
    expect(root.querySelector(".fall-headline")).toBeNull();
    expect(root.querySelector(".fall-v15-note")?.textContent).toBe(SUMMARY.fallV15Note);
  });

  it("aday sırası addsale, h99, pooled, @ZERO; karşılaştırıcılar base_rate, v1_5_h99 (rozetli); kasa sütunu bekliyor", () => {
    const ids = [...root.querySelectorAll<HTMLElement>("tr.summary-row")].map((r) => r.dataset.model);
    expect(ids).toEqual(["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO", "base_rate", "v1_5_h99"]);
    expect(root.querySelector('tr[data-model="fall_d10_v0_pooled@ZERO"] th')?.textContent).toBe(`${SUMMARY.fallRule} · fall_d10_v0_pooled@ZERO`);
    for (const c of ["base_rate", "v1_5_h99"]) {
      expect(root.querySelector(`tr[data-model="${c}"] .comparator-badge`)?.textContent).toBe(SUMMARY.comparatorBadge);
      expect(root.querySelector(`tr[data-model="${c}"] td.vault`)?.textContent).toBe("—");
    }
    for (const id of ["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled"]) {
      expect(root.querySelector(`tr[data-model="${id}"] td.vault`)?.textContent).toBe(SUMMARY.vaultClosed);
      expect(root.querySelector(`tr[data-model="${id}"] td.rule-5-5`)?.textContent).toBe("—");
    }
  });

  it("P(D10 ≤ arz) ve P(D5 ≤ arz) Rust yüzdelerinin biçimi (1 − p_up Rust'ta); ham değer tooltip'te", () => {
    for (const r of f.rows) {
      const tds = root.querySelectorAll<HTMLElement>(`tr[data-model="${r.model_id}"] td.p-fall`);
      expect(tds[0]?.textContent, r.model_id).toBe(pctInt(r.d10.pct_fall));
      expect(tds[1]?.textContent, r.model_id).toBe(pctInt(r.d5.pct_fall));
      expect(tds[0]?.getAttribute("title")).toBe(SUMMARY.fallRawTip(pyRepr(r.d10.p_up), pyRepr(r.d10.p_fall)));
    }
  });

  it("üç terazi üç sınıf; toplanmaz satırı; TÜFE satırı", () => {
    const head = root.querySelector("thead tr");
    expect(head?.querySelector(".scale-backtest")?.textContent).toBe(SUMMARY.colNearEra);
    expect(head?.querySelector(".scale-oot")?.textContent).toBe(SUMMARY.colVault);
    expect(head?.querySelector(".scale-live")?.textContent).toBe(SUMMARY.colLive);
    expect(root.querySelector(".scales-line")?.textContent).toContain(SUMMARY.scalesLine);
    expect(root.querySelector(".tufe-line")).not.toBeNull();
  });
});

describe("U79: düşüş kartı, öne çıkan aday (sentetik kasa)", () => {
  const f = fx<FallSummary>("summary_fall_featured_netgl.json");
  const root = fallCard(f);
  const top = fallRow(f, "fall_d10_v0_h99");

  it("öne çıkan h99 ilk satır (★); büyük satır P(D10 kapanışı ≤ arz fiyatı) = %k, altında P(kapanış > arz) = %(100 − k); D5 ikincil", () => {
    expect(root.querySelector<HTMLElement>("section.summary-fall")?.dataset.featured).toBe("fall_d10_v0_h99");
    expect(root.querySelector(".featured-line")?.textContent).toBe(SUMMARY.fallFeatured("fall_d10_v0_h99"));
    expect(root.querySelector("tr.summary-row")?.getAttribute("data-role")).toBe("FEATURED");
    expect(root.querySelector("tr.summary-row th")?.textContent).toBe(`${SUMMARY.featuredMark} fall_d10_v0_h99`);
    expect(root.querySelector(".fall-headline")?.textContent).toBe(SUMMARY.pFall("D10", pctInt(top.d10.pct_fall)));
    expect(root.querySelector(".fall-headline + .summary-probs")?.textContent).toBe(SUMMARY.pUpLine(pctInt(top.d10.pct_up)));
    expect(root.querySelector(".fall-d5")?.textContent).toBe(
      `${SUMMARY.pFall("D5", pctInt(top.d5.pct_fall))} · ${SUMMARY.pUpLine(pctInt(top.d5.pct_up))}`,
    );
    expect((top.d10.pct_fall ?? 0) + (top.d10.pct_up ?? 0)).toBe(100);
    expect(root.querySelector('tr[data-model="fall_d10_v0_h99"] td.rule-5-5')?.textContent).toBe(SUMMARY.fallEligible);
    expect(root.querySelector('tr[data-model="fall_d10_v0_pooled"] td.rule-5-5')?.textContent).toBe(SUMMARY.fallWhy.k2);
  });
});

describe("K2: düşüş kartı gerçek scores.json + scores_oot.json ile (K-P4-1, K-P4-2)", () => {
  const f = fx<FallSummary>("summary_fall_real_netgl.json");
  const root = fallCard(f);
  const vault = (id: string) => root.querySelector(`tr[data-model="${id}"] td.vault`);
  const near = (id: string) => root.querySelector(`tr[data-model="${id}"] td.near-era`);

  it("öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok (SPEC_C §9'un 'kasada geçen aday yok' metni değil)", () => {
    expect(root.querySelector<HTMLElement>("section.summary-fall")?.dataset.reason).toBe("RULE_5_5_NONE_ELIGIBLE");
    expect(root.querySelector(".featured-line")?.textContent).toBe("öne çıkan yok — kasa sonrası kural (§5.5): uygun aday yok");
    expect(root.textContent).not.toContain("kasada geçen aday yok");
    expect(root.querySelector(".fall-headline")).toBeNull();
  });

  it("ilk sağlanmayan koşul düz metinle: pooled k2, h99 ve addsale k1", () => {
    const why = (id: string) => root.querySelector(`tr[data-model="${id}"] td.rule-5-5`)?.textContent;
    expect(why("fall_d10_v0_pooled")).toBe("kasada V1.5'ten ayırt edilemiyor");
    expect(why("fall_d10_v0_h99")).toBe("kasada taban orandan ayırt edilemiyor");
    expect(why("fall_d10_v0_addsale")).toBe("kasada taban orandan ayırt edilemiyor");
    expect(why("fall_d10_v0_pooled@ZERO")).toBe("—");
  });

  it("zaman-dışı: kasa birincil hücresinin verdict'i + (zaman-dışı terazide) ve karşılaştırıcısı; renk yalnız geçiyor", () => {
    expect(vault("fall_d10_v0_pooled")?.textContent).toBe(`${VERDICT.pass}${SUMMARY.vaultSuffix} · ${SUMMARY.comparator("base_rate")}`);
    expect(vault("fall_d10_v0_pooled")?.classList.contains("win")).toBe(true);
    for (const id of ["fall_d10_v0_h99", "fall_d10_v0_addsale"]) {
      expect(vault(id)?.textContent).toBe(`${VERDICT.undecided}${SUMMARY.vaultSuffix} · ${SUMMARY.comparator("base_rate")}`);
      expect(vault(id)?.classList.contains("win") || vault(id)?.classList.contains("lose")).toBe(false);
    }
    expect(vault("fall_d10_v0_pooled")?.textContent).toBe("geçiyor (zaman-dışı terazide) · karşılaştırıcı: base_rate");
    expect(vault("fall_d10_v0_h99")?.textContent).toBe("ayırt edilemiyor (zaman-dışı terazide) · karşılaştırıcı: base_rate");
  });

  it("yakın dönem: etiket + karşılaştırıcı dosyadan (h99 tolerans içinde, pooled belirsiz/h99, addsale belirsiz, @ZERO tolerans içinde)", () => {
    for (const [id, label, cmp] of [
      ["fall_d10_v0_h99", "tolerans içinde", "base_rate"],
      ["fall_d10_v0_pooled", "belirsiz", "fall_d10_v0_h99"],
      ["fall_d10_v0_addsale", "belirsiz", "base_rate"],
      ["fall_d10_v0_pooled@ZERO", "tolerans içinde", "base_rate"],
    ]) {
      expect(near(id)?.textContent, id).toBe(`${label} · ${SUMMARY.comparator(cmp)}`);
      expect(near(id)?.getAttribute("data-label")).toBe(fallRow(f, id).near_era?.label);
    }
  });

  it("canlı: n < 10 → 'n = 0: hüküm yok'; karşılaştırıcı satırlarında terazi —; model kartları", () => {
    for (const id of ["fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_addsale", "fall_d10_v0_pooled@ZERO"]) {
      expect(root.querySelector(`tr[data-model="${id}"] td.live`)?.textContent).toBe(SUMMARY.liveNoVerdict("0"));
    }
    expect(root.querySelector('tr[data-model="v1_5_h99"] td.live')?.textContent).toBe("—");
    const cards = [...root.querySelectorAll<HTMLElement>("li.fall-card")].map((c) => c.dataset.model);
    expect(cards).toEqual(["fall_d10_v0_addsale", "fall_d10_v0_h99", "fall_d10_v0_pooled", "fall_d10_v0_pooled@ZERO"]);
    expect(root.querySelector('li.fall-card[data-model="fall_d10_v0_h99"]')?.textContent).toContain(SUMMARY.fallPrimary);
  });

  it("VEYAS (f3 boş): h99 ve pooled RET · F3_MISSING (talep katı metni), addsale ve @ZERO dolu", () => {
    const v = fx<FallSummary>("summary_fall_real_veyas.json");
    const r = fallCard(v);
    for (const id of ["fall_d10_v0_h99", "fall_d10_v0_pooled"]) {
      const td = r.querySelector(`tr[data-model="${id}"] td.refused-cell`);
      expect(td?.getAttribute("data-code")).toBe("F3_MISSING");
      expect(td?.textContent).toContain(SUMMARY.refused("F3_MISSING"));
      expect(td?.textContent).toContain(SUMMARY.fallRefused.F3_MISSING);
    }
    expect(r.querySelectorAll('tr[data-model="fall_d10_v0_addsale"] td.p-fall').length).toBe(2);
    expect(r.querySelectorAll('tr[data-model="fall_d10_v0_pooled@ZERO"] td.p-fall').length).toBe(2);
  });

  it("tavan serisi kartının hemen altında ikinci özet kart (aynı render çağrısı)", () => {
    const s = { ...fx<CeilingSummary>("summary_real_netgl_j0.json"), fall: f };
    const both = card(s);
    const secs = [...both.querySelectorAll("section.summary")].map((x) => x.className);
    expect(secs).toEqual(["summary summary-ceiling", "summary summary-fall"]);
    expect(card({ ...s, fall: null }).querySelector("section.summary-fall")).toBeNull();
  });
});

describe("resmi görünümde düşüş kartı yalnız kayıttan (U62 kalıbı)", () => {
  it("kayıttaki p_up 0.6 / 0.75 → %40 / %25; RESMİ KAYIT ve kaynak satırı", () => {
    const f = fx<FallSummary>("summary_fall_record.json");
    const root = fallCard(f);
    expect(root.querySelector(".mode-badge.official")).not.toBeNull();
    expect(root.textContent).toContain(f.record_file ?? "?");
    for (const r of f.rows) {
      const tds = root.querySelectorAll<HTMLElement>(`tr[data-model="${r.model_id}"] td.p-fall`);
      expect([tds[0]?.textContent, tds[1]?.textContent], r.model_id).toEqual(["%40", "%25"]);
    }
  });
});

describe("ön uçta hesap yok: düşüş kartı yalnız Rust yüzdelerini biçimlendirir", () => {
  it("1 − p_up ve 100 − k ön uçta yok; pct_fall / pct_up / p_fall okunur", () => {
    const { code } = split(readText("src/render/summary.ts"));
    expect(/100\s*-/.test(code)).toBe(false);
    for (const fld of ["pct_fall", "pct_up", "p_fall", "first_failed"]) expect(code, fld).toContain(fld);
  });
});
