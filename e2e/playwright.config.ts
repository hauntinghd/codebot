import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],
  use: {
    headless: process.env.PLAYWRIGHT_HEADLESS !== '0',
    viewport: { width: 1280, height: 800 },
    actionTimeout: 0,
    ignoreHTTPSErrors: true,
    baseURL: process.env.BASE_URL || 'http://localhost:4173/codebot',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
