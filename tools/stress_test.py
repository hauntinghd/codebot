#!/usr/bin/env python3
"""Simple async stress test for CodeBot auth and /api/me flows.
Usage: python3 tools/stress_test.py --concurrency 100 --users 500
This script will attempt to register and login `users` concurrent clients.
"""
import argparse
import asyncio
import aiohttp
import time

API_BASE = 'http://127.0.0.1:8080/codebot'

async def worker(i, session, results):
    email = f'stress_user_{i}@example.com'
    password = 'Password123!'
    # try register
    try:
        async with session.post(f'{API_BASE}/api/auth/email/register', json={'email': email, 'password': password}, timeout=20) as r:
            if r.status in (200, 201):
                results['registered'] += 1
            else:
                # 409 is expected if already exists
                if r.status == 409:
                    results['exists'] += 1
                else:
                    results['register_fail'] += 1
    except Exception:
        results['register_err'] += 1

    # login (use returned access_token for /me to avoid cookie/secure issues)
    try:
        async with session.post(f'{API_BASE}/api/auth/email/login', json={'email': email, 'password': password}, timeout=20) as r:
            if r.status == 200:
                results['login_ok'] += 1
                j = await r.json()
                access = j.get('access_token')
                headers = { 'Authorization': f'Bearer {access}'} if access else {}
                async with session.get(f'{API_BASE}/api/me', headers=headers, timeout=20) as m:
                    if m.status == 200:
                        results['me_ok'] += 1
                    else:
                        results['me_fail'] += 1
            else:
                results['login_fail'] += 1
    except Exception:
        results['login_err'] += 1

async def run(concurrency, total):
    results = {k:0 for k in ['registered','exists','register_fail','register_err','login_ok','login_fail','login_err','me_ok','me_fail']}
    sem = asyncio.Semaphore(concurrency)

    async def sem_worker(i):
        async with sem:
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                await worker(i, session, results)

    tasks = [asyncio.create_task(sem_worker(i)) for i in range(total)]
    start = time.time()
    await asyncio.gather(*tasks)
    dur = time.time() - start
    print(f'Completed {total} users in {dur:.2f}s')
    for k,v in results.items():
        print(f'{k}: {v}')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--concurrency', type=int, default=50)
    p.add_argument('--users', type=int, default=100)
    args = p.parse_args()
    asyncio.run(run(args.concurrency, args.users))

if __name__ == '__main__':
    main()
