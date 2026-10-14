// "Zaman-dışı test (eski kohort)" paneli (SPEC_APP EK 3 §7.2; K-P3-1, K-P3-2, K-P3-3) saf render. Bütün değerler Rust
// `scores_oot_view` / `scores_oot_model` çıktısından gelir (dosyadaki hücreler, kırılımlar ve sayaçlar aynen); burada yalnız
// biçimlendirme ve yerleşim vardır. Üçüncü terazi kendi rengiyle ayrı bölümdür (`.panel-oot`): geçmiş veri testi ve canlı
// sicil bloklarıyla hiçbir yerde birleşmez. Satır tablosu YALNIZ açık küme bloğunda (Rust yalnız `open == true` satırları
// verir); kasa, toplam ve D1 sonrası bloklarında yalnız hücreler, kırılımlar ve sayaçlar vardır.
import { ACCURACY, CARD, KIND_TEXT, VERDICT, VERDICT_OOT_SUFFIX } from "../i18n/tr";
import type { ModelInfo, OotBlockView, OotBreakdown, OotModelDetail, OotModelSummary, OotPanelView, OotRowView, ScoreCell } from "../types";
import { esc } from "../dom";
import { MIN_N_METRIC, renderModelCard, type CardVM } from "./card";
import { cellTip, ciText, value, wlt } from "./accuracy";
import { DASH, pct0, pctSigned1 } from "./format";

export interface OotPanelVM {
  view: OotPanelView | null;
  /** Blok başına seçili model (`block` → `model_id`). */
  selected: Record<string, string>;
  /** Blok başına seçili modelin ayrıntısı (`scores_oot_model`). */
  details: Record<string, OotModelDetail | null>;
  /** Gömülü INDEX künyesi (kartın "ne yapar", eğitim n / kesim, gömülü sha). */
  models?: ModelInfo[];
}

const T = ACCURACY.oot;
const SCALE = "oot";
const OPEN_BLOCK = "oot_pre_h99";
const SEALED_BLOCKS = ["oot_pre_h99_sealed", "oot_pre_h99_all"];
const POST_D1_BLOCKS = ["post_d1", "post_d1_sealed", "post_d1_all"];

/** Dosyadaki hüküm aynen; geçiyor / geçemiyor / ayırt edilemiyor'a terazi eki ("yetersiz örnek" ve null eksiz). */
export function ootVerdictText(v: string | null): string {
  if (v === null) return DASH;
  const suffixed = v === VERDICT.pass || v === VERDICT.fail || v === VERDICT.undecided;
  return suffixed ? `${v}${VERDICT_OOT_SUFFIX}` : v;
}

function verdictCell(v: string | null): string {
  const cls = v === VERDICT.pass ? " win" : v === VERDICT.fail ? " lose" : "";
  return `<td class="verdict${cls}" data-verdict="${esc(v ?? "")}">${esc(ootVerdictText(v))}</td>`;
}

function cellHead(): string {
  const h = [ACCURACY.colOutput, ACCURACY.colHorizon, ACCURACY.colMetric, ACCURACY.colModel, ACCURACY.colRule, ACCURACY.colDiff,
    ACCURACY.colCi, ACCURACY.colN, ACCURACY.colWlt, ACCURACY.colVerdict];
  return `<tr>${h.map((x) => `<th>${esc(x)}</th>`).join("")}</tr>`;
}

function nText(c: { n: number; n_blocks?: number | null }): string {
  return c.n_blocks === undefined || c.n_blocks === null ? String(c.n) : `${c.n} (${c.n_blocks})`;
}

function cellRow(c: ScoreCell, primary: boolean): string {
  const badge = primary ? ACCURACY.primaryBadge : c.label ?? ACCURACY.exploratoryBadge;
  return `<tr class="cell-row${primary ? " primary" : ""}" data-output="${esc(c.output)}" data-h="${esc(String(c.horizon_or_k))}" ` +
    `data-metric="${esc(c.metric)}" data-rule="${esc(c.rule_id)}" data-scale="${SCALE}">` +
    `<td>${esc(c.output)} <span class="tag label-tag">${esc(badge)}</span></td>` +
    `<td>${esc(c.horizon_or_k === null ? DASH : String(c.horizon_or_k))}</td><td>${esc(c.metric)}</td>` +
    `<td class="metric" title="${esc(cellTip(c))}">${esc(value(c, c.model_value))}</td>` +
    `<td class="metric"><span class="mono">${esc(c.rule_id)}</span> ${esc(value(c, c.rule_value))}</td>` +
    `<td class="metric diff">${esc(value(c, c.diff))}</td><td class="metric ci">${esc(ciText(c))}</td>` +
    `<td class="metric n">${esc(nText(c))}</td><td class="metric wlt">${esc(wlt(c))}</td>${verdictCell(c.verdict)}</tr>`;
}

/** Birincil hücre dosyadaki etiketle (`label == "birincil"`; EK 3 §7.2-3); öteki hücreler kendi etiketiyle. */
function cellTable(cells: ScoreCell[]): string {
  if (cells.length === 0) return `<p class="small muted rows-only">${esc(ACCURACY.rowsOnly)}</p>`;
  return `<div class="scroll"><table class="grid compact cells oot-cells"><thead>${cellHead()}</thead><tbody>` +
    cells.map((c) => cellRow(c, c.label === "birincil")).join("") + `</tbody></table></div>`;
}

/** Kırılım: n < 10 → "metrik yok (n < 10)" (dosyadaki null'lar); 10 ≤ n < 30 dosyadaki "yetersiz örnek"; renk yok. */
function breakdownTable(rows: OotBreakdown[], title: string, cls: string, metricName: string): string {
  if (rows.length === 0) return "";
  const head = [T.colSubset, ACCURACY.colN, ACCURACY.colModel, ACCURACY.colRule, ACCURACY.colDiff, ACCURACY.colCi, ACCURACY.colVerdict];
  const metric = { metric: metricName };
  const body = rows.map((r) => {
    if (r.n < MIN_N_METRIC) {
      return `<tr class="breakdown-row no-metric" data-subset="${esc(r.subset)}" data-n="${r.n}"><td>${esc(r.subset)}</td>` +
        `<td class="metric n">${esc(nText(r))}</td><td colspan="5" class="muted">${esc(T.noMetric)}</td></tr>`;
    }
    return `<tr class="breakdown-row" data-subset="${esc(r.subset)}" data-n="${r.n}"><td>${esc(r.subset)}</td>` +
      `<td class="metric n">${esc(nText(r))}</td><td class="metric">${esc(value(metric, r.model_value))}</td>` +
      `<td class="metric"><span class="mono">${esc(r.rule_id ?? "")}</span> ${esc(value(metric, r.rule_value))}</td>` +
      `<td class="metric diff">${esc(value(metric, r.diff))}</td><td class="metric ci">${esc(ciText({ metric: metricName, ci95: r.ci95 }))}</td>` +
      `<td class="verdict" data-verdict="${esc(r.verdict ?? "")}">${esc(ootVerdictText(r.verdict))}</td></tr>`;
  });
  return `<details class="${esc(cls)}"><summary>${esc(title)}</summary><div class="scroll"><table class="grid compact breakdown">` +
    `<thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body.join("")}</tbody></table></div></details>`;
}

function predText(r: OotRowView): string {
  if (r.pred_kind === "REFUSED") return ACCURACY.refusedPrediction(r.refused_code ?? "?");
  if (r.pred_kind === "S" && r.pred_s) return T.predS(pct0(r.pred_s[0]), pct0(r.pred_s[1]), pct0(r.pred_s[2]));
  if (r.pred_kind === "RETURN") return T.predReturn(r.pred_d5_return === null ? DASH : pctSigned1(r.pred_d5_return), pct0(r.pred_d5_p_up));
  return DASH;
}

function realizedText(r: OotRowView): string {
  return T.realized(r.realized_l === null ? DASH : String(r.realized_l), r.realized_d5_r === null ? DASH : pctSigned1(r.realized_d5_r));
}

/** Açık küme satır tablosu (EK 3 §7.2-3): arz · D1 · yıl · rejim · sınıf · durum · tahmin · gerçekleşen · kayıt. */
function rowTable(rows: OotRowView[]): string {
  const head = [ACCURACY.colTicker, ACCURACY.colD1, T.colYear, T.colRegime, ACCURACY.colClass, ACCURACY.colStatus,
    ACCURACY.colPrediction, ACCURACY.colRealized, ACCURACY.colRecord];
  const body = rows.map((r) =>
    `<tr data-ticker="${esc(r.ticker)}" data-class="${esc(r.class ?? "")}" data-status="${esc(r.status ?? "")}">` +
    `<td class="mono">${esc(r.ticker)}</td><td>${esc(r.d1 ?? DASH)}</td><td>${esc(r.year === null ? DASH : String(r.year))}</td>` +
    `<td class="small">${esc(r.alloc_regime ?? DASH)}</td>` +
    `<td title="${esc(JSON.stringify(r.class_evidence ?? {}))}">${esc(r.class ?? DASH)}</td><td>${esc(r.status ?? DASH)}</td>` +
    `<td class="pred">${esc(predText(r))}</td><td class="realized">${esc(realizedText(r))}</td>` +
    `<td class="mono small">${esc(r.record_id ?? DASH)}</td></tr>`);
  return `<div class="scroll"><table class="grid compact rows oot-rows"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${body.join("")}</tbody></table></div>`;
}

function n(c: Record<string, number>, k: string): string {
  const x = c[k];
  return x === undefined || x === null ? DASH : String(x);
}

/** Birincil hücreler tablosu (SCORES_OOT.md §2 / §8.1 / §9.1 kalıbı): yalnız birincil hücresi olan modeller. */
function primaryTable(b: OotBlockView): string {
  const withP = b.models.filter((m) => m.primary !== null);
  const without = b.models.filter((m) => m.primary === null).map((m) => m.model_id);
  const head = [ACCURACY.colModel, ACCURACY.colOutput, ACCURACY.colHorizon, ACCURACY.colMetric, ACCURACY.colRule, ACCURACY.colN,
    ACCURACY.colModel, ACCURACY.colRule, ACCURACY.colDiff, ACCURACY.colCi, ACCURACY.colWlt, ACCURACY.colVerdict];
  const rows = withP.map((m) => {
    const c = m.primary as ScoreCell;
    return `<tr class="primary-row" data-model="${esc(m.model_id)}" data-scale="${SCALE}"><th class="mono">${esc(m.model_id)}</th>` +
      `<td>${esc(c.output)}</td><td>${esc(c.horizon_or_k === null ? DASH : String(c.horizon_or_k))}</td><td>${esc(c.metric)}</td>` +
      `<td class="mono">${esc(c.rule_id)}</td><td class="metric n">${esc(nText(c))}</td>` +
      `<td class="metric model-value" title="${esc(cellTip(c))}">${esc(value(c, c.model_value))}</td>` +
      `<td class="metric rule-value">${esc(value(c, c.rule_value))}</td><td class="metric diff">${esc(value(c, c.diff))}</td>` +
      `<td class="metric ci">${esc(ciText(c))}</td><td class="metric wlt">${esc(wlt(c))}</td>${verdictCell(c.verdict)}</tr>`;
  });
  const table = withP.length
    ? `<h5>${esc(T.primaryTitle)}</h5><div class="scroll"><table class="grid compact oot-primary"><thead><tr>` +
      head.map((h) => `<th>${esc(h)}</th>`).join("") + `</tr></thead><tbody>${rows.join("")}</tbody></table></div>`
    : `<p class="muted no-models">${esc(T.noModels)}</p>`;
  const none = without.length ? `<p class="small muted no-primary" data-n="${without.length}">${esc(T.noPrimary(without.join(", ")))}</p>` : "";
  return table + none;
}

function modelCounters(m: OotModelSummary, post: boolean): string {
  const c = m.counters;
  const text = post
    ? T.postD1Counters(n(c, "n_rows"), n(c, "n_scored"), n(c, "n_refused"), n(c, "n_not_applicable"), n(c, "n_d1_label_na"), n(c, "n_no_record"), n(c, "n_oot_retro"))
    : T.modelCounters(n(c, "n_scored"), n(c, "n_refused"), n(c, "n_not_applicable_regime"), n(c, "n_target_unavailable"), n(c, "n_pending"), n(c, "n_skipped"), n(c, "n_oot_retro"));
  return `<p class="small model-counters" data-n="${esc(n(c, "n_scored"))}">${esc(text)}</p>`;
}

/** Model kartı (EK 3 §7.2-3; `CardVM` aynı): sha gömülü modelin sha'sı, karşılaştırma yok (dosya sha taşımaz); canlı alanlar —. */
function ootCardVM(m: OotModelSummary, info: ModelInfo | undefined): CardVM {
  const p = m.primary_cell;
  return {
    modelId: m.model_id,
    description: info?.description ?? null,
    kind: m.kind ? KIND_TEXT[m.kind] ?? m.kind : null,
    survival: null,
    trainingN: info?.training_n === undefined || info?.training_n === null ? null : String(info.training_n),
    trainingCutoff: info?.training_cutoff_date ?? null,
    sha: info?.params_sha256 ?? null,
    shaCompare: null,
    variants: null,
    primary: p ? `${p.output} · ${p.horizon_or_k ?? DASH} · ${p.metric} · ${(p.rule_ids ?? []).join(", ")}` : null,
    liveN: null,
    liveVerdict: null,
  };
}

/** Seçili modelin bloğu: kart, sayaçlar, hücreler (birincil işaretli), kırılımlar ve yalnız açık kümede satırlar. */
function modelDetail(b: OotBlockView, m: OotModelSummary | undefined, d: OotModelDetail | null, rowsAllowed: boolean, models: ModelInfo[]): string {
  if (!m) return "";
  const post = POST_D1_BLOCKS.includes(b.key);
  const badge = m.exposure_class ? ` <span class="tag exposure">${esc(T.exposure(m.exposure_class))}</span>` : "";
  let body = renderModelCard(ootCardVM(m, models.find((x) => x.model_id === m.model_id)), CARD.caption) + modelCounters(m, post);
  if (d) {
    const metric = d.primary_cell?.metric ?? "";
    body += cellTable(d.cells) + breakdownTable(d.by_year, T.byYear, "by-year", metric) + breakdownTable(d.by_regime, T.byRegime, "by-regime", metric);
    if (rowsAllowed && d.rows_block) {
      body += d.rows_available
        ? `<details class="oot-rows-block" data-n="${d.rows.length}"><summary>${esc(T.rowsTitle)} · ${d.rows.length}</summary>${rowTable(d.rows)}</details>`
        : `<p class="small muted rows-repo-only">${esc(T.rowsRepoOnly)}</p>`;
    }
  }
  return `<details class="model-block-oot" data-block="${esc(b.key)}" data-model="${esc(m.model_id)}" open>` +
    `<summary><span class="mono">${esc(m.model_id)}</span>${badge} <span class="small muted">${esc(T.noShaNote)}</span></summary>${body}</details>`;
}

function selector(b: OotBlockView, selected: string | undefined): string {
  if (b.models.length < 2) return "";
  const opts = b.models
    .map((m) => `<option value="${esc(m.model_id)}"${m.model_id === selected ? " selected" : ""}>${esc(m.model_id)}</option>`)
    .join("");
  return `<label class="oot-selector small">${esc(T.modelSelector)} <select data-action="oot-model" data-block="${esc(b.key)}">${opts}</select></label>`;
}

/** `heading` null: başlık dosyadaki `title`'dır (D1 sonrası alt bölümleri); değilse başlık + dosyadaki `title` satırı. */
function blockSection(b: OotBlockView, vm: OotPanelVM, heading: string | null): string {
  const sel = vm.selected[b.key] ?? b.models[0]?.model_id;
  const m = b.models.find((x) => x.model_id === sel) ?? b.models[0];
  const det = vm.details[b.key] ?? null;
  const c = b.counters;
  const counts = c.n_member !== undefined
    ? `<p class="small muted block-counters">${esc(T.counters(n(c, "n_member"), n(c, "n_open"), n(c, "n_sealed"), n(c, "n_out_of_scope"), n(c, "n_exposed_archive"), n(c, "n_exposed_codex"), n(c, "n_in_table")))}</p>`
    : "";
  const excluded = b.excluded_models.length
    ? `<details class="excluded-models"><summary>${esc(T.excluded)} · ${b.excluded_models.length}</summary><ul class="small">` +
      b.excluded_models.map((e) => `<li data-model="${esc(e.model_id)}">${esc(T.excludedLine(e.model_id, e.reason))}</li>`).join("") + `</ul></details>`
    : "";
  const post = POST_D1_BLOCKS.includes(b.key);
  const note = post ? `<p class="small muted post-d1-oot-note">${esc(T.postD1Note)} · ${esc(b.scale ?? "")}</p>` : "";
  const head = heading === null
    ? `<h4>${esc(b.title ?? b.key)}</h4>`
    : `<h4>${esc(heading)}</h4><p class="oot-block-title">${esc(b.title ?? "")}</p>`;
  return `<section class="oot-block" data-block="${esc(b.key)}" data-subset="${esc(b.subset ?? b.key)}">${head}` +
    `<p class="small muted subset-label">${esc(T.subsetLabel(b.subset ?? b.key))}</p>` +
    counts + note + excluded + primaryTable(b) + selector(b, m?.model_id) + modelDetail(b, m, det, b.key === OPEN_BLOCK, vm.models ?? []) + `</section>`;
}

function retroSection(v: OotPanelView): string {
  if (!v.rows_present) return `<details class="oot-retro"><summary>${esc(T.retroTitle)}</summary><p class="small muted">${esc(T.retroRepoOnly)}</p></details>`;
  const r = v.retro;
  const lines = r.groups.map((g) => `<li data-model="${esc(g.model_id)}" data-n="${g.n}">${esc(T.retroLine(g.model_id, g.n, g.tickers.join(", ")))}</li>`).join("");
  const hidden = r.n_not_drawn > 0 ? `<p class="small muted retro-not-drawn" data-n="${r.n_not_drawn}">${esc(T.retroNotDrawn(r.n_not_drawn))}</p>` : "";
  return `<details class="oot-retro" data-n="${r.n}"><summary>${esc(T.retroTitle)} · ${r.n}</summary><ul class="small">${lines}</ul>${hidden}</details>`;
}

function header(v: OotPanelView): string {
  const src = ACCURACY.oot.sourceText[v.source ?? ""] ?? v.source ?? DASH;
  return `<p class="small muted oot-source">${esc(T.source(src, v.generated_at_utc ?? DASH, v.git_head12 ?? DASH, v.cohort_sha12 ?? DASH, v.sha12 ?? DASH))}</p>`;
}

/** Üçüncü bölüm: kendi başlığı, kaynak satırı, kasa satırı, açık küme, kasa alt bölümleri, D1 sonrası ve RETRO. */
export function renderOotPanel(vm: OotPanelVM): string {
  const v = vm.view;
  const open = (body: string) => `<section class="panel-oot" data-scale="${SCALE}"><h3>${esc(T.sectionTitle)}</h3>${body}</section>`;
  if (!v || v.status === "NO_FILE") return open(`<p class="closed-state oot-no-file">${esc(T.noFile)}</p>`);
  if (v.status === "REPO_ONLY") return open(`<p class="closed-state oot-repo-only">${esc(T.repoOnly)}</p>`);
  if (v.status === "UNSUPPORTED") return open(`<div class="error-box oot-version">${esc(T.unsupported(v.unsupported_version ?? DASH))}</div>`);
  if (v.status === "INTEGRITY" && v.integrity) {
    const rule = T.integrityRule[v.integrity.rule] ?? v.integrity.rule;
    return open(header(v) + `<div class="error-box oot-integrity" data-rule="${esc(v.integrity.rule)}"><strong>${esc(T.integrityTitle(rule))}</strong>` +
      `<p class="mono small">${esc(v.integrity.detail)}</p><p class="small">${esc(ACCURACY.integrityNote)}</p></div>`);
  }
  const openBlock = v.blocks.find((b) => b.key === OPEN_BLOCK);
  const vault = v.vault_open
    ? `<p class="vault-line vault-open">${esc(T.vaultOpen(v.generated_at_utc ?? DASH))}</p>`
    : `<p class="vault-line vault-closed">${esc(T.vaultClosed)}</p>`;
  const classDef = v.class_definition
    ? `<details class="class-def"><summary>${esc(T.classDef)}</summary><p class="small">${esc(v.class_definition)}</p><p class="small muted">${esc(T.classNote)}</p></details>`
    : "";
  const sections: string[] = [];
  if (openBlock) sections.push(blockSection(openBlock, vm, T.openTitle));
  for (const key of SEALED_BLOCKS) {
    const b = v.blocks.find((x) => x.key === key);
    if (b) sections.push(blockSection(b, vm, key === "oot_pre_h99_sealed" ? T.sealedTitle : T.allTitle));
  }
  const post = POST_D1_BLOCKS.map((k) => v.blocks.find((x) => x.key === k)).filter((b): b is OotBlockView => b !== undefined);
  const postGroup = post.length
    ? `<section class="oot-post-d1"><h4>${esc(T.postD1Group)}</h4>${post.map((b) => blockSection(b, vm, null)).join("")}</section>`
    : "";
  if (v.blocks.length === 0) sections.push(`<p class="muted no-models">${esc(T.noModels)}</p>`);
  return open(`<p class="oot-title">${esc(openBlock?.title ?? "")}</p>` + header(v) + vault + classDef +
    `<p class="small muted scales-note">${esc(ACCURACY.scalesNote)}</p>` + sections.join("") + postGroup + retroSection(v));
}
