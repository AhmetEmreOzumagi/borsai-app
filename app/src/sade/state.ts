// Sade görünümün bellek durumu (yalnız görünüm; kalıcı olan yalnız Rust'ın yazdığı config.json'daki `ui_view`).
import type { SadeScreenId } from "../i18n/tr";
import type { AppError, ConfigView } from "../types";
import type { ArzView, BreakView, HeadlineGate, MonitorView, PerfView } from "./types";

/**
 * Resmi verinin kaynağı (FAZ9_SNAPSHOT K-SNAP-2): repo modu; kişisel modda gömülü sicil anlık görüntüsü; anlık görüntü
 * doğrulanamadı (ekranlar kapalı, fail-closed); ikisi de yok (repo modu gerekli). Karar Rust'ın `ConfigView`'undan.
 */
export type DataSource = "REPO" | "SNAPSHOT" | "FAILED" | "NONE";

export function dataSource(c: ConfigView | null): DataSource {
  if (c?.repo_mode) return "REPO";
  const s = c?.snapshot;
  if (!s || s.status === "NONE") return "NONE";
  return s.status === "FAILED" ? "FAILED" : "SNAPSHOT";
}

export interface SadeState {
  screen: SadeScreenId;
  /** Analiz ekranının arzı (monitör, arama ya da sicilden). */
  ticker: string | null;
  monitor: MonitorView | null;
  monitorError: AppError | null;
  gate: HeadlineGate | null;
  perf: PerfView | null;
  perfError: AppError | null;
  /** Monitörde seçili satır ve süzgeç. */
  selected: string | null;
  filter: "ALL" | "STREAK";
  /** Analiz: görünüm verisi ve hesaplayıcının seçili j'si (null = gözlenen). */
  arz: ArzView | null;
  breakView: BreakView | null;
  arzError: AppError | null;
  arzJ: number | null;
  /** Tahmin sonucu: hesaplayıcının seçili j'si (senaryo; varsayılan 0). */
  sonucJ: number;
  /** Sicil: seçili arz ve sekme. */
  sicilTicker: string | null;
  sicilTab: "PRE" | "BREAK" | "POST";
  sicilRaw: string | null;
  /** Kod arama kutusunun son mesajı. */
  searchMsg: string | null;
}

export const sade: SadeState = {
  screen: "monitor",
  ticker: null,
  monitor: null,
  monitorError: null,
  gate: null,
  perf: null,
  perfError: null,
  selected: null,
  filter: "ALL",
  arz: null,
  breakView: null,
  arzError: null,
  arzJ: null,
  sonucJ: 0,
  sicilTicker: null,
  sicilTab: "PRE",
  sicilRaw: null,
  searchMsg: null,
};

