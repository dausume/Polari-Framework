"""
@module appstore.appstore_tokens

Pure enrollment-token logic — mint, hash, verify, expiry. No Falcon,
no DB, no framework imports, so the selftest runs stdlib-only.

The contract:
  wire token   = '<name>.<secret>'    (handed out exactly once)
  name         = 'enr-' + 12 hex     (public id, safe to log)
  secret       = token_urlsafe(32)   (never stored anywhere)
  token_hash   = sha256(secret)      (what the row keeps)
Verification is constant-time (hmac.compare_digest); a token is
single-use — the CALLER flips status to 'redeemed' and saves before
responding, this module only judges.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

#: TTL clamp: floor stops instantly-dead tokens, ceiling stops
#: forever-tokens. Default 15 minutes — an install is an act, not a
#: standing credential.
TTL_MIN_S = 60
TTL_MAX_S = 86400
TTL_DEFAULT_S = 900


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clamp_ttl(seconds):
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return TTL_DEFAULT_S
    return max(TTL_MIN_S, min(TTL_MAX_S, s))


def expiry_iso(ttl_seconds):
    return (datetime.now(timezone.utc)
            + timedelta(seconds=clamp_ttl(ttl_seconds))).isoformat()


def hash_secret(secret):
    return hashlib.sha256(secret.encode('utf-8')).hexdigest()


def mint():
    """-> {'name', 'secret', 'wire', 'tokenHash'} — the ONLY place
    the secret ever exists in plaintext on the server side."""
    name = 'enr-' + secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    return {'name': name, 'secret': secret,
            'wire': f'{name}.{secret}',
            'tokenHash': hash_secret(secret)}


def split_wire(wire):
    """'<name>.<secret>' -> (name, secret) | (None, None)."""
    if not isinstance(wire, str) or '.' not in wire:
        return None, None
    name, _, secret = wire.partition('.')
    if not name or not secret:
        return None, None
    return name, secret


def judge(row_status, row_hash, row_expires_at, secret):
    """Verdict on one redemption attempt. Refusals NAME the reason —
    the token is single-use, so an oracle teaches an attacker
    nothing a replay could use (honest-refusal ethos)."""
    if row_status == 'redeemed':
        return {'ok': False, 'error': 'token already redeemed'}
    if row_status == 'revoked':
        return {'ok': False, 'error': 'token revoked'}
    expired = False
    if row_expires_at:
        try:
            expired = (datetime.fromisoformat(row_expires_at)
                       <= datetime.now(timezone.utc))
        except ValueError:
            expired = True
    if row_status == 'expired' or expired:
        return {'ok': False, 'error': 'token expired'}
    if row_status != 'active':
        return {'ok': False,
                'error': f'token status "{row_status}" is not active'}
    if not hmac.compare_digest(row_hash or '', hash_secret(secret)):
        return {'ok': False, 'error': 'unknown token'}
    return {'ok': True}
