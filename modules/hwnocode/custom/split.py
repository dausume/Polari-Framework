"""
@module hwnocode.custom.split

`hn-split` — THE COMPILER that partitions a HardwareSolution (HARDWARE_NOCODE_PLAN.md §1d, §4 h; a GraphCompilerDefinition row in
polariNoCode.graph_compilers): the placement rule first (refusals stop it, naming the node or the edge), the firmware_runtime knob
(hn-0: bare-c only), then

  board half    the referenced CGraph through `cmod-glue` — UNCHANGED output (the same files, the same files_sha256 as cmod-1's
                committed record, so the .hex stays byte-identical to the shipped sim-rig firmware)
  backend half  the states placed `backend` as their own definition (`<solution>.backend`), which the EventTrigger runs per frame
  browser half  the configured DisplayDefinition rows (seeded; nothing compiled)

The split's record (custom/splits/<solution>.json) is what `pol hwnocode render | build` and the probe write, and what the seed
projects into the HardwareSolution row — nothing is rendered or built at boot.
"""
import datetime
import hashlib
import json
import os

from hwnocode.custom import knobs as K
from hwnocode.custom import placement as PL

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, 'splits')
COMPILER = 'hwnocode.custom.split 1'


class SplitRefused(ValueError):
    pass


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def default_work(solution):
    from polariApiServer.module_home import module_home
    return os.path.join(module_home('hwnocode', os.environ.get('POLARI_HWNOCODE_HOME')), solution)


# ------------------------------------------------------------------ the rows a split reads (a running server's, else the seeds)
def _row_dict(r):
    import inspect
    return {k: getattr(r, k, '') for k in inspect.signature(type(r).__init__).parameters if k not in ('self', 'manager')}


def solution_rows(name, manager=None):
    """{'solution': HardwareSolution dict, 'definition': the canvas definition dict, 'cgraph': cmod rows, 'board': BoardDefinition
    dict} — live rows when a manager holds them, else the code-owned seeds."""
    from hwnocode.custom import seed_rows as SR
    t = (getattr(manager, 'objectTables', None) or {}) if manager is not None else {}
    hs = next((_row_dict(r) for r in (t.get('HardwareSolution') or {}).values() if r.name == name), None)
    if hs is None:
        hs = next((dict(r) for r in SR.SOLUTIONS if r['name'] == name), None)
    if hs is None:
        raise SplitRefused('no HardwareSolution %r (seeded: %s)' % (name, ', '.join(r['name'] for r in SR.SOLUTIONS)))
    sd = next((r for r in (t.get('SolutionDefinition') or {}).values() if getattr(r, 'name', '') == hs['solution']), None)
    if sd is not None:
        raw = getattr(sd, 'definition', '{}')
        definition = raw if isinstance(raw, dict) else json.loads(raw or '{}')
    else:
        definition = SR.definition_of(hs['solution'])
    if not definition or not definition.get('stateInstances'):
        raise SplitRefused('%s: SolutionDefinition %r has no states' % (name, hs['solution']))
    from cmod.custom import glue as GL
    cg = GL.graph_rows(hs['cgraph'], manager)
    board = next((_row_dict(r) for r in (t.get('BoardDefinition') or {}).values() if r.name == hs['board_definition']), None)
    if board is None:
        from board.board_seed import SEED_BOARD_DEFINITIONS
        board = next((dict(b) for b in SEED_BOARD_DEFINITIONS if b['name'] == hs['board_definition']), {'name': hs['board_definition']})
    return {'solution': hs, 'definition': definition, 'cgraph': cg, 'board': board}


def place_solution(name, manager=None, parts=None):
    from hwnocode.custom.solutions import TRIGGER
    p = parts or solution_rows(name, manager)
    hs = p['solution']
    displays = [d.strip() for d in str(hs.get('displays') or '').split(',') if d.strip()]
    rep = PL.place(p['definition'], p['cgraph'], hs.get('board_instance', ''), displays, manager, trigger=TRIGGER)
    ok, why = K.check_runtime(hs.get('firmware_runtime'), p['board'])
    rep['runtime'] = {'value': hs.get('firmware_runtime') or 'bare-c', 'ok': ok, 'why': why}
    return rep


# ------------------------------------------------------------------ the compiler (GraphCompilerDefinition `hn-split`)
def compile_parts(p):
    hs = p['solution']
    ok, why = K.check_runtime(hs.get('firmware_runtime'), p['board'])
    if not ok:
        raise SplitRefused(why)
    rep = place_solution(hs['name'], parts=p)
    try:
        PL.check(rep)
    except PL.PlacementRefused as e:
        raise SplitRefused(str(e))
    subs = [s for s in p['definition']['stateInstances'] if PL.state_class(s) == 'HardwareSubgraph']
    runs = [s for s in p['definition']['stateInstances'] if PL.state_class(s) == 'FirmwareRunState']
    loose = [s['stateName'] for s in p['definition']['stateInstances'] if PL.state_class(s) == 'CAtom']
    if loose:
        raise SplitRefused('c-atom node(s) %s sit loose on the solution canvas: in hn-0 a c-atom renders only inside a '
                           'HardwareSubgraph (add it to the CGraph rows of %s)' % (', '.join(loose), hs['cgraph']))
    if not (runs and not subs):
        # the OLDER shape (a HardwareSubgraph embedded directly on this canvas) still requires exactly one, matching
        # the solution's own cgraph — unchanged check, for any HardwareSolution that is NOT a fs-1 Cross-Domain canvas.
        if len(subs) != 1 or (subs[0].get('boundObjectFieldValues') or {}).get('cgraph') != hs['cgraph']:
            raise SplitRefused('hn-0 renders ONE HardwareSubgraph whose cgraph is the solution\'s (%s); the canvas has %s'
                               % (hs['cgraph'], ', '.join('%s → %s' % (s['stateName'], (s.get('boundObjectFieldValues') or {}).get('cgraph'))
                                                        for s in subs) or 'none'))
    # fs-1: a Cross-Domain canvas (FirmwareRunState, no embedded HardwareSubgraph) still compiles the SAME referenced
    # CGraph through cmod-glue — "cmod-glue still generates the C project; nothing about its C output changes"
    # (DEMONSTRABLES_PLAN.md §9) — only the ONE-HardwareSubgraph-on-THIS-canvas requirement above is skipped (the
    # firmware is cmod's own FirmwareSolution now, referenced by name from Firmware Run, never embedded here).
    from cmod.custom import glue as GL
    cg = p['cgraph']
    glue = GL.compile_graph({'CGraph': [cg['graph']], 'CGraphNode': cg['nodes'], 'CGraphEdge': cg['edges']})
    files = {a['path']: a['sha256'] for a in glue['artifacts']}
    files_sha = sha(''.join('%s %s\n' % (f, files[f]) for f in sorted(files)))
    backend_name = hs.get('backend_solution') or '%s.backend' % hs['name']
    backend = PL.backend_partition(p['definition'], rep, backend_name)
    from polariNoCode.graph_compilers import stamp_provenance
    stamp_provenance(backend, 'hn-split', ['HardwareSolution:%s' % hs['name'], 'SolutionDefinition:%s' % hs['solution'],
                                           'CGraph:%s' % hs['cgraph']], notes='the backend half of %s (placement rule §2b)' % hs['name'])
    placed = [[n['layer'], n['node'], n['placement']] for n in rep['nodes']]
    split_sha = sha(json.dumps({'placement': placed, 'backend': backend['stateInstances'], 'glue_files_sha256': files_sha},
                               sort_keys=True, default=str))
    return {'definition': backend, 'artifacts': glue['artifacts'], 'placement': rep,
            'provenance': {'compiler': 'hn-split', 'generator': COMPILER, 'solution': hs['name'], 'split_sha256': split_sha,
                           'glue': glue['provenance'], 'glue_files_sha256': files_sha, 'glue_files': files,
                           'placement_summary': PL.summary(rep), 'runtime': rep['runtime']}}


def compile_solution(domain_rows):
    """The seam (polariNoCode.graph_compilers `hn-split`): {'HardwareSolution': [row], 'SolutionDefinition': [row], 'CGraph': [row],
    'CGraphNode': [...], 'CGraphEdge': [...], 'BoardDefinition': [row]?} → {definition (the backend half), artifacts (the board half,
    cmod-glue's), provenance}."""
    hs = (domain_rows.get('HardwareSolution') or [None])[0]
    sd = (domain_rows.get('SolutionDefinition') or [None])[0]
    g = (domain_rows.get('CGraph') or [None])[0]
    if not hs or not sd or not g:
        raise SplitRefused('hn-split needs one HardwareSolution, its SolutionDefinition and its CGraph row')
    raw = sd.get('definition') if isinstance(sd, dict) else getattr(sd, 'definition', '{}')
    definition = raw if isinstance(raw, dict) else json.loads(raw or '{}')
    board = (domain_rows.get('BoardDefinition') or [None])[0]
    if board is None:
        from board.board_seed import SEED_BOARD_DEFINITIONS
        board = next((dict(b) for b in SEED_BOARD_DEFINITIONS if b['name'] == hs.get('board_definition')), {})
    p = {'solution': dict(hs), 'definition': definition, 'board': dict(board),
         'cgraph': {'graph': dict(g), 'nodes': [dict(n) for n in domain_rows.get('CGraphNode') or []],
                    'edges': [dict(e) for e in domain_rows.get('CGraphEdge') or []]}}
    return compile_parts(p)


# ------------------------------------------------------------------ the record
def record_path(name):
    return os.path.join(RECORDS, '%s.json' % name)


def load_record(name):
    p = record_path(name)
    return json.load(open(p)) if os.path.isfile(p) else None


def save_record(name, rec):
    os.makedirs(RECORDS, exist_ok=True)
    with open(record_path(name), 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, indent=1, ensure_ascii=False, default=str)
        fh.write('\n')


def render(name, manager=None, work=None, write_record=True):
    """The split → the board half written as a C project into <work>/project (never into cmod's committed project), compared with
    cmod-1's committed record: files_sha256 and every file's sha must be EQUAL (unchanged output)."""
    p = solution_rows(name, manager)
    r = compile_parts(p)
    work = work or default_work(name)
    d = os.path.join(work, 'project')
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f not in {a['path'] for a in r['artifacts']}:
            os.remove(os.path.join(d, f))
    for a in r['artifacts']:
        open(os.path.join(d, a['path']), 'wb').write(a['text'].encode())
    from cmod.custom import glue as GL
    crec = GL.load_record(p['solution']['cgraph']) or {}
    pv = r['provenance']
    same = {'files_sha256': pv['glue_files_sha256'] == crec.get('files_sha256'),
            'graph_sha256': pv['glue']['graph_sha256'] == crec.get('graph_sha256'),
            'files': {f: s == (crec.get('files') or {}).get(f) for f, s in pv['glue_files'].items()}}
    out = {'solution': name, 'work': work, 'project': d, 'placement': r['placement'], 'provenance': pv,
           'backend_definition': r['definition'], 'cmod_record': {'files_sha256': crec.get('files_sha256', ''),
                                                                  'graph_sha256': crec.get('graph_sha256', ''),
                                                                  'hex_sha256': (crec.get('build') or {}).get('hex_sha256', '')},
           'unchanged_output': same['files_sha256'] and same['graph_sha256'] and all(same['files'].values()), 'same': same}
    if write_record:
        rec = load_record(name) or {}
        keep = rec if rec.get('split_sha256') == pv['split_sha256'] else {}
        rec = {'solution': name, 'compiler': COMPILER, 'split_sha256': pv['split_sha256'], 'rendered_at': _now(),
               'placement_summary': pv['placement_summary'], 'runtime': pv['runtime'],
               'placement': [{k: n[k] for k in ('layer', 'node', 'kind', 'placement', 'language', 'why')} for n in r['placement']['nodes']],
               'board_half': {'compiler': 'cmod-glue', 'cgraph': p['solution']['cgraph'], 'graph_sha256': pv['glue']['graph_sha256'],
                              'files': pv['glue_files'], 'files_sha256': pv['glue_files_sha256'],
                              'equal_to_cmod_record': out['unchanged_output'], 'cmod_record': out['cmod_record']},
               'backend_half': {'solution': r['definition']['solutionName'],
                                'states': [s['stateName'] + ' (' + PL.state_class(s) + ')' for s in r['definition']['stateInstances']],
                                'sha256': sha(json.dumps(r['definition']['stateInstances'], sort_keys=True, default=str))},
               'build': keep.get('build'), 'proof': keep.get('proof'), 'costs': keep.get('costs'),
               'costs_by_db': keep.get('costs_by_db')}
        save_record(name, rec)
    return out


def build(name, manager=None, work=None):
    """make ALONE in <work>/project through the board engines (cmod's make_alone) → <work>/out/firmware.hex + a firmware_build.json
    record in <work> — what `pol board twin uno up --work <work>` runs (the same .hex a board would be flashed with)."""
    import time
    work = work or default_work(name)
    d = os.path.join(work, 'project')
    if not os.path.isdir(d):
        raise SplitRefused('%s is not rendered into %s — pol hwnocode render %s first' % (name, work, name))
    from cmod.custom import glue as GL
    from cmod.custom.glue_build import make_alone
    p = solution_rows(name, manager)
    t0 = time.time()
    mk = make_alone(d)
    wall = time.time() - t0
    if not mk['ok']:
        raise SplitRefused('make alone failed in %s (%s %s): %s' % (d, mk['how'], mk['where'], mk['stderr'] or mk['stdout']))
    out = os.path.join(work, 'out')
    os.makedirs(out, exist_ok=True)
    hexp = os.path.join(out, 'firmware.hex')
    open(hexp, 'wb').write(mk['hex'])
    crec = GL.load_record(p['solution']['cgraph']) or {}
    ref = (crec.get('build') or {}).get('hex_sha256', '')
    cls = p['cgraph']['graph'].get('class_name', '')
    hdr = os.path.join(d, '%s_packets.h' % cls.lower())
    row = {'name': '%s-%s' % (name, mk['hex_sha256'][:12]), 'board_definition': p['solution']['board_definition'], 'state': 'built',
           'variant': '', 'source': 'hwnocode %s (the board half: cmod-glue of %s)' % (name, p['solution']['cgraph']),
           'classes_json': json.dumps([{'class': cls, 'header': os.path.basename(hdr),
                                        'header_sha256': sha(open(hdr, 'rb').read()) if os.path.isfile(hdr) else ''}]),
           'artifact_sha256': mk['hex_sha256'], 'hex_path': hexp, 'size_text': mk['sizes'].get('.text', 0),
           'size_data': mk['sizes'].get('.data', 0), 'size_bss': mk['sizes'].get('.bss', 0),
           'flash_bytes': mk['sizes'].get('.text', 0) + mk['sizes'].get('.data', 0),
           'ram_bytes': mk['sizes'].get('.data', 0) + mk['sizes'].get('.bss', 0), 'built_at': _now(),
           'engines_json': json.dumps({'make': '%s %s' % (mk['how'], mk['where'])}), 'project_dir': d, 'work_dir': work,
           'notes': 'built by `pol hwnocode build %s` (make alone)' % name}
    from board.custom import gen
    gen.write_record(work, row)
    b = {'ok': True, 'built_by': 'make alone (%s %s)' % (mk['how'], mk['where']), 'hex_sha256': mk['hex_sha256'], 'ref_hex_sha256': ref,
         'byte_identical_to_cmod1': mk['hex_sha256'] == ref, 'size_text': row['size_text'], 'size_data': row['size_data'],
         'size_bss': row['size_bss'], 'flash_bytes': row['flash_bytes'], 'ram_bytes': row['ram_bytes'], 'wall_s': round(wall, 2),
         'built_at': row['built_at']}
    rec = load_record(name)
    if rec is not None:
        rec['build'] = b
        save_record(name, rec)
    return dict(b, hex_path=hexp, work=work, record=row)
