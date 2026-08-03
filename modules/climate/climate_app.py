"""
@module climate.climate_app

THE APP ROW (CO2_HEALTH_PLAN.md §9b): Climate Change & Atmosphere
as a `PolariAppDefinition` beside the eight discipline apps the
nav revamp seeded.

The app is defined HERE rather than appended to
`polariapps/apps_seed.py` so the climate module stays droppable:
`pol modules drop climate` removes its app row's source with its
code, instead of leaving an orphan entry in a core seed list.

Two new discipline strings arrive with it (`climate`) and two new
personas (`climate-scientist`, `public-health-analyst`). Both are
DERIVED indexes in the nav machinery, so adding them is a row, not
a code change - which is the property that made the nav revamp
worth building.

⚠ The apps selftest PINS the app count and the absent-nav-item
count on purpose, so a new gated item cannot slip in unnoticed.
Adding this app is a deliberate change to those pins, not an
accident to be papered over.

@consumers polariServer (climate seed pass), polariapps.apps_api
"""

import json as _json

from composition.seed_upsert import upsert_seed_pairs

PROV = 'co2-8'


def _it(label, kind, route='', requires_module='', ref=''):
    item = {'label': label, 'kind': kind}
    if route:
        item['route'] = route
    if requires_module:
        item['requires_module'] = requires_module
    if ref:
        item['ref'] = ref
    return item


def _grp(group, *items, top=False):
    grp = {'group': group, 'items': list(items)}
    if top:
        grp['top_menu'] = True
    return grp


def _tgrp(group, *items):
    return _grp(group, *items, top=True)


SEED_CLIMATE_APPS = [{
    'name': 'app-climate',
    'title': 'Climate Change & Atmosphere',
    'use_case': (
        'Climate scientists and public-health analysts reading the '
        'CO2 record as measured data - outdoor and indoor, '
        'instrumental and ice-core - and asking what it means for '
        'people breathing it.'),
    'description': (
        'The atmospheric series as first-class objects with their '
        'sources and coverage spans (climate), the ventilation '
        'mass balance they share with the greenhouse model '
        '(aquaponics), and the official-source registry behind '
        'every citation (dmvdata). The CO2-and-health study is '
        'the first study on top of them, not the whole subject.'),
    'modules_json': _json.dumps(
        ['climate', 'aquaponics', 'dmvdata', 'simulations']),
    'pages_json': _json.dumps(['/co2/health']),
    'nav_json': _json.dumps([
        _tgrp('Studies',
              _it('CO2 & human health', 'page',
                  route='/co2/health', requires_module='climate'),
              _it('The crossing table - when each line arrives',
                  'page', route='/co2/health?section=crossings',
                  requires_module='climate'),
              _it('Partial pressure & the mechanism', 'page',
                  route='/co2/health?section=partial-pressure',
                  requires_module='climate'),
              _it('What humans have actually breathed', 'page',
                  route='/co2/health?section=human-history',
                  requires_module='climate')),
        _grp('Data',
             _it('Series catalog', 'class-rows',
                 route='/class/AtmosphericSeriesDefinition',
                 requires_module='climate'),
             _it('Coverage spans - which source, which years',
                 'class-rows',
                 route='/class/SourceCoverageSpan',
                 requires_module='climate'),
             _it('Observations', 'class-rows',
                 route='/class/AtmosphericObservation',
                 requires_module='climate'),
             _it('Health thresholds (graded)', 'class-rows',
                 route='/class/CO2HealthThreshold',
                 requires_module='climate'),
             _it('Room archetypes', 'class-rows',
                 route='/class/IndoorSpaceProfile',
                 requires_module='climate'),
             _it('Sources & retrievals', 'class-rows',
                 route='/class/GovSource',
                 requires_module='dmvdata')),
        _grp('Tree',
             _it('Atmospheric measurement', 'tech-node',
                 ref='instruments/atmospheric-measurement')),
    ]),
    'personas_json': _json.dumps(
        ['climate-scientist', 'public-health-analyst']),
    'discipline': 'climate',
    'notes': (
        'co2-8. The Data group is CRUDE pages that exist for free '
        'once the classes are registered - that is the payoff of '
        'making every series an object rather than an engine '
        'payload.'),
}]


def seed_climate_app(manager):
    from polariapps.apps_basis import PolariAppDefinition
    return upsert_seed_pairs(manager, [
        ('PolariAppDefinition', PolariAppDefinition,
         SEED_CLIMATE_APPS),
    ], tag='ClimateAppSeed')
