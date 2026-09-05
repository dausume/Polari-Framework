"""
@module cntfet.cnt_links

fp-6 (FET_CELL_POWER_SILICON_PLAN): the WEAVE — for one FET, every
page and alternate view it has, its complementary partner, the cells
built from it, and the other FETs it is compared against, as DATA a
nav row renders (api-structured-panel — tables of links, never a JSON
wall; a link strip is a frontend follow-up). The point (Dustin 2026-08-27): "weaving together pages and
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
    coverage = None
    try:
        from cntfet.cnt_cell_coverage import device_cell_coverage
        cov = device_cell_coverage(manager, name)
        coverage = {k: cov[k] for k in ('latestLibraryRun', 'covered',
                                        'missing', 'coverageFraction',
                                        'missingByKind')}
        cells = [{'cell': c['cell'], 'kind': c['kind'],
                  'covered': c['covered'], 'run': c['run'],
                  'fill': c['fill'], **c['dataPaths']}
                 for c in cov['cells']]
    except ImportError:
        pass
    # fg-2 (fet, not cntfet): the generic pages, object-addressed.
    is_si = any(getattr(r, 'name', '') == name
                for r in (tables.get('SiliconMOSFET') or {}).values())
    home_route, home_title = (('sifet', 'Silicon FET home') if is_si
                              else ('cntfet', 'CNT FET home'))
    return {
        'ok': True, 'device': name,
        'start_here': _page(f'fet-detail?object={name}',
                            f'{name}: pick a characteristic',
                            'plain-language explanations, the views '
                            'that show it, 3-D field scenes'),
        'pages': [
            _page(home_route, home_title,
                  'every device, parameters, anchors, figures'),
            _page(f'fet?object={name}', f'{name}: scoring',
                  'figures of merit vs ideals, validity proofs, '
                  'competitive ranking'),
            _page(f'fet-detail?object={name}', f'{name}: detail',
                  'characteristic explorer + fields'),
        ],
        'api': {k: f'/api/fet/device/{name}/{k}' for k in (
            'characterization', 'states', 'regimes', 'transport',
            'score', 'compare', 'characteristics', 'fields',
            'cell-scores', 'ip')},
        'complementary': partner,
        'compared_against': others,
        'cells_built_from_it': cells,
        'cell_coverage': coverage,
        'categories': {
            'input': 'gate side: threshold, swing, doping',
            'output': 'drain side: Id(Vd), DIBL, on-conductance',
            'transfer': 'the switch: Id(Vg), on/off, gm, states, '
                        'transport, score',
            'structure': 'materials, potential, electron density'},
    }
