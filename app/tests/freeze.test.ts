// @vitest-environment jsdom
// Resmi "dondur" sihirbazı (SPEC_APP §3e; U30, U32). Görünümler Rust çıktısıdır
// (`freeze_preflight`, `copy_source_docs`, `preview_inputs_doc`, `freeze_record`).
import { describe, expect, it } from "vitest";

import { ERROR_TEXT, FREEZE, TUFE } from "../src/i18n/tr";
import { parityText, renderFreezeWizard, type FreezeVM } from "../src/render/freeze";
import type { FreezeResult, InputsDocPreview, Preflight, SourceDocsView } from "../src/types";
import { dom, fx, readText } from "./helpers";

function vm(extra: Partial<FreezeVM> = {}): FreezeVM {
  return {
    repoMode: true,
    hasResults: true,
    ticker: "SNTA1",
    company: "Sentetik Test A.Ş.",
    stage: "POST_BOOKBUILD_PRE_LISTING",
    values: { ipo_price_tl: "25.52", total_demand_multiple: "2.84", first_trading_date: "2030-01-10", ipo_size_tl: null },
    docs: [],
    copied: null,
    manifest: null,
    fields: {},
    collectionRules: FREEZE.defaultRules,
    ftdSource: "",
    preflight: null,
    preview: null,
    written: null,
    pit: null,
    acknowledged: false,
    frozen: null,
    busy: null,
    error: null,
    ...extra,
  };
}

describe("sihirbaz kabuğu", () => {
  it("6 adım, sırayla ve numaralı", () => {
    const root = dom(renderFreezeWizard(vm()));
    const steps = [...root.querySelectorAll<HTMLElement>(".wizard-step")];
    expect(steps.map((s) => s.dataset.step)).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(steps.map((s) => s.querySelector("h3")?.textContent)).toEqual(
      FREEZE.steps.map((t, i) => FREEZE.step(i + 1, t)),
    );
  });

  it("repo modu yoksa kapalı; tahmin yoksa girdi ekranına yönlendirir", () => {
    expect(dom(renderFreezeWizard(vm({ repoMode: false }))).querySelector(".closed-state")?.textContent).toBe(FREEZE.closed);
    const noRes = dom(renderFreezeWizard(vm({ hasResults: false })));
    expect(noRes.querySelector(".need-results")?.textContent).toBe(FREEZE.needResults);
    expect(noRes.querySelector("[data-action=go-inputs]")).not.toBeNull();
  });
});

describe("adım 1: ön koşullar", () => {
  it("geçen ön koşullar: tamam kutusu ve sha'lar", () => {
    const p = fx<Preflight>("preflight_ok.json");
    const root = dom(renderFreezeWizard(vm({ preflight: p })));
    expect(root.querySelector(".ok-box")?.textContent).toBe(FREEZE.preflightOk);
    expect(root.querySelector(".blockers")).toBeNull();
    expect(root.textContent).toContain(p.index_sha_embedded.slice(0, 12));
  });

  it("gömülü INDEX farklıysa DUR ve gerekçe", () => {
    const p = fx<Preflight>("preflight_blocked.json");
    expect(p.ok).toBe(false);
    const root = dom(renderFreezeWizard(vm({ preflight: p })));
    expect(root.querySelector(".band-error")?.textContent).toBe(FREEZE.preflightBlocked);
    const items = [...root.querySelectorAll<HTMLElement>(".blockers li")];
    expect(items.map((x) => x.dataset.blocker)).toEqual(["INDEX_SHA"]);
    expect(items[0].textContent).toBe(FREEZE.blockerText.INDEX_SHA);
  });
});

describe("adım 2: kaynak belgeler", () => {
  it("kopyalanan belgeler durumlarıyla listelenir", () => {
    const copied = fx<SourceDocsView>("source_docs_copied.json");
    const root = dom(renderFreezeWizard(vm({ copied, manifest: copied.manifest })));
    expect(root.querySelector(".ok-box")?.textContent).toBe(FREEZE.copyDone(3, "registry/source_docs/SNTA1"));
    const items = [...root.querySelectorAll<HTMLElement>(".copied-docs li")];
    expect(items.map((x) => x.dataset.source)).toEqual(["KAP_TEST_1", "KAP_TEST_2", "SPK_TEST"]);
    expect(items[0].textContent).toContain(FREEZE.docStateText.NEW);
    expect(root.textContent).toContain(FREEZE.manifestDocs(3));
  });

  it("belge yoksa boş hâl ve kapalı kopyala düğmesi", () => {
    const root = dom(renderFreezeWizard(vm()));
    expect(root.querySelector(".empty-state")?.textContent).toBe(FREEZE.noDocs);
    expect(root.querySelector<HTMLButtonElement>("[data-action=copy-docs]")?.disabled).toBe(true);
  });
});

describe("adım 3: girdi belgesi", () => {
  it("dolu alan kaynak ve alıntı ister; boş alan gerekçe ister", () => {
    const root = dom(renderFreezeWizard(vm()));
    const filled = root.querySelector<HTMLElement>('[data-field-row="ipo_price_tl"]');
    expect(filled?.classList.contains("filled")).toBe(true);
    expect(filled?.querySelector('[data-field-key="source_id"]')).not.toBeNull();
    expect(filled?.querySelector('[data-field-key="quote"]')).not.toBeNull();
    expect(filled?.querySelector<HTMLElement>(".value")?.textContent).toBe("25.52");
    const empty = root.querySelector<HTMLElement>('[data-field-row="ipo_size_tl"]');
    expect(empty?.classList.contains("empty")).toBe(true);
    expect(empty?.querySelector('[data-field-key="missing_reason"]')).not.toBeNull();
    // f3 kökeni yalnız dolu f3 satırında
    expect(root.querySelector('[data-field-row="total_demand_multiple"] [data-field-key="origin"]')).not.toBeNull();
    expect(root.querySelector('[data-field-row="ipo_price_tl"] [data-field-key="origin"]')).toBeNull();
  });

  it("var olan dosya: fark gösterilir ve düğme onay ister", () => {
    const preview = fx<InputsDocPreview>("inputs_preview_diff.json");
    expect(preview.exists && !preview.identical).toBe(true);
    const root = dom(renderFreezeWizard(vm({ preview })));
    expect(root.querySelector(".doc-exists")?.textContent).toBe(FREEZE.docExists);
    expect(root.querySelector(".diff")?.textContent).toContain('+      "quote": "belgede: 3.14",');
    expect(root.querySelector("[data-action=write-doc]")?.textContent).toBe(FREEZE.writeConfirm);
  });

  it("yazıldıktan sonra yol ve sha görünür", () => {
    const written: InputsDocPreview = { ...fx<InputsDocPreview>("inputs_preview_diff.json"), written: true, diff: [] };
    const root = dom(renderFreezeWizard(vm({ written })));
    expect(root.querySelector(".doc-written")?.textContent).toBe(
      FREEZE.docWritten(written.rel_path, written.sha256.slice(0, 12)),
    );
  });
});

describe("adım 4 ve 5", () => {
  it("yetkili denetim boş liste → geçti; dolu liste → DUR", () => {
    expect(dom(renderFreezeWizard(vm({ pit: [] }))).querySelector(".pit-ok")?.textContent).toBe(FREEZE.pitOk);
    const bad = dom(renderFreezeWizard(vm({ pit: ["ipo_price_tl: belge dosyası yok"] })));
    expect(bad.querySelector(".pit-fail")?.textContent).toContain("belge dosyası yok");
  });

  it("T ≤ bugün → kırmızı; T boş → sarı", () => {
    const red = fx<Preflight>("preflight_blocked.json");
    expect(red.t_level).toBe("RED");
    const root = dom(renderFreezeWizard(vm({ preflight: red })));
    expect(root.querySelector(".t-red")?.textContent).toBe(FREEZE.tRed(red.t ?? "", red.today_istanbul));
    const yellow = { ...red, t: null, t_level: "YELLOW" as const };
    const y = dom(renderFreezeWizard(vm({ preflight: yellow, values: { first_trading_date: null } })));
    expect(y.querySelector(".t-yellow")?.textContent).toBe(FREEZE.tYellow);
  });

  it("dondur düğmesi yalnız ön koşullar geçti + denetim geçti + onay + belge yazıldı iken açılır", () => {
    const written: InputsDocPreview = { ...fx<InputsDocPreview>("inputs_preview_diff.json"), written: true };
    const preflight = fx<Preflight>("preflight_ok.json");
    expect(preflight.ok).toBe(true);
    const locked = dom(renderFreezeWizard(vm({ preflight, pit: [], acknowledged: false, written })));
    expect(locked.querySelector<HTMLButtonElement>("[data-action=freeze]")?.disabled).toBe(true);
    const ready = dom(renderFreezeWizard(vm({ preflight, pit: [], acknowledged: true, written })));
    expect(ready.querySelector<HTMLButtonElement>("[data-action=freeze]")?.disabled).toBe(false);
  });

  it("B3: ön koşul adımı koşmadıysa ya da ok: false ise dondur düğmesi kapalı (öteki şartlar sağlansa bile)", () => {
    const written: InputsDocPreview = { ...fx<InputsDocPreview>("inputs_preview_diff.json"), written: true };
    const blocked = fx<Preflight>("preflight_blocked.json");
    expect(blocked.ok).toBe(false);
    const cases: [string, Preflight | null][] = [
      ["ön koşul adımı koşmadı", null],
      ["ok: false (INDEX_SHA)", blocked],
      ["ok: false, engelleyici listesi boş olsa bile", { ...fx<Preflight>("preflight_ok.json"), ok: false }],
    ];
    const open = cases
      .filter(([, preflight]) => {
        const root = dom(renderFreezeWizard(vm({ preflight, pit: [], acknowledged: true, written })));
        return root.querySelector<HTMLButtonElement>("[data-action=freeze]")?.disabled !== true;
      })
      .map(([name]) => name);
    expect(open, "dondur düğmesi açık kalan hâller").toEqual([]);
    // komutun ret kodu (Rust sabiti) ekranda Türkçe metinle görünür
    const code = readText("src-tauri/src/commands/freeze.rs").match(/pub const FREEZE_PREFLIGHT_BLOCKED: &str = "([A-Z_]+)";/)?.[1];
    expect(code).toBe("FREEZE_PREFLIGHT_BLOCKED");
    expect(ERROR_TEXT[code ?? ""]).toContain("ön koşullar sağlanmıyor");
  });
});

describe("adım 6: dondur ve 'Şimdi yapılacaklar'", () => {
  const frozen = () => fx<FreezeResult>("freeze_result.json");

  it("U30: kayıt INDEX'teki bütün modelleri içerir (27); parite satırı 27/27 (EK 3 P4 portu sonrası)", () => {
    const f = frozen();
    expect(f.n_models).toBe(27);
    expect(f.parity.n_supported + f.parity.unsupported.length).toBe(f.n_models);
    expect(f.parity.missing_in_record).toEqual([]);
    const root = dom(renderFreezeWizard(vm({ frozen: f })));
    expect(root.querySelector(".record-models")?.textContent).toBe(FREEZE.recordModels(27));
    expect(root.querySelector(".parity-line")?.textContent).toBe(
      FREEZE.parityLine(27, 27, "0", 0, ""),
    );
    expect(root.querySelector(".parity-line")?.textContent).toBe(parityText(f));
    expect(root.textContent).toContain(FREEZE.parityNote);
    expect(root.querySelector(".parity-mismatch")).toBeNull();
  });

  it("uyuşmazlık: kırmızı satır, kayıt yine geçerli, olay dosyası yolu", () => {
    const f = fx<FreezeResult>("freeze_result_mismatch.json");
    expect(f.parity.mismatches.length).toBeGreaterThan(0);
    const root = dom(renderFreezeWizard(vm({ frozen: f })));
    const box = root.querySelector(".parity-mismatch");
    expect(box?.textContent).toContain("PARİTE UYUŞMAZLIĞI");
    expect(box?.textContent).toContain("v1_5_h99");
    expect(box?.textContent).toContain(FREEZE.parityRecordWins);
    expect(box?.textContent).toContain("app/parity/incidents/");
  });

  it("U32: komut bloğu rev-parse ve push_proof içerir, yorum satırı yok, commit yollara sınırlı", () => {
    const f = frozen();
    const root = dom(renderFreezeWizard(vm({ frozen: f })));
    const block = root.querySelector(".todo-block")?.textContent ?? "";
    expect(block).toContain("git rev-parse HEAD");
    expect(block).toContain("-m borsai.push_proof");
    const lines = block.split("\n");
    expect(lines.every((l) => !l.trimStart().startsWith("#"))).toBe(true);
    for (const l of lines.filter((x) => x.startsWith("git commit"))) expect(l).toContain(" -- ");
    // git add ve commit aynı yolları sayar
    const add = lines.find((l) => l.startsWith("git add ") && l.includes("records")) ?? "";
    const commit = lines.find((l) => l.startsWith("git commit") && l.includes("records")) ?? "";
    expect(commit.split(" -- ")[1]).toBe(add.slice("git add ".length));
    // girdi dosyası adı doğru aşamadan
    expect(add).toContain("registry/inputs/SNTA1.json");
    expect(root.textContent).toContain(FREEZE.todoNote);
    expect(root.textContent).toContain(FREEZE.todoNotRun);
  });

  it("uygulama git ve push komutu ÇALIŞTIRMAZ (statik tarama)", () => {
    for (const f of ["src/screens/registry.ts", "src/render/freeze.ts", "src/api.ts"]) {
      const text = readText(f);
      for (const bad of ['invoke("git', "git_commit", "git_push", "push_proof_run"]) {
        expect(text.includes(bad), `${f}: ${bad}`).toBe(false);
      }
    }
  });
});

/** `borsai/tufe.py`'deki `APPEND_COMMAND` (bitişik Python dize sabitleri). */
function pythonAppendCommand(): string {
  const src = readText("../borsai/tufe.py");
  const start = src.indexOf("APPEND_COMMAND = (");
  const body = src.slice(start, src.indexOf(")\n", start));
  return [...body.matchAll(/"([^"]*)"/g)].map((m) => m[1]).join("");
}

describe("U57: TÜFE ayı eksik → TUFE_MONTH engeli ve ekleme komutu (EK 3 §3.4)", () => {
  it("engel metni, eksik ay ve Python'un ekleme komutu birebir; uygulama çalıştırmaz", () => {
    const p = fx<Preflight>("preflight_tufe_month.json");
    expect(p.blockers).toEqual(["TUFE_MONTH"]);
    const root = dom(renderFreezeWizard(vm({ preflight: p })));
    expect(root.querySelector('[data-blocker="TUFE_MONTH"]')?.textContent).toBe(FREEZE.blockerText.TUFE_MONTH);
    const box = root.querySelector(".tufe-missing");
    expect(box?.textContent).toContain(TUFE.missingMonth("2998-11"));
    expect(root.querySelector(".append-command")?.textContent).toBe(pythonAppendCommand().replace("{month}", "2998-11"));
    expect(box?.textContent).toContain(TUFE.commandNote);
  });

  it("geçen ön koşulda TÜFE satırı: ay, endeks, yayım, kaynak, pin (engel yok)", () => {
    const p = fx<Preflight>("preflight_ok.json");
    const root = dom(renderFreezeWizard(vm({ preflight: p })));
    expect(root.querySelector(".tufe-missing")).toBeNull();
    expect(root.querySelector(".tufe-line")?.textContent).toBe(TUFE.line("2026-08", "134.75", "2026-09-03", TUFE.sourceText.REPO, TUFE.pinOk));
  });

  it("TÜFE yayımı T'den önce değilse ya da pin tutmuyorsa sarı bilgi satırı (engel değil)", () => {
    const p = fx<Preflight>("preflight_ok.json");
    const pin = { ...p, tufe: { ...p.tufe!, refusal: "TUFE_FILE_MISMATCH" as const, reason: "PIN_MISMATCH" as const, index: null, pin_ok: false } };
    const root = dom(renderFreezeWizard(vm({ preflight: pin })));
    expect(root.querySelector(".tufe-line.warn-box")?.textContent).toBe(TUFE.pinMismatch);
    expect(root.querySelector(".blockers")).toBeNull();
  });
});
