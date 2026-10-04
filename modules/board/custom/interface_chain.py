"""
@module board.custom.interface_chain

brd-wire (grpc-j4, his ruling 2026-10-02 — "use objects at the polari level and still ensure they correspond to a very
specific hardware interface when analyzing them"): the BINDING CHAIN of one board instance, walked over rows only:

  object row (class, name, id, its fields now)
    → the class's gRPC contract (version, hash v1)
    → the wire contract (hash v2, field order, enum tables, index width, prelude bytes)
    → the HardwareInterfaceBinding (bridge, instance index, interface, port, frames seen / refused)
    → the BoardInstance (observed by detect; a twin or an undetected board says so)
    → the port / adapter (AdapterDefinition when the host reaches it through one)
    → the BoardDefinition → its cited DatasheetFacts (the interface's own facts flagged)

GET /api/board/instances/<instance>/interface (board.board_api). Nothing here is computed from code constants: a link
that is missing is reported as missing, in plain words.
"""
import json

#: which DatasheetFact keys speak about which interface kind (flagged `relevant` in the chain)
INTERFACE_FACT_WORDS = {'usart': ('usart', 'uart', 'baud', 'ubrr', 'serial', 'usb'), 'spi': ('spi',), 'i2c': ('twi', 'i2c')}


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _by_name(manager, cls, name):
    return next((r for r in _rows(manager, cls) if getattr(r, 'name', '') == name), None)


def _plain_fields(obj):
    return {k: v for k, v in vars(obj).items() if not k.startswith('_') and k != 'manager' and isinstance(v, (str, int, float, bool))}


def _fields(obj, keys):
    return {k: getattr(obj, k, '') for k in keys}


def link(manager, b):
    """The chain of ONE binding row."""
    from grpcbridge.custom.proto_gen import get_exposure
    cls, oname = b.object_class, b.object_name
    missing = []
    obj = next((r for r in _rows(manager, cls) if str(getattr(r, 'name', '')) == oname), None)
    if obj is None:
        missing.append('no %s row named %r yet (it appears with the first frame)' % (cls, oname))
    exp = get_exposure(manager, cls)
    if exp is None:
        missing.append('%s has no gRPC exposure on this server' % cls)
    wc = _by_name(manager, 'WireContract', '%s@%s' % (cls, b.bridge_name))
    if wc is None:
        missing.append('no WireContract %s@%s derived yet (generating the bridge derives it)' % (cls, b.bridge_name))
    inst = _by_name(manager, 'BoardInstance', b.board_instance)
    if inst is None:
        missing.append('board instance %r is not observed (%s)' % (
            b.board_instance, 'a simavr twin — never detected' if str(b.board_instance).startswith('twin:') else 'pol board detect --push'))
    adapter = _by_name(manager, 'AdapterDefinition', b.adapter) if b.adapter else None
    bdef_name = (getattr(inst, 'definition', '') if inst is not None and getattr(inst, 'definition_kind', '') != 'adapter'
                 else getattr(inst, 'target_board', '') if inst is not None else '') or b.board_definition
    bdef = _by_name(manager, 'BoardDefinition', bdef_name)
    if bdef is None:
        missing.append('no BoardDefinition %r' % bdef_name)
    words = next((w for k, w in INTERFACE_FACT_WORDS.items() if str(b.interface_name).lower().startswith(k)), ())
    facts = [dict(_fields(f, ('fact_key', 'value', 'unit', 'document', 'revision', 'page_table', 'url')),
                  relevant=any(w in (str(f.fact_key) + ' ' + str(getattr(f, 'notes', ''))).lower() for w in words))
             for f in _rows(manager, 'DatasheetFact') if getattr(f, 'board', '') == bdef_name]
    facts.sort(key=lambda f: (not f['relevant'], f['fact_key']))
    return {
        'object': {'class': cls, 'name': oname, 'id': getattr(obj, 'id', '') if obj is not None else '',
                   'fields': _plain_fields(obj) if obj is not None else {}},
        'contract': {'class': cls, 'version': getattr(exp, 'proto_version', 0) if exp else 0,
                     'contract_hash_v1': getattr(exp, 'contract_hash', '') if exp else '',
                     'status': getattr(exp, 'contract_status', '') if exp else 'none'},
        'wire': ({'name': wc.name, 'contract_hash_v2': wc.contract_hash_v2, 'wire_version': wc.wire_version,
                  'field_order': json.loads(wc.field_order_json or '[]'), 'enums': json.loads(wc.enums_json or '{}'),
                  'instance_count': wc.instance_count, 'index_width': wc.index_width, 'prelude_bytes': wc.prelude_bytes,
                  'index_repr': getattr(wc, 'index_repr', ''), 'index_bytes': getattr(wc, 'index_bytes', 0),
                  'suggested_index_width': getattr(wc, 'suggested_index_width', 0), 'packed_max_bits': getattr(wc, 'packed_max_bits', 4),
                  'suggestion': wc.notes, 'derived_at': wc.derived_at} if wc is not None else {}),
        'binding': _fields(b, ('name', 'bridge_name', 'instance_index', 'interface_kind', 'interface_name', 'port', 'adapter',
                               'wire_version', 'contract_hash_v2', 'frames_seen', 'refused_frames', 'last_seen_at', 'origin')),
        'instance': (_fields(inst, ('name', 'definition', 'definition_kind', 'state', 'host', 'by_id_path', 'port', 'usb_id',
                                    'firmware_sha', 'last_flash_at')) if inst is not None else {'name': b.board_instance, 'observed': False}),
        'port': {'path': b.port, 'kind': b.interface_kind,
                 'adapter': _fields(adapter, ('name', 'kind', 'chip', 'usb_connector')) if adapter is not None else None},
        'board_definition': (_fields(bdef, ('name', 'device_class', 'soc', 'isa', 'usb_route', 'programmer', 'simulated', 'twin'))
                             if bdef is not None else {'name': bdef_name}),
        'datasheet_facts': facts,
        'hash_agrees': bool(wc is not None and wc.contract_hash_v2 == b.contract_hash_v2),
        'missing': missing,
    }


def chain(manager, instance):
    """Every binding of a board instance, each walked to the datasheet. {ok, instance, links, plain}."""
    from grpcbridge.custom.wire_contract import bindings
    rows = [b for b in bindings(manager) if b.board_instance == instance]
    if not rows:
        known = sorted({b.board_instance for b in bindings(manager)})
        return {'ok': False, 'instance': instance,
                'error': 'no hardware-interface binding names board instance %r — bound instances: %s'
                         % (instance, ', '.join(known) or 'none')}
    links = [link(manager, b) for b in rows]
    plain = '; '.join('%s %s is %s instance %d on bridge %s, %s at %s → %s (wire %s, %d-bit index)'
                      % (l['object']['class'], l['object']['name'], l['binding']['interface_name'], l['binding']['instance_index'],
                         l['binding']['bridge_name'], l['binding']['interface_kind'], l['port']['path'], l['board_definition']['name'],
                         l['wire'].get('contract_hash_v2', '?'), l['wire'].get('index_width', -1)) for l in links)
    return {'ok': True, 'instance': instance, 'links': links, 'plain': plain}
