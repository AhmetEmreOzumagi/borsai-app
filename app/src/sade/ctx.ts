import type { SadeScreenId, ScreenId } from "../i18n/tr";
import type { Ctx } from "../screens/ctx";

/** Sade ekranların kabuğa erişimi. `legacy`: sade kabuğun içinde açılan eski ekranların (sihirbaz, kayıt sayfası) bağlamı. */
export interface SadeCtx {
  go: (screen: SadeScreenId) => void;
  openAnalysis: (ticker: string) => void;
  /** Ayrıntılı görünüme geçer (kalıcı; K-UI-1) ve karşılık gelen eski ekranı açar. */
  detailed: (screen: ScreenId) => void;
  /** Görünüm seçimi (Ayarlar). */
  switchView: (view: "SADE" | "AYRINTILI") => void;
  legacy: Ctx;
  refreshTop: () => void;
}
