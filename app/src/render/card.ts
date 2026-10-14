// Model kartı: sonuç ekranı ve doğruluk paneli TEK bu fonksiyonu kullanır (SPEC_APP §3b, §3d, U21).
// Alan kümesi ve sırası iki ekranda aynıdır. Kartta hiçbir sayı hesaplanmaz: değerler ya gömülü
// INDEX künyesinden ya da `scores.json`'dan olduğu gibi gelir (U25).
import { esc } from "../dom";
import { CARD } from "../i18n/tr";
import { DASH, sha8 } from "./format";

/** §8 eşikleri; dosyanın kendi `definitions.small_n` değerleriyle aynı (uygulama hesaplamaz). */
export const MIN_N_METRIC = 10;
export const MIN_N_VERDICT = 30;

export interface CardVM {
  modelId: string;
  /** "Ne yapar": gömülü INDEX künyesi. */
  description: string | null;
  /** "Tür": KIND_TEXT karşılığı (çağıran çevirir). */
  kind: string | null;
  /** Tavan yolu modellerinde seri modeli satırı; başka türlerde null (satır çizilmez). */
  survival: string | null;
  trainingN: string | null;
  trainingCutoff: string | null;
  /** Gösterilecek params sha256 (ham ya da ilk 8). */
  sha: string | null;
  /**
   * Karşılaştırma için öteki kaynağın sha'sı: sonuç ekranında `scores.json` kartı, doğruluk
   * panelinde gömülü modelin sha'sı. İkisi de biliniyor ve ilk 8 hane farklıysa sarı uyarı.
   */
  shaCompare: string | null;
  variants: string | null;
  /** Önceden ilan edilmiş birincil hücre metni; yoksa null. */
  primary: string | null;
  /** Canlı skorlanan arz sayısı (`scores.json`); bilinmiyorsa null. */
  liveN: number | null;
  /** Birincil hücrenin canlı hükmü; YALNIZ dosyadaki `verdict` alanından. */
  liveVerdict: string | null;
}

/** Prospektif durum: n < 10'da hüküm yok metni, n ≥ 10'da yalnız dosyadaki verdict (§3d, U19). */
export function prospectiveText(v: CardVM): string {
  if (v.liveN === null) return DASH;
  if (v.liveN < MIN_N_METRIC) return CARD.liveNoVerdict(String(v.liveN));
  return v.liveVerdict ?? DASH;
}

/** İki kaynağın sha'sı biliniyor ve ilk 8 hane farklı: skorlar bu parametrelerle üretilmemiş. */
export function shaMismatch(v: CardVM): boolean {
  if (v.sha === null || v.sha === "" || v.shaCompare === null || v.shaCompare === "") return false;
  return sha8(v.sha) !== sha8(v.shaCompare);
}

export function cardRows(v: CardVM): [string, string][] {
  const rows: [string, string][] = [
    [CARD.what, v.description ?? DASH],
    [CARD.kind, v.kind ?? DASH],
  ];
  if (v.survival !== null) rows.push([CARD.survival, v.survival]);
  rows.push(
    [CARD.training, `${v.trainingN ?? DASH} / ${v.trainingCutoff ?? DASH}`],
    [CARD.sha, sha8(v.sha)],
    [CARD.variants, v.variants ?? DASH],
    [CARD.primary, v.primary ?? `${DASH} (${CARD.primaryNone})`],
    [CARD.prospective, prospectiveText(v)],
  );
  return rows;
}

/** Kart gövdesi (başlık çağıranındır: sonuç ekranında panel başlığı, panelde tablo başlığı). */
export function renderModelCard(v: CardVM, caption: string): string {
  const warn = shaMismatch(v)
    ? `<p class="warn-box sha-scores-mismatch" data-model="${esc(v.modelId)}">${esc(CARD.shaMismatch)}</p>`
    : "";
  return `<table class="kv model-card" data-model="${esc(v.modelId)}"><caption>${esc(caption)}</caption>` +
    cardRows(v).map(([k, val]) => `<tr><th>${esc(k)}</th><td>${esc(val)}</td></tr>`).join("") +
    `</table>${warn}`;
}
