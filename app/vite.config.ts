import { defineConfig } from "vite";
// @ts-expect-error type error without @types/node package
import process from "node:process";
const host = process.env.TAURI_DEV_HOST;
// Ekran görüntüsü koşusu (app/scripts/screens.sh): dosya seçici yerel bir modaldır, demo ona
// tıklayamaz. YALNIZ bu koşuda dialog modülü src/dev/dialog-demo.ts ile değiştirilir; üretim ve
// normal `npm run tauri dev` derlemesinde bu takma ad yoktur.
const demo = process.env.VITE_BORSAI_DEMO === "1";

// Tauri geliştirme ayarları: sabit port, Rust hatalarını gizleme, src-tauri'yi izleme.
export default defineConfig(() => ({
  clearScreen: false,
  resolve: {
    alias: demo ? [{ find: /^@tauri-apps\/plugin-dialog$/, replacement: "/src/dev/dialog-demo.ts" }] : [],
  },
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
}));
