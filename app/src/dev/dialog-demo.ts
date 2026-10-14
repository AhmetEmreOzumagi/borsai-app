// YALNIZ EKRAN GÖRÜNTÜSÜ KOŞUSU (VITE_BORSAI_DEMO=1). `vite.config.ts` bu dosyayı
// `@tauri-apps/plugin-dialog` yerine koyar; üretim ve normal geliştirme derlemesinde hiç yüklenmez.
//
// Gerekçe: dosya seçici yerel bir modal penceredir, demo ona tıklayamaz. Burada YALNIZ `save`
// karşılanır ve hedef geçici uygulama verisidir (repo altı DEĞİL). Düğme, ön uç akışı ve Rust
// komutu gerçektir; yol bekçisi (U27) yine Rust tarafında koşar.
import { invoke } from "@tauri-apps/api/core";

export interface SaveOptions {
  title?: string;
  defaultPath?: string;
}

export async function save(options: SaveOptions = {}): Promise<string | null> {
  const cfg = (await invoke("get_config")) as { data_dir: string | null };
  const name = options.defaultPath ?? "demo_export.json";
  return `${cfg.data_dir ?? "."}/${name}`;
}

function unavailable(name: string): never {
  throw new Error(`demo: dialog.${name} is not stubbed`);
}

export function open(): never {
  return unavailable("open");
}

export function ask(): never {
  return unavailable("ask");
}

export function confirm(): never {
  return unavailable("confirm");
}

export function message(): never {
  return unavailable("message");
}
