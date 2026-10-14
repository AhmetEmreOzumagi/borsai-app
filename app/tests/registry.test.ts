// @vitest-environment jsdom
// Sicil ekranı ve arz sayfası (SPEC_APP §3e sonu, §3g; U38).
// Görünümler Rust `registry_view` / `record_ceiling` çıktısıdır (src-tauri/tests/stage3.rs üretir).
import { describe, expect, it } from "vitest";

import { COND, REGISTRY } from "../src/i18n/tr";
import { renderRecordPage, renderRegistryList, type RecordPageVM } from "../src/render/registry";
import type { ModelInfo, PathDisplayRow, PathParamsInfo, RecordCeiling, RegistryView, StreakView } from "../src/types";
import { dom, fx, readText, split } from "./helpers";

const view = () => fx<RegistryView>("registry_synthetic.json");
const ceiling = (name: string) => fx<RecordCeiling>(name);

function page(selected: number, extra: Partial<RecordPageVM> = {}): RecordPageVM {
  const v = view();
  return {
    ticker: v.tickers[0],
    selected,
    ceiling: null,
    streak: null,
    jSelected: 0,
    tab: "ceiling",
    hidden: [],
    declared: Array<boolean>(10).fill(false),
    declDropped: false,
    pathDisplay: fx<PathDisplayRow[]>("path_display_record.json"),
    pathParams: fx<PathParamsInfo[]>("path_params.json"),
    pathCond: [],
    models: fx<ModelInfo[]>("app_models.json"),
    hints: null,
    raw: null,
    cancelReason: "",
    cancelDone: null,
    today: v.today_istanbul,
    ...extra,
  };
}

describe("sicil ekranı", () => {
  it("arzları, kayıt sayılarını ve push kanıtı dosyalarını listeler", () => {
    const v = view();
    const root = dom(renderRegistryList(v));
    const rows = [...root.querySelectorAll<HTMLElement>(".registry-table tbody tr")];
    expect(rows.map((r) => r.dataset.ticker)).toEqual(["SNTA1", "SNTB2"]);
    expect(rows[0].textContent).toContain("Sentetik Test A.Ş.");
    expect(rows[0].textContent).toContain("2030-01-10");
    expect(root.querySelector(".proofs")?.textContent).toBe(REGISTRY.proofsTitle(v.proofs.length));
    expect(root.querySelector(".git-status")?.textContent).toContain(REGISTRY.gitClean);
    expect(root.textContent).toContain(REGISTRY.ipos(v.ipos.length));
    // sınıf hesaplanmaz uyarısı her zaman görünür
    expect(root.textContent).toContain(REGISTRY.proofNote);
  });

  it("boş sicil: ne yapılacağı yazılı", () => {
    const v = { ...view(), tickers: [] };
    expect(dom(renderRegistryList(v)).querySelector(".empty-state")?.textContent).toBe(REGISTRY.empty);
  });
});

describe("arz sayfası", () => {
  it("bir arzın birden çok kaydı ayrı sekmelerde; iptal edilen sekme üstü çizili", () => {
    const root = dom(renderRecordPage(page(0)));
    const tabs = [...root.querySelectorAll<HTMLElement>(".record-tabs .tab")];
    expect(tabs.length).toBe(4);
    expect(tabs[0].classList.contains("active")).toBe(true);
    expect(tabs[1].classList.contains("record-cancelled")).toBe(true);
    expect(tabs[2].textContent).toContain("İptal kaydı");
    expect(root.textContent).toContain(REGISTRY.primaryNote);
  });

  it("iptal edilen kayıt: üstü çizili bant, neden ve zaman", () => {
    const root = dom(renderRecordPage(page(1)));
    const band = root.querySelector(".cancelled-band");
    expect(band?.textContent).toContain(REGISTRY.cancelled);
    expect(band?.textContent).toContain("kurgusal: girdi belgesinde hatalı f3");
    expect(band?.textContent).toContain("2030-01-05T15:00:00+03:00");
    expect(root.querySelector(".cancel-form")).toBeNull();
  });

  it("push kanıtı göstergesi sınıf hesaplamaz", () => {
    const root = dom(renderRecordPage(page(0)));
    expect(root.querySelector(".proof")?.textContent).toBe(REGISTRY.proofMissing);
    expect(root.querySelector(".proof-line")?.textContent).toContain(REGISTRY.untracked);
    expect(root.textContent).toContain(REGISTRY.proofNote);
  });

  it("desteklenmeyen modeller adıyla listelenir, çıktıları render edilmez", () => {
    const rc = ceiling("record_ceiling_j3.json");
    const root = dom(renderRecordPage(page(0, { ceiling: rc, jSelected: 3 })));
    const items = [...root.querySelectorAll<HTMLElement>(".unsupported-models li")];
    expect(items.map((x) => x.dataset.model)).toEqual(["zzz_future_a", "zzz_future_b", "zzz_future_c"]);
    expect(items[0].textContent).toContain(REGISTRY.unsupportedNote);
    for (const id of ["zzz_future_a", "zzz_future_c"]) {
      expect(root.querySelector(`.cond-table td[data-model="${id}"]`)).toBeNull();
    }
  });

  it("U38: koşullu değerler yalnız kayıttaki S'ten; kaynak satırı kaydı ve params sha'sını yazar", () => {
    const rc = ceiling("record_ceiling_j3.json");
    const root = dom(renderRecordPage(page(0, { ceiling: rc, jSelected: 3 })));
    expect(root.querySelector(".record-source")?.textContent).toContain(REGISTRY.recordSource(rc.file));
    expect(root.querySelector(".record-source")?.textContent).toContain("ceiling_hazard_v0=");
    expect(root.textContent).toContain(REGISTRY.recordOnly);
    // kayıttaki S = 0.5^k → S_k|j=3 = 0.5^(k−3): k = 4 → %50, k = 5 → %25
    const cells = [...root.querySelectorAll<HTMLElement>('.cond-table td[data-model="ceiling_hazard_v0"]')];
    expect(cells[0].textContent).toBe("%50");
    expect(cells[1].textContent).toBe("%25");
    expect(root.querySelector<HTMLElement>(".cond-table")?.dataset.j).toBe("3");
  });

  it("j = 0: koşulsuz görünüm de kayıttan gelir", () => {
    const rc = ceiling("record_ceiling_j0.json");
    const root = dom(renderRecordPage(page(0, { ceiling: rc, jSelected: 0 })));
    const first = root.querySelector<HTMLElement>('.cond-table td[data-model="ceiling_hazard_v0"]');
    expect(first?.textContent).toBe("%50");
  });

  it("şerit beyanı arz sayfasında da çalışır (yalnız etiket, yalnız bellekte)", () => {
    const streak = fx<StreakView>("streak_sntb1.json"); // resmi j = 2, D3 PENDING
    const declared = [false, false, true, false, false, false, false, false, false, false];
    const rc = ceiling("record_ceiling_u52_j2.json");
    const root = dom(renderRecordPage(page(0, { ceiling: rc, streak, jSelected: 2, declared })));
    expect(root.querySelector(".user-badge")?.textContent).toBe(COND.userBadge);
    expect(root.textContent).toContain(COND.userNote);
    // beyan resmi verinin önünde: koşullu bölüm boş (U52-3)
    expect(root.querySelector(".official-pending")?.textContent).toBe(COND.officialPending);
    expect(root.querySelector(".cond-table")).toBeNull();
  });

  it("iptal formu: neden boşken düğme kapalı; T geçtiyse kural önceden gösterilir", () => {
    const closed = dom(renderRecordPage(page(0)));
    expect(closed.querySelector<HTMLButtonElement>("[data-action=cancel-record]")?.disabled).toBe(true);
    expect(closed.querySelector(".cancel-blocked")).toBeNull();
    expect(closed.textContent).toContain(REGISTRY.cancelRuleNote);
    const open = dom(renderRecordPage(page(0, { cancelReason: "girdi belgesi hatalı" })));
    expect(open.querySelector<HTMLButtonElement>("[data-action=cancel-record]")?.disabled).toBe(false);
    const late = dom(renderRecordPage(page(0, { today: "2030-02-01" })));
    expect(late.querySelector(".cancel-blocked")?.textContent).toBe(REGISTRY.cancelBlocked("2030-01-10"));
  });

  it("okunamayan ve eski sürümlü kayıtlar listede durur, içerik gösterilmez", () => {
    const old = dom(renderRecordPage(page(3)));
    expect(old.querySelector(".error-box")?.textContent).toBe(REGISTRY.unsupportedVersion("borsai.record/0"));
    const v = view();
    const broken = dom(renderRecordPage(page(0, { ticker: v.tickers[1] })));
    expect(broken.querySelector(".error-box")?.textContent).toContain(REGISTRY.unreadable);
  });
});

describe("resmi görünüm modeli yeniden çalıştırmaz (U38 / U49 statik)", () => {
  it("sicil ekranı ve arz sayfası predict_all yolunu hiç çağırmaz", () => {
    for (const f of ["src/screens/registry.ts", "src/render/registry.ts", "src/render/freeze.ts"]) {
      const text = readText(f);
      expect(text.includes("predictAll"), f).toBe(false);
      expect(text.includes("predict_all"), f).toBe(false);
    }
  });

  /** U49: tahmin yolu çağrı sayacı 0 — arz sayfası yalnız kayıt/dosya okuyan komutları çağırır. */
  it("arz sayfasının çağırdığı komutlar sabit bir kümededir", () => {
    const { code } = split(readText("src/screens/registry.ts"));
    const calls = [...new Set([...code.matchAll(/api\.(\w+)/g)].map((m) => m[1]))].sort();
    const allowed = new Set([
      "cancelRecord", "copySourceDocs", "freezePreflight", "freezeRecord", "inputsPitCheck",
      "pathConditional", "pathDisplay", "pathParams", "previewInputsDoc", "readRecordJson",
      "readSourceManifest", "recordCeiling", "registryView", "streakView", "writeInputsDoc",
      "recordSummary", // EK 3 U62: Tavan serisi kartı yalnız kayıttan (Rust record_summary; predict_all yok)
      // EK 3 P2: D1 sonrası satırı yalnız registry/post_d1 kaydından; sihirbaz Python freeze --post-d1 (predict_all yok)
      "postD1View", "postD1Records", "postD1Preflight", "postD1Freeze", "postD1Cancel", "postD1Todo",
    ]);
    expect(calls.filter((c) => !allowed.has(c))).toEqual([]);
    expect(calls).toContain("pathConditional");
  });
});
