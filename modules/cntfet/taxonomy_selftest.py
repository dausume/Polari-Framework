"""
Selftest for cntfet.cnt_taxonomy_basis (fp-3: optimization classes,
signal-quality scoring, shape types, complementary pairs, regions).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.taxonomy_selftest
"""

import json
import sys

from cntfet.custom import cnt_derive as cd
from cntfet import cnt_taxonomy_basis as tx
from cntfet import cntfet_selftest as st
from cntfet.cnt_device_viz_seed import device_model

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _derive(mgr, name):
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', name)
    rep = cd.derive_device(
        mgr, device,
        parameter_factory=st._row_factory(mgr, 'CNTFETParameterRow'))
    return rep['ok']


def main():
    mgr = st._mgr()
    st._seed_all(mgr)
    check('derive S1 and S1-p', _derive(mgr, 'cnt-aligned-s1')
          and _derive(mgr, 'cnt-aligned-s1-p'))
    id_fn, p, dev, refusal = device_model(mgr, 'cnt-aligned-s1')
    check('device_model(S1) without refusal', refusal is None)

    # ---- seeds ----------------------------------------------------
    ok = True
    for c in tx.SEED_FET_OPTIMIZATION_CLASSES:
        ok = ok and bool(json.loads(c['optimizes_json'])) \
            and bool(json.loads(c['aliases_json'])) \
            and bool(json.loads(c['design_rules_json'])) \
            and c['score_concept'] and c['preferred_region']
    check('SEED_FET_OPTIMIZATION_CLASSES: 2 rows, JSON parses, concept '
          'and region named',
          ok and len(tx.SEED_FET_OPTIMIZATION_CLASSES) == 2
          and {c['score_concept'] for c in
               tx.SEED_FET_OPTIMIZATION_CLASSES}
          == {'fet-switching-quality', 'fet-signal-quality'})
    check('rows construct: FETOptimizationClass / FETShapeType / '
          'ComplementaryPair',
          hasattr(tx.FETOptimizationClass(
              **{**tx.SEED_FET_OPTIMIZATION_CLASSES[0], 'manager': None}),
              'optimizes_json')
          and hasattr(tx.FETShapeType(
              **{**tx.SEED_FET_SHAPE_TYPES[0], 'manager': None}),
              'scale_length_formula')
          and hasattr(tx.ComplementaryPair(
              **{**tx.SEED_COMPLEMENTARY_PAIRS[0], 'manager': None}),
              'conditions_json'))
    shapes = {s['name'] for s in tx.SEED_FET_SHAPE_TYPES}
    check('SEED_FET_SHAPE_TYPES: 7 shapes, every row has a scale-length '
          'formula, a cited source and priors',
          shapes == {'planar-bulk', 'soi', 'finfet', 'gaa-nanowire',
                     'gaa-nanosheet', 'cnt-gaa', 'tfet'}
          and all(s['scale_length_formula'] and s['scale_length_source']
                  and s['priors_source'] and json.loads(s['materials_json'])
                  for s in tx.SEED_FET_SHAPE_TYPES))
    cited = set()
    for s in tx.SEED_FET_SHAPE_TYPES:
        for tag in tx.TAXONOMY_CITATIONS:
            if tag in s['scale_length_source'] + s['priors_source']:
                cited.add(tag)
    for t in tx.SIGNAL_TERMS.values():
        for tag in tx.TAXONOMY_CITATIONS:
            if tag in t['ideal_why']:
                cited.add(tag)
    check('citations: shape sources + signal ideals resolve to '
          'TAXONOMY_CITATIONS entries with full references',
          {'[YAN92]', '[AP97]', '[TN09]', '[EKV95]', '[SIL96]',
           '[RAZ01]'} <= cited
          and all(v['citation'] for v in tx.TAXONOMY_CITATIONS.values()))
    terms = {t['name'] for t in tx.SEED_SIGNAL_SCORE_TERMS}
    check('SEED_SIGNAL_SCORE_TERMS match SIGNAL_TERMS; concept '
          'fet-signal-quality weights every term; no collision with '
          'FET_TERMS',
          terms == set(tx.SIGNAL_TERMS)
          and all(json.loads(t['normalization_json'])['method']
                  == 'min-max' for t in tx.SEED_SIGNAL_SCORE_TERMS)
          and tx.SEED_SIGNAL_SCORE_CONCEPTS[0]['name']
          == 'fet-signal-quality'
          and {w['term'] for w in json.loads(
              tx.SEED_SIGNAL_SCORE_CONCEPTS[0]['term_weights_json'])}
          == set(tx.SIGNAL_TERMS)
          and not set(tx.SIGNAL_TERMS) & set(tx.FET_TERMS))

    # ---- signal frame on S1 --------------------------------------
    f = tx.signal_frame(id_fn, p, dev.temperature_k)
    gmid, lim = f['gm_over_id_per_v'], f['gm_over_id_limit_per_v']
    print(f'  S1 analog bias Vgs={f["bias"]["vgs_v"]:.3f} V '
          f'(Vt={f["bias"]["vt_v"]:.3f}), Vds={f["bias"]["vds_v"]:.2f} V: '
          f'Id={f["id_ua"]:.3f} uA gm={f["gm_us"]:.2f} uS '
          f'gds={f["gds_us"]:.3f} uS gm/Id={gmid:.2f}/V '
          f'(limit {lim:.2f}) gain={f["intrinsic_gain"]:.1f} '
          f'headroom={f["headroom_fraction"]:.3f} '
          f'nonlin={f["gm_nonlinearity_per_v"]:.2f}/V')
    check(f'signal frame: 0 < gm/Id = {gmid:.2f}/V < weak-inversion '
          f'limit {lim:.2f}/V (1/(n φt), n_ss = {p["n_ss"]:.3f})',
          gmid is not None and 0 < gmid < lim)
    check(f'signal frame: intrinsic gain gm/gds = '
          f'{f["intrinsic_gain"]:.1f} > 1',
          f['intrinsic_gain'] is not None and f['intrinsic_gain'] > 1)
    check('signal frame: bias is Vt + 0.15 V at Vds = Vdd/2 (knobs '
          'echoed)', abs(f['bias']['vgs_v'] - f['bias']['vt_v'] - 0.15)
          < 1e-9 and abs(f['bias']['vds_v'] - 0.3) < 1e-9
          and f['knobs']['vov_bias_v'] == 0.15)

    # ---- signal score ---------------------------------------------
    sig = tx.score_signal(mgr, 'cnt-aligned-s1')
    print(f'  S1 signal score = {sig["score"]:.4f}; terms: '
          + ', '.join(f'{r["term"]}={r.get("normalized")}'
                      for r in sig['terms']))
    check(f'score_signal(S1) = {sig["score"]:.4f} in (0, 1), valid FET, '
          'all 4 terms found',
          0 < sig['score'] < 1 and sig['validity']['valid']
          and not sig['termsMissing'] and len(sig['terms']) == 4)
    sw = tx.score_device(mgr, 'cnt-aligned-s1')
    cls = tx.classify_optimization(sw['score'], sig['score'])
    print(f'  S1 switching {sw["score"]:.4f} vs signal {sig["score"]:.4f} '
          f'→ {cls["suited_to"]} (margin {cls["margin"]:+.4f}): '
          f'{cls["why"]}')
    check('classify_optimization names a class with a why and the margin',
          cls['suited_to'] in ('switching-optimized', 'signal-optimized',
                               'either')
          and cls['why'] and abs(cls['margin']
                                 - (sig['score'] - sw['score'])) < 1e-9)
    check('classify_optimization: 0/0 → neither; 0.9/0.2 → switching; '
          '0.2/0.9 → signal; 0.5/0.52 → either',
          tx.classify_optimization(0, 0)['suited_to'] == 'neither'
          and tx.classify_optimization(0.9, 0.2)['suited_to']
          == 'switching-optimized'
          and tx.classify_optimization(0.2, 0.9)['suited_to']
          == 'signal-optimized'
          and tx.classify_optimization(0.5, 0.52)['suited_to'] == 'either')

    # ---- validity gate --------------------------------------------
    p_dead = {**p, 'vt0_v': 3.0}
    dead_fn = (lambda vg, vd:
               tx.vs_terminal_current(vg, vd, p_dead)['id_a'])
    dead = tx.score_signal_from_model(dead_fn, p_dead, 300.0, mgr)
    check('validity gate zeros the signal score for a dead model '
          f'(vt0 = 3 V): score {dead["score"]}, failed '
          f'{dead["validity"]["failed"]}',
          dead['score'] == 0.0 and not dead['validity']['valid']
          and dead['validity']['failed'])
    under = tx.score_signal(mgr, 'cnt-aligned-s1-lg30')
    check('underived device → signal score 0 with the derive affordance',
          under['score'] == 0.0 and under.get('unproven')
          and 'derive' in under['validity']['reason'])

    # ---- shapes ---------------------------------------------------
    sh = tx.shape_of(dev, mgr)
    check('shape_of(S1) = cnt-gaa with the [VS1] eq.(7) formula as data',
          sh['ok'] and sh['shape'] == 'cnt-gaa'
          and '[VS1]' in sh['row']['scale_length_source'])
    import types
    si = types.SimpleNamespace(name='si-fin', shape='finfet')
    si_none = types.SimpleNamespace(name='si-x')
    check('shape_of(SiliconMOSFET-like row) reads its shape field; a '
          'row without one gets the affordance',
          tx.shape_of(si)['shape'] == 'finfet'
          and not tx.shape_of(si_none)['ok']
          and 'affordance' in tx.shape_of(si_none))

    # ---- complementary pair ---------------------------------------
    pc = tx.check_pair(mgr, 'cnt-s1-pair')
    by = {c['name']: c for c in pc['checks']}
    print(f'  pair check: polarity {by["polarity"]["evidence"]}, '
          f'vt-symmetry {by["vt-symmetry"]["evidence"]}, '
          f'drive {by["drive-match"]["evidence"]["ratio"]:.3f}')
    check('check_pair(s1 ↔ s1-p): polarity differs',
          by['polarity']['passed'])
    check('check_pair: vt-symmetry passes under the explicit mirror '
          f'(Vt_n = {by["vt-symmetry"]["evidence"]["vt_n_v"]:.3f} V, '
          f'Vt_p = {by["vt-symmetry"]["evidence"]["vt_p_v"]:.3f} V, gap '
          f'{by["vt-symmetry"]["evidence"]["gap_v"]:.3g} V)',
          by['vt-symmetry']['passed']
          and by['vt-symmetry']['evidence']['vt_p_v'] < 0)
    check('check_pair: drive-match passes (ratio 1 by construction) and '
          'the payload SAYS the polarity is a label today',
          by['drive-match']['passed'] and pc['passed']
          and 'LABEL' in pc['caveat'] and 'mirror' in pc['caveat'])
    co = tx.complementary_of(mgr, 'cnt-aligned-s1')
    check('complementary_of(S1) = cnt-aligned-s1-p as pull-up with check',
          co['partner'] == 'cnt-aligned-s1-p' and co['check']['passed'])
    none = tx.complementary_of(mgr, 'cnt-aligned-s1-lg30')
    check('complementary_of(lg30) = none declared with affordance',
          none['partner'] is None and none['status'] == 'none declared'
          and 'ComplementaryPair' in none['affordance'])

    # ---- regions --------------------------------------------------
    rs = tx.regions_summary(id_fn, p, dev)
    names = [r['name'] for r in rs['regions']]
    b = {r['name']: r['boundaries'] for r in rs['regions']}
    knees = [v for v in b['saturation']['vdsat_per_vg']
             if v['vds_at_knee_v'] is not None]
    print(f'  regions: Vt(Vdd)={b["sub-threshold"]["vt_at_vdd_v"]:.3f} V '
          f'Vt+Vov_min={b["linear"]["vt_on_v"]:.3f} V; Vdsat knees: '
          + ', '.join(f'Vg {v["vgs_v"]}: {v["vds_at_knee_v"]:.3f} V'
                      for v in knees))
    check('regions_summary: 3 regions (sub-threshold, linear, '
          'saturation) with numeric boundaries and plain meaning',
          names == ['sub-threshold', 'linear', 'saturation']
          and isinstance(b['sub-threshold']['vt_at_vdd_v'], float)
          and b['linear']['vt_on_v'] > b['sub-threshold']['vt_at_vdd_v']
          and knees
          and all(r['meaning'] and r['used_by'] and r['where']
                  for r in rs['regions'])
          and 'cnt_states (fi-0)' in rs['cites'])

    # ---- report + graphs ------------------------------------------
    rep = tx.device_taxonomy_report(mgr, 'cnt-aligned-s1')
    check('device_taxonomy_report(S1): shape/optimization/complementary/'
          'regions/fidelity all present and JSON-serializable',
          {'shape', 'optimization', 'complementary', 'regions',
           'fidelity'} <= set(rep)
          and rep['optimization']['suited_to'] == cls['suited_to']
          and json.dumps(rep) is not None)
    ok = True
    for g in tx.SEED_CNT_TAXONOMY_GRAPHS:
        cfg = json.loads(g['definition'])['graphConfig']
        ok = ok and cfg['xDimension'] == 'x' and 'series' in json.dumps(cfg)
    check('graph seeds round-trip (signal-terms, optimization-radar) '
          'and CURVE_BUILDERS cover them',
          ok and {g['name'] for g in tx.SEED_CNT_TAXONOMY_GRAPHS}
          == {'cnt-device-signal-terms', 'cnt-device-optimization-radar'}
          and set(tx.CURVE_BUILDERS) == {'signal-terms',
                                         'optimization-radar'})
    rows_s = tx.CURVE_BUILDERS['signal-terms'](id_fn, p, dev, mgr, None)
    rows_r = tx.CURVE_BUILDERS['optimization-radar'](id_fn, p, dev, mgr,
                                                     None)
    check('curve builders: 4 signal dots + hguide; radar has switching '
          'and signal series',
          sum(r['style'] == 'dot' for r in rows_s) == 4
          and any(r['style'] == 'hguide' for r in rows_s)
          and {r['series'] for r in rows_r}
          >= {'switching', 'signal', 'ideal'})

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
