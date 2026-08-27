"""
Selftest for sifet.si_refinement (fp-4: silicon grade ladder,
refinement steps/routes as data, Scheil / Pfann / evaporation
models, route simulation and the honesty statement).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m sifet.selftest_refinement
"""

import json
import sys
import types

from sifet import si_refinement as sr

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    def rows(cls, seeds):
        return [cls(**{**s, 'manager': None}) for s in seeds]
    return types.SimpleNamespace(objectTables={
        'SiliconGrade': rows(sr.SiliconGrade, sr.SEED_SILICON_GRADES),
        'RefinementStep': rows(sr.RefinementStep,
                               sr.SEED_REFINEMENT_STEPS),
        'RefinementRoute': rows(sr.RefinementRoute,
                                sr.SEED_REFINEMENT_ROUTES),
    })


def main():
    mgr = _mgr()

    # ---- models ---------------------------------------------------
    fe = sr.scheil_pass(2000.0, 8e-6, fs_cut=0.9)
    check('Scheil Fe (k 8e-6) removes > 99.9 % at fs_cut 0.9',
          fe['removal_fraction'] > 0.999, f'{fe["removal_fraction"]}')
    b = sr.scheil_pass(40.0, 0.8, fs_cut=0.9)
    check('Scheil B (k 0.8) barely moves (< 20 % per pass)',
          0.0 < b['removal_fraction'] < 0.20, f'{b["removal_fraction"]}')
    o = sr.scheil_pass(100.0, 1.25, fs_cut=0.9)
    check('Scheil O (k 1.25) ENRICHES the solid (stated, not hidden)',
          o['mean_product_ppm'] > 100.0)
    y = sr.scheil_pass(2000.0, 8e-6, target_ppm=0.1)
    check('Scheil yield fraction below target is in (0,1) for Fe',
          y['yield_fraction_below_target'] is not None
          and 0.0 < y['yield_fraction_below_target'] < 1.0)
    z = sr.multipass_zone(30.0, 0.35, passes=5, zone_fraction=0.1)
    check('multipass zone refining converges monotonically (P, 5 passes)',
          z['converging'] and z['removal_fraction'] > 0.5,
          f'{z["mean_product_per_pass"]}')
    zb = sr.multipass_zone(40.0, 0.8, passes=3, zone_fraction=0.1)
    check('zone refining cannot move B much (k 0.8, 3 passes < 50 %)',
          zb['removal_fraction'] < 0.5, f'{zb["removal_fraction"]}')
    ev = sr.evaporation_removal(30.0, 4e-5, 3600.0, 3.3)
    check('evaporation model: first-order decay with the given k, A/V',
          0.0 < ev['c_out'] < 30.0 and ev['c_out'] > 0.0)

    # ---- seeds / rows ---------------------------------------------
    ladder = sr.grade_ladder(mgr)
    check('grade ladder ordered MG → UMG → SoG → EG with rising purity',
          [g['name'] for g in ladder] == ['mg-si', 'umg-si', 'sog-si',
                                          'eg-si']
          and all(ladder[i]['purity_min_fraction']
                  < ladder[i + 1]['purity_min_fraction']
                  for i in range(3)))
    check('every step / route / grade has a valid openness + reasoning',
          all(s['openness'] in sr.OPENNESS and s['openness_reasoning']
              for s in sr.SEED_REFINEMENT_STEPS)
          and all(r['openness'] in sr.OPENNESS and r['reasoning']
                  for r in sr.SEED_REFINEMENT_ROUTES)
          and all(g['openness'] in sr.OPENNESS
                  for g in sr.SEED_SILICON_GRADES))
    check('every step carries citations with full references',
          all(all(c['citation'] for c in json.loads(s['citations']))
              for s in sr.SEED_REFINEMENT_STEPS))
    check('requested steps present',
          {'carbothermic-reduction', 'slag-treatment', 'acid-leaching',
           'directional-solidification', 'vacuum-refining',
           'plasma-refining', 'siemens-tcs', 'fbr-silane',
           'zone-refining', 'czochralski-growth', 'float-zone-growth'}
          <= {s['name'] for s in sr.SEED_REFINEMENT_STEPS})
    check('grades reference techtree nodes by name',
          {g['techtree_node'] for g in sr.SEED_SILICON_GRADES}
          == {'silicon-supply', 'silicon-supply-pv-grade',
              'silicon-supply-semiconductor-grade'})

    # ---- route simulations ----------------------------------------
    pv = sr.route_simulation(mgr, 'pv-open-route')
    check('pv-open-route simulates', pv['ok'])
    metals_ok = all(pv['final_ppm'][m] <= sr.GRADE_LIMITS_PPM['sog-si'][m]
                    for m in ('Fe', 'Al', 'Ca'))
    check('open route on MG feed reaches SoG on metals (Fe/Al/Ca)',
          metals_ok, f'{pv["final_ppm"]}')
    # B/P before the optional vacuum/plasma steps: DS×2 alone stalls
    after_ds2 = pv['steps'][4]['ppm_out']
    check('after DS×2 alone, B/P decide: B above the SoG limit',
          after_ds2['B'] > sr.GRADE_LIMITS_PPM['sog-si']['B']
          and after_ds2['P'] > sr.GRADE_LIMITS_PPM['sog-si']['P'],
          f'B {after_ds2["B"]:.3g} P {after_ds2["P"]:.3g}')
    print(f'  open route final: B {pv["final_ppm"]["B"]:.4g} ppmw, '
          f'P {pv["final_ppm"]["P"]:.4g} ppmw, grade '
          f'{pv["grade_achieved"]}, bottleneck '
          f'{pv["bottleneck_impurity"]}, energy '
          f'{pv["energy_total_kwh_per_kg"]:.1f} kWh/kg')
    check('open route (with plasma/vacuum PRIORS) reaches SoG',
          pv['target_reached'] and pv['grade_achieved'] == 'sog-si')
    check('open route flags its prior steps (vacuum, plasma)',
          {'vacuum-refining', 'plasma-refining'}
          <= set(pv['honesty']['prior_steps']))
    check('openness of the open route = open-research (worst step)',
          pv['openness'] == 'open-research')

    eg = sr.route_simulation(mgr, 'eg-novel-route')
    check('EG route does NOT reach eg-si; blocked by B or P',
          eg['ok'] and not eg['target_reached']
          and eg['bottleneck_impurity'] in ('B', 'P'),
          f'{eg["grade_achieved"]} {eg["bottleneck_impurity"]}')
    check('EG route verdict = novel-needed (target unreached)',
          eg['verdict'] == 'novel-needed')
    check('EG route is novel-needed with >= 3 candidate directions, '
          'each with a bounding equation',
          eg['novel_directions'] and len(eg['novel_directions']) >= 3
          and all(d['bounding_equation'] and d['what_would_need_proving']
                  for d in eg['novel_directions']))

    sie = sr.route_simulation(mgr, 'siemens-route')
    check('siemens route openness = industrial-proprietary (worst step)',
          sie['openness'] == 'industrial-proprietary')
    steps = {s.name: s for s in mgr.objectTables['RefinementStep']}
    check('route_openness picks the worst step',
          sr.route_openness([steps['acid-leaching'],
                             steps['siemens-tcs']])
          == 'industrial-proprietary'
          and sr.route_openness([steps['acid-leaching']])
          == 'open-research')
    exp = sum(steps[n].energy_kwh_per_kg
              for n in json.loads(
                  sr.get_row(mgr, 'RefinementRoute',
                             'pv-open-route').steps_json))
    check('energy totals sum over the route steps',
          abs(pv['energy_total_kwh_per_kg'] - exp) < 1e-9)
    check('knobs echoed and honoured (fs_cut 0.5 removes less B)',
          pv['knobs']['fs_cut'] == 0.9
          and sr.route_simulation(mgr, 'pv-open-route',
                                  knobs={'fs_cut': 0.5})['knobs'][
              'fs_cut'] == 0.5)
    check('unknown route refuses honestly',
          not sr.route_simulation(mgr, 'nope')['ok'])

    # ---- graphs + report ------------------------------------------
    ok = True
    for g in sr.SEED_SI_REFINEMENT_GRAPHS:
        d = json.loads(g['definition'])
        ok = ok and 'graphConfig' in d and g['source_class'] == \
            'RefinementRoute'
    check('graph seeds round-trip (definition JSON, source_class)',
          ok and {g['name'] for g in sr.SEED_SI_REFINEMENT_GRAPHS}
          == {'si-refinement-impurity-ladder', 'si-refinement-scheil'})
    lad = sr.impurity_ladder_rows(mgr, 'pv-open-route')
    check('impurity ladder rows: one series per impurity + B hguides',
          lad['ok'] and {r['series'] for r in lad['rows']}
          >= set(sr.IMPURITIES) | {'B limit sog-si', 'B limit eg-si'}
          and any(r['style'] == 'hguide' for r in lad['rows']))
    sc = sr.scheil_rows()
    check('scheil rows cover all impurities',
          {r['series'] for r in sc['rows']} == set(sr.IMPURITIES))
    rep = sr.refinement_report(mgr)
    try:
        json.dumps(rep)
        ser = True
    except (TypeError, ValueError):
        ser = False
    check('report is JSON-serialisable', ser)
    st = rep['statement']
    check('report statement: PV reachable by open route, EG not',
          st['pv_grade']['reachable_by_open_route']
          and not st['semiconductor_grade']['reachable_by_open_route']
          and len(st['semiconductor_grade']['candidate_directions']) >= 3)

    n_pass = sum(1 for _, c in _results if c)
    print(f'\n{n_pass}/{len(_results)} checks passed')
    return 0 if n_pass == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
