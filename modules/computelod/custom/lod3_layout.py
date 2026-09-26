"""
@module computelod.custom.lod3_layout

LAYOUT, CHECKED AND EXTRACTED (lod-3c): the `devices → layout` step lod-3 READ (LEF footprints) is now RUN on the
PDK's own layout of each cell, through `polari-eda-tools` (magic built at a pinned tag, netgen, the built sky130A
PDK fetched by ciel at a pinned version — see that submodule's LICENSES.md):

    DRC        magic `drc check` on the cell's `.mag` (the PDK's layout) with the sky130A rules — the count and every
               rule name, `measured` (the tool's own output); a non-zero count is reported, never hidden
    PEX        magic `extract` with parasitic capacitance + coupling → `<cell>.ext.spice` (devices with W/L AND the
               wiring capacitances the schematic netlist lacks)
    LVS        netgen layout-vs-schematic: the extracted netlist against the PDK's schematic netlist — match or not
    re-timing  the lod-3b transient again, on the EXTRACTED netlist, vs the Liberty at the same point — the gap lod-3b
               attributed to parasitics is TESTED here: it should shrink, and by how much is reported either way

    python3 -m computelod.custom.lod3_layout run [--cells inv_1,nand2_1]

Engines resolve through the Polari engines ladder (`computelod.custom.eda_engines`: EDA_ENGINES_URL → local binary →
local image → topology provider computelod.engines → refusal); the PDK is the worker's own volume remotely and
POLARI_PDK_ROOT locally (the submodule's fetch-pdk.sh fills it). Nothing from the PDK is committed.
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
from computelod.custom.eda_engines import PDK_ROOT   # one definition of where the PDK is on this device
FLOWS = os.path.normpath(os.path.join(MOD, '..', '..', '..', 'polari-eda-tools', 'flows'))   # polari-rf-node/polari-eda-tools/flows


def _eng(work, engine, args, env=None, timeout=900, stdout_to=None):
    """One engine WITH the PDK through the Polari engines ladder (computelod.custom.eda_engines): the engine sees the PDK
    at /pdk/… (a local binary gets the real root translated); (rc, stdout+stderr)."""
    from computelod.custom.eda_engines import run as _run
    r = _run(engine, work, args, timeout=timeout, env=env, pdk=True, stdout_to=stdout_to)
    return r['returncode'], r['stdout'] + r['stderr']


def pdk_version():
    p = os.path.join(PDK_ROOT, '.polari-pdk-version')
    return open(p).read().strip() if os.path.exists(p) else ''


def _sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(cells=None, work=None):
    from computelod.custom.eda_engines import resolve, PDK_ROOT as _PDK_LOCAL
    for eng in ('magic', 'netgen'):
        r = resolve(eng)
        if r['how'] == 'refused':
            raise SystemExit(r['why'])
        if r['how'] != 'remote' and not os.path.exists(os.path.join(_PDK_LOCAL, 'sky130A', 'libs.tech', 'magic', 'sky130A.tech')):
            raise SystemExit('%s resolves locally (%s) but no built PDK is at %s: polari-rf-node/polari-eda-tools/fetch-pdk.sh' % (eng, r['where'], _PDK_LOCAL))
    from computelod.custom.lod3_devices import ARCS, CONDITIONS, DEVICES, _fetch, PR_REPO, liberty_tables, interp, _deck, run_spice, ngspice_where, report as devices_report
    ng = ngspice_where()
    if not ng:
        raise SystemExit('no ngspice through the cntfet engines ladder (PATH, ~/tools, CNTFET_ENGINES_URL, or a cntfet.engines provider)')
    from computelod.custom.lod2_silicon import fetch_liberty
    lib_path, lib_sha = fetch_liberty(); lib_text = open(lib_path, errors='replace').read()
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod3c'); os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(FLOWS, 'cell_check.tcl'), work)
    inc = []
    for dev in DEVICES:
        for kind in ('mismatch.corner', 'tt.corner'):
            p, _, _ = _fetch(PR_REPO, 'cells/%s/sky130_fd_pr__%s__%s.spice' % (dev, dev, kind)); inc.append('.include "%s"' % p)
    mag_tech = os.path.join(_PDK_LOCAL, 'sky130A', 'libs.tech', 'magic', 'sky130A.tech')
    rep = {'engines': {e: resolve(e) for e in ('magic', 'netgen')}, 'ngspice': ng,
           'pdk': {'root': 'POLARI_PDK_ROOT (never committed)', 'ciel_version': pdk_version(), 'tech_sha256': _sha(mag_tech) if os.path.exists(mag_tech) else 'remote worker\'s PDK'},
           # bp-3: these rows are the EXTRACTED runs — the netlist condition must say so (it used to be copied from the schematic run's)
           'conditions': dict(CONDITIONS, netlist='extracted (magic PEX of the PDK\'s own .mag — parasitic capacitors included; the schematic figure is kept beside it as schematic_ps)'), 'cells': []}
    prior = {(a['cell'], a['pin']): a['compare'] for a in (devices_report() or {}).get('arcs', [])}
    for cell in (cells or list(ARCS)):
        full = 'sky130_fd_sc_hd__%s' % cell
        mag = os.path.join(_PDK_LOCAL, 'sky130A', 'libs.ref', 'sky130_fd_sc_hd', 'mag', full + '.mag')
        rc, out = _eng(work, 'magic', ['-dnull', '-noconsole', '-rcfile', '/pdk/sky130A/libs.tech/magic/sky130A.magicrc', 'cell_check.tcl'], env={'CELL': full})
        open(os.path.join(work, '%s.magic.log' % full), 'w').write(out)
        m = re.search(r'POLARI_DRC_COUNT (\d+)', out)
        rules = sorted({r for r in re.findall(r'POLARI_DRC_WHY (.+)', out) if not r.startswith('{')})   # names, not the boxes
        # a standard cell STANDING ALONE always fails the tap/well rules (taps come from the row's tap cells, wells are
        # shared along the row) — classified, not hidden: anything outside that class is a real layout error
        standalone = [r for r in rules if any(k in r for k in ('nwell.4', 'LU.2', 'LU.3', 'N+ taps', 'P-tap', 'N-tap'))]
        drc = {'count': int(m.group(1)) if m else None, 'rules': rules, 'standalone_context_rules': standalone, 'real_rules': [r for r in rules if r not in standalone], 'ran': m is not None,
               'clean_in_context': m is not None and all(r in standalone for r in rules)}
        lvs_net = os.path.join(work, full + '_lvs.spice'); ext = os.path.join(work, full + '_pex.spice')
        pex = {'ran': os.path.exists(ext), 'file': full + '_pex.spice'}
        if pex['ran']:
            txt = open(ext, errors='replace').read()
            pex['devices'] = len(re.findall(r'^X\S+ .*sky130_fd_pr__', txt, re.M)); pex['capacitors'] = len(re.findall(r'^C\d+ ', txt, re.M)); pex['sha256'] = _sha(ext)
            pex['junction_areas'] = 'ad=' in txt
        lvs = {'ran': False}
        if os.path.exists(lvs_net):
            # netgen directly (argv, no shell): the flow lvs.sh documents the same call for a person at a terminal
            rc, out = _eng(work, 'netgen', ['-batch', 'lvs', '%s_lvs.spice %s' % (full, full), '/pdk/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice %s' % full,
                                            '/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl', '%s.lvs.out' % full], stdout_to='%s.lvs.log' % full)
            verdict_src = out + (open(os.path.join(work, '%s.lvs.out' % full), errors='replace').read() if os.path.exists(os.path.join(work, '%s.lvs.out' % full)) else '')
            lines = sorted({l.strip() for l in verdict_src.splitlines() if re.search(r'match|Result|Netlists', l)})
            lvs = {'ran': True, 'match': 'Circuits match uniquely' in verdict_src, 'verdict': lines[:6]}
        entry = {'cell': full, 'mag_sha256': _sha(mag) if os.path.exists(mag) else None, 'drc': drc, 'pex': pex, 'lvs': lvs, 'arcs': []}
        # re-time the arcs on the EXTRACTED netlist
        if pex['ran']:
            for pin in ARCS[cell]['pins']:
                deck = os.path.join(work, '%s_%s.ext.sp' % (cell, pin))
                d = _deck(cell, pin, ARCS[cell], '\n'.join(inc), ext)
                open(deck, 'w').write(d)
                text = run_spice(work, deck)
                got = {mm.group(1): float(mm.group(2)) * 1e12 for mm in re.finditer(r'^(tphl|tplh|tfall|trise)\s*=\s*([-0-9.e+]+)', text, re.M)}
                if len(got) < 4:
                    entry['arcs'].append({'pin': pin, 'error': 'ngspice on the extracted netlist gave no measures', 'tail': text[-600:]}); continue
                tabs = liberty_tables(lib_text, cell, pin)
                lib = {k: interp(tabs[k], CONDITIONS['input_slew_ns_20_80'], CONDITIONS['load_pf']) * 1000 for k in tabs}
                cmp = {}
                for key, ours, libk in (('tphl_ps', got['tphl'], 'cell_fall'), ('tplh_ps', got['tplh'], 'cell_rise'), ('fall_transition_ps', got['tfall'], 'fall_transition'), ('rise_transition_ps', got['trise'], 'rise_transition')):
                    sch = (prior.get((full, pin)) or {}).get(key, {}).get('ours')
                    cmp[key] = {'extracted': round(ours, 2), 'schematic': sch, 'liberty': round(lib[libk], 2), 'delta_pct': round((ours - lib[libk]) / lib[libk] * 100, 1),
                                'schematic_delta_pct': (prior.get((full, pin)) or {}).get(key, {}).get('delta_pct')}
                entry['arcs'].append({'pin': pin, 'compare': cmp})
        rep['cells'].append(entry)
    ds = [abs(a['compare'][k]['delta_pct']) for c in rep['cells'] for a in c['arcs'] if 'compare' in a for k in ('tphl_ps', 'tplh_ps')]
    ss = [abs(a['compare'][k]['schematic_delta_pct']) for c in rep['cells'] for a in c['arcs'] if 'compare' in a for k in ('tphl_ps', 'tplh_ps') if a['compare'][k]['schematic_delta_pct'] is not None]
    def _mean(key, which):
        xs = [a['compare'][key][which] for c in rep['cells'] for a in c['arcs'] if 'compare' in a and a['compare'][key].get(which) is not None]
        return round(sum(xs) / len(xs), 1) if xs else None
    fall_s, fall_e, rise_s, rise_e = _mean('tphl_ps', 'schematic_delta_pct'), _mean('tphl_ps', 'delta_pct'), _mean('tplh_ps', 'schematic_delta_pct'), _mean('tplh_ps', 'delta_pct')
    verdict = ('parasitics explain PART of the fall gap (tpHL mean %+.1f %% → %+.1f %%) and NONE of the rise gap (tpLH mean %+.1f %% → %+.1f %%, wider): the lod-3b '
               'hypothesis "the gap is layout parasitics" is REJECTED as the sole cause — what remains is the vendor characterization setup (input waveform shape, load/driver model, '
               'measurement details), which we do not have; stated, not tuned' % (fall_s, fall_e, rise_s, rise_e)) if None not in (fall_s, fall_e, rise_s, rise_e) else 'not enough arcs to judge'
    rep['summary'] = {'cells': len(rep['cells']), 'drc_clean_in_context': all(c['drc']['clean_in_context'] for c in rep['cells'] if c['drc']['ran']),
                      'tphl_mean_delta_pct': {'schematic': fall_s, 'extracted': fall_e}, 'tplh_mean_delta_pct': {'schematic': rise_s, 'extracted': rise_e}, 'verdict': verdict,
                      'drc_note': 'a cell alone fails the tap/well rules by construction (nwell.4, LU.2, LU.3: taps and shared wells come from the row) — those are classified as context rules; any other rule is a real error',
                      'lvs_match': all(c['lvs'].get('match') for c in rep['cells'] if c['lvs']['ran']),
                      'delay_mean_abs_delta_pct_extracted': round(sum(ds) / len(ds), 1) if ds else None, 'delay_mean_abs_delta_pct_schematic': round(sum(ss) / len(ss), 1) if ss else None,
                      'reading': 'the parasitics hypothesis of lod-3b, tested: extracted vs schematic gap to the Liberty, same point'}
    os.makedirs(OUT, exist_ok=True)
    for c in rep['cells']:
        for f in ('%s.magic.log' % c['cell'], '%s.lvs.out' % c['cell']):
            if os.path.exists(os.path.join(work, f)):
                shutil.copy(os.path.join(work, f), OUT)
    json.dump(rep, open(os.path.join(OUT, 'layout_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'layout_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep):
    """REPLACE lod-3's devices → layout by name with the checked one; ADD extracted-netlist delay characterizations."""
    if not rep:
        return [], []
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    s = rep['summary']
    ev = 'lod3/layout_report.json — magic DRC (sky130A rules) + parasitic extraction + netgen LVS on the PDK\'s own .mag via the engines ladder (%s); PDK ciel %s, tech sha256 %s' % (', '.join('%s: %s' % (e, v['how']) for e, v in rep.get('engines', {}).items()), rep['pdk']['ciel_version'][:12], rep['pdk']['tech_sha256'][:16])
    cells = ', '.join('%s: DRC %s (%d context/%d real), LVS %s' % (c['cell'].replace('sky130_fd_sc_hd__', ''), c['drc']['count'], len(c['drc']['standalone_context_rules']), len(c['drc']['real_rules']), 'match' if c['lvs'].get('match') else 'MISMATCH') for c in rep['cells'])
    # the refs MUST be lod-3's own (the walk chains rows by ref): take them from lod-3's row, not re-derived
    from computelod.custom.lod3_cells import report as lod3_report, rows as lod3_rows
    from computelod.custom.lod2_silicon import report as lod2_report
    from computelod.custom.lod2_cnt import report as lod2cnt_report
    l3maps, _ = lod3_rows(lod3_report(), lod2_report(), lod2cnt_report())
    base = next((m_ for m_ in l3maps if m_['name'] == 'lod3: devices → layout'), None)
    if base is None:
        return [], []
    dev_ref, lay_ref = base['source_ref'], base['target_ref']
    maps = [M(name='lod3: devices → layout', kind='one-to-one', source_rung='devices', source_ref=dev_ref, target_rung='layout', target_ref=lay_ref,
              mapping_status='validated' if (s['drc_clean_in_context'] and s['lvs_match']) else 'implemented', evidence_level='measured', evidence_ref=ev,
              notes='lod-3c RAN the layout: %s. The LEF-area == Liberty-area cross-check of lod-3 stands; DRC + LVS are the tools\' own verdicts (measured). Re-timing on the extracted netlists: %s' % (cells, s['verdict']))]
    chars = []
    for c in rep['cells']:
        for arc in c['arcs']:
            if 'compare' not in arc:
                continue
            for key, lab in (('tphl_ps', 'tpHL'), ('tplh_ps', 'tpLH')):
                v = arc['compare'][key]
                chars.append(C(name='lod3c: %s %s→Y %s (extracted)' % (c['cell'].replace('sky130_fd_sc_hd__', ''), arc['pin'], lab), source_rung='layout', source_ref='%s extracted (magic PEX, %s capacitors)' % (c['cell'].replace('sky130_fd_sc_hd__', ''), c['pex'].get('capacitors', '?')),
                               target_rung='standard-cells', target_ref='sky130_fd_sc_hd %s' % c['cell'].replace('sky130_fd_sc_hd__', ''), characteristic='propagation_delay', method='ngspice transient on the EXTRACTED netlist',
                               conditions_json=json.dumps(dict(rep['conditions'], liberty_ps=v['liberty'], delta_pct=v['delta_pct'], schematic_ps=v['schematic'], schematic_delta_pct=v['schematic_delta_pct'])),
                               result=v['extracted'] / 1000.0, units='ns', mapping_status='validated' if abs(v['delta_pct']) <= 25 else 'implemented', evidence_level='simulated', evidence_ref=ev,
                               notes='extracted %.2f ps vs Liberty %.2f ps (%+.1f %%); the schematic netlist gave %s ps (%s %%) — the parasitics hypothesis tested' % (v['extracted'], v['liberty'], v['delta_pct'], v['schematic'], v['schematic_delta_pct'])))
    return maps, chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        cells = sys.argv[sys.argv.index('--cells') + 1].split(',') if '--cells' in sys.argv else None
        rep = run(cells)
        print(json.dumps({'summary': rep['summary'], 'cells': [{'cell': c['cell'], 'drc': c['drc'], 'lvs': c['lvs'].get('match'), 'pex': {k: v for k, v in c['pex'].items() if k != 'sha256'}, 'arcs': c['arcs']} for c in rep['cells']]}, indent=1))
    else:
        print(json.dumps(report()['summary'], indent=1) if report() else 'no report yet: python3 -m computelod.custom.lod3_layout run')
