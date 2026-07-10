"""
Selftest — xsim-1: reference format + local resolution rungs +
identity map.

Run from polari-framework/:
    python3 -m polariRefs.selftest_refs

Covers the xsim-1 acceptance + edge-case ledger rows: bare refs resolve
exactly as before (byte-identical through component_binding);
authority-carrying refs parse; the local rung resolves via the identity
map; non-local rungs refuse honestly naming their phase; identity map
keeps two authorities distinct; schemaVersion mismatch refuses naming
both versions; rung-2 RowView is read-only.
"""

import json
import os
from types import SimpleNamespace

from materialsScience.component_binding import resolve_binding
from polariRefs.identity_map import RefIdentityMap, identity_map_for
from polariRefs.ref_format import (
    is_authority_ref, parse_ref, schema_version_of,
)
from polariRefs.resolver import resolve_ref, resolve_ref_value, walk_path

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _Row:
    """Weakref-able stand-in for a treeObject row."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakeDB:
    def __init__(self, tables):
        self._tables = tables

    def getAllInTable(self, table_name):
        columns, rows = self._tables[table_name]
        return columns, rows


def _mgr():
    rod = _Row(id='AAAAAAAA1', name='steel-rod',
               parameters_json=json.dumps(
                   {'inputs': {'matrixK': [[1, 0], [0, 1]]}}),
               last_result_json=json.dumps(
                   {'percolationThreshold': 0.163}))
    profile = _Row(id='PROF00001', name='ssp-MaterialScaleDefinition',
                   subject_class='MaterialScaleDefinition',
                   field_summary_json=json.dumps(
                       {'name': {'type': 'str'},
                        'last_result_json': {'type': 'str'}}))
    demoted_columns = ['id', 'name', 'sigma', '_instance_id']
    demoted_rows = [('DEMOTED01', 'cold-object', 157.7, 'a')]
    return SimpleNamespace(
        objectTables={
            'MaterialScaleDefinition': {rod.id: rod},
            'SchemaStabilityProfile': {profile.id: profile}},
        objectTyping=[],
        dynamicClasses={},
        db=_FakeDB({'DemotedThing': (demoted_columns, demoted_rows)}),
    ), rod


if __name__ == '__main__':
    os.environ.setdefault('POLARI_INSTANCE_ID', 'a')
    manager, rod = _mgr()

    print('ref format — parse + normalize')
    ok, ref, _ = parse_ref({'kind': 'objectRef',
                            'className': 'MaterialScaleDefinition',
                            'name': 'steel-rod', 'path': 'x.y'})
    check('bare ref parses with authority=None',
          ok and ref['authority'] is None)
    ok, ref, _ = parse_ref({'kind': 'objectRef',
                            'authority': {'instance': 'b'},
                            'className': 'MaterialScaleDefinition',
                            'id': 'AAAAAAAA1'})
    check("authority {'instance':'b'} parses",
          ok and ref['authority'] == {'instance': 'b'})
    ok, _, refusal = parse_ref({'kind': 'objectRef',
                                'authority': {'instance': 'b',
                                              'module': 'x'},
                                'className': 'C', 'name': 'n'})
    check('authority with two coordinates refuses',
          not ok and 'exactly one' in refusal['error'])
    ok, _, refusal = parse_ref({'kind': 'objectRef', 'className': 'C'})
    check('ref naming no row refuses', not ok
          and 'name' in refusal['error'])
    check('is_authority_ref only claims authority-carrying refs',
          is_authority_ref({'kind': 'objectRef', 'authority': {},
                            'className': 'C'})
          and not is_authority_ref({'kind': 'objectRef',
                                    'className': 'C', 'name': 'n'}))

    print('identity map — two authorities never collapse')
    imap = RefIdentityMap()
    row_a, row_b = _Row(id='5'), _Row(id='5')
    imap.register('instance:a', 'Thing', '5', row_a)
    imap.register('instance:b', 'Thing', '5', row_b)
    check('same (class,id) under two authorities stays two objects',
          imap.get('instance:a', 'Thing', '5') is row_a
          and imap.get('instance:b', 'Thing', '5') is row_b)
    reg = imap.register('instance:a', 'Thing', '5', _Row(id='5'))
    check('re-register hands back the canonical live object',
          reg['instance'] is row_a and 'already' in reg['note'])
    live_before = imap.live_count()
    del row_b, reg
    check('weakref values: dead objects leave the map',
          imap.live_count() < live_before
          and imap.get('instance:b', 'Thing', '5') is None)

    print('resolution ladder — local rungs')
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority': None,
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod'})
    check('rung 1 local tree resolves by name',
          result['ok'] and result['object'] is rod
          and result['provenance']['rung'] == 'local-tree')
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className':
                                       'MaterialScaleDefinition',
                                   'id': 'AAAAAAAA1'})
    check('rung 1 resolves by id (direct objectTables key)',
          result['ok'] and result['object'] is rod)
    check('rung 1 registered in the identity map',
          identity_map_for(manager).get(
              'local', 'MaterialScaleDefinition', 'AAAAAAAA1') is rod)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className': 'DemotedThing',
                                   'name': 'cold-object'})
    check('rung 2 local DB resolves a demoted row (RowView)',
          result['ok'] and getattr(result['object'], 'sigma', None)
          == 157.7 and result['provenance']['rung'] == 'local-db')
    view = result['object'] if result['ok'] else None
    refused_write = False
    try:
        view.sigma = 999
    except AttributeError as e:
        refused_write = 'xsim-2' in str(e)
    check('RowView write refuses naming the lease phase (xsim-2)',
          refused_write)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'no-such-row'})
    check('local miss refuses listing the rungs tried',
          not result['ok']
          and result['refusal'].get('tried') == ['local-tree',
                                                 'local-db'])

    print('resolution ladder — non-local rungs refuse naming phase')
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority': {'instance': 'b'},
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod'})
    check("authority instance 'b' without a shared DB refuses naming "
          'the xsim-6 rung',
          not result['ok']
          and 'xsim-6' in result['refusal'].get('phase', '')
          and "'b'" in result['refusal']['error'])
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority': {'instance': 'a'},
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod'})
    check("authority instance 'a' (this instance) resolves locally",
          result['ok'] and result['object'] is rod)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority':
                                       {'module': 'materialsScience'},
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod'})
    check('module authority + class installed locally resolves '
          '(no topology in selftest)',
          result['ok'] and result['object'] is rod)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority':
                                       {'module': 'notInstalled'},
                                   'className': 'GhostClass',
                                   'name': 'x'})
    check('uninstalled module refuses naming the allocate knob',
          not result['ok'] and 'pol allocate'
          in result['refusal']['suggestion']['action'])

    print('schemaVersion honesty')
    local_v = schema_version_of(manager, 'MaterialScaleDefinition')
    check('local schema version derives from the stability profile',
          len(local_v) == 16)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod',
                                   'schemaVersion': 'deadbeef00000000'})
    check('mismatch refuses naming BOTH versions',
          not result['ok']
          and 'deadbeef00000000' in result['refusal']['error']
          and local_v in result['refusal']['error'])
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'steel-rod',
                                   'schemaVersion': local_v})
    check('matching version resolves', result['ok'])
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'className': 'DemotedThing',
                                   'name': 'cold-object',
                                   'schemaVersion': 'abc'})
    check('unknown local version resolves with an unverified note',
          result['ok'] and 'schemaVersionUnverified'
          in result['provenance'])

    print('path walking + binding integration (bare refs UNTOUCHED)')
    ok, value, _ = walk_path(rod, 'last_result_json.'
                                  'percolationThreshold')
    check('walk_path descends attributes + JSON blobs',
          ok and value == 0.163)
    bare = {'kind': 'objectRef',
            'className': 'MaterialScaleDefinition',
            'name': 'steel-rod',
            'path': 'parameters_json.inputs.matrixK.0.1'}
    ok, value, refusal = resolve_binding(manager, bare)
    check('bare objectRef through resolve_binding still resolves',
          ok and value == 0, extra=f'refusal={refusal}' if not ok else '')
    authority_bound = dict(bare, authority={'instance': 'a'},
                           path='last_result_json.percolationThreshold')
    ok, value, _ = resolve_binding(manager, authority_bound)
    check('authority ref through resolve_binding rides the ladder',
          ok and value == 0.163)
    ok, _, refusal = resolve_binding(
        manager, dict(bare, authority={'instance': 'b'}))
    check('remote authority through resolve_binding refuses honestly',
          not ok and 'xsim-6' in (refusal or {}).get('phase', ''))
    ok, _, refusal = resolve_ref_value(
        manager, dict(bare, path='parameters_json.nope'))
    check('path miss refuses listing available keys',
          not ok and refusal.get('availableKeys') == ['inputs'])

    print('rung 3 — shared-DB peer read (xsim-3)')

    class _SharedDB:
        """Emulates the shared object DB holding instance b's rows."""
        def __init__(self, on=True):
            self.on = on
            self.peer_tables = {
                'MaterialScaleDefinition': (
                    ['id', 'name', 'last_result_json', '_instance_id'],
                    [('AAAAAAAA1', 'steel-rod',
                      json.dumps({'percolationThreshold': 0.201}),
                      'b')]),
                'GhostClass': (
                    ['id', 'name', 'sigma', '_instance_id'],
                    [('GH0ST0001', 'phantom', 42.5, 'b')]),
                '_dynamic_class_registry': (
                    ['className', 'variables'],
                    [('GhostClass', json.dumps(
                        [{'name': 'name'}, {'name': 'sigma'}]))]),
                'SchemaStabilityProfile': (
                    ['subject_class', 'field_summary_json'],
                    [('MaterialScaleDefinition', json.dumps(
                        {'name': {'type': 'str'},
                         'last_result_json': {'type': 'str'},
                         'extraPeerField': {'type': 'float'}}))]),
            }

        def getAllInTableForInstance(self, table, scope):
            if not self.on:
                return {'ok': False,
                        'error': 'shared object DB is off '
                                 '(POLARI_SHARED_OBJECT_DB)'}
            columns, rows = self.peer_tables.get(table, ([], []))
            return {'ok': True, 'columns': columns,
                    'rows': [r for r in rows]}

    manager.db = _SharedDB(on=False)
    b_ref = {'kind': 'objectRef', 'authority': {'instance': 'b'},
             'className': 'MaterialScaleDefinition',
             'name': 'steel-rod'}
    result = resolve_ref(manager, b_ref)
    check('shared DB off → refusal names xsim-6 + the DB knob',
          not result['ok']
          and 'xsim-6' in result['refusal'].get('phase', ''))
    manager.db = _SharedDB(on=True)
    result = resolve_ref(manager, b_ref)
    check('shared DB on but NO PeerAgreement → refusal names the '
          'join flow',
          not result['ok'] and 'PeerAgreement'
          in result['refusal']['error'])
    agreement = _Row(id='AGR000001', status='approved',
                     requester_name='polari-b',
                     approver_name='polari-a',
                     agreement_id='agr-b-1', scope='peer-basic')
    manager.objectTables['PeerAgreement'] = {agreement.id: agreement}
    result = resolve_ref(manager, b_ref)
    check("approved agreement → instance b's row hydrates "
          '(GenericRemoteObject)',
          result['ok']
          and result['provenance']['rung'] == 'shared-db-peer'
          and result['provenance']['agreement'] == 'agr-b-1')
    remote_rod = result['object'] if result['ok'] else None
    check("b's row 5 and local row 5 stay TWO objects (identity map)",
          remote_rod is not rod
          and identity_map_for(manager).get(
              'instance:b', 'MaterialScaleDefinition',
              'AAAAAAAA1') is remote_rod
          and identity_map_for(manager).get(
              'local', 'MaterialScaleDefinition',
              'AAAAAAAA1') is rod)
    ok, value, _ = resolve_ref_value(
        manager, dict(b_ref,
                      path='last_result_json.percolationThreshold'))
    check("path walk reads b's DIFFERENT value through the same ref "
          'shape', ok and value == 0.201)
    refused_write = False
    try:
        remote_rod.sigma = 1
    except AttributeError as e:
        refused_write = 'xsim-4' in str(e)
    check('write to a remote object refuses naming xsim-4',
          refused_write)
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority': {'instance': 'b'},
                                   'className': 'GhostClass',
                                   'name': 'phantom'})
    check('UNINSTALLED class hydrates typed from the peer registry',
          result['ok'] and result['object'].sigma == 42.5
          and result['provenance']['typedFrom']
          == 'peer-dynamic-class-registry')
    result = resolve_ref(manager, dict(
        b_ref, schemaVersion='deadbeef00000000'))
    check("schemaVersion mismatch vs the OWNER's profile names both",
          not result['ok'] and 'deadbeef00000000'
          in result['refusal']['error']
          and "'b'" in result['refusal']['error'])
    result = resolve_ref(manager, {'kind': 'objectRef',
                                   'authority': {'instance': 'b'},
                                   'className':
                                       'MaterialScaleDefinition',
                                   'name': 'not-on-b'})
    check("missing peer row → refusal names the owner instance",
          not result['ok'] and "'b'" in result['refusal']['error'])

    total, green = len(_results), sum(_results)
    print(f'\n{green}/{total} checks green')
    raise SystemExit(0 if green == total else 1)
