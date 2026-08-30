"""
Selftest for cntfet.cnt_fet_summary (fg-0: the common FET data
format — fet, not cntfet).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_summary
"""

import sys
import types

from cntfet import cnt_derive as cd
from cntfet import selftest_cntfet as st
from cntfet.cnt_fet_summary import (
    SCHEMA, SUMMARY_KEYS, fet_alias, fet_summary,
)
from cntfet.cnt_scoring import score_device
from sifet.si_basis import SEED_TABLES
from sifet.si_device import SI_TABLES, derive_si_device
from sifet.si_device import get_row as si_get

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    """The cntfet fake manager widened with the sifet tables — one
    manager holding BOTH technologies, the way the server does."""
    mgr = st._mgr()
    for t in SI_TABLES:
        mgr.objectTables.setdefault(t, {})
    return mgr


def _seed_si(mgr):
    """sifet seeds, derived-field defaults zeroed (the
    selftest_sifet convention)."""
    for table, seeds in SEED_TABLES:
        for seed in seeds:
            fields = dict(seed)
            if table == 'SiliconMOSFET':
                fields.update(vt0_v=0.0, n_ss=0.0, dibl_v_per_v=0.0,
                              dvt_v=0.0, mu_cm2_per_vs=0.0,
                              vxo_m_per_s=0.0, cinv_f_per_m=0.0,
                              lambda_nm=0.0, equation_revision='',
                              derived_at='', provenance_json='{}')
            row = types.SimpleNamespace(**fields)
            mgr.objectTables[table][id(row)] = row


def _derive_cnt(mgr, name):
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', name)
    rep = cd.derive_device(
        mgr, device,
        parameter_factory=st._row_factory(mgr, 'CNTFETParameterRow'))
    return rep['ok']


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    check('derive: S1 (CNT) and planar-90 (Si) derive on the shared '
          'manager',
          _derive_cnt(mgr, 'cnt-aligned-s1')
          and derive_si_device(
              mgr, si_get(mgr, 'SiliconMOSFET',
                          'si-nmos-planar-90'))['ok'])

    s1 = fet_summary(mgr, 'cnt-aligned-s1')
    si = fet_summary(mgr, 'si-nmos-planar-90')

    # ---- the stable schema ---------------------------------------
    check('schema: both technologies answer ok with fet-summary/1',
          s1.get('ok') and si.get('ok')
          and s1['schema'] == si['schema'] == SCHEMA)
    check('schema: CNT and Si produce the SAME key set — exactly '
          'SUMMARY_KEYS (the binding contract of fg-0)',
          set(s1) == set(si) == set(SUMMARY_KEYS),
          f'S1-only={set(s1) ^ set(SUMMARY_KEYS)} '
          f'Si-only={set(si) ^ set(SUMMARY_KEYS)}')

    # ---- identity -------------------------------------------------
    check('identity: technology / polarity / own-Vdd / derived are '
          'the device\'s own (S1: cnt 0.6 V; planar-90: silicon '
          '1.0 V)',
          s1['identity']['technology'] == 'cnt'
          and si['identity']['technology'] == 'silicon'
          and abs(s1['identity']['vdd_v'] - 0.6) < 1e-9
          and abs(si['identity']['vdd_v'] - 1.0) < 1e-9
          and s1['identity']['derived'] and si['identity']['derived'],
          f"s1={s1['identity']} si={si['identity']}")
    check('identity: both carry their engineered-for targets '
          '(mapping_for), never an empty claim',
          s1['identity']['targets'] and si['identity']['targets']
          and s1['identity']['engineered_for']
          and si['identity']['engineered_for'])

    # ---- sections = the per-endpoint reports ---------------------
    check('figures: the section IS the score report (same score as '
          'score_device) with a non-empty idealTable; validity '
          'surfaced top-level',
          s1['figures'].get('score')
          == score_device(mgr, 'cnt-aligned-s1').get('score')
          and s1['figures'].get('idealTable')
          and si['figures'].get('idealTable')
          and s1['validity'].get('valid') is True
          and si['validity'].get('valid') is True)
    check('speed: no cell-library run on this manager → an INLINE '
          'refusal (never a 500, never a missing key)',
          s1['speed'].get('ok') is False and s1['speed'].get('refusal')
          and si['speed'].get('ok') is False
          and si['speed'].get('refusal'),
          f"s1.speed={s1['speed']} si.speed={si['speed']}")
    check('curves: the servable curve names + the /api/fet points '
          'path',
          'transfer' in s1['curves']['names']
          and s1['curves']['pointsPath'].startswith(
              '/api/fet/device/cnt-aligned-s1/points'))
    check('compare: cross-technology ranking present in both, focus '
          'marked',
          any(r.get('isFocus') for r in
              s1['compare'].get('ranking', []))
          and any(r['device'] == 'cnt-aligned-s1' for r in
                  si['compare'].get('ranking', [])))

    # ---- refusals stay inline ------------------------------------
    underived = fet_summary(mgr, 'cnt-aligned-s1-lg30')
    check('underived comparator: summary still answers ok with the '
          'SAME key set; the fi-4 gate rule holds (score 0, '
          'unproven, validity.reason names the derive affordance)',
          underived.get('ok') and set(underived) == set(SUMMARY_KEYS)
          and underived['figures'].get('score') == 0.0
          and underived['figures'].get('unproven')
          and 'derive' in underived['validity'].get('reason', ''),
          f"figures={underived['figures']}")
    check('unknown device: ok False with the error named (404 at '
          'the route)',
          not fet_summary(mgr, 'no-such-fet').get('ok')
          and 'no device' in fet_summary(mgr, 'no-such-fet')['error'])

    # ---- fet, not cntfet: the /api/fet alias ---------------------
    check('fet_alias: device-scoped routes alias to /api/fet; '
          'catalogue / acts / sifet routes do NOT',
          fet_alias('/api/cntfet/device/{name}/score')
          == '/api/fet/device/{name}/score'
          and fet_alias('/api/cntfet/device/{name}/summary')
          == '/api/fet/device/{name}/summary'
          and fet_alias('/api/cntfet/devices') is None
          and fet_alias('/api/cntfet/devices/{name}') is None
          and fet_alias('/api/sifet/ladder') is None)
    paths = []
    fake = types.SimpleNamespace(falconServer=types.SimpleNamespace(
        add_route=lambda p, r, suffix=None: paths.append(p)))
    from cntfet.cnt_api import CNTFETAPI
    CNTFETAPI(polServer=fake, manager=None)
    check('routes: the server registers every device surface under '
          'BOTH prefixes (summary + score shown), and /api/fet '
          'carries no CNT-catalogue route',
          '/api/fet/device/{name}/summary' in paths
          and '/api/cntfet/device/{name}/summary' in paths
          and '/api/fet/device/{name}/score' in paths
          and '/api/fet/device/{name}/points' in paths
          and not any(p in ('/api/fet/devices', '/api/fet/devices/'
                            '{name}') for p in paths),
          f'{len(paths)} paths')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
