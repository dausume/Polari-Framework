"""
@module computelod.custom.lod3_cells

CELLS → TRANSISTORS → LAYOUT (lod-3, first slice; plan §C Phase 5): the two standard-cell mappings lod-2 left at
"standard cells" are READ one rung further down on both libraries, from the artefacts themselves:

    SKY130   each cell the adder uses → its SPICE netlist in the PDK (`sky130_fd_sc_hd__<cell>.spice`: every
             transistor with model, W, L) and its LEF (`SIZE w BY h`: the layout abstract's footprint). Fetched
             from google/skywater-pdk-libs-sky130_fd_sc_hd at a PINNED commit into the cache (cited by url +
             sha256, never committed — the same policy as the Liberty). Evidence: `analytical` (a cited file, not
             a tool run). The LEF areas summed over the mapped adder are cross-checked against lod-2's Liberty
             area — two independent PDK sources must agree, or the report says they do not.
    CNT      each cell → its device list in cntfet's CELL_LIBRARY (p/n transistors, composites expanded), the
             SAME topology the characterization netlisted; the device is the derived AlignedCNTFETDevice row.
             No layout exists for the CNT cells → that rung is UNRESOLVED, said so.

What is NOT done here (stated in the rows): DRC/LVS (Magic/netgen — not run), the transistor models themselves
(sky130_fd_pr corners — not simulated), fabrication (the process rows — the next rung, `partial`).

    python3 -m computelod.custom.lod3_cells run
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
LOD2 = os.path.join(MOD, 'initialData', 'lod2')
OUT = os.path.join(MOD, 'initialData', 'lod3')
CELLS_REPO = {'repo': 'google/skywater-pdk-libs-sky130_fd_sc_hd', 'commit': 'ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1', 'licence': 'Apache-2.0 (SkyWater PDK)'}
SPICE_SCALE_UM = 1e-6   # sky130 cell netlists: w=1e+06u means 1.0 µm (the PDK's .option scale)


def cache_dir():
    d = os.environ.get('POLARI_LOD_CACHE') or os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'polari-lod')
    os.makedirs(os.path.join(d, 'sky130_cells'), exist_ok=True)
    return os.path.join(d, 'sky130_cells')


def _fetch(rel):
    """(path, sha256, url) of one PDK file at the pinned commit; cached."""
    url = 'https://raw.githubusercontent.com/%s/%s/%s' % (CELLS_REPO['repo'], CELLS_REPO['commit'], rel)
    p = os.path.join(cache_dir(), os.path.basename(rel))
    if not os.path.exists(p) or os.path.getsize(p) < 100:
        r = subprocess.run(['curl', '-sfL', '-o', p, url], capture_output=True, timeout=120)
        if r.returncode != 0:
            raise SystemExit('could not fetch %s' % url)
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), url


def parse_spice(path):
    """Transistors of the first .subckt: [{name, model, w_um, l_um, d, g, s, b}] and the subckt pins."""
    devs, pins = [], []
    for ln in open(path, errors='replace'):
        t = ln.strip()
        if t.lower().startswith('.subckt'):
            pins = t.split()[2:]
        if not t or t[0] not in 'XxMm':
            continue
        f = t.split()
        kv = {k.lower(): v for k, v in (x.split('=', 1) for x in f if '=' in x)}
        model = next((x for x in f[1:] if 'fet' in x.lower()), f[-1] if len(f) > 5 else '')
        if not model:
            continue
        try:
            w = float(kv.get('w', '0').rstrip('uU')) * SPICE_SCALE_UM; l = float(kv.get('l', '0').rstrip('uU')) * SPICE_SCALE_UM
        except ValueError:
            w = l = 0.0
        devs.append({'name': f[0], 'model': model, 'w_um': round(w, 4), 'l_um': round(l, 4), 'd': f[1], 'g': f[2], 's': f[3], 'b': f[4] if len(f) > 4 else ''})
    return devs, pins


def parse_lef_size(path):
    m = re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', open(path, errors='replace').read())
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def _cell_rel(liberty_name, ext):
    base = liberty_name.replace('sky130_fd_sc_hd__', '')
    family = base.rsplit('_', 1)[0]
    return 'cells/%s/%s.%s' % (family, liberty_name, ext)


def cnt_devices(cell_key, library):
    """Expanded p/n device list of a CNT cell (composites via `compose`)."""
    c = library[cell_key]
    out = [{'type': d[0], 'drain': d[1], 'gate': d[2], 'source': d[3]} for d in c.get('devices', [])]
    for sub in c.get('compose', []) or []:
        out += cnt_devices(sub[0], library)
    return out


def run():
    rep2 = json.load(open(os.path.join(LOD2, 'report.json')))
    rep = {'sky130': {'source': dict(CELLS_REPO), 'cells': {}, 'files': {}}, 'cnt': {'cells': {}}, 'adder': {}}
    total_t, total_area, by_model = 0, 0.0, {}
    for lib_name, n in rep2['mapping']['by_type'].items():
        sp, sha_s, url_s = _fetch(_cell_rel(lib_name, 'spice')); lp, sha_l, url_l = _fetch(_cell_rel(lib_name, 'lef'))
        devs, pins = parse_spice(sp); w, h = parse_lef_size(lp)
        area = round(w * h, 4) if w else None
        hist = {}
        for d in devs:
            hist[d['model']] = hist.get(d['model'], 0) + 1; by_model[d['model']] = by_model.get(d['model'], 0) + n
        rep['sky130']['cells'][lib_name] = {'instances': n, 'transistors': len(devs), 'by_model': hist, 'pins': pins,
                                            'w_l_um': sorted({(d['w_um'], d['l_um']) for d in devs}), 'lef_size_um': [w, h], 'lef_area_um2': area,
                                            'devices': devs}
        rep['sky130']['files'][lib_name] = {'spice': {'url': url_s, 'sha256': sha_s}, 'lef': {'url': url_l, 'sha256': sha_l}}
        total_t += n * len(devs); total_area += n * (area or 0.0)
    lib_area = float(rep2['mapping']['area_um2'])
    rep['adder']['sky130'] = {'cells': rep2['mapping']['cells'], 'transistors': total_t, 'by_model': dict(sorted(by_model.items(), key=lambda kv: -kv[1])),
                              'lef_area_um2': round(total_area, 2), 'liberty_area_um2': lib_area, 'area_agrees': abs(total_area - lib_area) < 0.05,
                              'note': 'transistors = Σ instances × transistors-per-cell from the PDK netlists; area = Σ LEF SIZE, cross-checked against yosys stat -liberty (lod-2)'}
    # ---- the CNT library: topology from the cell library that netlisted the characterization
    try:
        sys.path.insert(0, os.path.dirname(MOD))
        from cntfet.objects.cnt_cell_library._shared import CELL_LIBRARY
    except Exception as exc:
        raise SystemExit('cntfet cell library not importable: %s' % exc)
    rep2c = json.load(open(os.path.join(LOD2, 'cnt', 'report.json')))
    key_of = {c['liberty_name']: c['cell'] for c in rep2c['characterization']['cells']}
    ct, cp, cn = 0, 0, 0
    for lib_name, n in rep2c['mapping']['by_type'].items():
        devs = cnt_devices(key_of[lib_name], CELL_LIBRARY)
        p = sum(1 for d in devs if d['type'] == 'p'); q = sum(1 for d in devs if d['type'] == 'n')
        rep['cnt']['cells'][lib_name] = {'instances': n, 'cell': key_of[lib_name], 'transistors': len(devs), 'p': p, 'n': q, 'devices': devs}
        ct += n * len(devs); cp += n * p; cn += n * q
    rep['adder']['cnt'] = {'cells': rep2c['mapping']['cells'], 'transistors': ct, 'p': cp, 'n': cn, 'device': rep2c['device'], 'partner': (rep2c.get('partner') or {}).get('name', ''),
                           'layout': None, 'note': 'device list = cntfet CELL_LIBRARY (the topology the characterization netlisted); the n device is %s, the p device its derived partner; NO layout exists for these cells' % rep2c['device']}
    rep['not_done'] = ['DRC/LVS of the SKY130 cells (Magic + netgen; not run)', 'transistor-level simulation with sky130_fd_pr corner models (not run — the Liberty carries the PDK\'s own characterization)',
                       'fabrication: the process rows behind sky130_fd_pr (next rung, partial)', 'CNT layout (none exists)']
    os.makedirs(OUT, exist_ok=True)
    from computelod.custom.repro import record
    rep['reproduction'] = record('computelod.custom.lod3_cells', inputs=[dict(v['spice'], label='%s .spice' % k) for k, v in rep['sky130']['files'].items()] + [dict(v['lef'], label='%s .lef' % k) for k, v in rep['sky130']['files'].items()],
                                 knobs={'cells_repo_commit': CELLS_REPO['commit']}, conditions={'reading': 'per-cell .spice (devices, W/L, scale 1e-6) and .lef SIZE, summed over the mapped instances'}, deterministic='a reading of fixed files')
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, lod2_rep, lod2cnt_rep):
    """(compute_mappings, characterizations): REPLACE lod-2's partial cells→devices by name, ADD devices→layout and
    layout→fabrication, and the transistor-count / LEF-area characterizations."""
    if not rep or not lod2_rep:
        return [], []
    a = rep['adder']['sky130']; src = rep['sky130']['source']
    mp = lod2_rep['mapping']
    cells_ref = 'sky130_fd_sc_hd rv32_add: %d cells, %.1f µm² (%s)' % (mp['cells'], mp['area_um2'], ', '.join('%s×%d' % (k.replace('sky130_fd_sc_hd__', ''), v) for k, v in list(mp['by_type'].items())[:3]))
    dev_ref = 'sky130_fd_pr rv32_add: %d transistors (%s)' % (a['transistors'], ', '.join('%s×%d' % (k.replace('sky130_fd_pr__', ''), v) for k, v in list(a['by_model'].items())[:3]))
    lay_ref = 'sky130_fd_sc_hd LEF rv32_add: %.2f µm² over %d cell footprints' % (a['lef_area_um2'], mp['cells'])
    ev = 'lod3/report.json — %s @ %s (%s): per-cell .spice + .lef, cited by url + sha256' % (src['repo'], src['commit'][:12], src['licence'])
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    maps = [
        M(name='lod2: standard cells → devices', kind='one-to-many', source_rung='standard-cells', source_ref=cells_ref, target_rung='devices', target_ref=dev_ref,
          mapping_status='implemented', evidence_level='analytical', evidence_ref=ev,
          notes='RESOLVED by lod-3: each cell\'s transistor netlist READ from the PDK (model, W, L per device; W/L in µm with the netlists\' 1e-6 scale). Not simulated here. ' + json.dumps(a['by_model'])),
        M(name='lod3: devices → layout', kind='one-to-one', source_rung='devices', source_ref=dev_ref, target_rung='layout', target_ref=lay_ref,
          mapping_status='validated' if a['area_agrees'] else 'implemented', evidence_level='analytical', evidence_ref=ev,
          notes='the LEF SIZE of every mapped cell, summed: %.2f µm² vs the Liberty area %.2f µm² from lod-2 — %s. DRC/LVS (Magic, netgen) NOT run; the GDS not read.' % (
              a['lef_area_um2'], a['liberty_area_um2'], 'AGREE (two independent PDK sources)' if a['area_agrees'] else 'DISAGREE — reported, not hidden')),
        M(name='lod3: layout → fabrication', kind='partial', source_rung='layout', source_ref=lay_ref, target_rung='fabrication', target_ref='SkyWater 130 nm process (sky130_fd_pr; the process rows are not read here)',
          mapping_status='proposed', evidence_level='none', evidence_ref='', notes='PARTIAL on purpose: the next rung is the process (lithography, implants, metal stack) behind sky130_fd_pr — lod-4.'),
    ]
    chars = [
        C(name='lod3: rv32_add transistor count', source_rung='devices', source_ref=dev_ref, target_rung='standard-cells', target_ref=cells_ref, characteristic='transistor_count', method='PDK netlists, counted',
          conditions_json=json.dumps({'library': 'sky130_fd_sc_hd', 'cells': mp['cells']}), result=float(a['transistors']), units='transistors', mapping_status='validated', evidence_level='analytical', evidence_ref=ev),
        C(name='lod3: rv32_add layout area (LEF)', source_rung='layout', source_ref=lay_ref, target_rung='standard-cells', target_ref=cells_ref, characteristic='area', method='LEF SIZE, summed',
          conditions_json=json.dumps({'library': 'sky130_fd_sc_hd', 'cells': mp['cells'], 'liberty_area_um2': a['liberty_area_um2']}), result=float(a['lef_area_um2']), units='um2',
          mapping_status='validated' if a['area_agrees'] else 'implemented', evidence_level='analytical', evidence_ref=ev, notes='agrees with yosys stat -liberty' if a['area_agrees'] else 'does NOT agree with the Liberty area'),
    ]
    if lod2cnt_rep and rep.get('cnt'):
        c = rep['adder']['cnt']; mpc = lod2cnt_rep['mapping']
        ccells_ref = 'polari_cnt_lib rv32_add: %d cells (%s)' % (mpc['cells'], ', '.join('%s×%d' % (k, v) for k, v in list(mpc['by_type'].items())[:3]))
        cdev_ref = 'AlignedCNTFETDevice %s (n) + %s (p): %d transistors (%d p, %d n)' % (c['device'], c['partner'] or 'mirror', c['transistors'], c['p'], c['n'])
        maps += [
            M(name='lod2-cnt: CNT standard cells → devices', kind='one-to-many', source_rung='standard-cells', source_ref=ccells_ref, target_rung='devices', target_ref=cdev_ref,
              mapping_status='implemented', evidence_level='simulated', evidence_ref='lod3/report.json cnt — cntfet CELL_LIBRARY device lists (the characterization\'s own netlists); ' + lod2cnt_rep['characterization']['result_row'],
              notes='the cell topology the ngspice characterization ran on: %d transistors for the adder; the device is the derived VS card (a model, hence simulated). No layout exists.' % c['transistors']),
            M(name='lod3-cnt: devices → layout', kind='unresolved', source_rung='devices', source_ref=cdev_ref, target_rung='layout', target_ref='',
              mapping_status='proposed', evidence_level='none', evidence_ref='', notes='UNRESOLVED: the CNT cells have no layout (no PDK, no LEF/GDS); the microchip ladder\'s process rows would have to supply one — stated, not invented.'),
        ]
        chars.append(C(name='lod3-cnt: rv32_add transistor count', source_rung='devices', source_ref=cdev_ref, target_rung='standard-cells', target_ref=ccells_ref, characteristic='transistor_count', method='cell library device lists, counted',
                       conditions_json=json.dumps({'library': 'polari_cnt_lib', 'cells': mpc['cells']}), result=float(c['transistors']), units='transistors', mapping_status='validated', evidence_level='simulated',
                       evidence_ref='lod3/report.json cnt', notes='%d p + %d n' % (c['p'], c['n'])))
    return maps, chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        rep = run()
        print(json.dumps(rep['adder'], indent=1))
    else:
        print(json.dumps(report()['adder'], indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod3_cells run')
