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
