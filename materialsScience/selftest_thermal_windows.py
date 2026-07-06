"""
Self-test for thermal processing windows (msci-9) — Dustin's
no-volatiles rule from the Base Wax Properties notes, as pure math and
as a composite-search gate.

Run from polari-framework/:
    python3 -m materialsScience.selftest_thermal_windows
"""

import sys

from materialsScience.thermal_windows import (
    SEED_THERMAL_PROFILES, machinable_verdict, printable_verdict,
    processing_window, profiles_from_rows,
)
from materialsScience.composite_search import (
    load_legacy_seed_data, normalize_targets, search_composites,
    thermal_name,
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


PROFILES = profiles_from_rows(SEED_THERMAL_PROFILES)


def test_note_data():
    print('[note data encoded faithfully]')
    noteRows = [r for r in SEED_THERMAL_PROFILES
                if 'IMG_2823' in r['provenance_note']]
    litRows = [r for r in SEED_THERMAL_PROFILES
               if 'LITERATURE-TYPICAL' in r['provenance_note']]
    check('four notebook waxes + literature fills (all quantified '
          'additives covered)', len(noteRows) == 4 and len(litRows) >= 12)
    check('beeswax melt 62-64, smoke 204',
          PROFILES['beeswax'] == {'meltLowC': 62.0, 'meltHighC': 64.0,
                                  'smokeLowC': 204.0, 'smokeHighC': 204.0,
                                  'melts': True})
    check('carnauba smoke range 200-220 keeps the LOW end as the limit',
          PROFILES['carnauba-wax']['smokeLowC'] == 200.0)
    check('every non-notebook value is labeled vetoable', all(
        'NOT' in r['provenance_note'] for r in litRows))
    check('fillers are melts=False; notebook waxes melt', all(
        not PROFILES[n]['melts'] for n in PROFILES
        if 'grog' in n or 'clay' in n) and PROFILES['beeswax']['melts'])
    check('pine rosin (Dustin 2026-07-06): melt 100-150, smoke 215',
          PROFILES['pine-rosin'] == {
              'meltLowC': 100.0, 'meltHighC': 150.0,
              'smokeLowC': 215.0, 'smokeHighC': 215.0, 'melts': True})
    rosinBlend = processing_window(['beeswax', 'pine-rosin'], PROFILES)
    check('beeswax+rosin: rosin governs melt-through (150), beeswax the '
          'volatile limit (204-20) -> window [150, 184]',
          rosinBlend['windowC'] == [150.0, 184.0]
          and rosinBlend['meltGovernedBy'] == 'pine-rosin'
          and rosinBlend['limitedBy'] == 'beeswax')


def test_windows():
    print('[processing windows]')
    solo = processing_window(['beeswax'], PROFILES)
    check('beeswax window [64, 184] at 20C margin',
          solo['ok'] and solo['windowC'] == [64.0, 184.0])

    blend = processing_window(['beeswax', 'carnauba-wax'], PROFILES)
    check('beeswax+carnauba window governed by carnauba melt, '
          'carnauba smoke', blend['windowC'] == [86.0, 180.0]
          and blend['meltGovernedBy'] == 'carnauba-wax'
          and blend['limitedBy'] == 'carnauba-wax')

    waxes = ['beeswax', 'candelilla-wax', 'carnauba-wax', 'coconut-wax']
    allFour = processing_window(waxes, PROFILES)
    check('all-wax window still open [86, 180]',
          allFour['ok'] and allFour['windowC'] == [86.0, 180.0])

    filled = processing_window(['beeswax', 'grog-(6-um)'], PROFILES)
    check('inert filler does not raise melt-through (melts=False)',
          filled['windowC'] == [64.0, 184.0]
          and filled['meltGovernedBy'] == 'beeswax')
    lecithin = processing_window(['beeswax', 'soy-lecithin'], PROFILES)
    check('lecithin honestly caps the window at 100C',
          lecithin['windowC'] == [64.0, 100.0]
          and lecithin['limitedBy'] == 'soy-lecithin')
    check('filler-only stock refused (no meltable binder)',
          processing_window(['grog-(6-um)'], PROFILES)['ok'] is False)

    # A hypothetical low-smoke component closes the window.
    withVolatile = dict(PROFILES)
    withVolatile['volatile-resin'] = {
        'meltLowC': 70.0, 'meltHighC': 75.0,
        'smokeLowC': 95.0, 'smokeHighC': 95.0}
    closed = processing_window(['carnauba-wax', 'volatile-resin'],
                               withVolatile)
    check('low-smoke component closes the window',
          closed['ok'] is False and closed['windowC'] is None
          and closed['limitedBy'] == 'volatile-resin')

    unknown = processing_window(['beeswax', 'mystery-goo'], PROFILES)
    check('missing profile is an honest gap, not assumed safe',
          unknown['ok'] is False
          and unknown['missingProfiles'] == ['mystery-goo'])

    check('margin is a knob', processing_window(
        ['beeswax'], PROFILES, marginC=0.0)['windowC'] == [64.0, 204.0])


def test_process_verdicts():
    print('[printable / machinable verdicts]')
    printable = printable_verdict(['beeswax', 'carnauba-wax'], PROFILES)
    check('beeswax+carnauba printable (94C-wide window)',
          printable['ok'] and printable['widthC'] == 94.0)

    tight = printable_verdict(['beeswax'], PROFILES, marginC=125.0)
    check('window-width knob refuses with the reason',
          tight['ok'] is False and 'too tight' in tight['refusal'])

    machinable = machinable_verdict(['beeswax', 'carnauba-wax'], PROFILES)
    check('beeswax+carnauba machinable (softest melts at 62 >= 40)',
          machinable['ok'] and machinable['softestComponent'] == 'beeswax')

    coconut = machinable_verdict(['coconut-wax', 'carnauba-wax'], PROFILES)
    check('coconut (35C melt) refused for CNC — smears under cutter',
          coconut['ok'] is False and 'smear' in coconut['refusal'])


def test_search_gate():
    print('[composite search thermal gate]')
    data = load_legacy_seed_data()
    check('thermal_name maps additive rows',
          thermal_name({'name': 'Carnauba Wax'}) == 'carnauba-wax')
    base = {'ShrinkageRate': 3.0, 'FlexuralModulus': 40.0}
    targets = normalize_targets([
        {'propertyName': 'ShrinkageRate', 'optimumValue': 1.0,
         'optimumRangeMin': 0.5, 'optimumRangeMax': 2.0,
         'hardMinimum': 0.0, 'hardMaximum': 2.0, 'weight': 1.0}])
    gated = search_composites(
        base, targets, data['additives'], data['effects'],
        data['compatibilizers'], maxAdditives=1,
        base_material_name='beeswax', thermal_profiles=PROFILES,
        process='3d-print')
    check('gated search runs', gated['evaluated'] > 0)
    check('thermal gate declared in assumptions',
          any('no-volatiles' in a for a in gated['assumptions']))
    check('every candidate carries a thermal verdict',
          all('thermal' in c for c in gated['ranked']))
    unknownAdditiveCandidates = [
        c for c in gated['ranked']
        if c['thermal']['missingProfiles']]
    check('additives without profiles are violations, not winners', all(
        not c['meets'] and any(v.get('type') == 'thermal-window'
                               for v in c['violations'])
        for c in unknownAdditiveCandidates))
    check('winners (if any) all have open windows', all(
        w['thermal']['ok'] for w in gated['winners']))

    cnc = search_composites(
        base, targets, data['additives'], data['effects'],
        data['compatibilizers'], maxAdditives=1,
        base_material_name='coconut-wax', thermal_profiles=PROFILES,
        process='cnc-machine')
    check('coconut base can never win CNC (35C melt)',
          cnc['winners'] == [] and all(not c['meets']
                                       for c in cnc['ranked']))


def main():
    test_note_data()
    test_windows()
    test_process_verdicts()
    test_search_gate()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
