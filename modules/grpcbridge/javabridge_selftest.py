"""
Selftest for grpcbridge java_bridge (grpc-j1, the Polari Hardware
Bridge generator).

Run from polari-framework/:
  python3 -m grpcbridge.javabridge_selftest

Stdlib-only fake manager (same idiom as selftest_contracts) PLUS a
real toolchain leg when javac/java are on PATH: the generated app's
dependency-free core is COMPILED and RUN — the loopback selftest
(frame round-trip, corrupted-CRC rejection, command round-trip
against the simulated MCU) and a bounded BridgeMain run. Skips the
toolchain leg honestly when no JDK is present.
"""

import json
import re
import shutil
import subprocess
import tempfile
import types
from pathlib import Path

from grpcbridge.custom import java_bridge as jb
from grpcbridge.custom import proto_gen as pg
from polariDataTyping import schema_stability as ss

_results = []
_skips = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def skip(label, why):
    _skips.append(label)
    print(f'SKIP: {label} — {why}')


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


class FakeDB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(row)


SNAPSHOTS = {
    'Widget': {
        'count': {'dominantType': 'int',
                  'dominantAffinity': 'INTEGER',
                  'schemaStrategy': 'typed'},
        'active': {'dominantType': 'bool',
                   'dominantAffinity': 'INTEGER',
                   'schemaStrategy': 'typed'},
        'ratio': {'dominantType': 'float', 'dominantAffinity': 'REAL',
                  'schemaStrategy': 'typed'},
        'label': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
                  'schemaStrategy': 'typed'},
        'extras': {'dominantType': 'dict', 'dominantAffinity': 'TEXT',
                   'schemaStrategy': 'variant'},
    },
    'SensorFrame': {
        'sample_rate_hz': {'dominantType': 'float',
                           'dominantAffinity': 'REAL',
                           'schemaStrategy': 'typed'},
        'channel': {'dominantType': 'int',
                    'dominantAffinity': 'INTEGER',
                    'schemaStrategy': 'typed'},
        'unit': {'dominantType': 'str', 'dominantAffinity': 'TEXT',
                 'schemaStrategy': 'typed'},
    },
}


def _int(): return {'dominantType': 'int', 'dominantAffinity': 'INTEGER', 'schemaStrategy': 'typed'}


def _bool(): return {'dominantType': 'bool', 'dominantAffinity': 'TEXT', 'schemaStrategy': 'typed'}


def _str(): return {'dominantType': 'str', 'dominantAffinity': 'TEXT', 'schemaStrategy': 'typed'}


# ucd-0e1: THE WIRE CONTRACT of the button-clock demo — same field shapes as the pinned contracts
# (board/custom/contracts/ButtonClock{State,Event}.v1.json), so this fresh in-process generation reproduces them.
SNAPSHOTS['ButtonClockState'] = {
    'name': _str(), 'seq': _int(), 'boot_session': _int(), 'uptime_ms': _int(), 'epoch_s': _int(), 'ms': _int(),
    'clock_synced': _bool(), 'sync_generation': _int(), 'sync_uncertainty_ms': _int(), 'drift_ms': _int(),
    'button_presses': _int(), 'led_on': _bool(), 'led_changed_at': _int(), 'sense_rises': _int(),
    'sense_falls': _int(), 'last_edge_at': _int(), 'last_edge_ms': _int(), 'dropped_events': _int(),
    'status': _str(), 'set_epoch_s': _int(), 'set_ms': _int(), 'set_sync_generation': _int(), 'set_led': _bool(),
    'snapshot': _bool(),
}
SNAPSHOTS['ButtonClockEvent'] = {
    'name': _str(), 'seq': _int(), 'boot_session': _int(), 'kind': _str(), 'uptime_ms': _int(), 'epoch_s': _int(),
    'ms': _int(),
}


def _mgr():
    mgr = types.SimpleNamespace(
        objectTables={'SchemaStabilityProfile': {},
                      'SchemaDeviationEvent': {},
                      'GrpcExposure': {},
                      'ProtoContractVersion': {},
                      'HardwareBridgeDefinition': {}},
        objectTypingDict={}, db=FakeDB())
    for cls, snap in SNAPSHOTS.items():
        profile = _factory(
            name=f'{cls}-schema-stability', subject_class=cls,
            status='stabilized', stabilize_threshold=4,
            clean_saves=4, total_saves=4, deviation_count=0,
            destabilize_count=0,
            field_summary_json=json.dumps(snap),
            stabilized_at='2026-07-09T00:00:00+00:00',
            destabilized_at='', skipped_analyses=0, notes='')
        mgr.objectTables['SchemaStabilityProfile'][profile.name] = \
            profile
    return mgr


def _track(mgr, row, table):
    mgr.objectTables[table][getattr(row, 'name', str(id(row)))] = row


def _enable(mgr, cls):
    """enable + register created rows in the fake tables (the real
    object tree does this registration in production)."""
    report = pg.exposure_action(mgr, cls, 'enable',
                                exposure_factory=_factory,
                                version_factory=_factory)
    assert report.get('ok'), report
    _track(mgr, report['exposure'], 'GrpcExposure')
    for row in mgr.db.saved:
        if getattr(row, 'field_map_json', None) is not None \
                and getattr(row, 'version', None) is not None:
            _track(mgr, row, 'ProtoContractVersion')
    return report


def _bridge_row(classes, **overrides):
    fields = dict(
        name='sim-rig-hw-bridge', bridge_name='sim-rig',
        source='simulated', serial_device='/dev/ttyACM0',
        baud=115200, exposed_classes_json=json.dumps(classes),
        sim_rate_hz=0, grpc_enabled=False,
        grpc_target='localhost:3002', device_id=1,
        last_generated_at='', manifest_json='{}',
        contract_hashes_json='{}', notes='')
    fields.update(overrides)
    return _factory(**fields)


def _run(cmd, cwd=None, timeout=120):
    return subprocess.run(cmd, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)


def _wire_checks(mgr):
    """grpc-j4: two Widget bindings + an EnumMapping on `label` → the
    generated project carries the mapping (width 1, enum, bindings)."""
    from grpcbridge.custom import wire_contract as wc
    mgr.objectTables.setdefault('HardwareInterfaceBinding', {})
    mgr.objectTables.setdefault('EnumMapping', {})
    for k in (1, 0):   # created out of order: indexes are assigned densely
        _track(mgr, _factory(
            name=f'pair/Widget/{k}', bridge_name='pair',
            object_class='Widget', object_name=f'widget-{k}',
            board_instance=f'twin:x#{k}', board_definition='x',
            interface_kind='twin-pty', interface_name='usart0',
            port=f'/tmp/w{k}', adapter='', instance_index=5 + k,
            wire_version=2, contract_hash_v2=''),
            'HardwareInterfaceBinding')
    _track(mgr, _factory(name='Widget.label', object_class='Widget',
                         field='label',
                         labels_json='["idle", "busy"]',
                         unknown_label='unknown'), 'EnumMapping')
    bridge = _bridge_row(['Widget', 'SensorFrame'], bridge_name='pair',
                         name='pair-hw-bridge', source='serial')
    _track(mgr, bridge, 'HardwareBridgeDefinition')
    rep = jb.generate_project(mgr, bridge, row_factory=_factory)
    check('grpc-j4 generate: a bridge with bindings + an enum mapping',
          rep.get('ok'), str(rep.get('error')))
    if not rep.get('ok'):
        return None
    f = rep['files']
    props = f['bridge.properties']
    idx = sorted((b.object_name, b.instance_index) for b in
                 mgr.objectTables['HardwareInterfaceBinding'].values())
    check('grpc-j4 indexes assigned densely 0..n-1 per class per bridge',
          idx == [('widget-0', 0), ('widget-1', 1)], str(idx))
    wcr = mgr.objectTables.get('WireContract', {}).get('Widget@pair')
    codec = f[f'{jb.JAVA_DIR}/codec/WidgetCodec.java']
    check('grpc-j4 two Widget instances on one bridge → a 1-bit index; '
          'the WireContract row carries width, enums and hash v2',
          'INDEX_WIDTH = 1;' in codec and wcr is not None
          and wcr.index_width == 1 and wcr.instance_count == 2
          and json.loads(wcr.enums_json) == {'label': ['idle', 'busy']}
          and wcr.contract_hash_v2 == rep['wireContracts']['Widget'][
              'hashV2'], str(rep.get('wireContracts')))
    check('grpc-j4 SensorFrame (no bindings) stays one instance: width 0',
          'INDEX_WIDTH = 0;' in
          f[f'{jb.JAVA_DIR}/codec/SensorFrameCodec.java'])
    check('grpc-j4 bridge.properties carries the bindings (identity '
          'lives here and in the gRPC message, never the struct)',
          'bridge.name=pair' in props and 'binding.count=2' in props
          and 'binding.1.object=widget-1' in props
          and 'binding.1.index=1' in props
          and 'binding.0.port=/tmp/w0' in props)
    proto = f['src/main/proto/polari_bridge.proto']
    check('grpc-j4 proto: HardwareInterface once, hardware_interface = '
          '2047 on each class, the enum declared, the field still string',
          proto.count('message HardwareInterface {') == 1
          and proto.count('HardwareInterface hardware_interface = 2047;')
          == 2 and 'enum WidgetLabel {' in proto
          and 'WIDGET_LABEL_BUSY = 2;' in proto
          and re.search(r'string label = \d+;', proto))
    enum = f.get(f'{jb.JAVA_DIR}/codec/WidgetLabelEnum.java', '')
    fwd = f[f'{jb.JAVA_DIR}/grpc/GrpcForwarder.java']
    check('grpc-j4 Java: the enum class, encodeV2/decodeFrame in the codec, '
          'the forwarder re-attaches identity up and routes by index down',
          'BUSY(2, "busy")' in enum and 'encodeV2(' in codec
          and 'decodeFrame(' in codec and 'setHardwareInterface(hw)' in fwd
          and 'port.sendTo("Widget", b.index' in fwd
          and 'refused: Widget index' in fwd)
    _ = wc
    return f


def _wire_jvm(files, javac, java):
    with tempfile.TemporaryDirectory(prefix='polari-jwire-') as tmp:
        root = Path(tmp)
        for path, text in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        core = [str(p) for p in (root / 'src/main/java').rglob('*.java')
                if '/grpc/' not in str(p)]
        comp = _run([javac, '--release', '17', '-d', str(root / 'out')]
                    + core)
        loop = _run([java, '-cp', str(root / 'out'),
                     'org.polari.bridge.LoopbackSelfTest']) \
            if comp.returncode == 0 else None
        check('grpc-j4 JVM: the bound project compiles; v2 round-trips '
              'carry index 1 and the enum (Widget) and index 0 '
              '(SensorFrame)',
              comp.returncode == 0 and loop is not None
              and loop.returncode == 0
              and re.search(r'PASS: v2 round-trip index=1 v2 Widget\{.*'
                            r'label=(idle|busy)', loop.stdout)
              and 'PASS: v2 round-trip index=0 v2 SensorFrame{'
              in loop.stdout,
              (comp.stderr[:600] + (loop.stdout[-600:] if loop else '')))


def _button_clock_checks(mgr, javac, java):
    """ucd-0e1: THE WIRE CONTRACT of the button-clock demo, end to end through the SAME machinery as Widget/
    SensorFrame above — the bridge row, both contracts, the WireContract derivation (grpc-j4), the generated Java
    project (record + codec + enums + registry + forwarder), and the JVM loopback (compile + run, honestly skipped
    with no JDK)."""
    from grpcbridge.custom import wire_contract as wc
    from grpcbridge.mapping_basis import SEED_BUTTON_CLOCK_BRIDGE
    mgr.objectTables.setdefault('HardwareInterfaceBinding', {})
    mgr.objectTables.setdefault('EnumMapping', {})
    mgr.objectTables.setdefault('WireContract', {})
    from grpcbridge.mapping_basis import SEED_ENUM_MAPPINGS
    for row in SEED_ENUM_MAPPINGS:
        if row['object_class'] in ('ButtonClockState', 'ButtonClockEvent'):
            _track(mgr, _factory(**row), 'EnumMapping')

    _enable(mgr, 'ButtonClockState')
    _enable(mgr, 'ButtonClockEvent')
    bridge = _bridge_row(['ButtonClockState', 'ButtonClockEvent'], **SEED_BUTTON_CLOCK_BRIDGE)
    _track(mgr, bridge, 'HardwareBridgeDefinition')

    # grpc-j4: the WireContract row per class on this bridge — DERIVED (never seeded), the same call
    # board_mapping_selftest.py makes for SimRigState@uno-pair. One unbound serial device: instance_count 1 (no
    # index on the wire), exactly like a single uno-adc-sweep board.
    for cls in ('ButtonClockState', 'ButtonClockEvent'):
        exp = pg.get_exposure(mgr, cls)
        fm = jb._field_map_for(mgr, cls, exp.proto_version)
        row, s = wc.derive(mgr, cls, 'button-clock', fm, exp.proto_version, exp.contract_hash, 'live',
                           factory=_factory)
        check('ucd-0e1: WireContract %s@button-clock derives — one unbound serial device (instance_count 1, no '
              'index on the wire), boot_session carried in field_order, the enum table present' % cls,
              row.instance_count == 1 and row.index_repr == 'none' and row.bridge_name == 'button-clock'
              and any(n == 'boot_session' for n, _ in json.loads(row.field_order_json))
              and bool(json.loads(row.enums_json)))

    rep = jb.generate_project(mgr, bridge, row_factory=_factory)
    check('ucd-0e1: generate_project ok for the button-clock bridge (both contracts ready)', rep.get('ok'),
          str(rep.get('error')))
    if not rep.get('ok'):
        return None
    f = rep['files']
    check('ucd-0e1: msg_type order — ButtonClockState=1, ButtonClockEvent=2 (the bridge\'s exposed_classes_json order)',
          'MSG_TYPE = 1' in f[f'{jb.JAVA_DIR}/codec/ButtonClockStateCodec.java']
          and 'MSG_TYPE = 2' in f[f'{jb.JAVA_DIR}/codec/ButtonClockEventCodec.java'])
    record = f[f'{jb.JAVA_DIR}/codec/ButtonClockStateRecord.java']
    codec = f[f'{jb.JAVA_DIR}/codec/ButtonClockStateCodec.java']
    erecord = f[f'{jb.JAVA_DIR}/codec/ButtonClockEventRecord.java']
    check('ucd-0e1: boot_session is a Java field on BOTH generated records (the bridge\'s reboot-vs-reconnect rule)',
          'public long boot_session;' in record and 'public long boot_session;' in erecord)
    check('ucd-0e1: the three SET_TIME fields + SET_LED + SNAPSHOT are ordinary Java fields on the record — no '
          'second message kind',
          all('public long %s;' % n in record for n in ('set_epoch_s', 'set_ms', 'set_sync_generation'))
          and 'public boolean set_led;' in record and 'public boolean snapshot;' in record)
    enum_s = f.get(f'{jb.JAVA_DIR}/codec/ButtonClockStateStatusEnum.java', '')
    enum_e = f.get(f'{jb.JAVA_DIR}/codec/ButtonClockEventKindEnum.java', '')
    check('ucd-0e1: the status/kind enums are generated Java enums (idle|commanded|synced|snapshot; '
          'press|led_on|led_off|sense_rise|sense_fall|sync)',
          'SYNCED(3, "synced")' in enum_s and 'SNAPSHOT(4, "snapshot")' in enum_s
          and 'SENSE_FALL(5, "sense_fall")' in enum_e and 'SYNC(6, "sync")' in enum_e)
    proto = f['src/main/proto/polari_bridge.proto']
    check('ucd-0e1: both services in the bundled proto, both carry the hardware_interface identity tag',
          'service ButtonClockStateSync' in proto and 'service ButtonClockEventSync' in proto
          and proto.count('HardwareInterface hardware_interface = 2047;') >= 2)
    check('ucd-0e1: bridge.properties carries source=serial, baud 115200 (the real kit, not the internal simulation)',
          'source=serial' in f['bridge.properties'] and 'serial.baud=115200' in f['bridge.properties'])

    if not (javac and java):
        return f
    with tempfile.TemporaryDirectory(prefix='polari-jbuttonclock-') as tmp:
        root = Path(tmp)
        for path, text in f.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        core = [str(p) for p in (root / 'src/main/java').rglob('*.java')
                if '/grpc/' not in str(p)]
        comp = _run([javac, '--release', '17', '-d', str(root / 'out')] + core)
        check('ucd-0e1 JVM: the generated button-clock core compiles cleanly', comp.returncode == 0,
              comp.stderr[:800])
        if comp.returncode == 0:
            loop = _run([java, '-cp', str(root / 'out'), 'org.polari.bridge.LoopbackSelfTest'])
            check('ucd-0e1 JVM: LOOPBACK OK for ButtonClockState + ButtonClockEvent — frame/CRC round-trip, the '
                  'enum, AND the command round-trip (ButtonClockState is msg_type 1, so the generic command-path '
                  'check in LoopbackSelfTest exercises its command fields against the simulated MCU)',
                  loop.returncode == 0 and 'LOOPBACK OK' in loop.stdout
                  and 'command round-trip' in loop.stdout
                  and loop.stdout.count('PASS: v2 round-trip') == 2,
                  loop.stdout[-800:] + loop.stderr[-200:])
    return f


def _wire_many(mgr, javac, java):
    """grpc-j4 at scale: 20 SensorFrame interfaces on one bridge → past
    packed_max_bits 4 the index becomes an explicit byte (version 3)."""
    for k in range(20):
        _track(mgr, _factory(
            name=f'many/SensorFrame/{k}', bridge_name='many',
            object_class='SensorFrame', object_name=f'sensor-{k}',
            board_instance=f'bus:rs485#{k}', board_definition='x',
            interface_kind='serial', interface_name='usart0',
            port='/tmp/bus', adapter='', instance_index=k,
            wire_version=2, contract_hash_v2=''),
            'HardwareInterfaceBinding')
    bridge = _bridge_row(['SensorFrame'], bridge_name='many',
                         name='many-hw-bridge', source='serial')
    _track(mgr, bridge, 'HardwareBridgeDefinition')
    rep = jb.generate_project(mgr, bridge, row_factory=_factory)
    f = rep.get('files', {})
    codec = f.get(f'{jb.JAVA_DIR}/codec/SensorFrameCodec.java', '')
    wcr = mgr.objectTables.get('WireContract', {}).get('SensorFrame@many')
    check('grpc-j4 n=20 on one bridge: an explicit index BYTE (wire version '
          '3), the suggestion (5 bits) and the knob recorded on the row',
          rep.get('ok') and 'WIRE_VERSION = 3;' in codec
          and 'INDEX_BYTES = 1;' in codec and wcr is not None
          and wcr.index_repr == 'byte' and wcr.suggested_index_width == 5
          and wcr.packed_max_bits == 4 and 'explicit 1-byte' in wcr.notes
          and f['bridge.properties'].count('.port=/tmp/bus') == 20,
          str(rep.get('error') or (wcr and wcr.notes)))
    if not (javac and java and rep.get('ok')):
        return
    with tempfile.TemporaryDirectory(prefix='polari-jmany-') as tmp:
        root = Path(tmp)
        for path, text in f.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        core = [str(p) for p in (root / 'src/main/java').rglob('*.java')
                if '/grpc/' not in str(p)]
        comp = _run([javac, '--release', '17', '-d', str(root / 'out')]
                    + core)
        loop = _run([java, '-cp', str(root / 'out'),
                     'org.polari.bridge.LoopbackSelfTest']) \
            if comp.returncode == 0 else None
        check('grpc-j4 JVM n=20: index 19 survives encodeV2 -> frame '
              '(version byte 3) -> parse -> decodeFrame',
              loop is not None and loop.returncode == 0
              and 'PASS: v2 round-trip index=19 v3 SensorFrame{'
              in loop.stdout,
              comp.stderr[:400] + (loop.stdout[-400:] if loop else ''))


def main():
    ss._STATUS_CACHE.clear()
    mgr = _mgr()

    # --- gate: unexposed class blocks generation with the knob named ----
    bridge = _bridge_row(['Widget', 'Ghost'])
    _track(mgr, bridge, 'HardwareBridgeDefinition')
    report = jb.generate_project(mgr, bridge)
    ghost = next((b for b in report.get('blocked', [])
                  if b['class'] == 'Ghost'), {})
    check('gate: unexposed class refused, knob named',
          not report.get('ok')
          and '/api/grpc/exposures/Ghost' in ghost.get('knob', ''))

    # --- generate a real two-class project ---------------------------------
    _enable(mgr, 'Widget')
    _enable(mgr, 'SensorFrame')
    bridge = _bridge_row(['Widget', 'SensorFrame'])
    _track(mgr, bridge, 'HardwareBridgeDefinition')
    report = jb.generate_project(mgr, bridge)
    check('generate: two-class project ok', report.get('ok'),
          str(report.get('error')))
    files = report['files']
    expected = ['pom.xml', 'README.md', 'bridge.properties',
                'install-ubuntu.sh',
                'systemd/polari-hw-bridge-sim-rig.service',
                'src/main/proto/polari_bridge.proto',
                f'{jb.JAVA_DIR}/PolariPacket.java',
                f'{jb.JAVA_DIR}/DevicePort.java',
                f'{jb.JAVA_DIR}/SimulatedDevice.java',
                f'{jb.JAVA_DIR}/SerialCdcPort.java',
                f'{jb.JAVA_DIR}/BridgeMain.java',
                f'{jb.JAVA_DIR}/CodecRegistry.java',
                f'{jb.JAVA_DIR}/codec/WidgetCodec.java',
                f'{jb.JAVA_DIR}/codec/SensorFrameRecord.java',
                f'{jb.JAVA_DIR}/grpc/GrpcForwarder.java']
    missing = [p for p in expected if p not in files]
    check('generate: every expected file present', not missing,
          f'missing {missing}')

    proto = files['src/main/proto/polari_bridge.proto']
    check('bundle: shared messages exactly once',
          proto.count(pg.SHARED_MARK_START) == 1)
    check('bundle: both services + Commands rpc present',
          'service WidgetSync' in proto
          and 'service SensorFrameSync' in proto
          and proto.count('rpc Commands (WatchRequest)') == 2)
    check('msg_type: order of the class list (Widget=1, '
          'SensorFrame=2)',
          'MSG_TYPE = 1' in files[
              f'{jb.JAVA_DIR}/codec/WidgetCodec.java']
          and 'MSG_TYPE = 2' in files[
              f'{jb.JAVA_DIR}/codec/SensorFrameCodec.java'])
    check('forwarder: both directions generated (push + commands)',
          'public void push(PolariPacket packet)' in files[
              f'{jb.JAVA_DIR}/grpc/GrpcForwarder.java']
          and 'startCommandsWidget();' in files[
              f'{jb.JAVA_DIR}/grpc/GrpcForwarder.java']
          and 'port.send(new PolariPacket(' in files[
              f'{jb.JAVA_DIR}/grpc/GrpcForwarder.java'])
    check('knob: bridge.properties carries simulated-first defaults',
          'source=simulated' in files['bridge.properties']
          and 'grpc.enabled=false' in files['bridge.properties'])
    check('manifest: every file listed with hash',
          len(report['manifest']) == len(files)
          and all(m['sha256'] for m in report['manifest']))

    # --- grpc-j4: the computer<->firmware mapping on a bridge -------------------
    wire_files = _wire_checks(mgr)

    # --- tarball ------------------------------------------------------------
    blob = jb.tarball(report)
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as tar:
        names = tar.getnames()
    check('tarball: opens and contains the project root',
          'polari-hw-bridge-sim-rig/pom.xml' in names
          and len(names) == len(files))
    check('tarball: deterministic across rebuilds',
          jb.tarball(report) == blob)

    # --- toolchain leg: compile + run the generated core ---------------------
    javac = shutil.which('javac')
    java = shutil.which('java')
    if not javac or not java:
        skip('javac compile of generated core', 'no JDK on PATH')
        skip('LoopbackSelfTest run', 'no JDK on PATH')
        skip('BridgeMain bounded simulated run', 'no JDK on PATH')
    else:
        with tempfile.TemporaryDirectory(
                prefix='polari-jbridge-') as tmp:
            root = Path(tmp)
            for path, text in files.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            core = [str(p) for p in
                    (root / 'src/main/java').rglob('*.java')
                    if '/grpc/' not in str(p)]
            out = root / 'out'
            compiled = _run([javac, '--release', '17', '-d',
                             str(out)] + core)
            check('javac: generated core compiles cleanly',
                  compiled.returncode == 0, compiled.stderr[:800])
            if compiled.returncode == 0:
                loop = _run([java, '-cp', str(out),
                             'org.polari.bridge.LoopbackSelfTest'])
                check('loopback: frame + CRC + command round-trips '
                      'all pass in the JVM',
                      loop.returncode == 0
                      and 'LOOPBACK OK' in loop.stdout
                      and 'command round-trip' in loop.stdout,
                      loop.stdout[-800:] + loop.stderr[-200:])
                check('grpc-j4 loopback: every class survives encodeV2 -> '
                      'frame -> parse -> decodeFrame (field 0 absent); the '
                      'resync keeps both frames after garbage ending in 0x4C '
                      'and a frame cut short',
                      loop.stdout.count('PASS: v2 round-trip') == 2
                      and 'PASS: resync keeps both frames [50, 51]'
                      in loop.stdout, loop.stdout[-800:])
                run = _run([java, '-cp', str(out),
                            'org.polari.bridge.BridgeMain',
                            str(root / 'bridge.properties'),
                            '--max-frames=6'])
                frames = re.search(r'done: frames=(\d+)',
                                   run.stdout)
                check('bridge app: bounded simulated run decodes '
                      'both classes + reports stats',
                      run.returncode == 0 and frames
                      and frames.group(1) == '6'
                      and 'Widget{' in run.stdout
                      and 'SensorFrame{' in run.stdout,
                      run.stdout[-800:] + run.stderr[-200:])

    if wire_files and javac and java:
        _wire_jvm(wire_files, javac, java)
    _wire_many(mgr, javac, java)
    _button_clock_checks(mgr, javac, java)   # ucd-0e1: THE WIRE CONTRACT of the button-clock demo

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed'
          + (f'; {len(_skips)} skipped (no JDK)' if _skips else '')
          + (f'; FAILED: {failed}' if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
