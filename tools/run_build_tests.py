import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
import backend.main as bm
import backend.auth as auth
from backend.database import db as _db

app = bm.app


def run():
    import uuid
    # create admin user
    admin_email = f"build-admin+{uuid.uuid4().hex[:8]}@example.com"
    admin_pw = "adminpass"
    admin_id = auth.create_user(admin_email, admin_pw)
    # mark admin in DB
    with _db() as conn:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (admin_id,))
    print('created admin id', admin_id)

    # create project as admin
    access = auth.make_access_token(str(admin_id))
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {access}"}

    r = client.post('/codebot/api/architecture/projects', json={"name": "Build Test", "template": "blank"}, params={"init": True}, headers=headers)
    print('create project status', r.status_code)
    print('create project body', r.text)
    if r.status_code != 200:
        return 2
    pid = r.json().get('project_id')
    if not pid:
        print('no project id returned')
        return 3

    # Call the research-based build endpoint (which requires an API key)
    print('Calling research-based build endpoint (this should fail without API key)')
    r2 = client.get(f'/codebot/api/architecture/projects/{pid}/build/research', headers=headers)
    print('build endpoint status', r2.status_code)
    try:
        text = r2.text
        print('build endpoint body (truncated):', text[:2000])
    except Exception as e:
        print('failed to read body', e)

    # Also call plan/stream endpoint (non-research) to see streaming responses
    print('Calling plan/stream (non-research)')
    r3 = client.get(f'/codebot/api/architecture/projects/{pid}/plan/stream?message=test-build', headers=headers)
    print('plan/stream status', r3.status_code)
    try:
        print('plan/stream body (truncated):', r3.text[:2000])
    except Exception as e:
        print('failed to read plan stream body', e)

    return 0

if __name__ == '__main__':
    raise SystemExit(run())
