# E2E Tests

## No display (CI / headless server)

On a server or VM **without an X server** (no graphical display), Playwright must run in headless mode or the browser will fail to launch with "Missing X server or $DISPLAY". Run:

```bash
HEADLESS=1 npx playwright test e2e/builder-live.spec.ts --project=chromium
```

To use a saved auth state on that server, run the auth-setup once **on a machine that has a display** (or use `xvfb-run`), then copy `.auth/user.json` to the server and run with `PLAYWRIGHT_AUTH_STATE=1` as below.

## Builder flow (with auth)

1. **Save auth state once** — must run in **headed** mode so you can complete Google sign-in. On a headless server, auth-setup will save an empty state and builder E2E will time out on `builder-prompt`.
   ```bash
   npx playwright test e2e/auth-setup.spec.ts --project=auth-setup
   ```
   Then copy `.auth/user.json` to CI/headless machines if needed.
2. **Run builder E2E using saved session**:
   ```bash
   PLAYWRIGHT_AUTH_STATE=1 npx playwright test e2e/builder-live.spec.ts --project=chromium
   ```

## Without auth

If you run `e2e/builder-live.spec.ts` without `PLAYWRIGHT_AUTH_STATE=1`, the test will hit the login redirect and may time out waiting for the builder prompt. Use the auth setup above for reliable runs.

## Base URL

Set `CODEBOT_BASE_URL` to point at your app (default: `https://chatbot.nyptidindustries.com/codebot`). Use `HEADLESS=1` for headless runs.
