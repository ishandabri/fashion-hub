import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const buildInfo = {
  version: process.env.APP_VERSION ?? "0.1.0",
  revision: process.env.APP_REVISION ?? "dev",
  built_at: process.env.APP_BUILT_AT ?? "development",
};

export default defineConfig({
  define: { __APP_BUILD_INFO__: JSON.stringify(buildInfo) },
  plugins: [react(), VitePWA({ registerType: "prompt", injectRegister: null, manifest: { name: "Store Manager", short_name: "Store", start_url: "/dashboard", display: "standalone", theme_color: "#18181b", background_color: "#fafafa", icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }, { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" }, { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }] }, workbox: { clientsClaim: true, navigateFallback: "/index.html", runtimeCaching: [] } })],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});

