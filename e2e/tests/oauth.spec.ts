import { test, expect } from '@playwright/test';

// E2E test that uses the DEV test-login helper (POST /__dev__/test-login)
// when no real OAuth credentials are provided. This avoids interacting with
// external providers during CI and allows quick smoke tests.

const EMAIL = process.env.E2E_OAUTH_EMAIL || 'e2e+test@example.com';

test.describe('Dev-login E2E', () => {
  test('sets session via dev endpoint and loads chat UI', async ({ page, baseURL }) => {
    // Call dev endpoint to create a test user and set a session cookie
    const BACKEND = process.env.BACKEND_BASE || 'http://127.0.0.1:8080';
    const devLoginUrl = `${BACKEND}/__dev__/test-login`;

    const resp = await page.request.post(devLoginUrl, { data: { email: EMAIL } });
    if (resp.status() !== 200) {
      throw new Error(`Dev test-login failed with status ${resp.status()}: ${await resp.text()}`);
    }

    // Extract set-cookie header and set it in the browser context so subsequent
    // navigation is authenticated.
    const sc = resp.headers()['set-cookie'];
    if (!sc) {
      throw new Error('Dev login did not return Set-Cookie header');
    }

    // Parse cookie name=value from header (first part before ';')
    const cookiePair = sc.split(';')[0];
    const eq = cookiePair.indexOf('=');
    const name = cookiePair.slice(0, eq);
    const value = cookiePair.slice(eq + 1);
    await page.context().addCookies([{ name, value, domain: new URL(BACKEND).hostname, path: '/', httpOnly: true, secure: false }]);

    // Now navigate to the chat page served by the backend (serves built SPA at /codebot)
    await page.goto(`${BACKEND}/codebot/chat`);
    // Wait for the chat root element
    await page.waitForSelector('#root, [data-testid="chat-root"]', { timeout: 10000 }).catch(() => {});

    // The app sets `codebot_user` in localStorage after fetching /api/me — assert that.
    await page.waitForFunction(() => !!localStorage.getItem('codebot_user'), { timeout: 20000 });
    const stored = await page.evaluate(() => localStorage.getItem('codebot_user'));
    const parsed = stored ? JSON.parse(stored) : null;
    if (!parsed || parsed.email !== EMAIL) {
      throw new Error('Logged-in user not found in localStorage');
    }
  });
});
