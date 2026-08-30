import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API runs separately on 8000. Proxying in development keeps the frontend
// free of absolute URLs and of any CORS configuration, which the server does not
// need: it binds to localhost and serves one user.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
