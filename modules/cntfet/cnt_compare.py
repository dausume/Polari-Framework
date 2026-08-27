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
    names = sorted(getattr(r, 'name', '')
                   for r in (tables.get('AlignedCNTFETDevice')
                             or {}).values())
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


def _score_page(device_name):
    d = device_name
    return {
        'name': f'cntfet-score-{d}',
        'description': f'Per-FET scoring page for {d}: figures of '
                       'merit vs their characteristic ideals, the '
                       'FET-validity proofs (score 0 if any fails), '
                       'the Monte Carlo spread, and the competitive '
                       'ranking against every other FET.',
        'source_class': 'AlignedCNTFETDevice',
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
        ]}),
    }


def score_pages(device_names):
    return [_score_page(n) for n in device_names]
