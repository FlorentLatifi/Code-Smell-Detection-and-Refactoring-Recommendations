/**
 * Pamjet e ndërfaqes për Nënkapitullin 4.8, të nxjerra nga aplikacioni i ndezur.
 *
 * Mentorja kërkoi më 15 tetor 2026 pamje nga ndërfaqja, që kontributi praktik të
 * shihet e jo vetëm të përshkruhet. Ato nxirren me skript, si figurat e tjera, që
 * një ndryshim i ndërfaqes të mos lërë në punim një pamje që nuk ekziston më.
 *
 * Kërkon paketën e ndezur (`javasmell.api.bundle`) te porti 4173, me
 * JAVASMELL_ROOT që përmban dosjen e projektit të analizuar, dhe Playwright-in e
 * ndërfaqes:
 *
 *     NODE_PATH=frontend/node_modules node docs/thesis/capture_screens.cjs [projekti] [dosja]
 *
 * Tema është e çelëta, sepse punimi shtypet. Mënyra është e thjeshta, ajo që sheh
 * një vizitor i ri, përveç pamjes së rishkrimit, ku diff-i lexohet më mirë teknik.
 */

const path = require("node:path");
const { chromium } = require("@playwright/test");

const BASE = process.env.JAVASMELL_URL ?? "http://127.0.0.1:4173";
const PROJECT = process.argv[2] ?? "jsoup";
const OUT = process.argv[3] ?? path.join(__dirname, "figures");

async function open(browser, mode) {
  const context = await browser.newContext({
    viewport: { width: mode === "technical" ? 1920 : 1440, height: 900 },
    deviceScaleFactor: 2,
    storageState: {
      cookies: [],
      origins: [
        {
          origin: BASE,
          localStorage: [
            { name: "javasmell.theme", value: "light" },
            { name: "javasmell.mode", value: mode },
          ],
        },
      ],
    },
  });
  const page = await context.newPage();
  await page.goto(`${BASE}/?path=${encodeURIComponent(PROJECT)}`);
  await page.getByRole("button", { name: "Analizo", exact: true }).click();
  await page.getByRole("img", { name: /erëra gjithsej|probleme gjithsej/ }).first().waitFor({ timeout: 120_000 }).catch(() => {});
  await page.waitForLoadState("networkidle");
  return { context, page };
}

async function main() {
  const browser = await chromium.launch();

  // 1. Paneli i analizës, në mënyrën e thjeshtë.
  {
    const { context, page } = await open(browser, "simple");
    await page.screenshot({ path: path.join(OUT, "nderfaqja_paneli.png"), fullPage: false });
    await context.close();
  }

  // 2. Rishkrimi i propozuar për gjetjen e parë që motori e ndreq vetë.
  {
    const { context, page } = await open(browser, "technical");
    await page.getByRole("button", { name: "Shfaq diff-in" }).first().click();
    // Jo çdo vend me transformim të automatizuar rishkruhet: motori refuzon kur një
    // parakusht nuk provohet. Merret gjetja e parë sipas renditjes së listës për të
    // cilën ai prodhon një diff, që pamja të tregojë një rishkrim të vërtetë.
    const diff = page.locator(".diff").first();
    const rows = page.locator("button.row");
    let found = false;
    for (let index = 0; index < (await rows.count()) && !found; index += 1) {
      await rows.nth(index).click();
      const ask = page.getByRole("button", { name: "Shfaq ndryshimin e propozuar" });
      if (!(await ask.count())) continue;
      await ask.click();
      await page.waitForFunction(
        () => !document.querySelector("article button.primary[disabled]"),
        null,
        { timeout: 120_000 },
      );
      found = (await diff.count()) > 0;
    }
    if (!found) throw new Error("asnjë gjetje e listës nuk dha diff");
    // Vetëm blloku i diff-it, me titullin «Ndryshimi i propozuar» dhe shënimin se asnjë
    // skedar nuk është prekur. Emri i metodës shtypet, që përshkrimi i figurës ta thotë.
    const where = await page.locator("article").first().locator("h2 + *").first().innerText();
    console.log(`rishkrimi: ${where.trim()}`);
    await page.waitForTimeout(500);
    await diff.screenshot({ path: path.join(OUT, "nderfaqja_rishkrimi.png") });
    await context.close();
  }

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
