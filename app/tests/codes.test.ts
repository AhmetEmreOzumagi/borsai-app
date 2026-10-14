// U8: her T-2 kodu için arayüz metni var; tr.ts anahtar kümesi = Rust'ın kod kümesi (+ şartname T-2).
import { describe, expect, it } from "vitest";

import { CODE_TEXT, MARKET20_REASON_TEXT } from "../src/i18n/tr";
import { codeText } from "../src/render/codes";
import { readText } from "./helpers";

function rustCodes(): Set<string> {
  const err = readText("src-tauri/crates/borsai_predict/src/error.rs");
  const consts = [...err.matchAll(/pub const [A-Z0-9_]+: &str = "([A-Z0-9_]+)";/g)].map((m) => m[1]).filter((c) => c !== "MARKET20_");
  const m20 = readText("src-tauri/crates/borsai_predict/src/market20.rs");
  const block = m20.match(/MARKET20_REASONS: \[&str; \d+\] = \[([^\]]*)\]/);
  const reasons = [...(block?.[1] ?? "").matchAll(/"([A-Z0-9_]+)"/g)].map((m) => `MARKET20_${m[1]}`);
  // predict_market20: f6 metni sayı değilse MARKET20_NOT_NUMERIC (format! ile kurulur)
  expect(m20).toContain('format!("{MARKET20_PREFIX}NOT_NUMERIC")');
  return new Set([...consts, ...reasons, "MARKET20_NOT_NUMERIC"]);
}

function specCodes(): Set<string> {
  const spec = readText("../docs/app/SPEC_APP.md");
  const start = spec.indexOf("#### 3b.1");
  const end = spec.indexOf("Parametre dosyası hataları", start);
  const out = new Set<string>();
  for (const line of spec.slice(start, end).split("\n").filter((l) => l.startsWith("| ") && !l.startsWith("| Kod"))) {
    const first = line.split("|")[1];
    for (const m of first.matchAll(/`([A-Z0-9_]+)`/g)) out.add(m[1]);
  }
  return out;
}

describe("codes_have_text (U8)", () => {
  it("tr.ts kod kümesi = Rust sabitleri", () => {
    expect(new Set(Object.keys(CODE_TEXT))).toEqual(rustCodes());
  });

  it("şartname T-2 tablosundaki her kodun metni var", () => {
    const spec = specCodes();
    expect(spec.size).toBeGreaterThanOrEqual(25);
    for (const c of spec) expect(Object.keys(CODE_TEXT), c).toContain(c);
  });

  it("her metin boş değil ve yer tutucular dolar", () => {
    for (const c of Object.keys(CODE_TEXT)) {
      const t = codeText(c, "total_demand_multiple", { code: c, message: "", feature: "f3", value: 500, train_min: 0.5, train_max: 120, used: 88.1, horizon: "D1" });
      expect(t.length, c).toBeGreaterThan(5);
      expect(t, c).not.toContain("undefined");
    }
    expect(codeText("INPUT_MISSING", "ipo_price_tl")).toBe("Halka arz fiyatı (TL) (ipo_price_tl) boş; bu model bu alansız tahmin vermez");
    expect(codeText("OUT_OF_TRAINING_RANGE", null, { code: "OUT_OF_TRAINING_RANGE", message: "", feature: "f3", value: 500, train_min: 0.5, train_max: 120 }))
      .toBe("f3 = 500 eğitim aralığı [0.5, 120] dışında; tahmin dışdeğerlemedir");
  });

  it("MARKET20 nedenlerinin açıklaması §3a.2'deki gibi", () => {
    expect(MARKET20_REASON_TEXT.STALE_S0).toContain("pinli XU100 dosyası bayat");
    expect(MARKET20_REASON_TEXT.CALENDAR_NOT_COVERING).toBe("takvim uzatması bitti");
    expect(codeText("MARKET20_STALE_S0", "f6_market20")).toContain("f6 (20 seanslık XU100 getirisi) yok");
  });
});
