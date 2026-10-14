// Test yardımcıları: fixture'lar Rust komutlarının gerçek çıktısıdır (src-tauri/tests/stage2.rs üretir).
// jsdom ortamında import.meta.url dosya yolu vermediği için yollar app/ kökünden çözülür.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

export const APP_DIR = existsSync(join(process.cwd(), "tests", "fixtures")) ? process.cwd() : join(process.cwd(), "app");

export function fx<T>(name: string): T {
  return JSON.parse(readFileSync(join(APP_DIR, "tests", "fixtures", "ui", name), "utf-8")) as T;
}

/** app/ köküne göre göreli yol. */
export function readText(rel: string): string {
  return readFileSync(join(APP_DIR, rel), "utf-8");
}

export function dom(html: string): HTMLElement {
  const d = document.createElement("div");
  d.innerHTML = html;
  return d;
}

/** Kod ve metin sabitlerini ayırır: yorumlar atılır; '…', "…", `…` metinleri `strings`'e, `${…}` içi koda gider. */
export function split(src: string): { code: string; strings: string[] } {
  let code = "";
  const strings: string[] = [];
  let i = 0;
  const stack: number[] = []; // şablon ${ } derinlikleri
  let depth = 0;
  const readTemplate = () => {
    let buf = "";
    i += 1;
    while (i < src.length) {
      const c = src[i];
      if (c === "\\") {
        buf += src.slice(i, i + 2);
        i += 2;
      } else if (c === "`") {
        i += 1;
        strings.push(buf);
        return;
      } else if (c === "$" && src[i + 1] === "{") {
        strings.push(buf);
        buf = "";
        i += 2;
        stack.push(depth);
        depth += 1;
        code += " ";
        return;
      } else {
        buf += c;
        i += 1;
      }
    }
  };
  while (i < src.length) {
    const c = src[i];
    const n = src[i + 1];
    if (c === "/" && n === "/") {
      while (i < src.length && src[i] !== "\n") i += 1;
    } else if (c === "/" && n === "*") {
      i = src.indexOf("*/", i + 2) + 2;
    } else if (c === "'" || c === '"') {
      let j = i + 1;
      while (j < src.length && src[j] !== c) j += src[j] === "\\" ? 2 : 1;
      strings.push(src.slice(i + 1, j));
      code += " ";
      i = j + 1;
    } else if (c === "`") {
      readTemplate();
    } else if (c === "}" && stack.length && depth - 1 === stack[stack.length - 1]) {
      stack.pop();
      depth -= 1;
      // şablona dönüş
      i -= 0;
      readTemplate();
    } else {
      if (c === "{") depth += 1;
      if (c === "}") depth -= 1;
      code += c;
      i += 1;
    }
  }
  return { code, strings };
}

/** `app/tests/fixtures/scores/<ad>` (SPEC_APP §5.3 sentetik skor belgeleri). */
export function scoresDoc<T>(file: string): T {
  return JSON.parse(readFileSync(join(APP_DIR, "tests", "fixtures", "scores", file), "utf-8")) as T;
}

/**
 * Doğruluk paneli görünümü: başlık alanları ve §2.3/§2.5 kararları Rust okuyucusunun ürettiği
 * `scores_views.json`'dan (src-tauri/tests/stage4.rs); belge diskteki kaynak fixture'dır.
 */
export function scoresView(name: string): import("../src/types").ScoresView {
  const all = fx<Record<string, Record<string, unknown> & { doc_file: string | null }>>("scores_views.json");
  const meta = all[name];
  if (!meta) throw new Error(`scores_views.json'da yok: ${name}`);
  const { doc_file: file, ...rest } = meta;
  return { ...rest, doc: file === null ? null : scoresDoc(file) } as import("../src/types").ScoresView;
}

/** Gerçek repo dosyası (salt okuma): `scores/scores.json`. */
export function repoScoresDoc<T>(): T {
  return JSON.parse(readFileSync(join(APP_DIR, "..", "scores", "scores.json"), "utf-8")) as T;
}
