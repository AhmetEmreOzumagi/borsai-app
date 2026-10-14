// Sihirbaz kabuğu (K-UI-11): dondur ve D1 sonrası sihirbazları ile ayrıntılı kayıt sayfası (iptal) eski ekranın
// kendisidir (`screens/registry.ts` aynen; mantık, komutlar ve metinler değişmez). Sade kabukta, `.s-legacy` kökü altında
// sade CSS'le gösterilir; üstte yalnız adım listesi ve "Akılda tut" paneli eklenir (eski render dosyaları değişmez).
import { esc } from "../../dom";
import { FREEZE, POST_D1, SADE } from "../../i18n/tr";
import { mount as mountRegistry } from "../../screens/registry";
import { store } from "../../state";
import type { SadeCtx } from "../ctx";

export function renderWizardFrame(mode: string): string {
  const W = SADE.wizard;
  const steps = mode === "wizard" ? FREEZE.steps : mode === "post_d1" ? POST_D1.steps : [];
  const crumb = mode === "wizard" ? W.freezeCrumb : mode === "post_d1" ? W.postD1Crumb : W.recordCrumb;
  const list = steps.length
    ? `<div class="s-steps" data-steps="${steps.length}">${steps.map((s, i) => `<div class="s-step"><span class="n">${i + 1}</span>${esc(s)}</div>`).join("")}</div>`
    : "";
  const keep = mode === "wizard"
    ? `<section class="s-panel side keep"><div class="s-panel-head"><h2>${esc(W.keepInMind)}</h2></div><div class="s-panel-body">` +
      `<p class="s-note">${esc(W.keep1)}</p><p class="s-note">${esc(W.keep2)}</p><p class="s-note">${esc(W.keep3)}</p></div></section>`
    : "";
  return `<div class="s-main sihirbaz" data-mode="${esc(mode)}"><div class="s-head-row"><div class="s-crumb"><button class="s-link" data-go="sicil">${esc(W.back)}</button> · ${esc(crumb)}</div></div>` +
    `${list}<div class="s-row"><div class="s-legacy grow-2" data-role="legacy-root"></div>${keep}</div></div>`;
}

export function mount(main: HTMLElement, ctx: SadeCtx): void {
  main.innerHTML = renderWizardFrame(store.registry.mode);
  const root = main.querySelector<HTMLElement>("[data-role=legacy-root]");
  if (!root) return;
  mountRegistry(root, ctx.legacy);
  // Eski ekran kendi içinde listeye dönerse (ör. "Sicile dön") sade Sicil'e geçilir.
  main.addEventListener("click", () => {
    queueMicrotask(() => {
      if (store.registry.mode === "list") ctx.go("sicil");
    });
  });
}
