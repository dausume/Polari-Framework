"""
sifet ladder selftest (check() style, no server): seeds the cntfet S1
rows + the sifet SEED_TABLES + the ladder rows into a plain manager,
derives the FreePDK45-class pair, and proves the two-axis ladder,
the anchors, the evidence / IP shapes and the report.

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m sifet.ladder_selftest
"""

import json
import os
import sys
import types

from cntfet import cnt_evidence_basis as ev
from cntfet import cnt_ip_basis as ip
from cntfet import cntfet_selftest as st
from cntfet.cnt_scoring_seed import fet_validity
from sifet import si_ladder_basis as L
from sifet.si_basis import SEED_TABLES
from sifet.custom.si_device import derive_si_device, get_row, si_device_model

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _seed(mgr, table, seeds, defaults=None):
    mgr.objectTables.setdefault(table, {})
    for seed in seeds:
        fields = dict(defaults or {})
        fields.update(seed)
        row = types.SimpleNamespace(**fields)
        mgr.objectTables[table][id(row)] = row


_DEV_DEFAULTS = dict(vt0_v=0.0, n_ss=0.0, dibl_v_per_v=0.0, dvt_v=0.0,
                     mu_cm2_per_vs=0.0, vxo_m_per_s=0.0, cinv_f_per_m=0.0,
                     lambda_nm=0.0, equation_revision='', derived_at='',
                     provenance_json='{}')


def _manager():
    mgr = st._mgr()
    st._seed_all(mgr)
    for table, seeds in SEED_TABLES:
        _seed(mgr, table, seeds,
              _DEV_DEFAULTS if table == 'SiliconMOSFET' else None)
    _seed(mgr, 'SiliconProcessNode', L.SEED_SILICON_PROCESS_NODES)
    _seed(mgr, 'CNTCalibrationAnchor', L.SEED_SILICON_ANCHORS)
    _seed(mgr, 'EvidenceItem', ev.SEED_EVIDENCE + L.SEED_LADDER_EVIDENCE)
    _seed(mgr, 'TechnologyIPRecord', ip.SEED_TECHNOLOGY_IP + L.SEED_LADDER_IP)
    return mgr


def main():
    mgr = _manager()
    nodes = L.SEED_SILICON_PROCESS_NODES
    by = {n['name']: n for n in nodes}

    # ---- the two axes on every rung ------------------------------
    check('every node row carries both axes with legal vocabularies + '
          'licence + gplv3 label',
          all(n['rights_class'] in L.RIGHTS_CLASS
              and n['fabrication_evidence'] in L.FABRICATION_EVIDENCE
              and n['licence_gplv3_compatible'] in ('yes', 'no', 'to-verify')
              and isinstance(n['licence_verified'], bool)
              for n in nodes), f'{len(nodes)} rungs')
    check('manufacturable is never True (no open process exists) and '
          'every rung says why',
          all(n['manufacturable'] is not True and n['manufacturable_reason']
              for n in nodes))
    check('ladder spans 90 -> 65 -> 45 -> 32 -> 22 -> 15/14 -> 7',
          sorted({n['node_nm'] for n in nodes}, reverse=True)
          == [90.0, 65.0, 45.0, 32.0, 22.0, 15.0, 14.0, 7.0],
          str(sorted({n['node_nm'] for n in nodes})))
    f45 = by['freepdk45']
    check('FreePDK45 = Apache-2.0 verified, gplv3 yes, incorporable-open, '
          'calibrated-predictive, manufacturable False',
          f45['licence'] == 'Apache-2.0' and f45['licence_verified']
          and f45['licence_gplv3_compatible'] == 'yes'
          and f45['rights_class'] == 'incorporable-open'
          and f45['fabrication_evidence'] == 'calibrated-predictive'
          and f45['manufacturable'] is False)
    kn = json.loads(f45['key_numbers_json'])
    check('FreePDK45 key numbers: Ion 975.5 / Ioff 10 / low-Vt 1246 with '
          'a source per number',
          kn['ion_ua_per_um']['value'] == 975.5
          and kn['ioff_na_per_um']['value'] == 10.0
          and kn['ion_lowvt_ua_per_um']['value'] == 1246.0
          and all('source' in v for v in kn.values()))
    a7 = by['asap7']
    check('ASAP7 = BSD-3-Clause verified, incorporable-open, '
          'predictive-only, BSIM-CMG, manufacturable False',
          a7['licence'] == 'BSD-3-Clause' and a7['licence_verified']
          and a7['rights_class'] == 'incorporable-open'
          and a7['fabrication_evidence'] == 'predictive-only'
          and a7['model_family'] == 'BSIM-CMG'
          and a7['manufacturable'] is False)
    check('FreePDK15 = encumbered (CC-BY-NC-SA rule kit), gplv3 no',
          by['freepdk15']['rights_class'] == 'encumbered'
          and by['freepdk15']['licence_gplv3_compatible'] == 'no')
    check('ptm32 unresolved (terms unread) with search text; every '
          'literature node = reference-oracle with search_json missing '
          'items + search_next',
          by['ptm32']['rights_class'] == 'unresolved'
          and by['ptm32']['licence_gplv3_compatible'] == 'to-verify'
          and json.loads(by['ptm32']['search_json'])['search_next']
          and all(n['rights_class'] == 'reference-oracle'
                  and json.loads(n['search_json'])['missing']
                  and json.loads(n['search_json'])['search_next']
                  for n in nodes if n['source'] == 'literature'))
    check('no rung claims enough public info for its own model except '
          'where every protocol item is present',
          all(json.loads(n['search_json'])['enough_for_own_model']
              == (not json.loads(n['search_json'])['missing'])
              for n in nodes))

    # ---- evidence + IP shapes -------------------------------------
    ref_item = ev.SEED_EVIDENCE[0]
    check('ladder evidence rows have EXACTLY the cnt_evidence._item key '
          'set and parse', all(set(e) == set(ref_item)
                                for e in L.SEED_LADDER_EVIDENCE)
          and all(json.loads(e['subjects_json'])
                  for e in L.SEED_LADDER_EVIDENCE))
    known_subjects = ({r['subject_ref'] for r in L.SEED_LADDER_IP}
                      | {n['name'] for n in nodes})
    check('evidence subjects resolve to ladder IP records / nodes',
          all(set(json.loads(e['subjects_json'])) <= known_subjects
              for e in L.SEED_LADDER_EVIDENCE))
    all_ev = {e['name'] for e in ev.SEED_EVIDENCE + L.SEED_LADDER_EVIDENCE}
    check('every evidence name referenced by a node or IP record exists '
          '(lic-bsd-3-clause reused from cnt_evidence, not re-seeded)',
          all(set(json.loads(n['evidence_json'])) <= all_ev for n in nodes)
          and all(set(json.loads(r['evidence_json'])) <= all_ev
                  for r in L.SEED_LADDER_IP)
          and 'lic-bsd-3-clause' in {e['name'] for e in ev.SEED_EVIDENCE}
          and not any(e['name'] == 'lic-bsd-3-clause'
                      for e in L.SEED_LADDER_EVIDENCE)
          and not any(e['name'] in {x['name'] for x in ev.SEED_EVIDENCE}
                      for e in L.SEED_LADDER_EVIDENCE))
    check('IP records shaped like cnt_ip seeds (same key set); verdicts '
          'legal; oracle nodes reference-only; FreePDK45 + ASAP7 '
          'open-chip-candidate',
          all(set(r) == set(ip.SEED_TECHNOLOGY_IP[0]) for r in L.SEED_LADDER_IP)
          and all(r['verdict'] in ip.VERDICT_RANK for r in L.SEED_LADDER_IP)
          and {r['name']: r['intended_use'] for r in L.SEED_LADDER_IP}
          == {'freepdk45': 'open-chip-candidate', 'asap7':
              'open-chip-candidate', 'ptm32': 'reference-only',
              'bsim4-model': 'reference-only'})
    check('IP records carry the make-your-own rule and a fabrication '
          'note', all(ip.MAKE_YOUR_OWN_RULE[:40] in r['self_manufacture_note']
                       and 'fabrication_evidence' in r['notes']
                       for r in L.SEED_LADDER_IP))

    # ---- the FreePDK45-class device ---------------------------------
    n45 = get_row(mgr, 'SiliconMOSFET', 'si-nmos-freepdk45-class')
    p45 = get_row(mgr, 'SiliconMOSFET', 'si-pmos-freepdk45-class')
    rn, rp = derive_si_device(mgr, n45), derive_si_device(mgr, p45)
    check('freepdk45-class NMOS + PMOS derive ok', rn['ok'] and rp['ok'],
          f"{rn.get('error')} {rp.get('error')}")
    check('derived NMOS Vt within 0.15 V of the PTM vth0 0.469 V it was '
          'calibrated to; PMOS Vt negative',
          abs(n45.vt0_v - 0.469) <= 0.15 and p45.vt0_v < 0,
          f'Vt_n = {n45.vt0_v:.3f} V, Vt_p = {p45.vt0_v:.3f} V, '
          f'lambda = {n45.lambda_nm:.2f} nm')
    id_fn, p, dev, refusal = si_device_model(mgr, 'si-nmos-freepdk45-class')
    v = fet_validity(id_fn, p, knobs={'vdd_v': dev.vdd_v})
    check('freepdk45-class NMOS is a valid FET at its Vdd 1.0 V',
          refusal is None and v['valid'], f"failed = {v['failed']}")
    rep = L.compare_to_anchors(mgr, 'si-nmos-freepdk45-class')
    c = rep.get('comparisons', {})
    check('anchor comparison: Ion/Ioff per um computed, ratios + verdicts '
          'reported against the FreePDK45 VTG anchors',
          rep['ok'] and all(k in c and 'ratio_ours_over_anchor' in c[k]
                            and c[k]['verdict'] for k in ('ion', 'ioff'))
          and c['ion']['anchor'] == 975.5 and c['ioff']['anchor'] == 10.0,
          f"Ion {c.get('ion', {}).get('ours', 0):.0f} vs 975.5 uA/um "
          f"({c.get('ion', {}).get('verdict')}); Ioff "
          f"{c.get('ioff', {}).get('ours', 0):.2f} vs 10 nA/um "
          f"({c.get('ioff', {}).get('verdict')}) -> {rep['verdict']}")
    check('if off tolerance, a 1-parameter KNOB suggestion is exposed '
          '(never applied: row vfb unchanged)',
          (rep['within_tolerance'] or rep['knob_suggestions'])
          and n45.vfb_v == -0.93,
          str(rep['knob_suggestions']))
    repp = L.compare_to_anchors(mgr, 'si-pmos-freepdk45-class')
    check('PMOS anchor comparison runs in the device\'s own frame '
          '(positive Ion per um vs 650.3)',
          repp['ok'] and repp['comparisons']['ion']['ours'] > 0,
          f"Ion_p {repp['comparisons']['ion']['ours']:.0f} uA/um -> "
          f"{repp['verdict']}")
    check('compare_to_anchors refuses an underived device',
          not L.compare_to_anchors(mgr, 'si-nmos-planar-90')['ok'])

    # ---- the report -------------------------------------------------
    lad = L.ladder_report(mgr)
    check('ladder_report: rungs sorted 90 -> 7 with both axes shown as '
          'separate columns',
          [r['node_nm'] for r in lad['rungs']]
          == sorted((r['node_nm'] for r in lad['rungs']), reverse=True)
          and all('rights_class' in r and 'fabrication_evidence' in r
                  for r in lad['rungs']))
    check('frontier = freepdk45 with reasoning from the two axes',
          lad['frontier']['node'] == 'freepdk45'
          and 'rights_class' in lad['frontier']['reasoning']
          and 'fabrication_evidence' in lad['frontier']['reasoning'],
          lad['frontier']['reasoning'])
    check('predictive_frontier = asap7 (rights-clean, predictive-only) '
          '— separate from frontier',
          lad['predictive_frontier']['node'] == 'asap7'
          and lad['predictive_frontier']['fabrication_evidence']
          == 'predictive-only')
    check('manufacturable_frontier honest: none, and says the 90-class '
          'is not proven manufacturable either',
          lad['manufacturable_frontier']['node'] is None
          and '90-class' in lad['manufacturable_frontier']['reasoning'])
    rung45 = next(r for r in lad['rungs'] if r['name'] == 'freepdk45')
    check('freepdk45 rung reconstruction status: derived + anchored with '
          'the gap verdict', rung45['reconstruction']['derived']
          and rung45['reconstruction']['anchored']
          and rung45['reconstruction']['gaps']['si-nmos-freepdk45-class']
          ['verdict'])

    # ---- graph seed round-trip ---------------------------------------
    g = L.SEED_SI_LADDER_GRAPHS[0]
    cfg = json.loads(g['definition'])['graphConfig']
    rows = L.ladder_ion_rows(mgr)
    check('graph seed si-ladder-ion-vs-node round-trips (source_class '
          'SiliconProcessNode, log x) and long-form rows carry the '
          'FreePDK45 dot + our derived dots',
          g['name'] == 'si-ladder-ion-vs-node'
          and g['source_class'] == 'SiliconProcessNode'
          and cfg['options']['xType'] == 'log'
          and all({'x', 'y', 'series', 'style'} <= set(r) for r in rows)
          and {r['series'] for r in rows} >= {'FreePDK45',
                                              'polari-model (derived)'}
          and L.CURVE_BUILDERS == {}, f'{len(rows)} rows')

    # ---- fg-4: the FreePDK45 Ioff gap -> apply-anchor-knob act -------
    before = L.compare_to_anchors(mgr, 'si-nmos-freepdk45-class')
    act = L.apply_anchor_knob(mgr, 'si-nmos-freepdk45-class')
    dev45 = get_row(mgr, 'SiliconMOSFET', 'si-nmos-freepdk45-class')
    check('fg-4: the NMOS FreePDK45-class Ioff gap is REPORTED with a '
          'knob suggestion, never auto-applied',
          before['ok'] and not before['within_tolerance']
          and any(s['knob'] == 'vfb_v'
                  for s in before['knob_suggestions'])
          and 'never fitted' in before['rule'],
          str(before.get('knob_suggestions')))
    check('fg-4: apply-anchor-knob is the EXPLICIT act — applies the '
          'vfb_v suggestion to the ROW, records the calibration in '
          'vfb_source (old value kept, source cited), re-derives, and '
          'lands within tolerance',
          act.get('ok') and act.get('within_tolerance')
          and act['applied']['knob'] == 'vfb_v'
          and dev45.vfb_v == act['applied']['new']
          and dev45.vfb_source.startswith('calibrated:')
          and f"{act['applied']['old']:+.3f}" in dev45.vfb_source
          and 'FreePDK45 documentation' in dev45.vfb_source,
          str({k: act.get(k) for k in ('ok', 'error',
                                       'within_tolerance')}))
    check('fg-4: a second apply refuses honestly (already within '
          'tolerance)',
          not L.apply_anchor_knob(
              mgr, 'si-nmos-freepdk45-class').get('ok'))

    # ---- plan file ----------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    plan = os.path.normpath(os.path.join(
        here, '..', '..', '..', '..', 'AI-Notes', 'plans',
        'FET_LADDER_PLAN.md'))
    text = open(plan).read() if os.path.exists(plan) else ''
    check('FET_LADDER_PLAN.md exists with the ladder table + S1 decision',
          '| 90' in text and '| 7' in text and 'FreePDK45' in text
          and 'S1' in text and 'Apache-2.0' in text, plan)

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
