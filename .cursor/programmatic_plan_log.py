#!/usr/bin/env python3
import sqlite3, requests, json, time, uuid, subprocess
DB='data/codebot.db'
BASE='http://127.0.0.1:8080'
API_BASE='/codebot/api'

# Find latest auto% user
conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
cur=conn.cursor()
cur.execute("SELECT id,email FROM users WHERE email LIKE 'auto%' ORDER BY created_at DESC LIMIT 1")
row=cur.fetchone()
if not row:
    raise SystemExit('no test user found')
user_id=row['id']
email=row['email']
print('found user', user_id, email)

# Login to get access token
login_url = f"{BASE}{API_BASE}/auth/email/login"
resp=requests.post(login_url, json={'email': email, 'password': 'Password123!'})
print('login status', resp.status_code)
if resp.status_code!=200:
    print(resp.text)
    raise SystemExit('login failed')
js=resp.json()
access=js.get('access_token')
print('access token present?', bool(access))

# Insert project
proj_id=str(uuid.uuid4())
now=int(time.time())
cur.execute("INSERT INTO architecture_projects (id,user_id,name,description,template,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (proj_id, user_id, 'AutoProj','Automated project','', 'planning', now, now))
conn.commit()
print('inserted project', proj_id)

# Call plan endpoint with Bearer token
plan_url=f"{BASE}{API_BASE}/architecture/projects/{proj_id}/plan"
hdr={'Authorization': f'Bearer {access}'}
plan_resp=requests.post(plan_url, json={'message':'Please create a simple plan'}, headers=hdr, timeout=30)
print('plan status', plan_resp.status_code)
print(plan_resp.text)

# Fetch recent journal lines to capture traceback
jc=subprocess.run(['journalctl','-u','aicoderbot.service','-n','240','--no-pager'], capture_output=True, text=True)
lines=jc.stdout.splitlines()
for i,l in enumerate(lines):
    if 'Traceback' in l or 'NameError' in l or 'api_key' in l:
        start=max(0,i-5)
        end=min(len(lines), i+30)
        print('\n--- journal excerpt ---')
        print('\n'.join(lines[start:end]))
        break
else:
    print('no traceback lines found in journal')

conn.close()
