"""
@module grpcbridge.custom.wire_contract

grpc-j4 (his ruling 2026-10-02): the computer↔firmware MAPPING as data → one WIRE SPEC every generator reads (the C
header, the Java codec, the bridge's proto bundle, the Python reference) and contract hash v2.

  index_width(n)        0 bits for 1 instance, 1 for 2, ceil(log2 n) otherwise (the suggestion)
  index_repr(n, packed_max_bits)
                        none (n=1) | bits (packed in the prelude, v2) | byte (an explicit index byte, v3, n <= 256) |
                        u16 (an explicit 16-bit index, v4) — the version byte says which
  spec(cls, field_map, enums, instances, packed_max_bits)
                        {fields: [{name, ptype, bit, enum}], index_repr, index_width, index_bytes, prelude_bytes, …, hash_v2}
  hash_v2(spec)         sha256 over [version, presence, [repr, packed bits, index bytes, packed_max_bits],
                        [[field, type, labels|None] in TAG order]]
  enum_tables(manager)  EnumMapping rows → {class: {field: {labels, unknown}}} (the seeds with no manager)
  bindings / assign_indexes / binding_for_object      HardwareInterfaceBinding helpers (dense 0..n-1 per class per bridge)
  derive(manager, cls, bridge, field_map)             → the WireContract row (upserted) + the spec

The prelude (plan GRPC_BRIDGE_PLAN.md §grpc-j4): [index byte | u16 index (v3 / v4 only)] then ceil((w + n) / 8)
bitfield bytes — bits 0..w-1 the packed index (v2 'bits' only, LSB first), then presence of field i in TAG order — then
only the present fields (enum fields one byte: 0 = the unknown slot, labels[i] = i + 1). `contract_hash` in proto_gen stays v1 (field → type, the schema
watch); v2 is the wire watch.

@consumers
  - grpcbridge.custom.c_twin_v2 · java_bridge_wire · java_bridge · descriptor_build · grpc_server
  - board.custom.compat / gen / packet_ref (firmware builds, compat on hash v2)
"""
import datetime
import hashlib
import json
import math

WIRE_VERSION = 2
MAX_FIELDS = 64          # the proto present_mask is a uint64
MAX_LABELS = 255         # u8 on the wire, 0 is the unknown slot
HW_TAG = 2047            # the hardware_interface field on every class message (the largest 2-byte varint key)
HW_FIELD = 'hardware_interface'


class WireRefused(ValueError):
    pass


def index_width(n):
    """Bits needed to tell n instances apart: 0 for 1, 1 for 2 (a boolean), ceil(log2 n) otherwise — the SUGGESTION;
    index_repr decides how the index is actually carried."""
    n = int(n or 0)
    if n <= 1:
        return 0
    return int(math.ceil(math.log2(n)))


def field_order(field_map):
    f = (field_map or {}).get('fields') or {}
    return [(n, f[n]['proto_type']) for n in sorted(f, key=lambda n: int(f[n]['tag']))]


#: the knob (WireContract.packed_max_bits): the largest index packed into the prelude's bitfield beside the presence
#: bits. 4 bits = up to 16 instances packed; past it a multiplexed link is likely, which wants the index byte-aligned
#: at a fixed offset (a gateway routes on it without knowing the class).
DEFAULT_PACKED_MAX_BITS = 4
#: index representation → (wire version byte, explicit index bytes, the largest n it carries)
INDEX_REPRS = {'none': (2, 0, 1), 'bits': (2, 0, None), 'byte': (3, 1, 256), 'u16': (4, 2, 65536)}


def index_repr(n, packed_max_bits=DEFAULT_PACKED_MAX_BITS):
    """How n instances are told apart on the wire → {repr, version, packed_bits, index_bytes, suggested_width}.

      n = 1                              'none'  v2  nothing
      ceil(log2 n) <= packed_max_bits    'bits'  v2  ceil(log2 n) bits in the prelude bitfield (the shortest)
      n <= 256                           'byte'  v3  an explicit index byte, then the presence bits
      n <= 65536                         'u16'   v4  an explicit 16-bit LE index, then the presence bits"""
    n, k = max(1, int(n or 1)), int(packed_max_bits)
    if not 0 <= k <= 8:
        raise WireRefused('packed_max_bits %d: 0..8 (an index wider than a byte is carried as an explicit byte or u16)' % k)
    w = index_width(n)
    if w == 0:
        rep = 'none'
    elif w <= k:
        rep = 'bits'
    elif n <= 256:
        rep = 'byte'
    elif n <= 65536:
        rep = 'u16'
    else:
        raise WireRefused('%d instances on one bridge: more than a 16-bit index carries' % n)
    version, nbytes, _ = INDEX_REPRS[rep]
    return {'repr': rep, 'version': version, 'packed_bits': w if rep == 'bits' else 0, 'index_bytes': nbytes,
            'suggested_width': w, 'packed_max_bits': k}


def spec(cls, field_map, enums=None, instances=1, packed_max_bits=DEFAULT_PACKED_MAX_BITS):
    """The wire spec of one class carried for `instances` bound instances. `enums` = {field: {'labels', 'unknown'}}
    (or {field: [labels]})."""
    order = field_order(field_map)
    if not order:
        raise WireRefused('%s has no fields in its contract — nothing to put on the wire' % cls)
    if len(order) > MAX_FIELDS:
        raise WireRefused('%s has %d fields; wire v2 carries presence as a uint64 in the gRPC message (at most %d)'
                          % (cls, len(order), MAX_FIELDS))
    if HW_FIELD in dict(order):
        raise WireRefused('%s has a field named %s — that name is the gRPC identity block' % (cls, HW_FIELD))
    names = dict(order)
    tables = {}
    for fld, t in (enums or {}).items():
        labels = list(t.get('labels') if isinstance(t, dict) else t)
        unknown = (t.get('unknown') if isinstance(t, dict) else None) or 'unknown'
        if fld not in names:
            raise WireRefused('enum mapping %s.%s: the contract has no field %s' % (cls, fld, fld))
        if names[fld] != 'string':
            raise WireRefused('enum mapping %s.%s: only a string field maps to an enum (it is %s)' % (cls, fld, names[fld]))
        if not labels or len(labels) > MAX_LABELS or len(set(labels)) != len(labels) or unknown in labels:
            raise WireRefused('enum mapping %s.%s: 1..%d distinct labels, none equal to the unknown label %r'
                              % (cls, fld, MAX_LABELS, unknown))
        tables[fld] = {'labels': labels, 'unknown': unknown}
    ix = index_repr(instances, packed_max_bits)
    w = ix['packed_bits']
    fields = [{'name': n, 'ptype': t, 'bit': w + i, 'enum': tables.get(n)} for i, (n, t) in enumerate(order)]
    bits = w + len(fields)
    out = {'class': cls, 'wire_version': ix['version'], 'presence': 'mask', 'index_repr': ix['repr'], 'index_width': w,
           'index_bytes': ix['index_bytes'], 'suggested_index_width': ix['suggested_width'], 'packed_max_bits': ix['packed_max_bits'],
           'instance_count': max(1, int(instances or 1)), 'fields': fields, 'field_count': len(fields), 'prelude_bits': bits,
           'bitfield_bytes': (bits + 7) // 8, 'prelude_bytes': ix['index_bytes'] + (bits + 7) // 8,
           'present_all': (1 << len(fields)) - 1, 'enums': {k: v['labels'] for k, v in tables.items()},
           'enum_unknown': {k: v['unknown'] for k, v in tables.items()}}
    out['hash_v2'] = hash_v2(out)
    return out


def hash_v2(s):
    """sha256 over the wire RULES: version, presence, the index representation (repr, packed bits, explicit bytes, the
    packed_max_bits knob that chose it) and [[field, type, enum labels|None] in TAG order]."""
    core = [s['wire_version'], s['presence'], [s['index_repr'], s['index_width'], s['index_bytes'], s['packed_max_bits']],
            [[f['name'], f['ptype'], (f['enum'] or {}).get('labels')] for f in s['fields']]]
    return hashlib.sha256(json.dumps(core, separators=(',', ':')).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- enum values (the Python reference of the mapping)
def enum_to_wire(table, label):
    try:
        return table['labels'].index(label) + 1
    except (ValueError, TypeError):
        return 0


def enum_from_wire(table, value):
    v = int(value)
    return table['labels'][v - 1] if 1 <= v <= len(table['labels']) else table.get('unknown', 'unknown')


# ---------------------------------------------------------------- rows
def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 — an in-memory manager has no db
        pass


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def _has_table(manager, cls):
    return manager is not None and cls in (getattr(manager, 'objectTables', None) or {})


def binding_count(manager, bridge, cls):
    """How many interfaces bind `cls` on `bridge` (rows; the seeds when this manager has no binding table)."""
    if not bridge:
        return 1
    if _has_table(manager, 'HardwareInterfaceBinding'):
        return len(bindings(manager, bridge, cls))
    from grpcbridge.mapping_basis import SEED_HARDWARE_BINDINGS
    return len([b for b in SEED_HARDWARE_BINDINGS if b['bridge_name'] == bridge and b['object_class'] == cls])


def enum_tables(manager=None, cls=None):
    """{class: {field: {'labels', 'unknown'}}} from EnumMapping rows; with no rows (no manager), the seeds."""
    if _has_table(manager, 'EnumMapping'):
        rows = _rows(manager, 'EnumMapping')
    else:   # no manager / the class not registered here: the code-owned seeds
        from grpcbridge.mapping_basis import SEED_ENUM_MAPPINGS
        rows = SEED_ENUM_MAPPINGS
    out = {}
    for r in rows:
        g = (lambda k, d='': r.get(k, d)) if isinstance(r, dict) else (lambda k, d='': getattr(r, k, d))
        try:
            labels = json.loads(g('labels_json', '[]') or '[]')
        except ValueError:
            continue
        out.setdefault(g('object_class'), {})[g('field')] = {'labels': labels, 'unknown': g('unknown_label') or 'unknown'}
    return out.get(cls, {}) if cls else out


def bindings(manager, bridge=None, cls=None):
    out = [b for b in _rows(manager, 'HardwareInterfaceBinding')
           if (bridge is None or getattr(b, 'bridge_name', '') == bridge) and (cls is None or getattr(b, 'object_class', '') == cls)]
    return sorted(out, key=lambda b: (getattr(b, 'object_class', ''), int(getattr(b, 'instance_index', 0) or 0), getattr(b, 'name', '')))


def binding_for_object(manager, cls, object_name, bridge=None):
    for b in bindings(manager, bridge, cls):
        if getattr(b, 'object_name', '') == object_name:
            return b
    return None


def assign_indexes(manager, bridge, cls, save=True):
    """Renumber the bindings of `cls` on `bridge` densely 0..n-1, keeping their present order (index, then name).
    Returns [(binding name, index)]. Two rows naming the same object are refused (one object = one interface)."""
    rows = bindings(manager, bridge, cls)
    seen = {}
    for b in rows:
        o = getattr(b, 'object_name', '')
        if o in seen:
            raise WireRefused('%s and %s both bind %s %r on bridge %s — one object is one hardware interface'
                              % (seen[o], b.name, cls, o, bridge))
        seen[o] = b.name
    out = []
    for i, b in enumerate(rows):
        if int(getattr(b, 'instance_index', 0) or 0) != i:
            b.instance_index = i
            if save:
                _save(manager, b)
        out.append((b.name, i))
    return out


def live_field_map(manager, cls):
    """(field_map, version, contract_hash_v1) of the class's exposure on this server, or None."""
    try:
        from grpcbridge.custom.proto_gen import get_exposure, get_versions
    except Exception:  # noqa: BLE001
        return None
    exp = get_exposure(manager, cls) if manager is not None else None
    want = int(getattr(exp, 'proto_version', 0) or 0) if exp is not None else 0
    if not want:
        return None
    for row in get_versions(manager, cls):
        if int(getattr(row, 'version', 0) or 0) == want:
            try:
                fm = json.loads(getattr(row, 'field_map_json', '{}') or '{}')
            except ValueError:
                return None
            return (fm, want, getattr(exp, 'contract_hash', '')) if fm.get('fields') else None
    return None


def packed_max_bits(manager, cls, bridge=''):
    """The knob, read from the WireContract row (contract data, so the hash sees it); the default with no row."""
    row = next((r for r in _rows(manager, 'WireContract') if getattr(r, 'name', '') == '%s@%s' % (cls, bridge or '-')), None)
    try:
        return int(getattr(row, 'packed_max_bits', DEFAULT_PACKED_MAX_BITS)) if row is not None else DEFAULT_PACKED_MAX_BITS
    except (TypeError, ValueError):
        return DEFAULT_PACKED_MAX_BITS


def spec_for(manager, cls, bridge='', field_map=None):
    """The spec of `cls` on `bridge` from rows: the field map (given, else the live exposure), its EnumMappings, and
    the width implied by its bindings on that bridge. None when no field map is known."""
    if field_map is None:
        live = live_field_map(manager, cls)
        if live is None:
            return None
        field_map = live[0]
    n = binding_count(manager, bridge, cls)
    return spec(cls, field_map, enum_tables(manager, cls), max(1, n), packed_max_bits(manager, cls, bridge))


def derive(manager, cls, bridge='', field_map=None, version=0, hash_v1='', source='live', factory=None):
    """Upsert the WireContract row for (cls, bridge) and stamp hash v2 on its bindings. Returns (row, spec) or
    (None, None) when no field map is known."""
    if field_map is None:
        live = live_field_map(manager, cls)
        if live is None:
            return None, None
        field_map, version, hash_v1 = live
    if bridge:
        assign_indexes(manager, bridge, cls)
    s = spec_for(manager, cls, bridge, field_map)
    if factory is None:
        from grpcbridge.mapping_basis import WireContract as factory
    name = '%s@%s' % (cls, bridge or '-')
    row = next((r for r in _rows(manager, 'WireContract') if getattr(r, 'name', '') == name), None)
    fields = dict(object_class=cls, bridge_name=bridge, contract_version=int(version or 0),
                  field_order_json=json.dumps([[f['name'], f['ptype']] for f in s['fields']]), enums_json=json.dumps(s['enums']),
                  instance_count=s['instance_count'], index_width=s['index_width'], presence='mask', prelude_bytes=s['prelude_bytes'],
                  wire_version=s['wire_version'], contract_hash_v1=hash_v1 or '', contract_hash_v2=s['hash_v2'], source=source,
                  derived_at=_now(), index_repr=s['index_repr'], index_bytes=s['index_bytes'],
                  suggested_index_width=s['suggested_index_width'], packed_max_bits=s['packed_max_bits'],
                  notes=suggestion(s))
    if row is None:
        row = factory(manager=manager, name=name, **fields)
        tables = getattr(manager, 'objectTables', None)
        if isinstance(tables, dict) and not hasattr(manager, 'idList'):   # a selftest's plain manager: track it
            tables.setdefault('WireContract', {})[name] = row
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    _save(manager, row)
    for b in bindings(manager, bridge, cls) if bridge else []:
        if getattr(b, 'contract_hash_v2', '') != s['hash_v2']:
            b.contract_hash_v2 = s['hash_v2']
            _save(manager, b)
    return row, s


def suggestion(s):
    """The computed width shown as a suggestion beside what the knob chose (plain words for the row's notes)."""
    n, w, k = s['instance_count'], s['suggested_index_width'], s['packed_max_bits']
    if s['index_repr'] == 'none':
        return '1 instance: no index on the wire'
    if s['index_repr'] == 'bits':
        return '%d instances: %d bit(s) packed beside the presence bits (suggested %d; packed_max_bits %d)' % (n, w, w, k)
    return ('%d instances: suggested %d bit(s), past packed_max_bits %d → an explicit %s index (wire version %d), byte-aligned '
            'so a gateway can route on it; raise the knob to pack it instead' % (n, w, k, '1-byte' if s['index_bytes'] == 1 else '16-bit',
                                                                                 s['wire_version']))


def note_frame(binding, sequence, refused=False):
    """Count one telemetry frame on its binding (in memory; the row is saved with the next derive / page write)."""
    if binding is None:
        return
    if refused:
        binding.refused_frames = int(getattr(binding, 'refused_frames', 0) or 0) + 1
        return
    binding.frames_seen = int(getattr(binding, 'frames_seen', 0) or 0) + 1
    binding.last_sequence = int(sequence or 0)
    binding.last_seen_at = _now()
