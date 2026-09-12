import axe from "axe-core";
import { expect, test, type Page } from "@playwright/test";

/**
 * Aksesueshmëria e matur mbi një shfletues të vërtetë.
 *
 * Suita me jsdom e ndalon `color-contrast`, sepse jsdom nuk llogarit ngjyra të
 * trashëguara dhe një mjet që pretendon më shumë se sa mat është më keq se asnjë
 * mjet. Kjo do të thoshte se kontrasti mbetej i pakontrolluar nga çdo portë, dhe
 * pikërisht aty u gjetën tridhjetë e dy shkelje pas ndërrimit të paletës: teksti
 * i vogël gri mbi kartë, etiketat e ashpërsisë mbi tintën e vet, ikona e rreshtit
 * anësor (VD-108).
 *
 * Këtu asnjë rregull nuk ndalohet. Chromium-i i jep axe-it ngjyrat e llogaritura,
 * ndaj kontrasti matet vërtet, dhe të dyja temat kontrollohen: ato kanë palete të
 * ndryshme dhe një prej tyre mund të bjerë vetëm.
 */

declare global {
  interface Window {
    axe: typeof axe;
  }
}

const FIXTURES = "backend/tests/fixtures";

/** Vetëm shkeljet, me nyjën e parë si provë se cila është. */
async function violations(page: Page): Promise<string[]> {
  await page.evaluate(axe.source);
  return page.evaluate(async () => {
    const result = await window.axe.run(document, { resultTypes: ["violations"] });
    return result.violations.map(
      (v) => `${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0]?.html.slice(0, 90)}`,
    );
  });
}

async function analyse(page: Page): Promise<void> {
  await page.getByLabel("Shtegu i projektit").fill(FIXTURES);
  await page.getByRole("button", { name: "Analizo", exact: true }).click();
  await expect(page.locator("button.row").first()).toBeVisible();
}

test("ekrani i parë nuk ka shkelje", async ({ page }) => {
  await page.goto("/");

  expect(await violations(page)).toEqual([]);
});

test("paneli me gjetje nuk ka shkelje në asnjërën temë", async ({ page }) => {
  await page.goto("/");
  await analyse(page);
  await page.locator("button.row").first().click();
  await expect(page.locator("pre.source .line").first()).toBeVisible();

  expect(await violations(page)).toEqual([]);

  await page.getByRole("button", { name: /tema e çelët/ }).click();
  await expect(page.getByRole("button", { name: /tema e errët/ })).toBeVisible();

  expect(await violations(page)).toEqual([]);
});

test("patch-i dhe diff-i nuk kanë shkelje", async ({ page }) => {
  await page.goto("/");
  await analyse(page);

  // Dy blloqet që rrëshqasin horizontalisht janë vetëm këtu, dhe pikërisht ato
  // ishin të paarritshme me tastierë derisa u matën (VD-108).
  await page.getByRole("button", { name: /Përgatit patch-in/ }).click();
  await expect(page.locator("pre.unified").first()).toBeVisible({ timeout: 30_000 });

  expect(await violations(page)).toEqual([]);
});

test("pamja e vlerësimit nuk ka shkelje", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Rezultatet/ }).click();
  await expect(page.getByRole("heading", { name: /Qasja A kundrejt Qasjes B/ })).toBeVisible();

  expect(await violations(page)).toEqual([]);
});
