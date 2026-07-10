"""
Selftest for resources.profile_* (res-2).

Run from polari-framework/:  python3 -m resources.selftest_profiles

Stdlib-only, fake manager + synthetic module sources in a temp dir.
Covers: classification (data / compute / balanced / engine-module /
honest-absence), storage-tier recommendation rules with reasons,
est_row_bytes reusing storage_predictor, declared-profile creation
(manifest knob wins; classification default otherwise), engine
/capability resources-block import (cache, update, measured-wins),
and seed coherence (single-threaded example, benefit-appropriate
engine numbers).
"""

import json
import os
import tempfile
import types

from resources.profile_analysis import (
    classify_module, declared_profile, estimate_module_row_bytes,
    import_engine_profile, profile_dict, recommend_backend,
    scan_module_source,
)
from resources.profile_seed import SEED_MODULE_RESOURCE_PROFILES

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(**tables):
    base = {'ModuleResourceProfile': {}, 'PolariModule': {},
            'ModuleAssignment': {}, 'InstanceDefinition': {}}
    base.update(tables)
    return types.SimpleNamespace(
        objectTables=base,
        objectTypingDict={},
        db=types.SimpleNamespace(saveInstanceInDB=lambda row: None))


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


def _write_module(root, name, files):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    for fname, text in files.items():
        with open(os.path.join(d, fname), 'w') as f:
            f.write(text)


def main():
    tmp = tempfile.mkdtemp(prefix='res2-selftest-')
    _write_module(tmp, 'datamod', {
        'datamod_basis.py': (
            'class RowA(treeObject):\n    pass\n\n'
            'class RowB(treeObject):\n    pass\n'),
        'datamod_analysis.py': 'def summarize():\n    pass\n'})
    _write_module(tmp, 'enginemod', {
        'solver.py': 'import skfem\n\ndef solve():\n    pass\n'})
    _write_module(tmp, 'bothmod', {
        'basis.py': ('import trimesh\n'
                     + '\n'.join(f'class R{i}(treeObject):\n    pass'
                                 for i in range(4)))})

    mgr = _mgr()

    # --- classification -------------------------------------------------
    data_v = classify_module(mgr, 'datamod', root=tmp)
    check('classify: mostly-rows module -> data',
          data_v['character'] == 'data'
          and data_v['dataClasses'] == ['RowA', 'RowB'])
    check('classify: evidence carried', len(data_v['evidence']) >= 1)
    eng_v = classify_module(mgr, 'enginemod', root=tmp)
    check('classify: heavy-import module -> compute',
          eng_v['character'] == 'compute'
          and eng_v['heavyImports'] == ['skfem'])
    both_v = classify_module(mgr, 'bothmod', root=tmp)
    check('classify: rows + compute -> balanced',
          both_v['character'] == 'balanced')
    fem_v = classify_module(mgr, 'materialsScience.fem', root=tmp)
    check('classify: engine module (ENGINE_MODULES) -> compute',
          fem_v['character'] == 'compute'
          and 'prf-msci-engines' in fem_v['evidence'][0])
    ghost = classify_module(mgr, 'no-such-module', root=tmp)
    check('classify: missing source named honestly in evidence',
          any('no source directory' in e for e in ghost['evidence']))

    # --- provider-assignment evidence ------------------------------------
    amgr = _mgr(
        ModuleAssignment={'a': types.SimpleNamespace(
            module_name='workermod', instance_name='engines',
            state='enabled')},
        InstanceDefinition={'engines': types.SimpleNamespace(
            name='engines',
            service_kinds_json=json.dumps(['prf-msci-engines']))})
    worker_v = classify_module(amgr, 'workermod', root=tmp)
    check('classify: provider assignment -> compute evidence',
          worker_v['character'] == 'compute'
          and worker_v['providerKinds'] == ['prf-msci-engines'])

    # --- est_row_bytes reuses storage_predictor --------------------------
    typing_obj = types.SimpleNamespace(polyTypedVars=[
        types.SimpleNamespace(varType='str'),
        types.SimpleNamespace(varType='int'),
        types.SimpleNamespace(varType='dict')])
    mgr.objectTypingDict = {'RowA': typing_obj}
    from simulations.storage_predictor import estimate_row_bytes
    est, est_class = estimate_module_row_bytes(mgr, ['RowA', 'RowB'])
    check('est_row_bytes matches storage_predictor',
          est == estimate_row_bytes(mgr, 'RowA') and est > 0
          and est_class == 'RowA')

    # --- recommend_backend rules ------------------------------------------
    hot = recommend_backend(types.SimpleNamespace(
        access_pattern='hot', durability='ephemeral',
        concurrency='single', growth_rate='high'))
    shared = recommend_backend(types.SimpleNamespace(
        access_pattern='warm', durability='durable',
        concurrency='shared', growth_rate='low'))
    small = recommend_backend(types.SimpleNamespace(
        access_pattern='warm', durability='durable',
        concurrency='single', growth_rate='low'))
    check('backend: hot+ephemeral -> redis with reason',
          hot['backend'] == 'redis' and 'hot' in hot['reason'])
    check('backend: shared+durable -> mariadb with reason',
          shared['backend'] == 'mariadb'
          and 'shared' in shared['reason'])
    check('backend: single+small+durable -> sqlite with reason',
          small['backend'] == 'sqlite'
          and 'single-writer' in small['reason'])

    # --- declared_profile ---------------------------------------------------
    dp = declared_profile(mgr, 'datamod', factory=_factory, root=tmp)
    check('declared_profile: created, data character, declared label',
          dp['created'] and dp['profile'].character == 'data'
          and dp['profile'].fidelity == 'declared')
    check('declared_profile: data module gets a recommended backend',
          dp['profile'].recommended_backend in (
              'redis', 'sqlite', 'mariadb'))
    check('declared_profile: est_row_bytes flows from the predictor',
          dp['profile'].est_row_bytes == est)
    mgr.objectTables['ModuleResourceProfile']['p'] = dp['profile']
    again = declared_profile(mgr, 'datamod', factory=_factory, root=tmp)
    check('declared_profile: idempotent (existing row wins)',
          not again['created'] and again['profile'] is dp['profile'])

    manifest_mgr = _mgr(PolariModule={'m': types.SimpleNamespace(
        name='datamod', manifest_json=json.dumps({'resources': {
            'min_ram_mb': 512.0, 'growth_rate': 'high'}}))})
    mp = declared_profile(manifest_mgr, 'datamod', factory=_factory,
                          root=tmp)
    check('declared_profile: manifest knob wins over defaults',
          mp['profile'].min_ram_mb == 512.0
          and mp['profile'].provenance_id
          == 'PolariModule.manifest_json')

    # --- engine capability import ------------------------------------------
    CAP = {'service': 'msci-engines', 'engines': {},
           'resources': {'minThreads': 1, 'threadCeiling': 8,
                         'cpuBenefit': 'sublinear', 'ramMb': 900,
                         'imageMb': 2160, 'fidelity': 'declared'}}
    emgr = _mgr()
    imp = import_engine_profile(
        emgr, 'prf-msci-engines', url='http://x:9500',
        fetch=lambda url, timeout=5: CAP, factory=_factory)
    check('engine import: cached from /capability resources block',
          imp['ok'] and imp['created']
          and imp['profile'].thread_ceiling == 8
          and imp['profile'].character == 'compute'
          and imp['profile'].min_ram_mb == 900.0)
    check('engine import: provenance = the capability URL',
          imp['profile'].provenance_id.endswith('/capability'))
    emgr.objectTables['ModuleResourceProfile']['e'] = imp['profile']
    upd = import_engine_profile(
        emgr, 'prf-msci-engines', url='http://x:9500',
        fetch=lambda url, timeout=5: CAP, factory=_factory)
    check('engine import: re-import updates in place',
          upd['ok'] and not upd['created'] and upd.get('updated'))
    imp['profile'].fidelity = 'measured'
    kept = import_engine_profile(
        emgr, 'prf-msci-engines', url='http://x:9500',
        fetch=lambda url, timeout=5: CAP, factory=_factory)
    check('engine import: measured profile never overridden',
          kept['ok'] and not kept.get('updated')
          and 'measured' in kept.get('note', ''))
    old = import_engine_profile(
        emgr, 'prf-cad-engines', url='http://x:9600',
        fetch=lambda url, timeout=5: {'ok': True}, factory=_factory)
    check('engine import: no resources block -> honest refusal + knob',
          not old['ok'] and 'resources' in old['error']
          and 'rebuild' in old['suggestion']['action'])
    dead = import_engine_profile(
        emgr, 'prf-cad-engines', url='http://x:9600',
        fetch=None if False else (lambda url, timeout=5:
                                  (_ for _ in ()).throw(OSError('no'))),
        factory=_factory)
    check('engine import: unreachable -> honest error', not dead['ok'])

    # --- seed coherence -----------------------------------------------------
    seeds = {s['subject_name']: s for s in SEED_MODULE_RESOURCE_PROFILES}
    check('seed: msci-engines compute + thread_ceiling > 1',
          seeds['prf-msci-engines']['character'] == 'compute'
          and seeds['prf-msci-engines']['thread_ceiling'] > 1)
    check('seed: cad-engines is the strictly single-threaded example',
          seeds['prf-cad-engines']['thread_ceiling'] == 1
          and seeds['prf-cad-engines']['cpu_benefit'] == 'none')
    check('seed: scoring data profile recommends mariadb consistently',
          seeds['scoring']['recommended_backend'] == 'mariadb'
          and recommend_backend(types.SimpleNamespace(
              **seeds['scoring']))['backend'] == 'mariadb')
    check('seed: topology data profile recommends sqlite consistently',
          seeds['topology']['recommended_backend'] == 'sqlite'
          and recommend_backend(types.SimpleNamespace(
              **seeds['topology']))['backend'] == 'sqlite')
    check('seed: every seed is declared-labeled with provenance',
          all(s['fidelity'] == 'declared' and s['provenance_id']
              for s in SEED_MODULE_RESOURCE_PROFILES))
    check('seed: profile_dict serializes every seed',
          all(profile_dict(types.SimpleNamespace(**s))['subjectName']
              for s in SEED_MODULE_RESOURCE_PROFILES))

    # --- real-tree sanity: the topology module reads as data ----------------
    real_v = classify_module(_mgr(), 'topology')
    check('real tree: topology module classifies data '
          f'(got {real_v["character"]})',
          real_v['character'] == 'data')
    src = scan_module_source('resources')
    check('real tree: resources module scan sees its own classes',
          'ModuleResourceProfile' in src['dataClasses'])

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
