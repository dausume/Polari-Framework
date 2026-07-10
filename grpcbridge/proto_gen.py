"""
@module grpcbridge.proto_gen

The contract generator (grpc-1, stdlib-only — no grpcio): turns a
class's SCHEMA-STABILIZATION snapshot into a proto3 contract.

The gate IS the feature: generate_contract REFUSES unless the class
is stabilized (`schema_stability.is_stabilized`), and it reads the
snapshot taken AT stabilization (`field_summary_json`), not live
typing — the contract matches what was trusted. A later OOPS
(SchemaDeviationEvent) flips the exposure 'stale' via
mark_exposures_stale (called failure-isolated from record_deviation).

Type mapping mirrors the affinity mapping the DB adapters already
use (one typing rule): INTEGER→int64 (bool→bool), REAL→double,
TEXT→string, variant/complex→string carrying JSON (HONEST: the wire
says what it really carries).

@consumers
  - grpcbridge.contract_api (the knob surface)
  - polariDataTyping.schema_stability.record_deviation (stale hook)
  - grpcbridge.selftest_contracts
"""

import hashlib
import json
from datetime import datetime, timezone

#: Framework-internal fields that never belong on the wire.
IGNORED_FIELDS = ('manager',)

#: Shared messages, identical in every generated file so each .proto
#: is self-contained (grpcurl-able alone). The markers let a bundler
#: (grpc-j1) keep exactly one copy when combining classes.
SHARED_MARK_START = ('// ---- shared messages (identical in every '
                     'Polari contract) ----')
SHARED_MARK_END = '// ---- end shared messages ----'

#: ObjectKey carries the composite identity from the shared object DB
#: (id, instance_id); ChangeNotification mirrors the STOMP payload of
#: polariCRUDE._notify_ws_subscribers field-for-field — parity by
#: construction.
SHARED_MESSAGES = f'''{SHARED_MARK_START}
message ObjectKey {{
  string id = 1;
  string instance_id = 2;
}}

message ListRequest {{
  int32 limit = 1;
  int32 offset = 2;
}}

message WatchRequest {{
  string class_name = 1;
  string format_type = 2;
}}

message ChangeNotification {{
  string class_name = 1;
  string operation = 2;
  string timestamp = 3;
  repeated string instance_ids = 4;
  string format_type = 5;
}}

message PushSummary {{
  int32 received = 1;
  int32 applied = 2;
  int32 refused = 3;
  string note = 4;
}}
{SHARED_MARK_END}'''


def _now():
    return datetime.now(timezone.utc).isoformat()


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {})


def _save_row(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def get_exposure(manager, class_name):
    for row in _rows(manager, 'GrpcExposure').values():
        if getattr(row, 'subject_class', '') == class_name:
            return row
    return None


def get_versions(manager, class_name):
    """This class's contract history, oldest first."""
    rows = [r for r in _rows(manager, 'ProtoContractVersion').values()
            if getattr(r, 'subject_class', '') == class_name]
    rows.sort(key=lambda r: int(getattr(r, 'version', 0) or 0))
    return rows


def trusted_snapshot(manager, class_name):
    """The field snapshot taken AT stabilization — what the schema
    was trusted AS. Contracts generate from THIS, never live typing."""
    from polariDataTyping.schema_stability import get_profile
    profile = get_profile(manager, class_name)
    if profile is None:
        return {}
    try:
        snap = json.loads(
            getattr(profile, 'field_summary_json', '{}') or '{}')
    except Exception:
        return {}
    return {k: v for k, v in snap.items()
            if isinstance(v, dict) and k not in IGNORED_FIELDS
            and not k.startswith('_')}


def proto_type_for(summary):
    """affinity → proto3 type. Returns (proto_type, comment) — the
    comment is non-empty when the wire carries JSON text (honest)."""
    strategy = summary.get('schemaStrategy', 'typed')
    dominant = summary.get('dominantType', '')
    affinity = (summary.get('dominantAffinity')
                or summary.get('sqliteAffinity') or 'TEXT').upper()
    if strategy in ('variant', 'complex'):
        return 'string', f'JSON-encoded (schema strategy: {strategy})'
    if dominant in ('list', 'dict', 'tuple', 'set', 'polariList'):
        return 'string', f'JSON-encoded (python {dominant})'
    if dominant == 'bool':
        # Regardless of DB affinity: Python bools ride storage as
        # TEXT in this framework, but the WIRE must carry a real
        # 1-byte bool — 'True' as a length-prefixed string is 7
        # bytes per message plus a 64-byte buffer on an MCU.
        return 'bool', ''
    if affinity == 'INTEGER':
        return 'int64', ''
    if affinity == 'REAL':
        return 'double', ''
    if affinity == 'BLOB':
        return 'bytes', ''
    return 'string', ''


def contract_hash(snapshot):
    """Stable hash over the WIRE-RELEVANT projection of the snapshot
    (field → proto type). Occurrence counters can't churn it."""
    core = {}
    for field, summary in sorted((snapshot or {}).items()):
        ptype, comment = proto_type_for(
            summary if isinstance(summary, dict) else {})
        core[field] = ptype + (f'|{comment}' if comment else '')
    blob = json.dumps(core, sort_keys=True)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


def merge_field_map(snapshot, prior_map=None):
    """The tag-number ledger. Unchanged fields keep their tag; new
    fields take the next free tag; removed fields — and retyped
    fields, whose old tag would be a wire break — surrender their tag
    to `reserved` forever."""
    prior_fields = dict((prior_map or {}).get('fields', {}))
    reserved = set(int(t) for t in (prior_map or {}).get('reserved', []))
    used = set(reserved)
    used.update(int(spec.get('tag', 0)) for spec in prior_fields.values())

    def next_tag():
        tag = 1
        while tag in used:
            tag += 1
        return tag

    fields = {}
    for name in sorted(snapshot or {}):
        summary = snapshot[name]
        if not isinstance(summary, dict):
            continue
        ptype, comment = proto_type_for(summary)
        prior = prior_fields.get(name)
        if prior and prior.get('proto_type') == ptype:
            tag = int(prior['tag'])
        else:
            if prior:  # retyped — retire the old tag (wire compat)
                reserved.add(int(prior['tag']))
            tag = next_tag()
        used.add(tag)
        fields[name] = {'tag': tag, 'proto_type': ptype,
                        'comment': comment}
    for name, spec in prior_fields.items():
        if name not in fields:
            reserved.add(int(spec.get('tag', 0)))
    reserved.discard(0)
    return {'fields': fields, 'reserved': sorted(reserved)}


def render_message(class_name, field_map):
    lines = [f'message {class_name} {{']
    fields = field_map.get('fields', {})
    for name in sorted(fields, key=lambda n: fields[n]['tag']):
        spec = fields[name]
        comment = f"  // {spec['comment']}" if spec.get('comment') else ''
        lines.append(
            f"  {spec['proto_type']} {name} = {spec['tag']};{comment}")
    reserved = field_map.get('reserved', [])
    if reserved:
        lines.append(f"  reserved {', '.join(str(t) for t in reserved)};")
    lines.append('}')
    return '\n'.join(lines)


def render_service(class_name):
    return (f'service {class_name}Sync {{\n'
            f'  rpc Get (ObjectKey) returns ({class_name});\n'
            f'  rpc List (ListRequest) returns (stream {class_name});\n'
            f'  rpc Watch (WatchRequest) returns '
            f'(stream ChangeNotification);\n'
            f'  // hardware in: devices stream telemetry up (grpc-4)\n'
            f'  rpc Push (stream {class_name}) returns (PushSummary);\n'
            f'  // hardware out: Polari streams commands down (grpc-4)\n'
            f'  rpc Commands (WatchRequest) returns '
            f'(stream {class_name});\n'
            f'}}')


def render_proto(class_name, field_map, version, chash, generated_at):
    """One self-contained .proto: header + shared messages + the
    class message + its sync service."""
    return '\n'.join([
        '// Generated by Polari grpcbridge (grpc-1) — do not edit;',
        '// regenerate via POST /api/grpc/exposures/'
        f'{class_name} {{"action": "regenerate"}}.',
        f'// class: {class_name}   contract v{version}   '
        f'hash {chash}',
        f'// generated from the schema-stabilization snapshot at '
        f'{generated_at};',
        '// a schema deviation (OOPS) marks this contract stale.',
        'syntax = "proto3";',
        '',
        'package polari.sync;',
        '',
        'option java_package = "org.polari.sync";',
        'option java_multiple_files = true;',
        '',
        SHARED_MESSAGES,
        '',
        render_message(class_name, field_map),
        '',
        render_service(class_name),
        '',
    ])


def _refusal(error, class_name=None, suggestion=None):
    out = {'ok': False, 'error': error}
    if suggestion:
        out['suggestion'] = suggestion
    if class_name:
        out['class'] = class_name
    return out


def _stabilize_suggestion(class_name):
    return {
        'knob': f'/api/schema/stability/{class_name}',
        'how': 'run traffic through the class until it stabilizes, '
               'or stabilize manually: POST {"action": "stabilize"}',
        'why': 'a gRPC contract is only as stable as the schema '
               'under it',
    }


def generate_contract(manager, class_name, reason='initial',
                      exposure=None, version_factory=None):
    """Generate a new contract version for a STABILIZED class and
    stamp it onto the exposure row. Refuses when the gate is shut."""
    from polariDataTyping.schema_stability import is_stabilized
    if not is_stabilized(manager, class_name):
        return _refusal(
            f'class "{class_name}" is not stabilized — no contract '
            'can be trusted yet', class_name,
            _stabilize_suggestion(class_name))
    snapshot = trusted_snapshot(manager, class_name)
    if not snapshot:
        return _refusal(
            f'class "{class_name}" is stabilized but its field '
            'snapshot is empty — destabilize and re-stabilize with '
            'traffic so the snapshot captures real fields',
            class_name, _stabilize_suggestion(class_name))
    if exposure is None:
        exposure = get_exposure(manager, class_name)
    if exposure is None:
        return _refusal(
            f'no GrpcExposure row for "{class_name}" — enable it '
            'first', class_name,
            {'knob': f'/api/grpc/exposures/{class_name}',
             'how': 'POST {"action": "enable"}'})

    versions = get_versions(manager, class_name)
    prior_map = None
    if versions:
        try:
            prior_map = json.loads(
                getattr(versions[-1], 'field_map_json', '{}') or '{}')
        except Exception:
            prior_map = None
    field_map = merge_field_map(snapshot, prior_map)
    version = (int(getattr(versions[-1], 'version', 0)) + 1
               if versions else 1)
    chash = contract_hash(snapshot)
    generated_at = _now()
    proto_text = render_proto(class_name, field_map, version, chash,
                              generated_at)

    if version_factory is None:
        from grpcbridge.contract_basis import ProtoContractVersion
        version_factory = ProtoContractVersion
    version_row = version_factory(
        name=f'{class_name}-proto-v{version}',
        subject_class=class_name, version=version,
        contract_hash=chash, proto_text=proto_text,
        field_map_json=json.dumps(field_map),
        generated_at=generated_at, reason=reason, notes='',
        manager=manager)
    _save_row(manager, version_row)

    exposure.service_name = f'PolariObjectSync.{class_name}'
    exposure.proto_version = version
    exposure.contract_hash = chash
    exposure.contract_status = 'current'
    exposure.proto_text = proto_text
    exposure.generated_at = generated_at
    _save_row(manager, exposure)
    return {'ok': True, 'class': class_name, 'version': version,
            'contractHash': chash, 'reason': reason,
            'fieldCount': len(field_map['fields']),
            'reserved': field_map['reserved'],
            'versionRow': version_row}


def _refresh_serving():
    """Tell the serving sidecar (grpc-2) the exposure set changed.
    Failure-isolated + lazy: a knob act never breaks on a missing or
    stopped server, and this module stays importable without grpcio."""
    try:
        from grpcbridge.grpc_server import refresh_grpc_runtime
        refresh_grpc_runtime()
    except Exception:
        pass


def exposure_action(manager, class_name, action,
                    exposure_factory=None, version_factory=None,
                    transport=None):
    """The knob acts: enable | disable | regenerate | set-transport.
    All human/API-initiated; the system only ever suggests."""
    from polariDataTyping.schema_stability import is_stabilized
    exposure = get_exposure(manager, class_name)

    if action == 'enable':
        if not is_stabilized(manager, class_name):
            return _refusal(
                f'cannot enable gRPC exposure: class "{class_name}" '
                'is not stabilized', class_name,
                _stabilize_suggestion(class_name))
        if exposure is None:
            if exposure_factory is None:
                from grpcbridge.contract_basis import GrpcExposure
                exposure_factory = GrpcExposure
            exposure = exposure_factory(
                name=f'{class_name}-grpc-exposure',
                subject_class=class_name, enabled=False,
                service_name=f'PolariObjectSync.{class_name}',
                transport_preference='stomp', proto_version=0,
                contract_hash='', contract_status='never-generated',
                proto_text='', generated_at='', notes='',
                manager=manager)
        if (getattr(exposure, 'contract_status', 'never-generated')
                == 'never-generated'):
            report = generate_contract(
                manager, class_name, reason='initial',
                exposure=exposure, version_factory=version_factory)
            if not report.get('ok'):
                return report
        exposure.enabled = True
        _save_row(manager, exposure)
        _refresh_serving()
        return {'ok': True, 'class': class_name, 'enabled': True,
                'contractStatus': exposure.contract_status,
                'version': exposure.proto_version,
                'exposure': exposure}

    if exposure is None:
        return _refusal(
            f'no gRPC exposure exists for "{class_name}"', class_name,
            {'knob': f'/api/grpc/exposures/{class_name}',
             'how': 'POST {"action": "enable"}'})

    if action == 'disable':
        exposure.enabled = False
        _save_row(manager, exposure)
        _refresh_serving()
        return {'ok': True, 'class': class_name, 'enabled': False}

    if action == 'regenerate':
        report = generate_contract(manager, class_name,
                                   reason='manual-regenerate',
                                   exposure=exposure,
                                   version_factory=version_factory)
        if report.get('ok'):
            _refresh_serving()
        return report

    if action == 'set-transport':
        if transport not in ('stomp', 'grpc', 'both'):
            return _refusal(
                f'set-transport needs "transport" of stomp | grpc | '
                f'both (got {transport!r})', class_name)
        exposure.transport_preference = transport
        _save_row(manager, exposure)
        return {'ok': True, 'class': class_name,
                'transportPreference': transport}

    return _refusal(f'unknown action "{action}" (enable | disable | '
                    'regenerate | set-transport)', class_name)


def mark_exposures_stale(manager, class_name, reason=''):
    """Flip the class's exposure to 'stale'. Called (failure-isolated)
    from schema_stability.record_deviation — an OOPS invalidates the
    trusted snapshot the contract was generated from."""
    exposure = get_exposure(manager, class_name)
    if exposure is None:
        return False
    if getattr(exposure, 'contract_status', '') != 'current':
        return False
    exposure.contract_status = 'stale'
    note = f'stale: {reason or "schema deviation"} @ {_now()}'
    prior = getattr(exposure, 'notes', '') or ''
    exposure.notes = f'{prior} | {note}'.strip(' |')
    _save_row(manager, exposure)
    _refresh_serving()  # the gate shut — serving must stop NOW
    return True


def check_contracts(manager):
    """Every enabled exposure vs the CURRENT stabilization snapshot:
    hash drift or a shut gate marks it stale (observation), and each
    stale contract yields a suggestion — regeneration stays a
    human/API act."""
    from polariDataTyping.schema_stability import is_stabilized
    checked = 0
    stale = []
    suggestions = []
    for exposure in list(_rows(manager, 'GrpcExposure').values()):
        if not getattr(exposure, 'enabled', False):
            continue
        cls = getattr(exposure, 'subject_class', '')
        checked += 1
        status = getattr(exposure, 'contract_status', '')
        if status == 'current':
            if not is_stabilized(manager, cls):
                mark_exposures_stale(manager, cls,
                                     'class no longer stabilized')
                status = 'stale'
            elif (contract_hash(trusted_snapshot(manager, cls))
                    != getattr(exposure, 'contract_hash', '')):
                mark_exposures_stale(manager, cls,
                                     'stabilization snapshot drifted '
                                     'from the generated contract')
                status = 'stale'
        if status == 'stale':
            stale.append(cls)
            suggestions.append({
                'class': cls,
                'knob': f'/api/grpc/exposures/{cls}',
                'how': 'POST {"action": "regenerate"} (requires the '
                       'class to be stabilized again)',
                'evidence': getattr(exposure, 'notes', ''),
            })
    return {'ok': True, 'checked': checked, 'stale': stale,
            'suggestions': suggestions}


def exposure_summary(exposure):
    return {
        'class': getattr(exposure, 'subject_class', ''),
        'enabled': getattr(exposure, 'enabled', False),
        'serviceName': getattr(exposure, 'service_name', ''),
        'transportPreference':
            getattr(exposure, 'transport_preference', 'stomp'),
        'protoVersion': getattr(exposure, 'proto_version', 0),
        'contractHash': getattr(exposure, 'contract_hash', ''),
        'contractStatus':
            getattr(exposure, 'contract_status', 'never-generated'),
        'generatedAt': getattr(exposure, 'generated_at', ''),
        'notes': getattr(exposure, 'notes', ''),
    }


def exposure_catalogue(manager):
    """Every exposure + every stabilized class that COULD be exposed
    (candidates — the suggestion side of the knob)."""
    freshness = check_contracts(manager)
    exposures = [exposure_summary(e)
                 for e in _rows(manager, 'GrpcExposure').values()]
    exposures.sort(key=lambda e: e['class'])
    exposed = {e['class'] for e in exposures}
    candidates = []
    for profile in _rows(manager, 'SchemaStabilityProfile').values():
        cls = getattr(profile, 'subject_class', '')
        if (getattr(profile, 'status', '') == 'stabilized'
                and cls and cls not in exposed):
            candidates.append({
                'class': cls,
                'stabilizedAt': getattr(profile, 'stabilized_at', ''),
                'how': f'POST /api/grpc/exposures/{cls} '
                       '{"action": "enable"}',
            })
    candidates.sort(key=lambda c: c['class'])
    return {'ok': True, 'exposures': exposures,
            'candidates': candidates,
            'staleSuggestions': freshness['suggestions']}
