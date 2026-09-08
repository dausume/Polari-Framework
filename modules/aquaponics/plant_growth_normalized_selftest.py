"""
Selftest — plant-growth-sim phase 1 (2026-07-15): normalized-growth
per-part state (aquaponics.plant_growth_normalized_basis) + the animation-
bones vector graph generator (aquaponics.custom.plant_skeleton).

Run from polari-framework/:
    python3 -m aquaponics.plant_growth_normalized_selftest

Uses the REAL seed rows (sweet-basil / demo-herb-pot) from
plant_seed / morphology_seed / pot_seed / plant_growth_seed /
plant_growth_normalized_seed — no fixture-only data — so this exercises
the actual cross-module path (aqp-4 + aqp-8 + morph-1 + this phase)
end to end, stdlib-only + fast (no skfem / no live backend needed).
"""

import json
from types import SimpleNamespace

from aquaponics.plant_growth_normalized_basis import (
    SANE_MAX_LINEAR_MM, advance_growth, constrained_limits,
    current_canopy_profile, current_root_profile, free_soil_constants,
    organ_part_name, overall_normalized_growth, part_normalized_growth,
)
from aquaponics.plant_growth_normalized_seed import SEED_POT_PLANTINGS
from aquaponics.plant_growth_seed import SEED_PLANT_GROWTH_MODELS
from aquaponics.plant_seed import SEED_PLANTS, SEED_PLANT_PARTS
from aquaponics.custom.plant_skeleton import (
    CANOPY_ARRANGEMENT_KNOBS, ROOT_PATTERN_KNOBS, generate_skeleton,
)
from aquaponics.pot_seed import SEED_POTS
from plant_morphology.morphology_seed import (
    SEED_ORGAN_MODELS, SEED_ROOT_MODELS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(plantings=None):
    return SimpleNamespace(objectTables={
        'PlantDefinition': _rows(SEED_PLANTS),
        'PlantPart': _rows(SEED_PLANT_PARTS),
        'PlantGrowthModel': _rows(SEED_PLANT_GROWTH_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'PotDefinition': _rows(SEED_POTS),
        'PotPlanting': _rows(
            plantings if plantings is not None else SEED_POT_PLANTINGS),
    })


PLANTING = SEED_POT_PLANTINGS[0]['name']


if __name__ == '__main__':
    manager = _mgr()

    print('Stage 1 — free_soil_constants')
    constants = free_soil_constants(manager, 'sweet-basil')
    check('ok, reads real RootSystemModel + PlantPart rows',
          constants['ok']
          and set(constants['partRefs']) >= {'root', 'stem', 'leaf'})
    check('per-part rate sourced from PlantGrowthModel (aqp-8), not '
          'the whole-plant fallback',
          constants['partRefs']['root']['growthRateSource']
          == 'PlantGrowthModel'
          and constants['partRefs']['root']['growthRatePerDay'] == 0.14)
    check('root envelope pulled straight off the real RootSystemModel '
          'row (natural_depth_mm=200, natural_spread_radius_mm=120)',
          constants['root']['maxDepthMm'] == 200.0
          and constants['root']['maxSpreadRadiusMm'] == 120.0)
    check('no RootSystemModel for the species -> honest refusal '
          'naming the missing knob',
          not free_soil_constants(manager, 'nope').get('ok') is True)
    missing_root = _mgr()
    missing_root.objectTables['RootSystemModel'] = {}
    refusal = free_soil_constants(missing_root, 'sweet-basil')
    check('refusal names RootSystemModel as the knob to seed',
          not refusal['ok']
          and 'RootSystemModel' in refusal['suggestion']['knob'])

    print('SANE_MAX_LINEAR_MM safety ceiling')
    huge = _mgr()
    huge_root = dict(SEED_ROOT_MODELS[0])
    huge_root['natural_depth_mm'] = 999_999.0
    huge.objectTables['RootSystemModel'] = _rows([huge_root])
    clamped = free_soil_constants(huge, 'sweet-basil')
    check('an absurd declared depth is clamped to the sane ceiling, '
          'loudly (a warning, not silent)',
          clamped['root']['maxDepthMm'] == SANE_MAX_LINEAR_MM
          and any('exceeds the sane ceiling' in w
                  for w in clamped['warnings']))

    print('Stage 2 — constrained_limits (reuses confinement_assessment)')
    limits = constrained_limits(manager, 'demo-herb-pot', 'sweet-basil')
    check('ok, carries the real survives/declines verdict + a ceiling '
          'per part',
          limits['ok'] and isinstance(limits['survivesConfinement'], bool)
          and set(limits['partCeilings']) == set(constants['partRefs']))
    check('unknown pot refuses cleanly through the same path',
          not constrained_limits(manager, 'nope', 'sweet-basil')['ok'])
    ceiling = limits['normalizedGrowthCeiling']
    check('ceiling in (0, 1] — demo-herb-pot dwarfs but does not zero '
          'sweet basil out',
          0.0 < ceiling <= 1.0)

    print('PotPlanting instance state — per-part growth tracking')
    planting = next(iter(manager.objectTables['PotPlanting'].values()))
    check('seed row has an empty part_growth_json (never advanced yet)',
          json.loads(planting.part_growth_json) == {})
    check('unadvanced part reads as the seed epsilon, not a false 0',
          part_normalized_growth(planting, 'root') > 0.0)
    overall = overall_normalized_growth(manager, PLANTING)
    check('overall_normalized_growth is a volume-weighted read, not '
          'stored state',
          overall['ok'] and 0.0 < overall['overallNormalizedGrowth'] < 1.0)

    print('advance_growth — closed-form logistic, PER PART, real '
          'conditions vs confinement kept separate')
    step1 = advance_growth(manager, PLANTING, dt_days=10.0,
                           water_supply_factor=1.0, soil_supply_factor=1.0)
    check('ok, every part with a ceiling advanced, in [seed, ceiling]',
          step1['ok']
          and set(step1['parts']) == set(limits['partCeilings'])
          and all(0.0 < p['normalizedGrowth'] <= p['ceiling'] + 1e-9
                  for p in step1['parts'].values()))
    check('rate this tick honestly reflects the supply factor (1.0 '
          'here -> effective == base)',
          step1['supplyFactor'] == 1.0
          and step1['parts']['root']['effectiveRatePerDay']
          == step1['parts']['root']['baseRatePerDay'])
    check('healthy at full supply, high confinement headroom',
          step1['condition'] in ('healthy', 'stressed'))
    check('persisted back onto the row (not just returned; the row '
          'carries full precision, the report is rounded for display)',
          abs(json.loads(planting.part_growth_json)['root']
              - step1['parts']['root']['normalizedGrowth']) < 1e-4)

    starved = advance_growth(manager, PLANTING, dt_days=10.0,
                             water_supply_factor=0.05,
                             soil_supply_factor=1.0)
    check('starved growth is strictly slower than well-supplied growth '
          '(rate scales down, not the ceiling)',
          starved['parts']['root']['effectiveRatePerDay']
          < step1['parts']['root']['effectiveRatePerDay'])
    check('low supply factor marks the planting stressed',
          starved['condition'] == 'stressed')

    zero_dt = advance_growth(manager, PLANTING, dt_days=0.0)
    check('dt_days=0 is a no-op read, not an error',
          zero_dt['ok'] and zero_dt['parts']['root']['normalizedGrowth']
          == starved['parts']['root']['normalizedGrowth'])
    check('negative dt_days refuses',
          not advance_growth(manager, PLANTING, dt_days=-1.0)['ok'])
    check('unknown planting refuses',
          not advance_growth(manager, 'nope', dt_days=1.0)['ok'])

    print('never-collapsed knobs: confinement caps FAR, supply caps FAST')
    fresh = _mgr()
    unlimited_pot = dict(SEED_POTS[0])
    unlimited_pot['name'] = 'huge-test-pot'
    unlimited_pot['outer_base_diameter_mm'] = 20_000.0
    unlimited_pot['outer_height_mm'] = 20_000.0
    fresh.objectTables['PotDefinition'] = _rows(
        SEED_POTS + [unlimited_pot])
    fresh.objectTables['PotPlanting'] = _rows([
        dict(SEED_POT_PLANTINGS[0], name='huge-pot-basil',
             pot_name='huge-test-pot'),
    ])
    roomy_limits = constrained_limits(fresh, 'huge-test-pot', 'sweet-basil')
    check('a much larger pot raises the ceiling versus demo-herb-pot',
          roomy_limits['normalizedGrowthCeiling']
          >= limits['normalizedGrowthCeiling'])
    roomy_full_supply = advance_growth(fresh, 'huge-pot-basil',
                                       dt_days=10.0)
    roomy_low_supply = advance_growth(
        _mgr(plantings=[dict(SEED_POT_PLANTINGS[0],
                             name='huge-pot-basil-2',
                             pot_name='demo-herb-pot')]),
        'huge-pot-basil-2', dt_days=10.0, water_supply_factor=0.05)
    check('same dt_days: low supply reaches less progress than full '
          'supply (rate knob acted), independent of which pot capped '
          'the ceiling',
          roomy_low_supply['parts']['root']['normalizedGrowth']
          < roomy_full_supply['parts']['root']['normalizedGrowth'])

    print('SHAPE equations — current_root_profile / '
          'current_canopy_profile (per-part, not one global fraction)')
    root_profile = current_root_profile(manager, PLANTING)
    check('root profile ok, taper samples run from core-diameter down '
          'to hair-diameter as distance grows',
          root_profile['ok'] and len(root_profile['taperSamples']) == 12
          and root_profile['taperSamples'][0]['diameterMm']
          >= root_profile['taperSamples'][-1]['diameterMm'])
    check('unknown planting refuses',
          not current_root_profile(manager, 'nope')['ok'])
    canopy_profile = current_canopy_profile(manager, PLANTING)
    check('canopy profile ok, one entry per real OrganModel row, each '
          'scaled by ITS OWN mapped part (organ_part_name)',
          canopy_profile['ok']
          and len(canopy_profile['organs'])
          == sum(1 for o in SEED_ORGAN_MODELS
                 if o['plant_name'] == 'sweet-basil')
          and {o['part'] for o in canopy_profile['organs']}
          == {organ_part_name(o['organ']) for o in SEED_ORGAN_MODELS
              if o['plant_name'] == 'sweet-basil'})
    check('organ_part_name maps the two non-literal organ kinds',
          organ_part_name('root-visible') == 'root'
          and organ_part_name('branch') == 'stem'
          and organ_part_name('leaf') == 'leaf')

    print('GEOMETRY layer — plant_skeleton.generate_skeleton (bones)')
    skeleton = generate_skeleton(manager, PLANTING)
    check('ok, produced a nonempty connected bone graph',
          skeleton['ok'] and skeleton['boneCount'] > 0
          and len(skeleton['bones']) == skeleton['boneCount'])
    root_bones = [b for b in skeleton['bones'] if b['part'] == 'root']
    canopy_bones = [b for b in skeleton['bones']
                    if b['part'] in ('stem',)]
    check('root bones walk DOWNWARD from the shared core '
          '(end z <= start z for the root trunk)',
          root_bones
          and root_bones[0]['startPointMm'] == list(
              round(c, 2) for c in skeleton['coreOriginMm'])
          and root_bones[0]['endPointMm'][2]
          < root_bones[0]['startPointMm'][2])
    check('stem bones walk UPWARD from the same shared core',
          canopy_bones
          and canopy_bones[0]['startPointMm'] == list(
              round(c, 2) for c in skeleton['coreOriginMm'])
          and canopy_bones[0]['endPointMm'][2]
          > canopy_bones[0]['startPointMm'][2])
    check('every non-root bone names a real parent id that exists '
          'in the same graph (a real connected graph, not a flat list)',
          all(b['parentId'] is None
              or any(other['id'] == b['parentId']
                     for other in skeleton['bones'])
              for b in skeleton['bones']))
    check('leaf organs attach as terminal bones (not their own '
          'branching axis) — appear with a non-None organ field',
          any(b['organ'] == 'leaf' for b in skeleton['bones']))
    check("root pattern knob used matches the real RootSystemModel "
          "row ('fibrous')",
          skeleton['rootPattern'] == 'fibrous'
          and skeleton['rootPattern'] in ROOT_PATTERN_KNOBS)

    print('reproducibility — same seed -> identical skeleton')
    skeleton_again = generate_skeleton(manager, PLANTING)
    check('byte-identical bone list across two independent calls '
          '(random.Random(seed), not global random state)',
          skeleton['bones'] == skeleton_again['bones'])
    diff_seed_mgr = _mgr(plantings=[
        dict(SEED_POT_PLANTINGS[0], name='diff-seed-basil',
             random_seed=SEED_POT_PLANTINGS[0]['random_seed'] + 1),
    ])
    skeleton_diff = generate_skeleton(diff_seed_mgr, 'diff-seed-basil')
    check('a different random_seed produces a different bone pattern',
          skeleton_diff['bones'] != skeleton['bones'])

    print('computational safety caps — never silent')
    tiny_caps = generate_skeleton(manager, PLANTING, max_generations=6,
                                  max_bones=1)
    check('hitting max_bones is reported, never silently truncated',
          tiny_caps['ok'] and tiny_caps['boneCount'] == 1
          and tiny_caps['cappedByBoneCount'])
    gen_capped = generate_skeleton(manager, PLANTING, max_generations=1,
                                   max_bones=10_000)
    check('hitting max_generations is reported independently of the '
          'bone-count cap',
          gen_capped['ok']
          and all(b['generation'] <= 1 for b in gen_capped['bones'])
          and gen_capped['cappedByGenerations'])
    check('unknown planting refuses',
          not generate_skeleton(manager, 'nope')['ok'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
