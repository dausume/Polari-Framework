"""
Self-test for the ssp-3 backend half (crystal_analysis): payload
shape, honest worker-absent refusal, agreement verdict + suggestion
on space-group disagreement, and the on-row analysis cache. The
worker itself (pymatgen) is exercised in-container — here remote_post
is faked, exactly like the other remote-laddered engine tests.

Run from polari-framework/:
    python3 -m materialsScience.selftest_crystal_analysis
"""

import json
import os
import sys
from types import SimpleNamespace

from materialsScience import crystal_analysis
from materialsScience.engines import remote
from materialsScience.crystal_structures_seed import (
    SEED_CRYSTAL_STRUCTURES,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def _seed(name):
    return next(s for s in SEED_CRYSTAL_STRUCTURES
                if s['name'] == name)


def _row(name):
    return SimpleNamespace(**_seed(name), last_analysis_json='{}')


class _FakeDB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(getattr(row, 'name', ''))
        return True


def test_payload():
    print('[worker payload]')
    verdict = crystal_analysis.structure_payload(
        _seed('rock-salt-nacl'))
    check('payload builds', verdict['ok'])
    payload = verdict['payload']
    check('P1 cell: 8 symbols, 8 frac, 3x3 cell',
          len(payload['symbols']) == 8 and len(payload['frac']) == 8
          and len(payload['cell']) == 3)
    check('fractional coords wrapped into [0, 1)',
          all(0 <= v < 1.0 for pos in payload['frac'] for v in pos))
    broken = dict(_seed('rock-salt-nacl'), basis_json='[]')
    verdict = crystal_analysis.structure_payload(broken)
    check('build refusal passes through', not verdict['ok'])


def test_worker_absent_refusal():
    print('[no worker -> honest refusal]')
    previous = os.environ.pop('MSCI_ENGINES_URL', None)
    try:
        verdict = crystal_analysis.analyze(_row('silicon-diamond'))
        check('refuses with the MSCI_ENGINES_URL knob named',
              not verdict.get('ok')
              and 'MSCI_ENGINES_URL'
              in verdict['suggestion']['knob'])
    finally:
        if previous is not None:
            os.environ['MSCI_ENGINES_URL'] = previous


def test_agreement_and_suggestion():
    print('[declared-vs-detected verdict]')
    original = remote.remote_post
    calls = {}

    def fake_post(path, payload, timeout=300):
        calls['path'] = path
        return {'ok': True, 'spaceGroupSymbol': 'Fd-3m',
                'spaceGroupNumber': calls['detected'],
                'crystalSystem': 'cubic', 'pointGroup': 'm-3m',
                'wyckoffSites': [], 'primitiveAtomCount': 2,
                'inputAtomCount': 8}

    remote.remote_post = fake_post
    try:
        manager = SimpleNamespace(db=_FakeDB())
        row = _row('silicon-diamond')
        calls['detected'] = 227
        report = crystal_analysis.analyze(row, manager)
        check('matching detection agrees, no suggestion',
              report['ok'] and report['agreesWithDeclared']
              and 'suggestion' not in report)
        cached = json.loads(row.last_analysis_json)
        check('symmetry report cached ON the row (+timestamp)',
              cached['symmetry']['spaceGroupNumber'] == 227
              and 'cachedAt' in cached)
        check('cache persisted through the manager db',
              manager.db.saved == [row.name])

        calls['detected'] = 221
        report = crystal_analysis.analyze(row, manager)
        check('disagreement -> evidence-bearing suggestion on the '
              'space_group knob (never auto-applied)',
              report['ok'] and not report['agreesWithDeclared']
              and report['suggestion']['knob'] == 'space_group'
              and '#227' in report['suggestion']['evidence'])
    finally:
        remote.remote_post = original


def test_xrd_path():
    print('[xrd delegation + cache]')
    original = remote.remote_post

    def fake_post(path, payload, timeout=300):
        if path != '/structure/xrd':
            return {'ok': False, 'error': f'wrong path {path}'}
        return {'ok': True, 'wavelength': payload['wavelength'],
                'peaks': [{'twoTheta': 28.44, 'intensity': 100.0,
                           'hkl': [[1, 1, 1]], 'dSpacingA': 3.135}],
                'peakCount': 1}

    remote.remote_post = fake_post
    try:
        manager = SimpleNamespace(db=_FakeDB())
        row = _row('silicon-diamond')
        report = crystal_analysis.xrd(row, manager,
                                      wavelength='CuKa')
        check('xrd delegates and returns peaks',
              report['ok'] and report['peaks'][0]['hkl'] == [[1, 1, 1]])
        cached = json.loads(row.last_analysis_json)
        check('xrd cached ON the row',
              cached['xrd']['peakCount'] == 1)
    finally:
        remote.remote_post = original


def main():
    test_payload()
    test_worker_absent_refusal()
    test_agreement_and_suggestion()
    test_xrd_path()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
