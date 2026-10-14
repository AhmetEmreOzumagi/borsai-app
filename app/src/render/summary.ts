// "Tavan serisi — kaç gün tavan?" özet kartı (SPEC_APP EK 3 §5) saf render. Bütün değerler Rust `ceiling_summary` /
// `record_summary` çıktısından gelir (ceiling_display satırları, scores.json ve scores_oot.json okuyucuları, öne çıkarma
// kuralı); burada yalnız biçimlendirme ve yerleşim vardır. Üç terazi üç ayrı sütundur, hiçbir yerde toplanmaz.
import { CEILING, COND, RESULTS, SUMMARY, TR, TUFE, VERDICT } from "../i18n/tr";
import type { CeilingSummary, FallRow, FallSummary, NearEraView, StreakView, SummaryRow, TufeInfo } from "../types";
import { esc } from "../dom";
import { MIN_N_METRIC } from "./card";
import { declarationState } from "./ceiling";
import { DASH, fixed1, metric4, pct0, pctInt, pyRepr, sha8 } from "./format";

/**
 * TÜFE satırı (EK 3 §3.3–§3.4): kullanılan ay, endeks, yayım günü, kaynak ve pin; ret nedeni; ay eksikse Python'un
 * aylık ekleme komutu (uygulama çalıştırmaz). Bütün alanlar Rust `TufeInfo`'dan; burada hesap yok.
 */
export function renderTufeInfo(info: TufeInfo | null): string {
  if (!info) return "";
  const src = TUFE.sourceText[info.source] ?? info.source;
  if (info.reason === "MONTH_MISSING") {
    return `<div class="tufe-line tufe-missing warn-box" data-reason="MONTH_MISSING"><p>${esc(TUFE.missingMonth(info.month ?? DASH))}</p>` +
      `<pre class="mono small append-command">${esc(info.append_command ?? "")}</pre><p class="small muted">${esc(TUFE.commandNote)}</p></div>`;
  }
  const text = info.reason === "T_UNKNOWN"
    ? TUFE.tUnknown
    : info.reason === "TABLE_INVALID"
      ? TUFE.invalid(info.detail ?? DASH)
      : info.reason === "NOT_PIT"
        ? TUFE.notPit(info.month ?? DASH, info.release_date ?? DASH)
        : info.reason === "PIN_MISMATCH"
          ? TUFE.pinMismatch
          : TUFE.line(info.month ?? DASH, info.index ?? DASH, info.release_date ?? DASH, src, info.pin_ok ? TUFE.pinOk : TUFE.pinBad);
  const cls = info.refusal ? "tufe-line warn-box" : "tufe-line small muted";
  return `<p class="${cls}" data-reason="${esc(info.reason ?? "OK")}" title="${esc(TUFE.noManual)}">${esc(text)}</p>`;
}

export interface SummaryVM {
  summary: CeilingSummary | null;
  /** Şerit (resmi gün durumları); beyanın resmi verinin önünde olup olmadığı yalnız bundan okunur. */
  streak: StreakView | null;
  /** D1..D10 "seri sürüyor" beyanı: yalnız etiket (U52). Resmi verinin önündeyse koşullu satır "resmi kapanış bekleniyor". */
  declared: boolean[];
}

/** Beyan resmi verinin önünde mi (U52-3; `render/ceiling.ts: declarationState` ile aynı kural, sayı üretmez). */
function pendingOfficial(vm: SummaryVM): boolean {
  return (vm.streak?.days ?? []).some((d, i) => declarationState(d.file, vm.declared[i] === true) === "AHEAD");
}

function rowLabel(r: SummaryRow): string {
  if (r.role === "CONSTANT") return CEILING.always;
  if (r.role === "POST_D1") return COND.postD1Row;
  if (r.role === "FEATURED") return `${SUMMARY.featuredMark} ${r.model_id}`;
  if (r.role === "RULE") return `${SUMMARY.roleRule} · ${r.model_id}`;
  return r.model_id;
}

function nearEraCell(n: NearEraView | null, role: SummaryRow["role"] = "CANDIDATE"): string {
  if (role === "POST_D1") return `<td class="scale-backtest near-era" title="${esc(SUMMARY.postD1NearEraTip)}">${DASH}</td>`;
  if (!n) return `<td class="scale-backtest near-era" title="${esc(SUMMARY.nearEraMissing)}">${DASH}</td>`;
  if (!n.supported) return `<td class="scale-backtest near-era unsupported">${esc(SUMMARY.nearEraUnsupported(n.schema_version ?? DASH))}</td>`;
  const ci = (n.ci95 ?? []).map((x) => metric4(x)).join(", ");
  const tip = SUMMARY.nearEraTip(n.comparator ?? DASH, metric4(n.diff), ci, String(n.n ?? DASH), String(n.n_blocks ?? DASH));
  return `<td class="scale-backtest near-era" data-label="${esc(n.label ?? "")}" title="${esc(tip)}">${esc(n.label ?? DASH)}</td>`;
}

/** Dosyadaki verdict aynen; geçiyor / geçemiyor / ayırt edilemiyor'a terazi eki, renk yalnız ilk ikisinde. */
function vaultCell(r: SummaryRow): string {
  const v = r.vault;
  if (v.status === "CLOSED") return `<td class="scale-oot vault" data-status="CLOSED">${esc(SUMMARY.vaultClosed)}</td>`;
  if (v.status === "UNAVAILABLE") return `<td class="scale-oot vault" data-status="UNAVAILABLE" title="${esc(SUMMARY.vaultUnavailable)}">${DASH}</td>`;
  if (v.status !== "OPEN" || v.verdict === null) return `<td class="scale-oot vault" data-status="${esc(v.status)}">${DASH}</td>`;
  const suffixed = v.verdict === VERDICT.pass || v.verdict === VERDICT.fail || v.verdict === VERDICT.undecided;
  const cls = v.verdict === VERDICT.pass ? " win" : v.verdict === VERDICT.fail ? " lose" : "";
  const ci = (v.ci95 ?? []).map((x) => metric4(x)).join(", ");
  const tip = `${v.rule_id ?? ""} · ${metric4(v.diff)} [${ci}] · n = ${v.n ?? DASH}`;
  // D1 sonrası satırı (K-P2-3): birincil hücre basit kurala değil ebeveyn modele karşıdır; karşılaştırıcı görünür yazılır
  const cmp = r.role === "POST_D1" && v.rule_id ? ` <span class="comparator small">· ${esc(SUMMARY.comparator(v.rule_id))}</span>` : "";
  return `<td class="scale-oot vault${cls}" data-status="OPEN" data-verdict="${esc(v.verdict)}" title="${esc(tip)}">` +
    `${esc(suffixed ? `${v.verdict}${SUMMARY.vaultSuffix}` : v.verdict)}${cmp}</td>`;
}

function liveCell(r: SummaryRow): string {
  const n = r.live.n_scored;
  if (r.role === "CONSTANT" || n === null) return `<td class="scale-live live">${DASH}</td>`;
  const text = n < MIN_N_METRIC ? SUMMARY.liveNoVerdict(String(n)) : r.live.verdict ?? DASH;
  return `<td class="scale-live live" data-n="${n}">${esc(text)}</td>`;
}

function numCells(r: SummaryRow, j: number): string {
  const nNum = j > 0 ? 6 : 5;
  if (!r.in_record) return `<td class="not-in-record muted" colspan="${nNum}">${esc(SUMMARY.recordWithoutModel)}</td>`;
  if (r.role === "POST_D1" && r.status === "NOT_APPLICABLE") {
    return `<td class="post-d1-na muted" colspan="${nNum}" data-code="${esc(r.refused?.code ?? "")}">${esc(COND.postD1NotApplicable)}</td>`;
  }
  if (r.refused || r.p_ge3 === null) {
    const code = r.refused?.code ?? DASH;
    return `<td class="refused-cell" colspan="${nNum}" data-code="${esc(code)}">${esc(SUMMARY.refused(code))}</td>`;
  }
  const tip = (x: number | null) => `${RESULTS.raw}: ${pyRepr(x)}`;
  const cells = [
    `<td class="num expected" title="${esc(CEILING.expectedLTip)}">${esc(fixed1(r.expected_l))}</td>`,
    `<td class="num median" title="${esc(CEILING.medianLTip)}">${esc(String(r.median_l ?? DASH))}</td>`,
    `<td class="num p-ge3" title="${esc(tip(r.p_ge3))}">${esc(pct0(r.p_ge3))}</td>`,
    `<td class="num p-ge5" title="${esc(tip(r.p_ge5))}">${esc(pct0(r.p_ge5))}</td>`,
    `<td class="num p-10" title="${esc(tip(r.p_10))}">${esc(pct0(r.p_10))}</td>`,
  ];
  if (j > 0) cells.push(`<td class="num p-break" title="${esc(tip(r.cond?.p_break_next ?? null))}">${esc(r.cond ? pct0(r.cond.p_break_next) : DASH)}</td>`);
  return cells.join("");
}

function tableRow(r: SummaryRow, j: number): string {
  const cls = ["summary-row", `role-${r.role.toLowerCase()}`, r.role === "CONSTANT" ? "muted" : ""].filter(Boolean).join(" ");
  return `<tr class="${cls}" data-model="${esc(r.model_id)}" data-role="${esc(r.role)}"><th class="mono">${esc(rowLabel(r))}</th>` +
    numCells(r, j) + nearEraCell(r.near_era, r.role) + vaultCell(r) + liveCell(r) + `</tr>`;
}

function tableHead(j: number): string {
  const cols = [SUMMARY.colModel, SUMMARY.colExpected, SUMMARY.colMedian, SUMMARY.colPGe3, SUMMARY.colPGe5, SUMMARY.colP10];
  if (j > 0) cols.push(SUMMARY.colBreak);
  return `<tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}` +
    `<th class="scale-backtest">${esc(SUMMARY.colNearEra)}</th><th class="scale-oot">${esc(SUMMARY.colVault)}</th>` +
    `<th class="scale-live">${esc(SUMMARY.colLive)}</th></tr>`;
}

/** Öne çıkan modelin büyük yazılı özeti (beklenen/medyan, olasılıklar, en olası bozulma günü). */
function headline(f: SummaryRow | undefined): string {
  if (!f) return "";
  if (f.refused || f.p_ge3 === null || !f.in_record) {
    const code = f.refused?.code ?? DASH;
    return `<p class="summary-headline refused" data-code="${esc(code)}">${esc(SUMMARY.headRefused(f.model_id))} · ${esc(SUMMARY.refused(code))}</p>`;
  }
  const mode = f.mode_l === 0
    ? SUMMARY.modeNone(pct0(f.p_mode))
    : f.mode_break_day !== null
      ? SUMMARY.modeDay(f.mode_break_day, f.mode_l ?? 0, pct0(f.p_mode))
      : SUMMARY.modeCensored(pct0(f.p_mode));
  return `<p class="summary-headline"><span class="big" title="${esc(CEILING.expectedLTip)}">${esc(SUMMARY.expected(fixed1(f.expected_l)))}</span> · ` +
    `<span class="big" title="${esc(CEILING.medianLTip)}">${esc(SUMMARY.medianDays(String(f.median_l ?? DASH)))}</span></p>` +
    `<p class="summary-probs"><span title="${esc(pyRepr(f.p_ge3))}">${esc(SUMMARY.pGe(3, pct0(f.p_ge3)))}</span> · ` +
    `<span title="${esc(pyRepr(f.p_ge5))}">${esc(SUMMARY.pGe(5, pct0(f.p_ge5)))}</span> · ` +
    `<span title="${esc(pyRepr(f.p_10))}">${esc(SUMMARY.p10(pct0(f.p_10)))}</span></p>` +
    `<p class="summary-mode" data-mode-l="${f.mode_l ?? ""}">${esc(SUMMARY.modeLabel)}: ${esc(mode)}</p>`;
}

/** j > 0'da koşullu satır; beyan resmi verinin önündeyse yalnız "resmi kapanış bekleniyor" (U52). */
function condLine(s: CeilingSummary, f: SummaryRow | undefined, pendingOfficial: boolean): string {
  if (s.j === 0 || !f) return "";
  if (pendingOfficial) return `<p class="warn-box official-pending summary-cond">${esc(COND.officialPending)}</p>`;
  const c = f.cond;
  if (!c) return `<p class="summary-cond muted" data-j="${s.j}">${esc(SUMMARY.condUndefined(s.j))}</p>`;
  const src = s.j_source === "OFFICIAL" ? SUMMARY.jObserved : SUMMARY.jHypothetical;
  return `<p class="summary-cond" data-j="${s.j}" data-j-source="${esc(s.j_source)}">` +
    `${esc(SUMMARY.condLine(s.j, src, pct0(c.p_break_next), fixed1(c.expected_remaining), pct0(c.s_cond_5), pct0(c.s_cond_10)))}</p>`;
}

function footer(s: CeilingSummary): string {
  const ne = s.rows.map((r) => r.near_era).find((n) => n !== null && n.supported) ?? null;
  const scales = `<p class="small muted scales-line">${esc(SUMMARY.scalesLine)}` +
    (ne ? ` · ${esc(SUMMARY.nearEraFoot(String(ne.n ?? DASH), String(ne.n_blocks ?? DASH)))}` : "") + `</p>`;
  const sc = s.scores ? SUMMARY.scoresSource(s.scores.source, s.scores.sha12) : SUMMARY.noScores;
  const oot = s.oot
    ? SUMMARY.ootSource(s.oot.source, s.oot.sha12 ?? DASH, s.oot.rows_present ? "" : SUMMARY.ootRowsNotEmbedded)
    : SUMMARY.vaultUnavailable;
  const checks = s.featured.candidates
    .map((c) => SUMMARY.candidateCheck(c.model_id, c.k1 ? TR.yes : TR.no, c.k2 ? TR.yes : TR.no, c.k3 ? TR.yes : TR.no))
    .join("\n");
  return scales + renderTufeInfo(s.tufe) +
    `<p class="small muted summary-sources" title="${esc(checks)}">${esc(SUMMARY.sources(sc, oot))}</p>` +
    `<p class="detail-link"><button class="link" data-action="open-group-b">▾ ${esc(SUMMARY.detailGroupB)}</button></p>`;
}

export function renderCeilingSummary(vm: SummaryVM): string {
  const s = vm.summary;
  if (!s) return "";
  const why = SUMMARY.featuredWhy[s.featured.reason] ?? s.featured.reason;
  const badge = s.official
    ? `<span class="mode-badge official">${esc(TR.modeOfficial)}</span> <span class="small muted">${esc(SUMMARY.officialSource(s.record_file ?? DASH, sha8(s.featured_params_sha256)))}</span>`
    : `<span class="mode-badge scenario">${esc(TR.modeScenario)}</span>`;
  const head = `<div class="summary-head"><h3>${esc(SUMMARY.ceilingTitle)}</h3> ${badge} ` +
    `<span class="featured-line" title="${esc(SUMMARY.featuredTip)}">${esc(SUMMARY.featured(s.featured.model_id, why))}</span></div>`;
  const open = `<section class="summary summary-ceiling" data-featured="${esc(s.featured.model_id)}" data-reason="${esc(s.featured.reason)}" data-j="${s.j}">`;
  if (s.integrity) {
    const src = s.oot?.integrity ? "scores_oot.json" : "scores.json";
    return `${open}${head}<p class="band-error summary-integrity" data-rule="${esc(s.integrity.rule)}">` +
      `${esc(SUMMARY.integrity(src, s.integrity.rule, s.integrity.detail))}</p></section>`;
  }
  const featured = s.rows.find((r) => r.role === "FEATURED");
  const main = s.rows.filter((r) => r.role !== "PB");
  const pb = s.rows.filter((r) => r.role === "PB");
  const table = (rows: SummaryRow[], cls: string) =>
    `<div class="scroll"><table class="grid compact ${cls}"><thead>${tableHead(s.j)}</thead><tbody>${rows.map((r) => tableRow(r, s.j)).join("")}</tbody></table></div>`;
  // PB aynası: f3 boşken listede açık, f3 doluyken katlanır
  const pbBlock = pb.length
    ? `<details class="pb-mirror"${s.f3_missing ? " open" : ""}><summary>${esc(SUMMARY.pbMirror)}: ${esc(pb.map((r) => r.model_id).join(", "))}</summary>${table(pb, "summary-table pb-table")}</details>`
    : "";
  return `${open}${head}${headline(featured)}${condLine(s, featured, pendingOfficial(vm))}` +
    table(main, "summary-table") + pbBlock + footer(s) + `</section>` + renderFallSummary(s.fall);
}

// ---------------------------------------------------------------- "Düşüş (D10)" kartı (EK 3 §8.4; K-P4-1, K-P4-2)

function fallLabel(r: FallRow): string {
  if (r.role === "FEATURED") return `${SUMMARY.featuredMark} ${r.model_id}`;
  if (r.role === "RULE") return `${SUMMARY.fallRule} · ${r.model_id}`;
  return r.model_id;
}

function fallNumCells(r: FallRow): string {
  if (!r.in_record) return `<td class="not-in-record muted" colspan="2">${esc(SUMMARY.recordWithoutModel)}</td>`;
  if (r.refused || r.d10.pct_fall === null) {
    const code = r.refused?.code ?? DASH;
    const why = SUMMARY.fallRefused[code] ?? "";
    return `<td class="refused-cell" colspan="2" data-code="${esc(code)}" title="${esc(why)}">${esc(SUMMARY.refused(code))}` +
      (why ? ` <span class="small muted">${esc(why)}</span>` : "") + `</td>`;
  }
  return [r.d10, r.d5]
    .map((c, i) => `<td class="num p-fall p-fall-${i === 0 ? "d10" : "d5"}" title="${esc(SUMMARY.fallRawTip(pyRepr(c.p_up), pyRepr(c.p_fall)))}">${esc(pctInt(c.pct_fall))}</td>`)
    .join("");
}

/** Yakın dönem: dosyadaki etiket + karşılaştırıcısı (dört (C) modelinde de; K-P4-2). Karşılaştırıcı satırlarında "—". */
function fallNearEraCell(r: FallRow): string {
  if (r.role === "COMPARATOR") return `<td class="scale-backtest near-era" title="${esc(SUMMARY.fallComparatorTip)}">${DASH}</td>`;
  const n = r.near_era;
  if (!n) return `<td class="scale-backtest near-era" title="${esc(SUMMARY.nearEraMissing)}">${DASH}</td>`;
  if (!n.supported) return `<td class="scale-backtest near-era unsupported">${esc(SUMMARY.nearEraUnsupported(n.schema_version ?? DASH))}</td>`;
  const ci = (n.ci95 ?? []).map((x) => metric4(x)).join(", ");
  const tip = SUMMARY.nearEraTip(n.comparator ?? DASH, metric4(n.diff), ci, String(n.n ?? DASH), String(n.n_blocks ?? DASH));
  return `<td class="scale-backtest near-era" data-label="${esc(n.label ?? "")}" data-comparator="${esc(n.comparator ?? "")}" title="${esc(tip)}">` +
    `${esc(n.label ?? DASH)} <span class="comparator small">· ${esc(SUMMARY.comparator(n.comparator ?? DASH))}</span></td>`;
}

/** Zaman-dışı: kasa birincil hücresinin verdict'i + terazi eki ve karşılaştırıcısı (K-P4-2); renk yalnız geçiyor/geçemiyor. */
function fallVaultCell(r: FallRow): string {
  if (r.role === "COMPARATOR") return `<td class="scale-oot vault" data-status="NONE" title="${esc(SUMMARY.fallComparatorTip)}">${DASH}</td>`;
  const v = r.vault;
  if (v.status === "CLOSED") return `<td class="scale-oot vault" data-status="CLOSED">${esc(SUMMARY.vaultClosed)}</td>`;
  if (v.status === "UNAVAILABLE") return `<td class="scale-oot vault" data-status="UNAVAILABLE" title="${esc(SUMMARY.vaultUnavailable)}">${DASH}</td>`;
  if (v.status !== "OPEN" || v.verdict === null) return `<td class="scale-oot vault" data-status="${esc(v.status)}">${DASH}</td>`;
  const suffixed = v.verdict === VERDICT.pass || v.verdict === VERDICT.fail || v.verdict === VERDICT.undecided;
  const cls = v.verdict === VERDICT.pass ? " win" : v.verdict === VERDICT.fail ? " lose" : "";
  const ci = (v.ci95 ?? []).map((x) => metric4(x)).join(", ");
  const tip = `${v.rule_id ?? ""} · ${metric4(v.diff)} [${ci}] · n = ${v.n ?? DASH}`;
  const cmp = v.rule_id ? ` <span class="comparator small">· ${esc(SUMMARY.comparator(v.rule_id))}</span>` : "";
  return `<td class="scale-oot vault${cls}" data-status="OPEN" data-verdict="${esc(v.verdict)}" title="${esc(tip)}">` +
    `${esc(suffixed ? `${v.verdict}${SUMMARY.vaultSuffix}` : v.verdict)}${cmp}</td>`;
}

function fallLiveCell(r: FallRow): string {
  const n = r.live.n_scored;
  if (r.role === "COMPARATOR" || n === null) return `<td class="scale-live live">${DASH}</td>`;
  const text = n < MIN_N_METRIC ? SUMMARY.liveNoVerdict(String(n)) : r.live.verdict ?? DASH;
  return `<td class="scale-live live" data-n="${n}">${esc(text)}</td>`;
}

/** §5.5 sütunu: adayda sağlanmayan ilk koşulun düz metni (K-P4-1); öne çıkan "uygun"; kural ve karşılaştırıcıda "—". */
function fallRuleCell(r: FallRow): string {
  if (r.role === "FEATURED") return `<td class="rule-5-5 eligible">${esc(SUMMARY.fallEligible)}</td>`;
  if (r.role !== "CANDIDATE" || !r.first_failed) return `<td class="rule-5-5">${DASH}</td>`;
  return `<td class="rule-5-5" data-failed="${esc(r.first_failed)}">${esc(SUMMARY.fallWhy[r.first_failed] ?? r.first_failed)}</td>`;
}

function fallRow(r: FallRow): string {
  const cls = ["summary-row", `role-${r.role.toLowerCase()}`, r.role === "COMPARATOR" ? "muted" : ""].filter(Boolean).join(" ");
  const badge = r.role === "COMPARATOR" ? ` <span class="badge comparator-badge">${esc(SUMMARY.comparatorBadge)}</span>` : "";
  return `<tr class="${cls}" data-model="${esc(r.model_id)}" data-role="${esc(r.role)}"><th class="mono">${esc(fallLabel(r))}${badge}</th>` +
    fallNumCells(r) + fallNearEraCell(r) + fallVaultCell(r) + fallLiveCell(r) + fallRuleCell(r) + `</tr>`;
}

/** Öne çıkan (varsa) için büyük satır: P(D10 ≤ arz) = %k, altında P(kapanış > arz) = %(100 − k); D5 ikincil. */
function fallHeadline(f: FallRow | undefined): string {
  if (!f) return `<p class="summary-headline muted fall-v15-note">${esc(SUMMARY.fallV15Note)}</p>`;
  if (f.refused || f.d10.pct_fall === null || !f.in_record) {
    const code = f.refused?.code ?? DASH;
    return `<p class="summary-headline refused" data-code="${esc(code)}">${esc(SUMMARY.headRefused(f.model_id))} · ${esc(SUMMARY.refused(code))}</p>`;
  }
  return `<p class="summary-headline fall-headline"><span class="big" title="${esc(SUMMARY.fallRawTip(pyRepr(f.d10.p_up), pyRepr(f.d10.p_fall)))}">` +
    `${esc(SUMMARY.pFall("D10", pctInt(f.d10.pct_fall)))}</span></p>` +
    `<p class="summary-probs">${esc(SUMMARY.pUpLine(pctInt(f.d10.pct_up)))}</p>` +
    `<p class="summary-probs small fall-d5">${esc(SUMMARY.pFall("D5", pctInt(f.d5.pct_fall)))} · ${esc(SUMMARY.pUpLine(pctInt(f.d5.pct_up)))}</p>`;
}

function fallCards(rows: FallRow[]): string {
  const items = rows
    .filter((r) => r.card)
    .map((r) => {
      const c = r.card!;
      const prim = c.primary_cell ? SUMMARY.fallPrimary : DASH;
      return `<li class="fall-card mono small" data-model="${esc(r.model_id)}">${esc(SUMMARY.fallCardLine(
        r.model_id, c.description ?? SUMMARY.fallWhat, String(c.training_n ?? DASH), String(c.training_cutoff ?? DASH),
        c.params_sha256_8 ?? DASH, String(c.n_variants_same_data ?? DASH), prim))}</li>`;
    })
    .join("");
  return items ? `<details class="fall-cards"><summary>${esc(SUMMARY.fallCardsTitle)}</summary><ul>${items}</ul></details>` : "";
}

/** "Düşüş (D10)" kartı (EK 3 §8.4): bütün sayılar ve öne çıkarma Rust `FallSummary`'den; burada yalnız biçimlendirme. */
export function renderFallSummary(f: FallSummary | null): string {
  if (!f) return "";
  const featuredId = f.featured.model_id;
  const line = f.featured.reason === "RULE_5_5" && featuredId
    ? SUMMARY.fallFeatured(featuredId)
    : f.featured.reason === "VAULT_CLOSED" ? SUMMARY.fallVaultClosed : SUMMARY.fallNone;
  const badge = f.official
    ? `<span class="mode-badge official">${esc(TR.modeOfficial)}</span> <span class="small muted">${esc(featuredId
      ? SUMMARY.officialSource(f.record_file ?? DASH, f.rows.find((r) => r.role === "FEATURED")?.card?.params_sha256_8 ?? DASH)
      : SUMMARY.fallOfficialSource(f.record_file ?? DASH))}</span>`
    : `<span class="mode-badge scenario">${esc(TR.modeScenario)}</span>`;
  const head = `<div class="summary-head"><h3>${esc(SUMMARY.fallTitle)}</h3> ${badge} ` +
    `<span class="featured-line" title="${esc(SUMMARY.fallFeaturedTip)}">${esc(line)}</span></div>`;
  const open = `<section class="summary summary-fall" data-featured="${esc(featuredId ?? "")}" data-reason="${esc(f.featured.reason)}">`;
  if (f.integrity) {
    return `${open}${head}<p class="band-error summary-integrity" data-rule="${esc(f.integrity.rule)}">` +
      `${esc(SUMMARY.integrity("scores.json", f.integrity.rule, f.integrity.detail))}</p></section>`;
  }
  const cols = [SUMMARY.colModel, SUMMARY.colFallD10, SUMMARY.colFallD5];
  const thead = `<tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}<th class="scale-backtest">${esc(SUMMARY.colNearEra)}</th>` +
    `<th class="scale-oot">${esc(SUMMARY.colVault)}</th><th class="scale-live">${esc(SUMMARY.colLive)}</th><th>${esc(SUMMARY.colRule55)}</th></tr>`;
  const table = `<div class="scroll"><table class="grid compact summary-table fall-table"><thead>${thead}</thead>` +
    `<tbody>${f.rows.map(fallRow).join("")}</tbody></table></div>`;
  const sc = f.scores ? SUMMARY.scoresSource(f.scores.source, f.scores.sha12) : SUMMARY.noScores;
  const oot = f.oot ? SUMMARY.ootSource(f.oot.source, f.oot.sha12 ?? DASH, f.oot.rows_present ? "" : SUMMARY.ootRowsNotEmbedded) : SUMMARY.vaultUnavailable;
  const foot = `<p class="small muted scales-line">${esc(SUMMARY.scalesLine)} · ${esc(SUMMARY.fallV15Note)}</p>` + renderTufeInfo(f.tufe) +
    `<p class="small muted summary-sources">${esc(SUMMARY.sources(sc, oot))}</p>`;
  return `${open}${head}${fallHeadline(f.rows.find((r) => r.role === "FEATURED"))}${table}${fallCards(f.rows)}${foot}</section>`;
}
