"""
Selftest for cntfet.cnt_open_library (the OPEN LIBRARY gate).

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m cntfet.selftest_open_library

Fake manager (SimpleNamespace rows); the characterization leg runs
the REAL ngspice + OSDI when available (small: 2 cells, drive 1,
2x2 grid) and falls back to a synthetic run row otherwise (said).
"""

import json
import os
import sys
import tempfile
import types

from cntfet import cnt_derive as cd
from cntfet import cnt_open_library as ol
from cntfet import selftest_cntfet as st
from cntfet.cnt_cell_library import CELL_LIBRARY
from cntfet.cnt_cell_scoring import parse_liberty
from cntfet.cnt_evidence import DISCLAIMER, SEED_EVIDENCE
from cntfet.cnt_ip import SEED_TECHNOLOGY_IP
from cntfet.cnt_osdi import find_ngspice
from microchip.chip_basis import SEED_DESIGN_LEVELS, SEED_DESIGN_NODES
from sifet.si_basis import SEED_TABLES
from sifet.si_device import derive_si_device, get_row

_results = []
REGISTERED = {'class-rows-table', 'api-json-panel', 'named-graph-panel',
              'freedom-proof-panel', 'evidence-browser'}
SI, CNT = 'polari-open-si-planar-90', 'polari-open-cnt-s1'


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    mgr = st._mgr()
    st._seed_all(mgr)
    for table, seeds in list(SEED_TABLES) + [
            ('TechnologyIPRecord', SEED_TECHNOLOGY_IP),
            ('EvidenceItem', SEED_EVIDENCE),
            ('DesignLevelDefinition', SEED_DESIGN_LEVELS),
            ('MicrochipDesignNode', SEED_DESIGN_NODES)]:
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
                  'CellCharacterizationRun', 'OpenCellLibrary'):
        mgr.objectTables.setdefault(table, {})
    pfac = st._row_factory(mgr, 'CNTFETParameterRow')
    for n in ('cnt-aligned-s1', 'cnt-aligned-s1-p'):
        cd.derive_device(mgr, cd.get_row(mgr, 'AlignedCNTFETDevice', n),
                         parameter_factory=pfac)
    for n in ('si-nmos-planar-90', 'si-pmos-planar-90'):
        derive_si_device(mgr, get_row(mgr, 'SiliconMOSFET', n))
    return mgr


def _components(definition):
    return {i['componentProps']['componentName']
            for r in json.loads(definition)['rows'] for i in r['items']}


def _synthetic_run(mgr, device_name):
    """A run row in the emitter's own format when ngspice is absent."""
    from cntfet.cnt_cell_library import _liberty_library
    def _pt(scale):
        return {'cell_rise_s': 5e-13 * scale, 'cell_fall_s': 5e-13 * scale,
                'rise_transition_s': 6e-13 * scale,
                'fall_transition_s': 6e-13 * scale,
                'energy_rise_j': 2e-18 * scale, 'energy_fall_j': 0.0}
    blocks = [{'libertyName': 'INVX1', 'function': '(!A)', 'inputs': ['A'],
               'inputCap_f': 1e-17, 'outputs': ['Y'],
               'functions': {'Y': '(!A)'}, 'three_state': None,
               'arcs': {'A': {'pin': 'A', 'sense': 'negative', 'when': None,
                              'output': 'Y', 'tables': [[_pt(1)] * 2] * 2}}},
              {'libertyName': 'NAND2X1', 'function': '(!(A*B))',
               'inputs': ['A', 'B'], 'inputCap_f': 1e-17, 'outputs': ['Y'],
               'functions': {'Y': '(!(A*B))'}, 'three_state': None,
               'arcs': {p: {'pin': p, 'sense': 'negative', 'when': None,
                            'output': 'Y', 'tables': [[_pt(1)] * 2] * 2}
                        for p in ('A', 'B')}}]
    text = _liberty_library(1.0, [1e-12, 4e-12], [1e-15, 4e-15], blocks)
    return st._row_factory(mgr, 'CellCharacterizationRun')(
        name=f'{device_name}-lib-synthetic', device=device_name,
        cell='library:INVX1,NAND2X1', executor='synthetic', vdd_v=1.0,
        liberty_text=text, verdict='library-characterized',
        ran_at='2026-08-29T00:00:00+00:00', notes='synthetic (no ngspice)')


def main():
    mgr = _mgr()

    # ---- 1. admission: the Si pair ----------------------------------
    adm_si = ol.admit_cells(mgr, 'si-nmos-planar-90', 'si-pmos-planar-90')
    lib_keys = sorted(CELL_LIBRARY)
    check(f'admit_cells(Si planar pair): all {len(lib_keys)} CELL_LIBRARY '
          f'cells + cdff admitted (excluded = '
          f'{[e["cell"] for e in adm_si["excluded"]]}), devices n/p both '
          'proven-free, library proven-free, open_source_ready',
          adm_si['ok'] and set(adm_si['admitted']) >= set(lib_keys)
          and 'cdff' in adm_si['admitted']
          and adm_si['deviceStatus'] == {'n': 'proven-free',
                                         'p': 'proven-free'}
          and adm_si['libraryStatus'] == 'proven-free'
          and adm_si['open_source_ready'] is True
          and adm_si['counts']['cells'] == len(ol.OPEN_CELL_KEYS) == 26,
          f'dev={adm_si["deviceStatus"]} lib={adm_si["libraryStatus"]} '
          f'excluded={adm_si["excluded"]}')
    check('Si admission: multi-output (cha, cfa), tri-state (ctbuf) and '
          'sequential (clatch, cdff) cells are judged and admitted by the '
          'same rule; `why` says open_source_ready and carries the '
          'licence statement (circuits public domain, artifacts GPL-3.0)',
          all(c in adm_si['admitted'] for c in
              ('cha', 'cfa', 'ctbuf', 'clatch', 'cdff'))
          and adm_si['why'].startswith('open_source_ready')
          and 'public domain' in adm_si['why']
          and 'GPL-3.0' in adm_si['why']
          and adm_si['licence']['artifacts'] == 'GPL-3.0',
          adm_si['why'][:200])

    # ---- 2. admission: the CNT pair — the contrast --------------------
    adm_cnt = ol.admit_cells(mgr, 'cnt-aligned-s1', 'cnt-aligned-s1-p')
    cnt_cells_free = all(s == 'proven-free'
                         for s in adm_cnt['cellStatus'].values())
    check('admit_cells(CNT S1 pair): NOT open_source_ready — both devices '
          'encumbered, library encumbered — while every cell is '
          'individually proven-free (same admitted set as Si)',
          adm_cnt['ok'] and adm_cnt['open_source_ready'] is False
          and adm_cnt['deviceStatus'] == {'n': 'encumbered',
                                          'p': 'encumbered'}
          and adm_cnt['libraryStatus'] == 'encumbered'
          and cnt_cells_free
          and adm_cnt['admitted'] == adm_si['admitted'],
          f'dev={adm_cnt["deviceStatus"]} lib={adm_cnt["libraryStatus"]} '
          f'cells_free={cnt_cells_free}')
    check('CNT `why` names the aligned-array gap (US 9,825,229 / '
          'cnt-aligned-array-process) as the DEVICE encumbrance and says '
          'exactly that the cell circuits are free but the transistor is '
          'not',
          'DEVICE pair is encumbered' in adm_cnt['why']
          and 'cell circuits are free' in adm_cnt['why']
          and ('9825229' in adm_cnt['why'] or '9,825,229' in adm_cnt['why']
               or 'cnt-aligned-array-process' in adm_cnt['why'])
          and any('9825229' in g or '9,825,229' in g
                  for g in adm_cnt['deviceGaps']['n']),
          adm_cnt['why'][:300])

    # ---- 3. seeds + index + report -----------------------------------
    idx = ol.open_library_index(mgr)
    by = {l['name']: l for l in idx['libraries']}
    check('SEED_OPEN_LIBRARIES: two seeds; open_library_index evaluates '
          'both live — Si ready, CNT not; ready list = [Si]; disclaimer',
          {s['name'] for s in ol.SEED_OPEN_LIBRARIES} == {SI, CNT}
          and idx['ok'] and by[SI]['open_source_ready']
          and not by[CNT]['open_source_ready'] and idx['ready'] == [SI]
          and idx['disclaimer'] == DISCLAIMER
          and by[CNT]['libraryStatus'] == 'encumbered',
          str({n: (l['open_source_ready'], l['libraryStatus'])
               for n, l in by.items()}))
    rep0 = ol.open_library_report(mgr, SI)
    check('open_library_report(Si) BEFORE any run: resolves; '
          'characterization refuses by name (no run); Liberty artifact '
          'unavailable, netlists available for every admitted cell '
          '(cdff via cnt_cells); licence + disclaimer + proof chain',
          rep0['ok'] and not rep0['characterization']['ok']
          and 'characterize' in rep0['characterization']['refusal']
          and rep0['artifacts']['liberty']['available'] is False
          and set(rep0['artifacts']['netlists']['cells'])
          == set(adm_si['admitted'])
          and rep0['licence']['artifacts'] == 'GPL-3.0'
          and rep0['licence']['circuits'] == 'public domain'
          and rep0['disclaimer'] == DISCLAIMER
          and 'device:si-nmos-planar-90' in rep0['proof']
          and 'cell:cinv' in rep0['proof']
          and rep0['proof']['device:si-nmos-planar-90']['chain'],
          f'char={rep0["characterization"]} nets='
          f'{rep0["artifacts"]["netlists"]["cells"]}')
    check('open_library_report on an unknown name refuses by name '
          'listing the seeds',
          not ol.open_library_report(mgr, 'nope')['ok']
          and 'nope' in ol.open_library_report(mgr, 'nope')['error'])
    nets = ol.open_netlists(['cinv', 'cfa', 'cdff'])
    check('open_netlists: library cells = subckt_text (cinv_x1, cfa_x1 '
          'with its compose targets available), cdff = the hand subckt '
          'with ctg + cinv dependencies',
          '.subckt cinv_x1' in nets['cinv'] and '.subckt cfa_x1' in nets['cfa']
          and '.subckt cdff' in nets['cdff'] and '.subckt ctg' in nets['cdff']
          and nets['cdff'].index('.subckt ctg') < nets['cdff'].index(
              '.subckt cdff'),
          nets['cdff'][:200])

    # ---- 4. characterize: refusal on CNT; real run on Si -------------
    ref = ol.characterize_open_library(mgr, CNT, drives=(1,))
    check('characterize_open_library(CNT) REFUSES without force, naming '
          'the encumbrance and the force knob',
          not ref['ok'] and 'NOT open_source_ready' in ref['refusal']
          and 'force=True' in ref['refusal']
          and 'encumbered' in ref['refusal'],
          str(ref)[:300])
    ngspice_path, why = find_ngspice()
    nmos = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    if ngspice_path is None:
        check(f'characterize_open_library(Si) real run SKIPPED — {why}; '
              'a synthetic run row stands in for the artifact checks',
              True)
        run_row = _synthetic_run(mgr, nmos.name)
        run_name = run_row.name
    else:
        from cntfet.cnt_cell_library import _pair_params
        from cntfet.cnt_cells import _tau_estimate
        p_n, _p_p, _e = _pair_params(mgr, nmos)
        tau = _tau_estimate(p_n, nmos.vdd_v)
        cin = 2.0 * p_n['cinv_f_per_m'] * p_n['lg_m'] + 2e-18
        rep = ol.characterize_open_library(
            mgr, SI, drives=(1,), cells=['cinv', 'cnand2'],
            slews_s=[2.0 * tau, 8.0 * tau], loads_f=[cin, 4.0 * cin],
            force=False, workdir=tempfile.mkdtemp(prefix='open-lib-'),
            result_factory=st._row_factory(mgr, 'CellCharacterizationRun'))
        names = {c['libertyName'] for c in rep.get('cells', [])}
        check('characterize_open_library(Si, [cinv, cnand2], drive 1, 2x2 '
              'grid, force=False): ok at the device\'s OWN Vdd 1.0 V, '
              'INVX1 + NAND2X1, pair-aware p card, labelled OPEN, run row '
              'created',
              rep.get('ok') and names == {'INVX1', 'NAND2X1'}
              and rep.get('vdd_v') == nmos.vdd_v
              and 'partner' in rep.get('pSide', '')
              and rep['label'].startswith('OPEN') and not rep['forced']
              and rep.get('resultRow'),
              f"ok={rep.get('ok')} err={rep.get('error', '')[:200]} "
              f"ref={rep.get('refusal', '')[:200]} names={names} "
              f"failures={rep.get('failures')}")
        run_name = rep.get('resultRow', '')
    runs = [r for r in mgr.objectTables['CellCharacterizationRun'].values()
            if getattr(r, 'device', '') == nmos.name]
    check('a CellCharacterizationRun row exists for the n device and the '
          'report now names it as the latest run (2 cells; NOT covering '
          'the full admitted set — missing named honestly)',
          runs and any(r.name == run_name for r in runs)
          and ol.open_library_report(mgr, SI)['characterization']['run']
          == run_name
          and ol.open_library_report(mgr, SI)['characterization']
          ['cellCount'] == 2
          and not ol.open_library_report(mgr, SI)['characterization']
          ['coversAdmitted']
          and 'cxor2' in ol.open_library_report(mgr, SI)
          ['characterization']['missing'],
          str(ol.open_library_report(mgr, SI)['characterization']))
    check('characterize_open_library refuses a cell that is not admitted '
          '(rule, not a typo check) and defers sequential cells by name',
          not ol.characterize_open_library(mgr, SI, cells=['nope'])['ok']
          and not ol.characterize_open_library(
              mgr, SI, cells=['clatch'])['ok'])

    # ---- 5. Liberty with provenance header --------------------------
    libt = ol.open_liberty_text(mgr, SI)
    parsed = parse_liberty(libt.get('text', ''))
    check('open_liberty_text(Si): comment-only provenance header '
          '(library, devices, pair, GPL-3.0 artifact, circuits public '
          'domain, proof status, evidence refs, disclaimer) prepended; '
          'parse_liberty still finds INVX1 + NAND2X1 and the grid',
          libt['ok'] and libt['text'].startswith('/*')
          and '*/\nlibrary (' in libt['text']
          and 'licence (this artifact): GPL-3.0' in libt['text']
          and 'cell circuits: public domain' in libt['text']
          and 'proof status: library proven-free' in libt['text']
          and 'pat-us-3356858' in libt['text']
          and 'si-pmos-planar-90' in libt['text']
          and DISCLAIMER in libt['text']
          and set(parsed['cells']) == {'INVX1', 'NAND2X1'}
          and len(parsed['index_1_ps']) == 2 == len(parsed['index_2_ff']),
          f"ok={libt.get('ok')} cells={sorted(parsed['cells'])} "
          f"{libt.get('refusal', '')}")
    check('open_liberty_text(CNT) refuses (no run) rather than emitting '
          'an unlabelled artifact',
          not ol.open_liberty_text(mgr, CNT)['ok'])

    # ---- 6. export ----------------------------------------------------
    outdir = tempfile.mkdtemp(prefix='open-lib-export-')
    exp = ol.export_open_library(mgr, SI, outdir)
    files = sorted(os.listdir(outdir)) if exp.get('ok') else []
    prov = {}
    if exp.get('ok'):
        with open(exp['paths']['provenance']) as fh:
            prov = json.load(fh)
    check('export_open_library(Si): writes 4 files (.lib, .sp, '
          '-PROVENANCE.json, -LICENSE.txt); PROVENANCE is JSON with the '
          'proof status, device status, evidence names + chains; '
          'LICENSE names GPL-3.0 + public-domain circuits + disclaimer',
          exp.get('ok') and files == sorted([f'{SI}.lib', f'{SI}.sp',
                                             f'{SI}-PROVENANCE.json',
                                             f'{SI}-LICENSE.txt'])
          and prov.get('proof_status') == 'proven-free'
          and prov.get('open_source_ready') is True
          and 'pat-us-3356858' in prov.get('evidence_names', [])
          and prov.get('evidence') and prov['proof_chain']
          and prov['disclaimer'] == DISCLAIMER
          and 'GPL-3.0' in open(exp['paths']['license']).read()
          and 'public domain' in open(exp['paths']['license']).read()
          and DISCLAIMER in open(exp['paths']['license']).read()
          and '.subckt cinv_x1' in open(exp['paths']['netlists']).read()
          and '.subckt cdff' in open(exp['paths']['netlists']).read(),
          f'exp={ {k: v for k, v in exp.items() if k != "paths"} } '
          f'files={files}')
    check('export_open_library(CNT) refuses without force',
          not ol.export_open_library(mgr, CNT, outdir)['ok'])

    # ---- 7. refresh stamps the row ----------------------------------
    rf = ol.refresh_open_library(mgr, SI, apply=True)
    row = next((r for r in mgr.objectTables['OpenCellLibrary'].values()
                if getattr(r, 'name', '') == SI), None)
    check('refresh_open_library(Si, apply=True) creates/stamps the '
          'OpenCellLibrary row: cells_json = admitted, run_ref = the run, '
          'open_source_ready True, licence GPL-3.0, generated_at set',
          rf['ok'] and row is not None
          and json.loads(row.cells_json) == adm_si['admitted']
          and row.run_ref == run_name and row.open_source_ready is True
          and row.licence == 'GPL-3.0' and row.generated_at
          and row.library_proof_status == 'proven-free',
          str(rf)[:300])

    # ---- 8. ladder tie-in (cell-4 as data) --------------------------
    lad = ol.ladder_cell_rung_update(mgr, apply=False)
    rung = next(r for r in mgr.objectTables['DesignLevelDefinition']
                .values() if r.name == 'standard-cell')
    node = next(r for r in mgr.objectTables['MicrochipDesignNode']
                .values() if r.name == 'polari-cell-lib')
    check('ladder_cell_rung_update(apply=False): status characterized, '
          'refs = the run name(s) + libraries, metrics = cell count 26 / '
          'proven count / open-ready [Si]; the fake rows are UNTOUCHED',
          lad['ok'] and lad['status'] == 'characterized'
          and lad['rung']['name'] == 'standard-cell'
          and lad['node']['name'] == 'polari-cell-lib'
          and any(r['name'] == run_name for r in
                  json.loads(lad['node']['artifact_refs_json']))
          and json.loads(lad['node']['metrics_json'])['cell_count'] == 26
          and json.loads(lad['node']['metrics_json'])
          ['proven_free_cells'] == len(adm_si['admitted'])
          and json.loads(lad['node']['metrics_json'])
          ['open_ready_libraries'] == [SI]
          and not lad['applied']
          and rung.status == 'unbuilt' and node.status == 'unbuilt',
          str(lad)[:400])
    lad2 = ol.ladder_cell_rung_update(mgr, apply=True)
    check('ladder_cell_rung_update(apply=True) updates the fake rows: '
          'rung status characterized + artifact classes; node status '
          'characterized + refs + metrics MERGED over the seed metrics '
          '(planned_cells kept)',
          lad2['applied'] and lad2['found'] == {'standard-cell': True,
                                                'polari-cell-lib': True}
          and rung.status == 'characterized'
          and any(c['class'] == 'OpenCellLibrary' for c in
                  json.loads(rung.artifact_classes_json))
          and node.status == 'characterized'
          and 'planned_cells' in json.loads(node.metrics_json)
          and json.loads(node.metrics_json)['runs'] == [run_name],
          f'rung={rung.status} node={node.status}')

    # ---- 9. page seed -------------------------------------------------
    page = ol.SEED_OPEN_LIBRARY_PAGES[0]
    comps = _components(page['definition'])
    defn = page['definition']
    check('SEED_OPEN_LIBRARY_PAGES: /display/open-library (route '
          'open-library, source_class OpenCellLibrary) uses only '
          'registered components (class-rows-table, api-json-panel, '
          'named-graph-panel, freedom-proof-panel, evidence-browser)',
          page['pageRoute'] == 'open-library' and page['isPage']
          and page['source_class'] == 'OpenCellLibrary'
          and comps == REGISTERED, str(comps))
    check('page wiring: OpenCellLibrary table, /api/cntfet/open-library '
          'index, per-library detail panels, freedom-proof-panel on each '
          'n device proof path, cell-scores graph per n device, '
          'evidence-browser, disclaimer in the description',
          '"OpenCellLibrary"' in defn
          and '"/api/cntfet/open-library"' in defn
          and f'/api/cntfet/open-library/{SI}' in defn
          and f'/api/cntfet/open-library/{CNT}' in defn
          and '/api/cntfet/device/si-nmos-planar-90/proof' in defn
          and '/api/cntfet/device/cnt-aligned-s1/proof' in defn
          and 'cnt-device-cell-scores' in defn
          and '/api/cntfet/device/si-nmos-planar-90/points?curve='
              'cell-scores' in defn
          and DISCLAIMER in page['description'])

    # ---- 10. disclaimer everywhere + routes as data ------------------
    payloads = [adm_si, adm_cnt, idx, rep0, libt, exp, rf, lad, ref]
    check('DISCLAIMER rides every payload (admission, index, report, '
          'liberty, export, refresh, ladder, refusal); API_ROUTES lists '
          'the 4 routes the integrator wires',
          all(p.get('disclaimer') == DISCLAIMER for p in payloads)
          and len(ol.API_ROUTES) == 4
          and all(r['path'].startswith('/api/cntfet/open-library')
                  for r in ol.API_ROUTES))

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    print(f'  Si admitted {len(adm_si["admitted"])}/{len(ol.OPEN_CELL_KEYS)}'
          f' ready={adm_si["open_source_ready"]}; CNT admitted '
          f'{len(adm_cnt["admitted"])} ready={adm_cnt["open_source_ready"]}'
          f' ({adm_cnt["libraryStatus"]})')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
