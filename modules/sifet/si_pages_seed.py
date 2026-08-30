"""
@module sifet.si_pages_seed

The /display/sifet home page + one score page and one detail page
PER seeded SiliconMOSFET — pure no-code data over the generic
registry components (class-rows-table, api-json-panel,
named-graph-panel), the cntfet-home shape. Every /api/cntfet/device/
{name}/… surface accepts the Si names (shared VS parameterisation),
so the per-device pages are the cnt_compare builders re-pointed at
the Si rows (with_scenes=False: the 3-D field scenes are CNT-only
and would refuse by name — a silicon device has no tube to draw).

Exposed for the integrator (polariServer DisplayDefinition seeds):
  SEED_SI_PAGE_DISPLAYS   — [sifet-home]
  SEED_SI_SCORE_PAGES     — score + detail page per Si device
  refinement_points(manager, route, curve) — the rows the two
      refinement graph panels read. NO endpoint serves them today:
      the integrator must route
        GET /api/sifet/refinement/{route}/points?curve=
            impurity-ladder | scheil
      (the dataPath the panels below carry, which is also the path
      si_refinement.SEED_SI_REFINEMENT_GRAPHS descriptions name)
      to this function.
  /api/cntfet/device/{name}/links is CNT-only today (404 for an Si
      name) — the links panels on the Si pages refuse honestly
      until cnt_api dispatches it.

@consumers
  - polariServer DisplayDefinition seeds (guarded import)
  - sifet.selftest_sifet_pages
"""

import json

from cntfet.cnt_compare import detail_pages, score_pages
from cntfet.cnt_pages_seed import _api, _device_graph, _row, _sapi, _table
from sifet.si_basis import SEED_SI_DEVICES

SI_DEVICE_NAMES = [d['name'] for d in SEED_SI_DEVICES]
SI_REFERENCE_DEVICE = 'si-nmos-planar-90'
REFINEMENT_ROUTE = 'pv-open-route'
REFINEMENT_POINTS_PATH = '/api/sifet/refinement/{route}/points?curve={curve}'
REFINEMENT_CURVES = ('impurity-ladder', 'scheil')


def _refinement_graph(item_id, index, segments, title, curve,
                      route=REFINEMENT_ROUTE):
    """named-graph-panel over the fp-4 seeded GraphDefinition
    `si-refinement-{curve}` (si_refinement.SEED_SI_REFINEMENT_GRAPHS)
    fed by the points path the integrator routes."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'named-graph-panel',
            'inputs': {
                'graphName': f'si-refinement-{curve}',
                'dataPath': REFINEMENT_POINTS_PATH.format(route=route,
                                                          curve=curve),
            },
        },
        'item': None, 'nestedRows': [],
    }


def refinement_points(manager, route=REFINEMENT_ROUTE,
                      curve='impurity-ladder', feed_ppm_json=None,
                      knobs=None):
    """The rows behind REFINEMENT_POINTS_PATH (integrator routes it):
    curve impurity-ladder → si_refinement.impurity_ladder_rows(route);
    curve scheil → si_refinement.scheil_rows (route-independent: one
    directional pass from the MG feed)."""
    from sifet.si_refinement import impurity_ladder_rows, scheil_rows
    if curve == 'impurity-ladder':
        return impurity_ladder_rows(manager, route, feed_ppm_json, knobs)
    if curve == 'scheil':
        feed = json.loads(feed_ppm_json) if feed_ppm_json else None
        return {**scheil_rows(feed), 'route': route}
    return {'ok': False,
            'error': f'unknown curve "{curve}"',
            'affordance': 'curve = ' + ' | '.join(REFINEMENT_CURVES)}


def _home_page():
    d = SI_REFERENCE_DEVICE
    return {
        'name': 'sifet-home',
        'description': 'Silicon MOSFETs on thermal / sol-gel dielectrics '
                       '(fp-2): the device rows with their derived VS '
                       'parameters, the dielectric / doping / shape '
                       'rows they decompose into, the capability '
                       'refusals, the cross-technology ranking against '
                       'the CNT devices, and the fp-4 silicon '
                       'refinement ladder (grade, routes, Scheil).',
        'source_class': 'SiliconMOSFET',
        'isPage': True,
        'pageRoute': 'sifet',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            _row(0, [
                _table('sifet-devices', 0, 8, 'Silicon MOSFETs '
                       '(derive before use: unproven → scores 0)',
                       'SiliconMOSFET',
                       'name,polarity,shape,dielectric,lg_nm,w_nm,'
                       'vdd_v,vt0_v,n_ss,mu_cm2_per_vs,derived_at'),
                _api('sifet-capability', 1, 4,
                     'Capability (honest refusals: gate leakage, GIDL, '
                     'traps, strain, sol-gel conformality)',
                     '/api/sifet/capability'),
            ], min_height=360),
            _row(1, [
                _table('sifet-dielectrics', 0, 4,
                       'Gate dielectrics (thermal reference + sol-gel '
                       'PRIORS)', 'SolGelDielectric',
                       'name,material,precursor,thickness_nm,k_rel,'
                       'breakdown_mv_per_cm,confidence,citation'),
                _table('sifet-dopings', 1, 4, 'Doping profiles',
                       'SiliconDopingProfile',
                       'name,dopant_type,species,concentration_cm3,'
                       'method,activation_fraction'),
                _table('sifet-shapes', 2, 4, 'FET shapes (scale-length '
                       'formula as data)', 'SiliconFETShape',
                       'name,kind,channel_width_nm,fin_height_nm,'
                       'fin_width_nm,n_fins'),
            ], min_height=320),
            # the reference NMOS's own curves — refuse verbatim until
            # derived (the affordance is named in the refusal).
            _row(2, [
                _device_graph('sifet-device-transfer', 0, 4,
                              f'{d}: transfer Id(Vg), log Y (A per um '
                              'of width)', d, 'transfer'),
                _device_graph('sifet-device-output', 1, 4,
                              f'{d}: output Id(Vd)', d, 'output'),
                _api('sifet-device-characterization', 2, 4,
                     f'{d}: characterization (SS/DIBL/Ion/Ioff/gm — '
                     'refusals verbatim)',
                     f'/api/cntfet/device/{d}/characterization'),
            ], min_height=430),
            # cross-technology ranking: every CNT + Si device on the
            # same terms, the reference NMOS as focus.
            _row(3, [
                _device_graph('sifet-compare-graph', 0, 6,
                              f'{d} vs every FET (CNT + Si): score + '
                              'terms (◀ = this device)', d, 'compare'),
                _api('sifet-compare', 1, 6,
                     'Cross-technology ranking (CNT + Si on the same '
                     'characteristic-equation terms; unproven = 0)',
                     f'/api/cntfet/device/{d}/compare'),
            ], min_height=430),
            # fp-4 silicon refinement: the ladder + Scheil graphs and
            # the report (grade reachability statement).
            _row(4, [
                _refinement_graph('sifet-refinement-ladder', 0, 6,
                                  'Refinement: impurity ppm after each '
                                  'step of pv-open-route (log y; B/P '
                                  'stall = grade stall)',
                                  'impurity-ladder'),
                _refinement_graph('sifet-refinement-scheil', 1, 6,
                                  'Refinement: Scheil C_s(f_s) per '
                                  'impurity, one directional pass from '
                                  'MG feed', 'scheil'),
            ], min_height=430),
            _row(5, [
                _api('sifet-refinement', 0, 12,
                     'Silicon refinement report: grade ladder, steps, '
                     'routes (openness), PV vs semiconductor grade '
                     'reachability', '/api/sifet/refinement'),
            ], min_height=360),
            # open-silicon ladder: 90 → 65 → 45 → 32 → 22 → 14 → 7 nm;
            # TWO independent axes per rung (rights / fabrication
            # evidence); manufacturability never inferred from a PDK.
            _row(6, [
                _ladder_graph('sifet-ladder-ion', 0, 6,
                              'Open-silicon ladder: documented Ion per '
                              'rung vs node (log x) + our derived devices'),
                _sapi('sifet-ladder-rungs', 1, 6,
                      'Open-silicon ladder: rungs — rights class × '
                      'fabrication evidence, frontier / predictive / '
                      'manufacturable', '/api/sifet/ladder', pick='rungs'),
            ], min_height=430),
            _row(7, [
                _sapi('sifet-ladder-anchors-n', 0, 6,
                      'si-nmos-freepdk45-class vs the FreePDK45 '
                      'documented anchors (gap + nearest knob, NOT applied)',
                      '/api/sifet/devices/si-nmos-freepdk45-class/anchors'),
                _sapi('sifet-ladder-anchors-p', 1, 6,
                      'si-pmos-freepdk45-class vs the FreePDK45 '
                      'documented anchors',
                      '/api/sifet/devices/si-pmos-freepdk45-class/anchors'),
            ], min_height=360),
        ]}),
    }


def _ladder_graph(item_id, index, segments, title, curve='ion-vs-node'):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'named-graph-panel',
            'inputs': {'graphName': f'si-ladder-{curve}',
                       'dataPath': f'/api/sifet/ladder/points?curve={curve}'},
        },
    }


SEED_SI_PAGE_DISPLAYS = [_home_page()]

#: One score page + one detail page per seeded Si device (routes
#: cntfet-score-{name} / cntfet-detail-{name}); scenes dropped.
SEED_SI_SCORE_PAGES = (
    score_pages(SI_DEVICE_NAMES, source_class='SiliconMOSFET')
    + detail_pages(SI_DEVICE_NAMES, with_scenes=False,
                   source_class='SiliconMOSFET'))
