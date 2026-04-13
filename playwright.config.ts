import { defineConfig, devices } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const authStatePath = path.join(process.cwd(), ".auth", "user.json");
const useAuthState = process.env.PLAYWRIGHT_AUTH_STATE === "1" && fs.existsSync(authStatePath);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.CODEBOT_BASE_URL || "https://chatbot.nyptidindustries.com/codebot",
    trace: "on-first-retry",
    headless: process.env.HEADLESS === "1",
    viewport: { width: 1280, height: 720 },
    actionTimeout: 30_000,
    navigationTimeout: 25_000,
    ...(useAuthState ? { storageState: authStatePath } : {}),
  },
  projects: [
    // auth-setup: use headless when no display (HEADLESS=1 or CI) so browser doesn't require X server
    { name: "auth-setup", testMatch: /auth-setup\.spec\.ts/, use: { ...devices["Desktop Chrome"], headless: process.env.HEADLESS === "1" || !!process.env.CI } },
    { name: "chromium", testIgnore: /auth-setup\.spec\.ts/, use: { ...devices["Desktop Chrome"] } },
  ],
  timeout: 300_000,
});
