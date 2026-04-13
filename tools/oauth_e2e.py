from playwright.sync_api import sync_playwright, TimeoutError
import os, json, sys, time

EMAIL = os.environ.get('GOOGLE_E2E_EMAIL')
PWD = os.environ.get('GOOGLE_E2E_PASSWORD')
START_URL = os.environ.get('E2E_START_URL', 'https://chatbot.nyptidindustries.com/codebot/api/auth/oauth/google')
AI_TEST_PROMPT = os.environ.get('E2E_AI_PROMPT', 'Say hello and confirm OAuth login')

if not EMAIL or not PWD:
    print('ERROR: GOOGLE_E2E_EMAIL and GOOGLE_E2E_PASSWORD must be set', file=sys.stderr)
    sys.exit(2)

print('Starting Playwright E2E test...')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        print('Navigating to OAuth start URL:', START_URL)
        page.goto(START_URL, timeout=60000)

        # Google email entry
        try:
            page.wait_for_selector('input[type="email"]', timeout=15000)
            page.fill('input[type="email"]', EMAIL)
            # Click next - use button selectors that commonly work for Google
            if page.query_selector('#identifierNext'):
                page.click('#identifierNext')
            else:
                page.click('button:has-text("Next")')
            print('Filled email, clicked Next')
        except TimeoutError:
            print('Email input not found; maybe already at password step')

        # Password entry
        page.wait_for_selector('input[type="password"]', timeout=20000)
        page.fill('input[type="password"]', PWD)
        if page.query_selector('#passwordNext'):
            page.click('#passwordNext')
        else:
            page.click('button:has-text("Next")')
        print('Filled password, clicked Next')

        # Consent screen (if present)
        try:
            # Wait for either consent or redirect back
            page.wait_for_url('**/codebot/**', timeout=30000)
            print('Redirected back to CodeBot callback')
        except TimeoutError:
            # Maybe consent page appears with buttons labeled "Allow" or "Continue"
            try:
                if page.query_selector('button:has-text("Allow")'):
                    page.click('button:has-text("Allow")')
                    print('Clicked Allow')
                elif page.query_selector('button:has-text("Continue")'):
                    page.click('button:has-text("Continue")')
                    print('Clicked Continue')
                page.wait_for_url('**/codebot/**', timeout=30000)
                print('Redirected back after consent')
            except TimeoutError:
                print('Consent/redirect timeout', file=sys.stderr)
                # continue to check cookies

        # Check for session cookie
        cookies = context.cookies()
        print('Cookies after login:', json.dumps(cookies, indent=2))

        # Make an AI request via fetch inside page context to use same cookies
        try:
            res = page.evaluate("(prompt)=>{return fetch('/codebot/api/ai/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt,max_tokens:200})}).then(r=>r.json()).catch(e=>({error:String(e)}));}", AI_TEST_PROMPT)
            print('AI request result:', json.dumps(res, indent=2))
        except Exception as e:
            print('AI request failed:', e, file=sys.stderr)

    except Exception as e:
        print('E2E script error:', e, file=sys.stderr)
        raise
    finally:
        try:
            context.close()
            browser.close()
        except Exception:
            pass

print('Playwright E2E finished')
