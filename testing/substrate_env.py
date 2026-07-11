"""
@module testing.substrate_env

acct-1: WHERE the live substrates are, and whether this environment
DECLARES them — the seam that makes substrate rows honest:

  undeclared  no container, no env knob        -> checks skip-honest
  declared    container exists or knob set     -> unreachable = FAIL
              (unplugging a substrate flips its row RED with the
              real error — the acct-1 acceptance)

Resolution order per substrate: explicit env knob (MARIADB_HOST /
KEYDB_HOST) first, else the staging container's bridge IP via docker
inspect. Credentials come from env (MARIADB_PASSWORD /
KEYDB_PASSWORD) or the suite's gitignored .generated/.env.staging
(POLARI_OBJECTS_DB_PASS / POLARI_KEYDB_PASS). Passwords NEVER appear
in evidence, suggestions, or logs — the repos are public.
"""

import os
import shutil
import subprocess

from testing.check_catalog import FRAMEWORK_ROOT

MARIADB_CONTAINER = 'pol-mariadb'
KEYDB_CONTAINER = 'prf-keydb'


def secrets_files():
    """Every ancestor's .generated/.env.staging, nearest first.
    (Both the rf-node and the suite carry a staging compose, but
    only the suite's .generated actually holds the secrets — so
    scan them all rather than stopping at the first compose.)"""
    paths, current = [], FRAMEWORK_ROOT
    for _ in range(4):
        current = os.path.dirname(current)
        candidate = os.path.join(current, '.generated',
                                 '.env.staging')
        if os.path.isfile(candidate):
            paths.append(candidate)
    return paths


def load_env_file(path):
    values = {}
    try:
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def _staging_secrets():
    values = {}
    for path in secrets_files():
        for key, value in load_env_file(path).items():
            values.setdefault(key, value)
    return values


def container_state(name):
    """'running' | 'exited' | ... | None (no docker / no container)."""
    if shutil.which('docker') is None:
        return None
    try:
        proc = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Status}}', name],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=10)
        return proc.stdout.strip() or None
    except Exception:
        return None


def container_ip(name):
    try:
        proc = subprocess.run(
            ['docker', 'inspect', '-f',
             '{{range .NetworkSettings.Networks}}{{.IPAddress}} '
             '{{end}}', name],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=10)
        addresses = proc.stdout.split()
        return addresses[0] if addresses else None
    except Exception:
        return None


def _resolve(env_host_key, container, default_port, port_key,
             user=None, database=None, password_env=None,
             secret_key=None):
    endpoint = {'host': None, 'port': int(os.environ.get(
                    port_key, default_port) or default_port),
                'declared': False, 'source': '',
                'container_state': None}
    if user is not None:
        endpoint['user'] = os.environ.get('MARIADB_USER', user)
    if database is not None:
        endpoint['database'] = os.environ.get(
            'MARIADB_DATABASE', database)
    explicit = (os.environ.get(env_host_key) or '').strip()
    if explicit:
        endpoint.update(host=explicit, declared=True,
                        source=f'env {env_host_key}')
    else:
        state = container_state(container)
        endpoint['container_state'] = state
        if state is not None:
            endpoint['declared'] = True
            endpoint['source'] = f'container {container} ({state})'
            if state == 'running':
                endpoint['host'] = container_ip(container)
    password = (os.environ.get(password_env) or '').strip()
    if not password and secret_key:
        password = _staging_secrets().get(secret_key, '')
    endpoint['password'] = password
    return endpoint


def resolve_mariadb():
    return _resolve('MARIADB_HOST', MARIADB_CONTAINER, 3306,
                    'MARIADB_PORT', user='polari',
                    database='polari_objects',
                    password_env='MARIADB_PASSWORD',
                    secret_key='POLARI_OBJECTS_DB_PASS')


def resolve_keydb():
    return _resolve('KEYDB_HOST', KEYDB_CONTAINER, 6379,
                    'KEYDB_PORT', password_env='KEYDB_PASSWORD',
                    secret_key='POLARI_KEYDB_PASS')


def disruption_allowed():
    """Compose-kind checks that bounce live containers are opt-in."""
    raw = (os.environ.get('POLARI_ALLOW_DISRUPTIVE') or '').lower()
    return raw in ('1', 'true', 'yes', 'on')


def classify_absence(endpoint, substrate, suggestion):
    """The honest-status decision for an unreachable substrate:
    None = proceed (host resolved); otherwise a partial result row
    {status, evidence}."""
    if not endpoint['declared']:
        return {'status': 'skip-honest',
                'evidence': f'{substrate} not declared here (no '
                            f'container, no env knob). {suggestion}'}
    if not endpoint['host']:
        state = endpoint['container_state'] or 'unknown'
        return {'status': 'fail',
                'evidence': f'{substrate} is declared '
                            f'({endpoint["source"]}) but has no '
                            f'reachable address — container state: '
                            f'{state}.'}
    return None
