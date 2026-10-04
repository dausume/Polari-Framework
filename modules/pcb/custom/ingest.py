"""
@module pcb.custom.ingest

`pol pcb ingest <path>` (pcb-0): a KiCad project → the pcb rows (pcb.custom.kicad_read, no engine) → with the engine
(pcb.custom.pcb_engines, the ladder) the checks and the exports → a RECORD (custom/records/<board>.json) + the exported files in
the artifact dir. The rows of the checks (DrcResult) and the files (FabricationExport) are built FROM the record, so a server
seeds them without running KiCad (the record is committed for the reference board) and a re-run proves byte-stability by sha.

Engine runs (each one kicad-cli verb through the ladder, the clock frozen at SOURCE_DATE, the job dir fixed):
  sch erc --format json --severity-all                       → DrcResult kind erc (a clean ERC = one severity-none row)
  pcb drc --format json --severity-all --schematic-parity    → kind drc / unconnected / parity — the board's OWN rules
  pcb drc … with <board>.kicad_dru written from the FabRules → kind drc, checker "kicad-cli + dkred rules" (5 mil clearance …)
  pcb export gerbers --layers <fab layers>                   → set protel (KiCad's default Protel extensions .gtl/.gbl/.gts/…)
  pcb export gerbers --no-protel-ext --layers …              → set kicad-gbr (every layer .gbr)
  pcb export drill --format excellon --generate-map --map-format gerberx2   → set drill (.drl + the drill map)
  pcb export pos --format csv --units mm --side both         → set assembly (+ sch export bom, sch export netlist)
  pcb export svg --mode-multi --layers …                     → set layers (one SVG per layer: /display/board-layout)
  sch export svg                                             → set layers (the schematic as KiCad draws it: /display/board-schematic)
  pcb export step --no-components                            → set 3d (board body + pads; no 3D models — kicad-packages3d is not in
                                                               the image, plan §4)
Each file → its sha256 + bytes + the fab's naming verdict (pcb.custom.fab_rules.naming).
"""
import datetime
import hashlib
import json
import os

from pcb.custom import fab_rules as FR
from pcb.custom import kicad_read as K
from pcb.custom import pcb_engines as E

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, 'records')
ARTIFACTS = os.path.join(HERE, 'artifacts')
FAB_LAYERS = ['F.Cu', 'B.Cu', 'F.Paste', 'B.Paste', 'F.Silkscreen', 'B.Silkscreen', 'F.Mask', 'B.Mask', 'Edge.Cuts']
#: the DRC violation types a .kicad_dru written by fab_rules.dru() can raise
DRU_TYPES = ('clearance', 'track_width', 'hole_size', 'via_diameter', 'annular_width', 'drill_out_of_range', 'via_diameter_out_of_range')
SVG_LAYERS = ['F.Cu', 'B.Cu', 'F.Silkscreen', 'B.Silkscreen', 'F.Mask', 'B.Mask', 'Edge.Cuts']
#: KiCad's plot file suffix → the board layer (Protel + --no-protel-ext + svg names: <board>-<suffix>.<ext>)
SUFFIX_LAYER = {'F_Cu': 'F.Cu', 'top_cu': 'F.Cu', 'B_Cu': 'B.Cu', 'bottom_cu': 'B.Cu', 'F_Paste': 'F.Paste', 'B_Paste': 'B.Paste',
                'F_Silkscreen': 'F.Silkscreen', 'B_Silkscreen': 'B.Silkscreen', 'F_Mask': 'F.Mask', 'B_Mask': 'B.Mask', 'Edge_Cuts': 'Edge.Cuts'}


def home():
    from polariApiServer.module_home import module_home
    return module_home('pcb', os.environ.get('POLARI_PCB_HOME'))


def read_source(path):
    """The ingested project's SOURCE.json, if there is one — pcb-0's provenance convention stores it beside the
    project (e.g. custom/upstream/kicad-demos-9.0.2/SOURCE.json, one level above its ecc83/ project directory), not
    inside it, so this walks up from `path` a few levels looking for one. {} when none is found — never invented."""
    here = path if os.path.isdir(path) else os.path.dirname(path)
    for _ in range(4):
        cand = os.path.join(here, 'SOURCE.json')
        if os.path.isfile(cand):
            try:
                return json.load(open(cand))
            except ValueError:
                return {}
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return {}


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def layer_of(board, filename, kind):
    base = os.path.basename(filename)
    if kind in ('drill', 'drill-map'):
        return 'drill-map' if '-drl_map' in base or '_map' in base else 'drill'
    stem = base.rsplit('.', 1)[0]
    suffix = stem[len(board) + 1:] if stem.startswith(board + '-') else stem
    return SUFFIX_LAYER.get(suffix, '')


def _kind(export_set, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if export_set in ('protel', 'kicad-gbr'):
        return 'job' if ext == 'gbrjob' else 'gerber'
    if export_set == 'drill':
        return 'drill-map' if '_map' in filename else 'drill'
    if export_set == 'assembly':
        return {'csv': 'pos' if 'pos' in filename else 'bom', 'net': 'netlist'}.get(ext, ext)
    if export_set == 'layers':
        return 'svg-schematic' if filename.startswith('schematic/') else 'svg-layer'
    return 'step' if ext == 'step' else ext


def _checks(board, files):
    pcb, sch = '%s.kicad_pcb' % board, '%s.kicad_sch' % board
    runs = []
    if sch in files:
        runs.append(('erc', ['sch', 'erc', '--format', 'json', '--severity-all', '-o', 'erc.json', sch], files, 'erc.json'))
    if pcb in files:
        runs.append(('drc', ['pcb', 'drc', '--format', 'json', '--severity-all', '--schematic-parity', '-o', 'drc.json', pcb], files, 'drc.json'))
        with_dru = dict(files)
        with_dru['%s.kicad_dru' % board] = FR.dru()
        runs.append(('drc-dkred', ['pcb', 'drc', '--format', 'json', '--severity-all', '-o', 'drc.json', pcb], with_dru, 'drc.json'))
    return runs


def _exports(board, files):
    pcb, sch = '%s.kicad_pcb' % board, '%s.kicad_sch' % board
    out = []
    if pcb in files:
        out += [('protel', ['pcb', 'export', 'gerbers', '--layers', ','.join(FAB_LAYERS), '-o', 'out/', pcb]),
                ('kicad-gbr', ['pcb', 'export', 'gerbers', '--no-protel-ext', '--layers', ','.join(FAB_LAYERS), '-o', 'out/', pcb]),
                ('drill', ['pcb', 'export', 'drill', '--format', 'excellon', '--generate-map', '--map-format', 'gerberx2', '-o', 'out/', pcb]),
                ('assembly', ['pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', 'out/%s-pos.csv' % board, pcb]),
                ('layers', ['pcb', 'export', 'svg', '--mode-multi', '--layers', ','.join(SVG_LAYERS), '--fit-page-to-board', '--exclude-drawing-sheet',
                            '-o', 'out/', pcb]),
                ('3d', ['pcb', 'export', 'step', '--no-components', '-o', 'out/%s.step' % board, pcb])]
    if sch in files:
        out += [('assembly', ['sch', 'export', 'bom', '-o', 'out/%s-bom.csv' % board, sch]),
                ('assembly', ['sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', 'out/%s.net' % board, sch]),
                ('layers', ['sch', 'export', 'svg', '-o', 'out/schematic/', sch])]
    return out


def run_engines(board, files, source_date=E.SOURCE_DATE):
    """Every check + export through the ladder → the record dict (no rows, no writing). EngineRefused when no engine."""
    where = E.resolve()
    if where['how'] == 'refused':
        raise E.EngineRefused(where['why'])
    rec = {'board': board, 'engine': {'version': E.version(), 'how': where['how'], 'where': where['where'], 'libraries': E.libraries(),
                                      'licence': E.LICENCE},
           'source_date': source_date, 'job_dir': E.JOB_DIR, 'inputs_sha256': {n: sha(t) for n, t in sorted(files.items())},
           'checks': {}, 'exports': [], 'costs': {}, 'blobs': {}}
    enc = {n: t.encode() for n, t in files.items()}
    for key, args, fs, report in _checks(board, files):
        res = E.run(args, {n: (t.encode() if isinstance(t, str) else t) for n, t in fs.items()}, source_date=source_date)
        data = res['files'].get(report, b'')
        try:
            parsed = json.loads(data) if data else {}
        except ValueError:
            parsed = {}
        rec['checks'][key] = {'argv': ' '.join(['kicad-cli'] + args), 'returncode': res['returncode'], 'report_sha256': sha(data) if data else '',
                              'report': parsed, 'stdout_tail': res['stdout'][-1500:], 'stderr_tail': res['stderr'][-600:],
                              'dru_sha256': sha(fs['%s.kicad_dru' % board]) if '%s.kicad_dru' % board in fs else ''}
        rec['costs'][key] = res['cost']
        rec['byte_stable'] = res.get('byte_stable', False)
    for export_set, args in _exports(board, files):
        res = E.run(args, enc, source_date=source_date)
        verb = ' '.join(args[:3])
        rec['costs']['%s %s' % (export_set, verb)] = res['cost']
        if res['returncode'] != 0:
            rec['exports'].append({'export_set': export_set, 'argv': ' '.join(['kicad-cli'] + args), 'error': (res['stderr'] or res['stdout'])[-400:]})
            continue
        for rel, data in sorted(res['files'].items()):
            name = rel[len('out/'):] if rel.startswith('out/') else rel
            kind = _kind(export_set, name)
            layer = layer_of(board, name, kind)
            acc, fab_name, note = FR.naming(name, layer) if kind in ('gerber', 'drill', 'drill-map') else ('n/a', '', '')
            path = '%s/%s' % (export_set, name)
            rec['exports'].append({'export_set': export_set, 'kind': kind, 'layer': layer, 'filename': os.path.basename(name), 'path': path,
                                   'extension': '.' + name.rsplit('.', 1)[-1], 'sha256': sha(data), 'bytes': len(data), 'accepted': acc,
                                   'fab_name': fab_name, 'naming_note': note, 'argv': ' '.join(['kicad-cli'] + args)})
            rec['blobs'][path] = data
    rec['netlist_vs_board'] = _netlist_vs_board(board, rec, files)
    return rec


def _netlist_vs_board(board, rec, files):
    """kicad-cli's schematic netlist nets vs the board's nets (both from KiCad, read by us): equal names = a faithful round trip."""
    net = rec['blobs'].get('assembly/%s.net' % board)
    if not net or '%s.kicad_pcb' % board not in files:
        return {}
    from pcb.custom import sexpr as S
    t = S.parse(net.decode())
    sch_nets = sorted(S.value(n, 'name') for n in S.find(S.find(t, 'nets')[0], 'net')) if S.find(t, 'nets') else []
    pcb_nets = sorted(n['net'] for n in K.read_project(files, board).get('BoardNet', []))
    return {'schematic_nets': len(sch_nets), 'board_nets': len(pcb_nets), 'only_schematic': sorted(set(sch_nets) - set(pcb_nets)),
            'only_board': sorted(set(pcb_nets) - set(sch_nets)), 'equal': sch_nets == pcb_nets}


def write_record(rec, artifacts_dir, record_path):
    """The blobs → the artifact dir (by path); the record (without blobs) → JSON. Returns the record path."""
    for path, data in rec['blobs'].items():
        fp = os.path.join(artifacts_dir, path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'wb').write(data)
    body = {k: v for k, v in rec.items() if k != 'blobs'}
    os.makedirs(os.path.dirname(record_path), exist_ok=True)
    json.dump(body, open(record_path, 'w'), indent=1, sort_keys=True)
    open(record_path, 'a').write('\n')
    return record_path


def load_record(board, records_dir=RECORDS):
    p = os.path.join(records_dir, '%s.json' % board)
    return json.load(open(p)) if os.path.isfile(p) else None


# ---------------------------------------------------------------- rows FROM a record
def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def drc_rows(board, rec):
    """DrcResult rows from the record's kicad-cli reports (ERC, DRC, parity, unconnected, DRC with the DKRed .kicad_dru)."""
    out = []
    ver = rec.get('engine', {}).get('version', '')
    for key, chk in sorted((rec.get('checks') or {}).items()):
        rep = chk.get('report') or {}
        checker = 'kicad-cli %s%s' % (rep.get('kicad_version', ''), ' + dkred rules (.kicad_dru from the FabRule rows)' if key == 'drc-dkred' else '')
        items = []
        if key == 'erc':
            for sheet in rep.get('sheets') or []:
                items += [('erc', v) for v in sheet.get('violations') or []]
        elif key == 'drc-dkred':   # only what the .kicad_dru's constraints raise — the board's own findings are the drc rows already
            items += [('fab-rule', v) for v in rep.get('violations') or [] if v.get('type') in DRU_TYPES]
        else:
            items += [('drc', v) for v in rep.get('violations') or []]
            if key == 'drc':
                items += [('unconnected', v) for v in rep.get('unconnected_items') or []]
                items += [('parity', v) for v in rep.get('schematic_parity') or []]
        base = {'board': board, 'checker': checker, 'report_sha256': chk.get('report_sha256', ''), 'engine_version': ver, 'argv': chk.get('argv', ''),
                'source_date': rec.get('source_date', ''), 'at': rec.get('source_date', '')}
        if not items:
            extra = ''
            if key == 'drc-dkred':
                extra = (' of the DKRed constraints (clearance %s, track width, hole size, via diameter — the .kicad_dru sha256 %s…); the run\'s other '
                         '%d finding(s) are the board\'s own rules, already the drc rows' % ('5 mil', chk.get('dru_sha256', '')[:12],
                                                                                           len(rep.get('violations') or [])))
            out.append(dict(base, name='%s:%s:clean' % (board, key), kind='erc' if key == 'erc' else ('fab-rule' if key == 'drc-dkred' else 'drc'),
                            severity='none', rule='—', description='%s: 0 violations%s (kicad-cli exit %s)' % (key, extra, chk.get('returncode')),
                            items_json='[]', x_mm=0.0, y_mm=0.0))
        for i, (kind, v) in enumerate(items):
            pos = ((v.get('items') or [{}])[0].get('pos') or {})
            out.append(dict(base, name='%s:%s:%d' % (board, key, i), kind=kind, severity=v.get('severity', ''), rule=v.get('type', ''),
                            description=v.get('description', ''), items_json=json.dumps([{'description': it.get('description', ''), 'pos': it.get('pos')}
                                                                                         for it in v.get('items') or []]),
                            x_mm=float(pos.get('x') or 0), y_mm=float(pos.get('y') or 0)))
    return out


def artifact_url(board, path):
    """Relative to the API root (`/api/pcb/artifacts/<board>/<path>`) by default — the frontend fetches it through
    the same API base it already uses, so a server never needs POLARI_PUBLIC_BASE_URL set just to make artifact
    links work (staging didn't set it; every row stored artifact_url='', which hid every drawing on
    /display/board-layout and /display/board-schematic). When POLARI_PUBLIC_BASE_URL IS set to an absolute http(s)
    URL (a public domain/CDN serving the same artifact tree), it is an optional ABSOLUTE prefix instead."""
    rel = '/api/pcb/artifacts/%s/%s' % (board, path)
    base = os.environ.get('POLARI_PUBLIC_BASE_URL', '').rstrip('/')
    return '%s%s' % (base, rel) if base.startswith('http') else rel


def export_rows(board, rec, board_sha=''):
    out = []
    for e in rec.get('exports') or []:
        if e.get('error'):
            out.append({'name': '%s:%s:error' % (board, e['export_set']), 'board': board, 'export_set': e['export_set'], 'kind': 'error', 'layer': '',
                        'filename': '', 'extension': '', 'sha256': '', 'bytes': 0, 'board_sha256': board_sha, 'fab_rule_set': FR.FAB, 'accepted': 'n/a',
                        'fab_name': '', 'naming_note': 'the export FAILED: %s' % e['error'][:300], 'artifact_path': '', 'artifact_url': '',
                        'engine_version': rec.get('engine', {}).get('version', ''), 'argv': e['argv'], 'source_date': rec.get('source_date', ''),
                        'at': rec.get('source_date', '')})
            continue
        out.append({'name': '%s:%s:%s' % (board, e['export_set'], e['path'].split('/', 1)[1]), 'board': board, 'export_set': e['export_set'],
                    'kind': e['kind'], 'layer': e['layer'], 'filename': e['filename'], 'extension': e['extension'], 'sha256': e['sha256'],
                    'bytes': e['bytes'], 'board_sha256': board_sha, 'fab_rule_set': FR.FAB if e['accepted'] != 'n/a' else '', 'accepted': e['accepted'],
                    'fab_name': e['fab_name'], 'naming_note': e['naming_note'], 'artifact_path': '%s/%s' % (board, e['path']),
                    'artifact_url': artifact_url(board, e['path']), 'engine_version': rec.get('engine', {}).get('version', ''), 'argv': e['argv'],
                    'source_date': rec.get('source_date', ''), 'at': rec.get('source_date', '')})
    return out


def ingest(path, board=None, engines=True, out_dir=None, source_date=E.SOURCE_DATE):
    """The whole ingest: rows (always) + the engine record (engines=True; a refusal is returned, never raised) + files written
    under out_dir (default POLARI_PCB_HOME/<board>/). → {'rows', 'record', 'refused', 'record_path'}"""
    files = K.read_dir(path) if os.path.isdir(path) else {os.path.basename(path): open(path).read()}
    rows = K.read_project(files, board, source=read_source(path))
    board = rows['board']
    pcb_rows = rows.get('PcbBoard') or [{}]
    rows['FabRuleSet'], rows['FabRule'] = FR.rule_set_rows(), FR.rule_rows()
    if rows.get('PcbBoard'):
        pcb_rows[0]['fab_rule_set'] = FR.FAB
        rows['DrcResult'] = FR.check_board(pcb_rows[0], files['%s.kicad_pcb' % board])
    res = {'rows': rows, 'record': None, 'refused': '', 'record_path': ''}
    if not engines:
        return res
    try:
        rec = run_engines(board, files, source_date)
    except E.EngineRefused as e:
        res['refused'] = str(e)
        return res
    d = out_dir or os.path.join(home(), board)
    res['record_path'] = write_record(rec, os.path.join(d, 'artifacts', board), os.path.join(d, 'records', '%s.json' % board))
    res['record'] = rec
    rows['DrcResult'] = rows.get('DrcResult', []) + drc_rows(board, rec)
    rows['FabricationExport'] = export_rows(board, rec, pcb_rows[0].get('sha256', ''))
    return res
