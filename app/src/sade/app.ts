// Sade görünüm kabuğu (K-UI-1): üst bar, ekran, alt bilgi. Eski ekranlara geçiş `SadeCtx.detailed` ile; sade kabuğun içinde
// açılan eski ekranların (sihirbaz, kayıt sayfası) `navigate` çağrıları sade ekranlara eşlenir.
import { el } from "../dom";
import { SADE, type SadeScreenId, type ScreenId } from "../i18n/tr";
import { clockTr } from "../render/format";
import type { Ctx } from "../screens/ctx";
import { store } from "../state";
import type { SadeCtx } from "./ctx";
import { renderFooter } from "./render/common";
import { renderTopBar } from "./render/shell";
import * as analiz from "./screens/analiz";
import * as ayarlar from "./screens/ayarlar";
import * as giris from "./screens/giris";
import * as kayitlarim from "./screens/kayitlarim";
import * as monitor from "./screens/monitor";
import * as perf from "./screens/perf";
import * as sicil from "./screens/sicil";
import * as sihirbaz from "./screens/sihirbaz";
import * as sonuc from "./screens/sonuc";
import { sade } from "./state";

export interface SadeHost {
  /** Ayrıntılı görünüme geçiş (kalıcı) ve eski ekran. */
  toDetailed: (screen: ScreenId) => void;
  /** Görünüm seçimi (Ayarlar): kalıcı yazılır ve kabuk yeniden çizilir. */
  switchView: (view: "SADE" | "AYRINTILI") => void;
}

let rootEl: HTMLElement | null = null;
let host: SadeHost | null = null;
let clockTimer: number | undefined;

/** Eski ekranın gezinmesi → sade ekran (§3 ekran eşlemesi). */
export function sadeScreenOf(s: ScreenId): SadeScreenId {
  switch (s) {
    case "inputs":
      return "giris";
    case "results":
      return "sonuc";
    case "scenarios":
      return "kayitlarim";
    case "settings":
    case "about":
      return "ayarlar";
    case "accuracy":
      return "perf";
    case "registry":
      return store.registry.mode === "list" ? "sicil" : "sihirbaz";
  }
}

const legacy: Ctx = {
  navigate: (s) => go(sadeScreenOf(s)),
  refreshShell: () => refreshTop(),
};

const ctx: SadeCtx = {
  go: (s) => go(s),
  openAnalysis: (t) => {
    const ticker = t.trim().toLocaleUpperCase("tr");
    if (ticker === "") return;
    if (sade.ticker !== ticker) {
      sade.arzJ = null;
      sade.arz = null;
      sade.breakView = null;
      sade.arzError = null;
    }
    sade.ticker = ticker;
    go("analiz");
  },
  detailed: (s) => host?.toDetailed(s),
  switchView: (v) => host?.switchView(v),
  legacy,
  refreshTop: () => refreshTop(),
};

function topHtml(): string {
  return renderTopBar({
    screen: sade.screen,
    registryMode: store.registry.mode,
    ticker: sade.ticker,
    repoMode: store.config?.repo_mode ?? false,
    repoRoot: store.config?.repo?.repo_root ?? null,
    dataDate: sade.monitor?.data_date ?? null,
    clock: clockTr(new Date()),
    searchMsg: sade.searchMsg,
  });
}

function refreshTop(): void {
  const old = rootEl?.querySelector("header.s-top");
  if (!old) return;
  const holder = el("div");
  holder.innerHTML = topHtml();
  const next = holder.firstElementChild;
  if (next) old.replaceWith(next);
}

function search(q: string): void {
  const t = q.trim().toLocaleUpperCase("tr");
  if (t === "") return;
  const known = sade.monitor?.rows.map((r) => r.ticker) ?? null;
  if (known && !known.includes(t)) {
    sade.searchMsg = SADE.searchNone(t);
    refreshTop();
    return;
  }
  sade.searchMsg = null;
  ctx.openAnalysis(t);
}

function go(s: SadeScreenId): void {
  sade.screen = s;
  render();
  window.scrollTo(0, 0);
}

export function render(): void {
  const root = rootEl;
  if (!root) return;
  root.replaceChildren();
  const wrap = el("div", "sade");
  const main = el("main", "s-screen");
  wrap.innerHTML = topHtml();
  wrap.append(main);
  const footer = el("div");
  footer.innerHTML = renderFooter(store.info?.app_version ?? null);
  wrap.append(...Array.from(footer.childNodes));
  root.append(wrap);
  switch (sade.screen) {
    case "monitor":
      monitor.mount(main, ctx);
      break;
    case "giris":
      giris.mount(main, ctx);
      break;
    case "sonuc":
      sonuc.mount(main, ctx);
      break;
    case "analiz":
      analiz.mount(main, ctx);
      break;
    case "perf":
      perf.mount(main, ctx);
      break;
    case "sicil":
      sicil.mount(main, ctx);
      break;
    case "kayitlarim":
      kayitlarim.mount(main, ctx);
      break;
    case "ayarlar":
      ayarlar.mount(main, ctx);
      break;
    case "sihirbaz":
      sihirbaz.mount(main, ctx);
      break;
  }
}

/** Sade kabuğu #app'e bağlar. Kabuk düzeyi tıklamalar: `data-go` (ekran), `data-detailed` (ayrıntılı görünüm). */
export function mountSade(root: HTMLElement, h: SadeHost, initial: SadeScreenId | null = null): void {
  rootEl = root;
  host = h;
  root.classList.add("sade-root");
  if (initial) sade.screen = initial;
  root.onclick = (ev) => {
    const t = ev.target as HTMLElement;
    const goEl = t.closest<HTMLElement>("[data-go]");
    if (goEl?.dataset.go) {
      ev.preventDefault();
      // K-FIX-1: "Analiz" sekmesi ve "Tüm arzlar" her zaman listeyi açar; arz yalnız `openAnalysis` ile açılır
      if (goEl.dataset.go === "analiz") sade.ticker = null;
      go(goEl.dataset.go as SadeScreenId);
      return;
    }
    const det = t.closest<HTMLElement>("[data-detailed]");
    if (det?.dataset.detailed) {
      ev.preventDefault();
      if (det.dataset.detailed === "registry" && sade.ticker) {
        store.registry.mode = "record";
        store.registry.ticker = sade.ticker;
        store.registry.selected = 0;
        store.registry.view = null;
      }
      host?.toDetailed(det.dataset.detailed as ScreenId);
    }
  };
  root.onkeydown = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (ev.key === "Enter" && t.dataset.role === "search") search(t.value);
  };
  window.clearInterval(clockTimer);
  clockTimer = window.setInterval(() => {
    const c = rootEl?.querySelector(".s-clock");
    if (c) c.textContent = clockTr(new Date());
  }, 30000);
  render();
}

/** Ayrıntılı görünüme geçince sade kabuğun kök sınıfı ve olay işleyicileri kaldırılır. */
export function unmountSade(root: HTMLElement): void {
  root.classList.remove("sade-root");
  root.onclick = null;
  root.onkeydown = null;
  window.clearInterval(clockTimer);
  rootEl = null;
}
