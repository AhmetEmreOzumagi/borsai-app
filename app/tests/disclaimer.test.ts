import { describe, expect, it } from "vitest";

import { DISCLAIMER, NAV } from "../src/i18n/tr";

describe("iskelet (SPEC_APP §3, §4)", () => {
  it("DISCLAIMER sabit dizesi şartnamedeki gibi", () => {
    expect(DISCLAIMER).toBe(
      "Bu uygulama yatırım tavsiyesi değildir; çıktılar istatistiksel tahmin ve olasılıklardır.",
    );
  });

  it("sol gezinme şartnamedeki yedi ekran", () => {
    expect(NAV.map((n) => n.label)).toEqual([
      "Girdi",
      "Sonuç",
      "Doğruluk",
      "Sicil",
      "Kişisel kayıtlar",
      "Ayarlar",
      "Hakkında",
    ]);
  });
});
