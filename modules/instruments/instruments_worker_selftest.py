"""instruments_worker_selftest — osc-5 (OSCILLOSCOPE_PLAN.md §3f): the scope-engines WORKER (polari-rf-node/prf-scope-engines/scope_engines_service.py,
run here on a free loopback port under wsgiref against the framework's own module files) answers /capability with the profiles and its SCPI
ports; the backend's engines seam resolves it (knob → worker; knob unreachable → REFUSAL, never a silent fallback; no knob → in-process;
where=worker without a worker → refusal naming the tile); start / source / feed / stop go to the worker and the capture reads the emulated
DHO804 over SCPI at the worker's port exactly as the in-process one; the catalog tile and the binder exist; `pol dev deploy scope-engines` is
listed. The measured process block is printed for COST.md.

    PYTHONPATH=.:modules python3 -m instruments.instruments_worker_selftest      # from polari-framework/
"""
import importlib.util
import json
import os
import re
import socket
import sys
import threading
import wsgiref.simple_server

passed = total = 0
_FW = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WORKER_DIR = os.path.join(os.path.dirname(_FW), 'prf-scope-engines')


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


class _Quiet(wsgiref.simple_server.WSGIRequestHandler):
    def log_message(self, *a):
        pass


def _serve(app):
    srv = wsgiref.simple_server.make_server('127.0.0.1', 0, app, handler_class=_Quiet)
    srv.daemon_threads = True
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, 'http://127.0.0.1:%d' % srv.server_address[1]


def _load_worker():
    first = socket.socket()
    first.bind(('127.0.0.1', 0))
    port = first.getsockname()[1]
    first.close()
    os.environ['SCOPE_SCPI_HOST'] = '127.0.0.1'
    os.environ['SCOPE_SCPI_PORT_FIRST'] = str(port)
    os.environ['SCOPE_SCPI_PORTS'] = '2'
    os.environ['SCOPE_VENDOR'] = os.path.join(_FW, 'modules')    # the framework's own module files stand in for vendor/
    spec = importlib.util.spec_from_file_location('scope_engines_service', os.path.join(_WORKER_DIR, 'scope_engines_service.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    from instruments.custom import scope_engines as SE
    from instruments.custom import captures as X
    from instruments.custom import lineage as L
    from instruments.custom.client import ScopeClient
    os.environ.pop(SE.KNOB, None)
    r = SE.resolve('auto')
    check('osc-5 LADDER: no knob, no binding row -> in-process, saying why', r['how'] == 'local' and 'no worker declared' in r['why'], r)
    r = SE.resolve('worker')
    check('osc-5 LADDER: where=worker with nothing declared -> refusal naming the knob, the tile and pol dev deploy scope-engines',
          r['how'] == 'refused' and SE.KNOB in r['why'] and 'scope-engines' in r['why'] and 'pol dev deploy' in r['why'], r)
    os.environ[SE.KNOB] = 'http://127.0.0.1:9/'
    r = SE.resolve('auto')
    check('osc-5 LADDER: the knob set to an unreachable worker -> REFUSAL (never a silent fallback to in-process)', r['how'] == 'refused' and 'unreachable' in r['why'], r)
    st, p = X.start_emulator(None, {'name': 'emu-x'})
    check('osc-5 DOOR with an unreachable knob: start is 502 with the refusal words', st == 502 and 'unreachable' in p['error'], p)
    check('osc-5 LADDER: where=local ignores the knob', SE.resolve('local')['how'] == 'local')
    check('osc-5 LADDER: a bad where is refused', SE.resolve('somewhere')['how'] == 'refused')
    mod = _load_worker()
    srv, url = _serve(mod.app)
    os.environ[SE.KNOB] = url
    try:
        cap = SE.capability(url)
        check('osc-5 WORKER /capability: worker scope-engines, profile dho804 (4 channels, 12 bits), two SCPI ports free, the cost block (unmeasured until the first build), a process block',
              cap and cap['worker'] == 'scope-engines' and cap['profiles']['dho804']['channels'] == 4 and cap['profiles']['dho804']['bits'] == 12
              and len(cap['scpi']['free']) == 2 and cap['scpi']['host'] == '127.0.0.1' and 'fidelity' in cap['resources'] and cap['process']['rss_mb'] > 0, cap)
        r = SE.resolve('auto')
        check('osc-5 LADDER: the knob names a reachable worker -> worker, with its capability', r['how'] == 'worker' and r['url'] == url and r.get('capability'), r)
        X._MEM['InstrumentEndpoint'].clear()
        X._MEM['WaveformCapture'].clear()
        st, p = X.start_emulator(None, {'name': 'emu-w', 'sources': {'1': {'kind': 'sine', 'freq_hz': 500, 'amp_v': 1.5}}})
        check('osc-5 DOOR start via the worker: 201, where=worker, the endpoint row carries the worker host + the SCPI port the worker handed out, note names the worker',
              st == 201 and p['where'] == 'worker' and p['port'] in cap['scpi']['ports'] and X.endpoint(None, 'emu-w')['address'] == '127.0.0.1'
              and X.endpoint(None, 'emu-w')['port'] == p['port'] and 'scope-engines worker' in X.endpoint(None, 'emu-w')['note'], p)
        wl = json.loads(json.dumps(SE._request('GET', url + '/emulators')))
        check('osc-5 WORKER /emulators lists it with ch1 sine 500 Hz', len(wl['rows']) == 1 and 'sine 500 Hz' in wl['rows'][0]['sources']['1'], wl)
        st, p = X.idn(None, 'emu-w')
        check('osc-5 *IDN? over SCPI at the worker port: POLARI,DHO804-EMU,...', st == 200 and p['idn'].startswith('POLARI,DHO804-EMU'), p)
        st, p = X.set_source(None, 'emu-w', {'channel': 2, 'source': {'kind': 'dc', 'offset_v': 1.25}})
        check('osc-5 DOOR source via the worker: 200, where=worker', st == 200 and p.get('where') == 'worker' and p['source'] == 'dc 1.25 V', p)
        st, p = X.capture(None, 'emu-w', {'channels': [1, 2], 'max_points': 4000})
        check('osc-5 CAPTURE from the worker-hosted emulator over SCPI: 201, two rows of 4000 points, ch1 peaks at 1.5 V, ch2 reads 1.25 V, source emulated with the worker named',
              st == 201 and len(p['rows']) == 2 and abs(p['rows'][0]['v_max'] - 1.5) <= 8.0 / 4096 and abs(p['rows'][1]['v_mean'] - 1.25) <= 8.0 / 4096
              and p['rows'][0]['source'] == 'emulated' and 'on worker' in p['rows'][0]['source_ref'], p)
        st, p = X.feed_device(None, 'emu-w', {'stimulus': 'uno-light', 'channels': {'3': 'PD2'}})
        check('osc-5 FEED via the worker: the stimulus is resolved HERE (the worker has no board module) and the specs posted; 200 with ch3 <- PD2',
              st == 200 and p['channels']['3'].endswith('<- PD2'), p)
        st, p = X.capture(None, 'emu-w', {'channels': [3]})
        check('osc-5 the fed channel captured from the worker: 0..5 V pulses, source_ref names the feed', st == 201 and abs(p['rows'][0]['v_max'] - 5.0) <= 16.0 / 4096
              and 'feed from stimulus uno-light' in p['rows'][0]['source_ref'], p)
        with ScopeClient('127.0.0.1', X.endpoint(None, 'emu-w')['port']) as sc:
            srate = float(sc.query(':ACQ:SRAT?'))
        check('osc-5 a plain SCPI client at the worker port sees the same instrument (three channels on -> the 4-channel sample-rate cap applies when the depth asks for it)', srate > 0)
        st2, p2 = X.start_emulator(None, {'name': 'emu-w2'})
        st3, p3 = X.start_emulator(None, {'name': 'emu-w3'})
        check('osc-5 WORKER ports: a second emulator takes the second port; a third is refused (409 -> 502 here) because every port is taken',
              st2 == 201 and p2['port'] != p['rows'][0] and st3 == 502 and 'every SCPI port is taken' in p3['error'], (p2, p3))
        st, p = X.stop_emulator(None, 'emu-w')
        st2, _ = X.stop_emulator(None, 'emu-w2')
        check('osc-5 DOOR stop via the worker: 200, the row says stopped, the worker lists none, a second stop is 404',
              st == 200 and st2 == 200 and X.endpoint(None, 'emu-w')['status'] == 'stopped' and SE._request('GET', url + '/emulators')['rows'] == []
              and X.stop_emulator(None, 'emu-w')[0] == 404)
        proc = SE._request('GET', url + '/system-info')['process']
        print('  measured: worker process rss %.1f MB, cpu %.2f s after the captures above (for COST.md)' % (proc['rss_mb'], proc['cpu_s']))
    finally:
        os.environ.pop(SE.KNOB, None)
        mod.stop_all()
        srv.shutdown()
        srv.server_close()
    # the tile, the binder, the compose file, pol dev
    from islemesh.islemesh_catalog import SEED_CATALOG, install_plan
    from islemesh.custom.islemesh_engines import _BINDERS
    tile = next((t for t in SEED_CATALOG if t['name'] == 'scope-engines'), None)
    step = (install_plan(tile)['steps'] or [''])[0] if tile else ''
    check('osc-5 TILE: scope-engines = mesh-app / engine / scope on :9880 from docker-compose.scope-engines.yml; the plan deploys it with --engine scope; a binder exists',
          tile and tile['provides_engine'] == 'scope' and tile['port'] == 9880 and '--engine scope' in step and '--port 9880' in step and 'scope' in _BINDERS, step)
    compose = open(os.path.join(os.path.dirname(_FW), 'docker-compose.scope-engines.yml')).read()
    check('osc-5 COMPOSE: the service scope-engines publishes 9880 and 5555-5559 from the image prf-scope-engines:trixie',
          'scope-engines:' in compose and '"9880:9880"' in compose and '"5555-5559:5555-5559"' in compose and 'prf-scope-engines:trixie' in compose)
    dev = open(os.path.join(os.path.dirname(os.path.dirname(_FW)), 'polari-cli', 'scripts', 'dev.sh')).read()
    check('osc-5 pol dev: scope-engines is a worker target that builds through prf-scope-engines/build.sh', 'scope-engines' in re.search(r'WORKERS="([^"]+)"', dev).group(1)
          and 'prf-scope-engines/build.sh' in dev and 'prf-scope-engines:trixie' in dev)
    build = open(os.path.join(_WORKER_DIR, 'build.sh')).read()
    check('osc-5 build.sh vendors exactly the five emulator files from modules/instruments/custom and records their sha256',
          all(f in build for f in ('scpi.py', 'lineage.py', 'sources.py', 'emulator.py', 'device_feed.py')) and 'SOURCES.sha256' in build)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
