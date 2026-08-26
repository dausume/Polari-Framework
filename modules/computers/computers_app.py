"""
@module computers.computers_app

THE APP ROW: Computer Assembly as a `PolariAppDefinition` — the
cmp-c arc's front door. The 2026-08-25 session built the module,
pages, and gates but never seeded a nav app, so the work was
reachable only by typed URL (/display/computers).

Defined HERE rather than appended to `polariapps/apps_seed.py`
for the same reason as climate_app: `pol modules drop computers`
removes the app row's source with its code, and the file stays in
the dev-cmpc-1 commit set without touching the chip arc's — the
two arcs remain SEPARABLE (COMPUTER_COMPOSITION_PLAN rule; the
chip counterpart is cntfet/cnt_app.py).

New discipline string `computing`, new persona `computer-builder`
— both DERIVED indexes in the nav machinery, so each is a row,
not a code change.

@consumers polariServer (computers seed pass), polariapps.apps_api
"""

import json as _json

from composition.seed_upsert import upsert_seed_pairs

PROV = 'cmp-c-nav'


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


SEED_COMPUTERS_APPS = [{
    'name': 'app-computer-assembly',
    'title': 'Computer Assembly',
    'use_case': (
        'Builders speccing real computers from the parts catalog: '
        'component taxonomy, dated prices, assembly gate checks, '
        'and use-case profile fits — separable from microchip '
        'creation and levels.'),
    'description': (
        'The component taxonomy, assemblies, and use-case profiles '
        '(computers) over the parts catalog with dated prices and '
        'example builds (computerparts), riding the composition '
        'machinery a computer is a composition of parts on '
        '(composition).'),
    'modules_json': _json.dumps(
        ['computers', 'computerparts', 'composition']),
    'pages_json': _json.dumps(['/display/computers']),
    'nav_json': _json.dumps([
        _tgrp('Assembly',
              _it('Computers home', 'page',
                  route='/display/computers',
                  requires_module='computers'),
              _it('Assemblies & gate reports', 'page',
                  route='/class-main-page/ComputerAssemblyDefinition',
                  requires_module='computers'),
              _it('Use-case profiles', 'page',
                  route='/class-main-page/ComputerProfileDefinition',
                  requires_module='computers'),
              _it('Component taxonomy', 'page',
                  route='/class-main-page/ComputerPartClassDefinition',
                  requires_module='computers')),
        _grp('Catalog',
             _it('Parts — dated prices', 'page',
                 route='/class-main-page/ComputerPartDefinition',
                 requires_module='computerparts'),
             _it('Example builds', 'page',
                 route='/class-main-page/ComputerBuildDefinition',
                 requires_module='computerparts')),
    ]),
    'personas_json': _json.dumps(['computer-builder']),
    'discipline': 'computing',
    'notes': (
        'cmp-c-nav. The Catalog group is CRUDE pages that exist '
        'for free once the classes are registered; the home page '
        'is the cmp-c-4 pure-data Display row.'),
}]


def seed_computers_app(manager):
    from polariapps.apps_basis import PolariAppDefinition
    return upsert_seed_pairs(manager, [
        ('PolariAppDefinition', PolariAppDefinition,
         SEED_COMPUTERS_APPS),
    ], tag='ComputersAppSeed')
