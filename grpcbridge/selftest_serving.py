"""
Selftest for grpcbridge (grpc-2, serving layer).

Run from polari-framework/:
  python3 -m grpcbridge.selftest_serving

Needs grpcio + protobuf (skips HONESTLY when missing — same idiom as
the JVM legs of selftest_javabridge). Fake manager + the REAL contract
layer (exposure_action builds the ledger) + the REAL server on an
ephemeral port + a REAL grpc client channel. Covers: server start,
reflection listing enabled services only, Get/List round-trip, Watch
receiving the change notification a MUX publish carries (field parity
with the STOMP payload asserted), stomp-only preference leaving gRPC
silent, Push landing as update AND create (with fan-out, and NO
command echo), Commands streaming full objects on a non-push change,
disabled/stale exposures refusing with evidence naming the knob, and
the shared-DB instance_id scope refusal.
"""

import json
import sys
import threading
import time
import types

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


try:
    import grpc
    from grpc_reflection.v1alpha import (reflection, reflection_pb2,
                                         reflection_pb2_grpc)
except ImportError:
    print('SKIP: grpcio / grpcio-reflection not importable — the '
          'serving selftest needs them (pip install grpcio '
          'grpcio-reflection). Honest skip, not a pass.')
    sys.exit(0)

from grpcbridge import proto_gen as pg
from grpcbridge.grpc_server import PolariGrpcServer, set_grpc_server
from grpcbridge.transport_mux import publish_crude_change
from polariApiServer import stompWebSocketServer as stomp_mod
from polariDataTyping import schema_stability as ss


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


class FakeDB:
    instanceScope = 'inst-a'

    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(row)


class FakeStomp:
    def __init__(self):
        self.published = []

    def publish(self, topic, body):
        self.published.append((topic, dict(body)))


_widget_seq = [0]


class Widget:
    """The class under sync — plain, all-defaults ctor (what the
    Push create path requires of a registered class)."""

    def __init__(self, manager=None):
        _widget_seq[0] += 1
        self.id = f'widget-gen-{_widget_seq[0]}'
        self.name = ''
        self.count = 0
        self.active = False
        self.ratio = 0.0
        self.label = ''
        self.extras = {}


SNAPSHOT = {
    'id': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
           'schemaStrategy': 'typed'},
    'name': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
             'schemaStrategy': 'typed'},
    'count': {'dominantType': 'int', 'dominantAffinity': 'INTEGER',
              'schemaStrategy': 'typed'},
    'active': {'dominantType': 'bool', 'dominantAffinity': 'INTEGER',
               'schemaStrategy': 'typed'},
    'ratio': {'dominantType': 'float', 'dominantAffinity': 'REAL',
              'schemaStrategy': 'typed'},
    'label': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
              'schemaStrategy': 'typed'},
    'extras': {'dominantType': 'dict', 'dominantAffinity': 'TEXT',
               'schemaStrategy': 'variant'},
}


def _mgr():
    mgr = types.SimpleNamespace(
        objectTables={'SchemaStabilityProfile': {},
                      'SchemaDeviationEvent': {},
                      'GrpcExposure': {},
                      'ProtoContractVersion': {},
                      'Widget': {}},
        objectTypingDict={'Widget': types.SimpleNamespace(
            classDefinition=Widget,
            apiFormatConfig=types.SimpleNamespace(
                polariTreeWsEnabled=True, flatJsonWsEnabled=False,
                d3ColumnWsEnabled=False, geoJsonWsEnabled=False))},
        db=FakeDB())
    profile = _factory(
        name='Widget-schema-stability', subject_class='Widget',
        status='stabilized', stabilize_threshold=4, clean_saves=4,
        total_saves=4, deviation_count=0, destabilize_count=0,
        field_summary_json=json.dumps(SNAPSHOT),
        stabilized_at='2026-07-09T00:00:00+00:00', destabilized_at='',
        skipped_analyses=0, notes='')
    mgr.objectTables['SchemaStabilityProfile'][profile.name] = profile
    return mgr


def _enable(mgr):
    report = pg.exposure_action(mgr, 'Widget', 'enable',
                                exposure_factory=_factory,
                                version_factory=_factory)
    assert report.get('ok'), report
    mgr.objectTables['GrpcExposure'][report['exposure'].name] = \
        report['exposure']
    for row in mgr.db.saved:
        if getattr(row, 'field_map_json', None):
            mgr.objectTables['ProtoContractVersion'][row.name] = row
    return report['exposure']


def _widget(mgr, pid, **vals):
    w = Widget(manager=mgr)
    w.id = pid
    for k, v in vals.items():
        setattr(w, k, v)
    mgr.objectTables['Widget'][pid] = w
    return w


def _stub(channel, runtime, method, kind):
    """A generic client stub off the SAME runtime message classes."""
    req_cls = {'Get': 'ObjectKey', 'List': 'ListRequest',
               'Watch': 'WatchRequest', 'Push': 'Widget',
               'Commands': 'WatchRequest'}[method]
    resp_cls = {'Get': 'Widget', 'List': 'Widget',
                'Watch': 'ChangeNotification', 'Push': 'PushSummary',
                'Commands': 'Widget'}[method]
    factory = {'uu': channel.unary_unary, 'us': channel.unary_stream,
               'su': channel.stream_unary}[kind]
    return factory(
        f'/polari.sync.WidgetSync/{method}',
        request_serializer=lambda m: m.SerializeToString(),
        response_deserializer=runtime.message_class(resp_cls)
        .FromString), runtime.message_class(req_cls)


def main():
    ss._STATUS_CACHE.clear()
    mgr = _mgr()
    exposure = _enable(mgr)
    _widget(mgr, 'w1', count=7, active=True, ratio=2.5,
            label='alpha', extras={'a': 1})
    _widget(mgr, 'w2', count=9, label='beta')

    fake_stomp = FakeStomp()
    stomp_mod.set_stomp_server(fake_stomp)

    server = PolariGrpcServer(mgr, port=0)
    server.start()
    set_grpc_server(server)
    check('server starts + serves the enabled class',
          server._running
          and server.runtime.service_names()
          == ['polari.sync.WidgetSync'])

    runtime = server.runtime
    channel = grpc.insecure_channel(f'localhost:{server.port}')

    # --- reflection lists enabled services only -----------------------
    refl = reflection_pb2_grpc.ServerReflectionStub(channel)
    resp = list(refl.ServerReflectionInfo(iter([
        reflection_pb2.ServerReflectionRequest(list_services='')]),
        timeout=5))[0]
    names = sorted(s.name for s in
                   resp.list_services_response.service)
    check('reflection: enabled service + reflection itself, nothing '
          'else',
          names == sorted(['polari.sync.WidgetSync',
                           reflection.SERVICE_NAME]), str(names))

    # --- Get round-trip ------------------------------------------------
    get, ObjectKey = _stub(channel, runtime, 'Get', 'uu')
    msg = get(ObjectKey(id='w1'), timeout=5)
    check('Get round-trips a row (typed fields + JSON variant)',
          msg.count == 7 and msg.active and msg.ratio == 2.5
          and msg.label == 'alpha'
          and json.loads(msg.extras) == {'a': 1})

    try:
        get(ObjectKey(id='nope'), timeout=5)
        check('Get unknown id -> NOT_FOUND', False)
    except grpc.RpcError as e:
        check('Get unknown id -> NOT_FOUND',
              e.code() == grpc.StatusCode.NOT_FOUND)

    try:
        get(ObjectKey(id='w1', instance_id='other-instance'), timeout=5)
        check('Get foreign instance_id refused (shared-DB scope)',
              False)
    except grpc.RpcError as e:
        check('Get foreign instance_id refused (shared-DB scope)',
              e.code() == grpc.StatusCode.NOT_FOUND
              and 'instance' in (e.details() or ''))

    # --- List ----------------------------------------------------------
    lst, ListRequest = _stub(channel, runtime, 'List', 'us')
    rows = list(lst(ListRequest(), timeout=5))
    check('List streams every row',
          sorted(m.id for m in rows) == ['w1', 'w2'])
    rows = list(lst(ListRequest(limit=1, offset=1), timeout=5))
    check('List honors limit/offset',
          [m.id for m in rows] == ['w2'])

    # --- Watch + MUX parity (preference: both) --------------------------
    exposure.transport_preference = 'both'
    watch, WatchRequest = _stub(channel, runtime, 'Watch', 'us')
    stream = watch(WatchRequest(class_name='Widget'), timeout=10)
    time.sleep(0.3)  # let the subscription register
    publish_crude_change(mgr, 'Widget', 'update', ['w1'])
    note = next(stream)
    check('Watch receives the change notification',
          note.class_name == 'Widget' and note.operation == 'update'
          and list(note.instance_ids) == ['w1']
          and note.format_type == 'crude')
    topic, body = fake_stomp.published[-1]
    check('parity: STOMP got the SAME payload fields on the same '
          'mutation',
          topic == '/topic/Widget'
          and body['className'] == note.class_name
          and body['operation'] == note.operation
          and body['instanceIds'] == list(note.instance_ids)
          and body['formatType'] == note.format_type
          and body['timestamp'] == note.timestamp)
    stream.cancel()

    # --- stomp-only preference leaves gRPC silent -----------------------
    exposure.transport_preference = 'stomp'
    stomp_before = len(fake_stomp.published)
    stream = watch(WatchRequest(class_name='Widget'), timeout=1.2)
    time.sleep(0.3)
    publish_crude_change(mgr, 'Widget', 'update', ['w2'])
    try:
        next(stream)
        check('stomp-only: gRPC watcher stays silent', False)
    except grpc.RpcError as e:
        check('stomp-only: gRPC watcher stays silent',
              e.code() == grpc.StatusCode.DEADLINE_EXCEEDED)
    check('stomp-only: STOMP still delivered',
          len(fake_stomp.published) == stomp_before + 1)

    # --- Push: update + create, fan-out, no command echo ----------------
    exposure.transport_preference = 'both'
    cmds, _ = _stub(channel, runtime, 'Commands', 'us')
    cmd_stream = cmds(WatchRequest(class_name='Widget'), timeout=1.5)
    watch_stream = watch(WatchRequest(class_name='Widget'), timeout=10)
    time.sleep(0.3)

    push, WidgetMsg = _stub(channel, runtime, 'Push', 'su')
    frames = [WidgetMsg(id='w1', count=42, ratio=3.5),
              WidgetMsg(id='hw-7', count=1, label='from-device',
                        extras=json.dumps({'src': 'sim'}))]
    summary = push(iter(frames), timeout=5)
    check('Push summary honest (2 received, 2 applied, 0 refused)',
          summary.received == 2 and summary.applied == 2
          and summary.refused == 0, str(summary))
    w1 = mgr.objectTables['Widget']['w1']
    check('Push landed as a scoped update (matched by id)',
          w1.count == 42 and w1.ratio == 3.5 and w1.label == 'alpha')
    hw = mgr.objectTables['Widget'].get('hw-7')
    check('Push created the unknown row keyed by the pushed id',
          hw is not None and hw.count == 1
          and hw.label == 'from-device'
          and hw.extras == {'src': 'sim'})
    got = {next(watch_stream).instance_ids[0] for _ in range(2)}
    check('pushed frames fan out to Watch subscribers',
          got == {'w1', 'hw-7'})

    # id-less frame: identity falls back to the `name` convention
    # (live stabilization snapshots often don't carry the polari id)
    mgr.objectTables['Widget']['w2'].name = 'rig-two'
    rows_before = len(mgr.objectTables['Widget'])
    summary = push(iter([WidgetMsg(name='rig-two', count=77)]),
                   timeout=5)
    check('id-less Push matches by name (updates, never multiplies '
          'rows)',
          summary.applied == 1
          and mgr.objectTables['Widget']['w2'].count == 77
          and len(mgr.objectTables['Widget']) == rows_before)
    try:
        next(cmd_stream)
        check('pushed telemetry does NOT echo down the Commands '
              'stream', False)
    except grpc.RpcError as e:
        check('pushed telemetry does NOT echo down the Commands '
              'stream',
              e.code() == grpc.StatusCode.DEADLINE_EXCEEDED)
    watch_stream.cancel()

    # --- Commands: a human/API change streams the full object down ------
    cmd_stream = cmds(WatchRequest(class_name='Widget'), timeout=10)
    time.sleep(0.3)
    w1.label = 'commanded'
    publish_crude_change(mgr, 'Widget', 'update', ['w1'])
    cmd = next(cmd_stream)
    check('Commands streams the FULL object on a non-push change',
          cmd.id == 'w1' and cmd.label == 'commanded'
          and cmd.count == 42)
    cmd_stream.cancel()

    # --- the gate: disabled + stale refuse with evidence ----------------
    report = pg.exposure_action(mgr, 'Widget', 'disable')
    assert report.get('ok')
    check('disable knob empties the serving runtime',
          server.runtime.service_names() == [])
    try:
        get(ObjectKey(id='w1'), timeout=5)
        check('disabled exposure refuses naming the knob', False)
    except grpc.RpcError as e:
        check('disabled exposure refuses naming the knob',
              e.code() == grpc.StatusCode.FAILED_PRECONDITION
              and '/api/grpc/exposures/Widget' in (e.details() or ''))

    pg.exposure_action(mgr, 'Widget', 'enable')
    check('re-enable restores serving',
          server.runtime.service_names()
          == ['polari.sync.WidgetSync'])
    pg.mark_exposures_stale(mgr, 'Widget', 'selftest OOPS')
    check('stale flip stops serving immediately',
          server.runtime.service_names() == [])
    try:
        get(ObjectKey(id='w1'), timeout=5)
        check('stale contract refuses with evidence', False)
    except grpc.RpcError as e:
        check('stale contract refuses with evidence',
              e.code() == grpc.StatusCode.FAILED_PRECONDITION
              and 'stale' in (e.details() or ''))

    server.stop()
    set_grpc_server(None)
    stomp_mod.set_stomp_server(None)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
