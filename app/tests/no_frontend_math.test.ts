// K2 / U25 statik tarama kalıbı: ön uç hesap yapmaz. Bütün sayılar Rust komutlarından gelir.
// - Hiçbir TS dosyasında metrik/istatistik fonksiyonu yok (bootstrap, percentile, mean( …).
// - Çarpma, bölme, mod ve üs işleçleri yalnız render/format.ts (yüzde biçimlendirme) ve render/svg.ts
//   (piksel koordinatı) içinde; yorumlar ve metin sabitleri taramadan önce ayıklanır.
// - Rust tarafında skor metriği hesaplayan fonksiyon yok (beyaz liste: beklenen/medyan L).
// - U21 hazırlığı: Türkçe serbest metin yalnız i18n/tr.ts'te; §4 yasak sözcükleri tr.ts'te yok.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, sep } from "node:path";
import { describe, expect, it } from "vitest";

import { APP_DIR, split } from "./helpers";

const SRC = join(APP_DIR, "src");
const RUST_SRC = join(APP_DIR, "src-tauri", "src");

function walk(dir: string, ext: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p, ext) : p.endsWith(ext) ? [p] : [];
  });
}

const files = walk(SRC, ".ts");
// Windows'ta ayırıcı '\\'; izin listeleri '/' ile yazılı (FAZ9_WINDOWS: yalnız ayırıcı, iddia aynı)
const rel = (p: string) => p.slice(SRC.length + 1).split(sep).join("/");

describe("ön uçta hesap yok (K2, U25 kalıbı)", () => {
  it("ayrıştırıcı kendini sınar", () => {
    const s = split("const a = `x ${b * 2} y`; // c / d\nconst e = 'f / g'; /* h * i */");
    expect(s.code).toContain("b * 2");
    expect(s.code).not.toContain("c / d");
    expect(s.code).not.toContain("f / g");
    expect(s.code).not.toContain("h * i");
    expect(s.strings).toContain("f / g");
  });

  it("metrik/istatistik fonksiyonu yok", () => {
    const banned = [/bootstrap/i, /percentile/i, /quantile/i, /\bmean\s*\(/, /\bmedian\s*\(/, /\baverage/i, /stdev|variance/i, /\.reduce\s*\(/, /\bsum\s*\(/, /Math\.(exp|log|pow|sqrt)/, /\*\*/];
    for (const f of files) {
      const { code } = split(readFileSync(f, "utf-8"));
      for (const b of banned) expect(b.test(code), `${rel(f)}: ${b}`).toBe(false);
    }
  });

  it("çarpma/bölme/mod yalnız render/format.ts ve render/svg.ts'te", () => {
    const allowed = new Set(["render/format.ts", "render/svg.ts"]);
    const op = /[^/*]\s*[*/%]\s*[^/*=]/;
    for (const f of files) {
      if (allowed.has(rel(f))) continue;
      const { code } = split(readFileSync(f, "utf-8"));
      const bad = code.split("\n").filter((l) => op.test(l) && !/^\s*import /.test(l));
      expect(bad, rel(f)).toEqual([]);
    }
  });

  // U25 genişletmesi (EK 2 §4): tavan yolu sayıları da ön uçta üretilmez.
  it("tavan yolu fiyatı ve kuantilleri ön uçta hesaplanmaz (yalnız Rust alanları okunur)", () => {
    for (const f of files) {
      if (rel(f) === "types.ts") continue; // yalnız alan bildirimleri (sözleşme)
      const { code } = split(readFileSync(f, "utf-8"));
      // `approx_price`, `c_text`, `limit_path_return` yalnız okunur: atama ya da aritmetik yok
      expect(/\b(approx_price|c_text|limit_path_return)\s*[:=][^=]/.test(code), rel(f)).toBe(false);
      expect(/\bq(10|50|90)\s*[-+*/]/.test(code), rel(f)).toBe(false);
    }
  });

  it("yelpaze grafiği (band poligonu) yalnız render/svg.ts'te çizilir", () => {
    for (const f of files) {
      if (rel(f) === "render/svg.ts") continue;
      const { code, strings } = split(readFileSync(f, "utf-8"));
      expect(/polygon|fill-opacity/.test(code + strings.join(" ")), rel(f)).toBe(false);
    }
  });

  it("koşullu değerler ön uçta bölünmez: S_cond/P_L_cond yalnız okunur", () => {
    for (const f of files) {
      const { code } = split(readFileSync(f, "utf-8"));
      expect(/S\s*\[[^\]]*\]\s*\//.test(code), rel(f)).toBe(false);
    }
  });

  // EK 3 §8.4 (P4): düşüş olasılığı (1 − p_up) ve tamamlayan yüzde (100 − k) yalnız Rust'ta (commands/fall.rs)
  it("düşüş olasılığı ön uçta türetilmez: p_up'tan çıkarma, 100'den çıkarma yok", () => {
    for (const f of files) {
      if (rel(f) === "types.ts") continue;
      const { code } = split(readFileSync(f, "utf-8"));
      expect(/\b1\s*-\s*[\w.?]*p_up\b/.test(code), rel(f)).toBe(false);
      expect(/\b100\s*-\s*[\w.?(]/.test(code), rel(f)).toBe(false);
      expect(/\bp_up\s*[-+*/]/.test(code), rel(f)).toBe(false);
    }
  });

  it("Rust'ta skor metriği hesaplayan fonksiyon yok (beklenen/medyan L beyaz listede)", () => {
    const banned = /bootstrap|percentile|quantile|fn\s+(mean|brier|rps|mae|accuracy)\b/i;
    for (const f of walk(RUST_SRC, ".rs")) {
      expect(banned.test(readFileSync(f, "utf-8")), f).toBe(false);
    }
  });

  it("Türkçe serbest metin yalnız i18n/tr.ts'te", () => {
    const tr = /[çğıöşüÇĞİÖŞÜ]/;
    for (const f of files) {
      if (rel(f) === "i18n/tr.ts") continue;
      const { strings } = split(readFileSync(f, "utf-8"));
      expect(strings.filter((s) => tr.test(s)), rel(f)).toEqual([]);
    }
  });

  it("§4 yasak sözcükleri tr.ts'te yok", () => {
    const text = readFileSync(join(SRC, "i18n/tr.ts"), "utf-8").toLocaleLowerCase("tr");
    for (const w of ["kesin", "garanti", "kazandırır", "al/sat", "hedef fiyat", "sinyal"]) expect(text, w).not.toContain(w);
    expect(/doğruluk %\d/.test(text)).toBe(false);
  });
});
