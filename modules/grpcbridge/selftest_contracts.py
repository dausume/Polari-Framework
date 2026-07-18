"""
Selftest for grpcbridge (grpc-1, contract layer).

Run from polari-framework/:
  python3 -m grpcbridge.selftest_contracts

Stdlib-only, fake manager + injected factories (same idiom as
selftest_schema_stability). Covers: the stabilization gate (refusal
names the stabilize knob), type mapping (int→int64, bool→bool,
float→double, str→string, variant/complex→string+JSON comment),
generation from the TRUSTED snapshot (not live typing), the
tag-number ledger across regenerations (kept / next-free / reserved
on removal / reserved on retype), destabilization flipping the
exposure stale through the REAL record_deviation hook, hash
stability (occurrence counts can't churn it; type changes do),
check_contracts drift detection + suggestions, the catalogue's
candidates, disable, and the knob-defaults-off contract of the
basis class signature.
"""

import inspect
import json
import types

from grpcbridge import proto_gen as pg
from polariDataTyping import schema_stability as ss

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


class FakeDB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(row)


SNAPSHOT = {
    'count': {'dominantType': 'int', 'dominantAffinity': 'INTEGER',
              'schemaStrategy': 'typed'},
    'active': {'dominantType': 'bool', 'dominantAffinity': 'INTEGER',
               'schemaStrategy': 'typed'},
    # The live framework stores Python bools as TEXT — the wire must
    # STILL carry a real 1-byte bool (MCU cost: 'True' as a string is
    # 7 wire bytes + a 64-byte firmware buffer).
    'armed': {'dominantType': 'bool', 'dominantAffinity': 'TEXT',
              'schemaStrategy': 'typed'},
    'ratio': {'dominantType': 'float', 'dominantAffinity': 'REAL',
              'schemaStrategy': 'typed'},
    'label': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
              'schemaStrategy': 'typed'},
    'extras': {'dominantType': 'dict', 'dominantAffinity': 'TEXT',
               'schemaStrategy': 'variant'},
    'manager': {'dominantType': 'managerObject',
                'dominantAffinity': 'TEXT', 'schemaStrategy': 'typed'},
}


def _mgr(stabilized=True, snapshot=None):
    mgr = types.SimpleNamespace(
        objectTables={'SchemaStabilityProfile': {},
                      'SchemaDeviationEvent': {},
                      'GrpcExposure': {},
                      'ProtoContractVersion': {}},
        objectTypingDict={},
        db=FakeDB())
    if stabilized:
        profile = _factory(
            name='Widget-schema-stability', subject_class='Widget',
            status='stabilized', stabilize_threshold=4,
            clean_saves=4, total_saves=4, deviation_count=0,
            destabilize_count=0,
            field_summary_json=json.dumps(snapshot or SNAPSHOT),
            stabilized_at='2026-07-09T00:00:00+00:00',
            destabilized_at='', skipped_analyses=0, notes='')
        mgr.objectTables['SchemaStabilityProfile'][profile.name] = \
            profile
    return mgr


def _track(mgr, row, table):
    mgr.objectTables[table][getattr(row, 'name', str(id(row)))] = row


def _enable(mgr):
    """enable + register the created rows in the fake tables (the
    real object tree does this registration in production)."""
    report = pg.exposure_action(mgr, 'Widget', 'enable',
                                exposure_factory=_factory,
                                version_factory=_factory)
    if report.get('ok'):
        _track(mgr, report['exposure'], 'GrpcExposure')
        # version row was created inside generate_contract
        for row in mgr.db.saved:
            if getattr(row, 'version', None) is not None \
                    and getattr(row, 'field_map_json', None):
                _track(mgr, row, 'ProtoContractVersion')
    return report


def main():
    ss._STATUS_CACHE.clear()

    # --- the gate: refusal names the stabilize knob ---------------------
    mgr = _mgr(stabilized=False)
    report = pg.exposure_action(mgr, 'Widget', 'enable',
                                exposure_factory=_factory,
                                version_factory=_factory)
    check('gate: non-stabilized class refused',
          not report.get('ok') and 'not stabilized' in report['error'])
    check('gate: refusal suggestion names the stabilize knob',
          report.get('suggestion', {}).get('knob')
          == '/api/schema/stability/Widget')

    # --- generation from the trusted snapshot ----------------------------
    ss._STATUS_CACHE.clear()
    mgr = _mgr()
    report = _enable(mgr)
    check('enable: stabilized class generates v1 + enables',
          report.get('ok') and report['version'] == 1
          and report['exposure'].enabled is True)
    exposure = report['exposure']
    proto = exposure.proto_text
    check('mapping: int → int64', 'int64 count = ' in proto)
    check('mapping: bool → bool', 'bool active = ' in proto)
    check('mapping: TEXT-affinity bool STILL → wire bool (MCU cost)',
          'bool armed = ' in proto)
    check('mapping: float → double', 'double ratio = ' in proto)
    check('mapping: str → string', 'string label = ' in proto)
    check('mapping: variant → string + honest JSON comment',
          'string extras = ' in proto
          and 'JSON-encoded (schema strategy: variant)' in proto)
    check('internal fields never reach the wire',
          ' manager = ' not in proto)
    check('service block: Get/List/Watch/Push/Commands all present',
          all(s in proto for s in
              ('service WidgetSync', 'rpc Get (ObjectKey)',
               'rpc List (ListRequest) returns (stream Widget)',
               'rpc Watch (WatchRequest)',
               'rpc Push (stream Widget) returns (PushSummary)',
               'rpc Commands (WatchRequest) returns (stream Widget)')))
    check('shared messages: ChangeNotification mirrors the STOMP '
          'payload fields',
          all(f in proto for f in
              ('string class_name = 1', 'string operation = 2',
               'string timestamp = 3',
               'repeated string instance_ids = 4',
               'string format_type = 5')))
    check('exposure stamped current with hash + service name',
          exposure.contract_status == 'current'
          and exposure.contract_hash
          and exposure.service_name == 'PolariObjectSync.Widget')

    # --- hash stability ---------------------------------------------------
    h1 = pg.contract_hash(SNAPSHOT)
    noisy = json.loads(json.dumps(SNAPSHOT))
    noisy['count']['totalOccurrences'] = 99999  # wire-irrelevant
    changed = json.loads(json.dumps(SNAPSHOT))
    changed['count']['dominantAffinity'] = 'TEXT'
    changed['count']['dominantType'] = 'str'
    check('hash: stable across occurrence-count churn',
          pg.contract_hash(noisy) == h1)
    check('hash: changes when a field retypes',
          pg.contract_hash(changed) != h1)

    # --- tag ledger across regeneration ------------------------------------
    v1_map = pg.merge_field_map(SNAPSHOT)
    tag_of = lambda m, f: m['fields'][f]['tag']  # noqa: E731
    grown = json.loads(json.dumps(SNAPSHOT))
    grown['flow_rate'] = {'dominantType': 'float',
                          'dominantAffinity': 'REAL',
                          'schemaStrategy': 'typed'}
    del grown['label']
    grown['count']['dominantAffinity'] = 'TEXT'  # retype int → str
    grown['count']['dominantType'] = 'str'
    v2_map = pg.merge_field_map(grown, v1_map)
    check('tags: unchanged fields keep their tags',
          tag_of(v2_map, 'ratio') == tag_of(v1_map, 'ratio')
          and tag_of(v2_map, 'extras') == tag_of(v1_map, 'extras'))
    check('tags: new field takes a never-used tag',
          tag_of(v2_map, 'flow_rate') not in
          {s['tag'] for s in v1_map['fields'].values()})
    check('tags: removed field surrenders its tag to reserved',
          tag_of(v1_map, 'label') in v2_map['reserved'])
    check('tags: retyped field gets a NEW tag, old tag reserved',
          tag_of(v2_map, 'count') != tag_of(v1_map, 'count')
          and tag_of(v1_map, 'count') in v2_map['reserved'])
    rendered = pg.render_message('Widget', v2_map)
    check('render: reserved statement emitted',
          'reserved ' in rendered)

    # --- regenerate through the profile (trusted snapshot updates) ---------
    profile = mgr.objectTables['SchemaStabilityProfile'][
        'Widget-schema-stability']
    profile.field_summary_json = json.dumps(grown)
    v1_row_map = json.loads(
        pg.get_versions(mgr, 'Widget')[0].field_map_json)
    report2 = pg.exposure_action(mgr, 'Widget', 'regenerate',
                                 version_factory=_factory)
    check('regenerate: v2 with preserved ledger',
          report2.get('ok') and report2['version'] == 2
          and tag_of(json.loads(
              report2['versionRow'].field_map_json), 'ratio')
          == tag_of(v1_row_map, 'ratio'))

    # --- OOPS flips the exposure stale (through REAL record_deviation) -----
    check('pre-OOPS: contract current',
          exposure.contract_status == 'current')
    ss.record_deviation(mgr, 'Widget', field='count',
                        actual_type='str', payload={'count': 'abc'},
                        db_error="Incorrect integer value: 'abc' for "
                                 "column `db`.`Widget`.`count`",
                        factory=_factory, event_factory=_factory)
    check('OOPS: record_deviation marks the exposure stale',
          exposure.contract_status == 'stale')
    check('OOPS: staleness note carries evidence',
          'schema deviation on field "count"' in exposure.notes)

    # --- check_contracts: drift + suggestions -------------------------------
    freshness = pg.check_contracts(mgr)
    check('check_contracts: stale exposure surfaces a regenerate '
          'suggestion',
          freshness['stale'] == ['Widget']
          and freshness['suggestions'][0]['knob']
          == '/api/grpc/exposures/Widget')

    # hash drift alone (no OOPS) also marks stale
    ss._STATUS_CACHE.clear()
    mgr2 = _mgr()
    rep = _enable(mgr2)
    drifted = json.loads(json.dumps(SNAPSHOT))
    drifted['ratio']['dominantAffinity'] = 'TEXT'
    drifted['ratio']['dominantType'] = 'str'
    mgr2.objectTables['SchemaStabilityProfile'][
        'Widget-schema-stability'].field_summary_json = \
        json.dumps(drifted)
    fresh2 = pg.check_contracts(mgr2)
    check('check_contracts: snapshot drift (no OOPS) marks stale',
          rep['exposure'].contract_status == 'stale'
          and fresh2['stale'] == ['Widget'])

    # --- catalogue: candidates are stabilized-but-unexposed classes --------
    ss._STATUS_CACHE.clear()
    mgr3 = _mgr()
    cat = pg.exposure_catalogue(mgr3)
    check('catalogue: stabilized class without exposure is a '
          'candidate with the enable knob named',
          cat['candidates']
          and cat['candidates'][0]['class'] == 'Widget'
          and 'action": "enable' in cat['candidates'][0]['how'])

    # --- disable ------------------------------------------------------------
    _enable(mgr3)
    rep = pg.exposure_action(mgr3, 'Widget', 'disable')
    exp3 = pg.get_exposure(mgr3, 'Widget')
    check('disable: knob off, contract kept',
          rep.get('ok') and exp3.enabled is False
          and exp3.proto_text)
    check('unknown action refused',
          not pg.exposure_action(mgr3, 'Widget', 'bogus').get('ok'))

    # --- knob defaults off on the real basis class ---------------------------
    from grpcbridge.contract_basis import GrpcExposure
    params = inspect.signature(GrpcExposure.__init__).parameters
    check('knob: GrpcExposure.enabled defaults to False',
          params['enabled'].default is False)
    check('knob: transport_preference defaults to stomp '
          '(byte-identical behavior until flipped)',
          params['transport_preference'].default == 'stomp')

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
