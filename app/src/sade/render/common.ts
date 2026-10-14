// Sade görünümün ortak saf render parçaları. Bütün metin tr.ts'ten; hüküm metni dosyadaki `verdict`'tir (U19), sade
// açıklama ona bağlı ayrı satırdır (K-UI-5). Hiçbir değer hesaplanmaz.
import { esc, renderError } from "../../dom";
import { DISCLAIMER, SADE, VERDICT, VERDICT_MARK, VERDICT_OOT_SUFFIX, VERDICT_PLAIN } from "../../i18n/tr";
import { dateTr } from "../../render/format";
import type { SnapshotInfo } from "../../types";
import type { DataSource } from "../state";
import type { ClassRow, GateEntry, HeadlineGate, RegimeInfo } from "../types";

/** Her sade ekranın altı: DISCLAIMER (değişmez) ve sürüm. */
export function renderFooter(version: string | null): string {
  return `<footer class="s-footer"><span class="s-disclaimer">${esc(DISCLAIMER)}</span>` +
    `<span class="s-footer-right"><span>${esc(SADE.version(version ?? SADE.dash))}</span>` +
    `<button class="s-link" data-go="ayarlar">${esc(SADE.about)}</button></span></footer>`;
}

/** Hüküm işareti sınıfı: yalnız dosyadaki verdict'e göre (renk tek başına bilgi taşımaz: yanında işaret ve metin). */
export function verdictClass(v: string | null | undefined): string {
  if (v === VERDICT.pass) return "mark-pass";
  if (v === VERDICT.fail) return "mark-fail";
  return "mark-undecided";
}

/** Hüküm hücresi: işaret + dosyadaki verdict metni aynen (`data-verdict`). */
export function verdictCell(v: string | null | undefined, suffix = ""): string {
  if (!v) return `<span class="muted">${esc(SADE.dash)}</span>`;
  const mark = VERDICT_MARK[v] ?? "";
  return `<span class="verdict ${verdictClass(v)}" data-verdict="${esc(v)}">${mark === "" ? "" : `${esc(mark)} `}${esc(v)}${esc(suffix)}</span>`;
}

/** Zaman-dışı hüküm: dosyadaki verdict + terazi eki (tr.ts'teki VERDICT_OOT_SUFFIX); dar panelde ek ipucundadır. */
export function ootVerdictCell(v: string | null | undefined, compact = false): string {
  if (!compact) return verdictCell(v, v ? VERDICT_OOT_SUFFIX : "");
  return `<span title="${esc(v ? `${v}${VERDICT_OOT_SUFFIX}` : "")}">${verdictCell(v)}</span>`;
}

/** Sade açıklama satırı (verdict'e bağlı ayrı dize; hüküm hücresinin yerine geçmez). */
export function verdictPlain(v: string | null | undefined): string {
  const t = v ? VERDICT_PLAIN[v] : undefined;
  return t ? `<div class="s-note verdict-plain">${esc(t)}</div>` : "";
}

export function gateOf(g: HeadlineGate | null, model: string, output: string, h: string | null): GateEntry | null {
  return g?.entries.find((e) => e.model_id === model && e.output === output && e.horizon_or_k === h) ?? null;
}

/**
 * Ana ekran kapısı (K-UI-4): öne çıkan çıktı altın; öne çıkmayan çıktı aynı değeri gri ve "≈" işaretiyle gösterir
 * (getiri tablosunda satırın "Geçmiş test" hücresi `notPrimaryLabel`). Karar yalnız `headline_gate`'ten.
 */
export function gated(e: GateEntry | null, valueHtml: string): string {
  if (e?.featured) return `<span class="gold" data-featured="1" title="${esc(SADE.featuredTip)}">${valueHtml}</span>`;
  return `<span class="mark-approx" data-featured="0" title="${esc(SADE.approxTip)}">${valueHtml} <span class="approx">${esc(SADE.approxMark)}</span></span>`;
}

/**
 * Öne çıkmayan çıktının "Geçmiş test" hücresi (FAZ9_WINDOWS K-TXT-1): "· birincil değil". Dosyadaki keşif hükmü burada
 * gösterilmez; hüküm sözcüğü yalnız birincil (öne çıkan) hücrededir.
 */
export function notPrimaryLabel(): string {
  return `<span class="muted not-primary">${esc(SADE.notPrimaryMark)} ${esc(SADE.notPrimaryText)}</span>`;
}

export function classText(c: string | null | undefined): string {
  if (!c) return SADE.classNone;
  return SADE.classText[c] ?? c;
}

/** Model başına sınıf satırı (scores.json canlı satırları ve aşama paydaları; burada hesaplanmaz). */
export function classLines(classes: ClassRow[], models: string[], short = false): string {
  return classes
    .filter((c) => models.includes(c.model_id))
    .map((c) => {
      const status = c.status === "REFUSED" ? SADE.classText.REFUSED : null;
      const text = status ?? classText(c.class);
      const cls = c.class === "LIVE" && c.status !== "REFUSED" ? "chip-live" : "";
      return `<div class="s-class-line" data-model="${esc(c.model_id)}" data-class="${esc(c.class ?? "")}">` +
        `${esc((short ? SADE.questionShort : SADE.question)[questionOf(c.model_id)] ?? c.model_id)}: <span class="${cls}">${esc(text)}</span></div>`;
    })
    .join("");
}

/** Model kimliği → soru anahtarı (üretimdeki dört model). */
export function questionOf(model: string): string {
  if (model === "ceiling_hazard_v0") return "CEILING_DAYS";
  if (model === "v1_5_h99") return "RETURN";
  if (model === "post_d1_hazard_v0") return "POST_D1_BREAK";
  if (model === "break_floor_v0") return "BREAK_FLOOR";
  return model;
}

/** Repo modu gerekli boş durumu (K-UI-13). */
export function renderRepoRequired(): string {
  return `<section class="s-panel s-empty repo-required"><h2>${esc(SADE.repoRequired)}</h2><p>${esc(SADE.repoRequiredNote)}</p>` +
    `<button class="primary" data-go="ayarlar">${esc(SADE.goSettings)}</button></section>`;
}

/**
 * Resmi veri kapısı (K-UI-13; FAZ9_SNAPSHOT K-SNAP-2): veri yoksa "repo modu gerekli"; gömülü anlık görüntü doğrulanamadıysa
 * bütünlük kutusu ve aynı boş durum (fail-closed, hiçbir sayı yok). Veri varsa `null`.
 */
export function closedScreen(src: DataSource, snap: SnapshotInfo | null | undefined): string | null {
  if (src === "NONE") return `<div class="s-main">${renderRepoRequired()}</div>`;
  if (src !== "FAILED") return null;
  const box = errorBox(renderError({ code: snap?.code ?? "SNAPSHOT_INTEGRITY_FAILED", message: snap?.detail ?? "" }));
  return `<div class="s-main snapshot-failed">${box}${renderRepoRequired()}</div>`;
}

/** Kişisel modda veri şeridi (K-SNAP-3): kaynak, derleme ve son sonuç tarihi Rust'tan (`snapshot`); repo modunda boş. */
export function renderSnapshotSource(s: SnapshotInfo | null | undefined): string {
  if (!s) return "";
  return `<p class="s-note snap-source" data-role="snapshot">${esc(SADE.snapshot.strip(s.build_sha7, dateTr(s.last_session), s.build_dirty))}</p>`;
}

/** Rejim şeridi (K-UI-12; C4): kural dosyadan (`start_d1`), metin tr.ts'ten. Etiketli arz yoksa boş. */
export function renderRegimeStripe(regime: RegimeInfo | null, anyTagged: boolean): string {
  if (!regime || !anyTagged) return "";
  return `<div class="s-stripe" data-regime="${esc(regime.tag)}"><span class="s-badge-regime">${esc(SADE.regimeBadge)}</span>` +
    `<span>${esc(SADE.regimeStripe(dateTr(regime.start_d1)))}</span></div>`;
}

/** Hata kutusu (dom.renderError ile aynı sınıflar; sade CSS'te koyu tema). */
export function errorBox(html: string): string {
  return `<div class="s-legacy">${html}</div>`;
}

/**
 * Kırılma modelinin geçmiş test hücresi (K-UI-4): dosyada hüküm alanı yok; `promotion` (kapı girdisi) ne diyorsa o —
 * işaret ve etiket `card.promotion.label` aynen ("ön eleme (…); canlı n = k").
 */
export function promotionCell(e: GateEntry | null): string {
  if (!e || e.status !== "OK") return `<span class="muted">${esc(SADE.dash)}</span>`;
  const mark = e.featured ? `<span class="mark-pass">✓</span>` : `<span class="mark-approx">${esc(SADE.approxMark)}</span>`;
  return `<span class="promotion-label" data-promoted="${e.featured ? 1 : 0}">${mark} ${esc(e.label ?? SADE.dash)}</span>`;
}

