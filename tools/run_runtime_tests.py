import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
import backend.main as bm
import backend.auth as auth
import json

app = bm.app
# Override current_user dependency to use the registered user for testing

def run():
    # We'll create TestClient after setting dependency override so cookies/session handling is not required

    # Register a fresh test user
    import uuid
    email = f"runtime-test+{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword"
    # Create the user directly in the DB (bypass HTTP registration)
    try:
        user_id = auth.create_user(email, password)
        print('created user id', user_id)
    except Exception as e:
        print('create_user error', e)
    # Fetch user row
    user = auth.get_user_by_email(email)
    if not user:
        print('failed to fetch registered user from DB')
        return 3
    # Debug: print user fields relevant to Architecture access
    try:
        print('user fields:', {'id': user['id'], 'is_admin': user['is_admin'], 'plan': user['plan'], 'is_saas_dev': user.get('is_saas_dev') if hasattr(user, 'get') else None})
    except Exception:
        print('user row keys:', list(user.keys()))
    # Create an access token for the test user and use it for authenticated requests
    access = auth.make_access_token(str(user["id"]))
    client = TestClient(app)

    # Attempt to create a website template project (should be blocked)
    headers = {"Authorization": f"Bearer {access}"}
    r2 = client.post('/codebot/api/architecture/projects', json={"name": "Site Test", "template": "website"}, params={"init": True}, headers=headers)
    print('create website project status', r2.status_code)
    print('create website body:', r2.text)

    # Attempt to create a blank project (should succeed)
    r3 = client.post('/codebot/api/architecture/projects', json={"name": "Blank Test", "template": "blank"}, params={"init": True}, headers=headers)
    print('create blank project status', r3.status_code)
    print('create blank body:', r3.text)

    # Now create an admin user (bypass subscription) and verify blank project succeeds
    admin_email = f"runtime-admin+{uuid.uuid4().hex[:8]}@example.com"
    admin_pw = "adminpass"
    admin_id = auth.create_user(admin_email, admin_pw)
    # Mark as admin in DB (direct DB update)
    from backend.database import db as _db
    with _db() as conn:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (admin_id,))

    admin_access = auth.make_access_token(str(admin_id))
    admin_headers = {"Authorization": f"Bearer {admin_access}"}

    r4 = client.post('/codebot/api/architecture/projects', json={"name": "Admin Blank", "template": "blank"}, params={"init": True}, headers=admin_headers)
    print('admin create blank status', r4.status_code)
    print('admin create blank body:', r4.text)

    r5 = client.post('/codebot/api/architecture/projects', json={"name": "Admin Site", "template": "website"}, params={"init": True}, headers=admin_headers)
    print('admin create website status', r5.status_code)
    print('admin create website body:', r5.text)

    return 0

if __name__ == '__main__':
    raise SystemExit(run())
