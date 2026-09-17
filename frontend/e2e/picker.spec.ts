import { expect, test } from "@playwright/test";

/**
 * Zgjedhja e projektit pa shkruar shteg, mbi serverin e vërtetë.
 *
 * Testet e njësive e provojnë dialogun mbi përgjigje të ndaluara, dhe testet e
 * backend-it provojnë `/browse` veç. Asnjëra anë nuk e kap mospërputhjen mes të
 * dyjave: një fushë e riemërtuar te lista e dosjeve kalon të dyja suitat dhe e
 * lë dialogun bosh. Këtu klikohet nga rrënja te fikstuarat, që është e njëjta
 * pemë Java që ekziston në çdo checkout.
 *
 * Importi nga GitHub provohet vetëm në drejtimin që nuk kërkon rrjet: një lidhje
 * që nuk është depo publike refuzohet nga serveri para se ai të kërkojë gjë.
 * Një test që varet nga GitHub-u do ta bënte suitën të dështonte për arsye që
 * nuk i përkasin kodit.
 */

test("zgjedh dosjen me klikime dhe e analizon", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Zgjidh një projekt Java" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Rrënja është ajo me të cilën u nis serveri; brenda saj klikohet deri te
  // fikstuarat, pa shkruar asnjë shteg.
  for (const folder of ["backend", "tests", "fixtures"]) {
    await dialog.getByRole("button", { name: new RegExp(`^${folder}`) }).click();
  }
  await dialog.getByRole("button", { name: "Analizo këtë dosje" }).click();

  // Analiza niset vetë pas zgjedhjes: dy skedarë, si te suita e backend-it.
  await expect(page.getByRole("banner")).toContainText("2 skedarë");
  await expect(page.locator("button.row").first()).toBeVisible();
  // Shtegu i zgjedhur hyn te kutia, që rifreskimi dhe linku të mbajnë të njëjtën.
  await expect(page.getByLabel("Shtegu i projektit")).toHaveValue(/fixtures$/);
});

test("dosja pa kod Java shënohet para se dikush ta zgjedhë", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Zgjidh një projekt Java" }).click();

  const dialog = page.getByRole("dialog");
  // `docs/` mban punimin dhe asnjë skedar Java; `backend/` mban kodin.
  await expect(dialog.getByRole("button", { name: /^backend/ })).toContainText("Java");
  await expect(dialog.getByRole("button", { name: /^docs/ })).toContainText("pa Java");
});

test("një lidhje që nuk është depo publike refuzohet shqip", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Zgjidh një projekt Java" }).click();

  const dialog = page.getByRole("dialog");
  await dialog.getByRole("tab", { name: /Nga GitHub/ }).click();
  await dialog.getByLabel("Lidhja e një depoje publike").fill("https://gitlab.com/a/b");
  await dialog.getByRole("button", { name: /Shkarko dhe analizo/ }).click();

  // Kodi vjen nga serveri, fjalia nga ndërfaqja: kjo e provon lidhjen mes tyre.
  await expect(dialog.getByRole("alert")).toContainText("vetëm depo nga github.com");
});
