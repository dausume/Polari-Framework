"""
@module computelod.custom.lod2_cnt

THE SECOND LIBERTY (lod-2b, plan §C Phase 5 / §G.7 owed): the same adder, technology-mapped onto OUR OWN
carbon-nanotube cell library — characterized by this instance's cntfet module (ngspice transients through the
OpenVAF-compiled VS model, the S5 sweep) — and timed with OpenSTA under that library's own conditions. Beside
SKY130 (a cited, fabricated PDK's timing model) this is a DERIVED library over a DERIVED device: every number is
`simulated`, its provenance is the device row + its derivation + the CellCharacterizationRun row, and the report
says what the library does NOT carry (cell area: not characterized → no area rung here; standin parasitics).

    python3 -m computelod.custom.lod2_cnt run [--device NAME] [--cells a,b,…] [--work DIR]

`run` BOOTS the real server in-process (the cntfet rows, the derivation, the characterization all live on a
manager) — run it from a throwaway cwd (the boot writes ./data/). Engines resolve through the cntfet ladder
(~/tools or a cnt-engines worker); yosys through the computelod tools image; OpenSTA through openroad/opensta.
Outputs (committed, small, ours): initialData/lod2/cnt/{polari_cnt_lib.lib, report.json, rv32_add_cnt.v, …}.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
LOD1 = os.path.join(MOD, 'initialData', 'lod1')
OUT = os.path.join(MOD, 'initialData', 'lod2', 'cnt')
IMAGE = os.environ.get('POLARI_COMPUTELOD_TOOLS_IMAGE', 'polari-computelod-tools:noble')
STA_IMAGE = os.environ.get('POLARI_OPENSTA_IMAGE', 'openroad/opensta')
LIB_NAME = 'polari_cnt_lib.lib'
#: the cells an adder needs (plus the basics abc reaches for); sequential cells refuse by design (not needed)
CELLS = ['cinv', 'cbuf', 'cnand2', 'cnor2', 'cnand3', 'cnor3', 'cxor2', 'cxnor2', 'caoi21', 'coai21', 'cha', 'cfa']
STA_TCL = '''read_liberty {lib}
read_verilog rv32_add_cnt.v
link_design rv32_add
set_load {load} [all_outputs]
set_input_transition {slew} [all_inputs]
report_checks -unconstrained -path_delay max -fields {{slew cap input_pins}} -digits 4
report_checks -unconstrained -path_delay min -digits 4
'''


def _docker_ok(image):
    try:
        return subprocess.run(['docker', 'image', 'inspect', image], capture_output=True, timeout=20).returncode == 0
    except Exception:
        return False


def _sh(work, cmd, image):
    if image == IMAGE and shutil.which('yosys'):
        full = ['sh', '-c', cmd]
    elif image == STA_IMAGE:
        full = ['docker', 'run', '--rm', '-v', '%s:/w' % work, '-w', '/w', '--entrypoint', '/OpenSTA/build/sta', STA_IMAGE, '-exit', 'sta.tcl']
    else:
        full = ['docker', 'run', '--rm', '-v', '%s:/w' % work, '-w', '/w', IMAGE, 'sh', '-c', cmd]
    r = subprocess.run(full, capture_output=True, text=True, timeout=900, cwd=work)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _boot():
    os.environ.setdefault('POLARI_MODULES', 'simulations,simSpace,materialsScience,pspp,magnetics,scoring,techtree,microchip,cntfet,electrodevice,sifet,hwfpga,tensormath,tensortree,computelod')
    os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
    fw = os.path.dirname(os.path.dirname(MOD))   # modules/computelod → modules → the framework
    sys.path.insert(0, fw); sys.path.insert(0, os.path.join(fw, 'modules'))
    from objectTreeManagerDecorators import managerObject
    return managerObject(hasServer=True, hasDB=True)


def _pick_device(manager, name):
    devs = list(manager.objectTables.get('AlignedCNTFETDevice', {}).values())
    if name:
        d = next((x for x in devs if str(x.name) == name), None)
        if d is None:
            raise SystemExit('no AlignedCNTFETDevice %r; have: %s' % (name, sorted(str(x.name) for x in devs)))
        return d
    try:   # prefer the n device of a ComplementaryPair (a real p partner instead of the mirror card)
        from cntfet.cnt_taxonomy_basis import _pair_rows
        for pair in _pair_rows(manager).values():
            d = next((x for x in devs if str(x.name) == pair['n_device']), None)
            if d is not None:
                return d
    except Exception:
        pass
    if not devs:
        raise SystemExit('no AlignedCNTFETDevice rows seeded — is cntfet in POLARI_MODULES?')
    return devs[0]


def run(device_name=None, cells=None, work=None):
    if not (shutil.which('yosys') or _docker_ok(IMAGE)):
        raise SystemExit('no yosys: docker build -t %s modules/computelod/custom/tools' % IMAGE)
    if not _docker_ok(STA_IMAGE):
        raise SystemExit('no OpenSTA: docker pull %s' % STA_IMAGE)
    manager = _boot()
    from cntfet.custom.cnt_derive import derive_device
    from cntfet.cnt_cell_library_basis import characterize_cells
    device = _pick_device(manager, device_name)
    rep = {'device': str(device.name), 'library': LIB_NAME}
    der = derive_device(manager, device)
    if not der.get('ok', True) and 'error' in der:
        raise SystemExit('derive refused: %s' % der.get('error'))
    rep['derivation'] = {'derived_at': str(getattr(device, 'derived_at', '')), 'summary': {k: der[k] for k in der if k in ('ok', 'ladder', 'steps', 'validity', 'anchors', 'vdd_v')}}
    partner = None
    try:
        from cntfet.cnt_taxonomy_basis import _pair_rows
        for pair in _pair_rows(manager).values():
            if str(device.name) == pair['n_device']:
                partner = pair['p_device']
    except Exception:
        pass
    if partner:
        pdev = next((x for x in manager.objectTables.get('AlignedCNTFETDevice', {}).values() if str(x.name) == partner), None)
        if pdev is not None:
            derive_device(manager, pdev)
            rep['partner'] = {'name': partner, 'derived_at': str(getattr(pdev, 'derived_at', ''))}
    vdd = float(getattr(device, 'vdd_v', None) or 0.6)
    cells = cells or CELLS
    ch = characterize_cells(manager, device, cells=cells, drives=(1,), vdd=vdd)
    if not ch.get('ok'):
        raise SystemExit('characterize refused: %s' % (ch.get('refusal') or ch.get('error')))
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod2-cnt')
    os.makedirs(work, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    shutil.copy(ch['libertyPath'], os.path.join(work, LIB_NAME)); shutil.copy(ch['libertyPath'], os.path.join(OUT, LIB_NAME))
    lib_sha = hashlib.sha256(open(ch['libertyPath'], 'rb').read()).hexdigest()
    rep['characterization'] = {'result_row': ch['resultRow'], 'vdd_v': ch['vdd_v'], 'p_side': ch.get('pSide', ''), 'executor': ch.get('executor', ''),
                               'cells': [{'cell': c['cell'], 'drive': c['drive'], 'liberty_name': c['libertyName'], 'arcs': c['arcs']} for c in ch['cells']],
                               'grid_slews_s': ch['gridSlews_s'], 'grid_loads_f': ch['gridLoads_f'], 'monotone': ch.get('monotone'), 'failures': ch.get('failures'),
                               'sta_gate': ch.get('staGate'), 'honesty': ch.get('honesty', ''), 'definitions': ch.get('definitions', {}), 'liberty_bytes': ch['libertyBytes'], 'liberty_sha256': lib_sha,
                               'not_carried': ['cell area (the library has no area attribute: layout is not characterized → no area rung from this Liberty)',
                                               'leakage beyond the ioff standin', 'setup/hold (combinational cells only)']}
    # conditions under which the adder is timed: the library's own nominal point, the sweep's own grid
    load_f = float(ch['gridLoads_f'][-1]); slew_s = float(ch['gridSlews_s'][1])
    cond = {'process': 'derived VS model (nom_process 1)', 'temperature_k': 300.0, 'voltage_v': vdd, 'load_ff': round(load_f * 1e15, 4), 'input_slew_ps': round(slew_s * 1e12, 4),
            'load_note': '4× a cinv input (the sweep\'s largest grid load — FO4-like); the slew is the grid\'s middle point; both inside the characterized grid, no extrapolation'}
    rep['conditions'] = cond
    shutil.copy(os.path.join(LOD1, 'rv32_add.v'), work)
    rc, out = _sh(work, 'yosys -q -p "read_verilog rv32_add.v; synth -top rv32_add; dfflibmap -liberty %s; abc -liberty %s; opt_clean; '
                        'tee -o mapped_stat.json stat -liberty %s -json; write_verilog -noattr rv32_add_cnt.v" > map.log 2>&1; echo rc=$?' % (LIB_NAME, LIB_NAME, LIB_NAME), IMAGE)
    if not os.path.exists(os.path.join(work, 'mapped_stat.json')):
        raise SystemExit('yosys mapping failed:\n' + open(os.path.join(work, 'map.log')).read()[-2000:])
    st = json.load(open(os.path.join(work, 'mapped_stat.json')))
    st = st.get('design') or st['modules'][list(st['modules'])[0]]
    rep['mapping'] = {'tool': 'yosys synth → dfflibmap → abc -liberty', 'cells': st['num_cells'], 'area_um2': None, 'area_note': 'the CNT Liberty carries no area',
                      'by_type': dict(sorted(st['num_cells_by_type'].items(), key=lambda kv: -kv[1]))}
    # Liberty time unit is ps → OpenSTA reports ps; set_load in fF (capacitive_load_unit ff); transition in ps
    open(os.path.join(work, 'sta.tcl'), 'w').write(STA_TCL.format(lib=LIB_NAME, load=cond['load_ff'], slew=cond['input_slew_ps']))
    rc, out = _sh(work, '', STA_IMAGE)
    open(os.path.join(work, 'sta.log'), 'w').write(out)
    arr = re.findall(r'^\s*(-?[0-9.]+)\s+data arrival time', out, re.M)
    sp = re.findall(r'Startpoint: (\S+)', out); ep = re.findall(r'Endpoint: (\S+)', out)
    rep['timing'] = {'tool': 'OpenSTA (openroad/opensta image)', 'unit': 'ps', 'max_path_ps': float(arr[0]) if arr else None, 'min_path_ps': float(arr[1]) if len(arr) > 1 else None,
                     'max_path': '%s → %s' % (sp[0], ep[0]) if sp and ep else '?', 'min_path': '%s → %s' % (sp[1], ep[1]) if len(sp) > 1 and len(ep) > 1 else '?',
                     'unconstrained': True, 'note': 'combinational only, under the conditions above; the library is intrinsic-grade (standin parasitics, S1 model) — NOT signoff'}
    for f in ('mapped_stat.json', 'sta.tcl', 'sta.log', 'map.log', 'rv32_add_cnt.v'):
        if os.path.exists(os.path.join(work, f)):
            shutil.copy(os.path.join(work, f), OUT)
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, adder_cells):
    """NEW rows beside lod-2's SKY130 ones (different names; nothing replaced): the CNT mapping, its delay, and
    the honest cells → devices step, which for THIS library is a real reference (the derived device row)."""
    if not rep:
        return [], []
    ch = rep['characterization']; mp = rep['mapping']; tm = rep['timing']; cond = rep['conditions']
    ev_lib = 'polari_cnt_lib.lib characterized by cntfet (ngspice transients, OpenVAF VS model) on device %s derived %s; CellCharacterizationRun %s; sha256 %s' % (
        rep['device'], rep['derivation']['derived_at'][:19], ch['result_row'], ch['liberty_sha256'][:16])
    ev_map = 'lod2/cnt/report.json mapping — %s; %s' % (mp['tool'], ev_lib)
    ev_sta = 'lod2/cnt/report.json timing — OpenSTA, %s; %s' % (json.dumps(cond), ev_lib)
    netlist_ref = 'yosys synth rv32_add: %d cells' % adder_cells
    cells_ref = 'polari_cnt_lib rv32_add: %d cells (%s)' % (mp['cells'], ', '.join('%s×%d' % (k, v) for k, v in list(mp['by_type'].items())[:3]))
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    maps = [
        M(name='lod2-cnt: netlist → CNT standard cells', kind='many-to-one', source_rung='logic-netlist', source_ref=netlist_ref, target_rung='standard-cells', target_ref=cells_ref,
          mapping_status='validated', evidence_level='simulated', evidence_ref=ev_map,
          notes='the SAME netlist as the SKY130 mapping, onto a library this instance derived and characterized itself; evidence is simulated (the library is a model of a model). ' + json.dumps(mp['by_type'])),
        M(name='lod2-cnt: CNT standard cells → devices', kind='one-to-many', source_rung='standard-cells', source_ref=cells_ref, target_rung='devices',
          target_ref='AlignedCNTFETDevice %s (n) %s' % (rep['device'], ('+ partner %s (p)' % rep['partner']['name']) if rep.get('partner') else '(p = mirror card)'),
          mapping_status='implemented', evidence_level='simulated', evidence_ref=ev_lib,
          notes='for THIS library the cells → devices step is a real reference: each cell\'s SPICE is the derived device\'s VS card (%s). Layout is not characterized (no area).' % ch.get('p_side', '')),
    ]
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    chars = [
        C(name='lod2-cnt: rv32_add propagation delay', source_rung='standard-cells', source_ref=cells_ref, target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='propagation_delay', method='OpenSTA',
          conditions_json=json.dumps(cond), result=float(tm['max_path_ps'] or 0.0) / 1000.0, units='ns', mapping_status='validated', evidence_level='simulated', evidence_ref=ev_sta,
          notes='the worst path %s under the stated conditions on the CNT library (intrinsic-grade: standin parasitics; NOT signoff)' % tm['max_path']),
        C(name='lod2-cnt: rv32_add fastest path', source_rung='standard-cells', source_ref=cells_ref, target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='min_path_delay', method='OpenSTA',
          conditions_json=json.dumps(cond), result=float(tm['min_path_ps'] or 0.0) / 1000.0, units='ns', mapping_status='validated', evidence_level='simulated', evidence_ref=ev_sta, notes=tm['min_path']),
    ]
    return maps, chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        dev = sys.argv[sys.argv.index('--device') + 1] if '--device' in sys.argv else None
        cells = sys.argv[sys.argv.index('--cells') + 1].split(',') if '--cells' in sys.argv else None
        work = sys.argv[sys.argv.index('--work') + 1] if '--work' in sys.argv else None
        rep = run(dev, cells, work)
        print(json.dumps({'device': rep['device'], 'cells': [c['liberty_name'] for c in rep['characterization']['cells']], 'mapping': rep['mapping'], 'timing': rep['timing']}, indent=1))
    else:
        print(json.dumps(report(), indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod2_cnt run')
