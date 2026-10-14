import type { ScreenId } from "../i18n/tr";

/** Ekranların kabuğa erişimi: gezinme ve mod bandını yenileme. */
export interface Ctx {
  navigate: (screen: ScreenId) => void;
  refreshShell: () => void;
}
