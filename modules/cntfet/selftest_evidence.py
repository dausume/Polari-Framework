"""
Selftest for cntfet.cnt_evidence (evidence + proof-of-freedom).

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m cntfet.selftest_evidence
"""

import datetime as _dt
import json
import sys
import types

from cntfet import cnt_evidence as ev
from cntfet import cnt_ip as ip
from cntfet import selftest_cntfet as st
from cntfet.cnt_cell_library import CELL_LIBRARY
from cntfet.cnt_characteristics import SEED_FET_CHARACTERISTICS
from cntfet.cnt_regimes import SEED_FET_REGIMES
from cntfet.cnt_transport import SEED_SCATTERING_MECHANISMS
from sifet.si_basis import SEED_TABLES
from sifet.si_refinement import (
    SEED_REFINEMENT_ROUTES, SEED_REFINEMENT_STEPS,
)

_results = []
TODAY = _dt.date.today()


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    mgr = st._mgr()
    st._seed_all(mgr)
    for table, seeds in list(SEED_TABLES) + [
            ('RefinementStep', SEED_REFINEMENT_STEPS),
            ('RefinementRoute', SEED_REFINEMENT_ROUTES),
            ('TechnologyIPRecord', ip.SEED_TECHNOLOGY_IP),
            ('EvidenceItem', ev.SEED_EVIDENCE),
            ('FETCharacteristic', SEED_FET_CHARACTERISTICS),
            ('ScatteringMechanism', SEED_SCATTERING_MECHANISMS),
            ('FETRegime', SEED_FET_REGIMES)]:
        mgr.objectTables.setdefault(table, {})
        for seed in seeds:
            row = types.SimpleNamespace(**seed)
            mgr.objectTables[table][id(row)] = row
    return mgr


def _chain_str(proof):
    return '; '.join(f'{c["record"]} ← '
                     + ', '.join(f'{e["ref"]}{"✓" if e["verified"] else "?"}'
                                 for e in c['evidence'] if e['satisfies'])
                     for c in proof['chain'])


def main():
    mgr = _mgr()
    items = ev.evidence_items(mgr)
    recs = ip.ip_records(mgr)

    # ---- 1. coverage: patents ---------------------------------------
    pats = {p['number'].replace(',', '') for r in recs.values()
            for p in json.loads(r['key_patents_json'])}
    missing = sorted(n for n in pats if f'pat-us-{n}' not in items)
    check(f'every key patent in cnt_ip ({len(pats)}) has an EvidenceItem',
          pats and not missing, str(missing))

    # ---- 2. coverage: citation keys ---------------------------------
    keys = ev.all_citation_keys()
    missing = [k for k in keys if k not in ev.CITATION_ITEMS
               or ev.CITATION_ITEMS[k] not in items]
    print(f'      citation keys ({len(keys)}): ' + ' '.join(keys))
    check(f'every citation key across cnt_citations / taxonomy / power / '
          f'si_model / si_refinement has an EvidenceItem ({len(keys)})',
          len(keys) >= 40 and not missing, str(missing))

    # ---- 3. every record's evidence_json resolves -------------------
    bad = {}
    for n, r in recs.items():
        names = json.loads(r.get('evidence_json') or '[]')
        unresolved = [x for x in names if x not in items]
        if not names or unresolved:
            bad[n] = unresolved or 'EMPTY'
    check('every TechnologyIPRecord has a non-empty evidence_json that '
          'resolves to EvidenceItems', not bad, str(bad))

    # ---- 4. items well-formed; expired patents -----------------------
    payloads = [ev.item_payload(i) for i in items.values()]
    malformed = [p['name'] for p in payloads if not (
        p['kind'] in ev.KINDS and p['proves'] in ev.PROVES and p['title']
        and p['jurisdiction'] == 'US' and p['detailPath'])]
    check('every item: kind/proves in vocab, title, jurisdiction US, '
          'detailPath', not malformed, str(malformed))
    expired = [p for p in payloads if p['kind'] == 'patent'
               and p['proves'] == 'expired']
    bad = [p['name'] for p in expired if not (
        p['expiry'] and _dt.date.fromisoformat(p['expiry']) <= TODAY)]
    check(f'expired patents ({len(expired)}) carry expiry <= today '
          f'(lapse observed on reviewed_at when the source gives no '
          f'date) and proves "expired"', expired and not bad, str(bad))
    lapsed = [p for p in expired if 'lapsed for non-payment (US)'
              in p['proves_detail']]
    check('fee-lapsed patents recorded as expired with "lapsed for '
          'non-payment (US)" (8354291, 7407895, 8802046, 5374564)',
          {p['name'] for p in lapsed} >= {'pat-us-8354291',
                                          'pat-us-7407895',
                                          'pat-us-8802046'},
          str([p['name'] for p in lapsed]))
    active = [p for p in payloads if p['is_active_claim']]
    check('active patents (9825229, 9966471, 11121044, 9428830) have '
          'expiry > today', {p['name'] for p in active} >= {
              'pat-us-9825229', 'pat-us-9966471', 'pat-us-11121044',
              'pat-us-9428830'} and all(
              _dt.date.fromisoformat(p['expiry']) > TODAY for p in active))

    # ---- 5. expiry rules as data -------------------------------------
    check('EXPIRY_RULES: cutover 1995-06-08, 20-y-from-filing after, '
          'max(17 y grant, 20 y filing) before, fee-lapse + foreign '
          'lines', ev.EXPIRY_RULES['cutover'] == '1995-06-08'
          and 'fee_lapse' in ev.EXPIRY_RULES
          and 'OUT OF SCOPE' in ev.EXPIRY_RULES['foreign'])
    check('expiry_estimate: 2000-10-23 → 2020-10-23; 1960-05-31 grant '
          '1963-08-27 → 1980-08-27 (17 y from grant wins); priority '
          '2018-10-10 → 2038-10-10',
          ev.expiry_estimate('2000-10-23') == '2020-10-23'
          and ev.expiry_estimate('1960-05-31', '1963-08-27')
          == '1980-08-27'
          and ev.expiry_estimate('2019-11-22', '2021-09-14',
                                 '2018-10-10') == '2038-10-10',
          f'{ev.expiry_estimate("1960-05-31", "1963-08-27")}')

    # ---- 6. planar Si NMOS proven-free -------------------------------
    p90 = ev.freedom_proof(mgr, 'device', 'si-nmos-planar-90')
    chain = {c['record']: c for c in p90['chain']}
    print('      si-nmos-planar-90 chain: ' + _chain_str(p90))
    check('si-nmos-planar-90 is proven-free', p90['ok']
          and p90['status'] == 'proven-free' and not p90['gaps'],
          f'{p90["status"]} gaps={p90["gaps"]}')

    def _has(rec, name):
        return any(e['name'] == name and e['verified'] and e['satisfies']
                   for e in chain.get(rec, {}).get('evidence', []))
    check('chain: mosfet-generic ← US 3,102,230 expired verified; '
          'cmos ← US 3,356,858; planar ← US 3,025,589; thermal oxide '
          '← Sze 1981 textbook; vs-compact-model ← GPL-3.0 + LUN97',
          _has('mosfet-generic', 'pat-us-3102230')
          and _has('cmos', 'pat-us-3356858')
          and _has('planar-process', 'pat-us-3025589')
          and _has('mosfet-generic', 'book-sze-1981')
          and _has('vs-compact-model', 'lic-gpl-3.0')
          and _has('vs-compact-model', 'pub-LUN97'),
          str({k: [e['name'] for e in c['evidence']]
               for k, c in chain.items()}))

    # ---- 7. S1 CNT encumbered ----------------------------------------
    s1 = ev.freedom_proof(mgr, 'device', 'cnt-aligned-s1')
    check('cnt-aligned-s1 is encumbered (aligned-array process amber '
          'with active US 9,825,229)', s1['status'] == 'encumbered'
          and any(c['record'] == 'cnt-aligned-array-process'
                  and c['recordStatus'] == 'encumbered'
                  for c in s1['chain']),
          s1['status'])
    check('S1 gaps name 9825229 and the array process; cnt-fet-basic '
          'itself is proven-free in the chain',
          any('9825229' in g and 'cnt-aligned-array-process' in g
              for g in s1['gaps'])
          and next(c for c in s1['chain']
                   if c['record'] == 'cnt-fet-basic')['recordStatus']
          == 'proven-free', str(s1['gaps']))

    # ---- 8. cells ----------------------------------------------------
    cell_keys = list(CELL_LIBRARY) + ['cdff']
    cells = {k: ev.freedom_proof(mgr, 'cell', k) for k in cell_keys}
    not_proven = {k: p['status'] for k, p in cells.items()
                  if p['status'] != 'proven-free'}
    check('every cell (25 + cdff) is proven-free (standard-cells ← '
          'US 3,356,858 expired + Weste & Eshraghian 1985/88 textbook '
          '≥ 20 y; cfa ← mirror-adder; clatch/cdff ← tg-latch)',
          len(CELL_LIBRARY) == 25 and not not_proven, str(not_proven))
    cfa = {c['record']: c for c in cells['cfa']['chain']}
    check('cfa chain: mirror-adder ← book-weste-eshraghian-1985 '
          '(verified, ≥ 20 y); clatch: tg-latch likewise',
          any(e['name'] == 'book-weste-eshraghian-1985' and e['satisfies']
              for e in cfa['mirror-adder']['evidence'])
          and any(e['name'] == 'book-weste-eshraghian-1985'
                  and e['satisfies'] for c in cells['clatch']['chain']
                  if c['record'] == 'tg-latch' for e in c['evidence']))
    wh = ev.item_payload(items['book-weste-harris-2010'])
    check('Weste & Harris 2010 is honestly < 20 y (does NOT satisfy); '
          'Weste & Eshraghian 1985 does',
          not wh['satisfies'] and wh['verified']
          and ev.item_payload(items['book-weste-eshraghian-1985'])
          ['satisfies'])

    # ---- 9. FinFET-on-sol-gel HfO2 ------------------------------------
    fh = ev.freedom_proof(mgr, 'device', 'si-nmos-finfet-solgel-hfo2')
    check('si-nmos-finfet-solgel-hfo2 → free-unverified (finfet '
          'proven-free via US 6,413,802; sol-gel HfO2 formulations '
          'amber with NO active item attached — RIKEN 7,407,895 '
          'lapsed)', fh['status'] == 'free-unverified'
          and next(c for c in fh['chain'] if c['record'] == 'finfet')
          ['recordStatus'] == 'proven-free'
          and any('sol-gel-hfo2-formulations' in g for g in fh['gaps']),
          f'{fh["status"]} {fh["gaps"]}')

    # ---- 10. unknown when no evidence ---------------------------------
    tmp = dict(ip.SEED_BY_NAME['cmos'])
    tmp.update(name='tmp-no-evidence', evidence_json='[]',
               key_patents_json='[]')
    mgr.objectTables['TechnologyIPRecord']['tmp'] = types.SimpleNamespace(
        **tmp)
    unk = ev.freedom_proof(mgr, 'record', 'tmp-no-evidence')
    check('a record with no evidence → status unknown, gap names it',
          unk['status'] == 'unknown' and unk['chain'][0]['evidence'] == []
          and any('tmp-no-evidence' in g for g in unk['gaps']))
    del mgr.objectTables['TechnologyIPRecord']['tmp']
    bad = ev.freedom_proof(mgr, 'device', 'no-such')
    check('unknown subject → ok False, status unknown, disclaimer + scope',
          not bad['ok'] and bad['status'] == 'unknown'
          and bad['disclaimer'] == ev.DISCLAIMER
          and bad['scope'] == ev.SCOPE_LINE)

    # ---- 11. routes ---------------------------------------------------
    routes = {r['name']: ev.freedom_proof(mgr, 'route', r['name'])
              for r in SEED_REFINEMENT_ROUTES}
    check('routes: eg-novel-route zone-refining step proven-free via '
          'Pfann US 2,739,088; siemens-route free-unverified (trade '
          'secret, Siemens US 3,011,877 expired verified)',
          any(c['record'] == 'zone-refining'
              and c['recordStatus'] == 'proven-free'
              for c in routes['eg-novel-route']['chain'])
          and routes['siemens-route']['status'] == 'free-unverified'
          and any(e['name'] == 'pat-us-3011877' and e['verified']
                  for c in routes['siemens-route']['chain']
                  for e in c['evidence']),
          str({k: v['status'] for k, v in routes.items()}))

    # ---- 12. provenance_summary ---------------------------------------
    ps = ev.provenance_summary(mgr, 'device', 'si-nmos-planar-90')
    pc = ev.provenance_summary(mgr, 'cell', 'cinv')
    check('provenance_summary: ipVerdict / proofStatus / evidenceCount / '
          'verifiedCount / topEvidence ≤3 / detailPath / disclaimer',
          all(k in ps for k in ('ipVerdict', 'proofStatus',
                                'evidenceCount', 'verifiedCount',
                                'topEvidence', 'detailPath',
                                'disclaimer'))
          and ps['detailPath'] == '/api/cntfet/device/si-nmos-planar-90/'
                                  'proof'
          and pc['detailPath'] == '/api/cntfet/cell/cinv/proof'
          and len(ps['topEvidence']) <= 3
          and all({'name', 'kind', 'ref', 'proves'} <= set(t)
                  for t in ps['topEvidence'])
          and ps['proofStatus'] == 'proven-free'
          and 0 < ps['verifiedCount'] <= ps['evidenceCount'])

    # ---- 13. evidence_detail ------------------------------------------
    d = ev.evidence_detail(mgr, 'pub-VS1')
    fc = d['citedBy'].get('FETCharacteristic', [])
    check('evidence_detail(pub-VS1): supports vs-compact-model + every '
          'device; citedBy lists FETCharacteristic rows citing [VS1] '
          '(transfer-characteristic …)',
          d['ok'] and 'vs-compact-model' in {r['record'] for r in
                                             d['supports']['records']}
          and len(d['supports']['devices']) >= 12
          and 'transfer-characteristic' in fc and len(fc) >= 5,
          f'{d.get("supports", {}).get("records")} citedBy={d.get("citedBy")}')
    d2 = ev.evidence_detail(mgr, 'pub-LUN97')
    check('evidence_detail(pub-LUN97): citedBy includes '
          'ScatteringMechanism rows (acoustic-phonon notes) and '
          'FETRegime rows',
          'acoustic-phonon' in d2['citedBy'].get('ScatteringMechanism', [])
          and d2['citedBy'].get('FETRegime'),
          str(d2['citedBy']))
    d3 = ev.evidence_detail(mgr, 'pat-us-3356858')
    check('evidence_detail(pat-us-3356858): supports cmos + '
          'standard-cells and all 26 cells',
          {'cmos', 'standard-cells'} <= {r['record'] for r in
                                         d3['supports']['records']}
          and len(d3['supports']['cells']) == 26)
    check('evidence_detail(no-such) → ok False + affordance',
          not ev.evidence_detail(mgr, 'no-such')['ok']
          and 'affordance' in ev.evidence_detail(mgr, 'no-such'))

    # ---- 14. evidence_index -------------------------------------------
    idx = ev.evidence_index(mgr)
    pidx = ev.evidence_index(mgr, kind='patent')
    sidx = ev.evidence_index(mgr, subject='cnt-fet-basic')
    check('evidence_index: counts sum over kinds; kind filter; subject '
          'filter; citation_keys listed',
          sum(idx['counts']['by_kind'].values()) == idx['counts']['total']
          == len(items)
          and all(i['kind'] == 'patent' for i in pidx['items'])
          and len(pidx['items']) == idx['counts']['by_kind']['patent']
          and all('cnt-fet-basic' in i['subjects'] for i in sidx['items'])
          and len(sidx['items']) >= 8
          and idx['citation_keys'] == keys)
    check('verified share: ≥ 14 patents and ≥ 20 publications/books '
          'verified online; unverified items name verify_next in notes',
          sum(1 for p in payloads if p['kind'] == 'patent'
              and p['verified']) >= 14
          and sum(1 for p in payloads if p['kind'] in
                  ('publication', 'textbook', 'prior-art')
                  and p['verified']) >= 20
          and all('verify_next' in p['notes'] or p['verified']
                  or p['kind'] == 'licence'
                  for p in payloads if p['kind'] != 'licence'),
          str([p['name'] for p in payloads if not p['verified']
               and 'verify_next' not in p['notes']
               and p['kind'] != 'licence']))

    # ---- 15. library_proof ---------------------------------------------
    lib = ev.library_proof(mgr)
    n_dev = (len(mgr.objectTables['AlignedCNTFETDevice'])
             + len(mgr.objectTables['SiliconMOSFET']))
    check('library_proof: every device + 26 cells + 3 routes; counts sum',
          len(lib['subjects']) == n_dev + 26 + 3
          and sum(lib['counts'][s] for s in ev.STATUSES)
          == lib['counts']['total'] == len(lib['subjects']),
          f'{len(lib["subjects"])} vs {n_dev}+26+3 {lib["counts"]}')
    order = [ev.STATUS_INDEX[s['proofStatus']] for s in lib['subjects']]
    check('library_proof sorted proven-free first; gaps_by_subject only '
          'for non-proven subjects', order == sorted(order)
          and all(lib['subjects'][0]['proofStatus'] == 'proven-free'
                  for _ in [0])
          and all(next(s for s in lib['subjects'] if s['subject'] == k)
                  ['proofStatus'] != 'proven-free'
                  for k in lib['gaps_by_subject']))
    check('library_proof: CNT devices encumbered, planar-90 pair '
          'proven-free, sol-gel HfO2 devices free-unverified, no unknown',
          lib['counts']['unknown'] == 0
          and all(s['proofStatus'] == 'encumbered' for s in lib['subjects']
                  if s['subject'].startswith('cnt-aligned'))
          and all(s['proofStatus'] == 'proven-free' for s in lib['subjects']
                  if s['subject'] in ('si-nmos-planar-90',
                                      'si-pmos-planar-90'))
          and all(s['proofStatus'] == 'free-unverified'
                  for s in lib['subjects'] if 'hfo2' in s['subject']))
    print('      proof-status table:')
    for s in lib['subjects']:
        print(f'        {s["kind"]:6} {s["subject"]:30} '
              f'{s["proofStatus"]:16} ip={s["ipVerdict"]}')

    # ---- 16. rows + graph seed + curve builder -------------------------
    rows = lib['proof_rows']
    check('proof_rows: categorical x = subject, y = status index 0..3, '
          'label = status, series = kind',
          len(rows) == len(lib['subjects'])
          and all(r['y'] in (0, 1, 2, 3) and r['label'] in ev.STATUSES
                  and r['series'] in ('device', 'cell', 'route')
                  for r in rows))
    dev = next(iter(mgr.objectTables['AlignedCNTFETDevice'].values()))
    crow = ev.CURVE_BUILDERS['proof-status'](None, None, dev, mgr, None)
    check('proof-status curve: one row per chain record for the device, '
          'y = record status index',
          len(crow) == len(s1['chain'])
          and any(r['x'] == 'cnt-aligned-array-process' and r['y']
                  == ev.STATUS_INDEX['encumbered'] for r in crow))
    g = ev.SEED_CNT_EVIDENCE_GRAPHS[0]
    cfg = json.loads(g['definition'])['graphConfig']
    check('SEED_CNT_EVIDENCE_GRAPHS: cnt-library-proof-status round-trips, '
          'xDimension x, yTickLabels = 4 statuses, disclaimer + scope in '
          'description', g['name'] == 'cnt-library-proof-status'
          and cfg['xDimension'] == 'x'
          and list(cfg['options']['yTickLabels'].values())
          == list(ev.STATUSES)
          and 'NOT LEGAL ADVICE' in g['description']
          and ev.SCOPE_LINE in g['description'])

    # ---- 17. rules as data, scope, disclaimer, serialisable -----------
    check('PROOF_RULES: four statuses + precedence + jurisdiction US; '
          'SATISFIES per proves',
          set(ev.STATUSES) <= set(ev.PROOF_RULES)
          and ev.PROOF_RULES['jurisdiction'] == 'US'
          and set(ev.SATISFIES) == set(ev.PROVES))
    all_payloads = [p90, s1, fh, unk, bad, ps, pc, d, d2, d3, idx, lib] \
        + list(cells.values()) + list(routes.values())
    check('every payload carries disclaimer (NOT LEGAL ADVICE) + '
          '"scope: United States; foreign families not assessed"',
          all(p.get('disclaimer') == ev.DISCLAIMER
              and p.get('scope') == ev.SCOPE_LINE for p in all_payloads)
          and 'NOT LEGAL ADVICE' in ev.DISCLAIMER)
    check('gaps never mention foreign families (out of scope)',
          not any('foreign' in g.lower() or 'non-US' in g
                  for p in all_payloads for g in p.get('gaps', [])))
    try:
        json.dumps(all_payloads)
        ser = True
    except (TypeError, ValueError):
        ser = False
    check('every payload JSON-serialisable', ser)

    # ---- 18. manager rows win ------------------------------------------
    edit = dict(ev.SEED_BY_NAME['pat-us-9825229'])
    edit.update(proves='expired', expiry='2026-01-01',
                proves_detail='TEST: pretend expired')
    mgr.objectTables['EvidenceItem']['edit'] = types.SimpleNamespace(**edit)
    s1b = ev.freedom_proof(mgr, 'device', 'cnt-aligned-s1')
    check('a manager EvidenceItem row overrides the seed (S1 leaves '
          '"encumbered" when 9825229 is marked expired; array process '
          'still amber → free-unverified)',
          s1b['status'] == 'free-unverified', s1b['status'])

    n_pass = sum(1 for _, ok in _results if ok)
    print(f'\n{n_pass}/{len(_results)} passed')
    return 0 if n_pass == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
