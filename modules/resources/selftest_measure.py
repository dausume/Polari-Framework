"""
Selftest for resources.profile_measure (res-3).

Run from polari-framework/:  python3 -m resources.selftest_measure

Stdlib-only, samplers mocked. Covers: speedup-curve derivation
(linear / sublinear / flat — a flat curve keeps thread_ceiling at 1
with cpu_benefit='none'), the observed data footprint
(estimate x count, labeled), engine RAM measurement from a mocked
worker /system-info process block, measured-overrides-declared with
the label stamped, honest-absence (unmeasured dims keep declared
values and are NAMED), and the no-profile refusal.
"""

import types

from resources.profile_measure import (
    derive_speedup_curve, measure_subject, observed_data_footprint,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(profiles=None, **tables):
    base = {'ModuleResourceProfile': profiles or {}}
    base.update(tables)
    return types.SimpleNamespace(
        objectTables=base, objectTypingDict={},
        db=types.SimpleNamespace(saveInstanceInDB=lambda row: None))


def _profile(**over):
    fields = dict(
        name='x-resource-profile', subject_name='x',
        subject_kind='module', character='balanced',
        min_ram_mb=64.0, min_disk_mb=50.0, min_threads=1,
        thread_ceiling=4, cpu_benefit='sublinear', ram_benefit='none',
        scales_note='', image_mb=0.0, deps_mb=0.0, est_row_bytes=0,
        growth_rate='low', access_pattern='warm', durability='durable',
        concurrency='single', recommended_backend='',
        fidelity='declared', provenance_id='seed', notes='')
    fields.update(over)
    return types.SimpleNamespace(**fields)


def main():
    # --- speedup curves ------------------------------------------------
    linear = derive_speedup_curve(
        bench=lambda n: 8.0 / n, max_threads=8)
    check('curve: perfectly parallel -> linear, ceiling 8',
          linear['threadCeiling'] == 8
          and linear['cpuBenefit'] == 'linear')
    sub = derive_speedup_curve(
        bench=lambda n: 8.0 / (n ** 0.6), max_threads=8)
    check('curve: diminishing returns -> sublinear',
          sub['cpuBenefit'] == 'sublinear'
          and 1 < sub['threadCeiling'] <= 8)
    flat = derive_speedup_curve(bench=lambda n: 8.0, max_threads=8)
    check('curve: flat (single-threaded) -> ceiling stays 1, none',
          flat['threadCeiling'] == 1 and flat['cpuBenefit'] == 'none')
    plateau = derive_speedup_curve(
        bench=lambda n: 8.0 / min(n, 2), max_threads=8)
    check('curve: plateaus at 2 -> ceiling 2',
          plateau['threadCeiling'] == 2
          and plateau['cpuBenefit'] == 'sublinear')
    boom = derive_speedup_curve(
        bench=lambda n: (_ for _ in ()).throw(OSError('x')),
        max_threads=8)
    check('curve: failing benchmark -> honest error', not boom['ok'])

    # --- observed data footprint ------------------------------------------
    import tempfile, os
    tmp = tempfile.mkdtemp(prefix='res3-selftest-')
    d = os.path.join(tmp, 'datamod')
    os.makedirs(d)
    with open(os.path.join(d, 'b.py'), 'w') as f:
        f.write('class RowA(treeObject):\n    pass\n')
    mgr = _mgr(RowA={i: object() for i in range(10)})
    mgr.objectTypingDict = {'RowA': types.SimpleNamespace(
        polyTypedVars=[types.SimpleNamespace(varType='str')])}
    data = observed_data_footprint(mgr, 'datamod', root=tmp)
    from simulations.storage_predictor import estimate_row_bytes
    expected = 10 * estimate_row_bytes(mgr, 'RowA')
    check('data footprint: rows x predictor bytes, labeled',
          data['ok'] and data['observedBytes'] == expected
          and 'estimate-x-count' in data['label'])

    # --- module measurement -------------------------------------------------
    prof = _profile(subject_name='datamod', character='balanced')
    m = _mgr(profiles={'p': prof},
             RowA={i: object() for i in range(10)})
    m.objectTypingDict = mgr.objectTypingDict
    report = measure_subject(m, 'datamod', bench=lambda n: 5.0,
                             root=tmp)
    check('module measure: flat bench -> measured ceiling 1 / none',
          report['ok'] and prof.thread_ceiling == 1
          and prof.cpu_benefit == 'none')
    check('module measure: fidelity flipped + provenance stamped',
          prof.fidelity == 'measured'
          and prof.provenance_id.startswith('measured@'))
    check('module measure: honest absence NAMES unmeasured ram',
          any('ram' in u for u in report['unmeasured']))
    check('module measure: declared min_ram_mb kept (not fabricated)',
          prof.min_ram_mb == 64.0)

    # --- engine measurement ---------------------------------------------------
    eng = _profile(subject_name='prf-cad-engines',
                   subject_kind='engine', min_ram_mb=300.0,
                   thread_ceiling=1, cpu_benefit='none',
                   image_mb=688.0)
    em = _mgr(profiles={'e': eng})
    DOC = [{'system-info': {'process': {'residentMb': 145.2,
                                        'peakMb': 210.0}}}]
    er = measure_subject(em, 'prf-cad-engines', url='http://x:9600',
                         fetch=lambda url, timeout=5: DOC)
    check('engine measure: RSS from the worker process block',
          er['ok'] and eng.min_ram_mb == 145.2
          and er['detail']['peak_ram_mb'] == 210.0)
    check('engine measure: declared image/threads kept + named',
          eng.image_mb == 688.0 and eng.thread_ceiling == 1
          and any('image' in u for u in er['unmeasured'])
          and any('threads' in u for u in er['unmeasured']))
    check('engine measure: fidelity measured + url in provenance',
          eng.fidelity == 'measured' and 'http://x:9600'
          in eng.provenance_id)

    dead = measure_subject(
        em, 'prf-cad-engines', url='http://x:9600',
        fetch=lambda url, timeout=5: (_ for _ in ()).throw(
            OSError('refused')))
    check('engine measure: unreachable worker -> honest refusal, '
          'nothing measurable',
          not dead['ok'] and any('unreachable' in u
                                 for u in dead['unmeasured']))

    ghost = measure_subject(_mgr(), 'nope')
    check('measure: no profile -> refusal pointing at declare-first',
          not ghost['ok'] and 'declare one first' in ghost['error'])

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
