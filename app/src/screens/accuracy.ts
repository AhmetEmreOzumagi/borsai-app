// Doğruluk ekranı (SPEC_APP §3d). Veri yalnız Rust `scores_view` komutundan gelir: kaynak seçimi,
// sürüm denetimi ve §2.3 bütünlük denetimi orada yapılır; burada yalnız render ve model seçici vardır.
import { api } from "../api";
import { asAppError, esc, renderError } from "../dom";
import { ACCURACY, TR } from "../i18n/tr";
import { renderAccuracy } from "../render/accuracy";
import { store } from "../state";

function paint(root: HTMLElement): void {
  const a = store.accuracy;
  const body = a.loaded
    ? renderAccuracy({ scores: a.scores, models: store.info?.models ?? [], pathParams: a.pathParams, hidden: a.hidden, open: a.open,
        postD1: a.postD1,
        oot: a.oot === undefined ? undefined : { view: a.oot, selected: a.ootSelected ?? {}, details: a.ootDetails ?? {} } })
    : `<p class="muted">${esc(TR.loading)}</p>`;
  root.innerHTML = `<h2>${esc(ACCURACY.title)}</h2>${body}${a.error ? renderError(a.error) : ""}`;
}

async function load(root: HTMLElement): Promise<void> {
  try {
    store.accuracy.scores = await api.scoresView();
    // Kartın "seri modeli" satırı gömülü tavan yolu künyesinden; skor dosyasından değil.
    store.accuracy.pathParams = await api.pathParams();
    // D1 sonrası skorlar (EK 3 §6.5): yalnız repo modunda okunur, gömülmez; ayrı ölçek
    store.accuracy.postD1 = await api.scoresPostD1View();
    // Zaman-dışı panel (EK 3 §7): görünüm + her bloğun seçili modelinin ayrıntısı (satırlar yalnız açık kümede)
    const oot = (await api.scoresOotView()) ?? null;
    store.accuracy.oot = oot;
    store.accuracy.ootDetails = {};
    for (const b of oot?.blocks ?? []) {
      const sel = store.accuracy.ootSelected?.[b.key] ?? b.models.find((m) => m.primary !== null)?.model_id ?? b.models[0]?.model_id;
      if (!sel) continue;
      store.accuracy.ootSelected = { ...(store.accuracy.ootSelected ?? {}), [b.key]: sel };
      store.accuracy.ootDetails[b.key] = await api.scoresOotModel(b.key, sel);
    }
    store.accuracy.error = null;
  } catch (e) {
    store.accuracy.scores = null;
    store.accuracy.error = asAppError(e);
  }
  store.accuracy.loaded = true;
  paint(root);
}

export function mount(root: HTMLElement): void {
  // Dosya her açılışta yeniden okunur (repo kopyası değişmiş olabilir); bayat panel gösterilmez.
  store.accuracy.loaded = false;
  paint(root);
  void load(root);
  root.onchange = (ev) => {
    const t = ev.target as HTMLInputElement;
    if (t.dataset.action === "oot-model") {
      // zaman-dışı panelde blok başına model seçimi: ayrıntı Rust'tan yeniden istenir (hesap yok)
      const block = t.dataset.block ?? "";
      store.accuracy.ootSelected = { ...(store.accuracy.ootSelected ?? {}), [block]: t.value };
      void api.scoresOotModel(block, t.value).then((d) => {
        store.accuracy.ootDetails = { ...(store.accuracy.ootDetails ?? {}), [block]: d };
        paint(root);
      });
      return;
    }
    if (t.dataset.action !== "toggle-model") return;
    const id = t.dataset.model ?? "";
    store.accuracy.hidden = t.checked ? store.accuracy.hidden.filter((x) => x !== id) : [...store.accuracy.hidden, id];
    paint(root);
  };
  // `toggle` olayı kabarmaz: yakalama evresinde dinlenir. Açık model blokları yeniden çizimde korunur.
  root.addEventListener(
    "toggle",
    (ev) => {
      const d = ev.target as HTMLElement;
      const id = d.dataset.model;
      if (!id || !d.classList.contains("model-block")) return;
      const open = (d as HTMLDetailsElement).open;
      store.accuracy.open = open ? [...store.accuracy.open.filter((x) => x !== id), id] : store.accuracy.open.filter((x) => x !== id);
    },
    true,
  );
}
