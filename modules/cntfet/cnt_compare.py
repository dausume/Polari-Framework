"""
@module cntfet.cnt_compare

fi-4 (Dustin 2026-08-27): "for each FET we should have a scoring page
to compare it competitively against other FETs" — and a FET that
cannot be proven to be one scores 0 (cnt_scoring.fet_validity).

The competitive ranking scores EVERY AlignedCNTFETDevice row with the
same terms (cnt_scoring.score_device), levelizes to the best = 100
(the scoring engine's knob, applied here explicitly), marks the
device the page belongs to, and attributes the gap to the leader per
term. Invalid / underived devices stay in the ranking at 0 with the
failed proofs (or the derive affordance) named — absence is data, a
missing competitor is not silently dropped.

fg-2 (FET_GENERIC_PAGES_PLAN; fet, not cntfet — Dustin 2026-08-30):
the per-device page stamping is GONE. TWO generic DisplayDefinition
seeds — `fet` (score) and `fet-detail` — carry '{object}' in every
dataPath/input; display-page substitutes it from ?object=<name>
(fg-1), so what the 90 nm display shows is what EVERY FET's view
shows. Graphs stay the same per-KIND GraphDefinition rows, pointed
at '{object}''s own paths. `legacy_page_names()` lists the
per-device rows the backfill script deletes only after explicit
confirmation.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/compare)
  - cntfet.cnt_device_viz (curve 'compare')
  - polariServer (SEED_CNT_SCORE_PAGES → DisplayDefinition seeds)
  - cntfet.selftest_cntfet
"""

import json

from cntfet.cnt_pages_seed import _api, _device_graph, _row, _sapi
from cntfet.cnt_scoring import CONCEPT_NAME, FET_TERMS, score_device


def compare_devices(manager, focus_name, knobs=None):
    """The /compare payload: every device scored + ranked; the focus
    device's per-term gap to the leader."""
    tables = getattr(manager, 'objectTables', None) or {}
    # fp-2: silicon MOSFETs compete on the same terms (shared VS
    # parameterisation) — cross-technology ranking is the point.
    names = sorted(
        getattr(r, 'name', '')
        for cls in ('AlignedCNTFETDevice', 'SiliconMOSFET')
        for r in (tables.get(cls) or {}).values())
    if focus_name not in names:
        return {'ok': False, 'error': f'no device named "{focus_name}"'}
    scored = {n: score_device(manager, n, knobs) for n in names}
    ranking = []
    for n in names:
        s = scored[n]
        v = s.get('validity', {})
        ranking.append({
            'device': n, 'score': s.get('score', 0.0),
            'valid': bool(v.get('valid')),
            'failed': v.get('failed', []),
            'unproven': bool(s.get('unproven')),
            'reason': v.get('reason', ''),
            'terms': {t['term']: t['normalized']
                      for t in s.get('terms', []) if t.get('found')},
            'isFocus': n == focus_name,
            # evidence: proof-of-freedom beside the score — a fast
            # device that is encumbered is a different answer
            'provenance': s.get('provenance'),
        })
    ranking.sort(key=lambda r: (-r['score'], r['device']))
    best = ranking[0]['score'] if ranking else 0.0
    for i, r in enumerate(ranking):
        r['rank'] = i + 1
        r['levelized'] = (round(100.0 * r['score'] / best, 2)
                          if best > 0 else 0.0)
    leader = ranking[0]
    focus = next(r for r in ranking if r['isFocus'])
    gap = []
    for term in FET_TERMS:
        a, b = focus['terms'].get(term), leader['terms'].get(term)
        if a is None or b is None:
            continue
        gap.append({'term': term, 'focus': a, 'leader': b,
                    'delta': round(a - b, 6)})
    gap.sort(key=lambda g: g['delta'])
    return {
        'ok': True, 'focus': focus_name, 'concept': CONCEPT_NAME,
        'ranking': ranking,
        'leader': leader['device'],
        'focusRank': focus['rank'], 'of': len(ranking),
        'gapToLeader': gap,
        'loses_most_on': gap[0]['term'] if gap and gap[0]['delta'] < 0
        else None,
        'validityRule': 'a device whose characteristic equations cannot '
                        'be proven to switch (fet_validity) or whose '
                        'model is underived scores 0 and ranks last, '
                        'with the failed proofs named',
        'levelized': 'best valid device = 100',
    }


def compare_rows(report):
    """Rows for `cnt-device-compare`: x = device (categorical); one
    dot series per term (normalized) + 'score'; hguide at 1.0."""
    rows = []
    for r in report['ranking']:
        label = r['device'] + (' ◀' if r['isFocus'] else '')
        rows.append({'series': 'score', 'style': 'dot', 'dash': False,
                     'x': label, 'y': r['score']})
        for term, v in r['terms'].items():
            rows.append({'series': term, 'style': 'dot', 'dash': True,
                         'x': label, 'y': v})
        if not r['valid']:
            rows.append({'series': 'invalid (0)', 'style': 'dot',
                         'dash': False, 'x': label, 'y': 0.0,
                         'label': ', '.join(r['failed']) or 'unproven'})
    rows.append({'series': 'ideal', 'style': 'hguide', 'dash': True,
                 'x': None, 'y': 1.0, 'label': 'ideal = 1.0'})
    return rows


def _generic_score_page():
    d = '{object}'
    return {
        'name': 'fet',
        'description': 'The generic FET scoring page — one definition '
                       'for every FET, CNT or Si. Open as /display/'
                       'fet?object=<device>: figures of merit vs '
                       'their characteristic ideals, the FET-validity '
                       'proofs (score 0 if any fails), the Monte '
                       'Carlo spread, parts & purpose, cell-layer '
                       'speed, proof of freedom and the competitive '
                       'ranking against every other FET.',
        'source_class': '',
        'isPage': True,
        'pageRoute': 'fet',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            # the GENERIC FET display (same for every FET; sub-sections
            # chosen by the device's own data: switching vs signal,
            # CNT vs Si, usable vs not) — tables and graphs, no JSON
            _row(0, [_component_item(f'score-{d}-overview', 0, 12,
                                     f'{d}: overview', 'fet-overview',
                                     {'device': d})], min_height=640),
            # fg-3: the 2-D parts view (compact on the score page)
            _row(12, [_component_item(f'score-{d}-parts2d', 0, 12,
                                      f'{d}: 2-D parts view — regions, '
                                      'materials, doping (compact)',
                                      'fet-parts-2d',
                                      {'device': d, 'compact': True})],
                 min_height=360),
            # parts & purpose: every piece, its material, doping and row
            _row(10, [_sapi(f'score-{d}-parts', 0, 12,
                            f'{d}: parts & purpose — material, doping '
                            '(n / p / undoped), dielectric, process, row',
                            f'/api/fet/device/{d}/parts', pick='parts')],
                 min_height=360),
            # speed, OWNED BY THE CELL LAYER: FO4 from the characterized
            # INV of this device's library → clock range for a
            # configurable 30–12 FO4/cycle logic depth (intrinsic-grade)
            _row(11, [_sapi(f'score-{d}-fo4', 0, 12,
                            f'{d}: intrinsic cell speed — FO4, INV '
                            'transition energy, clock range per FO4/cycle '
                            'band (excludes interconnect, clock tree, '
                            'SRAM, IR drop, package)',
                            f'/api/fet/device/{d}/fo4', pick='clock')],
                 min_height=300),
            _row(1, [
                _device_graph(f'score-{d}-terms', 0, 6,
                              f'{d}: figures of merit vs ideals '
                              '(MC spread, best/worst)',
                              d, 'score-terms'),
                _sapi(f'score-{d}-validity', 1, 6,
                      f'{d}: figures of merit — actual vs ideal',
                      f'/api/fet/device/{d}/score?samples=100',
                      pick='idealTable'),
            ], min_height=430),
            _row(2, [
                _device_graph(f'score-{d}-compare', 0, 6,
                              f'{d} vs every FET: score + terms '
                              '(◀ = this device)',
                              d, 'compare'),
                _sapi(f'score-{d}-ranking', 1, 6,
                      f'{d}: competitive ranking',
                      f'/api/fet/device/{d}/compare', pick='ranking'),
            ], min_height=430),
            _row(3, [
                _device_graph(f'score-{d}-transfer-states', 0, 6,
                              f'{d}: operating states on Id(Vg)',
                              d, 'transfer-states'),
                _device_graph(f'score-{d}-envelope', 1, 6,
                              f'{d}: stochastic Id(Vg) envelope',
                              d, 'transfer-envelope'),
            ], min_height=430),
            # evidence: the proof-of-freedom chain (US) — status badge,
            # governing records, clickable patents / papers / licences.
            _row(4, [_component_item(f'score-{d}-proof', 0, 12,
                                     f'{d}: is it free to use? — proof '
                                     'chain (patents, papers, licences; '
                                     'click any item)',
                                     'freedom-proof-panel',
                                     {'path': f'/api/fet/device/{d}/proof'})],
                 min_height=420),
            _row(5, [
                _sapi(f'score-{d}-ip', 0, 6,
                      f'{d}: licensing / freedom-to-operate records '
                      '(engineering record, not legal advice)',
                      f'/api/fet/device/{d}/ip', pick='records'),
                _sapi(f'score-{d}-links', 1, 6,
                      f'{d}: related pages, partner, cells',
                      f'/api/fet/device/{d}/links', pick='pages'),
            ], min_height=300),
        ]}),
    }


def score_pages(device_names=None, source_class=''):
    """fg-2: per-device stamping is gone — the ONE generic page.
    (Signature kept for the old call sites; arguments ignored.)"""
    return [_generic_score_page()]


def generic_pages():
    """The two generic FET page seeds (fg-2)."""
    return [_generic_score_page(), _generic_detail_page()]


def legacy_page_names(device_names):
    """The per-device DisplayDefinition rows fg-2 replaces — the
    backfill script lists these and deletes them only after explicit
    confirmation (plan decision 2)."""
    return ([f'cntfet-score-{n}' for n in device_names]
            + [f'cntfet-detail-{n}' for n in device_names])


def _component_item(item_id, index, segments, title, component, inputs):
    """Any generic-registry component as a page item."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {'componentName': component, 'inputs': inputs},
        'item': None, 'nestedRows': [],
    }


def _explorer_item(item_id, index, segments, title, device):
    """fv-5: the characteristic explorer (generic registry component)
    — lists the FETCharacteristic rows for this device and renders
    the selected one's views through the existing panels."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'fet-characteristic-explorer',
            'inputs': {'device': device, 'hideUnbuilt': False},
        },
        'item': None, 'nestedRows': [],
    }


def _generic_detail_page():
    """fv-5 → fg-2: the ONE generic DETAIL page — select a
    characteristic, get its views + meaning; below it the 3-D field
    scenes (scrub Vg). The scene rows STAY on the generic page: a
    device with no scene rows (Si — no tube to draw) shows the
    viewer's own named refusal, stated not faked (plan decision 3)."""
    from cntfet.cnt_scene import scene_page_items
    d = '{object}'
    rows = [
        _row(0, [_explorer_item(f'detail-{d}-explorer', 0, 12,
                                f'{d}: characteristics → views + '
                                'meaning', d)], min_height=640),
        # evidence: proof chain on the detail page too (first-class)
        # fg-3: the full 2-D parts view — field overlay + sliders
        _row(3, [_component_item(f'detail-{d}-parts2d', 0, 12,
                                 f'{d}: 2-D parts view — every region '
                                 'with its material, doping and row; '
                                 'field overlay at its own Vdd',
                                 'fet-parts-2d', {'device': d})],
             min_height=460),
        _row(7, [_sapi(f'detail-{d}-parts', 0, 12,
                       f'{d}: parts & purpose — material, doping, '
                       'dielectric, process, row',
                       f'/api/fet/device/{d}/parts', pick='parts')],
             min_height=360),
        _row(8, [_component_item(f'detail-{d}-proof', 0, 12,
                                 f'{d}: is it free to use? — proof '
                                 'chain (click any patent / paper)',
                                 'freedom-proof-panel',
                                 {'path': f'/api/fet/device/{d}/proof'})],
             min_height=420),
        # fp-6 weave: where else this FET lives (pages, partner,
        # cells, comparators) — a reader never dead-ends here.
        _row(9, [_api(f'detail-{d}-links', 0, 12,
                      f'{d}: related pages, partner, cells',
                      f'/api/fet/device/{d}/links')],
             min_height=220),
    ]
    rows += [
        _row(1, scene_page_items(d), min_height=420),
        _row(2, [
            _device_graph(f'detail-{d}-field-potential', 0, 6,
                          f'{d}: potential along the tube '
                          '(F1 sketch; D13 SCF beside it when '
                          'present)', d, 'field-potential'),
            _device_graph(f'detail-{d}-field-density', 1, 6,
                          f'{d}: electron density along the tube',
                          d, 'field-density'),
        ], min_height=430),
    ]
    return {
        'name': 'fet-detail',
        'description': 'The generic FET detail page — one definition '
                       'for every FET, CNT or Si. Open as /display/'
                       'fet-detail?object=<device>: select a FET '
                       'characteristic (IV, switching, transport, '
                       'fields, quality) and see the views that '
                       'explain it plus what it means for '
                       'performance; 2-D profiles and 3-D banded '
                       'field scenes along the tube (scene panels '
                       'refuse by name on a device without scenes).',
        'source_class': '',
        'isPage': True,
        'pageRoute': 'fet-detail',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


def detail_pages(device_names=None, with_scenes=True, source_class=''):
    """fg-2: the ONE generic detail page (arguments ignored)."""
    return [_generic_detail_page()]
