// Sade görünümün yeni Rust komutları (salt okuma; FAZ9_APP_UI K-UI-3). Var olan komutlar `../api`'den aynen kullanılır.
import { invoke } from "@tauri-apps/api/core";

import type { ConfigView, StreakView } from "../types";
import type { ArzView, BreakView, HeadlineGate, MonitorView, PerfView } from "./types";

export const sadeApi = {
  monitorView: () => invoke<MonitorView>("monitor_view"),
  arzView: (ticker: string) => invoke<ArzView>("arz_view", { ticker }),
  // Analiz'in gözlenen serisi veri kökünden (repo ya da kişisel modda gömülü anlık görüntü; FAZ9_SNAPSHOT K-SNAP-2)
  arzStreak: (ticker: string) => invoke<StreakView>("arz_streak", { ticker }),
  breakView: (ticker: string) => invoke<BreakView>("break_view", { ticker }),
  perfView: () => invoke<PerfView>("perf_view"),
  headlineGate: () => invoke<HeadlineGate>("headline_gate"),
  // K-UI-1: yalnız görünüm seçimi kalıcı yazılır
  setUiView: (view: "SADE" | "AYRINTILI") => invoke<ConfigView>("set_ui_view", { view }),
};
