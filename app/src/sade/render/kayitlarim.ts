// Kayıtlarım (pano `Kayitlarim`): gerçek kişisel kayıtlar (`list_scenarios`). Örnek satır yok (README §5).
import { esc } from "../../dom";
import { SADE } from "../../i18n/tr";
import { dateTr } from "../../render/format";
import type { ScenarioSummary } from "../../types";
import { stageLabel } from "./sonuc";

const K = SADE.kayitlarim;

export function renderKayitlarim(list: ScenarioSummary[], errorHtml: string, done: string | null): string {
  const head = `<div class="s-head-row"><div><h1 class="s-h1">${esc(K.title)}</h1><p class="s-lead">${esc(K.intro)}</p></div>` +
    `<button data-action="export-all"${list.length ? "" : " disabled"}>${esc(K.exportAll)}</button></div>` +
    (done ? `<p class="s-note mark-pass export-done">${esc(done)}</p>` : "") + errorHtml;
  if (!list.length) {
    return `<div class="s-main kayitlarim">${head}<section class="s-panel s-empty"><h2>${esc(K.emptyTitle)}</h2><p>${esc(K.emptyText)}</p>` +
      `<button class="primary" data-go="giris">${esc(SADE.newIpo)}</button></section></div>`;
  }
  const rows = list
    .map((s) => {
      const set = s.same_index ? `<span class="mark-pass">✓ ${esc(K.sameSet)}</span>` : `<span class="mark-approx">${esc(K.oldSet)}</span>`;
      const open = s.status === "OK" ? `<button class="s-link" data-action="open" data-id="${esc(s.scenario_id)}">${esc(K.open)}</button>` : "";
      return `<tr data-id="${esc(s.scenario_id)}"><td><strong>${esc(s.title ?? s.scenario_id)}</strong></td><td class="num">${esc(dateTr(s.created_at_local))}</td>` +
        `<td>${esc(stageLabel(s.stage))}</td><td>${set}</td><td class="s-actions">${open}` +
        `<button class="s-link" data-action="export" data-id="${esc(s.scenario_id)}" data-title="${esc(s.title ?? s.scenario_id)}">${esc(K.export)}</button>` +
        `<button class="s-link down" data-action="delete" data-id="${esc(s.scenario_id)}" data-title="${esc(s.title ?? s.scenario_id)}">${esc(K.remove)}</button></td></tr>`;
    })
    .join("");
  return `<div class="s-main kayitlarim">${head}<section class="s-panel"><table class="s-table"><thead><tr><th>${esc(K.colTitle)}</th><th class="num">${esc(K.colCreated)}</th>` +
    `<th>${esc(K.colStage)}</th><th>${esc(K.colSet)}</th><th>${esc(K.colActions)}</th></tr></thead><tbody>${rows}</tbody></table></section>` +
    `<p class="s-note">${esc(K.note)}</p></div>`;
}
