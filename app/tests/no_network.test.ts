// U34 (vitest tarafı, SPEC_APP §5.5): ön uç ağ bağımlılığı yok; CSP connect-src yalnız IPC.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf-8");

describe("ağ yok (U34)", () => {
  it("package-lock.json'da axios / node-fetch / plugin-http yok", () => {
    const lock = JSON.parse(read("../package-lock.json")) as { packages: Record<string, unknown> };
    const names = Object.keys(lock.packages);
    for (const bad of ["axios", "node-fetch", "@tauri-apps/plugin-http"]) {
      expect(names.some((n) => n === `node_modules/${bad}` || n.endsWith(`/node_modules/${bad}`))).toBe(false);
    }
  });

  it("package.json çalışma zamanı bağımlılıkları yalnız Tauri api + dialog", () => {
    const pkg = JSON.parse(read("../package.json")) as { dependencies: Record<string, string> };
    expect(Object.keys(pkg.dependencies).sort()).toEqual(["@tauri-apps/api", "@tauri-apps/plugin-dialog"]);
  });

  it("tauri.conf.json CSP connect-src 'self' ipc: http://ipc.localhost dışına izin vermez", () => {
    const conf = JSON.parse(read("../src-tauri/tauri.conf.json")) as { app: { security: { csp: string } } };
    const directives = conf.app.security.csp.split(";").map((d) => d.trim());
    expect(directives).toContain("connect-src 'self' ipc: http://ipc.localhost");
    expect(directives).toContain("default-src 'self'");
  });
});
