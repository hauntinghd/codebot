#!/usr/bin/env python3
"""Rotate JWT/SESSION secrets and create Grafana env file.

Backs up `.env` to `.env.bak.<timestamp>`, generates new `JWT_SECRET`
and `SESSION_SECRET`, updates `.env` in-place, and writes a
`monitoring/grafana.env` file containing `GF_SECURITY_ADMIN_PASSWORD`.

This script must be run from the repository root or with absolute paths.
"""
from pathlib import Path
import time
import secrets
import base64
import re
import os


ROOT = Path('/home/omatic657/aicoderbot')
ENV_PATH = ROOT / '.env'
MONITORING_DIR = ROOT / 'monitoring'
GRAF_ENV = MONITORING_DIR / 'grafana.env'


def backup_env():
    ts = time.strftime('%Y%m%dT%H%M%SZ')
    bak = ENV_PATH.parent / f'.env.bak.{ts}'
    text = ENV_PATH.read_text() if ENV_PATH.exists() else ''
    bak.write_text(text)
    bak.chmod(0o600)
    return bak


def gen_secret_bytes():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def update_env(jwt, session):
    if not ENV_PATH.exists():
        raise SystemExit('.env not found')
    s = ENV_PATH.read_text()
    if re.search(r'^JWT_SECRET=', s, flags=re.M):
        s = re.sub(r'^JWT_SECRET=.*$', f'JWT_SECRET={jwt}', s, flags=re.M)
    else:
        s += f'\nJWT_SECRET={jwt}\n'

    if re.search(r'^SESSION_SECRET=', s, flags=re.M):
        s = re.sub(r'^SESSION_SECRET=.*$', f'SESSION_SECRET={session}', s, flags=re.M)
    else:
        s += f'\nSESSION_SECRET={session}\n'

    ENV_PATH.write_text(s)
    ENV_PATH.chmod(0o600)


def write_grafana_env(admin_pw):
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    GRAF_ENV.write_text(f'GF_SECURITY_ADMIN_PASSWORD={admin_pw}\n')
    GRAF_ENV.chmod(0o600)
    return GRAF_ENV


def main():
    print('Backing up .env')
    bak = backup_env()
    print('Backup written to', bak)

    jwt = gen_secret_bytes()
    session = gen_secret_bytes()

    print('Updating .env with new secrets')
    update_env(jwt, session)

    admin_pw = secrets.token_urlsafe(24)
    print('Writing Grafana env file')
    graf = write_grafana_env(admin_pw)

    print('Done. Grafana env at', graf)


if __name__ == '__main__':
    main()
