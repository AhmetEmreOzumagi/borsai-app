// Kişisel kayıtlar (SPEC_APP §3f): liste, aç, sil, dışa aktar, tümünü dışa aktar.
// Yol bekçisi Rust'tadır (U27): ön uç hedefi yalnız dosya seçiciden alır, kendisi denetlemez.
import { ask, save } from "@tauri-apps/plugin-dialog";

import { api } from "../api";
import { asAppError, esc, renderError } from "../dom";
import { SCENARIOS, STAGES, TR } from "../i18n/tr";
import { sha8 } from "../render/format";
import { resetView, resultsFromScenario, store } from "../state";
import type { AppError, ScenarioSummary } from "../types";
import type { Ctx } from "./ctx";

export function renderScenarioList(list: ScenarioSummary[], error: AppError | null, done: string | null = null): string {
  const head = `<h2>${esc(SCENARIOS.title)}</h2><p class="banner-info">${esc(SCENARIOS.banner)}</p>` +
    (done ? `<p class="ok-box export-done">${esc(done)}</p>` : "");
  if (error) return head + renderError(error);
  const exportAll = `<div class="actions export-all-row"><button data-action="export-all"${list.length ? "" : " disabled"}>` +
    `${esc(SCENARIOS.exportAll)}</button></div>`;
  if (!list.length) return `${head}${exportAll}<p class="muted empty-state">${esc(SCENARIOS.empty)}</p>`;
  const stage = (s: string | null) => STAGES.find((x) => x.id === s)?.label ?? s ?? TR.dash;
  const rows = list.map((s) => {
    const status = s.status === "OK" ? "" : ` <span class="tag">${esc(s.status === "OLD_VERSION" ? SCENARIOS.oldVersion : SCENARIOS.unreadable)}</span>`;
    const open = s.status === "OK" ? `<button data-action="open" data-id="${esc(s.scenario_id)}">${esc(SCENARIOS.open)}</button> ` : "";
    return `<tr data-id="${esc(s.scenario_id)}"><td>${esc(s.title ?? s.scenario_id)}${status}</td><td class="mono small">${esc(s.created_at_local ?? TR.dash)}</td>` +
      `<td class="small">${esc(stage(s.stage))}</td><td class="mono small">${esc(s.app_version ?? TR.dash)}</td>` +
      `<td class="mono small">${esc(sha8(s.models_index_sha256))}</td><td>${esc(s.same_index ? TR.yes : TR.no)}</td>` +
      `<td>${open}<button data-action="export" data-id="${esc(s.scenario_id)}" data-title="${esc(s.title ?? s.scenario_id)}">${esc(SCENARIOS.export)}</button> ` +
      `<button data-action="delete" data-id="${esc(s.scenario_id)}" data-title="${esc(s.title ?? s.scenario_id)}">${esc(SCENARIOS.remove)}</button></td></tr>`;
  });
  return `${head}${exportAll}<table class="grid"><thead><tr><th>${esc(SCENARIOS.colTitle)}</th><th>${esc(SCENARIOS.colCreated)}</th><th>${esc(SCENARIOS.colStage)}</th>` +
    `<th>${esc(SCENARIOS.colVersion)}</th><th>${esc(SCENARIOS.colIndex)}</th><th>${esc(SCENARIOS.colSame)}</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table>` +
    `<p class="small muted">${esc(SCENARIOS.exportNote)}</p>`;
}

export function mount(root: HTMLElement, ctx: Ctx): void {
  let done: string | null = null;
  const load = async (err: AppError | null = null) => {
    try {
      root.innerHTML = renderScenarioList(await api.listScenarios(), err, done);
    } catch (e) {
      root.innerHTML = renderScenarioList([], asAppError(e), done);
    }
  };
  void load();
  root.onclick = async (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    const id = b.dataset.id ?? "";
    if (b.dataset.action === "open") {
      try {
        const l = await api.loadScenario(id);
        store.results = resultsFromScenario(l);
        resetView(l.doc.observed_streak_user?.days ?? []);
        ctx.navigate("results");
      } catch (e) {
        await load(asAppError(e));
      }
    } else if (b.dataset.action === "export") {
      try {
        const target = await save({ title: SCENARIOS.exportTitle, defaultPath: `${b.dataset.title ?? id}.json` });
        if (typeof target === "string") {
          done = SCENARIOS.exportDone(await api.exportScenario(id, target));
          await load();
        }
      } catch (e) {
        done = null;
        await load(asAppError(e));
      }
    } else if (b.dataset.action === "export-all") {
      try {
        const target = await save({ title: SCENARIOS.exportAllTitle, defaultPath: "borsai_kisisel_kayitlar.json" });
        if (typeof target === "string") {
          const r = await api.exportAllScenarios(target);
          done = SCENARIOS.exportAllDone(r.path, r.n_exported, r.n_unreadable);
          await load();
        }
      } catch (e) {
        done = null;
        await load(asAppError(e));
      }
    } else if (b.dataset.action === "delete") {
      if (!(await ask(SCENARIOS.confirmDelete(b.dataset.title ?? id), { kind: "warning" }))) return;
      try {
        await api.deleteScenario(id);
        done = null;
        await load();
      } catch (e) {
        await load(asAppError(e));
      }
    }
  };
}
