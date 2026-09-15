"""
moduleService.posture — what posture THIS instance runs in (ISLE_HARDENING_PLAN §16b/§17).

One accessor for the whole backend (before this every reader inlined its own env check). Two sources, in order:
  1. POLARI_POSTURE (+ POLARI_POSTURE_UNTIL) in the process environment — the stack's own knob;
  2. /etc/polari/posture.json — what posture.sh / the ISO install wrote on the machine (mounted read-only into the
     backend); {"posture": "dev"|"production", "until": ISO-8601 or "", "relaxations": [...], "applied_by": ...}.
A dev posture past its `until` is production again (the revert timer's promise, kept here too).

`is_dev()` is the ONE switch §17 names: in dev the security controls OBSERVE (evaluate, warn, never deny) — see
security.custom.security_observe. Production is the default whenever nothing says dev.
"""
import json
import os
import time

POSTURE_FILE = '/etc/polari/posture.json'
POSTURES = ('production', 'dev')


def _parse_until(until):
    if not until:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return time.mktime(time.strptime(until, fmt)) - (time.timezone if fmt.endswith('Z') else 0)
        except ValueError:
            continue
    return None


def read_file(path=POSTURE_FILE):
    try:
        d = json.load(open(path))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def state(env=None, path=POSTURE_FILE, now=None):
    """{posture, until, source, expired, relaxations, applied_by} — the posture and where it came from."""
    env = os.environ if env is None else env
    now = time.time() if now is None else now
    p = (env.get('POLARI_POSTURE') or '').strip().lower(); until = env.get('POLARI_POSTURE_UNTIL', '') or ''; src = 'env'
    relax = []; by = ''
    if p not in POSTURES:
        f = read_file(path)
        p = (f.get('posture') or '').strip().lower(); until = f.get('until') or ''; src = 'file' if f else 'default'
        relax = list(f.get('relaxations') or []); by = f.get('applied_by') or ''
    expired = False
    if p == 'dev':
        t = _parse_until(until)
        if t is not None and t < now:
            expired = True; p = 'production'
    if p not in POSTURES:
        p = 'production'
    return {'posture': p, 'until': until, 'source': src, 'expired': expired, 'relaxations': relax, 'applied_by': by}


def posture(env=None, path=POSTURE_FILE):
    return state(env, path)['posture']


def is_dev(env=None, path=POSTURE_FILE):
    return posture(env, path) == 'dev'
