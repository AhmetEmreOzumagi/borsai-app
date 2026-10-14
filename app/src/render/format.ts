// Sayı biçimlendirme (SPEC_APP §4): getiri 1 ondalık yüzde, fiyat 2 ondalık TL, olasılık 0 ondalık
// yüzde, hata "puan", tooltip'te ham binary64 (Python repr). Yalnız biçimlendirme: hiçbir değer
// hesaplanmaz; yüzdeye çevirme (× 100) gösterim ölçeğidir. Çarpma/bölme yalnız bu dosyada ve svg.ts'de
// bulunabilir (statik tarama: tests/no_frontend_math.test.ts).
import type { Num } from "../types";

export const DASH = "—";

/** JSON'daki sonlu olmayan metinler ("NaN", "Infinity", "-Infinity") dahil sayıya çevirir.
 * `scores.json`'daki gerçekleşen getiriler tam Decimal METNİDİR (`realized.R.D1`); bunlar da
 * okunur — çevirme yalnız gösterim ölçeğidir, hiçbir değer hesaplanmaz. */
export function toNum(x: Num | null | undefined): number | null {
  if (x === null || x === undefined) return null;
  if (typeof x === "number") return x;
  if (x === "NaN") return Number.NaN;
  if (x === "Infinity") return Number.POSITIVE_INFINITY;
  if (x === "-Infinity") return Number.NEGATIVE_INFINITY;
  if (x.trim() === "") return null;
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

function finite(x: Num | null | undefined): number | null {
  const n = toNum(x);
  return n !== null && Number.isFinite(n) ? n : null;
}

function nonFinite(x: Num | null | undefined): string {
  const n = toNum(x);
  return n === null ? DASH : String(x);
}

/** Getiri: işaretli yüzde, 1 ondalık ("+%7.7", "-%3.2", "%0.0"). */
export function pctSigned1(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  const body = Math.abs(n * 100).toFixed(1);
  if (body === "0.0") return "%0.0";
  return `${n < 0 ? "-" : "+"}%${body}`;
}

/** Olasılık: yüzde, 0 ondalık ("%91"). */
export function pct0(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return `%${(n * 100).toFixed(0)}`;
}

/** Rust'ın yuvarladığı tamsayı yüzde ("%16"; düşüş kartı: k ve 100 − k Rust'ta). */
export function pctInt(k: number | null | undefined): string {
  return k === null || k === undefined ? DASH : `%${k}`;
}

/** Fiyat: 2 ondalık TL ("27.48 TL"). */
export function tl2(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return `${n.toFixed(2)} TL`;
}

/** Getiri hatası puanının birimsiz hâli (aralık uçları): 0.030 → "3.0". */
export function points1Bare(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return (n * 100).toFixed(1);
}

/** Getiri hatası puan: 0.030 → "3.0 puan". */
export function points1(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return `${points1Bare(x)} puan`;
}

/** Metrik (Brier, RPS, isabet, kalibrasyon): 4 ondalık (§4). */
export function metric4(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return n.toFixed(4);
}

/** Gün sayısı gibi büyüklükler: 1 ondalık. */
export function fixed1(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return n.toFixed(1);
}

/** Uyarı metinlerindeki özellik değerleri: en çok 6 anlamlı hane. */
export function short(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return String(Number(n.toPrecision(6)));
}

/** Python `repr(float)`: en kısa gidiş-dönüş haneleri; 1e-4 ≤ |x| < 1e16 sabit, dışı bilimsel ("1e-05"). */
export function pyRepr(x: Num | null | undefined): string {
  const n = toNum(x);
  if (n === null) return DASH;
  if (Number.isNaN(n)) return "nan";
  if (!Number.isFinite(n)) return n > 0 ? "inf" : "-inf";
  if (n === 0) return Object.is(n, -0) ? "-0.0" : "0.0";
  const sign = n < 0 ? "-" : "";
  const [mant, expText] = Math.abs(n).toExponential().split("e");
  const e = Number(expText);
  const digits = mant.replace(".", "");
  if (e >= -4 && e < 16) {
    if (e >= 0) {
      const intPart = digits.slice(0, e + 1).padEnd(e + 1, "0");
      const frac = digits.slice(e + 1);
      return `${sign}${intPart}.${frac === "" ? "0" : frac}`;
    }
    return `${sign}0.${"0".repeat(-e - 1)}${digits}`;
  }
  const m = digits.length > 1 ? `${digits[0]}.${digits.slice(1)}` : digits;
  return `${sign}${m}e${e < 0 ? "-" : "+"}${String(Math.abs(e)).padStart(2, "0")}`;
}

export function sha8(s: string | null | undefined): string {
  return s ? s.slice(0, 8) : DASH;
}

export function sha12(s: string | null | undefined): string {
  return s ? s.slice(0, 12) : DASH;
}

// ---------------------------------------------------------------- sade görünüm biçimleyicileri (FAZ9_APP_UI; yalnız ekleme)
// Metin dönüşümü ve gösterim ölçeği; hiçbir değer hesaplanmaz. Türkçe sözcükler (ay adları, birimler) tr.ts'ten parametre gelir.

/** ISO tarih ("2026-09-17") → "17.09.2026"; tarih-saat → "22.09.2026 15:19" (+ " UTC" Z ise). Başka metin aynen. */
export function dateTr(s: string | null | undefined): string {
  if (!s) return DASH;
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(s);
  if (!m) return s;
  const day = `${m[3]}.${m[2]}.${m[1]}`;
  if (m[4] === undefined) return day;
  return `${day} ${m[4]}:${m[5]}${s.endsWith("Z") ? " UTC" : ""}`;
}

/** ISO tarih → "17 Eylül 2026" (ay adları tr.ts'ten). */
export function readableDate(s: string | null | undefined, months: readonly string[]): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((s ?? "").trim());
  if (!m) return DASH;
  const name = months[Number(m[2]) - 1];
  return name === undefined ? DASH : `${Number(m[3])} ${name} ${m[1]}`;
}

/** Büyük sayının okunur tekrarı: 312500000 → "312.5 milyon" (birimler tr.ts'ten; en çok 3 ondalık, sondaki sıfırlar atılır). */
export function readableCount(x: Num | null | undefined, units: { thousand: string; million: string; billion: string }): string {
  const n = finite(x);
  if (n === null) return DASH;
  const trim = (v: number) => v.toFixed(3).replace(/\.?0+$/, "");
  const a = Math.abs(n);
  if (a >= 1e9) return `${trim(n / 1e9)} ${units.billion}`;
  if (a >= 1e6) return `${trim(n / 1e6)} ${units.million}`;
  if (a >= 1e4) return `${trim(n / 1e3)} ${units.thousand}`;
  return trim(n);
}

/** İşaretli metrik / katsayı, 4 ondalık ("+0.9867", "-1.0007"). */
export function signed4(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return `${n < 0 ? "-" : "+"}${Math.abs(n).toFixed(4)}`;
}

/** Fiyat metni, 2 ondalık, birimsiz ("25.52"); tablo hücreleri için (birim sütun başlığında). */
export function price2(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return nonFinite(x);
  return n.toFixed(2);
}

/** Yerel saat (gösterim): "03.10.2026 13:20". */
export function clockTr(d: Date): string {
  const f = new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  return f.format(d).replace(",", "");
}

// ---------------------------------------------------------------- FAZ9_UI_FIX (yalnız ekleme)

/** Tam sayı sayımı (işlem sayısı; K-FIX-4) tr-TR binlik ayırıcısıyla: "17885" → "17.885"; sayı yoksa tire. */
export function countTr(x: Num | null | undefined): string {
  const n = finite(x);
  if (n === null) return DASH;
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0, useGrouping: true }).format(n);
}
