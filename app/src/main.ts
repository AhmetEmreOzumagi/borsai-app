// Kabuk (FAZ9_APP_UI K-UI-1): görünüme göre yönlendirir. SADE (varsayılan): sade kabuk (`sade/app.ts`). AYRINTILI: eski
// arayüz aynen — sol gezinme, mod bandı, repo modu göstergesi ve DISCLAIMER (SPEC_APP §3); gezinmenin sonunda "Sade
// görünüme dön" düğmesi. Seçim config.json'daki `ui_view`'dur (Ayarlar; yoksa SADE).
import "./sade/fonts";
import "./sade/sade.css";

import { api } from "./api";
import { el } from "./dom";
import { DISCLAIMER, NAV, SADE, TR, type ScreenId } from "./i18n/tr";
import { proofLine } from "./render/registry";
import { renderBand, type BandVM } from "./render/shell";
import { mountSade, unmountSade } from "./sade/app";
import { sadeApi } from "./sade/api";
import { loadMonitor } from "./sade/screens/monitor";
import * as about from "./screens/about";
import * as accuracy from "./screens/accuracy";
import type { Ctx } from "./screens/ctx";
import * as inputs from "./screens/inputs";
import * as registry from "./screens/registry";
import * as results from "./screens/results";
import * as scenarios from "./screens/scenarios";
import * as settings from "./screens/settings";
import { store } from "./state";

let current: ScreenId = "inputs";
let rootEl: HTMLElement | null = null;

/** Bant girdisi: hangi ekrandayız ve sicil ekranının hangi hâlindeyiz (§3 tablosu). */
function bandVM(): BandVM {
  const s = store.registry;
  const t = s.view?.tickers.find((x) => x.ticker === s.ticker);
  const r = t?.records[s.selected] ?? null;
  return {
    screen: current,
    registryMode: s.mode,
    recordFile: r?.file ?? null,
    // Zaman kanıtı dizesi arz sayfasındaki göstergeyle aynı kaynaktan; yeni hesap yok.
    recordProof: r === null ? null : proofLine(r),
    ticker: s.ticker,
    repoMode: store.config?.repo_mode ?? false,
    repoRoot: store.config?.repo?.repo_root ?? null,
  };
}

function band(): HTMLElement {
  const holder = el("div");
  holder.innerHTML = renderBand(bandVM());
  return holder.firstElementChild as HTMLElement;
}

const ctx: Ctx = {
  navigate: (s) => {
    current = s;
    render();
  },
  refreshShell: () => {
    const old = rootEl?.querySelector("header.mode-band");
    if (old) old.replaceWith(band());
  },
};

/** Eski ekran görüntüsü koşusu (scripts/screens*.sh; yalnız geliştirme) eski arayüzü sürer: o koşuda görünüm ayrıntılıdır. */
const legacyDemo = import.meta.env.DEV && import.meta.env.VITE_BORSAI_DEMO === "1" && import.meta.env.VITE_BORSAI_DEMO_V2 !== "1";

function isSade(): boolean {
  if (legacyDemo) return false;
  return (store.config?.config.ui_view ?? "SADE") !== "AYRINTILI";
}

/** Görünüm seçimini kalıcı yazar (set_ui_view); yazılamazsa (ör. uygulama verisi yok) yalnız bu oturumda geçerli olur. */
async function setView(view: "SADE" | "AYRINTILI"): Promise<void> {
  try {
    store.config = await sadeApi.setUiView(view);
  } catch {
    if (store.config) store.config = { ...store.config, config: { ...store.config.config, ui_view: view } };
  }
}

const sadeHost = {
  toDetailed: (screen: ScreenId) => {
    current = screen;
    void setView("AYRINTILI").then(render);
  },
  switchView: (view: "SADE" | "AYRINTILI") => {
    if (view === "AYRINTILI") current = "settings";
    void setView(view).then(render);
  },
};

function renderDetailed(root: HTMLElement): void {
  root.replaceChildren();
  const nav = el("nav", "sidebar");
  nav.append(el("div", "brand", TR.appName));
  for (const item of NAV) {
    const b = el("button", item.id === current ? "nav-item active" : "nav-item", item.label);
    b.dataset.nav = item.id;
    b.addEventListener("click", () => ctx.navigate(item.id));
    nav.append(b);
  }
  const back = el("button", "nav-item sade-back", SADE.backToSade);
  back.dataset.nav = "sade";
  back.addEventListener("click", () => void setView("SADE").then(render));
  nav.append(back);
  const main = el("main", "content");
  switch (current) {
    case "inputs":
      inputs.mount(main, ctx);
      break;
    case "results":
      results.mount(main, ctx);
      break;
    case "scenarios":
      scenarios.mount(main, ctx);
      break;
    case "settings":
      settings.mount(main, ctx);
      break;
    case "about":
      about.mount(main);
      break;
    case "accuracy":
      accuracy.mount(main);
      break;
    case "registry":
      registry.mount(main, ctx);
      break;
  }
  const body = el("div", "layout");
  body.append(nav, main);
  root.append(band(), body, el("footer", "disclaimer", DISCLAIMER));
}

function render(): void {
  const root = rootEl;
  if (!root) return;
  if (isSade()) {
    mountSade(root, sadeHost);
    return;
  }
  unmountSade(root);
  renderDetailed(root);
}

window.addEventListener("DOMContentLoaded", async () => {
  rootEl = document.querySelector<HTMLElement>("#app");
  if (!rootEl) return;
  rootEl.textContent = TR.loading;
  const [info, config, hints] = await Promise.all([
    api.appInfo().catch(() => null),
    api.getConfig().catch(() => null),
    api.scoreHints().catch(() => null),
  ]);
  store.info = info;
  store.config = config;
  store.hints = hints;
  // Sade kabuğun veri tarihi (üst bar) monitör görünümünden; repo modunda açılışta bir kez okunur.
  if (isSade() && config?.repo_mode) await loadMonitor();
  render();
  if (import.meta.env.DEV && import.meta.env.VITE_BORSAI_DEMO === "1") {
    const { runDemo } = await import("./dev/demo");
    await runDemo();
  }
});
