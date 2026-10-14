// @vitest-environment jsdom
// U36: farklı models_index_sha256 ile kaydedilmiş senaryo sarı uyarıyla açılır; çıktı dosyadaki gibi
// gösterilir (üzerine yazılmaz, yeniden hesaplanmaz). Fixture: Rust load_scenario çıktısı.
import { describe, expect, it } from "vitest";

import { RESULTS } from "../src/i18n/tr";
import { renderResults } from "../src/render/results";
import { renderScenarioList } from "../src/screens/scenarios";
import { resultsFromScenario } from "../src/state";
import type { LoadedScenario, ModelInfo, PathDisplayRow, PathParamsInfo } from "../src/types";
import { dom, fx } from "./helpers";

describe("U36: senaryo yükleme", () => {
  const loaded = fx<LoadedScenario>("scenario_other_index.json");
  const r = resultsFromScenario(loaded);

  it("belge biçimi: official false, record_type yok, 27 çıktı", () => {
    expect(loaded.doc.schema_version).toBe("borsai.app_scenario/1");
    expect(loaded.doc.official).toBe(false);
    expect("record_type" in loaded.doc).toBe(false);
    expect(Object.keys(loaded.doc.outputs).length).toBe(27);
    expect(r.runs.length).toBe(27);
    expect(r.source).toBe("SCENARIO");
  });

  it("farklı INDEX sha → sarı uyarı; dosyadaki çıktı aynen (0.0123456789 → +%1.2)", () => {
    const root = dom(renderResults({
      runs: r.runs, pathDisplay: fx<PathDisplayRow[]>("path_display_netgl.json"), pathParams: fx<PathParamsInfo[]>("path_params.json"),
      ceiling: null, hints: null, models: fx<ModelInfo[]>("app_models.json"), hidden: [],
      scenario: r.scenario, f6: r.f6, openCard: null, openWarnings: null, savedId: null, canSave: false,
    }));
    expect(root.querySelector(".other-index")?.textContent).toBe(RESULTS.otherIndex);
    expect(root.querySelector('td.cell[data-model="v1_5_h99"][data-h="D1"] .ret')?.textContent).toBe("+%1.2");
    expect(root.querySelector('td.cell[data-model="v1_5_h99"][data-h="D1"]')?.getAttribute("title")).toContain("return=0.0123456789");
    expect(root.querySelector("[data-action=save-scenario]")).toBeNull();
    expect(loaded.doc.outputs.v1_5_h99.output?.D1?.return).toBe(0.0123456789);
  });

  it("aynı INDEX sha → uyarı yok", () => {
    const same = resultsFromScenario({ ...loaded, same_index: true });
    const root = dom(renderResults({
      runs: same.runs, pathDisplay: [], pathParams: [], ceiling: null, hints: null, models: [], hidden: [], scenario: same.scenario, f6: same.f6,
      openCard: null, openWarnings: null, savedId: null, canSave: false,
    }));
    expect(root.querySelector(".other-index")).toBeNull();
    expect(root.textContent).toContain(loaded.doc.title);
  });

  it("liste: gömülü kümeyle aynı değil, eski sürüm açılmaz", () => {
    const html = renderScenarioList([
      { scenario_id: "01J0000000000000000000FXTR", status: "OK", title: "a", created_at_local: "x", stage: "PRE_BOOKBUILD", ticker_label: "", app_version: "0.1.0", models_index_sha256: "0".repeat(64), same_index: false, schema_version: "borsai.app_scenario/1" },
      { scenario_id: "01J0000000000000000000FXTS", status: "OLD_VERSION", title: "b", created_at_local: "y", stage: null, ticker_label: "", app_version: null, models_index_sha256: null, same_index: false, schema_version: "borsai.app_scenario/0" },
    ], null);
    const root = dom(html);
    expect(root.querySelectorAll("[data-action=open]").length).toBe(1);
    expect(root.querySelectorAll("[data-action=delete]").length).toBe(2);
    expect(root.textContent).toContain("Kişisel kayıtlar sicile ve doğruluk hesabına girmez.");
    expect(dom(renderScenarioList([], null)).textContent).toContain("Henüz kişisel kayıt yok");
  });
});
