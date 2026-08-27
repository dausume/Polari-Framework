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

Per-object surfaces ([[per-object-display-config]]): one seeded
DisplayDefinition PER DEVICE (`cntfet-score-{device}`, route
`cntfet-score-{device}`) generated from the seeded device list —
graphs are the same per-KIND GraphDefinition rows pointed at that
device's paths, plus the ranking/validity API panels.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/compare)
  - cntfet.cnt_device_viz (curve 'compare')
  - polariServer (SEED_CNT_SCORE_PAGES → DisplayDefinition seeds)
  - cntfet.selftest_cntfet
"""

import json

from cntfet.cnt_pages_seed import _api, _device_graph, _row
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


def _score_page(device_name, source_class='AlignedCNTFETDevice'):
    d = device_name
    return {
        'name': f'cntfet-score-{d}',
        'description': f'Per-FET scoring page for {d}: figures of '
                       'merit vs their characteristic ideals, the '
                       'FET-validity proofs (score 0 if any fails), '
                       'the Monte Carlo spread, and the competitive '
                       'ranking against every other FET.',
        'source_class': source_class,
        'isPage': True,
        'pageRoute': f'cntfet-score-{d}',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': [
            _row(0, [
                _device_graph(f'score-{d}-terms', 0, 6,
                              f'{d}: figures of merit vs ideals '
                              '(MC spread, best/worst)',
                              d, 'score-terms'),
                _api(f'score-{d}-validity', 1, 6,
                     f'{d}: is it a FET? (proofs) + score by '
                     'characteristic equations',
                     f'/api/cntfet/device/{d}/score?samples=100'),
            ], min_height=430),
            _row(1, [
                _device_graph(f'score-{d}-compare', 0, 6,
                              f'{d} vs every FET: score + terms '
                              '(◀ = this device)',
                              d, 'compare'),
                _api(f'score-{d}-ranking', 1, 6,
                     f'{d}: competitive ranking + gap to the leader',
                     f'/api/cntfet/device/{d}/compare'),
            ], min_height=430),
            _row(2, [
                _device_graph(f'score-{d}-transfer-states', 0, 6,
                              f'{d}: operating states on Id(Vg)',
                              d, 'transfer-states'),
                _device_graph(f'score-{d}-envelope', 1, 6,
                              f'{d}: stochastic Id(Vg) envelope',
                              d, 'transfer-envelope'),
            ], min_height=430),
            _row(3, [_api(f'score-{d}-links', 0, 12,
                          f'{d}: related pages, partner, cells',
                          f'/api/cntfet/device/{d}/links')],
                 min_height=220),
        ]}),
    }


def score_pages(device_names, source_class='AlignedCNTFETDevice'):
    return [_score_page(n, source_class) for n in device_names]


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


def _detail_page(device_name, with_scenes=True,
                 source_class='AlignedCNTFETDevice'):
    """fv-5: the per-FET DETAIL page — select a characteristic, get
    its views + meaning; below it the 3-D field scenes (scrub Vg).
    with_scenes=False drops the scene + field rows (fp-2 silicon
    devices: the field scenes are CNT-only and refuse by name — a
    Si detail page has no tube to draw)."""
    from cntfet.cnt_scene import scene_page_items
    d = device_name
    rows = [
        _row(0, [_explorer_item(f'detail-{d}-explorer', 0, 12,
                                f'{d}: characteristics → views + '
                                'meaning', d)], min_height=640),
        # fp-6 weave: where else this FET lives (pages, partner,
        # cells, comparators) — a reader never dead-ends here.
        _row(9, [_api(f'detail-{d}-links', 0, 12,
                      f'{d}: related pages, partner, cells',
                      f'/api/cntfet/device/{d}/links')],
             min_height=220),
    ]
    if with_scenes:
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
        'name': f'cntfet-detail-{d}',
        'description': f'Detail view of {d}: select a FET '
                       'characteristic (IV, switching, transport, '
                       'fields, quality) and see the views that '
                       'explain it plus what it means for '
                       'performance; 2-D profiles and 3-D banded '
                       'field scenes along the tube.',
        'source_class': source_class,
        'isPage': True,
        'pageRoute': f'cntfet-detail-{d}',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


def detail_pages(device_names, with_scenes=True,
                 source_class='AlignedCNTFETDevice'):
    return [_detail_page(n, with_scenes, source_class)
            for n in device_names]
