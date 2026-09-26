"""
@module computelod.custom.lod2_compare

THE TWO LIBERTIES COMPARED HONESTLY (lod-2c, 2026-09-26; plan §H.3). lod-2 timed the adder on SKY130 at ITS Liberty point
(1.8 V, 25 °C, 14.6 fF, 50 ps) and lod-2b on our CNT library at ITS point (0.6 V, 300 K, 41.65 aF, 1.02 ps) — two numbers
that must never be read as a ranking. This flow puts the SAME six cells side by side under the SAME conditions, twice:

    view `cnt-point`   both libraries at the CNT library's characterized point (0.6 V · 300 K · load 41.654 aF · slew
                       1.0178 ps 20–80 %): the CNT number is read from its Liberty (an exact grid point, no interpolation);
                       the SKY130 number is SIMULATED here — ngspice on the PDK's schematic netlists at 0.6 V, the lod-3b/3d
                       decks with the conditions overridden (there is no 0.6 V SKY130 Liberty to cross-check against).
                       Expect SKY130's hvt p device (Vt_sat 0.64 V, lod-4c) to be in subthreshold at |Vgs| = 0.6 V: the
                       rises take tens of ns. That is the point: 0.6 V is not the regime those cells were built for.
    view `own-fo4`     each library at its OWN nominal Vdd, loaded by four of its own inverter inputs (FO4), driven by
                       the slew its own FO4 inverter produces (iterated twice from a start value; both stated): the
                       classic technology-intrinsic comparison. SKY130 1.8 V / 4 × 2.302 fF; CNT 0.6 V / 4 × 10.4 aF.

Per cell the WORST arc delay (max over its arcs of tpHL, tpLH) and the mean are kept; the twins are inv_1↔INVX1,
nand2_1↔NAND2X1, nor2_1↔NOR2X1, xor2_1↔XOR2X1, xnor2_1↔XNOR2X1, o21ai_0↔OAI21X1 (same Boolean function; pins A1/A2/B1 ↔
A/B/C). AREA is REFUSED for the CNT cells: no layout, no design rules for the aligned-CNT process exist in this instance —
a "layout model" would be an invention; the SKY130 areas are the Liberty's. Every SKY130 number here is `simulated`
(schematic netlist — lod-3c showed extraction moves delays by 5–15 % at 1.8 V; not re-run at 0.6 V); every CNT number is
`simulated` (a Liberty we characterized over a derived device, intrinsic-grade, standin parasitics).

    python3 -m computelod.custom.lod2_compare run [--cells inv_1,nand2_1]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod2')
CNT_LIB = os.path.join(OUT, 'cnt', 'polari_cnt_lib.lib')
#: sky130 cell ↔ CNT cell with the same Boolean function
TWINS = [('inv_1', 'INVX1'), ('nand2_1', 'NAND2X1'), ('nor2_1', 'NOR2X1'), ('xor2_1', 'XOR2X1'), ('xnor2_1', 'XNOR2X1'), ('o21ai_0', 'OAI21X1')]
#: the CNT library's characterized point (lod-2b): Liberty grid slew index 1, load index 2 (= 4 × INVX1 input, FO4-like)
CNT_POINT = {'voltage_v': 0.6, 'temperature_c': 26.85, 'temperature_note': '300 K, the CNT characterization temperature', 'load_ff': 0.041654, 'input_slew_ps_20_80': 1.0178}
#: transient window for SKY130 at 0.6 V (subthreshold p devices: rises of tens of ns) — edges at 1 ns and 401 ns, 2 ps steps
SLOW_WINDOW = {'t_edges_ns': (1.0, 401.0), 't_end_ns': 801.0, 'tran_step_ns': 0.002}
FO4_START_SLEW_PS = {'sky130': 50.0, 'cnt': 1.0178}


# ---------------------------------------------------------------- Liberty reading (both libraries, normalised to ps / fF)
def _cell_block(text, marker):
    i = text.index(marker)
    j = text.find('\n  cell (', i + 10)
    j2 = text.find('\n    cell ("', i + 10)
    ends = [k for k in (j, j2) if k > 0]
    return text[i:min(ends)] if ends else text[i:]


def _tables(seg):
    out = {}
    for name in ('cell_fall', 'cell_rise', 'fall_transition', 'rise_transition'):
        k = seg.find(name + ' (')
        if k < 0:
            continue
        s = seg[k:k + 1500]
        idx1 = [float(x) for x in re.search(r'index_1\s*\("([^"]+)"\)', s).group(1).split(',')]
        idx2 = [float(x) for x in re.search(r'index_2\s*\("([^"]+)"\)', s).group(1).split(',')]
        vals = re.search(r'values\s*\((.*?)\);', s, re.S).group(1)
        out[name] = (idx1, idx2, [[float(v) for v in r.split(',')] for r in re.findall(r'"([^"]+)"', vals)])
    return out


def timing_groups(text, marker):
    """[{related_pin, timing_sense, when, tables}] of one cell — every `timing () {` group of its output pin(s)."""
    blk = _cell_block(text, marker)
    starts = [m.start() for m in re.finditer(r'timing \(\) \{', blk)]
    groups = []
    for n, s in enumerate(starts):
        seg = blk[s:starts[n + 1] if n + 1 < len(starts) else len(blk)]
        g = lambda key: (re.search(key + r'\s*:\s*"?([^";\n]+)', seg) or [None, None])[1]
        groups.append({'related_pin': g('related_pin'), 'timing_sense': (g('timing_sense') or '').strip(), 'when': g('when'), 'tables': _tables(seg)})
    return [g for g in groups if g['tables']]


def cell_area(text, marker):
    m = re.search(r'area\s*:\s*([\d.]+)', _cell_block(text, marker))
    return float(m.group(1)) if m else None


def pin_cap(text, marker, pin):
    m = re.search(r'pin\s*\(\s*"?%s"?\s*\)\s*\{[^{}]*?capacitance\s*:\s*([\d.]+)' % re.escape(pin), _cell_block(text, marker), re.S)
    return float(m.group(1)) if m else None


def units(text):
    tu = re.search(r'time_unit\s*:\s*"([^"]+)"', text).group(1)
    cu = re.search(r'capacitive_load_unit\s*\(([^)]+)\)', text).group(1)
    t_ps = {'1ns': 1000.0, '1ps': 1.0}[tu.strip()]
    c_ff = 1000.0 if 'pf' in cu.lower() else 1.0
    return t_ps, c_ff


def read_point(text, marker, slew_ps, load_ff, t_ps, c_ff):
    """Every arc of the cell at (slew, load): {arc: {tphl_ps, tplh_ps, rise_tr_ps, fall_tr_ps}} — bilinear inside the grid, REFUSED outside it."""
    from computelod.custom.lod3_devices import interp
    out = {}
    for g in timing_groups(text, marker):
        i1, i2, _ = g['tables']['cell_fall']
        s_u, l_u = slew_ps / t_ps, load_ff / c_ff
        if not (i1[0] - 1e-12 <= s_u <= i1[-1] + 1e-12 and i2[0] - 1e-12 <= l_u <= i2[-1] + 1e-12):
            out['%s%s' % (g['related_pin'], (' when ' + g['when']) if g['when'] else '')] = {'refused': 'outside the characterized grid (slew %s–%s, load %s–%s in the Liberty\'s units)' % (i1[0], i1[-1], i2[0], i2[-1])}
            continue
        out['%s%s' % (g['related_pin'], (' when ' + g['when']) if g['when'] else '')] = {
            'tphl_ps': interp(g['tables']['cell_fall'], s_u, l_u) * t_ps, 'tplh_ps': interp(g['tables']['cell_rise'], s_u, l_u) * t_ps,
            'fall_tr_ps': interp(g['tables']['fall_transition'], s_u, l_u) * t_ps, 'rise_tr_ps': interp(g['tables']['rise_transition'], s_u, l_u) * t_ps, 'sense': g['timing_sense']}
    return out


def summarize(arcs):
    ok = {k: v for k, v in arcs.items() if 'tphl_ps' in v}
    if not ok:
        return {'arcs': 0, 'refused': len(arcs), 'worst_ps': None}
    hl = [v['tphl_ps'] for v in ok.values()]; lh = [v['tplh_ps'] for v in ok.values()]
    tr = [v[k] for v in ok.values() for k in ('fall_tr_ps', 'rise_tr_ps') if v.get(k) is not None]
    return {'arcs': len(ok), 'refused': len(arcs) - len(ok), 'tphl_worst_ps': round(max(hl), 3), 'tplh_worst_ps': round(max(lh), 3), 'worst_ps': round(max(hl + lh), 3),
            'mean_ps': round(sum(hl + lh) / len(hl + lh), 3), 'mean_transition_ps': round(sum(tr) / len(tr), 3) if tr else None,
            'transitions_unavailable': sum(1 for v in ok.values() if v.get('transition_note'))}


# ---------------------------------------------------------------- SKY130 by simulation at a given point
def sky_point(cells, slew_ps, load_ff, vdd, temp_c, window, work, inc, lib_text=None):
    """{cell: {arc_label: {...}}} — ngspice on the schematic netlists with the conditions overridden."""
    from computelod.custom.lod3_devices import arcs_of, _deck, _fetch, SC_REPO, run_spice
    cond = dict({'voltage_v': vdd, 'temperature_c': temp_c, 'load_pf': load_ff / 1000.0, 'input_slew_ns_20_80': slew_ps / 1000.0}, **(window or {}))
    out = {}
    for cell in cells:
        cp, _, _ = _fetch(SC_REPO, 'cells/%s/sky130_fd_sc_hd__%s.spice' % (cell.rsplit('_', 1)[0], cell))
        arcs = {}
        for arc in arcs_of(cell):
            deck = os.path.join(work, '%s_%s_%sV.sp' % (cell, arc['label'].replace('@', '_').replace(',', '_'), str(vdd).replace('.', 'p')))
            open(deck, 'w').write(_deck(cell, arc, '\n'.join(inc), cp, cond))
            got, text, tries = {}, '', 0
            while tries < 2:   # a 400k-point deck can be KILLED on a loaded machine (systemd-oomd; empty output, no measures): one retry, stated
                tries += 1
                text = run_spice(work, deck, timeout=1800)
                got = {m.group(1): float(m.group(2)) * 1e12 for m in re.finditer(r'^(tphl|tplh|tfall|trise)\s*=\s*([-0-9.e+]+)', text, re.M)}
                if got:
                    break
            if not ('tphl' in got and 'tplh' in got) or got['tphl'] < 0 or got['tplh'] < 0:
                arcs[arc['label']] = {'refused': ('ngspice returned no measures at all after %d tries (killed or failed — the last 300 characters of its output follow); not a property of the cell' % tries) if not got
                                      else 'the delay edge did not finish inside the %s ns window, or was not found' % cond.get('t_end_ns', 5.0), 'got': got, 'ngspice_tail': text[-300:], 'tries': tries}
                continue
            entry = {'tphl_ps': got['tphl'], 'tplh_ps': got['tplh'], 'fall_tr_ps': got.get('tfall'), 'rise_tr_ps': got.get('trise'), 'sense': arc['sense']}
            # a transition measure can come back negative when the output is non-monotonic in a degenerate regime (a subthreshold
            # xor2 at 0.6 V dips through 20 % on its way up): the DELAYS stand, the transition is marked unavailable, said so
            for k in ('fall_tr_ps', 'rise_tr_ps'):
                if entry[k] is None or entry[k] < 0:
                    entry[k] = None; entry['transition_note'] = 'transition measure unavailable (non-monotonic output edge in this regime; delays measured)'
            arcs[arc['label']] = entry
        out[cell] = arcs
    return out


def run(cells=None, work=None):
    from computelod.custom.lod3_devices import _fetch, PR_REPO, DEVICES, ngspice_where, CONDITIONS as L3B
    from computelod.custom.lod2_silicon import fetch_liberty
    ng = ngspice_where()
    if not ng:
        raise SystemExit('no ngspice through the cntfet engines ladder (PATH, ~/tools, CNTFET_ENGINES_URL, or a cntfet.engines provider)')
    if not os.path.exists(CNT_LIB):
        raise SystemExit('no CNT Liberty at %s — run lod2_cnt first' % CNT_LIB)
    twins = [t for t in TWINS if not cells or t[0] in cells]
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod2c'); os.makedirs(work, exist_ok=True)
    inc = []
    for dev in DEVICES:
        for kind in ('mismatch.corner', 'tt.corner'):
            p, _, _ = _fetch(PR_REPO, 'cells/%s/sky130_fd_pr__%s__%s.spice' % (dev, dev, kind)); inc.append('.include "%s"' % p)
    sky_path, sky_sha = fetch_liberty(); sky = open(sky_path, errors='replace').read(); cnt = open(CNT_LIB, errors='replace').read()
    s_t, s_c = units(sky); c_t, c_c = units(cnt)
    sky_marker = lambda c: 'cell ("sky130_fd_sc_hd__%s")' % c
    cnt_marker = lambda c: 'cell (%s)' % c
    import hashlib
    rep = {'tool': 'ngspice-46 (%s) for SKY130 at the CNT point and at FO4; both Liberties READ for the rest' % ng, 'twins': twins, 'sky130_liberty_sha256': sky_sha,
           'cnt_liberty_sha256': hashlib.sha256(cnt.encode()).hexdigest(), 'views': {}, 'area': {}, 'cells': {}}
    # ---- view 1: the CNT point, both libraries
    v1 = {'conditions': dict(CNT_POINT, window_ns=SLOW_WINDOW, sky130_netlist='schematic (PDK cells/*.spice, no extracted parasitics; no 0.6 V Liberty exists to cross-check)', cnt_source='polari_cnt_lib.lib at an exact grid point')}
    sky1 = sky_point([t[0] for t in twins], CNT_POINT['input_slew_ps_20_80'], CNT_POINT['load_ff'], CNT_POINT['voltage_v'], CNT_POINT['temperature_c'], SLOW_WINDOW, work, inc)
    v1['cells'] = {}
    for s_cell, c_cell in twins:
        cnt1 = read_point(cnt, cnt_marker(c_cell), CNT_POINT['input_slew_ps_20_80'], CNT_POINT['load_ff'], c_t, c_c)
        v1['cells'][s_cell] = {'sky130': dict(summarize(sky1[s_cell]), arcs_detail=sky1[s_cell]), 'cnt': dict(summarize(cnt1), cell=c_cell, arcs_detail=cnt1)}
        a, b = v1['cells'][s_cell]['sky130']['worst_ps'], v1['cells'][s_cell]['cnt']['worst_ps']
        v1['cells'][s_cell]['ratio_sky_over_cnt'] = round(a / b, 1) if a and b else None
    rep['views']['cnt-point'] = v1
    # ---- view 2: each at its own nominal FO4 (load = 4 × own inverter input; slew iterated from a start value, twice)
    sky_cin = pin_cap(sky, sky_marker('inv_1'), 'A') * s_c; cnt_cin = pin_cap(cnt, cnt_marker('INVX1'), 'A') * c_c
    fo4 = {'sky130': {'vdd_v': 1.8, 'temperature_c': 25.0, 'load_ff': round(4 * sky_cin, 4), 'inverter_cin_ff': round(sky_cin, 4), 'slew_iterations_ps': [FO4_START_SLEW_PS['sky130']]},
           'cnt': {'vdd_v': 0.6, 'temperature_c': 26.85, 'load_ff': round(4 * cnt_cin, 6), 'inverter_cin_ff': round(cnt_cin, 6), 'slew_iterations_ps': [FO4_START_SLEW_PS['cnt']]}}
    for _ in range(2):   # the FO4 inverter's own output transition becomes the next input slew
        s = fo4['sky130']['slew_iterations_ps'][-1]
        inv = sky_point(['inv_1'], s, fo4['sky130']['load_ff'], 1.8, 25.0, None, work, inc)['inv_1']
        fo4['sky130']['slew_iterations_ps'].append(round(summarize(inv)['mean_transition_ps'], 3))
        s = fo4['cnt']['slew_iterations_ps'][-1]
        inv = read_point(cnt, cnt_marker('INVX1'), s, fo4['cnt']['load_ff'], c_t, c_c)
        sm = summarize(inv)
        fo4['cnt']['slew_iterations_ps'].append(round(sm['mean_transition_ps'], 4) if sm.get('mean_transition_ps') else s)
    fo4['sky130']['input_slew_ps_20_80'] = fo4['sky130']['slew_iterations_ps'][-1]; fo4['cnt']['input_slew_ps_20_80'] = fo4['cnt']['slew_iterations_ps'][-1]
    fo4['note'] = 'FO4: each cell drives four of its own library\'s inverter inputs and is driven by the slew its own FO4 inverter produces (two iterations from the start value; all values kept) — the intrinsic-speed comparison, each library at its own nominal voltage'
    sky2 = sky_point([t[0] for t in twins], fo4['sky130']['input_slew_ps_20_80'], fo4['sky130']['load_ff'], 1.8, 25.0, None, work, inc)
    v2 = {'conditions': fo4, 'cells': {}}
    for s_cell, c_cell in twins:
        cnt2 = read_point(cnt, cnt_marker(c_cell), fo4['cnt']['input_slew_ps_20_80'], fo4['cnt']['load_ff'], c_t, c_c)
        v2['cells'][s_cell] = {'sky130': dict(summarize(sky2[s_cell]), arcs_detail=sky2[s_cell]), 'cnt': dict(summarize(cnt2), cell=c_cell, arcs_detail=cnt2)}
        a, b = v2['cells'][s_cell]['sky130']['worst_ps'], v2['cells'][s_cell]['cnt']['worst_ps']
        v2['cells'][s_cell]['ratio_sky_over_cnt'] = round(a / b, 1) if a and b else None
    rep['views']['own-fo4'] = v2
    # ---- the SKY130 Liberty at its own point (lod-2), for the reading — read, not simulated
    v3 = {'conditions': {'voltage_v': 1.8, 'temperature_c': 25.0, 'load_ff': L3B['load_pf'] * 1000, 'input_slew_ps_20_80': L3B['input_slew_ns_20_80'] * 1000, 'source': 'sky130_fd_sc_hd__tt_025C_1v80.lib, bilinear at the lod-2 point'}, 'cells': {}}
    for s_cell, _ in twins:
        v3['cells'][s_cell] = dict(summarize(read_point(sky, sky_marker(s_cell), v3['conditions']['input_slew_ps_20_80'], v3['conditions']['load_ff'], s_t, s_c)))
    rep['views']['sky130-liberty-point'] = v3
    # ---- area: SKY130 from the Liberty; CNT REFUSED
    rep['area'] = {'sky130_um2': {s: cell_area(sky, sky_marker(s)) for s, _ in twins}, 'cnt_um2': None,
                   'cnt_refused': 'no layout and no design rules exist for the aligned-CNT process in this instance (lod-3: CNT devices → layout is UNRESOLVED); an area from a "layout model" would be invented — refused, stated'}
    # ---- summary
    r1 = [v1['cells'][s]['ratio_sky_over_cnt'] for s, _ in twins if v1['cells'][s]['ratio_sky_over_cnt']]
    r2 = [v2['cells'][s]['ratio_sky_over_cnt'] for s, _ in twins if v2['cells'][s]['ratio_sky_over_cnt']]
    rep['summary'] = {'twins': len(twins), 'cnt_point_ratio_sky_over_cnt': {'min': min(r1) if r1 else None, 'max': max(r1) if r1 else None, 'cells_measured': len(r1)},
                      'own_fo4_ratio_sky_over_cnt': {'min': min(r2) if r2 else None, 'max': max(r2) if r2 else None, 'cells_measured': len(r2)},
                      'sky130_fo4_inverter_worst_ps': v2['cells']['inv_1']['sky130']['worst_ps'] if 'inv_1' in v2['cells'] else None, 'cnt_fo4_inverter_worst_ps': v2['cells']['inv_1']['cnt']['worst_ps'] if 'inv_1' in v2['cells'] else None,
                      'reading': 'at the CNT point (0.6 V) the SKY130 hvt cells are in subthreshold and orders of magnitude slower — not the regime they were built for; at each library\'s own FO4 the ratio is the intrinsic comparison, '
                                 'with the CNT side intrinsic-grade (standin parasitics, no layout, no area) and the SKY130 side a schematic netlist of a fabricated process. Neither view is a ranking of technologies.'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(rep, open(os.path.join(OUT, 'compare_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'compare_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep):
    """Characterizations UP (devices → standard-cells), per twin cell per view per library: the WORST arc delay at the stated point."""
    if not rep:
        return [], []
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    chars = []
    ev = 'lod2/compare_report.json — SKY130 by ngspice on the PDK schematic netlists (models sky130_fd_pr tt), CNT read from polari_cnt_lib.lib (sha256 %s); both Liberties\' units normalised to ps / fF' % rep['cnt_liberty_sha256'][:16]
    for view, tag in (('cnt-point', '@cnt-point'), ('own-fo4', 'FO4')):
        v = rep['views'][view]
        for s_cell, c_cell in rep['twins']:
            e = v['cells'][s_cell]
            for lib, key, src_ref, method, cond_extra in (
                    ('sky130', 'sky130', 'sky130_fd_pr nfet_01v8 + pfet_01v8_hvt (tt BSIM4, run here)', 'ngspice transient on the schematic netlist', {}),
                    ('cnt', 'cnt', 'AlignedCNTFETDevice cnt-aligned-s1 + partner (derived; the CNT Liberty\'s device)', 'CNT Liberty tables (characterized here), read at the point', {})):
                s = e[key]
                if not s.get('worst_ps'):
                    chars.append(C(name='lod2c: %s %s %s' % (lib, s_cell if lib == 'sky130' else c_cell, tag), source_rung='devices', source_ref=src_ref, target_rung='standard-cells',
                                   target_ref=('sky130_fd_sc_hd %s' % s_cell) if lib == 'sky130' else ('polari_cnt_lib %s' % c_cell), characteristic='propagation_delay', method=method, units='ns', result=0.0,
                                   conditions_json=json.dumps(dict(v['conditions'] if view == 'cnt-point' else v['conditions'][key], view=view, refused=s.get('refused'), arcs_detail={k: vv.get('refused', 'ok') for k, vv in s.get('arcs_detail', {}).items()})),
                                   mapping_status='proposed', evidence_level='none', evidence_ref=ev, notes='REFUSED: no arc finished inside the window / inside the grid — stated, not filled in'))
                    continue
                cond = dict(v['conditions'] if view == 'cnt-point' else v['conditions'][key], view=view, tphl_worst_ps=s['tphl_worst_ps'], tplh_worst_ps=s['tplh_worst_ps'], mean_ps=s['mean_ps'], arcs=s['arcs'],
                            twin=(c_cell if lib == 'sky130' else s_cell), ratio_sky_over_cnt=e.get('ratio_sky_over_cnt'))
                if view == 'cnt-point':
                    cond.pop('window_ns', None)
                chars.append(C(name='lod2c: %s %s %s' % (lib, s_cell if lib == 'sky130' else c_cell, tag), source_rung='devices', source_ref=src_ref, target_rung='standard-cells',
                               target_ref=('sky130_fd_sc_hd %s' % s_cell) if lib == 'sky130' else ('polari_cnt_lib %s' % c_cell), characteristic='propagation_delay', method=method, units='ns', result=s['worst_ps'] / 1000.0,
                               conditions_json=json.dumps(cond), mapping_status='implemented', evidence_level='simulated', evidence_ref=ev,
                               notes='%s %s at the %s point: worst arc %s ps (tpHL %s, tpLH %s; mean %s over %d arcs); twin %s. %s' % (
                                   lib, s_cell if lib == 'sky130' else c_cell, view, s['worst_ps'], s['tphl_worst_ps'], s['tplh_worst_ps'], s['mean_ps'], s['arcs'], c_cell if lib == 'sky130' else s_cell,
                                   'SKY130 at 0.6 V: hvt p devices in subthreshold — not a regime the library was built for' if (lib == 'sky130' and view == 'cnt-point') else
                                   ('intrinsic-grade CNT Liberty: standin parasitics, no layout, no area (refused)' if lib == 'cnt' else 'schematic netlist at the library\'s own Vdd; extraction would add 5–15 % (lod-3c)'))))
    return [], chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        cells = sys.argv[sys.argv.index('--cells') + 1].split(',') if '--cells' in sys.argv else None
        rep = run(cells)
        slim = {'summary': rep['summary'], 'fo4': rep['views']['own-fo4']['conditions'],
                'cells': {s: {v: {'sky130': rep['views'][v]['cells'][s]['sky130'].get('worst_ps'), 'cnt': rep['views'][v]['cells'][s]['cnt'].get('worst_ps'), 'ratio': rep['views'][v]['cells'][s].get('ratio_sky_over_cnt')} for v in ('cnt-point', 'own-fo4')} for s, _ in rep['twins']}}
        print(json.dumps(slim, indent=1))
    else:
        r = report()
        print(json.dumps(r['summary'], indent=1) if r else 'no report yet: python3 -m computelod.custom.lod2_compare run')
