// Yeni arz girişi (pano `Giris`): alanlar belgelerin yayım sırasıyla gruplanır (SPK bülteni, KAP sonuçları, BIST
// duyuruları, piyasa). Denetim Rust `check_form`'dan (not, gereklilik, öneri); okunur tekrar yalnız biçimlendirme
// (`readableCount`, `readableDate`). Oran, ilerleme yüzdesi ve "modellerin göreceği değerler" çizilmez (K-UI-7).
import { esc, renderError } from "../../dom";
import { F3_DEFINITION, F6, FORM_NOTE_TEXT, INPUTS, MARKET20_REASON_TEXT, SADE, type StageId } from "../../i18n/tr";
import { dateTr, pctSigned1, readableCount, readableDate } from "../../render/format";
import type { FormState } from "../../state";
import type { FormCheck } from "../../types";

export interface GirisVM {
  form: FormState;
  repoMode: boolean;
  hasResults: boolean;
}

const G = SADE.giris;

export const GROUPS: { id: "spk" | "kap" | "bist"; fields: string[] }[] = [
  {
    id: "spk",
    fields: [
      "ipo_price_try",
      "planned_pre_ipo_capital",
      "planned_post_ipo_capital",
      "planned_capital_increase_shares",
      "planned_existing_share_sale",
      "planned_additional_sale_ceiling",
      "planned_base_offer_shares",
      "planned_max_offer_shares",
    ],
  },
  {
    id: "kap",
    fields: [
      "ipo_price_tl",
      "capital_increase_shares",
      "shares_offered",
      "existing_share_sale_shares",
      "additional_sale_shares",
      "ipo_size_tl",
      "total_demand_multiple",
      "total_demand_filter_status",
    ],
  },
  { id: "bist", fields: ["first_trading_date", "bookbuilding_start", "bookbuilding_end", "post_ipo_share_capital"] },
];

const PRICE_FIELDS = ["ipo_price_try", "ipo_price_tl"];
const TL_FIELDS = ["ipo_size_tl"];
const DATE_FIELDS = ["first_trading_date", "bookbuilding_start", "bookbuilding_end"];
const MULTIPLE_FIELDS = ["total_demand_multiple"];

/** Özdeşlikler (Rust check_form ile aynı alanlar): toplam = parçalar; durum yalnız Rust notundan. */
export const IDENTITIES: { id: string; total: string; parts: string[]; note: string }[] = [
  { id: "ID-A", total: "planned_post_ipo_capital", parts: ["planned_pre_ipo_capital", "planned_capital_increase_shares"], note: "PB_IDENTITY" },
  { id: "ID-B", total: "planned_base_offer_shares", parts: ["planned_capital_increase_shares", "planned_existing_share_sale"], note: "PB_IDENTITY" },
  { id: "ID-C", total: "planned_max_offer_shares", parts: ["planned_base_offer_shares", "planned_additional_sale_ceiling"], note: "PB_IDENTITY" },
  { id: "SUM", total: "shares_offered", parts: ["capital_increase_shares", "existing_share_sale_shares", "additional_sale_shares"], note: "SHARES_SUM_MISMATCH" },
];

function unitOf(name: string): string {
  if (PRICE_FIELDS.includes(name) || TL_FIELDS.includes(name)) return G.unit.TL;
  if (MULTIPLE_FIELDS.includes(name)) return G.unit.kat;
  if (DATE_FIELDS.includes(name) || name === "total_demand_filter_status") return "";
  return G.unit.pay;
}

/** Okunur tekrar (biçimlendirme; hesap yok). */
export function readback(name: string, value: string): string {
  if (value.trim() === "") return "";
  if (DATE_FIELDS.includes(name)) return readableDate(value, SADE.months);
  if (PRICE_FIELDS.includes(name)) return G.readableTl(value.trim());
  if (TL_FIELDS.includes(name)) return G.readableTl(readableCount(value, SADE.units));
  if (MULTIPLE_FIELDS.includes(name)) return `${value.trim()} ${G.unit.kat}`;
  if (name === "total_demand_filter_status") return "";
  return G.readableShares(readableCount(value, SADE.units));
}

function notesFor(name: string, check: FormCheck | null): { cls: string; html: string } {
  const notes = (check?.notes ?? []).filter((n) => n.field === name && n.code !== "REQUIRED_EMPTY");
  if (!notes.length) return { cls: "", html: "" };
  const level = notes.some((n) => n.level === "error") ? "error" : notes.some((n) => n.level === "warn") ? "warn" : "info";
  const html = notes.map((n) => esc((FORM_NOTE_TEXT[n.code] ?? (() => n.code))({ value: n.value, name: n.name }))).join("<br/>");
  return { cls: level === "error" ? "has-error" : level === "warn" ? "has-warn" : "", html: `<div class="s-field-notes ${level}">${html}</div>` };
}

function fieldHtml(name: string, f: FormState): string {
  const value = f.fields[name] ?? "";
  const check = f.check;
  const req = check?.requirements[name] ?? null;
  const tag = req === "OPTIONAL" ? `<span class="opt">${esc(G.optional)}</span>` : req === "EMPTY" ? `<span class="opt">${esc(G.emptyExpected)}</span>` : "";
  const notes = notesFor(name, check);
  const disabled = f.stage === null ? " disabled" : "";
  const unit = unitOf(name);
  const input = name === "total_demand_filter_status"
    ? `<select data-field="${name}"${disabled}><option value="">${esc(INPUTS.filterStatusEmpty)}</option>` +
      ["NOT_SPECIFIED", "UNFILTERED", "FILTERED"].map((o) => `<option value="${o}"${value === o ? " selected" : ""}>${esc(SADE.filterStatus[o] ?? o)}</option>`).join("") +
      `</select>`
    : `<input type="text" data-field="${name}" value="${esc(value)}" inputmode="decimal" autocomplete="off"${disabled}/>`;
  const sug = check?.suggestions[name];
  const suggestion = sug && sug !== value
    ? `<div class="s-note">${esc(G.suggestion(sug))} <button class="s-link" data-action="apply-suggestion" data-field="${name}" data-value="${esc(sug)}">${esc(G.apply)}</button></div>`
    : "";
  const missing = f.missingReasons[name] && value === "" ? `<div class="s-note">${esc(G.fromDoc(f.missingReasons[name]))}</div>` : "";
  const ok = value.trim() !== "" && notes.cls !== "has-error" ? `<span class="ok">✓</span>` : "";
  return `<div class="s-field ${notes.cls}" data-name="${name}"><label><span>${esc(SADE.fieldLabel[name] ?? name)}</span>${tag}</label>` +
    `<div class="s-input">${input}${unit ? `<span class="unit">${esc(unit)}</span>` : ""}</div>` +
    `<div class="s-readback" data-readback="${name}"><span>${esc(readback(name, value))}</span>${ok}</div>${notes.html}${suggestion}${missing}</div>`;
}

function group(g: (typeof GROUPS)[number], f: FormState): string {
  const t = G.groups[g.id];
  const pre = g.id === "kap" && f.stage === "PRE_BOOKBUILD" ? `<p class="s-note kap-pre">${esc(G.kapPreNote)}</p>` : "";
  return `<section class="s-panel group-${g.id}"><div class="s-panel-head"><div><h2>${esc(t.title)}</h2><div class="s-panel-sub">${esc(t.sub)}</div></div></div>` +
    `<div class="s-panel-body">${pre}<div class="s-fields">${g.fields.map((n) => fieldHtml(n, f)).join("")}</div></div></section>`;
}

function topPanel(vm: GirisVM): string {
  const f = vm.form;
  const stageBtn = (id: StageId, label: string) =>
    `<button data-action="stage" data-stage="${id}" class="${f.stage === id ? "active" : ""}">${esc(label)}</button>`;
  const prefill = vm.repoMode
    ? `<div><div class="s-note">${esc(G.prefill)}</div><div class="s-actions"><select data-role="prefill-ticker">` +
      f.tickers.map((t) => `<option value="${esc(t)}"${t === f.prefillTicker ? " selected" : ""}>${esc(t)}</option>`).join("") +
      `</select><button data-action="prefill">${esc(G.prefillButton)}</button></div></div>`
    : `<p class="s-note">${esc(G.prefillNeedsRepo)}</p>`;
  return `<section class="s-panel giris-top"><div class="s-panel-body" style="padding-top:16px"><div class="s-head-row">` +
    `<div><div class="s-note">${esc(G.stage)}</div><div class="s-seg">${stageBtn("PRE_BOOKBUILD", G.stagePre)}${stageBtn("POST_BOOKBUILD_PRE_LISTING", G.stagePost)}</div></div>` +
    `<div><div class="s-note">${esc(G.ticker)}</div><input type="text" data-role="ticker-label" value="${esc(f.tickerLabel)}" autocomplete="off" style="width:140px;font-weight:600"/></div>` +
    `<div style="margin-left:auto">${prefill}</div></div>` +
    (f.prefillMsg ? `<p class="s-note mark-pass">✓ ${esc(f.prefillMsg)}</p>` : "") +
    (f.stage === null ? `<p class="s-note">${esc(G.stageFirst)}</p>` : "") + `</div></section>`;
}

function identityRows(f: FormState): string {
  const check = f.check;
  const has = (n: string) => (check?.normalized[n] ?? null) !== null;
  return IDENTITIES.map((id) => {
    const all = [id.total, ...id.parts].every(has);
    const bad = (check?.notes ?? []).some((n) => n.code === id.note && (id.id === "SUM" || n.name === id.id));
    // SUM tutmazsa yalnız uyarıdır (form.rs SHARES_SUM_MISMATCH `warn`; FAZ9_WINDOWS K-TXT-3); ID-A/B/C PB modellerini durdurur
    const badHtml = id.id === "SUM"
      ? `<span class="mark-warn">${esc(G.identityWarnMark)} ${esc(G.identityWarn)}</span>`
      : `<span class="mark-fail">× ${esc(G.identityBad)}</span>`;
    const state = !all ? `<span class="muted">${esc(SADE.dash)}</span>` : bad ? badHtml : `<span class="mark-pass">✓ ${esc(G.identityOk)}</span>`;
    const val = (n: string) => readableCount(check?.normalized[n] ?? null, SADE.units);
    const eq = all ? `<div class="cond">${esc(val(id.total))} = ${id.parts.map((p) => esc(val(p))).join(" + ")}</div>` : "";
    return `<div class="identity" data-identity="${id.id}"><div class="s-head-row"><span class="s-text2">${esc(G.identity[id.id] ?? id.id)}</span>${state}</div>${eq}</div>`;
  }).join("");
}

function checkPanel(vm: GirisVM): string {
  const f = vm.form;
  const missing = (f.check?.notes ?? []).filter((n) => n.code === "REQUIRED_EMPTY").map((n) => SADE.fieldLabel[n.field] ?? n.field);
  const miss = f.stage === null
    ? ""
    : missing.length
      ? `<p class="s-note">${esc(G.missingSome)} <span class="down">${esc(missing.join(", "))}</span></p>`
      : `<p class="s-note mark-pass">✓ ${esc(G.missingNone)}</p>`;
  return `<section class="s-panel check-panel"><div class="s-panel-head"><div><h2>${esc(G.checkTitle)}</h2><div class="s-panel-sub">${esc(G.checkSub)}</div></div></div>` +
    `<div class="s-panel-body">${miss}<div class="s-text2"><strong>${esc(G.identities)}</strong></div>${identityRows(f)}<p class="s-note">${esc(G.identityNote)}</p></div></section>`;
}

function marketPanel(vm: GirisVM): string {
  const f6 = vm.form.f6;
  const mode = (id: "REPO_PYTHON" | "MANUAL" | "NONE", label: string, dis = false) =>
    `<button data-action="f6-mode" data-mode="${id}" class="${f6.mode === id ? "active" : ""}"${dis ? " disabled" : ""}>${esc(label)}</button>`;
  let body = "";
  if (f6.mode === "REPO_PYTHON") {
    const r = f6.market20?.record ?? null;
    const val = r?.f6 ?? null;
    const neg = val !== null && val.trim().startsWith("-");
    const value = val === null
      ? `<div class="market-refusal s-text2">${esc(MARKET20_REASON_TEXT[r?.refusal ?? ""] ?? r?.refusal ?? SADE.dash)} <span class="mono">${esc(r?.refusal ?? "")}</span></div>`
      : `<div class="s-big ${neg ? "down" : "up"}">${esc(pctSigned1(val))}</div>`;
    body = (r
      ? `<div class="s-row" style="gap:28px;align-items:center"><div><div class="s-note">${esc(G.market20)}</div>${value}</div>` +
        `<div class="s-kv" style="min-width:240px"><div>${esc(G.marketClose(dateTr(r.S0_date)))}</div><div class="num">${esc(r.close_S0 ?? SADE.dash)}</div>` +
        `<div>${esc(G.marketClose(dateTr(r.S20_date)))}</div><div class="num">${esc(r.close_S20 ?? SADE.dash)}</div></div>` +
        `<p class="s-note" style="flex:1 1 260px">${esc(G.marketNote)}</p></div>`
      : "") +
      `<div class="s-actions"><button data-action="f6-compute"${f6.busy ? " disabled" : ""}>${esc(f6.busy ? F6.computing : F6.compute)}</button></div>` +
      (f6.error ? renderError(f6.error) : "");
  } else if (f6.mode === "MANUAL") {
    body = `<label class="s-note">${esc(F6.manualLabel)}</label><input type="text" data-f6-manual value="${esc(f6.manual)}" autocomplete="off"/>`;
  } else {
    body = `<p class="s-note">${esc(F6.modeNone)}</p>`;
  }
  return `<section class="s-panel market"><div class="s-panel-head"><div><h2>${esc(G.market)}</h2><div class="s-panel-sub">${esc(G.marketSub)}</div></div>` +
    `<div class="s-seg">${mode("REPO_PYTHON", G.marketCompute, !vm.repoMode)}${mode("MANUAL", G.marketManual)}${mode("NONE", G.marketNone)}</div></div>` +
    `<div class="s-panel-body">${!vm.repoMode && f6.mode === "REPO_PYTHON" ? `<p class="s-note">${esc(G.marketRepoOnly)}</p>` : body}</div></section>`;
}

export function renderGiris(vm: GirisVM): string {
  const f = vm.form;
  const f3 = `<details class="s-details"><summary>${esc(G.f3How)}</summary>${F3_DEFINITION.map((l) => `<p class="s-note">${esc(l)}</p>`).join("")}</details>`;
  const predict = `<button class="primary" data-action="predict" style="width:100%;min-height:44px"${f.stage === null || f.busy ? " disabled" : ""}>${esc(f.busy ? G.predicting : G.predict)}</button>`;
  const official = vm.repoMode
    ? `<button data-action="official" style="width:100%;min-height:44px"${vm.hasResults ? "" : " disabled"} title="${esc(INPUTS.prepareOfficialNote)}">${esc(G.official)}</button>`
    : `<button disabled style="width:100%;min-height:44px" title="${esc(G.officialClosed)}">${esc(G.official)}</button>`;
  return `<div class="s-main giris"><div class="s-head-row"><div><h1 class="s-h1">${esc(G.title)}</h1><p class="s-lead">${esc(G.intro)}</p></div>` +
    `<button class="s-link" data-detailed="inputs">${esc(SADE.detailedGo)}</button></div>${topPanel(vm)}` +
    `<div class="s-row"><div class="s-col grow-2">${GROUPS.map((g) => group(g, f)).join("")}${marketPanel(vm)}${f3}</div>` +
    `<div class="s-col side">${checkPanel(vm)}${predict}${official}<p class="s-note">${esc(G.footNote)}</p>` +
    (f.error ? renderError(f.error) : "") + `</div></div></div>`;
}
