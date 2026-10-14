// Ret/uyarı kodu → Türkçe metin (T-2). Metinler tr.ts'te; burada yalnız yer tutucular doldurulur.
import { CODE_TEXT, FIELDS, UNKNOWN_CODE_TEXT, type CodeParams } from "../i18n/tr";
import type { Warning } from "../types";
import { DASH, short } from "./format";

export function fieldLabel(name: string | null | undefined): string {
  if (!name) return "";
  const f = FIELDS.find((x) => x.name === name);
  return f ? `${f.label} (${name})` : name;
}

export function codeText(code: string, field: string | null | undefined, w?: Warning): string {
  const p: CodeParams = {
    field: fieldLabel(field ?? w?.feature),
    fieldRaw: field ?? "",
    feature: w?.feature ?? field ?? "",
    value: short(w?.value),
    min: short(w?.train_min),
    max: short(w?.train_max),
    used: short(w?.used),
    horizon: w?.horizon ?? "",
    snapped: w?.snapped ?? DASH,
    tick: w?.tick ?? DASH,
    specialVolume: w?.special_trade_volume ?? DASH,
    volume: w?.volume ?? DASH,
  };
  const fn = (CODE_TEXT as Record<string, (p: CodeParams) => string>)[code];
  return fn ? fn(p) : UNKNOWN_CODE_TEXT(code);
}
