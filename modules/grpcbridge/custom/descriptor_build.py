"""
@module grpcbridge.custom.descriptor_build

Runtime protobuf descriptors for the serving layer (grpc-2) — built
programmatically FROM the stored tag ledger (ProtoContractVersion
.field_map_json), never by parsing .proto text and never by runtime
protoc codegen. The field_map is the source of truth; the .proto text
on the exposure row is its human/client rendering — both derive from
the same stabilization snapshot, so they agree by construction.

Also owns wire (de)serialization: object-tree instance ⇄ dynamic
protobuf message per the field_map. JSON-carrying fields (variant /
complex / containers — the honest `string` mapping from proto_gen)
ride as json.dumps text both directions.

@consumers
  - grpcbridge.custom.grpc_server (the sidecar)
  - grpcbridge.serving_selftest
"""

import json

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

PACKAGE = 'polari.sync'
SHARED_FILE = 'polari/sync/polari_shared.proto'

_F = descriptor_pb2.FieldDescriptorProto

#: proto type name (as stored in the field_map ledger) → descriptor enum.
PROTO_TYPE_ENUM = {
    'int64': _F.TYPE_INT64,
    'int32': _F.TYPE_INT32,
    'uint32': _F.TYPE_UINT32,
    'uint64': _F.TYPE_UINT64,
    'double': _F.TYPE_DOUBLE,
    'bool': _F.TYPE_BOOL,
    'string': _F.TYPE_STRING,
    'bytes': _F.TYPE_BYTES,
}

#: Shared messages — the descriptor twin of proto_gen.SHARED_MESSAGES
#: (field names/tags MUST stay in lockstep with that rendering).
SHARED_MESSAGES_SPEC = {
    'ObjectKey': [('id', 'string', 1), ('instance_id', 'string', 2)],
    'ListRequest': [('limit', 'int32', 1), ('offset', 'int32', 2)],
    'WatchRequest': [('class_name', 'string', 1),
                     ('format_type', 'string', 2)],
    'ChangeNotification': [('class_name', 'string', 1),
                           ('operation', 'string', 2),
                           ('timestamp', 'string', 3),
                           ('instance_ids', 'repeated string', 4),
                           ('format_type', 'string', 5)],
    'PushSummary': [('received', 'int32', 1), ('applied', 'int32', 2),
                    ('refused', 'int32', 3), ('note', 'string', 4)],
    # grpc-j4: the hardware-interface identity (proto_gen twin)
    'HardwareInterface': [('bridge', 'string', 1), ('binding', 'string', 2),
                          ('board_instance', 'string', 3),
                          ('port', 'string', 4),
                          ('interface_name', 'string', 5),
                          ('object_class', 'string', 6),
                          ('object_name', 'string', 7),
                          ('contract_hash', 'string', 8),
                          ('instance_index', 'uint32', 9),
                          ('present_mask', 'uint64', 10),
                          ('wire_version', 'uint32', 11)],
}
HW_TAG = 2047          # proto_gen.HW_TAG
HW_FIELD = 'hardware_interface'


def _add_field(msg_pb, name, type_name, tag):
    repeated = type_name.startswith('repeated ')
    if repeated:
        type_name = type_name[len('repeated '):]
    field = msg_pb.field.add()
    field.name = name
    field.number = tag
    field.type = PROTO_TYPE_ENUM[type_name]
    field.label = _F.LABEL_REPEATED if repeated else _F.LABEL_OPTIONAL


def build_shared_file():
    """FileDescriptorProto for the shared messages (built once per pool)."""
    fdp = descriptor_pb2.FileDescriptorProto()
    fdp.name = SHARED_FILE
    fdp.package = PACKAGE
    fdp.syntax = 'proto3'
    for msg_name, fields in SHARED_MESSAGES_SPEC.items():
        msg_pb = fdp.message_type.add()
        msg_pb.name = msg_name
        for fname, ftype, tag in fields:
            _add_field(msg_pb, fname, ftype, tag)
    return fdp


def _add_method(svc_pb, name, input_type, output_type,
                client_streaming=False, server_streaming=False):
    m = svc_pb.method.add()
    m.name = name
    m.input_type = input_type
    m.output_type = output_type
    m.client_streaming = client_streaming
    m.server_streaming = server_streaming


def build_class_file(class_name, field_map):
    """FileDescriptorProto for one exposed class: its message (fields
    per the tag ledger) + the <Class>Sync service — the descriptor
    twin of proto_gen.render_message/render_service."""
    fdp = descriptor_pb2.FileDescriptorProto()
    fdp.name = f'polari/sync/{class_name.lower()}.proto'
    fdp.package = PACKAGE
    fdp.syntax = 'proto3'
    fdp.dependency.append(SHARED_FILE)

    msg_pb = fdp.message_type.add()
    msg_pb.name = class_name
    fields = field_map.get('fields', {})
    for name in sorted(fields, key=lambda n: int(fields[n]['tag'])):
        _add_field(msg_pb, name, fields[name]['proto_type'],
                   int(fields[name]['tag']))
    for tag in field_map.get('reserved', []):
        rng = msg_pb.reserved_range.add()
        rng.start = int(tag)
        rng.end = int(tag) + 1
    hw = msg_pb.field.add()   # grpc-j4: the identity block
    hw.name, hw.number = HW_FIELD, HW_TAG
    hw.type, hw.label = _F.TYPE_MESSAGE, _F.LABEL_OPTIONAL
    hw.type_name = f'.{PACKAGE}.HardwareInterface'

    cls_type = f'.{PACKAGE}.{class_name}'
    svc_pb = fdp.service.add()
    svc_pb.name = f'{class_name}Sync'
    _add_method(svc_pb, 'Get', f'.{PACKAGE}.ObjectKey', cls_type)
    _add_method(svc_pb, 'List', f'.{PACKAGE}.ListRequest', cls_type,
                server_streaming=True)
    _add_method(svc_pb, 'Watch', f'.{PACKAGE}.WatchRequest',
                f'.{PACKAGE}.ChangeNotification', server_streaming=True)
    _add_method(svc_pb, 'Push', cls_type, f'.{PACKAGE}.PushSummary',
                client_streaming=True)
    _add_method(svc_pb, 'Commands', f'.{PACKAGE}.WatchRequest', cls_type,
                server_streaming=True)
    return fdp


class ContractRuntime:
    """One immutable descriptor pool over a set of exposed classes.

    Rebuilt whole whenever the exposure set changes (a pool cannot
    redefine a file, so refresh = new ContractRuntime). Holds the
    message classes + field maps the generic handlers serialize with.
    """

    def __init__(self, class_field_maps):
        # {class_name: field_map} — ONLY enabled+current exposures.
        self.field_maps = dict(class_field_maps)
        self.pool = descriptor_pool.DescriptorPool()
        self.pool.Add(build_shared_file())
        self._messages = {}
        for name, fmap in self.field_maps.items():
            self.pool.Add(build_class_file(name, fmap))
        for shared in SHARED_MESSAGES_SPEC:
            self._messages[shared] = message_factory.GetMessageClass(
                self.pool.FindMessageTypeByName(f'{PACKAGE}.{shared}'))
        for name in self.field_maps:
            self._messages[name] = message_factory.GetMessageClass(
                self.pool.FindMessageTypeByName(f'{PACKAGE}.{name}'))

    def message_class(self, name):
        return self._messages[name]

    def service_names(self):
        return sorted(f'{PACKAGE}.{name}Sync' for name in self.field_maps)

    def class_for_service(self, service_full_name):
        """'polari.sync.FooSync' → 'Foo' (None if not served)."""
        prefix = f'{PACKAGE}.'
        if (service_full_name.startswith(prefix)
                and service_full_name.endswith('Sync')):
            cls = service_full_name[len(prefix):-len('Sync')]
            if cls in self.field_maps:
                return cls
        return None

    # ---- wire (de)serialization ------------------------------------

    def instance_to_message(self, class_name, inst):
        """Object-tree instance → dynamic message, field by field per
        the ledger. Unset/None values ride as proto3 defaults; a field
        that refuses coercion is skipped (never crashes serving)."""
        msg = self._messages[class_name]()
        fields = self.field_maps[class_name].get('fields', {})
        for name, spec in fields.items():
            value = getattr(inst, name, None)
            if value is None:
                continue
            try:
                setattr(msg, name, _coerce_out(spec, value))
            except Exception:
                continue
        return msg

    def overlay_values(self, class_name, msg, values):
        """Set the given {field: value} on a class message (fields of the
        ledger only; a value that refuses coercion is skipped)."""
        fields = self.field_maps[class_name].get('fields', {})
        for name, value in (values or {}).items():
            if name in fields and value is not None:
                try:
                    setattr(msg, name, _coerce_out(fields[name], value))
                except Exception:
                    continue
        return msg

    def message_to_values(self, class_name, msg):
        """Dynamic message → {field: python value} (JSON fields
        decoded) — a telemetry frame updates what it says, no more.

        grpc-j4 (fixes brd-fi finding (1)): when the message carries a
        `hardware_interface` with a wire_version, its `present_mask`
        decides — bit i (tag order) set = the field IS in the frame and
        is applied even at its default (false / 0 / ""), so a row can
        return to false. Without it: the old proto3 rule (non-default
        values only)."""
        values = {}
        fields = self.field_maps[class_name].get('fields', {})
        hw = hardware_interface_of(msg)
        if hw and hw.get('wire_version'):
            mask = int(hw.get('present_mask') or 0)
            order = sorted(fields, key=lambda n: int(fields[n]['tag']))
            for bit, name in enumerate(order):
                if (mask >> bit) & 1:
                    values[name] = _coerce_in(fields[name],
                                              getattr(msg, name))
            return values
        for name, spec in fields.items():
            wire = getattr(msg, name, None)
            if wire is None or wire == _default_for(spec):
                continue
            values[name] = _coerce_in(spec, wire)
        return values


def hardware_interface_of(msg):
    """The message's `hardware_interface` as a dict, or None (absent)."""
    try:
        if not msg.HasField(HW_FIELD):
            return None
    except ValueError:      # a message without the field (old runtime)
        return None
    hw = getattr(msg, HW_FIELD)
    return {name: getattr(hw, name)
            for name, _, _ in SHARED_MESSAGES_SPEC['HardwareInterface']}


def set_hardware_interface(msg, values):
    """Fill `hardware_interface` on a class message from a dict."""
    hw = getattr(msg, HW_FIELD)
    for name, ptype, _ in SHARED_MESSAGES_SPEC['HardwareInterface']:
        if name in values and values[name] is not None:
            setattr(hw, name, int(values[name]) if ptype.startswith('uint')
                    else str(values[name]))
    return msg


def _is_json_field(spec):
    return bool(spec.get('comment'))  # proto_gen comments == JSON carrier


def _coerce_out(spec, value):
    ptype = spec['proto_type']
    if _is_json_field(spec):
        return value if isinstance(value, str) else json.dumps(value)
    if ptype == 'int64':
        return int(value)
    if ptype == 'double':
        return float(value)
    if ptype == 'bool':
        return bool(value)
    if ptype == 'bytes':
        return bytes(value)
    return str(value)


def _coerce_in(spec, wire):
    if _is_json_field(spec):
        try:
            return json.loads(wire)
        except Exception:
            return wire
    return wire


def _default_for(spec):
    ptype = spec['proto_type']
    if ptype in ('int64', 'int32'):
        return 0
    if ptype == 'double':
        return 0.0
    if ptype == 'bool':
        return False
    if ptype == 'bytes':
        return b''
    return ''


def runtime_from_manager(manager):
    """Build the ContractRuntime for every enabled+current exposure,
    reading each class's field_map from the ledger row matching the
    exposure's proto_version (the contract actually in force)."""
    from grpcbridge.custom.proto_gen import get_versions
    maps = {}
    tables = getattr(manager, 'objectTables', None) or {}
    for exposure in (tables.get('GrpcExposure') or {}).values():
        if not getattr(exposure, 'enabled', False):
            continue
        if getattr(exposure, 'contract_status', '') != 'current':
            continue
        cls = getattr(exposure, 'subject_class', '')
        wanted = int(getattr(exposure, 'proto_version', 0) or 0)
        for row in get_versions(manager, cls):
            if int(getattr(row, 'version', 0) or 0) == wanted:
                try:
                    maps[cls] = json.loads(
                        getattr(row, 'field_map_json', '{}') or '{}')
                except Exception:
                    pass
                break
    return ContractRuntime(maps)
