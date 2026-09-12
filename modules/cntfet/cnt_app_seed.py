"""
@module cntfet.cnt_app_seed

THE APP ROW: Microchips & Semiconductors as a
`PolariAppDefinition` — the chip arc's front door over the levels
ladder (cntfet → electrodevice → hwdigital/hwfpga → microchip).
The 2026-08-25 session built the ladder's pages but never seeded
a nav app, so the work was reachable only by typed URL.

Defined HERE rather than appended to `polariapps/apps_seed.py`
so the row's source drops with the module and the file stays in
the dev-chip-1 commit set without touching the cmp-c arc's — the
two arcs remain SEPARABLE (COMPUTER_COMPOSITION_PLAN rule; the
assembly counterpart is computers/computers_app_seed.py). It lives in
cntfet (the ladder's base module) so the app appears as soon as
the arc's first rung is online; every deeper rung is a gated nav
item with the bring-online affordance, per nav-2.

New discipline string `semiconductors`, new persona
`semiconductor-engineer` — both DERIVED indexes in the nav
machinery, so each is a row, not a code change.

@consumers polariServer (cntfet seed pass), polariapps.apps_api
"""

import json as _json

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'chip-nav'


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


SEED_CHIP_APPS = [{
    'name': 'app-microchips',
    'title': 'Microchips & Semiconductors',
    'use_case': (
        'Semiconductor engineers working the microchip levels '
        'ladder: CNT FET compact models against cited figures, '
        'device and circuit rows, logic blocks, FPGA register '
        'maps, and the chip design levels over them.'),
    'description': (
        'The CNT FET compact model, calibration anchors, and '
        'figure-replica graphs (cntfet), device/circuit rows and '
        'SPICE cards (electrodevice), logic block designs '
        '(hwdigital), FPGA register maps (hwfpga), and the design '
        'levels ladder (microchip). Separable from computer '
        'assembly — that is its own app.'),
    'modules_json': _json.dumps(
        ['cntfet', 'electrodevice', 'microchip', 'hwdigital',
         'hwfpga']),
    'pages_json': _json.dumps(['/display/cntfet',
                               '/display/microchip']),
    'nav_json': _json.dumps([
        _tgrp('Ladder',
              _it('CNT FET — devices & figures', 'page',
                  route='/display/cntfet',
                  requires_module='cntfet'),
              _it('Microchip design levels', 'page',
                  route='/display/microchip',
                  requires_module='microchip'),
              _it('Figure replicas — Graphs editor', 'page',
                  route='/graphs', requires_module='cntfet')),
        _grp('Devices & circuits',
             _it('CNT FET devices', 'page',
                 route='/class-main-page/AlignedCNTFETDevice',
                 requires_module='cntfet'),
             _it('Parameter rows (cited)', 'page',
                 route='/class-main-page/CNTFETParameterRow',
                 requires_module='cntfet'),
             _it('Electronic devices', 'page',
                 route='/class-main-page/ElectronicDeviceDefinition',
                 requires_module='electrodevice'),
             _it('Logic block designs', 'page',
                 route='/class-main-page/LogicBlockDesign',
                 requires_module='hwdigital'),
             _it('FPGA register maps', 'page',
                 route='/class-main-page/RegisterMapDefinition',
                 requires_module='hwfpga')),
    ]),
    'personas_json': _json.dumps(
        ['semiconductor-engineer', 'electrical-engineer']),
    'discipline': 'semiconductors',
    'notes': (
        'chip-nav. The Devices & circuits group is CRUDE pages '
        'that exist for free once the classes are registered; '
        'deeper-rung items gate on their own modules so the app '
        'is honest about what is online.'),
}]


def seed_chip_app(manager):
    from polariapps.apps_basis import PolariAppDefinition
    return upsert_seed_pairs(manager, [
        ('PolariAppDefinition', PolariAppDefinition,
         SEED_CHIP_APPS),
    ], tag='ChipAppSeed')
