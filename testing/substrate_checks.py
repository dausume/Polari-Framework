"""
@module testing.substrate_checks

acct-1: LIVE substrate checks — databases + cache — as callable
matrix rows (runner_kind 'callable'). Each callable returns a
partial result row {status, evidence[, passed, total]}; the matrix
runner adds identity + timing.

  mariadb-reachability      connect + SELECT VERSION().
  mariadb-credential-honesty  a WRONG password must be refused (the
                            wrong-password-boots-healthy gotcha from
                            the dbcombo track, pinned as a check) —
                            and the right one must still work, so a
                            dead server can't fake a pass.
  mariadb-auto-tables       the object-tree schema really was
                            auto-generated on the live server.
  keydb-roundtrip           the FRAMEWORK's PolariCache seam
                            (setTable/getTable/invalidateTable),
                            not a bare PING.
  dialect-parity            the dbcombo proof, repeatable: the same
                            unittest file on sqlite AND mariadb
                            (throwaway schema polari_objects_test)
                            must fail IDENTICALLY.
  restart-persistence       volume-backed data survives a container
                            bounce — DISRUPTIVE, so opt-in via
                            POLARI_ALLOW_DISRUPTIVE=true; otherwise
                            skip-honest naming the knob.

Passwords never appear in evidence — repos are public.
"""

import os
import subprocess
import time

from testing.check_catalog import FRAMEWORK_ROOT
from testing.substrate_env import (
    MARIADB_CONTAINER, classify_absence, disruption_allowed,
    resolve_keydb, resolve_mariadb,
)

MARIADB_SUGGESTION = (
    'Start staging (suite docker-compose.staging-nip.yml — service '
    'pol-mariadb) or set MARIADB_HOST + MARIADB_PASSWORD.')
KEYDB_SUGGESTION = (
    'Start staging (suite docker-compose.staging-nip.yml — service '
    'prf-keydb) or set KEYDB_HOST (+ KEYDB_PASSWORD).')
PARITY_SCHEMA = 'polari_objects_test'


def _connect(endpoint, password=None, database=None, timeout=8):
    import pymysql
    return pymysql.connect(
        host=endpoint['host'], port=endpoint['port'],
        user=endpoint['user'],
        password=endpoint['password'] if password is None
        else password,
        database=endpoint.get('database') if database is None
        else database,
        connect_timeout=timeout, charset='utf8mb4')


def check_mariadb_reachability():
    endpoint = resolve_mariadb()
    absent = classify_absence(endpoint, 'MariaDB',
                              MARIADB_SUGGESTION)
    if absent:
        return absent
    try:
        conn = _connect(endpoint, database='')
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
        conn.close()
        return {'status': 'pass',
                'evidence': f'{version} at {endpoint["host"]}:'
                            f'{endpoint["port"]} '
                            f'({endpoint["source"]})'}
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'declared ({endpoint["source"]}) but '
                            f'connect failed: '
                            f'{type(exc).__name__}: {exc}'}


def check_mariadb_credential_honesty():
    endpoint = resolve_mariadb()
    absent = classify_absence(endpoint, 'MariaDB',
                              MARIADB_SUGGESTION)
    if absent:
        absent['status'] = 'skip-honest'
        return absent
    try:
        conn = _connect(endpoint,
                        password=(endpoint['password']
                                  + '-wrong-acct1'), database='')
        conn.close()
        return {'status': 'fail',
                'evidence': 'a WRONG password was ACCEPTED — '
                            'credential checking is not honest'}
    except Exception as exc:
        refusal = f'{type(exc).__name__}: {exc}'
    try:
        conn = _connect(endpoint, database='')
        conn.close()
    except Exception as exc:
        return {'status': 'fail',
                'evidence': 'wrong password refused, but the RIGHT '
                            'one also failed — server broken or '
                            'creds stale: '
                            f'{type(exc).__name__}: {exc}'}
    return {'status': 'pass',
            'evidence': 'wrong password honestly refused '
                        f'({refusal[:120]}); real credentials '
                        'still accepted'}


def check_mariadb_auto_tables():
    endpoint = resolve_mariadb()
    absent = classify_absence(endpoint, 'MariaDB',
                              MARIADB_SUGGESTION)
    if absent:
        return absent
    try:
        conn = _connect(endpoint, database='')
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM information_schema.tables '
                'WHERE table_schema = %s', (endpoint['database'],))
            count = cursor.fetchone()[0]
        conn.close()
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'{type(exc).__name__}: {exc}'}
    if count >= 150:
        return {'status': 'pass',
                'evidence': f'{count} auto-generated object-tree '
                            f'tables in {endpoint["database"]}'}
    return {'status': 'fail',
            'evidence': f'only {count} tables in '
                        f'{endpoint["database"]} — the auto-'
                        'generated schema is missing or partial'}


def check_keydb_roundtrip():
    endpoint = resolve_keydb()
    absent = classify_absence(endpoint, 'KeyDB', KEYDB_SUGGESTION)
    if absent:
        return absent
    saved = {key: os.environ.get(key)
             for key in ('CACHE_BACKEND', 'KEYDB_HOST',
                         'KEYDB_PORT', 'KEYDB_PASSWORD')}
    os.environ['CACHE_BACKEND'] = 'keydb'
    os.environ['KEYDB_HOST'] = endpoint['host']
    os.environ['KEYDB_PORT'] = str(endpoint['port'])
    if endpoint['password']:
        os.environ['KEYDB_PASSWORD'] = endpoint['password']
    try:
        from polariDBmanagement.keydb_cache import PolariCache
        cache = PolariCache()
        if not cache.enabled or not cache.ping():
            return {'status': 'fail',
                    'evidence': f'declared ({endpoint["source"]}) '
                                'but the framework cache could not '
                                'connect/ping'}
        columns, rows = ['id', 'name'], [(1, 'acct1-probe')]
        cache.setTable('acct1_db', 'probe', columns, rows)
        fetched = cache.getTable('acct1_db', 'probe')
        stored_ok = fetched == (columns, rows)
        ttl = cache.client.ttl(cache.tableKey('acct1_db', 'probe'))
        cache.invalidateTable('acct1_db', 'probe')
        gone = cache.getTable('acct1_db', 'probe') is None
        live_keys = len(cache.client.keys('polari:table:*'))
        hits = cache.client.info('stats').get('keyspace_hits')
        if stored_ok and 0 < ttl <= cache.ttl and gone:
            return {'status': 'pass',
                    'evidence': 'PolariCache setTable/getTable/'
                                f'invalidateTable round-trip ok, '
                                f'ttl={ttl}s; live polari:table:* '
                                f'keys={live_keys}, '
                                f'keyspace_hits={hits}'}
        return {'status': 'fail',
                'evidence': f'round-trip broke: stored_ok='
                            f'{stored_ok}, ttl={ttl}, '
                            f'invalidated={gone}'}
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'{type(exc).__name__}: {exc}'}
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _parity_leg(dialect, endpoint, timeout):
    env = dict(os.environ, PYTHONUNBUFFERED='1',
               DATABASE_TYPE=dialect)
    if dialect == 'mariadb':
        env.update(MARIADB_HOST=endpoint['host'],
                   MARIADB_PORT=str(endpoint['port']),
                   MARIADB_USER=endpoint['user'],
                   MARIADB_PASSWORD=endpoint['password'],
                   MARIADB_DATABASE=PARITY_SCHEMA)
    proc = subprocess.run(
        ['python3', '-m', 'testing.parity_probe'],
        cwd=FRAMEWORK_ROOT, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=timeout)
    for line in proc.stdout.splitlines():
        if line.startswith('PARITY_RESULT '):
            import json
            leg = json.loads(line[len('PARITY_RESULT '):])
            leg['exit'] = proc.returncode
            return leg
    return {'dialect': dialect, 'created': False, 'save_ok': False,
            'roundtrip': False, 'columns': [],
            'exit': proc.returncode,
            'tail': proc.stdout.strip()[-400:]}


def check_dialect_parity(timeout_per_leg=600):
    """The dbcombo parity proof, repeatable: the SAME auto-table
    generation (adapter-translated), save, and read-back must
    succeed with identical columns on sqlite and mariadb. Each leg
    must actually reach its database (created=True) — a leg that
    never touched the DB is a loud fail, not a vacuous pass."""
    endpoint = resolve_mariadb()
    absent = classify_absence(endpoint, 'MariaDB',
                              MARIADB_SUGGESTION)
    if absent:
        absent['status'] = 'skip-honest'
        return absent
    try:
        sqlite_leg = _parity_leg('sqlite', endpoint,
                                 timeout_per_leg)
        mariadb_leg = _parity_leg('mariadb', endpoint,
                                  timeout_per_leg)
    except subprocess.TimeoutExpired:
        return {'status': 'fail',
                'evidence': f'a parity leg exceeded '
                            f'{timeout_per_leg}s'}
    summary = '; '.join(
        f"{leg['dialect']}: created={leg['created']} "
        f"save={leg['save_ok']} roundtrip={leg['roundtrip']}"
        for leg in (sqlite_leg, mariadb_leg))
    both_real = all(leg['created'] and leg['save_ok']
                    and leg['roundtrip'] and leg['exit'] == 0
                    for leg in (sqlite_leg, mariadb_leg))
    same_columns = sqlite_leg['columns'] == mariadb_leg['columns']
    if both_real and same_columns:
        return {'status': 'pass',
                'evidence': 'auto-table + upsert + read-back '
                            'identical on both dialects '
                            f'(schema {PARITY_SCHEMA}) — {summary}; '
                            f"columns={sqlite_leg['columns']}"}
    return {'status': 'fail',
            'evidence': f'dialect drift — {summary}; columns '
                        f"sqlite={sqlite_leg['columns']} vs "
                        f"mariadb={mariadb_leg['columns']}"
                        + ('' if 'tail' not in mariadb_leg
                           else f"; mariadb tail: "
                                f"{mariadb_leg['tail']}")}


def check_restart_persistence():
    endpoint = resolve_mariadb()
    absent = classify_absence(endpoint, 'MariaDB',
                              MARIADB_SUGGESTION)
    if absent:
        absent['status'] = 'skip-honest'
        return absent
    if not disruption_allowed():
        return {'status': 'skip-honest',
                'evidence': 'probe restarts the live '
                            f'{MARIADB_CONTAINER} container — '
                            'opt in with '
                            'POLARI_ALLOW_DISRUPTIVE=true'}
    marker = f'acct1-{int(time.time())}'
    try:
        conn = _connect(endpoint, database='')
        with conn.cursor() as cursor:
            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS {PARITY_SCHEMA} '
                'CHARACTER SET utf8mb4')
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS {PARITY_SCHEMA}.'
                'acct_persistence_probe '
                '(marker VARCHAR(64) PRIMARY KEY)')
            cursor.execute(
                f'INSERT INTO {PARITY_SCHEMA}.'
                'acct_persistence_probe VALUES (%s)', (marker,))
        conn.commit()
        conn.close()
        subprocess.run(['docker', 'restart', MARIADB_CONTAINER],
                       check=True, timeout=120,
                       stdout=subprocess.DEVNULL)
        deadline = time.monotonic() + 120
        survived, last_error = False, ''
        while time.monotonic() < deadline:
            try:
                endpoint = resolve_mariadb()  # IP can change
                conn = _connect(endpoint, database='')
                with conn.cursor() as cursor:
                    cursor.execute(
                        f'SELECT marker FROM {PARITY_SCHEMA}.'
                        'acct_persistence_probe '
                        'WHERE marker = %s', (marker,))
                    survived = cursor.fetchone() is not None
                    cursor.execute(
                        f'DELETE FROM {PARITY_SCHEMA}.'
                        'acct_persistence_probe '
                        'WHERE marker = %s', (marker,))
                conn.commit()
                conn.close()
                break
            except Exception as exc:
                last_error = f'{type(exc).__name__}: {exc}'
                time.sleep(3)
        if survived:
            return {'status': 'pass',
                    'evidence': f'marker {marker} survived a real '
                                f'docker restart of '
                                f'{MARIADB_CONTAINER}'}
        return {'status': 'fail',
                'evidence': 'marker did not survive the restart '
                            f'(last error: {last_error or "none"})'}
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'{type(exc).__name__}: {exc}'}
