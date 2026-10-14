// YALNIZ GELİŞTİRME: ekran görüntüsü koşusu (app/docs/screens). `import.meta.env.DEV` ve
// VITE_BORSAI_DEMO=1 olmadan çağrılmaz; üretim derlemesinde ölü koddur. Kullanıcı gibi davranır:
// yalnız gerçek düğmelere tıklar ve alanları doldurur; her adımda Rust `dev_snapshot` ile görüntü alır.
import { invoke } from "@tauri-apps/api/core";

const sleep = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

async function until(pred: () => boolean, ms = 15000): Promise<void> {
  const start = Date.now();
  while (!pred()) {
    if (Date.now() - start > ms) throw new Error("demo: timeout");
    await sleep(100);
  }
}

const q = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel);

async function nav(id: string): Promise<void> {
  q<HTMLButtonElement>(`[data-nav="${id}"]`)?.click();
  await sleep(400);
}

async function click(sel: string): Promise<void> {
  await until(() => q(sel) !== null && !(q<HTMLButtonElement>(sel)?.disabled ?? false));
  q<HTMLElement>(sel)?.click();
  await sleep(300);
}

function change(el: HTMLInputElement | HTMLSelectElement, value?: string): void {
  if (value !== undefined) el.value = value;
  if (el instanceof HTMLInputElement && (el.type === "radio" || el.type === "checkbox")) el.checked = true;
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function type(el: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  el.value = value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

async function shot(name: string, scrollSel?: string): Promise<void> {
  const main = q<HTMLElement>("main.content");
  if (main) main.scrollTop = 0;
  if (scrollSel) q(scrollSel)?.scrollIntoView({ block: "start" });
  await sleep(600);
  await invoke("dev_snapshot", { name });
  await sleep(900);
}

/** Bir <details> bölümünü açar (zaten açıksa dokunmaz). */
async function openDetails(sel: string): Promise<void> {
  const block = q<HTMLDetailsElement>(sel);
  if (block && !block.open) await click(`${sel} > summary`);
}

/** Doğruluk panelinde bir model bloğunu açar (zaten açıksa dokunmaz). */
async function openBlock(modelId: string): Promise<void> {
  await openDetails(`.model-block[data-model="${modelId}"]`);
}

async function predictFor(ticker: string): Promise<void> {
  await nav("inputs");
  await until(() => q("[data-role=prefill-ticker]") !== null);
  const sel = q<HTMLSelectElement>("[data-role=prefill-ticker]");
  if (sel) change(sel, ticker);
  await click("[data-action=prefill]");
  await until(() => (q<HTMLInputElement>('[data-field="ipo_price_tl"]')?.value ?? "") !== "");
  const repo = q<HTMLInputElement>('input[name=f6mode][value="REPO_PYTHON"]');
  if (repo) change(repo);
  await sleep(300);
  await click("[data-action=f6-compute]");
  await until(() => q(".f6-result") !== null || q(".f6 .error-box") !== null);
}

export async function runDemo(): Promise<void> {
  try {
    // EK 3 P1 ekran görüntüleri (docs/app/p1/ekran): yalnız Tavan serisi kartı adımları
    if (import.meta.env.VITE_BORSAI_DEMO_P1 === "1") await p1Steps();
    // EK 3 P2 ekran görüntüleri (docs/app/p2/ekran): D1 sonrası sihirbazı ve satırı, YALNIZ geçici klonda
    else if (import.meta.env.VITE_BORSAI_DEMO_P2 === "1") await p2Steps();
    // EK 3 P3/P4 ekran görüntüleri (docs/app/p34/ekran): düşüş kartı ve zaman-dışı panel (asıl repo, salt okuma)
    else if (import.meta.env.VITE_BORSAI_DEMO_P34 === "1") await p34Steps();
    // FAZ9_WINDOWS ekran metni düzeltmeleri (app/docs/screens/v2/win_*; VITE_BORSAI_DEMO_V2=1 ile birlikte: sade görünüm)
    else if (import.meta.env.VITE_BORSAI_DEMO_WIN === "1") await winSteps();
    // FAZ9_SNAPSHOT kişisel mod, gömülü sicil anlık görüntüsü (app/docs/screens/v2/snap_*; VITE_BORSAI_DEMO_V2=1 ile birlikte)
    else if (import.meta.env.VITE_BORSAI_DEMO_SNAP === "1") await snapSteps();
    // Sade görünüm (FAZ9_APP_UI; app/docs/screens/v2): asıl repo, salt okuma
    else if (import.meta.env.VITE_BORSAI_DEMO_V2 === "1") await v2Steps();
    else await steps();
  } catch (e) {
    const box = document.createElement("pre");
    box.className = "error-box";
    box.textContent = `demo: ${String(e)}`;
    document.body.prepend(box);
    await sleep(300);
    await invoke("dev_snapshot", { name: "zz_demo_error" });
    await sleep(900);
  }
  await invoke("dev_snapshot_done").catch(() => undefined);
}

async function steps(): Promise<void> {
  await until(() => q("[data-nav]") !== null);
  // 1. repo modu (önerilen repo kökü; uygulama verisi BORSAI_DATA_DIR'de)
  await nav("settings");
  await click("[data-action=suggested]");
  await click("[data-action=save]");
  await until(() => q(".checks") !== null);
  await shot("01_ayarlar_repo_modu");

  // 2. VEYAS girdileri (f3 boş) → U7: 5 RET + 14 dolu
  await predictFor("VEYAS");
  await shot("02_girdi_veyas");
  await shot("03_girdi_veyas_f3_f6", ".f3-def");
  await click("[data-action=predict]");
  await until(() => q(".group-a") !== null && q(".conditional") !== null);
  await shot("04_sonuc_veyas_grup_a", ".group-a");
  await shot("05_sonuc_veyas_grup_b", ".group-b");
  await shot("06_sonuc_veyas_tavan_grafikleri", ".group-b .chart-wrap");
  await shot("04b_sonuc_veyas_grup_c", ".group-c");
  await shot("07_sonuc_veyas_kosullu", ".conditional");

  // 3. senaryo: NETGL (gözlenen j = 3), kişisel kayıt olarak sakla, listede gör, geri yükle
  await predictFor("NETGL");
  await click("[data-action=predict]");
  await until(() => q(".conditional .strip") !== null);
  const title = q<HTMLInputElement>("[data-role=save-title]");
  if (title) title.value = "NETGL senaryo (demo)";
  await click("[data-action=save-scenario]");
  await until(() => q(".ok-box") !== null);
  await shot("08_senaryo_netgl_sonuc", ".group-a");
  await shot("08b_senaryo_netgl_grup_c", ".group-c");
  await shot("09_senaryo_netgl_kosullu_j3", ".conditional");
  // "Getiri (koşullu)" sekmesi: gözlenen j = 3 (durum 1), kapanışlar data/outcomes/NETGL.csv'den
  await click('[data-action=cond-tab][data-tab="return"]');
  await until(() => q(".cond-return-table") !== null || q(".return-none") !== null || q(".path-cond") !== null);
  await shot("09b_senaryo_netgl_getiri_kosullu_j3", ".conditional");
  await click('[data-action=cond-tab][data-tab="ceiling"]');
  await until(() => q(".cond-table") !== null);
  const jSel = q<HTMLSelectElement>("[data-action=select-j]");
  if (jSel) change(jSel, "5");
  await until(() => q(".hypo") !== null);
  await shot("10_senaryo_netgl_varsayimsal_j5", ".conditional");
  await nav("scenarios");
  await until(() => q("[data-action=open]") !== null);
  await shot("11_kisisel_kayitlar");
  // §3f "tümünü dışa aktar": tek JSON dizisi. Dosya seçici bu koşuda src/dev/dialog-demo.ts'tir
  // (vite takma adı): hedef geçici uygulama verisindedir, repo altı değildir.
  await click("[data-action=export-all]");
  await until(() => q(".export-done") !== null);
  await shot("11b_kisisel_kayitlar_tumunu_disa_aktar");
  await click("[data-action=open]");
  await until(() => q(".scenario-head") !== null && q(".conditional") !== null);
  await shot("12_senaryo_yuklendi");
  await nav("about");
  await shot("13_hakkinda");

  // 3b. doğruluk paneli (§3d): önce gerçek scores/scores.json, sonra sentetik fixture'lar.
  // Fixture'a geçiş YALNIZ ekran görüntüsü koşusunda vardır (dev_scores_fixture, --features snapshot);
  // dosyalar salt okunur ve `synthetic: true` taşır.
  await nav("accuracy");
  await until(() => q(".model-blocks") !== null, 30000);
  await openBlock("v1_5_h99");
  await openBlock("ceiling_path_v0");
  await shot("25_dogruluk_gercek_dosya", '.model-block[data-model="v1_5_h99"]');
  await shot("25b_dogruluk_gercek_tavan_yolu", '.model-block[data-model="ceiling_path_v0"] .panel-backtest');
  // payda bölümü iki alt tablodur: SKIPPED ve OUT_OF_SCOPE (§3d, görev kararı G2)
  await openDetails(".retro");
  await openDetails(".skipped");
  await shot("25c_dogruluk_retro_atlanan", ".retro");
  for (const [fixture, name, sel] of [
    ["n7", "26_dogruluk_n7_satir_tablosu", ".panel-live"],
    ["n12", "27_dogruluk_n12_yetersiz_ornek", ".panel-live"],
    ["n35", "28_dogruluk_n35_hukum", ".panel-live"],
    ["conditional", "29_dogruluk_kosullu_sentetik", ".cond-scores"],
    ["bad_live_cells", "30_dogruluk_butunluk_hatasi", ".integrity-error"],
  ] as [string, string, string][]) {
    await invoke("dev_scores_fixture", { name: fixture });
    await nav("accuracy");
    await until(() => q(".model-blocks") !== null || q(".integrity-error") !== null, 30000);
    await openBlock("v1_5_h99");
    await shot(name, sel);
  }
  await invoke("dev_scores_fixture", { name: "" });

  // 4. sicil ekranı ve arz sayfası (ASIL REPO, salt okuma)
  await nav("registry");
  await until(() => q(".registry-table") !== null);
  await shot("14_sicil_listesi");
  await click('[data-action=open-ticker][data-ticker="NETGL"]');
  await until(() => q(".record-tabs") !== null && q(".cond-table") !== null);
  await shot("15_arz_sayfasi_netgl", ".record-tabs");
  await shot("16_arz_sayfasi_netgl_kosullu", ".conditional");
  // 16 modelli (Faz 4 öncesi) kayıt: koşullu getiri sekmesi "kayıt Faz 4 modellerini içermiyor" der
  await click('[data-action=cond-tab][data-tab="return"]');
  await until(() => q(".record-no-path") !== null || q(".path-cond") !== null);
  await shot("16b_arz_sayfasi_netgl_getiri_kosullu", ".conditional");

  // 5. dondur sihirbazı: YALNIZ geçici klonda (asıl repoda sihirbaz çalıştırılmaz)
  const clone = import.meta.env.VITE_BORSAI_DEMO_REPO;
  if (typeof clone !== "string" || clone === "") return;
  await nav("settings");
  const repoInput = q<HTMLInputElement>("[data-cfg=repo_root]");
  if (repoInput) type(repoInput, clone);
  // Klonda .venv yoktur: Python yolu asıl repo'nun yorumlayıcısıdır; cwd klon olduğu için
  // `import borsai` yine klondan çözülür (PYTHON_IMPORT denetimi bunu doğrular).
  const pyInput = q<HTMLInputElement>("[data-cfg=python_path]");
  const python = import.meta.env.VITE_BORSAI_DEMO_PYTHON;
  if (pyInput && typeof python === "string") type(pyInput, python);
  await click("[data-action=save]");
  await until(() => q(".checks tr.fail") === null && q(".ok-text") !== null);
  await predictFor("NETGL");
  await click("[data-action=predict]");
  await until(() => q(".group-a") !== null);
  await click("[data-action=official-flow]");
  await until(() => q(".wizard-step") !== null);
  const ticker = q<HTMLInputElement>("[data-role=wz-ticker]");
  if (ticker) type(ticker, "SNTC3");
  const company = q<HTMLInputElement>("[data-role=wz-company]");
  if (company) type(company, "SNTC3 Kurgusal Demo A.S.");
  await click("[data-action=read-manifest]");
  await until(() => q('[data-field-row="ipo_price_tl"] [data-field-key="source_id"] option[value="KAP_E2E_SONUC"]') !== null);
  await click("[data-action=preflight]");
  await until(() => q(".wizard-step[data-step='1'] .ok-box") !== null || q(".blockers") !== null);
  await shot("17_dondur_adim1_on_kosullar", "[data-step='1']");
  await shot("18_dondur_adim2_kaynak_belgeler", "[data-step='2']");
  fillWizardFields();
  await sleep(300);
  await shot("19_dondur_adim3_alanlar", "[data-step='3']");
  await click("[data-action=preview-doc]");
  await until(() => q(".doc-preview") !== null || q(".doc-problems") !== null || q(".doc-identical") !== null);
  await click("[data-action=write-doc]");
  await until(() => q(".doc-written") !== null || q(".doc-problems") !== null);
  await shot("20_dondur_adim3_belge_yazildi", "[data-step='3']");
  await click("[data-action=pit]");
  await until(() => q(".pit-ok") !== null || q(".pit-fail") !== null);
  const ack = q<HTMLInputElement>("[data-action=acknowledge]");
  if (ack) change(ack);
  await sleep(300);
  await shot("21_dondur_adim4_5_denetim_ve_uyari", "[data-step='4']");
  await click("[data-action=freeze]");
  await until(() => q(".parity-line") !== null || q(".error-box") !== null, 60000);
  // adım 6 son bölümdür: kayıt, parite satırı ve "Şimdi yapılacaklar" bloğu tek görüntüde
  await shot("22_dondur_adim6_kayit_ve_parite", "[data-step='6']");

  // 6. geçici klondaki YENİ kayıt (19 model): arz sayfasında Grup A/C ve koşullu getiri
  await click("[data-action=back-registry]");
  await until(() => q(".registry-table") !== null, 30000);
  await click('[data-action=open-ticker][data-ticker="SNTC3"]');
  await until(() => q(".record-path") !== null, 30000);
  await shot("23_arz_sayfasi_klon_19_model", ".record-path");
  await click('[data-action=cond-tab][data-tab="return"]');
  await until(() => q(".path-cond") !== null || q(".record-no-path") !== null, 30000);
  await shot("24_arz_sayfasi_klon_getiri_kosullu", ".conditional");
}

/** EK 3 P1: "Tavan serisi — kaç gün tavan?" kartı (asıl repo, salt okuma; uygulama verisi BORSAI_DATA_DIR'de). */
async function p1Steps(): Promise<void> {
  await until(() => q("[data-nav]") !== null);
  await nav("settings");
  await click("[data-action=suggested]");
  await click("[data-action=save]");
  await until(() => q(".checks") !== null);
  await shot("p1_00_ayarlar_tufe", ".checks");
  // VEYAS (f3 boş): v1 üçü RET · F3_MISSING, pooled@INF dolu, PB aynası açık
  await predictFor("VEYAS");
  await click("[data-action=predict]");
  await until(() => q(".summary-ceiling") !== null && q(".conditional") !== null, 30000);
  await shot("p1_01_veyas_kart", ".summary-ceiling");
  await shot("p1_02_veyas_kart_tablo", ".summary-ceiling .summary-table");
  await shot("p1_03_veyas_grup_b_katli", "details.group-b-details");
  // NETGL: gözlenen j (data/outcomes/NETGL.csv) → koşullu satır; sonra j = 0
  await predictFor("NETGL");
  await click("[data-action=predict]");
  await until(() => q(".summary-ceiling .summary-cond") !== null, 30000);
  await shot("p1_04_netgl_kart_j3", ".summary-ceiling");
  await shot("p1_05_netgl_adaylar_j3", ".summary-ceiling .summary-table");
  const jSel = q<HTMLSelectElement>("[data-action=select-j]");
  if (jSel) change(jSel, "0");
  await until(() => q(".summary-ceiling[data-j='0']") !== null);
  await shot("p1_06_netgl_kart_j0", ".summary-ceiling");
  await shot("p1_07_netgl_grup_b_katli", "details.group-b-details");
  await click("[data-action=open-group-b]");
  await until(() => q<HTMLDetailsElement>("details.group-b-details")?.open === true);
  await shot("p1_08_netgl_grup_b_acik", "details.group-b-details");
  // arz sayfası (resmi görünüm; 16 modelli kayıt: v1 satırları "kayıt bu modeli içermiyor")
  await nav("registry");
  await until(() => q(".registry-table") !== null);
  await click('[data-action=open-ticker][data-ticker="NETGL"]');
  await until(() => q(".summary-ceiling") !== null, 30000);
  await shot("p1_09_arz_sayfasi_netgl_kart", ".summary-ceiling");
  await nav("about");
  await shot("p1_10_hakkinda_tufe");
}

/**
 * EK 3 P3/P4: "Düşüş (D10)" kartı (NETGL, VEYAS, arz sayfası) ve Doğruluk sekmesindeki zaman-dışı panel (açık küme, kasa,
 * toplam, D1 sonrası, OOT_RETRO). Asıl repo salt okunur; panel yalnız açık küme kodlarını gösterir.
 */
async function p34Steps(): Promise<void> {
  await until(() => q("[data-nav]") !== null);
  await nav("settings");
  await click("[data-action=suggested]");
  await click("[data-action=save]");
  await until(() => q(".checks") !== null);
  // NETGL: fall card under the ceiling card
  await predictFor("NETGL");
  await click("[data-action=predict]");
  await until(() => q(".summary-fall") !== null, 30000);
  await shot("p34_01_netgl_dusus_karti", ".summary-fall");
  await openDetails(".summary-fall details.fall-cards");
  await shot("p34_02_netgl_dusus_tablo_kartlar", ".summary-fall .fall-table");
  await shot("p34_03_netgl_kartlar_ust_uste", ".summary-ceiling");
  // VEYAS (f3 missing): h99/pooled refused, addsale and @ZERO predict
  await predictFor("VEYAS");
  await click("[data-action=predict]");
  await until(() => q(".summary-fall") !== null, 30000);
  await shot("p34_04_veyas_dusus_karti", ".summary-fall");
  // official view (16-model record: fall rows say the record predates the model)
  await nav("registry");
  await until(() => q(".registry-table") !== null);
  await click('[data-action=open-ticker][data-ticker="NETGL"]');
  await until(() => q(".summary-fall") !== null, 30000);
  await shot("p34_05_arz_sayfasi_netgl_dusus", ".summary-fall");
  // accuracy: out-of-time panel
  await nav("accuracy");
  await until(() => q(".panel-oot .oot-block") !== null, 60000);
  await shot("p34_06_zaman_disi_baslik", ".panel-oot");
  await shot("p34_07_zaman_disi_acik_kume", '.oot-block[data-block="oot_pre_h99"]');
  await openDetails('.oot-block[data-block="oot_pre_h99"] details.by-year');
  await shot("p34_08_zaman_disi_acik_kume_hucreler", '.oot-block[data-block="oot_pre_h99"] .model-block-oot');
  await openDetails('.oot-block[data-block="oot_pre_h99"] details.oot-rows-block');
  await shot("p34_09_zaman_disi_acik_kume_satirlar", '.oot-block[data-block="oot_pre_h99"] details.oot-rows-block');
  await shot("p34_10_zaman_disi_kasa", '.oot-block[data-block="oot_pre_h99_sealed"]');
  const sel = q<HTMLSelectElement>('select[data-action="oot-model"][data-block="oot_pre_h99_sealed"]');
  if (sel) {
    change(sel, "fall_d10_v0_pooled");
    await until(() => q('.oot-block[data-block="oot_pre_h99_sealed"] .model-block-oot[data-model="fall_d10_v0_pooled"]') !== null, 30000);
    await shot("p34_11_zaman_disi_kasa_dusus_pooled", '.oot-block[data-block="oot_pre_h99_sealed"] .model-block-oot');
  }
  await shot("p34_12_zaman_disi_toplam", '.oot-block[data-block="oot_pre_h99_all"]');
  await shot("p34_13_zaman_disi_d1_sonrasi", ".oot-post-d1");
  await openDetails(".panel-oot details.oot-retro");
  await shot("p34_14_zaman_disi_retro", ".panel-oot details.oot-retro");
}

/**
 * EK 3 P2: "D1 sonrası kayıt" sihirbazı ve "D1 sonrası" satırı. YALNIZ geçici klonda (app/scripts/screens_p2.sh: kurgusal
 * SNTA1'in listeleme öncesi kaydı ve sentetik D_1'i klonda hazır); sihirbaz Python `freeze --post-d1`'i klonda çağırır.
 */
async function p2Steps(): Promise<void> {
  await until(() => q("[data-nav]") !== null);
  const clone = import.meta.env.VITE_BORSAI_DEMO_REPO;
  if (typeof clone !== "string" || clone === "") throw new Error("demo P2: VITE_BORSAI_DEMO_REPO (temp clone) required");
  await nav("settings");
  const repoInput = q<HTMLInputElement>("[data-cfg=repo_root]");
  if (repoInput) type(repoInput, clone);
  const pyInput = q<HTMLInputElement>("[data-cfg=python_path]");
  const python = import.meta.env.VITE_BORSAI_DEMO_PYTHON;
  if (pyInput && typeof python === "string") type(pyInput, python);
  await click("[data-action=save]");
  await until(() => q(".checks tr.fail") === null && q(".ok-text") !== null, 30000);
  await nav("registry");
  await until(() => q(".registry-table") !== null, 30000);
  await shot("p2_00_sicil_listesi", ".registry-table");
  await click('[data-action=open-ticker][data-ticker="SNTA1"]');
  await until(() => q(".record-tabs") !== null && q(".cond-table") !== null, 30000);
  // sihirbaz: 1 ön koşullar → 2 komutlar → 3 kayıt (Python) + parite → 4 komutlar
  await click("[data-action=pd1-wizard]");
  await until(() => q(".post-d1-wizard") !== null);
  await click("[data-action=pd1-preflight]");
  await until(() => q(".post-d1-checks") !== null, 30000);
  await shot("p2_01_sihirbaz_adim1_on_kosullar", "[data-step='1']");
  await shot("p2_02_sihirbaz_adim2_komutlar", "[data-step='2']");
  await click("[data-action=pd1-freeze]");
  await until(() => q(".post-d1-parity") !== null || q(".post-d1-wizard .error-box") !== null, 60000);
  await shot("p2_03_sihirbaz_adim3_kayit_parite", "[data-step='3']");
  await shot("p2_04_sihirbaz_adim4_simdi_yapilacaklar", "[data-step='4']");
  // arz sayfası: j = 0'da satır yok + not; j = 2'de satır (S kayıttan)
  await click("[data-action=pd1-back]");
  await until(() => q(".record-tabs") !== null && q(".cond-table") !== null, 30000);
  const setJ = (j: string) => {
    const sel = q<HTMLSelectElement>("[data-action=select-j]");
    if (sel) change(sel, j);
  };
  setJ("0");
  await until(() => q(".post-d1-j0") !== null, 30000);
  await shot("p2_05_kosullu_j0_satir_yok", ".conditional");
  setJ("2");
  await until(() => q('.cond-table[data-j="2"] td[data-model="post_d1_hazard_v0"]') !== null, 30000);
  await shot("p2_06_kosullu_j2_d1_sonrasi_satiri", ".conditional");
  await shot("p2_07_kart_post_d1_satiri", ".summary-ceiling");
  await shot("p2_08_kart_tablo_terazi_sutunlari", ".summary-ceiling .summary-table");
  await click('[data-action=cond-tab][data-tab="return"]');
  await until(() => q(".post-d1-path") !== null || q(".record-no-path") !== null, 30000);
  await shot("p2_09_getiri_kosullu_d1_sonrasi_karti", ".post-d1-path");
  await click('[data-action=cond-tab][data-tab="ceiling"]');
  // Doğruluk: scores_post_d1.json (klondaki gerçek dosyanın kopyası; repo modu)
  await nav("accuracy");
  await until(() => q(".panel-post-d1") !== null, 30000);
  await openDetails(".post-d1-retro");
  await shot("p2_10_dogruluk_d1_sonrasi_bolumu", ".panel-post-d1");
  await nav("about");
  await shot("p2_11_hakkinda_ikinci_dizin");
}

/** Sihirbaz adım 3: kaynak seçimi ve alıntılar (kullanıcının yapacağı doldurma). */
function fillWizardFields(): void {
  const rows = [...document.querySelectorAll<HTMLElement>("[data-field-row]")];
  for (const row of rows) {
    const name = row.dataset.fieldRow ?? "";
    const source = row.querySelector<HTMLSelectElement>('[data-field-key="source_id"]');
    if (source) {
      const wanted = name === "total_demand_multiple" || name === "total_demand_filter_status" ? "KAP_E2E_EK" : name.startsWith("planned") || name === "ipo_price_try" || name.startsWith("bookbuilding") ? "SPK_E2E_BULTEN" : "KAP_E2E_SONUC";
      change(source, wanted);
    }
    const origin = row.querySelector<HTMLSelectElement>('[data-field-key="origin"]');
    if (origin) change(origin, "SOURCE_REPORTED");
    const quote = row.querySelector<HTMLInputElement>('[data-field-key="quote"]');
    if (quote) type(quote, `kurgusal belgede: ${name}`);
    const missing = row.querySelector<HTMLInputElement>('[data-field-key="missing_reason"]');
    if (missing) type(missing, "kurgusal demo: bu alan belgede yok");
  }
  const ftd = document.querySelector<HTMLSelectElement>("[data-role=ftd-source]");
  if (ftd) change(ftd, "KAP_E2E_SONUC");
}

// ---------------------------------------------------------------- sade görünüm (FAZ9_APP_UI, app/docs/screens/v2)

/** Sade kabukta görüntü: belge kaydırılır (üst bar yapışkan); seçici verilirse o bölüm üste gelir. */
async function shotV2(name: string, scrollSel?: string): Promise<void> {
  window.scrollTo(0, 0);
  if (scrollSel) {
    const el = q<HTMLElement>(scrollSel);
    if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 64);
  }
  await sleep(1900);
  await invoke("dev_snapshot", { name });
  await sleep(900);
}

async function goV2(screen: string): Promise<void> {
  q<HTMLElement>(`.s-top [data-go="${screen}"]`)?.click();
  await sleep(500);
}

/** YALNIZ görüntü koşusu: pencere boyutu (Rust `dev_window_size`; K-FIX-6 görüntüleri ve 1024 × 680 denetimi). */
async function windowV2(width: number, height: number): Promise<void> {
  await invoke("dev_window_size", { width, height });
  await sleep(900);
}

/** K-FIX-6: bu pencerede hiçbir sade ekranda yatay kaydırma çubuğu yok (belge genişliği görünür alanı aşmaz). */
function assertNoHorizontalScroll(screen: string): void {
  const doc = document.documentElement;
  if (doc.scrollWidth > doc.clientWidth || document.body.scrollWidth > doc.clientWidth) {
    throw new Error(`demo: horizontal overflow on ${screen} (${doc.scrollWidth} > ${doc.clientWidth})`);
  }
}

/**
 * Sade görünüm: bağımsız mod boş durumu → repo modu (öneri) → Monitör → Yeni arz girişi (NETGL, talep sonrası, f6 Python) →
 * Tahmin sonucu j = 0 ve j = 3 → kişisel kayıt → Kayıtlarım → Analiz NETGL (gözlenen j = 3; kırılma kartı) → Model
 * performansı → Sicil → dondur sihirbazı adım 1 (yalnız ön koşul denetimi; yazma yok) → Ayrıntılı görünüme geçiş ve dönüş.
 */
async function v2Steps(): Promise<void> {
  await until(() => q(".s-top") !== null);
  await windowV2(1440, 900);
  await goV2("monitor");
  await until(() => q(".repo-required") !== null);
  await shotV2("v2_00_bagimsiz_mod_monitor");
  await goV2("ayarlar");
  await click("[data-action=suggested]");
  await click("[data-action=save]");
  await until(() => q(".ayarlar .checks") !== null && (q(".ayarlar")?.textContent ?? "").includes("/"), 30000);
  await shotV2("v2_10_ayarlar_hakkinda");

  await goV2("monitor");
  await until(() => q(".monitor-table tr[data-ticker]") !== null, 30000);
  await shotV2("v2_01_monitor");
  await shotV2("v2_01b_monitor_olay_akisi", ".events");

  await goV2("giris");
  await click('[data-action=stage][data-stage="POST_BOOKBUILD_PRE_LISTING"]');
  await until(() => q("[data-role=prefill-ticker]") !== null);
  await sleep(1200);
  const sel = q<HTMLSelectElement>("[data-role=prefill-ticker]");
  if (sel) change(sel, "NETGL");
  await click("[data-action=prefill]");
  await until(() => (q<HTMLInputElement>('[data-field="ipo_price_tl"]')?.value ?? "") !== "");
  await sleep(1200);
  await click('[data-action=f6-mode][data-mode="REPO_PYTHON"]');
  // anında denetim formu yeniden çizer; düğme yenisiyle değişmeden tıklanmasın
  await sleep(1500);
  await click("[data-action=f6-compute]");
  // "Hesapla" bugünü referans alır (§3a.2); XU100 dosyası bugüne yetişmemişse Python ret metni döner
  await until(() => q(".market .s-big") !== null || q(".market .market-refusal") !== null || q(".market .error-box") !== null, 90000);
  await shotV2("v2_02_giris_netgl_talep_sonrasi");
  await shotV2("v2_02b_giris_kap_bist_piyasa", ".group-kap");

  await click("[data-action=predict]");
  await until(() => q('.sonuc .calc[data-j="0"] [data-reading="tomorrow"]') !== null, 60000);
  await shotV2("v2_03_sonuc_j0");
  await click('[data-action=calc-j][data-j="3"]');
  await until(() => q('.sonuc .calc[data-j="3"] [data-reading="tomorrow"]') !== null);
  await shotV2("v2_04_sonuc_j3", ".calc");
  await shotV2("v2_04b_sonuc_getiri_dayanaklar", ".returns");
  const title = q<HTMLInputElement>("[data-role=save-title]");
  if (title) title.value = "NETGL post-bookbuild (demo)";
  await click("[data-action=save]");
  await until(() => q(".save .mark-pass") !== null);

  await goV2("kayitlarim");
  await until(() => q(".kayitlarim tr[data-id]") !== null);
  await shotV2("v2_08_kayitlarim");

  // Analiz (FAZ9_UI_FIX K-FIX-1): sekme listeyi açar; satır arzı açar; yol + "Tüm arzlar" + değiştirici; K-FIX-3 j = 3 ve j = 6;
  // K-FIX-4 işlem sayısı çubukları
  await goV2("analiz");
  await until(() => q(".analiz-pick tr[data-ticker]") !== null, 30000);
  await shotV2("v2_05a_analiz_listesi");
  await click('.analiz-pick tr[data-action=pick][data-ticker="NETGL"]');
  await until(() => q('.analiz .calc[data-j="3"] [data-reading="tomorrow"]') !== null, 30000);
  await shotV2("v2_05_analiz_netgl");
  await shotV2("v2_05e_analiz_islem_sayisi", ".corridor-panel");
  await shotV2("v2_05b_analiz_hesaplayici_gozlenen_j3", ".calc");
  await click('[data-action=calc-j][data-j="6"]');
  await until(() => q('.analiz .calc[data-j="6"] [data-reading="tomorrow"]') !== null, 30000);
  await shotV2("v2_05b2_analiz_hesaplayici_j6", ".calc");
  await click("[data-action=calc-observed]");
  await until(() => q('.analiz .calc[data-j="3"] [data-reading="tomorrow"]') !== null, 30000);
  await shotV2("v2_05c_analiz_kirilma_getiri", ".break-card");
  await shotV2("v2_05d_analiz_gunluk", ".events");
  // "Tüm arzlar" listeye döner; değiştirici başka arzı açar; sonra NETGL'e dönülür
  await click("[data-role=all-ipos]");
  await until(() => q(".analiz-pick tr[data-ticker]") !== null, 30000);
  await click('.analiz-pick tr[data-action=pick][data-ticker="NETGL"]');
  await until(() => q('.analiz[data-ticker="NETGL"] .calc') !== null, 30000);
  const sw = q<HTMLSelectElement>("[data-role=arz-switch]");
  if (sw) change(sw, "BKRGY");
  await until(() => q('.analiz[data-ticker="BKRGY"] .calc') !== null, 30000);
  await shotV2("v2_05f_analiz_bkrgy_degistirici");

  await goV2("perf");
  await until(() => q(".perf-row") !== null, 30000);
  await shotV2("v2_06_model_performansi");
  await shotV2("v2_06b_model_performansi_terazi_canli", ".perf-scales");

  await goV2("sicil");
  await until(() => q(".sicil-table tr[data-ticker]") !== null, 30000);
  await shotV2("v2_07_sicil");
  // K-FIX-2 + K-FIX-6: 1200 px pencerede BKRGY satırı tıklanır; künye yeniden çizilir ve görünür alana kayar
  await windowV2(1200, 800);
  await click('.sicil-table tr[data-action=sicil-select][data-ticker="BKRGY"]');
  await until(() => (q(".sicil-card h2")?.textContent ?? "") === "BKRGY", 30000);
  await sleep(1500);
  await invoke("dev_snapshot", { name: "v2_07b_sicil_1200_bkrgy" });
  await sleep(900);
  // K-FIX-6: en küçük pencerede (1024 × 680) hiçbir sade ekranda yatay kaydırma çubuğu yok
  await windowV2(1024, 680);
  for (const screen of ["monitor", "analiz", "perf", "sicil", "kayitlarim"]) {
    await goV2(screen);
    await sleep(900);
    assertNoHorizontalScroll(screen);
  }
  await goV2("analiz");
  await click('.analiz-pick tr[data-action=pick][data-ticker="NETGL"]');
  await until(() => q('.analiz[data-ticker="NETGL"] .calc') !== null, 30000);
  await sleep(600);
  assertNoHorizontalScroll("analiz NETGL");
  await shotV2("v2_13_analiz_1024");
  await click('[data-go="giris"]');
  await sleep(900);
  assertNoHorizontalScroll("giris");
  await windowV2(1440, 900);
  await goV2("sicil");
  await until(() => q(".sicil-table tr[data-ticker]") !== null, 30000);

  await click("[data-action=new-record]");
  await until(() => q(".sihirbaz .s-legacy") !== null);
  await click(".sihirbaz [data-action=preflight]");
  await until(() => (q(".sihirbaz .s-legacy")?.textContent ?? "").includes("HEAD"), 60000);
  await shotV2("v2_09_sihirbaz_adim1_on_kosullar");

  await goV2("ayarlar");
  const det = q<HTMLInputElement>('input[name=ui_view][value="AYRINTILI"]');
  if (det) change(det);
  await until(() => q("nav.sidebar") !== null);
  await sleep(600);
  await invoke("dev_snapshot", { name: "v2_11_ayrintili_gorunume_gecis" });
  await sleep(900);
  await click('[data-nav="sade"]');
  await until(() => q(".s-top") !== null);
  await shotV2("v2_12_sade_gorunume_donus");
}

/**
 * FAZ9_WINDOWS (yalnız görüntü koşusu; `screens_v2.sh` kalıbı + VITE_BORSAI_DEMO_WIN=1): repo modu (öneri) → Monitör veri şeridi
 * (K-TXT-2) → Yeni arz girişi NETGL (talep sonrası) → Tahmin sonucu getiri tablosu (K-TXT-1) → Analiz NETGL getiri paneli
 * (K-TXT-1) → girişe dönüş, ek satış alanı demo için değiştirilir: SUM tutmaz, uyarı (K-TXT-3). Kayıt yazılmaz.
 */
async function winSteps(): Promise<void> {
  await until(() => q(".s-top") !== null);
  await windowV2(1440, 900);
  await goV2("ayarlar");
  await click("[data-action=suggested]");
  await click("[data-action=save]");
  await until(() => q(".ayarlar .checks") !== null && (q(".ayarlar")?.textContent ?? "").includes("/"), 30000);

  await goV2("monitor");
  await until(() => q(".monitor-table tr[data-ticker]") !== null, 30000);
  await shotV2("win_02_monitor_serit");

  await goV2("giris");
  await click('[data-action=stage][data-stage="POST_BOOKBUILD_PRE_LISTING"]');
  await until(() => q("[data-role=prefill-ticker]") !== null);
  await sleep(1200);
  const sel = q<HTMLSelectElement>("[data-role=prefill-ticker]");
  if (sel) change(sel, "NETGL");
  await click("[data-action=prefill]");
  await until(() => (q<HTMLInputElement>('[data-field="ipo_price_tl"]')?.value ?? "") !== "");
  await sleep(1200);
  await click('[data-action=f6-mode][data-mode="REPO_PYTHON"]');
  await sleep(1500);
  await click("[data-action=f6-compute]");
  await until(() => q(".market .s-big") !== null || q(".market .market-refusal") !== null || q(".market .error-box") !== null, 90000);
  await click("[data-action=predict]");
  await until(() => q('.sonuc .calc[data-j="0"] [data-reading="tomorrow"]') !== null, 60000);
  await until(() => q(".sonuc .returns .not-primary") !== null, 30000);
  await shotV2("win_01_sonuc_birincil_degil", ".returns");

  await goV2("analiz");
  await until(() => q(".analiz-pick tr[data-ticker]") !== null, 30000);
  await click('.analiz-pick tr[data-action=pick][data-ticker="NETGL"]');
  await until(() => q(".analiz .returns .not-primary") !== null, 30000);
  await shotV2("win_04_analiz_birincil_degil", ".returns");

  await goV2("giris");
  await until(() => q<HTMLInputElement>('[data-field="additional_sale_shares"]') !== null, 30000);
  const add = q<HTMLInputElement>('[data-field="additional_sale_shares"]');
  if (add) type(add, "12500000");
  await until(() => q('[data-identity="SUM"] .mark-warn') !== null, 30000);
  await shotV2("win_03_giris_sum_uyari", ".check-panel");
}

/**
 * FAZ9_SNAPSHOT (yalnız görüntü koşusu; `screens_v2.sh` kalıbı + VITE_BORSAI_DEMO_SNAP=1): repo ayarı BOŞ (kişisel mod), veri
 * gömülü sicil anlık görüntüsünden → Monitör (veri şeridi, 7 arz), Analiz NETGL (gözlenen j, kırılma kartı), Sicil (kaynak),
 * Model performansı. Repo ayarlanmaz, kayıt yazılmaz.
 */
async function snapSteps(): Promise<void> {
  await until(() => q(".s-top") !== null);
  await windowV2(1440, 900);
  await goV2("monitor");
  await until(() => q(".monitor-table tr[data-ticker]") !== null && q(".snap-source") !== null, 30000);
  if (q(".s-standalone") === null || q(".repo-required") !== null) throw new Error("demo SNAP: personal mode with snapshot expected");
  if (document.querySelectorAll(".monitor-table tr[data-ticker]").length !== 7) throw new Error("demo SNAP: 7 rows expected");
  await shotV2("snap_01_monitor");

  await goV2("analiz");
  await until(() => q(".analiz-pick tr[data-ticker]") !== null, 30000);
  await click('.analiz-pick tr[data-action=pick][data-ticker="NETGL"]');
  await until(() => q('.analiz .calc[data-j="3"] [data-reading="tomorrow"]') !== null && q(".break-card") !== null, 30000);
  await shotV2("snap_02_analiz_netgl");

  await goV2("sicil");
  await until(() => q(".sicil-table tr[data-ticker]") !== null && q(".sicil-card .sicil-source") !== null, 30000);
  await shotV2("snap_03_sicil");

  await goV2("perf");
  await until(() => q(".perf-row") !== null && q(".perf .snap-source") !== null, 30000);
  await shotV2("snap_04_model_performansi");
}
