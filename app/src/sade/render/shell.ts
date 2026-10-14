// Sade kabuk (üst bar). Mod göstergesi eski mod bandıyla AYNI kaynaktan: `render/shell.ts` `bandFor` (K-UI-12); metinler
// TR.modeScenario vb. aynen, yalnız gösterim (CSS) cümle düzenindedir.
import { esc } from "../../dom";
import { SADE, SADE_NAV, TR, type SadeScreenId, type ScreenId } from "../../i18n/tr";
import { dateTr } from "../../render/format";
import { bandFor, bandText, type BandVM, type RegistryMode } from "../../render/shell";

export interface TopBarVM {
  screen: SadeScreenId;
  registryMode: RegistryMode;
  ticker: string | null;
  repoMode: boolean;
  repoRoot: string | null;
  dataDate: string | null;
  clock: string;
  searchMsg: string | null;
}

/** Sade ekran → eski ekran kimliği (mod bandı tablosu §3; ekran başına tek kaynak). */
export function legacyScreenOf(s: SadeScreenId): ScreenId {
  switch (s) {
    case "giris":
      return "inputs";
    case "sonuc":
      return "results";
    case "kayitlarim":
      return "scenarios";
    case "perf":
      return "accuracy";
    case "analiz":
    case "sicil":
    case "sihirbaz":
      return "registry";
    case "monitor":
    case "ayarlar":
      return "settings";
  }
}

/** Sekme vurgusu: giriş, sonuç ve ayarlar sekme değildir; sihirbaz sicilin altındadır. */
export function activeTab(s: SadeScreenId): string | null {
  if (s === "sihirbaz") return "sicil";
  return SADE_NAV.some((n) => n.id === s) ? s : null;
}

export function bandOf(v: TopBarVM): ReturnType<typeof bandFor> {
  const mode: RegistryMode = v.screen === "sihirbaz" ? v.registryMode : "list";
  const vm: BandVM = {
    screen: legacyScreenOf(v.screen),
    registryMode: mode,
    recordFile: null,
    recordProof: null,
    ticker: v.ticker,
    repoMode: v.repoMode,
    repoRoot: v.repoRoot,
  };
  return bandFor(vm);
}

const GEAR =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"></path></svg>';

export function renderTopBar(v: TopBarVM): string {
  const tab = activeTab(v.screen);
  const nav = SADE_NAV.map((n) => `<button data-go="${n.id}" class="${n.id === tab ? "active" : ""}">${esc(n.label)}</button>`).join("");
  const b = bandOf(v);
  const pill = b.head === "" ? "" : `<span class="s-mode ${esc(b.cls)}" data-band="${esc(b.cls)}" title="${esc(bandText(b))}">${esc(b.head)}</span>`;
  const standalone = v.repoMode ? "" : `<span class="s-standalone" title="${esc(TR.standaloneMode)}">${esc(SADE.ayarlar.standalone)}</span>`;
  const date = v.dataDate ? `<span>${esc(SADE.dataDate(dateTr(v.dataDate)))}</span>` : "";
  const msg = v.searchMsg ? `<span class="s-note search-msg">${esc(v.searchMsg)}</span>` : "";
  return `<header class="s-top"><span class="s-brand">${esc(SADE.brand)}</span><nav class="s-nav" aria-label="${esc(SADE.brand)}">${nav}</nav>` +
    `<div class="s-search-wrap"><input type="search" class="s-search" data-role="search" placeholder="${esc(SADE.search)}" aria-label="${esc(SADE.search)}" autocomplete="off"/>${msg}</div>` +
    `${pill}${standalone}<div class="s-meta">${date}<strong class="s-clock">${esc(v.clock)}</strong></div>` +
    `<button class="primary" data-go="giris">${esc(SADE.newIpo)}</button>` +
    `<button class="s-gear" data-go="ayarlar" aria-label="${esc(SADE.settings)}" title="${esc(SADE.settings)}">${GEAR}</button></header>`;
}
