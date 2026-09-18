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
 * Një kalim i vetëm mbi mjetin e vërtetë, ashtu si i dërgohet përdoruesit.
 *
 * Testet e tjera e ndalojnë `fetch` dhe kontrollojnë ndërfaqen veç; testet e
 * backend-it e kontrollojnë API-në veç. Asnjëra anë nuk e kap një mospërputhje mes
 * të dyjave — një fushë e riemërtuar te përgjigjja kalon të dyja suitat dhe prish
 * ekranin. Kjo është e vetmja gjë që kjo suitë mbulon dhe që tjetrat nuk e mbulojnë
 * dot, ndaj ajo mbetet e vogël me qëllim.
 *
 * Serveri është paketa, jo dy shërbimet e zhvillimit: ndërfaqja e ndërtuar dhe
 * API-ja nga një proces i vetëm, te `/` dhe `/api` (VD-127). Kështu provohet
 * rruga që përdor nisësi, dhe një prefiks që ndërfaqja dhe serveri e shkruajnë
 * ndryshe del këtu e jo te përdoruesi.
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
  webServer: {
    // Ndërtimi para nisjes: ajo që provohet duhet të jetë ajo që dërgohet, dhe
    // ndërtimi është hapi ku një gabim tipesh do të dilte.
    command: `npm --prefix ../frontend run build && "${PYTHON}" -m uvicorn javasmell.api.bundle:create_bundle --factory --host 127.0.0.1 --port 4173`,
    cwd: "../backend",
    env: {
      JAVASMELL_ROOT: "..",
      // Dosja e depove të importuara tregohet te një shteg që nuk ekziston, që
      // rrënja të jetë e vetme sido që të jetë makina. Pa këtë, një checkout
      // ku dikush kishte importuar një depo hapte listën e rrënjëve në vend që
      // të hynte drejt brenda, dhe testet e zgjedhjes dështonin për arsye që
      // nuk i përkasin kodit (VD-126).
      JAVASMELL_PROJECTS: "../data/projects-e2e",
    },
    url: "http://127.0.0.1:4173/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
