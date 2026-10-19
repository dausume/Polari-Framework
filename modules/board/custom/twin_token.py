"""
@module board.custom.twin_token

sim-1: the control token of a twin session is DERIVED, never stored in a row: HMAC-SHA256(server secret, session name), 32 hex characters. The server secret is
POLARI_TWIN_TOKEN_SECRET, else a 0600 file (POLARI_TWIN_TOKEN_FILE, default ~/.polari/twin_token_secret) created on first use. A backend restart derives the
same token again, so it can reconnect to a session it started; a reader of the TwinSession rows learns nothing about it. The start door and `pol board twin
session start` show it ONCE to the person who started the session (a bridge needs it).
"""
import hashlib
import hmac
import os
import secrets


def _secret():
    env = os.environ.get('POLARI_TWIN_TOKEN_SECRET', '')
    if env:
        return env.encode()
    path = os.environ.get('POLARI_TWIN_TOKEN_FILE') or os.path.expanduser('~/.polari/twin_token_secret')
    try:
        return open(path, 'rb').read().strip()
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    value = secrets.token_hex(32).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(value)
    return value


def derive(session_name):
    return hmac.new(_secret(), session_name.encode(), hashlib.sha256).hexdigest()[:32]
