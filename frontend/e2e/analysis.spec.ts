import { expect, test } from "@playwright/test";

/**
 * Rruga e vërtetë, nga shtegu te kodi i shfaqur.
 *
 * Gjithçka këtu kalon nëpër API-në e ndezur mbi skedarë të vërtetë. Asgjë nuk
 * ndalohet dhe asgjë nuk trillohet, sepse e vetmja arsye që kjo suitë ekziston
 * është të kapë atë që dy suitat e tjera nuk e kapin dot: mospërputhjen mes asaj
 * që serveri dërgon dhe asaj që ndërfaqja pret.
 *
 * Shtegu `backend/tests/fixtures` është pema e vetme Java që ekziston në çdo
 * checkout, dhe përmbajtja e saj është e fiksuar nga testet e backend-it.
 */

const FIXTURES = "backend/tests/fixtures";

test("analizon një projekt dhe hap kodin e një gjetjeje", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Shtegu i projektit").fill(FIXTURES);
  await page.getByRole("button", { name: "Analizo", exact: true }).click();

  // Shifrat vijnë nga serveri, jo nga ndërfaqja. Rreshti i kontekstit i mban:
  // fikstuarat janë dy skedarë dhe pesë klasa, të fiksuara nga testet e backend-it.
  await expect(page.locator(".context")).toContainText("2");
  await expect(page.locator(".context")).toContainText("skedarë");
  // Unaza e përmbledhjes e përshkruan veten, ndaj totali lexohet pa pikselë.
  await expect(page.locator(".donut svg")).toHaveAttribute("aria-label", /erëra/);

  const rows = page.locator("button.row");
  await expect(rows.first()).toBeVisible();
  expect(await rows.count()).toBeGreaterThan(0);

  await rows.first().click();

  // Kodi vjen nga `/source`: nëse ai kontrat thyhet, këtu duket.
  await expect(page.locator("pre.source .line").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pse u shënua" })).toBeVisible();
});

test("e thotë shqip kur shtegu nuk ekziston", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Shtegu i projektit").fill("nuk/ekziston/fare");
  await page.getByRole("button", { name: "Analizo", exact: true }).click();

  // Kodi vjen nga serveri, fjalia nga ndërfaqja: kjo e provon lidhjen mes tyre.
  await expect(page.getByRole("alert")).toContainText("Nuk ka asgjë te ky shteg");
});

test("e mban shtegun te adresa, që linku të hapë atë që premton", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Shtegu i projektit").fill(FIXTURES);
  await page.getByRole("button", { name: "Analizo", exact: true }).click();
  await expect(page.locator("button.row").first()).toBeVisible();

  expect(page.url()).toContain("path=backend%2Ftests%2Ffixtures");

  // Rifreskimi duhet ta rihapë të njëjtin shteg, jo një ekran bosh.
  await page.reload();
  await expect(page.getByLabel("Shtegu i projektit")).toHaveValue(FIXTURES);
});

test("kalon mes pamjeve dhe shfaq rezultatet e vlerësimit", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("tab", { name: /Rezultatet/ }).click();

  await expect(page.getByRole("heading", { name: /Qasja A kundrejt Qasjes B/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Rezultatet/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("i lë filtrat të përdorshëm me tastierë", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Shtegu i projektit").fill(FIXTURES);
  await page.getByRole("button", { name: "Analizo", exact: true }).click();
  await expect(page.locator("button.row").first()).toBeVisible();

  // Defekti që auditimi gjeti: shigjeta mbi filtrin e vidhte fokusin dhe e çonte
  // te lista, ndaj kontrolli nuk përdorej dot fare me tastierë.
  //
  // Matet fokusi, jo vlera. Shigjeta mbi një `select` të mbyllur nuk e ndryshon
  // vlerën te një shfletues headless — kjo është sjellje e sistemit operativ, jo e
  // faqes — ndaj një pohim mbi vlerën do të maste shfletuesin e jo defektin.
  // "Ashpërsia" përputhet edhe me "Radhitur sipas: ashpërsia", ndaj zgjidhet i pari
  // te grupi i filtrave.
  const severity = page.locator(".filters select").first();
  await severity.focus();
  await severity.press("ArrowDown");

  await expect(severity).toBeFocused();

  // Dhe shigjeta mbi një rresht duhet të vazhdojë ta lëvizë përzgjedhjen.
  const rows = page.locator("button.row");
  await rows.first().focus();
  await rows.first().press("ArrowDown");

  await expect(page.locator("button.row.selected")).toHaveCount(1);
});
