"""pcb_kicad_spice_selftest - kxc-3 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): A SPICE DECK FROM OUR OWN ROWS. The deck of an ingested schematic is built from
SchematicSymbol (Sim.* fields) + NetEndpoint (our nets) + the project's own files (directives, model libraries) - KiCad's export is the cross-check.
References (custom/reference/): kicad10_spice_<b>.cir = `kicad-cli sch export netlist --format spice`, kicad10_sim_<b>.json = libngspice's run of that deck
(KiCad 10.0.6 on econ-core, 2026-10-30). Fixtures: simulation/rectifier (.tran, a SPICE-mode source, a diode model file) and simulation/sallen_key (.ac, an
op-amp subcircuit in a library, DC sources) from kicad-demos 9.0.2 (GPL-2+).
Run by pcb_selftest.main().
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2', 'simulation')
REF = os.path.join(HERE, 'custom', 'reference')


def run_kicad_spice(check):
    from electrodevice.custom import ngspice_shared as NS
    from pcb.custom import kicad_read as K
    from pcb.custom import kicad_spice as P

    decks, diffs = {}, {}
    for b in ('rectifier', 'sallen_key'):
        rows = K.read_project(K.read_dir(os.path.join(SIM, b)), b)
        decks[b] = (rows, P.build_deck(rows))
        ours, theirs = decks[b][1]['elements'], P.parse_deck(open(os.path.join(REF, 'kicad10_spice_%s.cir' % b)).read())
        diffs[b] = sorted(k for k in set(ours) | set(theirs) if not (k in ours and k in theirs and ours[k]['nodes'] == theirs[k]['nodes']
                                                                       and ours[k]['value'].split() == theirs[k]['value'].split()))
    check('KXC-3 OUR DECK = KiCad\'s: every element of both demo decks (rectifier 5, sallen_key 8) has KiCad\'s nodes in KiCad\'s order and KiCad\'s value - '
          'diode pins by Sim.Pins (2=1 1=2: anode first), the op-amp\'s five nodes in its .subckt port order (1 2 99 50 45 from ad8051.lib), the SPICE-mode '
          'source\'s SINE(...); the one difference is V1 of sallen_key, where KiCad writes "DC ac=1 AC 1" and we write "DC 0 AC 1"',
          diffs == {'rectifier': [], 'sallen_key': ['V1']} and len(decks['rectifier'][1]['elements']) == 5 and len(decks['sallen_key'][1]['elements']) == 8
          and decks['sallen_key'][1]['elements']['XU1']['nodes'] == ['Net-_U1-+_', '/lowpass', 'VDD', 'VSS', '/lowpass'], diffs)
    r = decks['rectifier'][1]
    check('KXC-3 DIRECTIVES + MODELS from the project files: the schematic\'s ".tran 1u 10m" text is a directive, its commented "*.ac" is not; diode.mod and '
          'ad8051.lib are included by name (the run writes them beside the deck); nothing skipped, no problems',
          r['directives'] == ['.tran 1u 10m'] and r['includes'] == ['diode.mod'] and decks['sallen_key'][1]['includes'] == ['ad8051.lib']
          and not r['skipped'] and not r['problems'] and not decks['sallen_key'][1]['problems'], (r['directives'], r['includes']))
    check('KXC-3 VALUES as KiCad reads them: 1M -> 1Meg (mega - ngspice reads M as milli), 4k7 -> 4.7k, 100nF -> 100n',
          (P.spice_value('1M'), P.spice_value('4k7'), P.spice_value('100nF'), P.spice_value('1k')) == ('1Meg', '4.7k', '100n', '1k'))
    cap = NS.capability()
    if cap['shared_library']:
        ok = True
        for b in ('rectifier', 'sallen_key'):
            rows, d = decks[b]
            res = NS.run(d['deck'], {a['path']: a['content'] for a in rows['KiCadArtifact'] if a['path'] in d['includes']})
            ref = json.load(open(os.path.join(REF, 'kicad10_sim_%s.json' % b)))
            for name, vals in ref['vectors'].items():
                key = 'real' if 'real' in vals else 'mag'
                mine = res.get('vectors', {}).get(name, {}).get(key, [])[::ref['step']]
                ok = ok and len(mine) == len(vals[key]) and all(abs(a - c) <= 1e-9 + 1e-6 * abs(c) for a, c in zip(mine, vals[key]))
        check('KXC-3 OUR DECK RUNS TO KiCad\'s NUMBERS (this host has libngspice): both decks\' results equal the recorded run of KiCad\'s own decks', ok)
    else:
        res = NS.run(r['deck'])
        check('KXC-3 NO SOLVER HERE, SAID: this host has no libngspice, so the run is refused in words (econ-core has it). Recorded there 2026-10-30: our decks '
              'and KiCad\'s gave the same vectors - rectifier max difference 0 over 10008 points, sallen_key 5.6e-15 over 61 frequencies',
              not res['ok'] and 'no ngspice shared library' in res['refused'], res)


def run_spice_runs(check):
    """kxc-3b: a run is KEPT (SpiceRun + one SpiceVector per vector, values verbatim), listed on the Board Details page, and charted in long form."""
    from board.custom import board_details as BD
    from board.board_details_page import BOARD_DETAILS_PAGES, SEED_BOARD_DETAILS_GRAPHS, RUN_GRAPH
    from pcb.custom import spice_runs as SR
    SR._MEM['SpiceRun'].clear()
    SR._MEM['SpiceVector'].clear()
    names = {}
    for b in ('rectifier', 'sallen_key'):
        ref = json.load(open(os.path.join(REF, 'kicad10_sim_%s.json' % b)))
        res = {'ok': True, 'plot': ref['plot'], 'vectors': ref['vectors'], 'library': 'libngspice (KiCad 10.0.6)'}
        names[b] = SR.store(None, b, open(os.path.join(REF, 'kicad10_spice_%s.cir' % b)).read(), res, 'reference', 'econ-core', '2026-10-30T12:00:00+00:00')
    vec = {v['vector']: v for v in SR._MEM['SpiceVector'].values() if v['run'] == names['rectifier']}
    ref = json.load(open(os.path.join(REF, 'kicad10_sim_rectifier.json')))
    check('KXC-3b A RUN IS KEPT: one SpiceRun (plot tran1, 101 points, source reference, host econ-core) + one SpiceVector per vector with the values VERBATIM; '
          'units by ngspice\'s naming - time s (the scale), /rect_out V, v1#branch A; the AC run keeps magnitude AND phase',
          len(vec) == 4 and json.loads(vec['/rect_out']['values_json']) == ref['vectors']['/rect_out']['real'] and vec['time']['role'] == 'scale'
          and (vec['time']['unit'], vec['/rect_out']['unit'], vec['v1#branch']['unit']) == ('s', 'V', 'A')
          and SR._MEM['SpiceRun'][names['rectifier']]['points'] == 101
          and any(v['complex_values'] and json.loads(v['phase_json']) for v in SR._MEM['SpiceVector'].values() if v['run'] == names['sallen_key']), sorted(vec))
    st, c = SR.chart(None, names['rectifier'], 50)
    st2, c2 = SR.chart(None, names['sallen_key'], 2000)
    check('KXC-3b THE CHART: long form (x, y, series) for the named graph pcb-spice-run - each value vector a series labelled with its unit, against the scale; '
          'max 50 points per series -> stride 3 (101 points); the AC run charts magnitude against frequency (Hz); an unknown run is 404 in words',
          st == 200 and c['stride'] == 3 and c['x_unit'] == 's' and sorted({r['series'] for r in c['rows']}) == ['/rect_out (V)', '/signal_in (V)', 'v1#branch (A)']
          and len(c['rows']) == 3 * 34 and st2 == 200 and c2['x_vector'] == 'frequency' and '/lowpass (|V|)' in {r['series'] for r in c2['rows']}
          and SR.chart(None, 'nope', 10)[0] == 404, (st, c.get('stride'), len(c.get('rows', []))))
    refused = SR.store(None, 'rectifier', 'deck', {'ok': False, 'refused': 'no ngspice shared library on this host'}, 'local', 'here')
    runs = BD.part('layers', 'rectifier', 'runs')[0]
    page = BOARD_DETAILS_PAGES[0]
    d = json.loads(page['definition'])
    text = json.dumps(d)
    check('KXC-3b ON THE BOARD DETAILS PAGE: the runs part lists the PCB\'s runs newest first, a REFUSED attempt kept with its reason (and no vectors); the page has a '
          'Simulation tab (runs -> scope run -> vectors + the named-graph-panel over GraphDefinition pcb-spice-run, long form: series = the vector)',
          [r['status'] for r in runs] == ['REFUSED - no ngspice shared library on this host', 'ran'] and SR.chart(None, refused, 10)[0] == 404
          and '/api/pcb/runs/{scope:run}/chart' in text and RUN_GRAPH in text and d['scope_from_query'] == ['board', 'run']
          and json.loads(SEED_BOARD_DETAILS_GRAPHS[0]['definition'])['graphConfig']['seriesDimension'] == 'series', [r['status'] for r in runs])


def run_spice_projection(check):
    """kxc-3c: a run's results projected onto the board's nets (and through them onto a PCB's footholds - the way simulated numbers reach the Bench)."""
    from pcb.custom import kicad_read as K
    from pcb.custom import spice_runs as SR
    SR._MEM['SpiceRun'].clear()
    SR._MEM['SpiceVector'].clear()
    got = {}
    for b in ('rectifier', 'sallen_key'):
        rows = K.read_project(K.read_dir(os.path.join(SIM, b)), b)
        ref = json.load(open(os.path.join(REF, 'kicad10_sim_%s.json' % b)))
        name = SR.store(None, b, 'deck', {'ok': True, 'plot': ref['plot'], 'vectors': ref['vectors']}, 'reference', 'econ-core', '2026-10-30T12:00:00+00:00')
        got[b] = ({r['net']: r for r in SR.projection(None, b, nets=[n['net'] for n in rows['SchematicNet']])[0]}, name, ref)
    rect, name, ref = got['rectifier']
    sk = got['sallen_key'][0]
    out = ref['vectors']['/rect_out']['real']
    check('KXC-3c THE RUN ON THE NETS: each net\'s own node vector summarised - the rectifier\'s /rect_out min / max / final from its transient (= the '
          'vector\'s own numbers), GND 0 V by definition (SPICE node 0), a net the run did not save says so; the AC run gives /lowpass its peak |V| and where; '
          'the run-scoped call finds the board from the run name',
          rect['/rect_out']['max'] == max(out) and rect['/rect_out']['final'] == out[-1] and rect['GND']['max'] == 0.0 and 'by definition' in rect['GND']['basis']
          and 'no vector' in rect['Net-(D1-A)']['basis'] and sk['/lowpass']['unit'] == '|V|' and sk['/lowpass']['at'].endswith('Hz')
          and SR.projection(None, '', name)[0] and SR.projection(None, 'nope')[1].startswith('no finished run'), {k: (v['min'], v['max']) for k, v in rect.items()})


def run_thermal(check):
    """bob-3c / kxc-3d: the first-order thermal view - per-part power from a kept run, the energy balance, the board's mean rise (a stated model)."""
    from pcb.custom import kicad_read as K
    from pcb.custom import spice_runs as SR
    from pcb.custom import thermal as T
    SR._MEM['SpiceRun'].clear()
    SR._MEM['SpiceVector'].clear()
    rows = K.read_project(K.read_dir(os.path.join(SIM, 'rectifier')), 'rectifier')
    ref = json.load(open(os.path.join(REF, 'kicad10_sim_rectifier.json')))
    SR.store(None, 'rectifier', 'deck', {'ok': True, 'plot': ref['plot'], 'vectors': ref['vectors']}, 'reference', 'econ-core', '2026-10-30T12:00:00+00:00')
    parts, why = T.dissipation(None, 'rectifier', rows=rows)
    p = {r['ref']: r for r in parts}
    v = ref['vectors']['/rect_out']['real']
    peak_r2 = max(x * x / 100e3 for x in v)
    check('THERMAL POWER PER PART from the run: R2 (100k across /rect_out) by Ohm\'s law - its peak = max(V^2) / R from the vector itself; V1 by what it '
          'delivers (branch current); C1 0 W on average by definition; D1 and R1 undetermined, each saying why (a diode\'s current / a node the run did not save)',
          not why and abs(p['R2']['peak_w'] - peak_r2) < 1e-15 and p['V1']['avg_w'] > p['R2']['avg_w'] > 0 and p['C1']['avg_w'] == 0.0
          and p['D1']['avg_w'] == -1.0 and 'current' in p['D1']['basis'] and p['R1']['avg_w'] == -1.0, {k: (r['avg_w'], r['basis'][:40]) for k, r in p.items()})
    est, _ = T.estimate(None, 'rectifier', rows=rows)
    est2, _ = T.estimate(None, 'rectifier', rows=rows, pcb={'width_mm': 50.0, 'height_mm': 40.0})
    check('THERMAL ESTIMATE: energy conservation - what V1 delivers minus what the counted parts take = the power in the undetermined parts (D1, R1); a '
          'schematic-only project has no board area, so no rise (said); with a 50 x 40 mm outline dT = P / (h x 2A) at the cited free-air knob h = 10 W/m2K',
          abs(est['unaccounted_w'] - (est['delivered_w'] - est['dissipated_w'])) < 1e-18 and est['unaccounted_w'] > 0 and est['parts_undetermined'] == 'D1, R1'
          and est['delta_t_c'] == -1.0 and 'no PCB outline' in est['basis']
          and abs(est2['delta_t_c'] - est2['dissipated_w'] / (10.0 * 2 * 2000e-6)) < 1e-15 and 'Incropera' in est2['basis'] and 'not a hot-spot map' in est2['basis']
          and T.spice_number('1Meg') == 1e6 and T.spice_number('2m') == 0.002, (est, est2.get('delta_t_c')))
    sk = K.read_project(K.read_dir(os.path.join(SIM, 'sallen_key')), 'sallen_key')
    refa = json.load(open(os.path.join(REF, 'kicad10_sim_sallen_key.json')))
    SR.store(None, 'sallen_key', 'deck', {'ok': True, 'plot': refa['plot'], 'vectors': refa['vectors']}, 'reference', 'econ-core', '2026-10-30T12:00:00+00:00')
    check('THERMAL REFUSES an AC sweep in words (small-signal: it carries no power) and a board with no run',
          'small-signal' in T.dissipation(None, 'sallen_key', rows=sk)[1] and 'no finished run' in T.dissipation(None, 'nope')[1])
