// Ayarlar ve Hakkında ekranı: `get_config` / `set_config` / `validate_repo` (eski Ayarlar ile aynı) + görünüm seçimi
// (`set_ui_view`; K-UI-1) + `app_info`.
import { open } from "@tauri-apps/plugin-dialog";

import { api } from "../../api";
import { asAppError, renderError } from "../../dom";
import { SADE } from "../../i18n/tr";
import { store } from "../../state";
import type { AppConfig, AppError, ConfigView, RepoCheck } from "../../types";
import type { SadeCtx } from "../ctx";
import { renderAyarlar } from "../render/ayarlar";
import { sade } from "../state";

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  const base = store.config?.config;
  let view: ConfigView | null = store.config;
  const draft: AppConfig = base
    ? { ...base }
    : { schema_version: "borsai.app_config/1", repo_root: null, python_path: null, scores_source: "REPO", ui_view: "SADE" };
  let check: RepoCheck | null = null;
  let msg: string | null = null;
  let error: AppError | null = null;
  const paint = () => {
    main.innerHTML = renderAyarlar({ view, draft, check, info: store.info, msg, errorHtml: error ? `<div class="s-legacy">${renderError(error)}</div>` : "" });
  };
  paint();
  main.oninput = (ev) => {
    const t = ev.target as HTMLInputElement;
    const k = t.dataset.cfg;
    if (k === "repo_root" || k === "python_path") draft[k] = t.value.trim() === "" ? null : t.value;
  };
  main.onchange = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.cfg === "scores_source") draft.scores_source = t.value === "EMBEDDED" ? "EMBEDDED" : "REPO";
    if (t.dataset.action === "ui-view") ctx.switchView(t.value === "AYRINTILI" ? "AYRINTILI" : "SADE");
  };
  main.onclick = async (ev) => {
    const b = (ev.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!b || b.tagName === "INPUT") return;
    msg = null;
    error = null;
    try {
      switch (b.dataset.action) {
        case "pick": {
          const p = await open({ directory: true, multiple: false });
          if (typeof p === "string") draft.repo_root = p;
          break;
        }
        case "suggested":
          draft.repo_root = view?.suggested_repo_root ?? null;
          break;
        case "validate":
          if (draft.repo_root) check = await api.validateRepo(draft.repo_root, draft.python_path);
          break;
        case "save":
        case "clear": {
          if (b.dataset.action === "clear") draft.repo_root = null;
          draft.ui_view = view?.config.ui_view ?? "SADE";
          view = await api.setConfig(draft);
          store.config = view;
          store.form.tickers = [];
          store.hints = await api.scoreHints().catch(() => null);
          // skor ve sicil önbellekleri repo değişince geçersiz
          sade.monitor = null;
          sade.gate = null;
          sade.perf = null;
          sade.arz = null;
          check = null;
          msg = SADE.ayarlar.saved;
          ctx.refreshTop();
          break;
        }
        default:
          return;
      }
    } catch (e) {
      error = asAppError(e);
    }
    paint();
  };
}
