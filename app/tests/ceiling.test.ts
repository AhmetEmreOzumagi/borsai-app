// @vitest-environment jsdom
// U40: şerit ve tanımsızlık (sentetik SNTA1; görünümler Rust streak_view/ceiling_display çıktısı).
import { describe, expect, it } from "vitest";

import { COND } from "../src/i18n/tr";
import { renderConditional, renderStrip, type ConditionalVM } from "../src/render/ceiling";
import type { CeilingDisplay, StreakView } from "../src/types";
import { dom, fx } from "./helpers";

function vm(streak: string | null, cond: string, jSelected: number, extra: Partial<ConditionalVM> = {}): ConditionalVM {
  return {
    streak: streak ? fx<StreakView>(streak) : null,
    cond: fx<CeilingDisplay>(cond),
    jSelected,
    tab: "ceiling",
    hidden: [],
    declared: Array<boolean>(10).fill(false),
    declDropped: false,
    pathAvailable: false,
    pathCond: [],
    pathParams: [],
    recordWithoutPath: false,
    ...extra,
  };
}

const states = (root: HTMLElement) => [...root.querySelectorAll<HTMLElement>(".day")].map((d) => d.dataset.state);

describe("U40 şerit", () => {
  it("3 OK-tavan + PENDING → j = 3; şerit yeşil×3 + gri; kaynak satırı", () => {
    const s = fx<StreakView>("streak_pending.json");
    expect(s.j_observed).toBe(3);
    const root = dom(renderStrip(s));
    expect(states(root).slice(0, 4)).toEqual(["CEILING", "CEILING", "CEILING", "PENDING"]);
    expect(root.querySelectorAll(".day-CEILING").length).toBe(3);
    expect(root.textContent).toContain("kaynak: data/outcomes/SNTA1.csv (as-of 2030-01-09)");
    const c = dom(renderConditional(vm("streak_pending.json", "ceiling_netgl_j3.json", 3)));
    expect(c.textContent).toContain(COND.jObserved(3));
    expect(c.querySelector(".hypo")).toBeNull();
    expect(c.querySelector("svg.cond-curve")).not.toBeNull();
    expect(c.querySelector<HTMLElement>(".cond-table")?.dataset.j).toBe("3");
  });

  it("2 tavan + 1 tavan değil → 'seri D3'te bozuldu; L = 2', koşullu eğri yok", () => {
    const root = dom(renderConditional(vm("streak_broken.json", "ceiling_netgl_j3.json", 2)));
    expect(root.querySelector(".broken-box")?.textContent).toBe("seri D3'te bozuldu; gerçekleşen L = 2");
    expect(root.querySelector("svg.cond-curve")).toBeNull();
    expect(root.querySelector(".cond-table")).toBeNull();
  });

  it("NA_LIMIT satırı → 'etiket yok' + uyarı; eğri j ile yine var", () => {
    const root = dom(renderConditional(vm("streak_na_limit.json", "ceiling_netgl_j3.json", 1)));
    expect(states(root)[1]).toBe("NO_LABEL");
    expect(root.querySelector(".day-NO_LABEL")?.textContent).toContain(COND.state.NO_LABEL);
    expect(root.querySelector(".unlabeled")?.textContent).toBe(COND.unlabeled);
  });

  it("j = 10 → bütün koşullu hücreler '—'", () => {
    const d = fx<CeilingDisplay>("ceiling_netgl_j10.json");
    expect(d.rows.every((r) => r.cond === null)).toBe(true);
    const root = dom(renderConditional(vm("streak_all10.json", "ceiling_netgl_j10.json", 10)));
    expect(root.textContent).toContain(COND.undefinedAll);
    const cells = [...root.querySelectorAll(".cond-table td")];
    expect(cells.length).toBeGreaterThan(0);
    expect(cells.every((c) => c.textContent === "—")).toBe(true);
  });

  it("S_j = 0 → o model '—', her zaman tavan tanımlı", () => {
    const root = dom(renderConditional(vm(null, "ceiling_zero_sj.json", 2)));
    const km = [...root.querySelectorAll<HTMLElement>('.cond-table td[data-model="base_km_expanding"]')];
    expect(km.length).toBeGreaterThan(0);
    expect(km.every((c) => c.textContent === "—")).toBe(true);
    expect(root.querySelector('.cond-table td[data-model="ALWAYS_CEILING"]')?.textContent).toBe("%100");
  });

  it("gözlenen j ile seçilen j farklı → 'varsayımsal j'", () => {
    const root = dom(renderConditional(vm("streak_pending.json", "ceiling_netgl_j3.json", 5)));
    expect(root.querySelector(".hypo")?.textContent).toBe(COND.hypothetical);
  });

  // U52 (proje sahibi kararı 2026-09-23): beyan yalnız etikettir; eski "hesap beyanla yapılır"
  // davranışı kalktı. Beyan resmi j'yi değiştirmez, çelişkide gösterilmez.
  it("kullanıcı beyanı yalnız etiket: resmi j ve şerit durumu dosyadan kalır", () => {
    const s = fx<StreakView>("streak_sntb1.json");
    const declared = [false, false, true, false, false, false, false, false, false, false];
    const root = dom(renderStrip(s, declared));
    expect(s.j_observed).toBe(2);
    expect(root.querySelector(".user-badge")?.textContent).toBe(COND.userBadge);
    const d3 = root.querySelector<HTMLElement>('.day[data-h="3"]');
    expect(d3?.classList.contains("declared")).toBe(true);
    expect(d3?.dataset.state).toBe("PENDING");
    expect(root.textContent).toContain(COND.declaredNotCounted(3));
    expect(root.textContent).toContain(COND.userNote);
  });

  it("beyan resmi veriyle çelişirse gösterilmez; uyarı çıkar", () => {
    const s = fx<StreakView>("streak_broken.json"); // D3 dosyada 'tavan değil'
    const declared = [false, false, true, false, false, false, false, false, false, false];
    const root = dom(renderStrip(s, declared));
    expect(root.querySelector(".decl-conflict")?.textContent).toBe(COND.declarationConflict);
    expect(root.querySelector(".user-badge")).toBeNull();
    expect(root.querySelector<HTMLElement>('.day[data-h="3"]')?.dataset.state).toBe("NOT_CEILING");
  });

  it("dosya yok → 'gözlenen seri yok (Faz 2B henüz üretmedi)'", () => {
    expect(dom(renderStrip(fx<StreakView>("streak_missing.json"))).textContent).toContain("gözlenen seri yok (Faz 2B henüz üretmedi)");
  });

  it("getiri (koşullu) sekmesi: 'henüz yok'", () => {
    const root = dom(renderConditional(vm("streak_pending.json", "ceiling_netgl_j3.json", 3, { tab: "return" })));
    expect(root.querySelector(".return-none")?.textContent).toBe(COND.returnNone);
  });

  it("koşullu değerler Rust çıktısıyla aynı (ön uç bölme yapmaz)", () => {
    const d = fx<CeilingDisplay>("ceiling_netgl_j3.json");
    const row = d.rows.find((r) => r.model_id === "ceiling_hazard_v0");
    const root = dom(renderConditional(vm("streak_pending.json", "ceiling_netgl_j3.json", 3)));
    const cell = root.querySelector<HTMLElement>('.cond-table td[data-model="ceiling_hazard_v0"]');
    expect(cell?.textContent).toBe(`%${((row?.cond?.S_cond[3] as number) * 100).toFixed(0)}`);
  });
});

describe("Türkçe bulunma eki", () => {
  it("D1'de, D3'te, D6'da, D10'da", () => {
    expect(COND.broken(1, 0)).toBe("seri D1'de bozuldu; gerçekleşen L = 0");
    expect(COND.broken(3, 2)).toBe("seri D3'te bozuldu; gerçekleşen L = 2");
    expect(COND.broken(6, 5)).toBe("seri D6'da bozuldu; gerçekleşen L = 5");
    expect(COND.broken(10, 9)).toBe("seri D10'da bozuldu; gerçekleşen L = 9");
  });
});
