/**
 * One-time auth setup: run in headed mode, log in manually, then storage state is saved.
 * Usage: npx playwright test e2e/auth-setup.spec.ts --project=auth-setup
 * Then run builder E2E with: PLAYWRIGHT_AUTH_STATE=1 npx playwright test e2e/builder-live.spec.ts
 */
import { test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const AUTH_STATE_PATH = path.join(process.cwd(), ".auth", "user.json");
const LOGIN_URL = "/login";
const BUILDER_OR_DASHBOARD = /\/(builder|dashboard|account|codebot)(\/|$)/;

test.describe("Auth setup", () => {
  test("save auth state after manual login", async ({ page }) => {
    await page.goto(LOGIN_URL);
    // Wait for user to complete login and land on builder/dashboard (up to 2 min)
    await page.waitForURL(BUILDER_OR_DASHBOARD, { timeout: 120_000 });
    const dir = path.dirname(AUTH_STATE_PATH);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    await page.context().storageState({ path: AUTH_STATE_PATH });
  });
});
