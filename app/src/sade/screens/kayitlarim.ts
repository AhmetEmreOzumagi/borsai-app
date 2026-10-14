// Kayıtlarım ekranı: eski Kişisel kayıtlar ekranıyla aynı komutlar (`list_scenarios`, `load_scenario`, `export_scenario`,
// `export_all_scenarios`, `delete_scenario`). Yol bekçisi Rust'tadır (U27). Açılan kayıt yeniden hesaplanmaz (U36).
import { ask, save } from "@tauri-apps/plugin-dialog";

import { api } from "../../api";
import { asAppError, renderError } from "../../dom";
import { SCENARIOS } from "../../i18n/tr";
import { openScenarioIntoStore } from "../../state";
import type { AppError } from "../../types";
import type { SadeCtx } from "../ctx";
import { renderKayitlarim } from "../render/kayitlarim";
import { sade } from "../state";

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  let done: string | null = null;
  const load = async (err: AppError | null = null) => {
    try {
      main.innerHTML = renderKayitlarim(await api.listScenarios(), err ? `<div class="s-legacy">${renderError(err)}</div>` : "", done);
    } catch (e) {
      main.innerHTML = renderKayitlarim([], `<div class="s-legacy">${renderError(asAppError(e))}</div>`, done);
    }
  };
  void load();
  main.onclick = async (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    const id = b.dataset.id ?? "";
    try {
      switch (b.dataset.action) {
        case "open": {
          openScenarioIntoStore(await api.loadScenario(id));
          sade.sonucJ = 0;
          ctx.go("sonuc");
          return;
        }
        case "export": {
          const target = await save({ title: SCENARIOS.exportTitle, defaultPath: `${b.dataset.title ?? id}.json` });
          if (typeof target === "string") done = SCENARIOS.exportDone(await api.exportScenario(id, target));
          break;
        }
        case "export-all": {
          const target = await save({ title: SCENARIOS.exportAllTitle, defaultPath: "borsai_kisisel_kayitlar.json" });
          if (typeof target === "string") {
            const r = await api.exportAllScenarios(target);
            done = SCENARIOS.exportAllDone(r.path, r.n_exported, r.n_unreadable);
          }
          break;
        }
        case "delete":
          if (!(await ask(SCENARIOS.confirmDelete(b.dataset.title ?? id), { kind: "warning" }))) return;
          await api.deleteScenario(id);
          done = null;
          break;
        default:
          return;
      }
      await load();
    } catch (e) {
      done = null;
      await load(asAppError(e));
    }
  };
}
