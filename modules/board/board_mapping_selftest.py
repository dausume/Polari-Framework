"""board_mapping_selftest — brd-wire's half of the board selftest (called by board.board_selftest): the `mapping` section.
The computer↔firmware mapping as ROWS (grpc-j4, his ruling 2026-10-02 + his clarification on the index): the seeded enum
tables and the uno-pair bindings; the WireContract derived from rows (hash v1 + v2, the index representation, the
knob, the suggestion); the index width as a pure function of the bound count, through the rows at n = 1..257 (fakes —
three-or-more simavr twins are the probe's job); one object = one interface; the same firmware built for instance 0 and
1 (same wire, different index), an index that does not fit refused; compat judged on hash v2 when a third interface is
bound; and the binding chain an analysis walks (object → … → datasheet facts) plus its API door.

The REAL two-twin proof (simavr ×2, the generated bridge, index 0/1 routing both ways, the presence-mask toggle) is
tests/board_pair_probe.py.
"""
import json
import os
import tempfile
import types


class _M:
    def __init__(self, *classes):
        self.objectTables = {c: {} for c in classes}
        self.idList = []
        self.db = None

    def persistTree(self):
        return None

    def noteTreeMutation(self, *a, **k):
        return None


def _mgr():
    return _M('HardwareInterfaceBinding', 'EnumMapping', 'WireContract', 'GrpcExposure', 'ProtoContractVersion', 'SimRigState',
              'BoardDefinition', 'DatasheetFact', 'BoardInstance', 'AdapterDefinition', 'FirmwareVariant')


def _seed(m):
    from grpcbridge.mapping_basis import SEED_ENUM_MAPPINGS, SEED_HARDWARE_BINDINGS, EnumMapping, HardwareInterfaceBinding
    from board.board_basis import BoardDefinition, DatasheetFact
    from board.custom.register_map import board_rows
    from board.custom.uno_facts import SEED_UNO_FACTS
    for r in SEED_ENUM_MAPPINGS:
        EnumMapping(manager=m, **r)
    for r in SEED_HARDWARE_BINDINGS:
        HardwareInterfaceBinding(manager=m, **r)
    for r in board_rows():
        if r['name'] == 'arduino-uno-r3':
            BoardDefinition(manager=m, **{k: v for k, v in r.items() if not k.startswith('_')})
    for r in SEED_UNO_FACTS:
        DatasheetFact(manager=m, **{k: v for k, v in r.items() if not k.startswith('_')})


def _rows(m, cls):
    return list(m.objectTables.get(cls, {}).values())


def rows_and_rules(check, m, fm, v1hash):
    from grpcbridge.mapping_basis import SEED_ENUM_MAPPINGS, SEED_HARDWARE_BINDINGS, HardwareInterfaceBinding
    from grpcbridge.custom import wire_contract as W
    check('mapping: seeded EnumMappings — SimRigState.status {boot, ok, commanded, echoed, fault}, UnoAnalogState.status',
          [e['name'] for e in SEED_ENUM_MAPPINGS] == ['SimRigState.status', 'UnoAnalogState.status']
          and json.loads(SEED_ENUM_MAPPINGS[0]['labels_json']) == ['boot', 'ok', 'commanded', 'echoed', 'fault'])
    check('mapping: two seeded bindings on ONE bridge (uno-pair): rows uno-twin-0 / -1 ↔ twin instances #0 / #1, index 0 / 1, '
          'distinct ports, interface usart0',
          [(b['object_name'], b['board_instance'], b['instance_index']) for b in SEED_HARDWARE_BINDINGS]
          == [('uno-twin-0', 'twin:arduino-uno-r3#0', 0), ('uno-twin-1', 'twin:arduino-uno-r3#1', 1)]
          and len({b['port'] for b in SEED_HARDWARE_BINDINGS}) == 2 and {b['bridge_name'] for b in SEED_HARDWARE_BINDINGS} == {'uno-pair'})
    row, s = W.derive(m, 'SimRigState', 'uno-pair', fm, 2, v1hash, 'pinned')
    b = sorted(_rows(m, 'HardwareInterfaceBinding'), key=lambda r: r.instance_index)
    check('mapping: WireContract SimRigState@uno-pair derived FROM ROWS — 2 instances → a 1-bit packed index (wire v2), the '
          'status enum, 1-byte prelude, hash v1 %s kept beside hash v2 %s, both bindings stamped' % (v1hash, s['hash_v2']),
          row.index_repr == 'bits' and row.index_width == 1 and row.instance_count == 2 and row.prelude_bytes == 1
          and json.loads(row.enums_json) == {'status': ['boot', 'ok', 'commanded', 'echoed', 'fault']}
          and row.contract_hash_v1 == v1hash and row.contract_hash_v2 == s['hash_v2'] and row.wire_version == 2
          and all(x.contract_hash_v2 == s['hash_v2'] for x in b), row.notes)
    pair_hash = s['hash_v2']
    third = HardwareInterfaceBinding(manager=m, name='uno-pair/SimRigState/2', bridge_name='uno-pair', object_class='SimRigState',
                                     object_name='uno-twin-2', board_instance='twin:arduino-uno-r3#2', board_definition='arduino-uno-r3',
                                     interface_kind='twin-pty', interface_name='usart0', port='/tmp/polari-uno-twin-2-uart',
                                     instance_index=9)
    row3, s3 = W.derive(m, 'SimRigState', 'uno-pair', fm, 2, v1hash, 'pinned')
    check('mapping: a THIRD interface bound → the index is renumbered densely (9 → 2), the width becomes 2 bits, hash v2 moves '
          '(%s → %s), every binding re-stamped' % (pair_hash, s3['hash_v2']),
          third.instance_index == 2 and row3.index_width == 2 and row3.instance_count == 3 and s3['hash_v2'] != pair_hash
          and all(x.contract_hash_v2 == s3['hash_v2'] for x in _rows(m, 'HardwareInterfaceBinding')), row3.notes)
    del m.objectTables['HardwareInterfaceBinding'][next(k for k, v in m.objectTables['HardwareInterfaceBinding'].items() if v is third)]
    row2, s2 = W.derive(m, 'SimRigState', 'uno-pair', fm, 2, v1hash, 'pinned')
    check('mapping: unbinding it returns the pair to 1 bit and the SAME hash v2 (the hash is a function of the rows)',
          row2.index_width == 1 and s2['hash_v2'] == pair_hash)
    dup = HardwareInterfaceBinding(manager=m, name='uno-pair/SimRigState/dup', bridge_name='uno-pair', object_class='SimRigState',
                                   object_name='uno-twin-0', board_instance='twin:arduino-uno-r3#9', instance_index=5)
    try:
        W.assign_indexes(m, 'uno-pair', 'SimRigState')
        refused = ''
    except W.WireRefused as e:
        refused = str(e)
    check('mapping: two bindings naming the same object are refused (one object = one hardware interface)', 'one object' in refused, refused)
    del m.objectTables['HardwareInterfaceBinding'][next(k for k, v in m.objectTables['HardwareInterfaceBinding'].items() if v is dup)]
    return pair_hash


def scale(check, fm):
    """n = 1..257 THROUGH ROWS (fake binding rows on a fake bridge; the probe proves n = 2 and 3 on real twins)."""
    from grpcbridge.custom import wire_contract as W
    got = {}
    for n in (1, 2, 3, 4, 5, 8, 9, 16, 17, 20, 256, 257):
        m = types.SimpleNamespace(objectTables={'HardwareInterfaceBinding': {}, 'EnumMapping': {}, 'WireContract': {}})
        for k in range(n):
            m.objectTables['HardwareInterfaceBinding']['b%d' % k] = types.SimpleNamespace(
                name='scale/SimRigState/%03d' % k, bridge_name='scale', object_class='SimRigState', object_name='rig-%d' % k,
                instance_index=n - 1 - k, contract_hash_v2='')
        row, s = W.derive(m, 'SimRigState', 'scale', fm, 2, 'v1', 'pinned', factory=lambda manager=None, **f: types.SimpleNamespace(**f))
        idx = sorted(b.instance_index for b in m.objectTables['HardwareInterfaceBinding'].values())
        got[n] = (row.index_repr, row.wire_version, row.index_width, row.index_bytes, row.suggested_index_width, idx == list(range(n)))
    want = {1: ('none', 2, 0, 0, 0), 2: ('bits', 2, 1, 0, 1), 3: ('bits', 2, 2, 0, 2), 4: ('bits', 2, 2, 0, 2), 5: ('bits', 2, 3, 0, 3),
            8: ('bits', 2, 3, 0, 3), 9: ('bits', 2, 4, 0, 4), 16: ('bits', 2, 4, 0, 4), 17: ('byte', 3, 0, 1, 5),
            20: ('byte', 3, 0, 1, 5), 256: ('byte', 3, 0, 1, 8), 257: ('u16', 4, 0, 2, 9)}
    check('mapping at scale (unit level, fake rows): n = 1,2,3,4,5,8,9,16,17,20,256,257 bound → representation / version / '
          'packed bits / index bytes / suggestion as the rule says, indexes dense 0..n-1 every time',
          all(got[n][:5] == want[n] and got[n][5] for n in want), {n: got[n] for n in got if got[n][:5] != want[n] or not got[n][5]})
    m = types.SimpleNamespace(objectTables={'HardwareInterfaceBinding': {}, 'EnumMapping': {}, 'WireContract': {
        'w': types.SimpleNamespace(name='SimRigState@scale', packed_max_bits=5)}})
    for k in range(20):
        m.objectTables['HardwareInterfaceBinding']['b%d' % k] = types.SimpleNamespace(
            name='scale/SimRigState/%02d' % k, bridge_name='scale', object_class='SimRigState', object_name='rig-%d' % k,
            instance_index=k, contract_hash_v2='')
    s = W.spec_for(m, 'SimRigState', 'scale', fm)
    check('mapping: the knob lives on the WireContract row — packed_max_bits 5 there packs 20 instances into 5 bits (v2)',
          s['index_repr'] == 'bits' and s['index_width'] == 5 and s['packed_max_bits'] == 5)


def firmware(check, m, fm, pair_hash):
    from board.custom import gen
    tmp = tempfile.mkdtemp(prefix='board-mapping-')
    r0 = gen.gen('uno', work=os.path.join(tmp, 'p0'), variant='uno-pair', manager=m, instance_index=0)
    r1 = gen.gen('uno', work=os.path.join(tmp, 'p1'), variant='uno-pair', manager=m, instance_index=1)
    c0, c1 = json.loads(r0['classes_json'])[0], json.loads(r1['classes_json'])[0]
    cfg1 = open(os.path.join(r1['project_dir'], 'board_config.h')).read()
    hdr = open(os.path.join(r1['project_dir'], 'simrigstate_packets.h')).read()
    check('mapping: uno-pair built for instance 0 and 1 — the SAME header (sha, hash v2 %s, 1-bit index), a different '
          'INSTANCE_INDEX, SEND_NAME 0 (the binding is the identity)' % c1['hash_v2'],
          c0['header_sha256'] == c1['header_sha256'] and c1['hash_v2'] == pair_hash == r1['contract_hash_v2']
          and r0['source_sha'] != r1['source_sha'] and '#define INSTANCE_INDEX 1u' in cfg1 and '#define SEND_NAME    0' in cfg1
          and 'SIMRIGSTATE_INDEX_WIDTH 1u' in hdr and r1['bridge_name'] == 'uno-pair' and r1['instance_index'] == 1)
    try:
        gen.gen('uno', work=os.path.join(tmp, 'p2'), variant='uno-pair', manager=m, instance_index=2)
        why = ''
    except gen.GenRefused as e:
        why = str(e)
    check('mapping: instance_index 2 on a 2-instance bridge is refused (it does not fit the 1-bit index), naming the fix',
          'does not fit' in why and 'bind another interface' in why, why)
    return r1


def compat_on_v2(check, m, fm, build):
    from board.custom import compat
    from grpcbridge.mapping_basis import HardwareInterfaceBinding
    from grpcbridge.custom import wire_contract as W
    r = compat.check(build, m)
    check('mapping compat: the pair build vs this server (two bindings) → compatible (hash v2 + header sha agree)',
          r['verdict'] == 'compatible' and r['classes'][0]['now_hash_v2'] == r['classes'][0]['built_hash_v2'], r['plain'])
    third = HardwareInterfaceBinding(manager=m, name='uno-pair/SimRigState/2', bridge_name='uno-pair', object_class='SimRigState',
                                     object_name='uno-twin-2', board_instance='twin:arduino-uno-r3#2', instance_index=2)
    r = compat.check(build, m)
    check('mapping compat: a third interface bound → the pair firmware is stale-header (its 1-bit index cannot name 3), '
          'the reason names the bridge',
          r['verdict'] == 'stale-header' and "'uno-pair'" in r['plain'], r['plain'])
    del m.objectTables['HardwareInterfaceBinding'][next(k for k, v in m.objectTables['HardwareInterfaceBinding'].items() if v is third)]
    W.assign_indexes(m, 'uno-pair', 'SimRigState')


def chain(check, m):
    from board.custom.interface_chain import chain as walk
    from grpcbridge.objects.hwsim.SimRigState import SimRigState
    SimRigState(manager=m, name='uno-twin-1', uptime_ms=1200, temp_c=24.7, pwm_duty=42, led_on=False, status='commanded')
    out = walk(m, 'twin:arduino-uno-r3#1')
    link = (out.get('links') or [{}])[0]
    facts = link.get('datasheet_facts') or []
    check('mapping chain: twin:arduino-uno-r3#1 → SimRigState uno-twin-1 (its fields now) → contract → wire contract (hash v2, '
          '1-bit index) → binding index 1 at its pty → arduino-uno-r3 → %d cited facts, the USART ones first' % len(facts),
          out.get('ok') and link['object']['fields'].get('pwm_duty') == 42 and link['binding']['instance_index'] == 1
          and link['wire'].get('index_width') == 1 and link['board_definition']['name'] == 'arduino-uno-r3'
          and facts and facts[0]['relevant'] and link['hash_agrees'] and link['port']['path'] == '/tmp/polari-uno-twin-1-uart',
          out.get('plain') or out.get('error'))
    check('mapping chain: what is missing is SAID — the twin is never detected, this manager has no gRPC exposure',
          any('never detected' in x for x in link['missing']) and any('no gRPC exposure' in x for x in link['missing']), link.get('missing'))
    nope = walk(m, 'twin:nobody')
    check('mapping chain: an unbound instance → not ok, the bound instances listed', not nope['ok'] and 'twin:arduino-uno-r3#0' in nope['error'])
    from board.board_api import BoardAPI
    routes = []
    srv = types.SimpleNamespace(falconServer=types.SimpleNamespace(add_route=lambda path, res, suffix=None: routes.append((path, suffix))))
    api = BoardAPI(polServer=srv, manager=m)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_interface(None, resp, 'twin:arduino-uno-r3#0')
    check('mapping API: GET /api/board/instances/{instance}/interface is routed and answers the chain (404 when unbound)',
          ('/api/board/instances/{instance}/interface', 'interface') in routes and resp.media['ok']
          and resp.media['links'][0]['binding']['instance_index'] == 0)


def run_mapping(check):
    from board.custom import gen
    print('  -- mapping (brd-wire / grpc-j4)')
    c, _ = gen.pinned_contract('SimRigState')
    m = _mgr()
    _seed(m)
    pair_hash = rows_and_rules(check, m, c['field_map'], c['contract_hash'])
    scale(check, c['field_map'])
    build = firmware(check, m, c['field_map'], pair_hash)
    compat_on_v2(check, m, c['field_map'], build)
    chain(check, m)
