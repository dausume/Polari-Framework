"""
sifet pages selftest (check() style, no server): the FET SET flush —
every seeded silicon FET derives, has a shape, a partner where one
is declared (checked with real numbers), competes in the cross-
technology ranking, owns a score + detail page, sits on sifet-home,
and drives the cell library through a pair-aware p card.

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m sifet.selftest_sifet_pages
"""

import json
import math
import sys
import tempfile

from cntfet import cnt_derive as cd
from cntfet import cnt_taxonomy as tx
from cntfet import selftest_cntfet as st
from cntfet.cnt_compare import compare_devices
from cntfet.cnt_device_viz import device_model
from cntfet.cnt_osdi import find_ngspice
from cntfet.cnt_scoring import score_device
from sifet import si_model as sm
from sifet.si_basis import SEED_TABLES
from sifet.si_device import derive_si_device, get_row, metric_spec
from sifet.si_pages_seed import (
    REFINEMENT_POINTS_PATH, SEED_SI_PAGE_DISPLAYS, SEED_SI_SCORE_PAGES,
    SI_DEVICE_NAMES, refinement_points,
)

_results = []
REGISTERED = {'class-rows-table', 'api-json-panel', 'named-graph-panel'}


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _seed_si(mgr):
    for table, seeds in SEED_TABLES:
        mgr.objectTables.setdefault(table, {})
        for seed in seeds:
            fields = dict(seed)
            if table == 'SiliconMOSFET':
                fields.update(vt0_v=0.0, n_ss=0.0, dibl_v_per_v=0.0,
                              dvt_v=0.0, mu_cm2_per_vs=0.0,
                              vxo_m_per_s=0.0, cinv_f_per_m=0.0,
                              lambda_nm=0.0, equation_revision='',
                              derived_at='', provenance_json='{}')
            st._row_factory(mgr, table)(**fields)
    for table in ('ComplementaryPair', 'FETShapeType',
                  'CellCharacterizationRun'):
        mgr.objectTables.setdefault(table, {})
    # si_refinement._rows reads LIST-valued tables (list(dict) would
    # yield ids) — seed those the way selftest_refinement does.
    from sifet.si_refinement import (
        SEED_REFINEMENT_ROUTES, SEED_REFINEMENT_STEPS, SEED_SILICON_GRADES,
    )
    import types
    for table, seeds in (('SiliconGrade', SEED_SILICON_GRADES),
                         ('RefinementStep', SEED_REFINEMENT_STEPS),
                         ('RefinementRoute', SEED_REFINEMENT_ROUTES)):
        mgr.objectTables[table] = [types.SimpleNamespace(**s)
                                   for s in seeds]


def _components(definition):
    names = set()
    for row in json.loads(definition)['rows']:
        for item in row['items']:
            names.add(item['componentProps']['componentName'])
    return names


def _pair_report(name, vdd):
    pc = tx.check_pair(mgr_global, name, knobs={'vdd_v': vdd})
    by = {c['name']: c for c in pc['checks']}
    vt = by['vt-symmetry']['evidence']
    dr = by['drive-match']['evidence']
    w_ratio = (dr['ion_n_ua'] / dr['ion_p_ua'] if dr['ion_p_ua'] > 0
               else float('inf'))
    print(f'  {name} @ Vdd {vdd} V: Vt_n = {vt["vt_n_v"]:.3f} V, Vt_p = '
          f'{vt["vt_p_v"]:.3f} V, gap = {vt["gap_v"]*1e3:.1f} mV; Ion_n '
          f'= {dr["ion_n_ua"]:.1f} uA, Ion_p = {dr["ion_p_ua"]:.1f} uA, '
          f'ratio = {dr["ratio"]:.3f} (window {dr["window"]}); '
          f'W_p/W_n to match = {w_ratio:.2f}')
    return pc, by, w_ratio


mgr_global = None


def main():
    global mgr_global
    mgr = st._mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    mgr_global = mgr
    pfac = st._row_factory(mgr, 'CNTFETParameterRow')
    for n in ('cnt-aligned-s1', 'cnt-aligned-s1-p'):
        cd.derive_device(mgr, cd.get_row(mgr, 'AlignedCNTFETDevice', n),
                         parameter_factory=pfac)

    # ---- 1. every Si device derives; metric_spec gives its Vdd ----
    reports = {n: derive_si_device(mgr, get_row(mgr, 'SiliconMOSFET', n))
               for n in SI_DEVICE_NAMES}
    check(f'derive: all {len(SI_DEVICE_NAMES)} seeded SiliconMOSFETs '
          'derive ok (3 new: pmos finfet HfO2, nmos planar sol-gel '
          'SiO2, pmos planar HfO2)',
          len(SI_DEVICE_NAMES) == 7
          and all(r['ok'] for r in reports.values()),
          str({n: r.get('error') for n, r in reports.items()
               if not r['ok']}))
    specs = {n: metric_spec(get_row(mgr, 'SiliconMOSFET', n))
             for n in SI_DEVICE_NAMES}
    check('metric_spec: every device carries its own Vdd (planar 1.0 V, '
          'finfet 0.8 V) and a per-um Vt criterion',
          all(s['vdd_v'] == get_row(mgr, 'SiliconMOSFET', n).vdd_v
              and s['id_crit_a'] > 0 for n, s in specs.items())
          and specs['si-nmos-finfet-solgel-hfo2']['vdd_v'] == 0.8
          and specs['si-pmos-planar-90']['vdd_v'] == 1.0,
          str({n: s['vdd_v'] for n, s in specs.items()}))
    check('every device note states its comparison purpose and '
          '"unproven → scores 0 until derived"',
          all('unproven' in d['notes'] and 'xists to' in d['notes']
              for d in dict(SEED_TABLES)['SiliconMOSFET']))
    sio2 = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-solgel-sio2')
    ref = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    check('sol-gel TEOS SiO2 (4 nm) vs 2 nm thermal: LOWER Cinv, '
          'LARGER scale length (the honest cost of the thicker film)',
          sio2.cinv_f_per_m < ref.cinv_f_per_m
          and sio2.lambda_nm > ref.lambda_nm,
          f'Cinv {sio2.cinv_f_per_m:.3e} vs {ref.cinv_f_per_m:.3e} F/m; '
          f'lambda {sio2.lambda_nm:.1f} vs {ref.lambda_nm:.1f} nm')
    pfin = get_row(mgr, 'SiliconMOSFET', 'si-pmos-finfet-solgel-hfo2')
    php = get_row(mgr, 'SiliconMOSFET', 'si-pmos-planar-solgel-hfo2')
    check('new PMOS rows: Vt negative, hole mobility below the NMOS '
          'partner, finfet n_ss below planar',
          pfin.vt0_v < 0 and php.vt0_v < 0
          and php.mu_cm2_per_vs < get_row(
              mgr, 'SiliconMOSFET', 'si-nmos-planar-solgel-hfo2')
          .mu_cm2_per_vs and pfin.n_ss < php.n_ss,
          f'Vt pfin {pfin.vt0_v:.3f} V, php {php.vt0_v:.3f} V; mu_p '
          f'{php.mu_cm2_per_vs:.0f} cm^2/Vs; n_ss fin {pfin.n_ss:.3f} '
          f'planar {php.n_ss:.3f}')

    # ---- 2. shape_of maps Si rows through their shape ROW ---------
    shapes = {n: tx.shape_of(get_row(mgr, 'SiliconMOSFET', n), mgr)
              for n in SI_DEVICE_NAMES}
    check('shape_of: planar-90nm-class rows → planar-bulk, finfet-class '
          'rows → finfet (resolved through the SiliconFETShape row\'s '
          'kind), every one ok',
          all(s['ok'] for s in shapes.values())
          and shapes['si-nmos-planar-90']['shape'] == 'planar-bulk'
          and shapes['si-pmos-finfet-solgel-hfo2']['shape'] == 'finfet'
          and 'SiliconFETShape' in shapes['si-nmos-planar-90']['how'],
          str({n: s.get('shape') or s.get('error')
               for n, s in shapes.items()}))

    # ---- 3. pairs with real numbers -------------------------------
    mu_n_eff = sm.effective_mobility(1e17, 'n')[1]
    mu_p_eff = sm.effective_mobility(1e17, 'p')[1]
    print(f'  mu_n_eff = {mu_n_eff:.0f}, mu_p_eff = {mu_p_eff:.0f} '
          f'cm^2/Vs → mu_n/mu_p = {mu_n_eff/mu_p_eff:.2f}')
    pc1, by1, w1 = _pair_report('si-planar-90-pair', 1.0)
    check('si-planar-90-pair: polarity differs; Vt symmetric (|Vt_n| = '
          '|Vt_p| within tol from the ±0.6 V Vfb priors on mirrored '
          '1e17 dopings)',
          by1['polarity']['passed'] and by1['vt-symmetry']['passed']
          and by1['vt-symmetry']['evidence']['vt_p_v'] < 0,
          str(by1['vt-symmetry']['evidence']))
    ratio1 = by1['drive-match']['evidence']['ratio']
    check('si-planar-90-pair: drive ratio Ion_p/Ion_n at equal W is a '
          'REAL hole number (< 1, not the CNT mirror\'s 1.0) and the '
          f'matching width W_p/W_n = {w1:.2f} lies between 1 and '
          f'mu_n/mu_p = {mu_n_eff/mu_p_eff:.2f} (VS: part ballistic, '
          'v_xo shared)',
          0.0 < ratio1 < 1.0 and 1.0 < w1 <= mu_n_eff / mu_p_eff + 0.05,
          f'ratio {ratio1:.3f}, drive-match passed = '
          f'{by1["drive-match"]["passed"]} (window '
          f'{by1["drive-match"]["evidence"]["window"]})')
    pc2, by2, w2 = _pair_report('si-finfet-hfo2-pair', 0.8)
    check('si-finfet-hfo2-pair: polarity + Vt symmetry pass; drive '
          f'ratio real; fins per n fin to match = {math.ceil(w2)}',
          by2['polarity']['passed'] and by2['vt-symmetry']['passed']
          and 0.0 < by2['drive-match']['evidence']['ratio'] < 1.0
          and 1 < w2 < 4,
          f'ratio {by2["drive-match"]["evidence"]["ratio"]:.3f}')
    co = tx.complementary_of(mgr, 'si-nmos-planar-90', {'vdd_v': 1.0})
    co_fin = tx.complementary_of(mgr, 'si-pmos-finfet-solgel-hfo2',
                                 {'vdd_v': 0.8})
    co_none = tx.complementary_of(mgr, 'si-nmos-planar-solgel-sio2')
    check('complementary_of(si-nmos-planar-90) = si-pmos-planar-90 '
          '(pull-up) with the check; finfet pmos → its nmos; the '
          'sol-gel SiO2 NMOS = none declared with affordance',
          co['partner'] == 'si-pmos-planar-90' and 'pull-down' in co['role']
          and co['check']['ok'] and co['check']['passed']
          and co_fin['partner'] == 'si-nmos-finfet-solgel-hfo2'
          and co_none['partner'] is None and 'affordance' in co_none)

    # ---- 4. scoring + cross-technology ranking --------------------
    scores = {n: score_device(mgr, n) for n in SI_DEVICE_NAMES}
    valid = {n: s['validity']['valid'] for n, s in scores.items()}
    check('score_device: every Si device is scored; the 3 PMOS rows are '
          'valid FETs in their own frame (frame_aware_id_fn) with '
          '0 < score < 1; the sol-gel SiO2 NMOS (Vt '
          f'{sio2.vt0_v:.3f} V) is judged at its OWN 1.0 V supply '
          '(cnt_scoring.device_knobs) and is a valid FET too — the '
          'validity window is the device\'s Vdd, not the CNT 0.6 V',
          all(valid[n] and 0.0 < scores[n]['score'] < 1.0
              for n in SI_DEVICE_NAMES)
          and scores['si-nmos-planar-solgel-sio2']['validity']['knobs']
          ['vdd_v'] == 1.0,
          str({n: (valid[n], round(s['score'], 3))
               for n, s in scores.items()}))
    xc = compare_devices(mgr, 'si-nmos-planar-90')
    ranked = [r['device'] for r in xc['ranking']]
    check('compare_devices from a Si focus ranks CNT + all 7 Si devices '
          f'(leader {xc["leader"]}, focus rank {xc["focusRank"]}/'
          f'{xc["of"]})',
          xc['ok'] and all(n in ranked for n in SI_DEVICE_NAMES)
          and any(n.startswith('cnt-') for n in ranked)
          and xc['of'] >= 9, str(ranked))

    # ---- 5. pages ----------------------------------------------------
    by_route = {p['pageRoute']: p for p in SEED_SI_SCORE_PAGES}
    check('SEED_SI_SCORE_PAGES: one score + one detail page per Si '
          'device (14), routes cntfet-score-/cntfet-detail-{name}, '
          'source_class SiliconMOSFET',
          len(SEED_SI_SCORE_PAGES) == 2 * len(SI_DEVICE_NAMES)
          and all(f'cntfet-score-{n}' in by_route
                  and f'cntfet-detail-{n}' in by_route
                  for n in SI_DEVICE_NAMES)
          and all(p['source_class'] == 'SiliconMOSFET' and p['isPage']
                  for p in SEED_SI_SCORE_PAGES))
    det = json.loads(by_route['cntfet-detail-si-nmos-planar-90']
                     ['definition'])
    ids = [i['id'] for r in det['rows'] for i in r['items']]
    check('Si detail pages drop the CNT-only field scenes '
          '(with_scenes=False) but keep the explorer + links',
          not any('scene' in i or 'field' in i for i in ids)
          and any('explorer' in i for i in ids)
          and any('links' in i for i in ids), str(ids))
    score_def = by_route['cntfet-score-si-pmos-planar-90']['definition']
    check('Si score page points every panel at /api/cntfet/device/'
          '{si-name}/… (the shared VS surfaces accept Si names)',
          '/api/cntfet/device/si-pmos-planar-90/compare' in score_def
          and 'curve=score-terms' in score_def)
    home = SEED_SI_PAGE_DISPLAYS[0]
    comps = _components(home['definition'])
    check('sifet-home (route sifet) uses only registered components '
          '(class-rows-table, api-json-panel, named-graph-panel)',
          home['pageRoute'] == 'sifet' and home['name'] == 'sifet-home'
          and comps <= REGISTERED and comps == REGISTERED, str(comps))
    hd = home['definition']
    check('sifet-home: SiliconMOSFET + dielectric/doping/shape tables, '
          '/api/sifet/capability, the cross-technology ranking from '
          'si-nmos-planar-90, both refinement graphs (dataPath = '
          'REFINEMENT_POINTS_PATH) and /api/sifet/refinement',
          all(k in hd for k in (
              '"SiliconMOSFET"', '"SolGelDielectric"',
              '"SiliconDopingProfile"', '"SiliconFETShape"',
              '/api/sifet/capability',
              '/api/cntfet/device/si-nmos-planar-90/compare',
              'si-refinement-impurity-ladder', 'si-refinement-scheil',
              REFINEMENT_POINTS_PATH.format(route='pv-open-route',
                                            curve='scheil'),
              '"/api/sifet/refinement"')))
    pts_l = refinement_points(mgr, 'pv-open-route', 'impurity-ladder')
    pts_s = refinement_points(mgr, 'pv-open-route', 'scheil')
    check('refinement_points serves both graph curves with rows '
          '(x/y/series/style) — the integrator routes '
          f'{REFINEMENT_POINTS_PATH}',
          pts_l.get('ok') and pts_s.get('ok')
          and all({'x', 'y', 'series', 'style'} <= set(r)
                  for r in pts_l['rows'] + pts_s['rows'])
          and not refinement_points(mgr, 'pv-open-route', 'nope')['ok'],
          f"ladder {len(pts_l.get('rows', []))} rows, scheil "
          f"{len(pts_s.get('rows', []))} rows; "
          f"{pts_l.get('error', '')}{pts_s.get('error', '')}")

    # ---- 6. cells on silicon, pair-aware p card -----------------------
    from cntfet.cnt_cell_library import _pair_params, characterize_cells
    from cntfet.cnt_cells import _cards
    nmos = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    p_n, p_p, err = _pair_params(mgr, nmos)
    card_n, card_p = _cards(p_n, p_p)
    check('_pair_params(si-nmos-planar-90): n card = the Si p (W = 1 um '
          'per-device Cinv); p card = si-pmos-planar-90\'s OWN derived '
          'p (ptype 1, hole mobility), not the mirror',
          err is None and 'partner "si-pmos-planar-90"' in p_p['p_side']
          and p_p['mu_m2_per_vs'] < p_n['mu_m2_per_vs']
          and p_p['ptype'] == 1 and 'ptype=1' in card_p
          and abs(p_n['cinv_f_per_m'] - nmos.cinv_f_per_m) < 1e-15,
          f"p_side = {p_p.get('p_side')}; mu_n "
          f"{p_n['mu_m2_per_vs']*1e4:.0f} vs mu_p "
          f"{p_p['mu_m2_per_vs']*1e4:.0f} cm^2/Vs")
    p_n2, p_p2, _e = _pair_params(mgr, sio2)
    check('device without a declared partner falls back to the mirror '
          'card and says so',
          'mirror' in p_p2['p_side'] and p_p2['mu_m2_per_vs']
          == p_n2['mu_m2_per_vs'], p_p2['p_side'])
    ngspice_path, why = find_ngspice()
    if ngspice_path is None:
        check(f'characterize_cells on silicon honestly SKIPPED — {why}',
              True)
    else:
        from cntfet.cnt_cells import _tau_estimate
        tau = _tau_estimate(p_n, nmos.vdd_v)
        cin = 2.0 * p_n['cinv_f_per_m'] * p_n['lg_m'] + 2e-18
        lib = characterize_cells(
            mgr, nmos, cells=['cinv', 'cnand2'], drives=(1,),
            vdd=nmos.vdd_v, slews_s=[2.0 * tau, 8.0 * tau],
            loads_f=[cin, 4.0 * cin],
            workdir=tempfile.mkdtemp(prefix='sifet-lib-'),
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        names = {c['libertyName'] for c in lib.get('cells', [])}
        mono = lib.get('monotone', [])
        check('characterize_cells(si-nmos-planar-90, [cinv, cnand2], '
              'drive 1, 2x2 grid) at Vdd 1.0 V: ok, INVX1 + NAND2X1, '
              'monotone in load, STA gate reported, pair-aware p card',
              lib.get('ok') and names == {'INVX1', 'NAND2X1'}
              and mono and all(m['monotoneInLoad'] for m in mono)
              and not lib.get('failures')
              and 'staGate' in lib and 'partner' in lib.get('pSide', ''),
              f"ok={lib.get('ok')} err={lib.get('error', '')[:200]} "
              f"failures={lib.get('failures')} sta="
              f"{ {k: v for k, v in (lib.get('staGate') or {}).items() if k in ('ok', 'refusal', 'verdict', 'error')} } "
              f"tau={tau:.2e}s")
        inv = next((c for c in lib.get('cells', [])
                    if c['libertyName'] == 'INVX1'), None)
        if inv:
            e = inv['energy'].get('A', {})
            print(f"  INVX1 mid-grid energy rise {e.get('rise_aJ', 0):.1f} "
                  f"aJ / fall {e.get('fall_aJ', 0):.1f} aJ")

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
