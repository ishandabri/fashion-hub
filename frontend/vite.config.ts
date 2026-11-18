import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [react(), VitePWA({ registerType: "autoUpdate", manifest: { name: "Store Manager", short_name: "Store", display: "standalone", theme_color: "#18181b", background_color: "#fafafa", icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }, { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" }, { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }] }, workbox: { navigateFallback: "/index.html", runtimeCaching: [] } })],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});

