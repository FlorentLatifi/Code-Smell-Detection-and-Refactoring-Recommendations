import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/vite";

// The API runs separately on 8000. Proxying in development keeps the frontend
// free of absolute URLs and of any CORS configuration, which the server does not
// need: it binds to localhost and serves one user.
export default defineConfig({
  // Tailwind-i sherben vetem faqen e dizajnit te `design.html`; aplikacioni qe
  // punon mbetet mbi `src/styles.css` dhe nuk e importon fare (VD-105).
  plugins: [react(), tailwind()],
  build: {
    rollupOptions: {
      input: { main: "index.html", design: "design.html" },
    },
  },
  server: {
    port: 5173,
    // Paneli i rezultateve i importon skedarët e komituar te `data/results/`, të
    // cilët rrinë jashtë kësaj dosjeje. Kopjimi i tyre këtu do të krijonte një
    // burim të dytë të së vërtetës për numra që punimi i raporton.
    fs: { allow: [".."] },
    proxy: { "/api": { target: "http://127.0.0.1:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
  test: {
    // `e2e/` i përket Playwright-it dhe importon API-në e tij; vitest do të
    // provonte ta mblidhte dhe do të dështonte pa e ekzekutuar asnjë test.
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});
