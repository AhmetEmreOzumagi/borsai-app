// Sade görünümün statik denetimleri (FAZ9_APP_UI): U19, U21, U25 ve U34 taramaları yeni dosyaları da kapsar; yazı tipleri
// yerel paketten (ağ yok, K-UI-9); eski ekran ve render dosyalarına sade bağımlılığı yok (K-UI-2).
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, sep } from "node:path";
import { describe, expect, it } from "vitest";

import { APP_DIR, split } from "./helpers";

const SRC = join(APP_DIR, "src");
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((n) => {
    const p = join(d, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
// Windows'ta ayırıcı '\\'; izin listeleri '/' ile yazılı (FAZ9_WINDOWS: yalnız ayırıcı, iddia aynı)
const rel = (p: string) => p.slice(SRC.length + 1).split(sep).join("/");

describe("sade dosyaları taramalarda", () => {
  const files = walk(SRC).filter((p) => p.endsWith(".ts")).map(rel);

  it("no_frontend_math (U25) ve U19 / U21 yürüyüşleri src/sade/**'ı görür", () => {
    const sade = files.filter((f) => f.startsWith("sade/"));
    expect(sade).toEqual(expect.arrayContaining(["sade/app.ts", "sade/render/monitor.ts", "sade/render/calc.ts", "sade/screens/analiz.ts"]));
    expect(sade.length).toBeGreaterThanOrEqual(20);
  });

  it("sade kodunda çarpma, bölme, mod ve üs yok; Türkçe serbest metin yok (tr.ts dışında)", () => {
    const op = /[^/*]\s*[*/%]\s*[^/*=]/;
    const tr = /[çğıöşüÇĞİÖŞÜ]/;
    for (const f of files.filter((x) => x.startsWith("sade/"))) {
      const { code, strings } = split(readFileSync(join(SRC, f), "utf-8"));
      expect(code.split("\n").filter((l) => op.test(l) && !/^\s*import /.test(l)), f).toEqual([]);
      expect(strings.filter((s) => tr.test(s)), f).toEqual([]);
      expect(/\*\*|\.reduce\s*\(|Math\.(exp|log|pow|sqrt)/.test(code), f).toBe(false);
    }
  });

  it("eski ekran ve render dosyaları sade koduna bağlanmaz (yalnız main.ts yönlendirir)", () => {
    for (const f of files.filter((x) => x.startsWith("screens/") || x.startsWith("render/"))) {
      expect(readFileSync(join(SRC, f), "utf-8").includes("/sade/"), f).toBe(false);
    }
    expect(readFileSync(join(SRC, "main.ts"), "utf-8")).toContain("./sade/app");
  });
});

describe("yazı tipleri ve ağ (K-UI-9, U34)", () => {
  const pkg = JSON.parse(readFileSync(join(APP_DIR, "package.json"), "utf-8")) as {
    dependencies: Record<string, string>;
    devDependencies: Record<string, string>;
  };

  it("üç @fontsource paketi yalnız devDependencies'te; çalışma zamanı bağımlılıkları değişmedi", () => {
    for (const p of ["@fontsource/ibm-plex-sans", "@fontsource/ibm-plex-sans-condensed", "@fontsource/ibm-plex-mono"]) {
      expect(pkg.devDependencies[p], p).toBeDefined();
      expect(pkg.dependencies[p], p).toBeUndefined();
    }
    expect(Object.keys(pkg.dependencies).sort()).toEqual(["@tauri-apps/api", "@tauri-apps/plugin-dialog"]);
  });

  it("fonts.ts yalnız yerel paket dosyalarını içe aktarır (OFL lisansı); CSS'te uzak URL yok", () => {
    const fonts = readFileSync(join(SRC, "sade", "fonts.ts"), "utf-8");
    const imports = [...fonts.matchAll(/^import "([^"]+)";$/gm)].map((m) => m[1]);
    expect(imports.length).toBe(18);
    for (const i of imports) {
      expect(i.startsWith("@fontsource/"), i).toBe(true);
      expect(existsSync(join(APP_DIR, "node_modules", i)), i).toBe(true);
    }
    for (const p of ["ibm-plex-sans", "ibm-plex-sans-condensed", "ibm-plex-mono"]) {
      const lic = JSON.parse(readFileSync(join(APP_DIR, "node_modules", "@fontsource", p, "package.json"), "utf-8")) as { license: string };
      expect(lic.license, p).toBe("OFL-1.1");
    }
    const css = readFileSync(join(SRC, "sade", "sade.css"), "utf-8");
    expect(/https?:\/\//.test(css)).toBe(false);
    expect(/@import/.test(css)).toBe(false);
    expect(/https?:\/\//.test(readFileSync(join(APP_DIR, "index.html"), "utf-8"))).toBe(false);
  });

  it("hareket yalnız CSS ve prefers-reduced-motion destekli (K-UI-10)", () => {
    const css = readFileSync(join(SRC, "sade", "sade.css"), "utf-8");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    for (const f of walk(join(SRC, "sade")).filter((p) => p.endsWith(".ts"))) {
      const { code } = split(readFileSync(f, "utf-8"));
      expect(/requestAnimationFrame|\.animate\s*\(/.test(code), f).toBe(false);
    }
  });
});
