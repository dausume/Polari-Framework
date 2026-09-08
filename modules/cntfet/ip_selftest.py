"""
Selftest for cntfet.cnt_ip_basis (IP / licensing / FTO records).

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m cntfet.ip_selftest
"""

import json
import sys
import types

from cntfet import cnt_ip_basis as ip
from cntfet import cntfet_selftest as st
from cntfet.cnt_cell_library_basis import CELL_LIBRARY
from sifet.si_basis import SEED_TABLES
from sifet.si_refinement_basis import (
    SEED_REFINEMENT_ROUTES, SEED_REFINEMENT_STEPS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    mgr = st._mgr()
    st._seed_all(mgr)
    for table, seeds in list(SEED_TABLES) + [
            ('RefinementStep', SEED_REFINEMENT_STEPS),
            ('RefinementRoute', SEED_REFINEMENT_ROUTES)]:
        mgr.objectTables.setdefault(table, {})
        for seed in seeds:
            row = types.SimpleNamespace(**seed)
            mgr.objectTables[table][id(row)] = row
    mgr.objectTables.setdefault('TechnologyIPRecord', {})
    return mgr


def _year(s):
    try:
        return int(str(s)[:4])
    except ValueError:
        return None


def main():
    mgr = _mgr()
    recs = ip.ip_records(mgr)
    names = set(recs)

    # ---- 1. every seed complete -----------------------------------
    required = ('mosfet-generic', 'cmos', 'planar-process', 'soi',
                'finfet', 'gaa-nanosheet', 'gaa-nanowire',
                'cnt-fet-basic', 'cnt-aligned-array-process', 'tfet',
                'sol-gel-dielectric-generic', 'sol-gel-hfo2-formulations',
                'standard-cells', 'mirror-adder', 'tg-latch',
                'siemens-tcs', 'fbr-silane', 'directional-solidification',
                'zone-refining', 'vs-compact-model', 'liberty-format',
                'ngspice', 'openvaf', 'opensta', 'kwant', 'verilog-a')
    check('seeds: all 26 required records present',
          set(required) <= names, str(set(required) - names))
    incomplete = [n for n, r in recs.items() if not (
        r['verdict'] in ip.VERDICT_RANK and r['fto_reasoning']
        and r['self_manufacture_note'] and r['verify_next']
        and r['confidence'] in ('verified', 'partially-verified',
                                'unverified')
        and r['subject_kind'] in ip.SUBJECT_KINDS
        and r['ip_kind'] in ip.IP_KINDS)]
    check('seeds: every record has verdict / reasoning / self-'
          'manufacture note / verify_next / confidence', not incomplete,
          str(incomplete))
    check('seeds: every self-manufacture note carries the make/use/'
          'sell rule',
          all('271(a)' in r['self_manufacture_note'] for r in
              recs.values()))

    # ---- 2. expired patents ---------------------------------------
    for n in ('mosfet-generic', 'cmos', 'planar-process', 'finfet',
              'zone-refining', 'cnt-fet-basic'):
        pats = json.loads(recs[n]['key_patents_json'])
        check(f'{n}: expired patent(s) with expiry_est < 2026 and '
              f'status expired, verdict green, confidence verified',
              pats and all(p['status'] == 'expired' and
                           _year(p['expiry_est']) < 2026 for p in pats)
              and recs[n]['verdict'] == 'green'
              and recs[n]['confidence'] == 'verified',
              json.dumps(pats)[:200])
    fin = json.loads(recs['finfet']['key_patents_json'])[0]
    check('finfet: US 6,413,802 filed 2000-10-23 → expiry 2020-10-23',
          fin['number'] == '6,413,802' and fin['filed'] == '2000-10-23'
          and fin['expiry_est'] == '2020-10-23')

    # ---- 3. active / mixed ----------------------------------------
    for n in ('gaa-nanosheet', 'cnt-aligned-array-process',
              'fbr-silane'):
        r = recs[n]
        pats = json.loads(r['key_patents_json'])
        recent = any(_year(p.get('filed')) and _year(p['filed'])
                     >= 2006 for p in pats)
        check(f'{n}: amber/red with a patent filed within 20 years, '
              f'or unverified + verify_next',
              r['verdict'] in ('amber', 'red') and (
                  recent or (r['confidence'] == 'unverified'
                             and r['verify_next'])),
              f'verdict={r["verdict"]} conf={r["confidence"]}')
    check('gaa-nanosheet: two verified active claims (TSMC 9,966,471 '
          '2015; IBM 11,121,044 2019)',
          {p['number'] for p in json.loads(
              recs['gaa-nanosheet']['key_patents_json'])}
          == {'9,966,471', '11,121,044'}
          and recs['gaa-nanosheet']['confidence'] == 'verified')
    check('unverified records name what to search (tfet, gaa-nanowire, '
          'siemens-tcs, directional-solidification)',
          all(recs[n]['confidence'] == 'unverified'
              and len(recs[n]['verify_next']) > 40
              for n in ('tfet', 'gaa-nanowire', 'siemens-tcs',
                        'directional-solidification')))

    # ---- 4. device reports ----------------------------------------
    s1 = ip.device_ip_report(mgr, 'cnt-aligned-s1')
    s1_names = {r['name'] for r in s1['records']}
    check('S1 (cnt-gaa) report lists cnt-fet-basic + cnt-aligned-'
          'array-process + vs-compact-model',
          s1['ok'] and {'cnt-fet-basic', 'cnt-aligned-array-process',
                        'vs-compact-model'} <= s1_names, str(s1_names))
    check('S1 worst verdict amber (array process may be active), '
          'shape cnt-gaa', s1['worst_verdict'] == 'amber'
          and s1['shape'] == 'cnt-gaa')
    check('S1 self_manufacture_answer says making your own does NOT '
          'clear an active patent',
          'does NOT clear' in s1['self_manufacture_answer']
          and '271(a)' in s1['self_manufacture_answer'])
    check('S1 no sol-gel records (ALD HfO2 gate stack)',
          not (s1_names & {'sol-gel-dielectric-generic',
                           'sol-gel-hfo2-formulations'})
          and s1['dielectric']['kind'] == 'ald')

    p90 = ip.device_ip_report(mgr, 'si-nmos-planar-90')
    p90_names = {r['name'] for r in p90['records']}
    check('si-nmos-planar-90 → green (mosfet/cmos/planar expired + '
          'thermal oxide)', p90['worst_verdict'] == 'green'
          and {'mosfet-generic', 'cmos', 'planar-process'} <= p90_names
          and p90['dielectric']['kind'] == 'thermal',
          f'{p90["worst_verdict"]} {p90_names}')

    fh = ip.device_ip_report(mgr, 'si-nmos-finfet-solgel-hfo2')
    fh_names = {r['name'] for r in fh['records']}
    check('si-nmos-finfet-solgel-hfo2 → amber: finfet expired (green) '
          'but sol-gel HfO2 formulations mixed',
          fh['worst_verdict'] == 'amber' and 'finfet' in fh_names
          and 'sol-gel-hfo2-formulations' in fh_names
          and recs['finfet']['verdict'] == 'green',
          f'{fh["worst_verdict"]} {fh_names}')
    sg = ip.device_ip_report(mgr, 'si-nmos-planar-solgel-sio2')
    check('si-nmos-planar-solgel-sio2 → green (generic sol-gel SiO2 '
          'chemistry is public domain, no HfO2 record)',
          sg['worst_verdict'] == 'green' and
          'sol-gel-dielectric-generic' in {r['name'] for r in
                                           sg['records']})
    missing = ip.device_ip_report(mgr, 'no-such-device')
    check('unknown device → ok False with affordance + disclaimer',
          not missing['ok'] and 'affordance' in missing
          and missing['disclaimer'] == ip.DISCLAIMER)

    # ---- 5. cells -------------------------------------------------
    cell_reps = {k: ip.cell_ip_report(mgr, k) for k in
                 list(CELL_LIBRARY) + ['cdff']}
    check('cells: all 25 library cells + cdff green',
          len(CELL_LIBRARY) == 25 and
          all(r['worst_verdict'] == 'green' for r in cell_reps.values()))
    check('cfa includes mirror-adder; clatch/cdff include tg-latch',
          'mirror-adder' in {r['name'] for r in cell_reps['cfa']['records']}
          and all('tg-latch' in {r['name'] for r in
                                 cell_reps[c]['records']}
                  for c in ('clatch', 'cdff')))

    # ---- 6. refinement routes -------------------------------------
    pv = ip.route_ip_report(mgr, 'pv-open-route')
    si = ip.route_ip_report(mgr, 'siemens-route')
    eg = ip.route_ip_report(mgr, 'eg-novel-route')
    check('pv-open-route green/amber (directional solidification is '
          'the only mixed step)', pv['ok'] and
          pv['worst_verdict'] in ('green', 'amber'))
    check('siemens-route amber (trade-secret know-how)',
          si['ok'] and si['worst_verdict'] == 'amber' and
          any(s['record'] == 'siemens-tcs' for s in si['steps']))
    check('fbr-silane amber/red',
          recs['fbr-silane']['verdict'] in ('amber', 'red'))
    check('eg-novel-route: zone-refining step maps to the expired '
          'Pfann record (green)',
          any(s['record'] == 'zone-refining' and s['verdict'] == 'green'
              for s in eg['steps']))

    # ---- 7. tools / formats ---------------------------------------
    for n in ('opensta', 'openvaf'):
        check(f'{n}: GPL-3.0, green (compatible with our GPLv3)',
              recs[n]['licence'].startswith('GPL-3.0')
              and recs[n]['verdict'] == 'green')
    check('liberty-format green; kwant BSD-2 green; ngspice BSD-3 green; '
          'verilog-a green',
          all(recs[n]['verdict'] == 'green' for n in
              ('liberty-format', 'kwant', 'ngspice', 'verilog-a'))
          and 'BSD-2' in recs['kwant']['licence']
          and 'BSD-3' in recs['ngspice']['licence'])
    check('vs-compact-model: ours, GPL-3.0, cites the never-read '
          'Stanford CMC gate',
          recs['vs-compact-model']['licence'].startswith('GPL-3.0')
          and 'never read' in recs['vs-compact-model']['fto_reasoning']
          and 'CMC' in recs['vs-compact-model']['fto_reasoning'])

    # ---- 8. gate vocabulary + library report ----------------------
    check('ip_gate: green proceed / amber verify before commercial / '
          'red blocker',
          'proceed' in ip.ip_gate('green')['meaning']
          and 'VERIFY' in ip.ip_gate('amber')['meaning']
          and ip.ip_gate('red')['blocker']
          and not ip.ip_gate('green')['blocker'])
    lib = ip.library_ip_report(mgr)
    n_dev = (len(mgr.objectTables['AlignedCNTFETDevice'])
             + len(mgr.objectTables['SiliconMOSFET']))
    check('library report: every device + every cell + every route + '
          'tools', lib['ok'] and len(lib['devices']) == n_dev
          and len(lib['cells']) == 26 and len(lib['routes']) == 3
          and len(lib['tools']) >= 7,
          f'{len(lib["devices"])}/{n_dev} {len(lib["cells"])} '
          f'{len(lib["routes"])} {len(lib["tools"])}')
    check('library report: no red anywhere today; unverified list '
          'names the unfetched records',
          lib['worst_verdict'] != 'red'
          and set(lib['unverified']) >= {'tfet', 'gaa-nanowire'})

    # ---- 9. serialisable + disclaimer everywhere ------------------
    payloads = [s1, p90, fh, missing, lib, pv, si] + list(
        cell_reps.values())
    try:
        json.dumps(payloads)
        ser = True
    except (TypeError, ValueError):
        ser = False
    check('every payload JSON-serialisable', ser)
    check('disclaimer present on every payload (device / cell / route '
          '/ library / refusal)',
          all(p.get('disclaimer') == ip.DISCLAIMER for p in payloads)
          and 'NOT LEGAL ADVICE' in ip.DISCLAIMER
          and 'verify with counsel before commercial use'
          in ip.DISCLAIMER)

    # ---- 10. graph rows + seed -------------------------------------
    dev = next(iter(mgr.objectTables['AlignedCNTFETDevice'].values()))
    rows = ip.CURVE_BUILDERS['ip-verdicts'](None, None, dev, mgr, None)
    check('ip-verdicts curve: one categorical row per record, y in '
          '{0,1,2} with verdict label',
          len(rows) == len(s1['records'])
          and all(r['y'] in (0, 1, 2) and r['label'] for r in rows))
    g = ip.SEED_CNT_IP_GRAPHS[0]
    check('SEED_CNT_IP_GRAPHS: cnt-device-ip-verdicts, no hguide, '
          'disclaimer in description',
          g['name'] == 'cnt-device-ip-verdicts'
          and not any(r['style'] == 'hguide' for r in rows)
          and 'NOT LEGAL ADVICE' in g['description']
          and json.loads(g['definition'])['graphConfig']['xDimension']
          == 'x')

    # ---- 11. manager rows win over seeds ---------------------------
    edit = dict(ip.SEED_BY_NAME['cnt-aligned-array-process'])
    edit['verdict'] = 'red'
    mgr.objectTables['TechnologyIPRecord'][1] = types.SimpleNamespace(
        **edit)
    s1b = ip.device_ip_report(mgr, 'cnt-aligned-s1')
    check('a manager TechnologyIPRecord row overrides the seed (S1 '
          'goes red when the array process is marked red)',
          s1b['worst_verdict'] == 'red' and s1b['gate']['blocker'])

    n_pass = sum(1 for _, ok in _results if ok)
    print(f'\n{n_pass}/{len(_results)} passed')
    return 0 if n_pass == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
