"""
@module computelod.custom.lod3_devices

DEVICES → CELLS, SIMULATED BY US (lod-3b): the transistor netlists lod-3 READ are now RUN — ngspice-46 on the
PDK's own BSIM4 models (`sky130_fd_pr`, tt corner, per-device `*.corner.spice` + `*.mismatch.corner.spice` +
`*.pm3.spice`, fetched at a PINNED commit into the cache, cited by sha256, never committed) — and the result is
CROSS-CHECKED against the Liberty the foundry characterized (lod-2): the same cell, the same slew (sky130's
20–80 % convention) and load, our transient vs their table (bilinearly interpolated at the same point).

What agreement means, and what the gap is: the `.spice` under `cells/` is the SCHEMATIC netlist (devices with
W/L, no wiring parasitics); the Liberty was characterized on the extracted layout. A ~10–20 % difference is the
parasitics + the vendor's characterization setup, and it is REPORTED, not tuned away. Evidence level:
`simulated` (a model of the process, run here). Conditions named on every number (§F2).

    python3 -m computelod.custom.lod3_devices run [--cells inv_1,nand2_1]
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
OUT = os.path.join(MOD, 'initialData', 'lod3')
PR_REPO = {'repo': 'google/skywater-pdk-libs-sky130_fd_pr', 'commit': 'f62031a1be9aefe902d6d54cddd6f59b57627436', 'licence': 'Apache-2.0 (SkyWater PDK)'}
SC_REPO = {'repo': 'google/skywater-pdk-libs-sky130_fd_sc_hd', 'commit': 'ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1'}
CONDITIONS = {'corner': 'tt', 'temperature_c': 25.0, 'voltage_v': 1.8, 'load_pf': 0.0146, 'input_slew_ns_20_80': 0.05, 'input_shape': 'linear ramp (0–100 % over 83.3 ps so 20–80 % = 50 ps)',
              'thresholds': 'delay 50 %/50 %, transition 20–80 % (the Liberty\'s own)', 'netlist': 'schematic (cells/<cell>/*.spice) — NO extracted parasitics'}
#: the arcs proven: (cell, input pin, the other pins tied so the arc is sensitised)
ARCS = {'inv_1': {'pins': ['A'], 'ties': {}, 'out': 'Y', 'inverting': True},
        'nand2_1': {'pins': ['A', 'B'], 'ties': {'A': 'VPWR', 'B': 'VPWR'}, 'out': 'Y', 'inverting': True}}
DEVICES = ['nfet_01v8', 'pfet_01v8_hvt']


def cache_dir():
    d = os.environ.get('POLARI_LOD_CACHE') or os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'polari-lod')
    os.makedirs(os.path.join(d, 'sky130_pr'), exist_ok=True)
    return os.path.join(d, 'sky130_pr')


def _fetch(repo, rel):
    url = 'https://raw.githubusercontent.com/%s/%s/%s' % (repo['repo'], repo['commit'], rel)
    p = os.path.join(cache_dir(), os.path.basename(rel))
    if not os.path.exists(p) or os.path.getsize(p) < 100:
        r = subprocess.run(['curl', '-sfL', '-o', p, url], capture_output=True, timeout=300)
        if r.returncode != 0:
            raise SystemExit('could not fetch %s' % url)
    return p, hashlib.sha256(open(p, 'rb').read()).hexdigest(), url


def ngspice_where():
    """ngspice through the cntfet engines ladder (cntfet.custom.cnt_osdi.find_ngspice: CNTFET_ENGINES_URL → local
    PATH/~/tools → topology provider cntfet.engines → refusal): the path, 'remote', or None."""
    try:
        from cntfet.custom.cnt_osdi import find_ngspice
        path, _why = find_ngspice()
        return path
    except Exception:
        return None


def run_spice(work, deck_path, timeout=600):
    """Run one deck wherever ngspice resolves; stdout+stderr as text (the .meas lines are in there)."""
    from cntfet.custom.cnt_osdi import find_ngspice, run_ngspice
    path, why = find_ngspice()
    if path is None:
        raise SystemExit('no ngspice: %s' % why)
    if path == 'remote':
        # the worker receives netlist TEXT only: inline every absolute `.include` (the cached model files, the cell
        # netlist) so the deck is self-contained where it runs; relative includes are left (they travel as-is)
        text = open(deck_path, errors='replace').read()
        def _inline(m):
            fp = m.group(1)
            return ('* inlined %s\n' % fp) + open(fp, errors='replace').read() if os.path.isabs(fp) and os.path.exists(fp) else m.group(0)
        text = re.sub(r'^\.include\s+"([^"]+)"\s*$', _inline, text, flags=re.M)
        deck_path = deck_path[:-3] + '.remote.sp' if deck_path.endswith('.sp') else deck_path + '.remote'
        open(deck_path, 'w').write(text)
    r = run_ngspice(path, work, deck_path, timeout=timeout)
    return (getattr(r, 'stdout', '') or '') + (getattr(r, 'stderr', '') or '')


def find_ngspice():   # kept for callers of the old name
    return ngspice_where()


def liberty_tables(lib_text, cell, pin):
    """{cell_fall, cell_rise, fall_transition, rise_transition: (index_1[], index_2[], rows[][])} for one related pin."""
    i = lib_text.index('cell ("sky130_fd_sc_hd__%s")' % cell); blk = lib_text[i:i + 60000]
    j = blk.index('related_pin : "%s"' % pin); tb = blk[j:j + 14000]
    out = {}
    for name in ('cell_fall', 'cell_rise', 'fall_transition', 'rise_transition'):
        k = tb.index(name + ' ('); seg = tb[k:k + 1500]
        idx1 = [float(x) for x in re.search(r'index_1\("([^"]+)"\)', seg).group(1).split(',')]
        idx2 = [float(x) for x in re.search(r'index_2\("([^"]+)"\)', seg).group(1).split(',')]
        vals = re.search(r'values\((.*?)\);', seg, re.S).group(1)
        out[name] = (idx1, idx2, [[float(v) for v in r.split(',')] for r in re.findall(r'"([^"]+)"', vals)])
    return out


def interp(t, slew, load):
    import bisect
    i1, i2, rows = t
    def ax(idx, x):
        k = max(1, min(len(idx) - 1, bisect.bisect_left(idx, x))); return k - 1, (x - idx[k - 1]) / (idx[k] - idx[k - 1])
    a, fa = ax(i1, slew); b, fb = ax(i2, load)
    return (1 - fa) * ((1 - fb) * rows[a][b] + fb * rows[a][b + 1]) + fa * ((1 - fb) * rows[a + 1][b] + fb * rows[a + 1][b + 1])


def _deck(cell, pin, arc, includes, cell_spice):
    ties = ' '.join('V%s %s 0 %s' % (p, p.lower(), '1.8' if arc['ties'].get(p) == 'VPWR' else '0') for p in arc['pins'] if p != pin)
    pins = ' '.join(p.lower() if p != pin else 'a_in' for p in arc['pins'])
    vdd, ramp = CONDITIONS['voltage_v'], CONDITIONS['input_slew_ns_20_80'] / 0.6
    v20, v80, v50 = vdd * 0.2, vdd * 0.8, vdd * 0.5
    return '''* sky130_fd_sc_hd__%(cell)s pin %(pin)s → %(out)s on sky130_fd_pr tt — Polari lod-3b
.option scale=1.0e-6
.temp %(temp)s
%(includes)s
.include "%(cell_spice)s"
VDD vpwr 0 %(vdd)s
VSS vgnd 0 0
%(ties)s
Xdut %(pins)s vgnd vgnd vpwr vpwr y sky130_fd_sc_hd__%(cell)s
Cload y 0 %(load)sp
Vin a_in 0 pwl(0 0 1n 0 %(t1)sn %(vdd)s 3n %(vdd)s %(t2)sn 0 5n 0)
.tran 1p 5n
.control
run
meas tran tphl trig v(a_in) val=%(v50)s rise=1 targ v(y) val=%(v50)s fall=1
meas tran tplh trig v(a_in) val=%(v50)s fall=1 targ v(y) val=%(v50)s rise=1
meas tran tfall trig v(y) val=%(v80)s fall=1 targ v(y) val=%(v20)s fall=1
meas tran trise trig v(y) val=%(v20)s rise=1 targ v(y) val=%(v80)s rise=1
quit
.endc
.end
''' % {'cell': cell, 'pin': pin, 'out': arc['out'], 'temp': CONDITIONS['temperature_c'], 'includes': includes, 'cell_spice': cell_spice, 'vdd': vdd, 'ties': ties, 'pins': pins,
       'load': CONDITIONS['load_pf'], 't1': round(1 + ramp, 6), 't2': round(3 + ramp, 6), 'v50': v50, 'v80': v80, 'v20': v20}


def run(cells=None, work=None):
    ng = ngspice_where()
    if not ng:
        raise SystemExit('no ngspice through the cntfet engines ladder (PATH, ~/tools, CNTFET_ENGINES_URL, or a cntfet.engines provider)')
    from computelod.custom.lod2_silicon import fetch_liberty
    lib_path, lib_sha = fetch_liberty(); lib_text = open(lib_path, errors='replace').read()
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod3b'); os.makedirs(work, exist_ok=True)
    files = {}
    inc = []
    for dev in DEVICES:
        for kind in ('mismatch.corner', 'tt.corner', 'tt.pm3'):
            rel = 'cells/%s/sky130_fd_pr__%s__%s.spice' % (dev, dev, kind)
            p, sha, url = _fetch(PR_REPO, rel); files[os.path.basename(rel)] = {'url': url, 'sha256': sha, 'bytes': os.path.getsize(p)}
            if kind != 'tt.pm3':   # the corner file includes the pm3 itself
                inc.append('.include "%s"' % p)
    rep = {'tool': 'ngspice-46 (%s)' % ng, 'engine_ladder': 'cntfet.engines (find_ngspice)', 'models': dict(PR_REPO, files=files), 'liberty_sha256': lib_sha, 'conditions': CONDITIONS, 'arcs': []}
    for cell in (cells or list(ARCS)):
        arc = ARCS[cell]
        rel = 'cells/%s/sky130_fd_sc_hd__%s.spice' % (cell.rsplit('_', 1)[0], cell)
        cp, csha, curl = _fetch(SC_REPO, rel)
        tabs_all = {}
        for pin in arc['pins']:
            deck = os.path.join(work, '%s_%s.sp' % (cell, pin)); open(deck, 'w').write(_deck(cell, pin, arc, '\n'.join(inc), cp))
            text = run_spice(work, deck)
            got = {m.group(1): float(m.group(2)) * 1e12 for m in re.finditer(r'^(tphl|tplh|tfall|trise)\s*=\s*([-0-9.e+]+)', text, re.M)}
            if len(got) < 4:
                raise SystemExit('ngspice measures missing for %s/%s:\n%s' % (cell, pin, text[-1500:]))
            tabs = liberty_tables(lib_text, cell, pin)
            lib = {k: interp(tabs[k], CONDITIONS['input_slew_ns_20_80'], CONDITIONS['load_pf']) * 1000 for k in tabs}
            cmp = {'tphl_ps': {'ours': round(got['tphl'], 2), 'liberty': round(lib['cell_fall'], 2)}, 'tplh_ps': {'ours': round(got['tplh'], 2), 'liberty': round(lib['cell_rise'], 2)},
                   'fall_transition_ps': {'ours': round(got['tfall'], 2), 'liberty': round(lib['fall_transition'], 2)}, 'rise_transition_ps': {'ours': round(got['trise'], 2), 'liberty': round(lib['rise_transition'], 2)}}
            for k, v in cmp.items():
                v['delta_pct'] = round((v['ours'] - v['liberty']) / v['liberty'] * 100, 1)
            rep['arcs'].append({'cell': 'sky130_fd_sc_hd__%s' % cell, 'pin': pin, 'out': arc['out'], 'ties': {p: arc['ties'][p] for p in arc['pins'] if p != pin}, 'cell_spice': {'url': curl, 'sha256': csha}, 'compare': cmp})
    deltas = [abs(v['delta_pct']) for a in rep['arcs'] for v in a['compare'].values()]
    rep['summary'] = {'arcs': len(rep['arcs']), 'max_abs_delta_pct': max(deltas), 'mean_abs_delta_pct': round(sum(deltas) / len(deltas), 1),
                      'reading': 'our schematic-netlist transient on the PDK models vs the foundry-characterized Liberty at the same slew/load: the gap is layout parasitics + the vendor setup, reported not tuned'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(rep, open(os.path.join(OUT, 'devices_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'devices_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep):
    """Characterizations UP from devices to cells: one per arc's tpHL/tpLH, evidence simulated, the Liberty value in conditions."""
    if not rep:
        return [], []
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    ev = 'lod3/devices_report.json — %s on sky130_fd_pr @ %s (%s), cell netlists @ %s; %s' % (rep['tool'].split(' (')[0], PR_REPO['commit'][:12], PR_REPO['licence'], SC_REPO['commit'][:12], json.dumps(rep['conditions']))
    chars = []
    for a in rep['arcs']:
        for key, lab in (('tphl_ps', 'tpHL'), ('tplh_ps', 'tpLH')):
            v = a['compare'][key]
            chars.append(C(name='lod3: %s %s→%s %s' % (a['cell'].replace('sky130_fd_sc_hd__', ''), a['pin'], a['out'], lab), source_rung='devices',
                           source_ref='sky130_fd_pr nfet_01v8 + pfet_01v8_hvt (tt BSIM4, run here)', target_rung='standard-cells', target_ref='sky130_fd_sc_hd %s' % a['cell'].replace('sky130_fd_sc_hd__', ''),
                           characteristic='propagation_delay', method='ngspice transient on the schematic netlist', conditions_json=json.dumps(dict(rep['conditions'], liberty_ps=v['liberty'], delta_pct=v['delta_pct'], ties=a['ties'])),
                           result=v['ours'] / 1000.0, units='ns', mapping_status='validated' if abs(v['delta_pct']) <= 25 else 'implemented', evidence_level='simulated', evidence_ref=ev,
                           notes='ours %.2f ps vs the Liberty %.2f ps (%+.1f %%): schematic netlist (no extracted parasitics) vs the foundry\'s extracted characterization — the gap is reported, not tuned' % (v['ours'], v['liberty'], v['delta_pct'])))
    return [], chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        cells = sys.argv[sys.argv.index('--cells') + 1].split(',') if '--cells' in sys.argv else None
        rep = run(cells)
        print(json.dumps({'summary': rep['summary'], 'arcs': [{'cell': a['cell'], 'pin': a['pin'], 'compare': a['compare']} for a in rep['arcs']]}, indent=1))
    else:
        print(json.dumps(report()['summary'], indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod3_devices run')
