// @vitest-environment jsdom
// Girdi formu render (§3a): aşama seçilmeden alanlar kapalı; 20 alan; denetim notları kod adıyla;
// öneri; f6 modları (repo modu yoksa Python seçeneği kapalı; elle girişte etiket).
import { describe, expect, it } from "vitest";

import { F6, FIELDS, INPUTS } from "../src/i18n/tr";
import { renderInputs, type InputsVM } from "../src/render/inputs";
import type { FormCheck } from "../src/types";
import { dom } from "./helpers";

function vm(extra: Partial<InputsVM> = {}): InputsVM {
  return {
    stage: null, fields: {}, tickerLabel: "", check: null, repoMode: false, tickers: [], prefillTicker: "", prefillMsg: null,
    missingReasons: {}, f6: { mode: "NONE", manual: "", market20: null, market20ForT: null, busy: false, error: null }, busy: false, error: null,
    ...extra,
  };
}

describe("girdi formu", () => {
  it("aşama seçilmemiş: 20 alan kapalı, Tahmin et kapalı", () => {
    const root = dom(renderInputs(vm()));
    const inputs = root.querySelectorAll<HTMLInputElement>("[data-field]");
    expect(inputs.length).toBe(20);
    expect([...inputs].every((i) => i.disabled)).toBe(true);
    expect(root.querySelector<HTMLButtonElement>("[data-action=predict]")?.disabled).toBe(true);
    expect(root.textContent).toContain(INPUTS.stageNone);
    expect(FIELDS.map((f) => f.name)).toContain("total_demand_multiple");
  });

  it("aşama seçili: denetim notları kod adıyla, öneri düğmesi, zorunluluk metni", () => {
    const check: FormCheck = {
      stage: "PRE_BOOKBUILD",
      normalized: {},
      notes: [
        { field: "planned_post_ipo_capital", code: "PB_IDENTITY", level: "error", name: "ID-A", value: "125" },
        { field: "ipo_price_tl", code: "COMMA_CONVERTED", level: "info", value: "25.52" },
      ],
      suggestions: { planned_max_offer_shares: "77500000" },
      requirements: { shares_offered: "EMPTY", ipo_price_try: "REQUIRED" },
      model_inputs: {},
    };
    const root = dom(renderInputs(vm({ stage: "PRE_BOOKBUILD", check })));
    const notes = root.querySelector('[data-notes="planned_post_ipo_capital"]')?.textContent ?? "";
    expect(notes).toContain("PB_IDENTITY");
    expect(notes).toContain("ID-A: yeni sermaye = mevcut sermaye + bedelli");
    expect(root.querySelector('[data-notes="ipo_price_tl"]')?.textContent).toContain("virgül noktaya çevrildi: 25.52");
    expect(root.querySelector<HTMLElement>('[data-action="apply-suggestion"]')?.dataset.value).toBe("77500000");
    expect(root.querySelector('[data-row="shares_offered"]')?.textContent).toContain("boş (bu aşamada beklenmez)");
    expect(root.querySelector<HTMLButtonElement>("[data-action=predict]")?.disabled).toBe(false);
  });

  it("f6: repo modu yoksa Python seçeneği kapalı; elle giriş etiketli; resmi kayıt notu", () => {
    const root = dom(renderInputs(vm({ stage: "POST_BOOKBUILD_PRE_LISTING", f6: { mode: "MANUAL", manual: "0.02", market20: null, market20ForT: null, busy: false, error: null } })));
    expect(root.querySelector<HTMLInputElement>('input[value="REPO_PYTHON"]')?.disabled).toBe(true);
    expect(root.querySelector("[data-f6-manual]")).not.toBeNull();
    expect(root.textContent).toContain(F6.manualLabel);
    expect(root.textContent).toContain(F6.officialNote);
  });

  it("f6 repo sonucu: STALE_S0 nedeni ve T bilinmiyor notu", () => {
    const root = dom(renderInputs(vm({
      stage: "POST_BOOKBUILD_PRE_LISTING", repoMode: true,
      f6: { mode: "REPO_PYTHON", manual: "", busy: false, error: null, market20ForT: "",
        market20: { t_unknown: true, record: { ref_date: "2026-09-22", f6: null, refusal: "STALE_S0", S0_date: "2026-09-01", S20_date: "2026-08-04", close_S0: null, close_S20: null, calendar_sha256: null, xu100_sha256: "04637c911f912e00" } } },
    })));
    expect(root.textContent).toContain("MARKET20_STALE_S0");
    expect(root.textContent).toContain("pinli XU100 dosyası bayat");
    expect(root.textContent).toContain(F6.tUnknown);
  });
});
