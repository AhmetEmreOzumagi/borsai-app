// @vitest-environment jsdom
// Sade ekranların Rust komut çağrıları (sahte `invoke`; gerçek `mount` ve gerçek tıklamalar). Beklenen: hesaplayıcı yalnız
// var olan komutları çağırır (K-UI-8: senaryoda ceiling_display / ceiling_summary(runs, j, null, t); resmi görünümde
// record_summary(T, file, j, jObserved) ve record_ceiling; jObserved arz_streak'ten); resmi görünümde predict_all hiç
// çağrılmaz (U38); hiçbir argümanda beyan alanı yok (U52); kişisel kayıt isteğinde beyan alanı boş. Kişisel modda
// gömülü sicil anlık görüntüsü varken Monitör, Analiz ve Sicil aynı komutları çağırır (FAZ9_SNAPSHOT K-SNAP-2).
import { beforeEach, describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({
  calls: [] as { cmd: string; args: Record<string, unknown> }[],
  respond: (_cmd: string, _args: Record<string, unknown>): unknown => null,
}));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string, args: Record<string, unknown> = {}) => {
    h.calls.push({ cmd, args: structuredClone(args) });
    return h.respond(cmd, args);
  }),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn(async () => null), save: vi.fn(async () => null), ask: vi.fn(async () => true) }));

import { mountSade } from "../src/sade/app";
import { sade } from "../src/sade/state";
import { store } from "../src/state";
import { SADE } from "../src/i18n/tr";
import { dateTr } from "../src/render/format";
import type { ConfigView, ModelRun, SnapshotInfo } from "../src/types";
import { fx } from "./helpers";

function config(ui: "SADE" | "AYRINTILI" = "SADE"): ConfigView {
  return {
    config: { schema_version: "borsai.app_config/1", repo_root: "/r", python_path: null, scores_source: "REPO", ui_view: ui },
    config_note: null,
    repo: { repo_root: "/r", python_path: "/r/.venv/bin/python", ok: true, checks: [], git_head: "x", market20_sources: null },
    repo_mode: true,
    data_dir: "/d",
    suggested_repo_root: null,
  };
}

function respond(cmd: string, args: Record<string, unknown>): unknown {
  switch (cmd) {
    case "monitor_view":
      return fx("sade_monitor.json");
    case "headline_gate":
      return fx("sade_gate.json");
    case "perf_view":
      return fx("sade_perf.json");
    case "arz_view":
      return fx("sade_arz_netgl.json"); // her arz için NETGL fixture'ı; BKRGY'de ekran ad uyuşmazlığıyla "yükleniyor"da kalır
    case "break_view":
      return fx("sade_break_netgl.json");
    case "streak_view":
    case "arz_streak":
      return fx("sade_streak_netgl.json");
    case "record_summary":
      return fx(args.j === 0 ? "sade_record_summary_netgl_j0.json" : "sade_record_summary_netgl_j3.json");
    case "record_ceiling":
      return fx(args.j === 0 ? "sade_record_ceiling_netgl_j0.json" : "sade_record_ceiling_netgl_j3.json");
    case "ceiling_display":
      return fx(args.j === 0 ? "sade_ceiling_netgl_j0.json" : "sade_ceiling_netgl_j3.json");
    case "ceiling_summary":
      return fx("sade_summary_netgl_j0.json");
    case "registry_view":
      return fx("registry_synthetic.json");
    case "post_d1_records":
      return [];
    case "list_scenarios":
      return [];
    case "save_scenario":
      return { scenario_id: "01KX", status: "OK" };
    case "set_ui_view":
      return config(args.view as "SADE" | "AYRINTILI");
    default:
      throw new Error(`beklenmeyen komut: ${cmd}`);
  }
}

const DECL = ["declared", "declDropped", "observed_streak_user", "userDays"];

function keysDeep(v: unknown): string[] {
  if (Array.isArray(v)) return v.flatMap(keysDeep);
  if (v && typeof v === "object") return Object.entries(v as Record<string, unknown>).flatMap(([k, x]) => [k, ...keysDeep(x)]);
  return [];
}

async function settle(): Promise<void> {
  for (let i = 0; i < 40; i += 1) await new Promise((r) => setTimeout(r, 0));
}

const of = (cmd: string) => h.calls.filter((c) => c.cmd === cmd);

function host() {
  return { toDetailed: vi.fn(), switchView: vi.fn() };
}

let root: HTMLElement;

beforeEach(() => {
  h.calls.length = 0;
  h.respond = respond;
  document.body.innerHTML = '<div id="app"></div>';
  root = document.querySelector<HTMLElement>("#app") as HTMLElement;
  store.config = config();
  store.info = null;
  store.results = null;
  Object.assign(sade, { screen: "monitor", ticker: null, monitor: null, monitorError: null, gate: null, perf: null, arz: null, breakView: null, arzJ: null, sonucJ: 0, arzError: null, sicilTicker: null, sicilTab: "PRE", sicilRaw: null });
});

describe("sade ekranların komut çağrıları", () => {
  it("Monitör: monitor_view + headline_gate + perf_view; kod araması Analiz'i açar", async () => {
    mountSade(root, host(), "monitor");
    await settle();
    expect(of("monitor_view").length).toBe(1);
    expect(of("headline_gate").length).toBe(1);
    expect(of("perf_view").length).toBe(1);
    expect(root.querySelectorAll("tr[data-ticker]").length).toBe(7);
    const search = root.querySelector<HTMLInputElement>("[data-role=search]") as HTMLInputElement;
    search.value = "netgl";
    search.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await settle();
    expect(sade.screen).toBe("analiz");
    expect(of("arz_view")[0]?.args).toEqual({ ticker: "NETGL" });
  });

  it("Analiz (resmi): j varsayılanı gözlenen j = 3; record_summary jObserved = 3; j seçimi ve 'Gözlenene dön'; predict_all yok", async () => {
    sade.ticker = "NETGL";
    mountSade(root, host(), "analiz");
    await settle();
    expect(of("arz_streak")[0]?.args).toEqual({ ticker: "NETGL" });
    expect(of("streak_view").length).toBe(0);
    const file = "20260922T121936Z_65a39d7392dd.json";
    expect(of("record_summary")[0]?.args).toEqual({ ticker: "NETGL", file, j: 3, jObserved: 3 });
    expect(of("record_ceiling")[0]?.args).toEqual({ ticker: "NETGL", file, j: 3 });
    root.querySelector<HTMLElement>('[data-action="calc-j"][data-j="0"]')?.click();
    await settle();
    expect(of("record_summary").at(-1)?.args).toEqual({ ticker: "NETGL", file, j: 0, jObserved: 3 });
    expect(root.querySelector('.calc[data-j="0"]')).not.toBeNull();
    root.querySelector<HTMLElement>('[data-action="calc-observed"]')?.click();
    await settle();
    expect(of("record_summary").at(-1)?.args).toEqual({ ticker: "NETGL", file, j: 3, jObserved: 3 });
    expect(of("predict_all").length).toBe(0);
    expect(of("ceiling_display").length).toBe(0);
    for (const c of h.calls) for (const k of keysDeep(c.args)) expect(DECL, `${c.cmd}.${k}`).not.toContain(k);
  });

  // FAZ9_UI_FIX K-FIX-1: sekme listeyi açar; liste satırı, "Tüm arzlar" ve değiştirici
  it("Analiz sekmesi her zaman listeyi açar; satır arzı açar; 'Tüm arzlar' listeye döner; değiştirici başka arzı açar", async () => {
    sade.ticker = "NETGL";
    mountSade(root, host(), "analiz");
    await settle();
    expect(root.querySelector('.analiz[data-ticker="NETGL"] .arz-crumb')).not.toBeNull();
    expect(of("monitor_view").length).toBe(1, "değiştirici için takipteki arzlar");
    root.querySelector<HTMLElement>('.s-top [data-go="analiz"]')?.click();
    await settle();
    expect(sade.ticker).toBeNull();
    expect(root.querySelectorAll(".analiz-pick tr[data-action=pick]").length).toBe(7);
    root.querySelector<HTMLElement>('.analiz-pick tr[data-action="pick"][data-ticker="NETGL"]')?.click();
    await settle();
    expect(sade.ticker).toBe("NETGL");
    expect(root.querySelector('.analiz[data-ticker="NETGL"]')).not.toBeNull();
    root.querySelector<HTMLElement>("[data-role=all-ipos]")?.click();
    await settle();
    expect(sade.ticker).toBeNull();
    expect(root.querySelector(".analiz-pick")).not.toBeNull();
    root.querySelector<HTMLElement>('.analiz-pick [data-action="pick"][data-ticker="NETGL"]')?.click();
    await settle();
    const sw = root.querySelector<HTMLSelectElement>("[data-role=arz-switch]") as HTMLSelectElement;
    expect(sw.value).toBe("NETGL");
    sw.value = "BKRGY";
    sw.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect(sade.ticker).toBe("BKRGY");
    expect(of("arz_view").at(-1)?.args).toEqual({ ticker: "BKRGY" });
    expect(of("arz_streak").at(-1)?.args).toEqual({ ticker: "BKRGY" });
    expect(of("predict_all").length).toBe(0);
  });

  // FAZ9_UI_FIX K-FIX-2: satır ya da "Aç" künyeyi yeniden çizer; görünür alanın dışındaysa sayfa künyeye kayar
  it("Sicil: 'Aç' seçili arzı değiştirir; künye görünür alanın dışındaysa yumuşakça kayar (hareket azaltılmışsa anında); içindeyse kaymaz", async () => {
    const scroll = vi.fn();
    const rect = { top: 2000, bottom: 2400 };
    Element.prototype.scrollIntoView = scroll;
    const orig = HTMLElement.prototype.getBoundingClientRect;
    HTMLElement.prototype.getBoundingClientRect = function (this: HTMLElement) {
      const base = orig.call(this);
      return this.classList.contains("sicil-card") ? ({ ...base, top: rect.top, bottom: rect.bottom, height: rect.bottom - rect.top } as DOMRect) : base;
    };
    let reduced = false;
    window.matchMedia = ((q: string) => ({ matches: reduced && q.includes("reduce"), media: q }) as MediaQueryList) as typeof window.matchMedia;
    try {
      mountSade(root, host(), "sicil");
      await settle();
      const reg = fx<{ tickers: { ticker: string }[] }>("registry_synthetic.json");
      const second = reg.tickers[1].ticker;
      root.querySelector<HTMLElement>(`.sicil-table [data-action="sicil-select"][data-ticker="${second}"]`)?.click();
      await settle();
      expect(sade.sicilTicker).toBe(second);
      expect(root.querySelector(".sicil-card h2")?.textContent).toBe(second);
      expect(of("break_view").at(-1)?.args).toEqual({ ticker: second });
      expect(scroll).toHaveBeenCalledTimes(1);
      expect(scroll.mock.calls[0][0]).toEqual({ block: "start", behavior: "smooth" });
      reduced = true;
      root.querySelector<HTMLElement>(`.sicil-table tr[data-action="sicil-select"][data-ticker="${reg.tickers[0].ticker}"]`)?.click();
      await settle();
      expect(scroll.mock.calls[1][0]).toEqual({ block: "start", behavior: "auto" });
      rect.top = 100;
      rect.bottom = 500;
      root.querySelector<HTMLElement>(`.sicil-table tr[data-action="sicil-select"][data-ticker="${second}"]`)?.click();
      await settle();
      expect(scroll).toHaveBeenCalledTimes(2);
    } finally {
      HTMLElement.prototype.getBoundingClientRect = orig;
    }
  });

  it("Tahmin sonucu (senaryo): ceiling_summary(runs, 0, null, t) ve ceiling_display(S, j); j düğmesi yalnız ceiling_display'i yeniden çağırır; kayıt isteğinde beyan boş", async () => {
    const runs = fx<ModelRun[]>("sade_runs_netgl.json");
    store.results = {
      runs,
      inputs: { ipo_price_tl: "25.52" },
      inputDates: { first_trading_date: "2026-09-17" },
      stage: "POST_BOOKBUILD_PRE_LISTING",
      tickerLabel: "NETGL",
      f6: { value: null, refusal: null, origin: "NONE", S0_date: null, S20_date: null, xu100_sha256: null, ref_date: null },
      source: "FORM",
      scenario: null,
      savedId: null,
    };
    mountSade(root, host(), "sonuc");
    await settle();
    const s = of("ceiling_summary")[0]?.args as { j: number; jObserved: number | null; t: string };
    expect([s.j, s.jObserved, s.t]).toEqual([0, null, "2026-09-17"]);
    expect(of("ceiling_display")[0]?.args.j).toBe(0);
    expect(of("ceiling_display")[0]?.args.ipoPriceTl).toBe("25.52");
    root.querySelector<HTMLElement>('[data-action="calc-j"][data-j="3"]')?.click();
    await settle();
    expect(of("ceiling_display").at(-1)?.args.j).toBe(3);
    expect(of("ceiling_summary").length).toBe(1);
    expect(root.querySelector('.calc[data-j="3"] [data-reading="tomorrow"] .s-reading-value')?.textContent).toBe("%67");
    root.querySelector<HTMLElement>('[data-action="save"]')?.click();
    await settle();
    const req = of("save_scenario")[0]?.args.req as Record<string, unknown>;
    expect(req.observed_streak_user).toBeNull();
    expect(req.title).toContain("NETGL");
    expect(store.results?.savedId).toBe("01KX");
    expect(of("predict_all").length).toBe(0);
  });

  it("Ayarlar: görünüm seçimi kabuğa iletilir (kalıcı yazım kabuktadır)", async () => {
    const hst = host();
    mountSade(root, hst, "ayarlar");
    await settle();
    const r = root.querySelector<HTMLInputElement>('input[name=ui_view][value="AYRINTILI"]') as HTMLInputElement;
    r.checked = true;
    r.dispatchEvent(new Event("change", { bubbles: true }));
    expect(hst.switchView).toHaveBeenCalledWith("AYRINTILI");
  });

  it("ayrıntılı görünüm bağlantısı karşılık gelen eski ekrana gider", async () => {
    const hst = host();
    mountSade(root, hst, "perf");
    await settle();
    root.querySelector<HTMLElement>('[data-detailed="accuracy"]')?.click();
    expect(hst.toDetailed).toHaveBeenCalledWith("accuracy");
  });

  it("bağımsız mod: Monitör, Analiz, Sicil 'repo modu gerekli'; komut çağrılmaz", async () => {
    store.config = { ...config(), repo_mode: false, repo: null };
    for (const s of ["monitor", "analiz", "sicil"] as const) {
      h.calls.length = 0;
      mountSade(root, host(), s);
      await settle();
      expect(root.querySelector(".repo-required"), s).not.toBeNull();
      expect(h.calls.length, s).toBe(0);
    }
  });

  // FAZ9_SNAPSHOT K-SNAP-2/3: kişisel modda gömülü anlık görüntü varken ekranlar dolu; doğrulanamazsa kapalı (fail-closed)
  const SNAP: SnapshotInfo = {
    status: "READY", code: null, detail: null, build_sha7: "e6c2e07", build_dirty: false,
    manifest_sha256: "0".repeat(64), n_files: 63, bytes: 627365, last_session: "2026-09-30",
  };
  const snapRespond = (cmd: string, args: Record<string, unknown>): unknown => {
    const v = respond(cmd, args);
    if (cmd === "monitor_view" || cmd === "registry_view") return { ...(v as object), snapshot: SNAP };
    return v;
  };

  it("kişisel mod + gömülü anlık görüntü: Monitör, Analiz, Sicil, Performans dolu; şerit ve künye kaynağı söyler", async () => {
    store.config = { ...config(), repo_mode: false, repo: null, snapshot: SNAP };
    h.respond = snapRespond;
    mountSade(root, host(), "monitor");
    await settle();
    expect(root.querySelector(".repo-required")).toBeNull();
    expect(root.querySelectorAll("tr[data-ticker]").length).toBe(7);
    expect(root.querySelector(".snap-source")?.textContent).toBe(SADE.snapshot.strip("e6c2e07", dateTr("2026-09-30"), false));
    expect(root.querySelector(".snap-source")?.textContent).toContain("Veri: gömülü anlık görüntü · derleme e6c2e07 · son sonuç");
    expect(root.querySelector(".s-standalone")).not.toBeNull();
    h.calls.length = 0;
    mountSade(root, host(), "analiz");
    sade.ticker = "NETGL";
    mountSade(root, host(), "analiz");
    await settle();
    for (const c of ["arz_view", "break_view", "arz_streak", "record_summary", "record_ceiling"]) expect(of(c).length, c).toBeGreaterThan(0);
    expect(root.querySelector('.analiz[data-ticker="NETGL"]')).not.toBeNull();
    h.calls.length = 0;
    mountSade(root, host(), "sicil");
    await settle();
    expect(of("registry_view").length).toBe(1);
    expect(root.querySelector(".sicil-card .sicil-source")?.textContent).toBe(SADE.snapshot.cardSource("e6c2e07"));
    expect(root.querySelector(".s-strip .snap-source")?.textContent).toContain(SADE.snapshot.sourceVal);
    mountSade(root, host(), "perf");
    await settle();
    expect(root.querySelector(".perf .repo-only")).toBeNull();
    expect(root.querySelector(".perf .snap-source")).not.toBeNull();
  });

  it("kişisel mod, anlık görüntü doğrulanamadı: dört ekran kapalı, bütünlük kodu görünür, okuma komutu çağrılmaz", async () => {
    store.config = { ...config(), repo_mode: false, repo: null, snapshot: { ...SNAP, status: "FAILED", code: "SNAPSHOT_INTEGRITY_FAILED", detail: "x" } };
    for (const s of ["monitor", "analiz", "sicil"] as const) {
      h.calls.length = 0;
      mountSade(root, host(), s);
      await settle();
      expect(root.querySelector('.snapshot-failed [data-code="SNAPSHOT_INTEGRITY_FAILED"]'), s).not.toBeNull();
      expect(root.querySelector(".repo-required"), s).not.toBeNull();
      expect(h.calls.length, s).toBe(0);
    }
  });
});
