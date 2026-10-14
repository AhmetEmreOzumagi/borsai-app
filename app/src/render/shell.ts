// Mod bandı (SPEC_APP §3 genel çerçeve): ekran ve ekran içi hâl başına tek SAF fonksiyon.
// `main.ts` yalnız çağırır; ekranlar kendi bandını yazmaz. Bantta hiçbir değer hesaplanmaz:
// arz sayfasındaki zaman kanıtı dizesi sayfadaki göstergenin ta kendisidir (aynı `proofLine`).
import { esc } from "../dom";
import { TR, type ScreenId } from "../i18n/tr";

/** Sicil ekranının içinde bulunulan hâl (`store.registry.mode`). */
export type RegistryMode = "list" | "record" | "wizard" | "post_d1";

export interface BandVM {
  screen: ScreenId;
  registryMode: RegistryMode;
  /** Arz sayfasında seçili kaydın dosya adı; kayıt yoksa null. */
  recordFile: string | null;
  /** Arz sayfasındaki push kanıtı göstergesiyle AYNI dize (render/registry.ts `proofLine`). */
  recordProof: string | null;
  /** Arz sayfasının arzı (kayıt yokken banttaki tanıtıcı). */
  ticker: string | null;
  repoMode: boolean;
  repoRoot: string | null;
}

export interface Band {
  /** `mode-scenario` | `mode-official` | `mode-neutral` */
  cls: string;
  /** Kalın mod sözcüğü; Ayarlar ve Hakkında'da boştur (mod sözcüğü yok). */
  head: string;
  /** Mod sözcüğünden sonraki açıklama; boş olabilir. */
  note: string;
}

const SCENARIO_SCREENS: ScreenId[] = ["inputs", "results", "scenarios"];

function registryBand(v: BandVM): Band {
  const head = TR.modeOfficial;
  if (v.registryMode === "wizard") return { cls: "mode-official", head, note: TR.modeOfficialWizard };
  if (v.registryMode === "post_d1") return { cls: "mode-official", head, note: TR.modeOfficialPostD1(v.ticker ?? TR.dash) };
  if (v.registryMode === "record") {
    const note =
      v.recordFile === null
        ? `${v.ticker ?? TR.dash} · ${TR.modeOfficialNoRecord}`
        : `${v.recordFile} · ${v.recordProof ?? TR.dash}`;
    return { cls: "mode-official", head, note };
  }
  return { cls: "mode-official", head, note: TR.modeOfficialList };
}

/** Tablonun tamamı (§3): ekran + hâl → sınıf ve metin. Başka hiçbir yerde bant üretilmez. */
export function bandFor(v: BandVM): Band {
  if (SCENARIO_SCREENS.includes(v.screen)) {
    return { cls: "mode-scenario", head: TR.modeScenario, note: TR.modeScenarioNote };
  }
  if (v.screen === "registry") return registryBand(v);
  if (v.screen === "accuracy") return { cls: "mode-neutral", head: TR.modeAccuracy, note: TR.modeAccuracyNote };
  return { cls: "mode-neutral", head: "", note: "" };
}

/** Banttaki tam metin (sınama ve ekran görüntüsü karşılaştırması için). */
export function bandText(b: Band): string {
  return [b.head, b.note].filter((x) => x !== "").join(" · ");
}

/** Sağdaki repo modu göstergesi her bantta aynen kalır. */
export function renderBand(v: BandVM): string {
  const b = bandFor(v);
  const repo = v.repoMode && v.repoRoot !== null ? TR.repoMode(v.repoRoot) : TR.standaloneMode;
  return `<header class="mode-band ${esc(b.cls)}">` +
    (b.head === "" ? "" : `<strong>${esc(b.head)}</strong>`) +
    (b.note === "" ? "" : `<span>${b.head === "" ? "" : " · "}${esc(b.note)}</span>`) +
    `<span class="${v.repoMode ? "repo-mode repo-on" : "repo-mode"}">${esc(repo)}</span></header>`;
}
