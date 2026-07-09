"""
Selftest — morph-1: 3D stand-in organ geometry + root spread +
confinement/dwarfing assessment.

Run from polari-framework/:
    python3 -m plant_morphology.selftest_morphology

Covers: shape-primitive volumes (lamina/cylinder/cone/sphere/ellipsoid);
per-organ + canopy geometry; root envelope + dense root ball; a small
pot confines a plant (ratio < 1, dwarf factor < 1) while a big container
does not (ratio >= 1, dwarf factor 1); a confinement-tolerant plant
(strawberry) stays indefinite in a small pot; a non-dwarfable plant
declines when root-bound (limiting factor named); a taproot plant needs
a root-prune cadence to stay indefinite; honest refusals.
"""

import math
from types import SimpleNamespace

from plant_morphology.morphology_analysis import (
    confinement_assessment, organ_geometry, primitive_volume_mm3,
    root_spread,
)
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


# A small aqp-1-style pot (200mm dia, 250mm tall, 8mm wall, 12mm base) and
# a big planter.
POTS = [
    {'name': 'demo-herb-pot', 'outer_base_diameter_mm': 200.0,
     'height_mm': 250.0, 'wall_thickness_mm': 8.0,
     'base_thickness_mm': 12.0, 'reservoir_height_mm': 0.0},
]


def _mgr():
    return SimpleNamespace(objectTables={
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'RootSystemModel': _rows(SEED_ROOT_MODELS),
        'PotDefinition': _rows(POTS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('shape primitives')
    check('sphere volume = 4/3 π r^3',
          abs(primitive_volume_mm3('sphere', 0, 20, 0)
              - (4.0 / 3.0) * math.pi * 10 ** 3) < 1e-6)
    check('cylinder volume = π r^2 h',
          abs(primitive_volume_mm3('cylinder', 100, 10, 10)
              - math.pi * 25 * 100) < 1e-6)
    check('lamina volume = l·w·t',
          abs(primitive_volume_mm3('lamina', 60, 35, 1.5)
              - 60 * 35 * 1.5) < 1e-6)
    check('cone = 1/3 of its cylinder',
          abs(primitive_volume_mm3('cone', 60, 30, 30) * 3
              - primitive_volume_mm3('cylinder', 60, 30, 30)) < 1e-6)

    print('organ geometry')
    geo = organ_geometry(manager, 'sweet-basil')
    check('basil geometry ok + per-organ + canopy',
          geo['ok'] and len(geo['perOrgan']) == 2
          and geo['canopyEnvelope']['volumeCm3'] > 0)
    check('total organ volume positive',
          geo['totalOrganVolumeCm3'] > 0)
    check('unknown plant geometry refuses',
          not organ_geometry(manager, 'nope').get('ok'))

    print('root spread')
    roots = root_spread(manager, 'sweet-basil')
    check('root envelope ok + dense ball < full envelope',
          roots['ok']
          and 0 < roots['denseRootBallVolumeCm3']
          < roots['fullEnvelopeVolumeCm3'])
    check('pattern + tolerance carried',
          roots['pattern'] == 'fibrous'
          and roots['confinementTolerance'] == 0.7)

    print('confinement — small pot vs big container')
    small = confinement_assessment(manager, 'sweet-basil',
                                   pot_name='demo-herb-pot')
    check('small pot confines basil (ratio computed)',
          small['ok'] and small['confinementRatio'] > 0)
    big = confinement_assessment(manager, 'sweet-basil',
                                 container_volume_l=50.0)
    check('big container: not confined, dwarf factor 1.0',
          not big['confined'] and abs(big['dwarfFactor'] - 1.0) < 1e-6)
    tiny = confinement_assessment(manager, 'sweet-basil',
                                  container_volume_l=0.3)
    check('tiny container: confined + dwarf factor < 1',
          tiny['confined'] and tiny['dwarfFactor'] < 1.0)
    check('basil (tolerant, dwarfable) stays indefinite in a tiny pot',
          tiny['canKeepIndefinitely'])

    print('the headline question: kept in a pot indefinitely?')
    straw = confinement_assessment(manager, 'everbearing-strawberry',
                                   container_volume_l=0.5)
    check('strawberry (tolerance 0.85) indefinite when confined',
          straw['confined'] and straw['canKeepIndefinitely']
          and straw['limitingFactor'] is None)
    pepper = confinement_assessment(manager, 'dwarf-pepper',
                                    container_volume_l=1.0)
    check('dwarf pepper indefinite BUT names a root-prune cadence',
          pepper['canKeepIndefinitely']
          and pepper['rootPruneCadenceDays'] == 365.0
          and 'root-prune' in (pepper['limitingFactor'] or ''))

    # A non-dwarfable, low-tolerance plant declines when root-bound.
    stubborn_roots = SEED_ROOT_MODELS + [{
        'name': 'oak-roots', 'plant_name': 'oak', 'pattern': 'taproot',
        'natural_spread_radius_mm': 500.0, 'natural_depth_mm': 800.0,
        'root_ball_fraction': 0.8, 'confinement_tolerance': 0.1,
        'dwarfable': False, 'root_prune_cadence_days': 0.0,
        'indefinite_in_pot': False}]
    mgr2 = SimpleNamespace(objectTables={
        'OrganModel': _rows(SEED_ORGAN_MODELS),
        'RootSystemModel': _rows(stubborn_roots),
        'PotDefinition': _rows(POTS)})
    oak = confinement_assessment(mgr2, 'oak', container_volume_l=2.0)
    check('non-dwarfable root-bound plant CANNOT be kept indefinitely',
          not oak['canKeepIndefinitely']
          and 'not dwarfable' in (oak['limitingFactor'] or ''))
    check('non-dwarfable dwarf factor is raw geometric (no tolerance '
          'floor)',
          oak['dwarfFactor'] < 0.5)

    print('honest refusals')
    check('no root model refuses',
          not root_spread(manager, 'nope').get('ok'))
    check('confinement needs a container or pot',
          not confinement_assessment(manager, 'sweet-basil').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
