"""
Selftest for fv-6 (FET_VIEWS_PLAN §1): the comparator FET set
(lg10 / tox2 / p-twin) and the 3-input + composed cells
(NAND3 / NOR3 / AND2 / OR2 / XOR2).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_more_cells

Reuses selftest_cntfet's fake manager + seeding; the
characterization leg runs the REAL openvaf + ngspice (honest skip
otherwise). Kept SMALL on purpose — the three new cells at drive
1 over a 2x2 grid; the full sweep is the engines worker's job.
"""

import sys

from cntfet import cnt_derive as cd
from cntfet import selftest_cntfet as st
from cntfet.cnt_basis import (
    SEED_CNT_DEVICES, SEED_CNT_GEOMETRIES, SEED_GATE_STACKS,
)
from cntfet.cnt_cell_library import (
    CELL_LIBRARY, COMBINATIONAL, DRIVES, SEED_CNT_CELLS, cell_arcs,
    characterize_cells, fet_count, liberty_cell_name, subckt_text,
)
from cntfet.cnt_osdi import find_ngspice, find_openvaf
from cntfet.cnt_scoring import score_device

_results = []

NEW_DEVICES = ['cnt-aligned-s1', 'cnt-aligned-s1-lg30',
               'cnt-aligned-s1-lg10', 'cnt-aligned-s1-tox2',
               'cnt-aligned-s1-p']
NEW_CELLS = {'cnand3': 6, 'cnor3': 6, 'cand2': 6, 'cor2': 6,
             'cxor2': 10}


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _terms(mgr, name):
    sc = score_device(mgr, name)
    return sc, {t['term']: t for t in sc.get('terms', [])}


def main():
    mgr = st._mgr()
    st._seed_all(mgr)
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    pfac = st._row_factory(mgr, 'CNTFETParameterRow')

    # ---- A. devices -------------------------------------------------
    names = {d['name'] for d in SEED_CNT_DEVICES}
    check('fv-6: the three comparator devices + their geometry / '
          'gate-stack rows are seeded by name',
          set(NEW_DEVICES) <= names
          and any(g['name'] == 'cnt-s1-lg10' and g['lg_nm'] == 10.0
                  for g in SEED_CNT_GEOMETRIES)
          and any(g['name'] == 'cnt-s1-hfo2-gaa-tox2'
                  and g['t_ox_nm'] == 2.0 and g['k_ox'] == 16.0
                  for g in SEED_GATE_STACKS))
    devs, derived = {}, {}
    for name in NEW_DEVICES:
        dev = cd.get_row(mgr, 'AlignedCNTFETDevice', name)
        devs[name] = dev
        _rows, missing = cd.resolve_components(mgr, dev)
        res = cd.derive_device(mgr, dev, parameter_factory=pfac)
        derived[name] = (missing, res)
    check('fv-6: every device resolves all six component rows by '
          'name and derives ok',
          all(not m and r.get('ok') for m, r in derived.values()),
          f'{[(n, m, r.get("ok"), r.get("error")) for n, (m, r) in derived.items()]}')

    def tr(name):
        return cd.get_row(mgr, 'CNTTransportModel',
                          devs[name].transport)

    def gs(name):
        return cd.get_row(mgr, 'GateStack', devs[name].gate_stack)

    # transport rows are SHARED between devices (one prior row) and
    # re-stamped per derive — so read each device's derived numbers
    # right after ITS derive, via a per-device re-derive here.
    nums = {}
    for name in NEW_DEVICES:
        cd.derive_device(mgr, devs[name], parameter_factory=pfac)
        t, g = tr(name), gs(name)
        sc, by = _terms(mgr, name)
        nums[name] = {'dibl': t.dibl_v_per_v, 'n_ss': t.n_ss,
                      'vxo': t.vxo_m_per_s, 'lambda_nm': t.lambda_nm,
                      'cinv': g.cinv_f_per_m, 'cox': g.cox_f_per_m,
                      'score': sc.get('score'),
                      'valid': sc.get('validity', {}).get('valid'),
                      'gm_over_g0': by.get('fet-gm-over-g0', {}).get('raw'),
                      'ss': by.get('fet-ss', {}).get('raw')}
        print(f'  {name}: ' + ', '.join(
            f'{k}={v:.4g}' if isinstance(v, float) else f'{k}={v}'
            for k, v in nums[name].items()))
    s1, lg10, tox2, p = (nums['cnt-aligned-s1'], nums['cnt-aligned-s1-lg10'],
                         nums['cnt-aligned-s1-tox2'], nums['cnt-aligned-s1-p'])
    check('fv-6 lg10: the aggressive channel is SHORT-CHANNEL — larger '
          'DIBL and n_ss than S1 (lambda/Lg grows), higher v_xo, and '
          'it scores as a valid FET once derived',
          lg10['dibl'] > s1['dibl'] and lg10['n_ss'] > s1['n_ss']
          and lg10['vxo'] > s1['vxo'] and lg10['valid']
          and lg10['score'] > 0,
          f'lg10={lg10}, s1={s1}')
    check('fv-6 tox2: the thinner oxide has larger Cox and Cinv, '
          'higher gm/G0 than S1, tighter SCE (shorter lambda) and a '
          'valid score',
          tox2['cox'] > s1['cox'] and tox2['cinv'] > s1['cinv']
          and tox2['gm_over_g0'] > s1['gm_over_g0']
          and tox2['lambda_nm'] < s1['lambda_nm']
          and tox2['valid'] and tox2['score'] > 0,
          f'tox2={tox2}, s1={s1}')
    check('fv-6 p-twin: the row exists with polarity p, and — '
          'HONESTLY — the flag is a LABEL today: derive never reads '
          'it (build_vs_params pins ptype 0), so it derives to the '
          'SAME numbers and score as S1',
          devs['cnt-aligned-s1-p'].polarity == 'p'
          and devs['cnt-aligned-s1'].polarity == 'n'
          and all(abs(p[k] - s1[k]) < 1e-12 * max(1.0, abs(s1[k]))
                  for k in ('dibl', 'n_ss', 'vxo', 'cinv', 'gm_over_g0'))
          and p['score'] == s1['score']
          and 'LABEL' in devs['cnt-aligned-s1-p'].notes,
          f'p={p}, s1={s1}')
    check('fv-6: comparator notes name the trade-off they expose and '
          'the unproven-until-derived rule',
          all('COMPARATOR' in devs[n].notes and 'derive' in devs[n].notes
              and 'scores 0' in devs[n].notes
              for n in ('cnt-aligned-s1-lg10', 'cnt-aligned-s1-tox2',
                        'cnt-aligned-s1-p')))

    # ---- B. cells ---------------------------------------------------
    check('fv-6: NAND3/NOR3/AND2/OR2/XOR2 are in CELL_LIBRARY and '
          'COMBINATIONAL; seed rows cover every (cell, drive)',
          set(NEW_CELLS) <= set(CELL_LIBRARY)
          and set(NEW_CELLS) <= set(COMBINATIONAL)
          and len(SEED_CNT_CELLS) == len(CELL_LIBRARY) * len(DRIVES)
          and {f'{c}-x{d}' for c in NEW_CELLS for d in DRIVES}
          <= {r['name'] for r in SEED_CNT_CELLS})
    counts_ok = all(fet_count(c, d) == n * d
                    for c, n in NEW_CELLS.items() for d in DRIVES)
    check('fv-6: fet_count — nand3 6, nor3 6, and2 6, or2 6, xor2 10 '
          '(NOR2 + AOI21), each x drive',
          counts_ok,
          f'{[(c, [fet_count(c, d) for d in DRIVES]) for c in NEW_CELLS]}')
    rendered = {}
    for c in NEW_CELLS:
        for d in DRIVES:
            rendered[(c, d)] = subckt_text(c, d)
    n3 = rendered[('cnand3', 2)]
    x2 = rendered[('cxor2', 1)]
    a2 = rendered[('cand2', 4)]
    check('fv-6: subckt_text renders every new cell at x1/x2/x4 — '
          'device stacks scale with drive, composed cells wire '
          'multi-input sub-cells (NOR2 -> AOI21 for XOR2, NAND2 -> INV '
          'for AND2) at the same drive',
          all(t.startswith(f'.subckt {c}_x{d} ')
              and t.endswith(f'.ends {c}_x{d}')
              for (c, d), t in rendered.items())
          and n3.count('cntn') == 6 and n3.count('cntp') == 6
          and 'Cmid1 mid1 0' in n3 and 'Cmid2 mid2 0' in n3
          and '.subckt cxor2_x1 A B Y vddn' in x2
          and 'X0 A B m1 vddn cnor2_x1' in x2
          and 'X1 A B m1 Y vddn caoi21_x1' in x2
          and 'X0 A B m1 vddn cnand2_x4' in a2
          and 'X1 m1 Y vddn cinv_x4' in a2,
          f'nand3x2={n3!r}, xor2={x2!r}')
    nand3_arcs = cell_arcs('cnand3')
    nor3_arcs = cell_arcs('cnor3')
    and2_arcs = cell_arcs('cand2')
    or2_arcs = cell_arcs('cor2')
    xor_arcs = cell_arcs('cxor2')
    check('fv-6: arcs — NAND3 ties the other two pins hi (negative), '
          'NOR3 ties lo (negative), AND2 hi / OR2 lo (positive), XOR2 '
          'carries both senses per pin as `when` arcs',
          [a['id'] for a in nand3_arcs] == ['A', 'B', 'C']
          and all(a['ties'] == {o: 1 for o in 'ABC' if o != a['pin']}
                  and a['sense'] == 'negative' for a in nand3_arcs)
          and all(a['ties'] == {o: 0 for o in 'ABC' if o != a['pin']}
                  and a['sense'] == 'negative' for a in nor3_arcs)
          and [(a['id'], a['ties'], a['sense']) for a in and2_arcs]
          == [('A', {'B': 1}, 'positive'), ('B', {'A': 1}, 'positive')]
          and [(a['id'], a['ties'], a['sense']) for a in or2_arcs]
          == [('A', {'B': 0}, 'positive'), ('B', {'A': 0}, 'positive')]
          and [a['id'] for a in xor_arcs]
          == ['A|!B', 'A|B', 'B|!A', 'B|A']
          and [a['sense'] for a in xor_arcs]
          == ['positive', 'negative', 'positive', 'negative']
          and CELL_LIBRARY['cxor2']['unate'] == 'non-unate'
          and CELL_LIBRARY['cxor2']['liberty_function']
          == '((A*!B)+(!A*B))',
          f'xor={xor_arcs}')

    # ---- C. characterization (real ngspice, small grid) -------------
    device = devs['cnt-aligned-s1']
    cd.derive_device(mgr, device, parameter_factory=pfac)
    ngspice_path, why_ng = find_ngspice()
    openvaf_path, why_va = find_openvaf()
    if ngspice_path is None or openvaf_path is None:
        check('fv-6: characterization leg honestly SKIPPED — '
              f'{why_ng or why_va}', True)
    else:
        from cntfet.cnt_cells import _tau_estimate
        from cntfet.cnt_cell_library import _device_params
        params, _err = _device_params(mgr, device)
        tau = _tau_estimate({**params, 'ptype': 0}, 0.6)
        cin = 2.0 * params['cinv_f_per_m'] * params['lg_m'] + 2e-18
        lib = characterize_cells(
            mgr, device, cells=['cnand3', 'cnor3', 'cxor2'],
            drives=(1,), slews_s=[2.0 * tau, 8.0 * tau],
            loads_f=[cin, 4.0 * cin],
            result_factory=st._row_factory(
                mgr, 'CellCharacterizationRun'))
        cells = {c['libertyName']: c for c in lib.get('cells', [])}
        text = open(lib['libertyPath']).read() if lib.get('ok') else ''
        check('fv-6: NAND3X1 + NOR3X1 + XOR2X1 characterize in ONE '
              'Liberty — every arc measured, monotone in load, zero '
              'failed points, XOR2 `when` arcs emitted, staGate '
              'reflects the live binary',
              lib.get('ok')
              and set(cells) == {'NAND3X1', 'NOR3X1', 'XOR2X1'}
              and cells['NAND3X1']['arcs'] == ['A', 'B', 'C']
              and cells['NOR3X1']['arcs'] == ['A', 'B', 'C']
              and cells['XOR2X1']['arcs']
              == ['A|!B', 'A|B', 'B|!A', 'B|A']
              and all(m['monotoneInLoad'] for m in lib['monotone'])
              and not lib['failures']
              and all(f'cell ({liberty_cell_name(c, 1)})' in text
                      for c in ('cnand3', 'cnor3', 'cxor2'))
              and 'when : "!B";' in text and 'when : "A";' in text
              and 'function : "(!(A*B*C))";' in text
              and ((lib['staGate'].get('ran')
                    and lib['staGate'].get('accepted'))
                   or (not lib['staGate'].get('ran')
                       and lib['staGate'].get('refusal'))),
              f'cells={lib.get("cells")}, failures={lib.get("failures")}, '
              f'sta={lib.get("staGate")}, err={lib.get("error")}')
        if lib.get('ok'):
            print(f'  grid: slews={lib["gridSlews_s"]} loads={lib["gridLoads_f"]}')
            print(f'  staGate: {lib["staGate"]}')
            # readable summary: delays at the mid grid point (ps),
            # parsed from the emitted Liberty (the report keeps the
            # full tables only in the text)
            import re as _re
            for c in cells.values():
                print(f'  {c["libertyName"]}: arcs={c["arcs"]} '
                      f'energy(mid aJ rise/fall)='
                      + str({k: (round(v['rise_aJ'], 3),
                                 round(v['fall_aJ'], 3))
                             for k, v in c['energy'].items()}))
            blocks = _re.split(r'\n  cell \(', text)[1:]
            for blk in blocks:
                cname = blk.split(')')[0]
                for m in _re.finditer(
                        r'related_pin : "(\w+)";\s*timing_sense : \w+;'
                        r'(?:\s*when : "([^"]*)";)?\s*cell_rise[^;]*;'
                        r'[^;]*;\s*values \(\s*\\\n\s*(.*?) \);\s*\}'
                        r'\s*cell_fall[^;]*;[^;]*;\s*values \(\s*\\\n'
                        r'\s*(.*?) \);', blk, _re.S):
                    def mid(vals):
                        rows = [r.strip().strip('"').split(', ')
                                for r in vals.split(', \\\n')]
                        return rows[len(rows) // 2][len(rows[0]) // 2]
                    print(f'    {cname} {m.group(1)}'
                          f'{" when " + m.group(2) if m.group(2) else ""}'
                          f': cell_rise={mid(m.group(3))} ps, '
                          f'cell_fall={mid(m.group(4))} ps')
    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
