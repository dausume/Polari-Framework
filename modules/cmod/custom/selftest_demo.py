"""selftest_demo — ucd-app (UNO_CORE_DEMO_PLAN.md §5l): the `demo-bundle` export form and the upload door.
  * demo-bundle: firmware.hex + polari-install.json + INSTALL.md + bridge.properties (serial placeholder, gRPC on, grpc.target =
    <the asked-from host>:3002) + app-definition.json (uno-light-app + uno-light) + README with every file's sha; the bridge jar built
    (when java/mvn are here) or an honest BRIDGE-NOT-BUILT.txt (forced here by hiding the tools) — the export succeeds either way;
  * the same form through the REAL door on a real falcon.App (POST /api/firmware/solutions/uno-light/export), the row listed and the tar served;
  * POST /api/firmware/exports/upload: a good upload -> row + download (its own bytes), a wrong sha -> 422 and nothing stored,
    a bad form / missing file -> 400, the JSON+base64 spelling works.
Run by cmod_selftest.main() (demo_parts)."""
import atexit
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from types import SimpleNamespace


def _tmpdir(prefix):
    """A temp dir removed when the selftest process exits (66 leaked bundle dirs, 4.2 GB, once filled pol-core's disk)."""
    d = tempfile.mkdtemp(prefix=prefix)
    atexit.register(shutil.rmtree, d, True)
    return d


def demo_parts(check):
    return (lambda: _bundle(check), lambda: _no_jdk(check), lambda: _door(check), lambda: _upload(check), lambda: _no_engine(check))


def _make_rung(check):
    from cmod.custom import cmod_engines as CE
    where = CE.resolve('make')
    if where['how'] == 'refused':
        print('  [SKIP] demo-bundle needs the make rung — %s' % where['why'])
        return False
    return True


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _bundle(check):
    if not _make_rung(check):
        return
    from cmod.custom import export_cmake as EX, firmware_cli as CLI
    tmp = _tmpdir('polari-demo-selftest-')
    row = EX.export(CLI._solution('uno-light'), target='board', out_root=tmp, form='demo-bundle', api_host='https://node.invalid:8443/x')
    check('demo-bundle: FirmwareExport row records form=demo-bundle and the download door', row['form'] == 'demo-bundle'
          and row['download_url'] == '/api/firmware/exports/%s/download' % row['name'], row['form'])
    d = row['path']
    files = set(os.listdir(d))
    base = {'firmware.hex', 'polari-install.json', 'INSTALL.md', 'bridge.properties', 'app-definition.json', 'README.md'}
    check('demo-bundle: holds the install files, bridge.properties, app-definition.json and README (+ the jar or BRIDGE-NOT-BUILT.txt)',
          base <= files and ('polari-hw-bridge.jar' in files) != ('BRIDGE-NOT-BUILT.txt' in files), sorted(files))
    install = json.load(open(os.path.join(d, 'polari-install.json')))
    hexb = open(os.path.join(d, 'firmware.hex'), 'rb').read()
    check('demo-bundle: firmware.hex matches polari-install.json\'s hex_sha256 and the row\'s makefile sha (the gate)',
          _sha(hexb) == install['hex_sha256'] == row['makefile_sha256'])
    props = open(os.path.join(d, 'bridge.properties')).read()
    check('demo-bundle: bridge.properties = serial source + a serial-port placeholder + gRPC on + grpc.target host:3002 derived from the asked-from address',
          'source=serial' in props and 'serial.device=/dev/ttyACM0' in props and 'grpc.enabled=true' in props
          and 'grpc.target=node.invalid:3002' in props and 'twin-uart' not in props, props[:400])
    usb = json.load(open(os.path.join(d, 'usb-interfaces.json')))
    by = {i['name']: i for i in usb.get('interfaces', [])}
    check('demo-bundle: usb-interfaces.json carries the board design\'s USB-serial variants from the model (16U2 verified with its three ids, '
          'CH340 unverified) — the app\'s Detect matches these, never a hard-coded list',
          usb.get('board') == 'arduino-uno-r3' and by.get('atmega16u2-bridge', {}).get('verification') == 'verified'
          and '2341:0043' in by.get('atmega16u2-bridge', {}).get('ids', []) and by.get('ch340-bridge', {}).get('verification') == 'unverified',
          usb)
    app = json.load(open(os.path.join(d, 'app-definition.json')))
    names = {s['name']: s for s in app['solutions']}
    check('demo-bundle: app-definition.json = the uno-light-app (hardware-app) and uno-light (cross-domain) rows, definitions parsed',
          set(names) == {'uno-light-app', 'uno-light'} and names['uno-light-app']['category'] == 'hardware-app'
          and names['uno-light']['category'] == 'cross-domain' and isinstance(names['uno-light-app']['definition'], dict))
    readme = open(os.path.join(d, 'README.md')).read()
    check('demo-bundle: the README names every file with its real sha256',
          all(('`%s` (sha256 `%s`)' % (f, _sha(open(os.path.join(d, f), 'rb').read()))) in readme
              for f in files - {'README.md'}), readme[:300])
    if 'polari-hw-bridge.jar' in files:
        jar = open(os.path.join(d, 'polari-hw-bridge.jar'), 'rb').read()
        check('demo-bundle: the bridge jar was built (a real zip, over 100 kB)', jar[:2] == b'PK' and len(jar) > 100000, len(jar))
    else:
        why = open(os.path.join(d, 'BRIDGE-NOT-BUILT.txt')).read()
        print('  [note] bridge not built on this host: %s' % why.splitlines()[1][:160])
        check('demo-bundle: no jar -> BRIDGE-NOT-BUILT.txt says why, and the export still succeeded', 'Why:' in why and row['status'] == 'created')
    with tarfile.open(row['tar_path']) as t:
        inside = {m.name.split('/', 1)[1] for m in t.getmembers() if '/' in m.name}
    check('demo-bundle: the tar.gz holds the same files', inside == files, sorted(inside ^ files))


def _no_jdk(check):
    if not _make_rung(check):
        return
    from cmod.custom import export_cmake as EX, firmware_cli as CLI
    from hwnocode.custom import export_demo as DEMO
    real = DEMO.shutil.which
    DEMO.shutil.which = lambda tool, *a, **k: None if tool in ('java', 'mvn') else real(tool, *a, **k)
    try:
        tmp = _tmpdir('polari-demo-nojdk-')
        row = EX.export(CLI._solution('uno-light'), target='board', out_root=tmp, form='demo-bundle')
    finally:
        DEMO.shutil.which = real
    files = set(os.listdir(row['path']))
    note = open(os.path.join(row['path'], 'BRIDGE-NOT-BUILT.txt')).read() if 'BRIDGE-NOT-BUILT.txt' in files else ''
    check('demo-bundle with java/mvn hidden: still succeeds, no jar, BRIDGE-NOT-BUILT.txt names the missing tool, README says so',
          row['status'] == 'created' and 'polari-hw-bridge.jar' not in files and 'java is not installed' in note
          and 'The bridge was not built' in open(os.path.join(row['path'], 'README.md')).read(), (sorted(files), note[:120]))
    check('demo-bundle: with no server address known the target falls back to localhost:3002',
          'grpc.target=localhost:3002' in open(os.path.join(row['path'], 'bridge.properties')).read())
    check('demo-bundle: grpc_target() never invents a host (url, host:port, bare host, empty)',
          [DEMO.grpc_target(x) for x in ('https://a.invalid:8443/p', 'b.invalid:80', 'c.invalid', '')]
          == ['a.invalid:3002', 'b.invalid:3002', 'c.invalid:3002', 'localhost:3002'])


def _client(check):
    import falcon
    from falcon import testing
    from cmod.cmod_firmware_api import FirmwareAPI
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from board.board_seed import BOARD_SEED_PAIRS
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None, saveObjToDB=lambda o: None)
    for _mid, pairs in (('board', BOARD_SEED_PAIRS), ('cmod', CMOD_SEED_PAIRS)):
        for name, cls, seed_rows in pairs:
            for row in seed_rows:
                o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    FirmwareAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)   # every route on ONE app: a conflict raises here
    return testing.TestClient(app), tables


def _multipart(fields, filename, data):
    b = 'XUPLOADBOUNDARYX'
    parts = []
    for k, v in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n'
                  % (b, filename)).encode() + data + b'\r\n')
    parts.append(('--%s--\r\n' % b).encode())
    return {'Content-Type': 'multipart/form-data; boundary=%s' % b}, b''.join(parts)


def _door(check):
    if not _make_rung(check):
        return
    os.environ['POLARI_EXP_HOME'] = _tmpdir('polari-demo-door-')
    c, tables = _client(check)
    r = c.simulate_post('/api/firmware/solutions/uno-light/export', json={'form': 'demo-bundle', 'target': 'board'},
                        headers={'Host': 'node.invalid:8443'})
    ex = (r.json or {}).get('export') or {}
    check('POST /api/firmware/solutions/uno-light/export {form: demo-bundle} answers ok with a demo-bundle row', r.status_code == 200
          and r.json.get('ok') and ex.get('form') == 'demo-bundle', r.text[:300])
    if not ex:
        return
    props = open(os.path.join(ex['path'], 'bridge.properties')).read()
    check('…grpc.target in the bundle comes from the Host the door was reached at (node.invalid:3002)', 'grpc.target=node.invalid:3002' in props, props[:300])
    dl = c.simulate_get(ex['download_url'])
    check('…GET download serves the tar.gz (gzip magic, filename .tar.gz)', dl.status_code == 200 and dl.content[:2] == b'\x1f\x8b'
          and dl.headers.get('content-disposition', '').endswith('.tar.gz"'), dl.headers)


def _upload(check):
    os.environ['POLARI_EXP_HOME'] = _tmpdir('polari-upload-')
    c, tables = _client(check)
    data = b'!<arch>\ndebian-binary   fake deb bytes\n' * 50
    sha = _sha(data)
    h, body = _multipart({'solution': 'uno-light', 'form': 'bridge-app-deb', 'sha256': sha}, 'polari-app-uno-core-demo_1.0_amd64.deb', data)
    r = c.simulate_post('/api/firmware/exports/upload', headers=h, body=body)
    ex = (r.json or {}).get('export') or {}
    check('upload: a good multipart upload answers {ok, export:{name, form, download_url, tar_sha256}}', r.status_code == 200 and r.json.get('ok')
          and {'name', 'form', 'download_url', 'tar_sha256'} <= set(ex) and ex['form'] == 'bridge-app-deb' and ex['tar_sha256'] == sha, r.text[:300])
    row = next((x for x in tables.get('FirmwareExport', {}).values() if getattr(x, 'name', '') == ex.get('name')), None)
    check('upload: a FirmwareExport row exists (solution uno-light, form bridge-app-deb, tar_path = the stored file, sha verified)',
          row is not None and row.solution == 'uno-light' and row.form == 'bridge-app-deb' and os.path.isfile(row.tar_path)
          and row.tar_path.endswith('.deb') and row.tar_sha256 == sha and row.download_url == ex['download_url'])
    dl = c.simulate_get(ex['download_url'])
    check('upload: the download door serves the uploaded bytes, as a .deb', dl.status_code == 200 and dl.content == data
          and dl.headers.get('content-type') == 'application/vnd.debian.binary-package'
          and '.deb' in dl.headers.get('content-disposition', ''), dl.headers)
    lst = c.simulate_get('/api/firmware/exports')
    check('upload: GET /api/firmware/exports lists it', any(x['name'] == ex['name'] and x['form'] == 'bridge-app-deb' for x in lst.json['rows']))
    before = {r.name for r in tables.get('FirmwareExport', {}).values()}
    h2, body2 = _multipart({'solution': 'uno-light', 'form': 'shell-core-deb', 'sha256': '0' * 64}, 'core.deb', data)
    r2 = c.simulate_post('/api/firmware/exports/upload', headers=h2, body=body2)
    left = [f for _d, _s, fs in os.walk(os.environ['POLARI_EXP_HOME']) for f in fs if f == 'core.deb' or f.startswith('.upload')]
    check('upload: a sha256 that does not match is refused 422, no row, nothing left on disk', r2.status_code == 422 and not r2.json['ok']
          and {r.name for r in tables.get('FirmwareExport', {}).values()} == before and not left, (r2.status_code, r2.text[:200], left))
    h3, body3 = _multipart({'solution': 'uno-light', 'form': 'not-a-form', 'sha256': sha}, 'x.deb', data)
    r3 = c.simulate_post('/api/firmware/exports/upload', headers=h3, body=body3)
    check('upload: an unknown form is refused 400, naming the two forms', r3.status_code == 400 and 'bridge-app-deb' in r3.text and 'shell-core-deb' in r3.text, r3.text[:200])
    h4, body4 = _multipart({'solution': 'uno-light', 'form': 'shell-core-deb', 'sha256': sha}, 'x.deb', b'')
    body4 = body4.replace(b'filename="x.deb"', b'filename="x.deb"')
    nofile = b'--XUPLOADBOUNDARYX\r\nContent-Disposition: form-data; name="solution"\r\n\r\nuno-light\r\n--XUPLOADBOUNDARYX--\r\n'
    r4 = c.simulate_post('/api/firmware/exports/upload', headers=h4, body=nofile)
    check('upload: a body with no file part is refused 400', r4.status_code == 400, r4.text[:200])
    import base64
    d5 = b'second file ' * 20
    r5 = c.simulate_post('/api/firmware/exports/upload', json={'solution': 'uno-light', 'form': 'shell-core-deb', 'filename': '../../evil name.deb',
                                                                'sha256': _sha(d5), 'file': base64.b64encode(d5).decode()})
    e5 = (r5.json or {}).get('export') or {}
    row5 = next((x for x in tables.get('FirmwareExport', {}).values() if getattr(x, 'name', '') == e5.get('name')), None)
    check('upload: the JSON+base64 spelling works, and a path in the filename is reduced to a plain name inside the exports root',
          r5.status_code == 200 and row5 is not None and os.path.basename(row5.tar_path) == 'evil_name.deb'
          and os.path.realpath(row5.tar_path).startswith(os.path.realpath(os.environ['POLARI_EXP_HOME'])), r5.text[:200])


def _no_engine(check):
    """2026-10-19: a compiled export form on a server with no reachable compiler engine answered a bare 500; it is a named 422."""
    from cmod.custom import export_cmake as EX
    from board.custom.engine_run import EngineRefused
    os.environ['POLARI_EXP_HOME'] = _tmpdir('polari-noengine-')
    c, _tables = _client(check)
    real = EX.export

    def refuse(*a, **k):
        raise EngineRefused('avr-gcc resolves to refused () and that worker does not list make')
    EX.export = refuse
    try:
        r = c.simulate_post('/api/firmware/solutions/uno-light/export', json={'form': 'install-bundle', 'target': 'board'})
    finally:
        EX.export = real
    check('export door: no reachable compiler engine -> 422 that names the engine and points at source-dir (never a bare 500)',
          r.status_code == 422 and not r.json.get('ok') and 'no compiler engine is reachable' in r.json.get('refused', '')
          and 'source-dir' in r.json.get('refused', ''), (r.status_code, r.text[:300]))
