"""
Self-test for pspp-4 process layer: the declared execution-effect
discriminator (invariant I2), the process vocabulary, and thermal-
window admissibility riding the existing no-volatiles machinery.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_material_processes
"""

import sys

from pspp.material_processes import (
    ENERGY_DEPOSITION_MODELS, SEED_PROCESS_DEFINITIONS,
    admissible_schedule, validate_execution,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def _definition(name):
    return next(d for d in SEED_PROCESS_DEFINITIONS
                if d['name'] == name)


def test_vocabulary():
    print('[process vocabulary]')
    names = [d['name'] for d in SEED_PROCESS_DEFINITIONS]
    check('names unique', len(set(names)) == len(names))
    check('heating family carries all five deposition models',
          sorted(d['energy_deposition_model']
                 for d in SEED_PROCESS_DEFINITIONS
                 if d['energy_deposition_model'])
          == sorted(ENERGY_DEPOSITION_MODELS))
    check('crystallization is nucleation + growth processes (F10)',
          'nucleation' in names and 'crystal-growth' in names)
    check('exactly one OBSERVATIONAL seed (characterization)',
          [d['name'] for d in SEED_PROCESS_DEFINITIONS
           if d['execution_effect'] == 'OBSERVATIONAL']
          == ['characterization'])
    check('cure variants encode the water boundary condition',
          'sealed-cure' in names and 'open-cure' in names)


def test_execution_effect():
    print('[invariant I2: declared effect]')
    cure = _definition('sealed-cure')
    good = {'output_state_ids_json':
            '["metakaolin-geopolymer#cured-solid"]'}
    check('TRANSFORMATIVE with outputs ok',
          validate_execution(cure, good)['ok'])
    check('TRANSFORMATIVE without outputs refused',
          validate_execution(cure, {'output_state_ids_json': '[]'})
          ['ok'] is False)

    obs = _definition('characterization')
    check('OBSERVATIONAL without outputs ok',
          validate_execution(obs, {'output_state_ids_json': '[]'})
          ['ok'])
    bad = validate_execution(obs, good)
    check('OBSERVATIONAL naming outputs refused (claims, not states)',
          bad['ok'] is False and 'claims' in bad['refusal'])
    undeclared = validate_execution({'execution_effect': ''}, good)
    check('undeclared effect refused — never inferred',
          undeclared['ok'] is False
          and 'declared' in undeclared['suggestion'])


def test_thermal_admissibility():
    print('[thermal-window admissibility]')
    free = admissible_schedule(_definition('mixing'),
                               [{'holdC': 500}])
    check('process without a thermal constraint passes with a note',
          free['ok'] and 'no thermal constraint' in free['note'])

    waxy = {'name': 'wax-extrusion-test',
            'execution_effect': 'TRANSFORMATIVE',
            'accepted_input_constraints_json':
                '{"thermal_window_components": '
                '["beeswax", "carnauba-wax"]}'}
    ok = admissible_schedule(waxy, [{'holdC': 120.0}])
    check('hold inside the beeswax+carnauba window [86, 180] admitted',
          ok['ok'] and ok['window']['windowC'] == [86.0, 180.0])
    hot = admissible_schedule(waxy, [{'holdC': 195.0}])
    check('hold above the window refused naming the limiting '
          'component',
          hot['ok'] is False and 'carnauba-wax' in hot['suggestion'])
    unknown = admissible_schedule(
        {'accepted_input_constraints_json':
         '{"thermal_window_components": ["mystery-goo"]}'},
        [{'holdC': 100.0}])
    check('unknown component refused (missing profile is a gap, not '
          'safe)', unknown['ok'] is False)


def main():
    test_vocabulary()
    test_execution_effect()
    test_thermal_admissibility()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
