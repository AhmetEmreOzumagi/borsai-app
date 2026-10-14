// Küçük DOM yardımcıları. Bütün metin HTML'e `esc` ile girer.
import { ERROR_DETAIL, ERROR_TEXT, ERROR_UNKNOWN } from "./i18n/tr";
import type { AppError } from "./types";

const ENTITIES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const SPECIAL = new RegExp("[&<>\"']", "g");

export function esc(s: string | number | null | undefined): string {
  return String(s ?? "").replace(SPECIAL, (c) => ENTITIES[c] ?? c);
}

export function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Tauri `invoke` reddi: `AppError` ya da düz metin. */
export function asAppError(e: unknown): AppError {
  if (e && typeof e === "object" && "code" in e) return e as AppError;
  return { code: "UNKNOWN", message: String(e) };
}

/** Hata sınıfı (§3): Türkçe metin + kod; ham çıktı açılır kutuda. */
export function renderError(e: AppError): string {
  const text = ERROR_TEXT[e.code] ?? ERROR_UNKNOWN;
  const detail = e.detail ?? e.message;
  return `<div class="error-box" data-code="${esc(e.code)}"><strong>${esc(text)}</strong> <span class="mono">${esc(e.code)}</span>` +
    (detail ? `<details><summary>${esc(ERROR_DETAIL)}</summary><pre class="mono">${esc(detail)}</pre></details>` : "") +
    `</div>`;
}
