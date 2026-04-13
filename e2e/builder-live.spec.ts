import { test, expect } from "@playwright/test";

const BUILDER_URL = "/builder";
const LOGIN_URL = "/login";
const E2E_WAIT_FOR_LOGIN_MS = 90_000;

test("live builder pipeline: prompt -> build -> multiple files", async ({ page }) => {
  await page.goto(BUILDER_URL);

  const url = page.url();
  if (url.includes(LOGIN_URL) || url.includes("oauth")) {
    await page.getByRole("button", { name: /sign in with google/i }).click().catch(() => {});
    await page.waitForTimeout(E2E_WAIT_FOR_LOGIN_MS);
    await page.goto(BUILDER_URL);
  }

  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(3000); // allow AuthGate to finish (redirect or show builder)

  // If we're still on login or "Authenticating…", saved auth state is empty — builder-prompt never appears
  const onLogin = page.url().includes(LOGIN_URL) || page.url().includes("oauth");
  const authScreen = page.getByText(/Authenticating…|Sign in with Google/i);
  const stillAuthBlocked = onLogin || (await authScreen.isVisible().catch(() => false));
  if (stillAuthBlocked) {
    throw new Error(
      "Builder requires login but saved auth state is empty. Run auth-setup in HEADED mode and complete sign-in, then copy .auth/user.json and run with PLAYWRIGHT_AUTH_STATE=1. See e2e/README.md."
    );
  }

  const prompt = "Build a luxury handbag e-commerce site with home, products, contact, and terms pages. Professional styling.";
  const textarea = page.getByTestId("builder-prompt");
  await textarea.waitFor({ state: "visible", timeout: 15_000 });
  await textarea.fill(prompt);

  const buildBtn = page.getByTestId("builder-build-now");
  await buildBtn.click();

  await page.waitForSelector('text=/Project Generated|files created|Your project is ready/i', { timeout: 180_000 });

  await page.waitForTimeout(3000);

  const codeTab = page.getByRole("tab", { name: /code/i }).first();
  await codeTab.click().catch(() => {});
  await page.waitForTimeout(2000);

  const body = await page.locator("body").textContent();
  const hasIndex = body?.includes("index.html") ?? false;
  const hasStyles = body?.includes("styles.css") ?? false;
  const hasAppJs = body?.includes("app.js") ?? false;
  const hasExtraPage = (body?.includes("products.html") || body?.includes("contact.html")) ?? false;

  expect(hasIndex, "expected index.html in output").toBe(true);
  expect(hasStyles, "expected styles.css in output").toBe(true);
  expect(hasAppJs, "expected app.js in output").toBe(true);
  expect(hasExtraPage, "expected at least one of products.html or contact.html").toBe(true);
});
