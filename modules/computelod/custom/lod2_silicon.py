"""
@module computelod.custom.lod2_silicon

OPEN SILICON, FIRST RUNG DOWN (lod-2, plan §C Phase 5, §F2): the adder netlist lod-1 left at "logic / netlist"
is TECHNOLOGY-MAPPED onto a real, cited standard-cell library — SKY130 HD (Apache-2, the open PDK the plan
names) — and TIMED with OpenSTA under the library's own stated conditions. Two of lod-1's honest gaps close:

    netlist → standard cells     yosys `dfflibmap` + `abc -liberty`: which SKY130 cells, how many, what area
    propagation delay            OpenSTA: the worst arrival at the outputs, with process / temperature /
                                 voltage / load / input slew NAMED — a delay without them is misleading (§F2)

The Liberty (12.8 MB) is NEVER committed: `run` fetches it into a cache dir from OpenROAD-flow-scripts at a
PINNED commit and records the URL, the commit and the sha256 in the report; the rows cite those. Evidence
levels as ruled: the cell histogram and area are `measured` (the tool's own output); the OpenSTA delay is
`simulated` (a timing model of the process, not a bench); the cell → transistor step stays `partial` — the
cells' SPICE (sky130_fd_pr) is the next reference and is not read here.

    python3 -m computelod.custom.lod2_silicon run [--work DIR]     run: fetch (cached) → map → time → report
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
OUT = os.path.join(MOD, 'initialData', 'lod2')
IMAGE = os.environ.get('POLARI_EDA_IMAGE') or os.environ.get('POLARI_COMPUTELOD_TOOLS_IMAGE', 'polari-eda-tools:noble')   # built from polari-rf-node/polari-eda-tools
STA_IMAGE = os.environ.get('POLARI_OPENSTA_IMAGE', 'openroad/opensta')
LIB = {'name': 'sky130_fd_sc_hd__tt_025C_1v80.lib', 'repo': 'The-OpenROAD-Project/OpenROAD-flow-scripts',
       'commit': 'db8b985f89d456db29d39588443a025e7305a0a6', 'path': 'flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib',
       'licence': 'Apache-2.0 (SkyWater PDK)', 'corner': 'tt_025C_1v80 = typical process, 25 °C, 1.8 V'}
LIB['url'] = 'https://raw.githubusercontent.com/%s/%s/%s' % (LIB['repo'], LIB['commit'], LIB['path'])
CONDITIONS = {'process': 'tt (nom_process 1.0)', 'temperature_c': 25.0, 'voltage_v': 1.8, 'load_pf': 0.0146, 'input_slew_ns': 0.05,
              'load_note': '14.6 fF ≈ 4× an inv_1 input (FO4-like); a stated assumption, not a measured board'}
STA_TCL = '''read_liberty {lib}
read_verilog rv32_add_sky130.v
link_design rv32_add
set_load {load} [all_outputs]
set_input_transition {slew} [all_inputs]
report_checks -unconstrained -path_delay max -fields {{slew cap input_pins}} -digits 4
report_checks -unconstrained -path_delay min -digits 4
'''


def cache_dir():
    d = os.environ.get('POLARI_LOD_CACHE') or os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'polari-lod')
    os.makedirs(d, exist_ok=True)
    return d


def fetch_liberty():
    p = os.path.join(cache_dir(), LIB['name'])
    if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
        r = subprocess.run(['curl', '-sL', '-o', p, LIB['url']], capture_output=True, timeout=600)
        if r.returncode != 0 or os.path.getsize(p) < 1_000_000:
            raise SystemExit('could not fetch the SKY130 Liberty from %s' % LIB['url'])
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest()


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


def run(work=None):
    if not (shutil.which('yosys') or _docker_ok(IMAGE)):
        raise SystemExit('no yosys: docker build -t %s modules/computelod/custom/tools' % IMAGE)
    if not _docker_ok(STA_IMAGE):
        raise SystemExit('no OpenSTA: docker pull %s' % STA_IMAGE)
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod2')
    os.makedirs(work, exist_ok=True)
    lib_path, sha = fetch_liberty()
    shutil.copy(lib_path, os.path.join(work, LIB['name']))
    shutil.copy(os.path.join(LOD1, 'rv32_add.v'), work)
    rep = {'liberty': dict(LIB, sha256=sha, bytes=os.path.getsize(lib_path)), 'conditions': CONDITIONS}
    rc, out = _sh(work, 'yosys -q -p "read_verilog rv32_add.v; synth -top rv32_add; dfflibmap -liberty %s; abc -liberty %s; opt_clean; '
                        'tee -o mapped_stat.json stat -liberty %s -json; write_verilog -noattr rv32_add_sky130.v" > map.log 2>&1; echo rc=$?' % (LIB['name'], LIB['name'], LIB['name']), IMAGE)
    st = json.load(open(os.path.join(work, 'mapped_stat.json')))
    st = st.get('design') or st['modules'][list(st['modules'])[0]]
    rep['mapping'] = {'tool': 'yosys synth → dfflibmap → abc -liberty', 'cells': st['num_cells'], 'area_um2': round(float(st.get('area', 0.0)), 2),
                      'by_type': dict(sorted(st['num_cells_by_type'].items(), key=lambda kv: -kv[1]))}
    open(os.path.join(work, 'sta.tcl'), 'w').write(STA_TCL.format(lib=LIB['name'], load=CONDITIONS['load_pf'], slew=CONDITIONS['input_slew_ns']))
    rc, out = _sh(work, '', STA_IMAGE)
    open(os.path.join(work, 'sta.log'), 'w').write(out)
    arr = re.findall(r'^\s*([0-9.]+)\s+data arrival time', out, re.M)
    sp = re.findall(r'Startpoint: (\S+)', out); ep = re.findall(r'Endpoint: (\S+)', out)
    rep['timing'] = {'tool': 'OpenSTA (openroad/opensta image)', 'max_path_ns': float(arr[0]) if arr else None, 'min_path_ns': float(arr[1]) if len(arr) > 1 else None,
                     'max_path': '%s → %s' % (sp[0], ep[0]) if sp and ep else '?', 'min_path': '%s → %s' % (sp[1], ep[1]) if len(sp) > 1 and len(ep) > 1 else '?',
                     'unconstrained': True, 'note': 'combinational only: no clock — the worst arrival at any output from any input, under the conditions above'}
    os.makedirs(OUT, exist_ok=True)
    for f in ('mapped_stat.json', 'sta.tcl', 'sta.log', 'map.log'):
        if os.path.exists(os.path.join(work, f)):
            shutil.copy(os.path.join(work, f), OUT)
    # the mapped netlist (~20 kB) is worth keeping: it is the standard-cells rung's artifact
    shutil.copy(os.path.join(work, 'rv32_add_sky130.v'), OUT)
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, adder_cells):
    """(compute_mappings, characterizations) that REPLACE lod-1's two gaps, keyed by lod-1's names + new ones."""
    if not rep:
        return [], []
    lib = rep['liberty']; mp = rep['mapping']; tm = rep['timing']; cond = rep['conditions']
    ev_lib = 'SKY130 HD %s (%s) from %s @ %s, sha256 %s' % (lib['name'], lib['corner'], lib['repo'], lib['commit'][:12], lib['sha256'][:16])
    ev_map = 'lod2/report.json mapping — %s; %s' % (mp['tool'], ev_lib)
    ev_sta = 'lod2/report.json timing — OpenSTA, %s; %s' % (json.dumps(cond), ev_lib)
    netlist_ref = 'yosys synth rv32_add: %d cells' % adder_cells
    cells_ref = 'sky130_fd_sc_hd rv32_add: %d cells, %.1f µm² (%s)' % (mp['cells'], mp['area_um2'], ', '.join('%s×%d' % (k.replace('sky130_fd_sc_hd__', ''), v) for k, v in list(mp['by_type'].items())[:3]))
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    maps = [
        M(name='lod1: netlist → standard cells', kind='many-to-one', source_rung='logic-netlist', source_ref=netlist_ref, target_rung='standard-cells', target_ref=cells_ref,
          mapping_status='validated', evidence_level='measured', evidence_ref=ev_map,
          notes='RESOLVED by lod-2: abc maps the generic gates onto the library\'s cells (a ripple-carry adder becomes XNOR2 + MAJ3 chains). ' + json.dumps(mp['by_type'])),
        M(name='lod2: standard cells → devices', kind='partial', source_rung='standard-cells', source_ref=cells_ref, target_rung='devices', target_ref='sky130_fd_pr MOSFETs (the cells\' SPICE, not read here)',
          mapping_status='proposed', evidence_level='none', evidence_ref='',
          notes='PARTIAL on purpose: each SKY130 cell is a known transistor netlist in the PDK (sky130_fd_pr); reading those and the layout (Magic/KLayout, DRC/LVS) is the next rung down — lod-3.'),
    ]
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    chars = [
        C(name='lod1: rv32_add propagation delay', source_rung='standard-cells', source_ref=cells_ref, target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='propagation_delay', method='OpenSTA',
          conditions_json=json.dumps(cond), result=float(tm['max_path_ns'] or 0.0), units='ns', mapping_status='validated', evidence_level='simulated', evidence_ref=ev_sta,
          notes='RESOLVED by lod-2: the worst path %s under the stated conditions; a bench on fabricated silicon would be `measured` — this is the library\'s timing model' % tm['max_path']),
        C(name='lod2: rv32_add fastest path', source_rung='standard-cells', source_ref=cells_ref, target_rung='rtl', target_ref='lod1/rv32_add.v', characteristic='min_path_delay', method='OpenSTA',
          conditions_json=json.dumps(cond), result=float(tm['min_path_ns'] or 0.0), units='ns', mapping_status='validated', evidence_level='simulated', evidence_ref=ev_sta, notes=tm['min_path']),
        C(name='lod2: rv32_add cell area', source_rung='standard-cells', source_ref=cells_ref, target_rung='logic-netlist', target_ref=netlist_ref, characteristic='area', method='yosys stat -liberty',
          conditions_json=json.dumps({'library': lib['name'], 'cells': mp['cells']}), result=float(mp['area_um2']), units='um2', mapping_status='validated', evidence_level='measured', evidence_ref=ev_map),
    ]
    return maps, chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        work = sys.argv[sys.argv.index('--work') + 1] if '--work' in sys.argv else None
        rep = run(work)
        print(json.dumps({'mapping': rep['mapping'], 'timing': rep['timing']}, indent=1))
    else:
        print(json.dumps(report(), indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod2_silicon run')
