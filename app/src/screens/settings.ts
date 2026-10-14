// Ayarlar (SPEC_APP §6 "Uygulama verisi"): repo_root, python_path, scores_source; repo doğrulaması.
import { open } from "@tauri-apps/plugin-dialog";

import { api } from "../api";
import { asAppError, esc, renderError } from "../dom";
import { ERROR_TEXT, SETTINGS, TR } from "../i18n/tr";
import { store } from "../state";
import type { AppConfig, AppError, ConfigView, RepoCheck } from "../types";
import type { Ctx } from "./ctx";

export function renderChecks(r: RepoCheck | null): string {
  if (!r) return "";
  const rows = r.checks.map((c) => {
    const state = c.ok ? SETTINGS.ok : c.required ? SETTINGS.fail : SETTINGS.info;
    return `<tr class="${c.ok ? "ok" : c.required ? "fail" : "info"}" data-check="${esc(c.id)}"><th>${esc(SETTINGS.checkText[c.id] ?? c.id)}</th>` +
      `<td>${esc(state)}</td><td class="mono small">${esc(c.detail)}</td></tr>`;
  });
  const m = r.market20_sources;
  const m20 = m
    ? `<p class="small">${esc(SETTINGS.xu100Last)}: <span class="mono">${esc(m.xu100_last ?? TR.dash)}</span> · ${esc(SETTINGS.calendarLast)}: <span class="mono">${esc(m.calendar_last ?? TR.dash)}</span></p>`
    : "";
  return `<h3>${esc(SETTINGS.checks)}: <span class="${r.ok ? "ok-text" : "fail-text"}">${esc(r.ok ? SETTINGS.modeOn : SETTINGS.modeOff)}</span></h3>` +
    `<table class="kv checks">${rows.join("")}</table>${m20}`;
}

interface SettingsVM {
  view: ConfigView | null;
  draft: AppConfig;
  check: RepoCheck | null;
  msg: string | null;
  error: AppError | null;
}

export function renderSettings(v: SettingsVM): string {
  const d = v.draft;
  const sug = v.view?.suggested_repo_root;
  const note = v.view?.config_note ? `<p class="warn-box">${esc(ERROR_TEXT[v.view.config_note] ?? v.view.config_note)}</p>` : "";
  return `<h2>${esc(SETTINGS.title)}</h2>${note}` +
    `<div class="settings-form"><label>${esc(SETTINGS.repoRoot)}<br/><input type="text" data-cfg="repo_root" value="${esc(d.repo_root ?? "")}" size="70" autocomplete="off"/></label> ` +
    `<button data-action="pick">${esc(SETTINGS.pick)}</button>` +
    (sug ? `<div class="small muted">${esc(SETTINGS.useSuggested(sug))} <button class="link" data-action="suggested">${esc(SETTINGS.useSuggestedButton)}</button></div>` : "") +
    `<label>${esc(SETTINGS.python)}<br/><input type="text" data-cfg="python_path" value="${esc(d.python_path ?? "")}" size="70" autocomplete="off"/></label>` +
    `<label>${esc(SETTINGS.scoresSource)}<br/><select data-cfg="scores_source">` +
    `<option value="REPO"${d.scores_source === "REPO" ? " selected" : ""}>${esc(SETTINGS.scoresRepo)}</option>` +
    `<option value="EMBEDDED"${d.scores_source === "EMBEDDED" ? " selected" : ""}>${esc(SETTINGS.scoresEmbedded)}</option></select></label>` +
    `<div class="actions"><button data-action="validate">${esc(SETTINGS.validate)}</button> <button class="primary" data-action="save">${esc(SETTINGS.save)}</button> ` +
    `<button data-action="clear">${esc(SETTINGS.clearRepo)}</button></div></div>` +
    (v.msg ? `<p class="ok-box">${esc(v.msg)}</p>` : "") + (v.error ? renderError(v.error) : "") +
    renderChecks(v.check ?? v.view?.repo ?? null) +
    `<p class="small muted">${esc(SETTINGS.dataDir)}: <span class="mono">${esc(v.view?.data_dir ?? TR.dash)}</span></p>`;
}

export function mount(root: HTMLElement, ctx: Ctx): void {
  const base = store.config?.config;
  const vm: SettingsVM = {
    view: store.config,
    draft: base ? { ...base } : { schema_version: "borsai.app_config/1", repo_root: null, python_path: null, scores_source: "REPO" },
    check: null,
    msg: null,
    error: null,
  };
  const paint = () => {
    root.innerHTML = renderSettings(vm);
  };
  paint();
  root.oninput = (ev) => {
    const t = ev.target as HTMLInputElement;
    const k = t.dataset.cfg;
    if (k === "repo_root" || k === "python_path") vm.draft[k] = t.value.trim() === "" ? null : t.value;
  };
  root.onchange = (ev) => {
    const t = ev.target as HTMLSelectElement;
    if (t.dataset.cfg === "scores_source") vm.draft.scores_source = t.value === "EMBEDDED" ? "EMBEDDED" : "REPO";
  };
  root.onclick = async (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b) return;
    vm.msg = null;
    vm.error = null;
    try {
      switch (b.dataset.action) {
        case "pick": {
          const p = await open({ directory: true, multiple: false });
          if (typeof p === "string") vm.draft.repo_root = p;
          break;
        }
        case "suggested":
          vm.draft.repo_root = vm.view?.suggested_repo_root ?? null;
          break;
        case "validate":
          if (vm.draft.repo_root) vm.check = await api.validateRepo(vm.draft.repo_root, vm.draft.python_path);
          break;
        case "save":
        case "clear": {
          if (b.dataset.action === "clear") vm.draft.repo_root = null;
          vm.view = await api.setConfig(vm.draft);
          store.config = vm.view;
          store.form.tickers = [];
          store.hints = await api.scoreHints().catch(() => null);
          vm.check = null;
          vm.msg = SETTINGS.saved;
          ctx.refreshShell();
          break;
        }
      }
    } catch (e) {
      vm.error = asAppError(e);
    }
    paint();
  };
}
