"""
Selftest — acct-1: live substrate checks (databases + cache).

Run from polari-framework/:
    python3 -m testing.selftest_substrate

Covers: the six substrate rows are on the matrix (category
substrate = blocking), the declared/undeclared honesty ladder
(undeclared -> skip-honest with suggestion; declared-but-down ->
FAIL — unplugging flips the row red), and — when staging is
actually reachable from this box — the real checks: MariaDB
reachability, credential honesty (wrong password refused, right one
accepted), auto-generated schema presence, the framework
PolariCache round-trip on KeyDB, and the repeatable dialect-parity
proof. The disruptive restart-persistence probe is pinned to its
skip-honest default here (POLARI_ALLOW_DISRUPTIVE scrubbed);
its live path is exercised via the matrix, not the selftest.

Secrets: asserts no evidence string leaks the DB password.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# Deterministic: this selftest always asserts the restart probe's
# opt-in refusal, even inside a disruption-enabled matrix run.
os.environ.pop('POLARI_ALLOW_DISRUPTIVE', None)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _catalog_rows():
    from testing.check_catalog import catalog_by_name
    print('catalog: substrate rows')
    by_name = catalog_by_name()
    names = [
        'substrate:mariadb-reachability',
        'substrate:mariadb-credential-honesty',
        'substrate:mariadb-auto-tables',
        'substrate:keydb-roundtrip',
        'substrate:dialect-parity',
        'substrate:restart-persistence',
    ]
    check('all six substrate rows registered',
          all(name in by_name for name in names))
    check('substrate rows are blocking (plan §4)',
          all(by_name[name]['criticality'] == 'blocking'
              for name in names))
    check('restart probe is compose-kind, others live',
          by_name['substrate:restart-persistence']['kind']
          == 'compose'
          and by_name['substrate:mariadb-reachability']['kind']
          == 'live')
    return by_name


def _honesty_ladder():
    from testing.substrate_env import classify_absence
    print('declared/undeclared honesty ladder')
    undeclared = {'declared': False, 'host': None,
                  'container_state': None, 'source': ''}
    row = classify_absence(undeclared, 'MariaDB', 'suggestion-text')
    check('undeclared substrate -> skip-honest + suggestion',
          row['status'] == 'skip-honest'
          and 'suggestion-text' in row['evidence'])
    stopped = {'declared': True, 'host': None,
               'container_state': 'exited',
               'source': 'container pol-mariadb (exited)'}
    row = classify_absence(stopped, 'MariaDB', 'x')
    check('declared-but-down substrate -> FAIL (red row)',
          row['status'] == 'fail' and 'exited' in row['evidence'])
    resolved = {'declared': True, 'host': '10.0.0.5',
                'container_state': 'running', 'source': 'env'}
    check('resolved substrate -> proceed',
          classify_absence(resolved, 'MariaDB', 'x') is None)


def _live_checks(by_name):
    from testing.check_runners import run_check
    from testing.substrate_env import resolve_mariadb
    reachable = resolve_mariadb()['host'] is not None
    print(f'live substrate checks (staging reachable: {reachable})')
    rows = []
    for name in ('substrate:mariadb-reachability',
                 'substrate:mariadb-credential-honesty',
                 'substrate:mariadb-auto-tables',
                 'substrate:keydb-roundtrip'):
        row = run_check(by_name[name])
        rows.append(row)
        if reachable:
            check(f'{name} green against staging',
                  row['status'] == 'pass', row['evidence'][:100])
        else:
            check(f'{name} honest without staging',
                  row['status'] in ('skip-honest', 'fail'),
                  row['status'])
    if reachable:
        print('dialect parity (two unittest legs, ~minutes)...')
        row = run_check(by_name['substrate:dialect-parity'])
        rows.append(row)
        check('dialect parity identical on sqlite + mariadb',
              row['status'] == 'pass', row['evidence'][:140])
    row = run_check(by_name['substrate:restart-persistence'])
    rows.append(row)
    # Two honest refusals exist: with MariaDB declared, the probe
    # names the disruptive knob; on a host with no substrate at all
    # (the distributed-matrix machines) it skips at declaration —
    # both are the honest path, neither is a pass-through.
    check('restart probe refuses without the disruptive knob',
          row['status'] == 'skip-honest'
          and ('POLARI_ALLOW_DISRUPTIVE' in row['evidence']
               or 'not declared' in row['evidence']))
    return rows


def _secret_hygiene(rows):
    from testing.substrate_env import resolve_keydb, resolve_mariadb
    print('secret hygiene')
    secrets = {resolve_mariadb().get('password'),
               resolve_keydb().get('password')} - {'', None}
    leaked = [row['name'] for row in rows
              if any(secret in row['evidence']
                     for secret in secrets)]
    check('no evidence string leaks a password (repos are public)',
          not leaked, ','.join(leaked))


if __name__ == '__main__':
    by_name = _catalog_rows()
    _honesty_ladder()
    rows = _live_checks(by_name)
    _secret_hygiene(rows)
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
