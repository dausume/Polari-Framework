"""
Selftest for grpcbridge java_bridge (grpc-j1, the Polari Hardware
Bridge generator).

Run from polari-framework/:
  python3 -m grpcbridge.selftest_javabridge

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

from grpcbridge import java_bridge as jb
from grpcbridge import proto_gen as pg
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

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed'
          + (f'; {len(_skips)} skipped (no JDK)' if _skips else '')
          + (f'; FAILED: {failed}' if failed else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
