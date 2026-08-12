"""
@cross-cutting
@module collab.livekit_remote
@tags @xc:bindings

Resolution + signing for the pol-livekit media server (mtg-2). The
fourth walk of the *_remote ladder (cad_remote → recon_remote →
here), with one addition: SIGNING KEYS, because the backend mints
LiveKit JWTs itself — pure-stdlib HS256, NO LiveKit SDK in this
image (proven against the real server in mtg-0 before this module
existed).

Three knobs, each with its own honest refusal:

  LIVEKIT_KEYS        'APIkey: secret' — MUST equal pol-livekit's
                      generated livekit/keys.env value or every
                      token is garbage. LIVEKIT_KEYS_FILE points at
                      the file itself where a shared mount exists.
  LIVEKIT_URL         server-side base (http://host:7880) for
                      reachability probes; unset → topology resolves
                      the 'collab.media' module's provider.
  LIVEKIT_CLIENT_URL  what BROWSERS connect to (wss://livekit.prf.
                      <ip>.nip.io — TLS at prf-proxy). Never derived:
                      guessing a TLS name a device must trust would
                      be inventing security posture.

Never raises. Refusals carry evidence + knob + action.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request

_MODULE = 'collab.media'

#: Short-lived by design (plan §1: "short-lived, never issued to a
#: client Polari has not just authorized").
DEFAULT_TOKEN_TTL_S = 900


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def signing_keys():
    """(api_key, secret) or None. LIVEKIT_KEYS wins; LIVEKIT_KEYS_FILE
    is read when set. Format either way: 'APIkey: secret'."""
    raw = os.environ.get('LIVEKIT_KEYS', '')
    if not raw:
        path = os.environ.get('LIVEKIT_KEYS_FILE', '')
        if path:
            try:
                with open(path) as f:
                    raw = f.read()
            except OSError:
                return None
    raw = raw.strip()
    if raw.startswith('LIVEKIT_KEYS='):
        raw = raw[len('LIVEKIT_KEYS='):]
    if ':' not in raw:
        return None
    key, _, secret = raw.partition(':')
    key, secret = key.strip(), secret.strip()
    if not key or not secret:
        return None
    return (key, secret)


def server_url():
    url = os.environ.get('LIVEKIT_URL', '').rstrip('/')
    if url:
        return url
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def client_url():
    return os.environ.get('LIVEKIT_CLIENT_URL', '').rstrip('/')


def unavailable_suggestion(evidence):
    return {
        'evidence': evidence,
        'knob': "LIVEKIT_KEYS ('APIkey: secret', = pol-livekit's "
                "livekit/keys.env), LIVEKIT_URL (server base) or the "
                "topology's livekit provider (module 'collab.media'), "
                'LIVEKIT_CLIENT_URL (the wss:// name browsers dial)',
        'action': 'pol compose livekit up on the media host, then set '
                  'LIVEKIT_KEYS + LIVEKIT_CLIENT_URL='
                  'wss://livekit.prf.<ip>.nip.io on this backend '
                  '(signalling rides prf-proxy; media is direct UDP).',
    }


def reachable(timeout=3):
    """Whether the resolved server answers at all (LiveKit serves a
    plain 200 'OK' at /). None when no URL resolves."""
    url = server_url()
    if not url:
        return None
    try:
        with urllib.request.urlopen(url + '/', timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def mint_token(identity, room, admin=False, ttl_s=None, name='',
               now=None, keys=None):
    """A LiveKit access JWT (HS256, stdlib only) — the mtg-0-proven
    signing shape. Returns {'ok': True, 'token', 'expires_at'} or an
    honest refusal when keys are missing/invalid.

    `now`/`keys` are injectable for tests; production callers pass
    neither."""
    pair = keys if keys is not None else signing_keys()
    if not pair:
        return {'ok': False, 'error': 'no LiveKit signing keys configured',
                'suggestion': unavailable_suggestion(
                    'LIVEKIT_KEYS and LIVEKIT_KEYS_FILE are both unset '
                    'or unparseable — tokens cannot be signed.')}
    api_key, secret = pair
    issued = int(now if now is not None else time.time())
    ttl = int(ttl_s or os.environ.get('COLLAB_TOKEN_TTL_S',
                                      DEFAULT_TOKEN_TTL_S))
    grants = {'room': room, 'roomJoin': True,
              'canPublish': True, 'canSubscribe': True}
    if admin:
        grants['roomAdmin'] = True
    claims = {'iss': api_key, 'sub': identity,
              'name': name or identity,
              'nbf': issued - 10, 'exp': issued + ttl,
              'video': grants}
    header = {'alg': 'HS256', 'typ': 'JWT'}
    signing_input = (_b64url(json.dumps(header, separators=(',', ':'))
                             .encode())
                     + '.'
                     + _b64url(json.dumps(claims, separators=(',', ':'))
                               .encode()))
    signature = hmac.new(secret.encode(), signing_input.encode(),
                         hashlib.sha256).digest()
    return {'ok': True, 'token': signing_input + '.' + _b64url(signature),
            'expires_at': issued + ttl, 'ttl_s': ttl}


def verify_token(token, keys=None):
    """Decode + verify one of OUR tokens (selftest / debugging aid —
    LiveKit itself is the production verifier). Returns the claims
    dict or None."""
    pair = keys if keys is not None else signing_keys()
    if not pair or not token or token.count('.') != 2:
        return None
    head, payload, sig = token.split('.')
    expected = hmac.new(pair[1].encode(), f'{head}.{payload}'.encode(),
                        hashlib.sha256).digest()
    got = base64.urlsafe_b64decode(sig + '=' * (-len(sig) % 4))
    if not hmac.compare_digest(expected, got):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(
            payload + '=' * (-len(payload) % 4)))
    except Exception:
        return None
