"""
@module cntfet.cnt_links

fp-6 (FET_CELL_POWER_SILICON_PLAN): the WEAVE — for one FET, every
page and alternate view it has, its complementary partner, the cells
built from it, and the other FETs it is compared against, as DATA a
nav row renders (api-json-panel today; a link strip is a frontend
follow-up). The point (Dustin 2026-08-27): "weaving together pages and
alternate views for FETs so we can more easily understand it for the
average person" — a reader never dead-ends on one page.

@consumers cnt_api (GET /api/cntfet/device/{name}/links),
  cnt_compare (nav rows on the score/detail pages)
"""


def _page(route, title, what):
    return {'route': f'/display/{route}', 'title': title, 'what': what}


def device_links(manager, device):
    name = device.name
    tables = getattr(manager, 'objectTables', None) or {}
    others = sorted(getattr(r, 'name', '')
                    for r in (tables.get('AlignedCNTFETDevice') or {})
                    .values() if getattr(r, 'name', '') != name)
    partner = None
    try:
        from cntfet.cnt_taxonomy import complementary_of
        partner = complementary_of(manager, name)
    except ImportError:
        partner = {'status': 'taxonomy module absent (fp-3)'}
    cells = []
    try:
        from cntfet.cnt_cell_library import COMBINATIONAL, DRIVES
        cells = [{'cell': c, 'drives': list(DRIVES),
                  'logic': f'/api/cntfet/cell/{c}/logic',
                  'scores': f'/api/cntfet/device/{name}/cell-scores'}
                 for c in COMBINATIONAL]
    except ImportError:
        pass
    return {
        'ok': True, 'device': name,
        'start_here': _page(f'cntfet-detail-{name}',
                            f'{name}: pick a characteristic',
                            'plain-language explanations, the views '
                            'that show it, 3-D field scenes'),
        'pages': [
            _page('cntfet', 'CNT FET home',
                  'every device, parameters, anchors, figures'),
            _page(f'cntfet-score-{name}', f'{name}: scoring',
                  'figures of merit vs ideals, validity proofs, '
                  'competitive ranking'),
            _page(f'cntfet-detail-{name}', f'{name}: detail',
                  'characteristic explorer + fields'),
        ],
        'api': {k: f'/api/cntfet/device/{name}/{k}' for k in (
            'characterization', 'states', 'regimes', 'transport',
            'score', 'compare', 'characteristics', 'fields',
            'cell-scores')},
        'complementary': partner,
        'compared_against': others,
        'cells_built_from_it': cells,
        'categories': {
            'input': 'gate side: threshold, swing, doping',
            'output': 'drain side: Id(Vd), DIBL, on-conductance',
            'transfer': 'the switch: Id(Vg), on/off, gm, states, '
                        'transport, score',
            'structure': 'materials, potential, electron density'},
    }
