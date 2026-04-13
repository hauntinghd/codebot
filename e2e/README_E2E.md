E2E Playwright test scaffold

Purpose
- Provide a safe, repeatable way to run an end-to-end browser test for login/OAuth flows.
- This scaffold intentionally does NOT include hard-coded credentials. Provide credentials via environment variables.

Setup
1. Install dev dependency (from repository root):

```bash
cd frontend || cd .
# from repo root: install Playwright dev tooling
npm install -D @playwright/test
npx playwright install --with-deps
```

2. Create `.env.e2e` in the `e2e/` folder by copying the sample and adding credentials (DO NOT commit this file):

```bash
cp e2e/.env.e2e.sample e2e/.env.e2e
# edit e2e/.env.e2e and set E2E_OAUTH_EMAIL and E2E_OAUTH_PASSWORD
```

Running the tests

From the repo root run:

```bash
# load environment from file, then run Playwright tests
export $(grep -v '^#' e2e/.env.e2e | xargs) || true
npx playwright test --config=e2e/playwright.config.ts
```

Notes & recommendations
- If your app uses third-party OAuth providers (Google), automated login to those providers is often blocked or rate-limited. For robust E2E testing consider:
  - Creating a test-only OAuth client and using test accounts.
  - Bypassing provider UI by creating a test session/token via backend APIs and setting the cookie in Playwright before navigating to the app.
  - Using headful/manual verification for provider consent once, then capturing a refreshable token for automated tests.

- Update selectors in `e2e/tests/oauth.spec.ts` to match your login page's DOM. The test currently assumes a simple `input[name="email"]` + `input[name="password"]` flow.

- Never paste production admin credentials into chat or into committed files. Use ephemeral test accounts and secrets stored in CI secret stores.

If you want, I can:
- Add an example helper that programmatically creates a session via your backend (if you have a test-login endpoint), and a Playwright helper that sets the session cookie directly before visiting `/chat`.
- Create a GitHub Actions workflow that runs E2E tests using repository secrets.
