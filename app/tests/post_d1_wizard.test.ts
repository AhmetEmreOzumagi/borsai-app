// @vitest-environment jsdom
// "D1 sonrası kayıt" sihirbazı (SPEC_APP EK 3 §6.6; U69'un ön uç kısmı). Görünümler Rust'ın gerçek çıktısıdır
// (src-tauri/tests/stage3.rs: post_d1_wizard_fixtures — sahte Python, sabit saat, gerçek ön koşul ve parite fonksiyonları);
// uçtan uca akış app/tests/e2e_post_d1_tmp_repo.sh'tedir. Burada yalnız render ve komut bloklarının biçimi sınanır.
import { describe, expect, it } from "vitest";

import { POST_D1 } from "../src/i18n/tr";
import { renderPostD1Wizard, type PostD1WizardVM } from "../src/render/post_d1";
import type { PostD1CancelResult, PostD1FreezeResult, PostD1Preflight } from "../src/types";
import { dom, fx, readText, split } from "./helpers";

function vm(extra: Partial<PostD1WizardVM> = {}): PostD1WizardVM {
  return {
    repoMode: true,
    ticker: "SNTA1",
    preflight: null,
    outcomesTodo: null,
    frozen: null,
    cancelFile: "",
    cancelReason: "",
    cancelled: null,
    busy: null,
    error: null,
    ...extra,
  };
}

const render = (extra: Partial<PostD1WizardVM> = {}) => dom(renderPostD1Wizard(vm(extra)));
const pf = (name: string) => fx<PostD1Preflight>(name);
const freezeButton = (root: HTMLElement) => root.querySelector<HTMLButtonElement>("[data-action=pd1-freeze]");

describe("U69 sihirbaz: dört adım ve ön koşullar", () => {
  it("dört adım başlığı (§9 P2 metinleri) ve iptal bölümü", () => {
    const root = render();
    const heads = [...root.querySelectorAll(".post-d1-step h3")].map((h) => h.textContent);
    expect(heads).toEqual(POST_D1.steps.map((s, i) => POST_D1.step(i + 1, s)));
    expect(root.querySelector(".post-d1-cancel h3")?.textContent).toBe(POST_D1.cancelTitle);
    expect(freezeButton(root)?.disabled).toBe(true);
  });

  it("listeleme öncesi kayıt yokken DUR: iki engel, kayıt düğmesi kapalı", () => {
    const root = render({ preflight: pf("post_d1_preflight_blocked.json") });
    const blockers = [...root.querySelectorAll<HTMLElement>(".preflight-blocked li")].map((li) => li.dataset.blocker);
    expect(blockers).toEqual(["NO_PRE_LISTING_RECORD", "D1_PENDING"]);
    expect(root.querySelector(".preflight-blocked")?.textContent).toContain(POST_D1.blockerText.NO_PRE_LISTING_RECORD);
    expect(root.querySelector(".preflight-blocked")?.textContent).toContain(POST_D1.d1Pending);
    expect(freezeButton(root)?.disabled).toBe(true);
  });

  it("commit bekliyor: sarı satır ve git durumu; engel değil (kayıt düğmesi açık)", () => {
    const p = pf("post_d1_preflight_uncommitted.json");
    const root = render({ preflight: p });
    expect(root.querySelector(".uncommitted")?.textContent).toBe(POST_D1.uncommitted);
    expect(root.querySelector(".git-status")?.textContent).toContain("data/");
    expect(freezeButton(root)?.disabled).toBe(false);
  });

  it("commit'li ve T_open Python'dan: yeşil, T_open metni, yerel saat notu ve kalan dakika (yalnız bilgi)", () => {
    const p = pf("post_d1_preflight_ok.json");
    const root = render({ preflight: p, outcomesTodo: fx<string[]>("post_d1_outcomes_todo.json") });
    expect(root.querySelector(".committed")?.textContent).toBe(POST_D1.committed);
    expect(root.querySelector(".t-open")?.textContent).toBe(POST_D1.tOpen("2030-01-08T09:40:00+03:00"));
    expect(root.textContent).toContain(POST_D1.tOpenNote);
    expect(root.querySelector(".minutes-left")?.textContent).toBe(POST_D1.minutesLeft("820"));
    expect(root.querySelector(".preflight-ok")?.textContent).toBe(POST_D1.ok);
    expect(freezeButton(root)?.disabled).toBe(false);
  });

  it("takvim dışı D_1: CALENDAR_NOT_AVAILABLE metni ve Python hatası aynen", () => {
    const root = render({ preflight: pf("post_d1_preflight_calendar.json") });
    expect(root.querySelector(".calendar-na")?.textContent).toBe(POST_D1.blockerText.CALENDAR_NOT_AVAILABLE);
    expect(root.textContent).toContain("CALENDAR_NOT_AVAILABLE: D_1 2031-01-07");
    expect(freezeButton(root)?.disabled).toBe(true);
  });
});

describe("U69 sihirbaz: komut blokları (uygulama çalıştırmaz) ve kayıt sonucu", () => {
  it("adım 2: tek fonksiyonun bloğu; satır başına bir komut, && yok, commit yollara sınırlı", () => {
    const todo = fx<string[]>("post_d1_outcomes_todo.json");
    const root = render({ preflight: pf("post_d1_preflight_ok.json"), outcomesTodo: todo });
    expect(root.querySelector(".post-d1-outcomes-todo")?.textContent).toBe(todo.join("\n"));
    expect(todo[1]).toBe("/REPO/.venv/bin/python -m borsai.outcomes update --through 2030-01-07");
    for (const l of todo) expect(l.includes("&&") || l.trim().startsWith("#")).toBe(false);
    for (const l of todo.filter((x) => x.startsWith("git commit"))) expect(l).toContain(" -- ");
    expect(root.querySelector("[data-action=pd1-preflight]")).not.toBeNull();
  });

  it("adım 3–4: parite 1/1, karşılaştırıcı kopyaları, komut bloğu ve zaman kanıtı metni", () => {
    const f = fx<PostD1FreezeResult>("post_d1_frozen_ok.json");
    const root = render({ preflight: pf("post_d1_preflight_ok.json"), frozen: f });
    const parity = root.querySelector<HTMLElement>(".post-d1-parity");
    expect(parity?.dataset.ok).toBe("true");
    expect(parity?.textContent).toBe(POST_D1.parity(true, 1, String(f.parity.max_abs)));
    expect(root.querySelector(".post-d1-comparators")?.getAttribute("data-ok")).toBe("true");
    expect(root.querySelector(".post-d1-frozen")?.textContent).toContain(f.record_rel_path);
    const block = root.querySelector(".post-d1-record-todo")?.textContent ?? "";
    expect(block).toBe(f.todo.join("\n"));
    expect(block).toContain("git add registry/post_d1/SNTA1/");
    expect(block).toContain("-m borsai.push_proof $(git rev-parse HEAD)");
    const proof = root.querySelector(".time-proof")?.textContent ?? "";
    expect(proof).toContain(POST_D1.timeProof);
    expect(proof).toContain(POST_D1.liveNote("2030-01-08T09:40:00+03:00"));
  });

  it("parite uyuşmazlığı kırmızı ve sapma listesi (tolerans gevşetilmez)", () => {
    const f = fx<PostD1FreezeResult>("post_d1_frozen_mismatch.json");
    const root = render({ frozen: f });
    const parity = root.querySelector<HTMLElement>(".post-d1-parity");
    expect(parity?.dataset.ok).toBe("false");
    expect(parity?.classList.contains("band-error")).toBe(true);
    expect(root.textContent).toContain("S[3]");
  });

  it("iptal: --cancel ile Python yazar; blokta commit/push satırları, Python satırı tekrar yok", () => {
    const c = fx<PostD1CancelResult>("post_d1_cancelled.json");
    const root = render({ preflight: pf("post_d1_preflight_ok.json"), cancelled: c });
    expect(root.textContent).toContain(POST_D1.cancelDone(c.cancel_rel_path));
    const block = root.querySelector(".post-d1-cancel-todo")?.textContent ?? "";
    expect(block).toContain("git push origin main");
    expect(block).not.toContain("--cancel");
    expect(root.textContent).toContain(POST_D1.cancelRule);
  });

  it("sihirbazın düğmeleri yalnız okuma/Python/kopyala eylemleri; commit/push düğmesi yok", () => {
    const root = render({ preflight: pf("post_d1_preflight_ok.json"), frozen: fx<PostD1FreezeResult>("post_d1_frozen_ok.json"),
      outcomesTodo: fx<string[]>("post_d1_outcomes_todo.json") });
    const actions = new Set([...root.querySelectorAll<HTMLElement>("[data-action]")].map((b) => b.dataset.action));
    expect([...actions].sort()).toEqual(["pd1-back", "pd1-copy", "pd1-freeze", "pd1-preflight"]);
  });

  it("repo modu değilken kapalı", () => {
    const root = render({ repoMode: false });
    expect(root.querySelector(".post-d1-step")).toBeNull();
  });

  it("ekran kodu git'e yazan bir komut çağırmaz (yalnız Rust sarmalayıcıları)", () => {
    const { code } = split(readText("src/screens/registry.ts"));
    expect(/invoke\s*\(/.test(code)).toBe(false);
    for (const w of ["commit", "push"]) expect(new RegExp(`api\\.\\w*${w}`, "i").test(code), w).toBe(false);
  });
});
