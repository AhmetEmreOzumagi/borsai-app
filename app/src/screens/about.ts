// Hakkında (SPEC_APP §1.4, §8-2): derleme bilgisi, gömülü model kümesi, bütünlük, repo modu.
import { esc } from "../dom";
import { ABOUT, SETTINGS, TR, TUFE } from "../i18n/tr";
import { store } from "../state";

function row(label: string, value: string): string {
  return `<tr><th>${esc(label)}</th><td class="mono">${esc(value)}</td></tr>`;
}

/** Gömülü TÜFE tablosu satırı (EK 3 §3.1): son ay, derleme ve pin durumu; Rust `TufeStatus`'tan. */
function tufeText(t: import("../types").TufeStatus | null, head: string): string {
  if (!t) return ABOUT.none;
  if (!t.valid) return TUFE.invalid(t.error ?? TR.dash);
  const pin = t.pins.every((p) => p.ok) ? TUFE.pinOk : TUFE.pinBad;
  return `${TUFE.embeddedThrough(t.through_month ?? TR.dash, head.slice(0, 12))} · pin ${pin}`;
}

export function mount(root: HTMLElement): void {
  const info = store.info;
  if (!info) {
    root.innerHTML = `<h2>${esc(ABOUT.title)}</h2><p class="error">${esc(ABOUT.loadFailed)}</p>`;
    return;
  }
  const status = info.build_git_status_models_scores.trim();
  const cfg = store.config;
  root.innerHTML = `<h2>${esc(ABOUT.title)}</h2>` +
    (info.integrity_ok ? "" : `<p class="band-error">${esc(info.integrity_error?.message ?? ABOUT.integrityFailed)}</p>`) +
    `<table class="kv">` +
    row(ABOUT.appVersion, info.app_version) +
    row(ABOUT.buildGitHead, info.build_git_head) +
    row(ABOUT.buildGitStatus, status === "" ? ABOUT.buildGitStatusClean : status) +
    row(ABOUT.indexSha, info.index_sha256) +
    row(ABOUT.embeddedModels, `${info.embedded_models.length}: ${info.embedded_models.join(", ")}`) +
    row(ABOUT.ignoredModels, info.ignored_index_models.length ? info.ignored_index_models.join(", ") : ABOUT.none) +
    row(ABOUT.postD1Models, `${(info.embedded_post_d1_models ?? []).join(", ") || ABOUT.none} · ${ABOUT.postD1Index(info.index_post_d1_sha256 ?? TR.dash)}`) +
    row(ABOUT.scoresEmbedded, info.scores_embedded ? ABOUT.yes : ABOUT.no) +
    row(ABOUT.tufeEmbedded, tufeText(info.tufe_embedded, info.build_git_head)) +
    row(ABOUT.integrity, info.integrity_ok ? ABOUT.integrityOk : `${ABOUT.integrityFailed} · ${info.integrity_error?.message ?? ""}`) +
    row(ABOUT.modelTable, info.models.map((m) => `${m.model_id} · ${m.kind} · ${m.params_sha256.slice(0, 8)}`).join("\n")) +
    row(ABOUT.dataDir, cfg?.data_dir ?? TR.dash) +
    row(ABOUT.repo, cfg?.repo_mode ? `${SETTINGS.modeOn}: ${cfg.repo?.repo_root ?? ""}` : SETTINGS.modeOff) +
    `</table>`;
}
