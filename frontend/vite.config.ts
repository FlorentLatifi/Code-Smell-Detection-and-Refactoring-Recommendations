import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/vite";

// The API runs separately on 8000. Proxying in development keeps the frontend
// free of absolute URLs and of any CORS configuration, which the server does not
// need: it binds to localhost and serves one user.
// Ndërfaqja ka një buton që shkruan në disk, ndaj asnjë faqe tjetër nuk guxon
// ta mbështjellë në iframe dhe ta mashtrojë klikimin (clickjacking). Të njëjtat
// koka i vendos API-ja te përgjigjet e veta (VD-127).
const SECURITY_HEADERS = {
  "X-Frame-Options": "DENY",
  "Content-Security-Policy": "frame-ancestors 'none'",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};

export default defineConfig({
  plugins: [react(), tailwind()],
  preview: { headers: SECURITY_HEADERS },
  server: {
    port: 5173,
    headers: SECURITY_HEADERS,
    // Paneli i rezultateve i importon skedarët e komituar te `data/results/`, të
    // cilët rrinë jashtë kësaj dosjeje. Kopjimi i tyre këtu do të krijonte një
    // burim të dytë të së vërtetës për numra që punimi i raporton.
    fs: { allow: [".."] },
    proxy: { "/api": { target: "http://127.0.0.1:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
  test: {
    setupFiles: ["src/test-setup.ts"],
    // `e2e/` i përket Playwright-it dhe importon API-në e tij; vitest do të
    // provonte ta mblidhte dhe do të dështonte pa e ekzekutuar asnjë test.
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});
