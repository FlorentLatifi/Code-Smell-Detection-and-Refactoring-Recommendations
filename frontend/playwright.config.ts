import { existsSync } from "node:fs";

import { defineConfig, devices } from "@playwright/test";

/**
 * Python-i i mjedisit lokal, ose ai i PATH-it.
 *
 * Një checkout lokal e mban te `.venv`; CI-ja e instalon me `setup-python` dhe e
 * lë te PATH-i. Shkrimi i njërit prej të dyve do ta bënte suitën të ekzekutueshme
 * vetëm në njërin vend. Shtegu është i njëjti nga `frontend` dhe nga `backend`,
 * sepse të dyja janë motra nën rrënjën e depos.
 */
const PYTHON =
  ["../.venv/Scripts/python.exe", "../.venv/bin/python"].find((p) => existsSync(p)) ?? "python";

/**
 * Një kalim i vetëm mbi mjetin e vërtetë, me të dy shërbimet e ndezura.
 *
 * Testet e tjera e ndalojnë `fetch` dhe kontrollojnë ndërfaqen veç; testet e
 * backend-it e kontrollojnë API-në veç. Asnjëra anë nuk e kap një mospërputhje mes
 * të dyjave — një fushë e riemërtuar te përgjigjja kalon të dyja suitat dhe prish
 * ekranin. Kjo është e vetmja gjë që kjo suitë mbulon dhe që tjetrat nuk e mbulojnë
 * dot, ndaj ajo mbetet e vogël me qëllim.
 *
 * `JAVASMELL_ROOT` tregon te rrënja e depos, që testi të analizojë fikstuarat e
 * backend-it: ato janë e vetmja pemë Java që ekziston në çdo checkout.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  // Analiza është punë e vërtetë mbi skedarë të vërtetë, jo një përgjigje e ndalur.
  timeout: 60_000,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${PYTHON}" -m uvicorn javasmell.api.app:create_app --factory --port 8000`,
      cwd: "../backend",
      env: { JAVASMELL_ROOT: ".." },
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      // `preview` mbi ndërtimin, jo `dev`: ajo që provohet duhet të jetë ajo që
      // dërgohet, dhe ndërtimi është hapi ku një gabim tipesh do të dilte.
      // `--host 127.0.0.1`: pa te, vite lidhet te `localhost`, i cili mund të
      // zgjidhet si IPv6 ndërsa Playwright pret te 127.0.0.1.
      command: "npm run build && npm run preview -- --port 4173 --strictPort --host 127.0.0.1",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
