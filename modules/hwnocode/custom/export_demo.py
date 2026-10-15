"""
@module hwnocode.custom.export_demo

THE DEMO BUNDLE (export form `demo-bundle`, slice ucd-app, UNO_CORE_DEMO_PLAN.md §5l): everything the Hardware App needs to
run the light demo from one folder, with or without Polari reachable:

    firmware.hex  polari-install.json  INSTALL.md   the install bundle, byte for byte (cmod.custom.export_cmake.install_files)
    polari-hw-bridge.jar                           the generated Java bridge for the `uno-light` bridge, built with Maven here;
                                                   when java/mvn are missing (or the build fails) BRIDGE-NOT-BUILT.txt says why
                                                   and the export still succeeds
    bridge.properties                              the bridge's settings: a serial-port placeholder, gRPC on, grpc.target =
                                                   <this server's host>:3002 (derived from the address the export was asked from)
    app-definition.json                            the SolutionDefinition rows `uno-light-app` and `uno-light`, as served
    README.md                                      what each file is and its sha256

The bridge project comes from hwnocode.custom.offline_project (the same generate_project the server runs, fed by the pinned
LightState contract), so it works from the command line with no server.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess

GRPC_PORT = 3002
JAR = 'polari-hw-bridge.jar'
SERIAL_PLACEHOLDER = '/dev/ttyACM0'
BRIDGE_SOLUTION = 'uno-light'
APP_SOLUTION = 'uno-light-app'


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def grpc_target(api_host=''):
    """<host>:3002 from the address this server was reached at (a URL, host:port or bare host) — never a literal; when nothing
    is known, localhost (the bridge's own default)."""
    h = (api_host or '').strip()
    h = re.sub(r'^[a-z]+://', '', h).split('/')[0]
    if h.startswith('['):                       # [v6]:port
        h = h.split(']')[0] + ']'
    else:
        h = h.split(':')[0]
    return '%s:%d' % (h or 'localhost', GRPC_PORT)


def build_jar(files, work):
    """Write the generated project (minus bridge.properties) under `work` and run `mvn package`. -> (jar bytes | None, why).
    Cached by the code fingerprint, so a second export does not rebuild."""
    for tool in ('java', 'mvn'):
        if not shutil.which(tool):
            return None, '%s is not installed on this host (the bridge is a Java program built with Maven)' % tool
    code = {p: t for p, t in files.items() if p != 'bridge.properties'}
    fp = hashlib.sha256(json.dumps(code, sort_keys=True).encode()).hexdigest()[:16]
    proj = os.path.join(work, 'build-%s' % fp)
    jar = os.path.join(proj, 'target', JAR)
    if not os.path.isfile(jar):
        shutil.rmtree(proj, ignore_errors=True)
        for path, text in code.items():
            os.makedirs(os.path.dirname(os.path.join(proj, path)) or proj, exist_ok=True)
            with open(os.path.join(proj, path), 'w') as f:
                f.write(text)
        try:
            m = subprocess.run(['mvn', '-q', '-o', 'package', '-DskipTests'], cwd=proj, capture_output=True, text=True, timeout=900)
            if m.returncode != 0:
                m = subprocess.run(['mvn', '-q', 'package', '-DskipTests'], cwd=proj, capture_output=True, text=True, timeout=1200)
        except (OSError, subprocess.TimeoutExpired) as e:
            return None, 'mvn package did not finish: %s' % e
        if m.returncode != 0 or not os.path.isfile(jar):
            return None, 'mvn package failed: %s' % (m.stdout + m.stderr)[-500:]
    with open(jar, 'rb') as f:
        return f.read(), ''


def _properties(text, target):
    head = ('# The bridge\'s settings. Set serial.device to the board\'s serial port (the Hardware App fills it in when it finds\n'
            '# the board). grpc.target is where Polari listens for the bridge.\n')
    text = re.sub(r'(?m)^grpc\.target=.*$', 'grpc.target=%s' % target, text)
    text = re.sub(r'(?m)^serial\.device=.*$', 'serial.device=%s' % SERIAL_PLACEHOLDER, text)
    return head + text


def app_definition_json(manager=None):
    """{'schema', 'solutions': [the uno-light-app and uno-light SolutionDefinition rows as served]} — from the server's rows when
    a manager has them, else the code-owned seed rows (the same ones the server seeds)."""
    from hwnocode.custom import seed_rows as SR
    seeded = {r['name']: r for r in SR.solution_definitions()}
    rows = []
    for name in (APP_SOLUTION, BRIDGE_SOLUTION):
        live = next((r for r in ((getattr(manager, 'objectTables', None) or {}).get('SolutionDefinition') or {}).values()
                     if getattr(r, 'name', '') == name), None)
        src = ({k: getattr(live, k, '') for k in ('name', 'function_name', 'target_runtime', 'definition', 'contract_json', 'category')}
               if live is not None else seeded[name])
        row = dict(src)
        for k in ('definition', 'contract_json'):
            try:
                row[k] = json.loads(row[k]) if isinstance(row[k], str) else row[k]
            except ValueError:
                pass
        rows.append(row)
    return {'schema': 'polari-app-definition/1', 'solutions': rows}


def _readme(solution, hex_sha, shas, bridge_note, target):
    names = [('firmware.hex', 'The firmware to put on the board.'),
             ('polari-install.json', 'The install notes the app reads: which board, the exact flashing command and the firmware\'s fingerprint.'),
             ('INSTALL.md', 'The same instructions for a person, if you would rather flash by hand.'),
             (JAR, 'The bridge: a small Java program that carries the light\'s state from the board up to Polari and commands back down.'),
             ('bridge.properties', 'The bridge\'s settings (the board\'s serial port, and %s as the place Polari listens).' % target),
             ('app-definition.json', 'The Hardware App\'s steps and the light demo\'s steps, as Polari holds them.'),
             ('usb-interfaces.json', 'The USB-serial chips this board design can have (the genuine bridge and known clones), their USB ids and '
                                     'whether each is confirmed by a document: the app\'s Detect step finds the board with these.')]
    lines = ['# %s: demo bundle' % solution, '',
             'Everything the Hardware App needs to run the light demo from this one folder. Open it in the Hardware App (it checks',
             'the firmware, finds the board, flashes it and starts the bridge), or follow INSTALL.md by hand.', '',
             '## The files', '']
    for f, what in names:
        lines.append('- `%s` (sha256 `%s`): %s' % (f, shas.get(f, 'not in this bundle'), what))
    lines += ['', '## Check the firmware first', '',
              'Run `sha256sum firmware.hex`. It must read `%s`. Never flash a file with a different fingerprint.' % hex_sha, '']
    if bridge_note:
        lines += ['## The bridge was not built', '', bridge_note, '']
    return '\n'.join(lines) + '\n'


def usb_interfaces_json(board, manager=None):
    """The board design's USB-interface variants for the app's Detect step: the UsbInterfaceDefinition rows allowed on `board`
    (live rows when a manager holds them, else the board module's seed) -> {"interfaces": [{name, title, ids[], verification,
    dtr_resets_mcu}]}. The physical board's actual variant is never asserted here — Detect reports which one it saw.
    `board` is the board's name or the export's board-facts dict (its `name`)."""
    if isinstance(board, dict):
        board = board.get('name') or board.get('board') or ''
    rows = []
    tables = (getattr(manager, 'objectTables', None) or {}) if manager is not None else {}
    live = list((tables.get('UsbInterfaceDefinition') or {}).values())
    if live:
        rows = [{k: getattr(r, k, '') for k in ('name', 'title', 'usb_ids_json', 'verification', 'dtr_resets_mcu', 'allowed_boards_json')}
                for r in live]
    else:
        from board.custom.usb_interfaces import usb_interfaces
        rows = usb_interfaces()
    out = []
    for r in rows:
        try:
            allowed = json.loads(r.get('allowed_boards_json') or '[]')
        except ValueError:
            allowed = []
        if allowed and board not in allowed:
            continue
        try:
            ids = [i['id'] if isinstance(i, dict) else str(i) for i in json.loads(r.get('usb_ids_json') or '[]')]
        except ValueError:
            ids = []
        out.append({'name': r.get('name', ''), 'title': r.get('title', ''), 'ids': ids,
                    'verification': r.get('verification', ''), 'dtr_resets_mcu': r.get('dtr_resets_mcu', '')})
    return {'schema': 'polari-usb-interfaces/1', 'board': board, 'interfaces': out}


def export_demo_bundle(path, name, solution, board, makefile_sha, proof, d, target, graph, manager=None, api_host='', work=None):
    """Write the demo bundle into `path` (+ tar.gz). -> the FirmwareExport row fields."""
    from cmod.custom import export_cmake as EX
    from hwnocode.custom import offline_project as OP
    out, hex_sha = EX.install_files(solution, board, makefile_sha, proof, d)
    tgt = grpc_target(api_host)
    rep = OP.light_project(grpc_target=tgt, serial_device=SERIAL_PLACEHOLDER)
    bridge_note = ''
    if not rep.get('ok'):
        bridge_note = 'The bridge project could not be generated: %s' % rep.get('error')
        props = _properties('source=serial\nserial.device=\ngrpc.enabled=true\ngrpc.target=\n', tgt)
    else:
        props = _properties(rep['files']['bridge.properties'], tgt)
        jar, why = build_jar(rep['files'], work or os.path.join(os.path.dirname(path), '.bridge-build'))
        if jar is None:
            bridge_note = why
        else:
            out[JAR] = jar
    out['bridge.properties'] = props.encode()
    if bridge_note:
        out['BRIDGE-NOT-BUILT.txt'] = ('The bridge program (%s) is not in this bundle.\nWhy: %s\n'
                                       'Build it where Java and Maven are installed with: pol firmware export %s --form demo-bundle\n'
                                       % (JAR, bridge_note, solution)).encode()
    out['app-definition.json'] = (json.dumps(app_definition_json(manager), indent=1, ensure_ascii=False) + '\n').encode()
    out['usb-interfaces.json'] = (json.dumps(usb_interfaces_json(board, manager), indent=1, ensure_ascii=False) + '\n').encode()
    out['README.md'] = _readme(solution, hex_sha, {f: _sha(b) for f, b in out.items()}, bridge_note, tgt).encode()
    files, tar_path, tar_sha = EX.pack(path, name, out)
    return {'name': name, 'solution': solution, 'graph': graph, 'board': board['name'], 'form': 'demo-bundle',
            'target': target, 'mode': 'online', 'path': path, 'tar_path': tar_path, 'tar_sha256': tar_sha,
            'files_json': json.dumps(files), 'makefile_sha256': hex_sha, 'cmake_sha256': '', 'parity': 'not-run',
            'verify_log': '', 'download_url': '/api/firmware/exports/%s/download' % name,
            'created_at': datetime.datetime.now().isoformat(timespec='seconds'), 'status': 'created', 'why': bridge_note,
            'notes': ('bridge jar built' if JAR in out else 'bridge NOT built: %s' % bridge_note) + ' · ' +
                     '%s · %s' % (proof.get('proof_status', ''), proof.get('advice', ''))}
