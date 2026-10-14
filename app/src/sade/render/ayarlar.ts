// Ayarlar ve Hakkında (pano `Ayarlar`): `get_config`, `set_config`, `validate_repo`, `set_ui_view` (K-UI-1), `app_info`.
import { esc } from "../../dom";
import { ERROR_TEXT, SADE, SETTINGS } from "../../i18n/tr";
import { sha12 } from "../../render/format";
import type { AppConfig, AppInfo, ConfigView, RepoCheck } from "../../types";

export interface AyarlarVM {
  view: ConfigView | null;
  draft: AppConfig;
  check: RepoCheck | null;
  info: AppInfo | null;
  msg: string | null;
  errorHtml: string;
}

const Y = SADE.ayarlar;

function checks(r: RepoCheck | null): string {
  if (!r) return "";
  const rows = r.checks
    .map((c) => {
      const mark = c.ok ? `<span class="mark-pass">✓</span>` : c.required ? `<span class="mark-fail">×</span>` : `<span class="muted">i</span>`;
      return `<div class="check-row" data-check="${esc(c.id)}">${mark} ${esc(SETTINGS.checkText[c.id] ?? c.id)}</div><div class="mono">${esc(c.detail)}</div>`;
    })
    .join("");
  return `<section class="s-plain checks"><h2 class="s-h2">${esc(Y.checks)}: <span class="${r.ok ? "up" : "down"}">${esc(r.ok ? SETTINGS.modeOn : SETTINGS.modeOff)}</span></h2>` +
    `<div class="s-kv">${rows}</div></section>`;
}

function about(info: AppInfo | null): string {
  if (!info) return "";
  const kv: [string, string][] = [
    [Y.appVersion, esc(info.app_version)],
    [Y.integrity, info.integrity_ok ? `<span class="mark-pass">✓ ${esc(Y.integrityOk)}</span>` : `<span class="mark-fail">× ${esc(Y.integrityBad)}</span>`],
    [Y.preModels, `${info.embedded_models.length} <span class="mono">${esc(sha12(info.index_sha256))}</span>`],
    [Y.postModels, `${info.embedded_post_d1_models.length} <span class="mono">${esc(sha12(info.index_post_d1_sha256))}</span>`],
    [Y.embeddedScores, esc(info.scores_embedded ? Y.yes : Y.no)],
    [Y.embeddedTufe, esc(info.tufe_embedded?.through_month ?? Y.no)],
    [Y.appData, esc(Y.appDataVal)],
  ];
  return `<section class="s-panel about"><div class="s-panel-head"><div><h2>${esc(Y.about)}</h2><div class="s-panel-sub">${esc(Y.aboutSub)}</div></div></div>` +
    `<div class="s-panel-body"><div class="s-kv">${kv.map(([k, v]) => `<div>${esc(k)}</div><div class="num">${v}</div>`).join("")}</div>` +
    `<p><button class="s-link" data-detailed="about">${esc(Y.fullList)}</button></p></div></section>`;
}

export function renderAyarlar(vm: AyarlarVM): string {
  const d = vm.draft;
  const sug = vm.view?.suggested_repo_root;
  const note = vm.view?.config_note ? `<div class="s-legacy"><p class="warn-box">${esc(ERROR_TEXT[vm.view.config_note] ?? vm.view.config_note)}</p></div>` : "";
  const ui = vm.view?.config.ui_view ?? "SADE";
  const radio = (id: "SADE" | "AYRINTILI", label: string, sub: string) =>
    `<label class="view-opt"><input type="radio" name="ui_view" data-action="ui-view" value="${id}"${ui === id ? " checked" : ""}/> ` +
    `<span><strong>${esc(label)}</strong><div class="s-note">${esc(sub)}</div></span></label>`;
  const form = `<section class="s-panel settings-form"><div class="s-panel-body" style="padding-top:18px">` +
    `<label class="s-note">${esc(Y.repo)}</label><div class="s-actions"><input type="text" data-cfg="repo_root" value="${esc(d.repo_root ?? "")}" style="flex:1 1 280px" autocomplete="off"/>` +
    `<button data-action="pick">${esc(Y.pick)}</button></div>` +
    (sug ? `<div class="s-note">${esc(Y.suggested(sug))} <button class="s-link" data-action="suggested">${esc(Y.useSuggested)}</button></div>` : "") +
    `<label class="s-note">${esc(Y.python)}</label><input type="text" data-cfg="python_path" value="${esc(d.python_path ?? "")}" placeholder="${esc(Y.pythonPlaceholder)}" autocomplete="off"/>` +
    `<div class="s-note">${esc(Y.scores)}</div>` +
    `<label><input type="radio" name="scores_source" data-cfg="scores_source" value="REPO"${d.scores_source === "REPO" ? " checked" : ""}/> ${esc(Y.scoresRepo)} <span class="s-id">scores/scores.json</span></label>` +
    `<label><input type="radio" name="scores_source" data-cfg="scores_source" value="EMBEDDED"${d.scores_source === "EMBEDDED" ? " checked" : ""}/> ${esc(Y.scoresEmbedded)}</label>` +
    `<div class="s-actions"><button class="primary" data-action="save">${esc(Y.save)}</button><button data-action="validate">${esc(Y.validate)}</button>` +
    `<button class="s-link down" data-action="clear">${esc(Y.clear)}</button></div>` +
    (vm.msg ? `<p class="s-note mark-pass">${esc(vm.msg)}</p>` : "") + vm.errorHtml + `</div></section>`;
  const view = `<section class="s-panel ui-view"><div class="s-panel-head"><h2>${esc(Y.view)}</h2></div><div class="s-panel-body">` +
    radio("SADE", Y.viewSade, Y.viewSadeSub) + radio("AYRINTILI", Y.viewDetailed, Y.viewDetailedSub) + `</div></section>`;
  const mode = vm.view?.repo_mode
    ? `<p class="s-note"><span class="mark-pass">✓</span> ${esc(Y.repoMode)}: <span class="mono">${esc(vm.view.repo?.repo_root ?? "")}</span></p>`
    : `<p class="s-note">${esc(Y.standalone)}</p>`;
  return `<div class="s-main ayarlar"><div class="s-row"><div class="s-col grow-1"><div><h1 class="s-h1">${esc(Y.title)}</h1><p class="s-lead">${esc(Y.intro)}</p></div>` +
    `${note}${form}${mode}${checks(vm.check ?? vm.view?.repo ?? null)}<p class="s-note">${esc(Y.dataDir)}: <span class="mono">${esc(vm.view?.data_dir ?? SADE.dash)}</span></p></div>` +
    `<div class="s-col grow-1">${view}${about(vm.info)}</div></div></div>`;
}
