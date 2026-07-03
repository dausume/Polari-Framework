"""
Self-test for mesh facts + role auto-config (mesh convergence Phase 1).

Run from polari-framework/:
    python3 -m polariPeers.selftest_mesh

mesh_facts is exercised against REAL subprocesses (python3 -c mocks via
POLARI_MESH_FACTS_CMD — exactly how it runs before isle-mesh ships
`isle facts`); role_autoconfig against mocked probes/join.
"""

import json
import os
from types import SimpleNamespace

import polariPeers.role_autoconfig as rac_mod
from polariPeers.mesh_facts import claim_name, get_mesh_facts
from polariPeers.role_autoconfig import auto_configure

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _mock_facts_cmd(payload: dict, path: str = '/tmp/selftest_mesh.json') -> str:
    """Exactly how mesh_facts will be mocked in the twin containers: any
    command that prints JSON. `cat <file>` is the simplest such command."""
    with open(path, 'w') as f:
        json.dump(payload, f)
    return f'cat {path}'


def _manager():
    return SimpleNamespace(objectTables={'PeerAgreement': {}, 'PeerNode': {}},
                           db=None)


def _clear_env():
    for var in ('POLARI_MESH_FACTS_CMD', 'POLARI_MESH_CLAIM_CMD',
                'POLARI_NODE_ROLE', 'POLARI_PARENT_URL',
                'POLARI_DISCOVERY_URLS', 'POLARI_PUBLIC_BASE_URL',
                'POLARI_INSTANCE_NAME', 'POLARI_INSTANCE_ID'):
        os.environ.pop(var, None)


def main():
    print('Mesh facts + role auto-config — detect, claim, discover, decide\n')
    _clear_env()

    # --- mesh_facts: graceful absence ---------------------------------
    os.environ['POLARI_MESH_FACTS_CMD'] = 'definitely-not-a-real-binary-xyz'
    facts = get_mesh_facts()
    check('missing CLI -> unmeshed, never raises',
          facts['meshed'] is False and facts['source'].startswith('absent'))

    os.environ['POLARI_MESH_FACTS_CMD'] = \
        'python3 -c "import sys; sys.exit(3)"'
    facts = get_mesh_facts()
    check('failing CLI (exit 3) -> unmeshed', facts['meshed'] is False
          and 'exit 3' in facts['source'])

    os.environ['POLARI_MESH_FACTS_CMD'] = \
        'python3 -c "print(\'not json at all\')"'
    check('garbage stdout -> unmeshed',
          get_mesh_facts()['meshed'] is False)

    # --- mesh_facts: the mocked happy path ----------------------------
    os.environ['POLARI_MESH_FACTS_CMD'] = _mock_facts_cmd({
        'meshed': True, 'isleName': 'home-isle',
        'devices': ['isle-core', 'b-host'],
        'claims': {'polari-a.isle': 'isle-core'}})
    facts = get_mesh_facts()
    check('mocked facts parse (meshed, isle, devices, claims)',
          facts['meshed'] is True and facts['isleName'] == 'home-isle'
          and facts['devices'] == ['isle-core', 'b-host']
          and facts['claims'] == {'polari-a.isle': 'isle-core'}
          and facts['source'] == 'cli')

    # --- claim: absence + mock ----------------------------------------
    os.environ['POLARI_MESH_CLAIM_CMD'] = 'nope-no-such-cmd {name}'
    claim = claim_name('polari-x.isle')
    check('claim with no CLI -> unavailable, not claimed',
          claim['claimed'] is False and claim['available'] is False)
    os.environ['POLARI_MESH_CLAIM_CMD'] = _mock_facts_cmd(
        {'claimed': True, 'owner': 'me'}, path='/tmp/selftest_claim.json')
    claim = claim_name('polari-x.isle')
    check('mocked claim succeeds atomically',
          claim['claimed'] is True and claim['available'] is True)

    # --- role auto-config ----------------------------------------------
    os.environ['POLARI_MESH_FACTS_CMD'] = 'definitely-not-a-real-binary-xyz'
    real_probe = rac_mod._probe_polari
    try:
        # Unmeshed, nothing to discover -> parent (standalone leads).
        rac_mod._probe_polari = lambda url: {'_error': 'unreachable'}
        report = auto_configure(_manager())
        check('unmeshed + nothing found -> parent, evidence-logged no-op',
              report['role'] == 'parent' and report['meshed'] is False
              and any('none found' in e for e in report['evidence']))

        # Discovery finds a live Polari -> auto says child + join fires.
        os.environ['POLARI_DISCOVERY_URLS'] = 'http://a:3000'
        os.environ['POLARI_PUBLIC_BASE_URL'] = 'http://b:3000'
        os.environ['POLARI_INSTANCE_NAME'] = 'polari-b'
        rac_mod._probe_polari = lambda url: {
            'instanceName': 'polari-a', 'framework': 'polari'}
        join_calls = []
        import polariPeers.join_flow as jf_mod
        real_join = jf_mod.join_parent

        def fake_join(manager, parent_url, my_url, max_polls=1):
            join_calls.append((parent_url, my_url))
            return {'joined': True, 'evidence': ['(mock join)']}
        jf_mod.join_parent = fake_join
        try:
            report = auto_configure(_manager())
        finally:
            jf_mod.join_parent = real_join
        check('live Polari discovered -> child + join request sent',
              report['role'] == 'child' and report['joined'] is True
              and join_calls == [('http://a:3000', 'http://b:3000')])

        # The role knob outranks the evidence.
        os.environ['POLARI_NODE_ROLE'] = 'parent'
        report = auto_configure(_manager())
        check('role knob parent overrides child evidence',
              report['role'] == 'parent'
              and any('knob' in e for e in report['evidence']))
        os.environ['POLARI_NODE_ROLE'] = 'child'
        os.environ.pop('POLARI_DISCOVERY_URLS')
        rac_mod._probe_polari = lambda url: {'_error': 'unreachable'}
        report = auto_configure(_manager())
        check('role knob child with no reachable parent -> joined False, '
              'retryable', report['role'] == 'child'
              and report['joined'] is False)
        os.environ.pop('POLARI_NODE_ROLE')

        # Child without POLARI_PUBLIC_BASE_URL cannot join (clear evidence).
        os.environ['POLARI_DISCOVERY_URLS'] = 'http://a:3000'
        os.environ.pop('POLARI_PUBLIC_BASE_URL')
        rac_mod._probe_polari = lambda url: {
            'instanceName': 'polari-a', 'framework': 'polari'}
        report = auto_configure(_manager())
        check('child without a public base url: no join, evidence says why',
              report['joined'] is False
              and any('POLARI_PUBLIC_BASE_URL' in e
                      for e in report['evidence']))

        # Self-discovery is filtered out (a node never parents itself).
        os.environ['POLARI_INSTANCE_NAME'] = 'polari-a'
        report = auto_configure(_manager())
        check('discovering ONLY yourself -> parent (self filtered)',
              report['role'] == 'parent')
    finally:
        rac_mod._probe_polari = real_probe
        _clear_env()

    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
