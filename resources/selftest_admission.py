"""
Selftest for resources.admission_advisor (res-4).

Run from polari-framework/:  python3 -m resources.selftest_admission

Stdlib-only, fake manager. Covers the four verdicts (route-to-storage
with a named backend + reason; fits-as-is on the benefit-appropriate
node — single-threaded lands on the SMALL node even when a big one is
free; fits-with-reallocation naming the move + gain; would-break
naming the conflict + limiting resource + what to add), set
feasibility yes/tight/no with the limiting resource, honest absence
(unobserved nodes, unprofiled modules), the efficiency-swap
suggestion, and cost-aware provider ranking.
"""

import types

from resources.admission_advisor import (
    assess_module_admission, assess_set_feasibility,
    efficiency_suggestions, node_allocation, rank_candidates_by_fit,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _machine(name, cpus, avail_ram, free_disk=100000.0):
    return types.SimpleNamespace(
        name=name, ssh_alias='', arch='x86_64', mem_gb=0.0,
        logical_cpus=cpus, physical_cpus=cpus,
        total_ram_mb=avail_ram * 2, available_ram_mb=avail_ram,
        total_disk_mb=free_disk * 2, free_disk_mb=free_disk,
        cgroup_ram_limit_mb=0.0, load_snapshot_json='{}',
        resource_source='observed-local', resource_observed_at='t',
        system_info_url='', roles_json='[]', swarm_role='none',
        repo_dir='', source='manual', notes='')


def _profile(subject, **over):
    fields = dict(
        name=f'{subject}-resource-profile', subject_name=subject,
        subject_kind='module', character='compute',
        min_ram_mb=64.0, min_disk_mb=10.0, min_threads=1,
        thread_ceiling=1, cpu_benefit='none', ram_benefit='none',
        scales_note='', image_mb=0.0, deps_mb=0.0, est_row_bytes=0,
        growth_rate='low', access_pattern='warm',
        durability='durable', concurrency='single',
        recommended_backend='', fidelity='declared',
        provenance_id='seed', notes='')
    fields.update(over)
    return types.SimpleNamespace(**fields)


def _instance(name, machine, db_backend='sqlite'):
    return types.SimpleNamespace(
        name=name, machine_name=machine, db_backend=db_backend,
        service_kinds_json='[]')


def _assignment(module, instance):
    return types.SimpleNamespace(
        name=f'{module}@{instance}', module_name=module,
        instance_name=instance, state='enabled', topology_name='t')


def _mgr(machines, profiles, instances=(), assignments=()):
    return types.SimpleNamespace(
        objectTables={
            'PolariNodeMachine': {m.name: m for m in machines},
            'ModuleResourceProfile': {p.name: p for p in profiles},
            'InstanceDefinition': {i.name: i for i in instances},
            'ModuleAssignment': {a.name: a for a in assignments},
            'PolariModule': {},
        },
        objectTypingDict={},
        db=types.SimpleNamespace(saveInstanceInDB=lambda row: None))


def main():
    big = _machine('big', 8, 12000.0)
    med = _machine('med', 4, 6000.0)
    small = _machine('small', 2, 3000.0)

    # --- route-to-storage ------------------------------------------------
    dmgr = _mgr([big, small],
                [_profile('rowsmod', character='data',
                          concurrency='shared', growth_rate='high',
                          recommended_backend='mariadb')],
                instances=[_instance('shared-infra', 'big',
                                     db_backend='mariadb')])
    d = assess_module_admission(dmgr, 'rowsmod')
    check('data module -> route-to-storage w/ backend + reason',
          d['verdict'] == 'route-to-storage'
          and d['backend'] == 'mariadb' and d['reason'])
    check('route-to-storage suggestion names a carrier instance',
          'shared-infra' in d['suggestion']['action'])

    # --- fits-as-is, benefit-aware ------------------------------------------
    fmgr = _mgr(
        [big, med, small],
        [_profile('singlemod', thread_ceiling=1, cpu_benefit='none'),
         _profile('scalemod', thread_ceiling=8,
                  cpu_benefit='linear'),
         _profile('rammod', thread_ceiling=1, cpu_benefit='none',
                  ram_benefit='linear', min_ram_mb=512.0)],
        instances=[_instance('big-inst', 'big'),
                   _instance('med-inst', 'med'),
                   _instance('small-inst', 'small')])
    s = assess_module_admission(fmgr, 'singlemod')
    check('single-threaded -> SMALLEST adequate node (big stays free)',
          s['verdict'] == 'fits-as-is' and s['node'] == 'small'
          and 'single-threaded' in s['rationale'])
    check('fits-as-is suggestion = pol allocate at an instance there',
          'pol allocate singlemod small-inst'
          in s['suggestion']['action'])
    sc = assess_module_admission(fmgr, 'scalemod')
    check('scaling module -> biggest adequate node',
          sc['verdict'] == 'fits-as-is' and sc['node'] == 'big'
          and 'scales' in sc['rationale'])
    rm = assess_module_admission(fmgr, 'rammod')
    check('RAM-bound module -> most free RAM',
          rm['verdict'] == 'fits-as-is' and rm['node'] == 'big'
          and 'RAM' in rm['rationale'])

    # --- fits-with-reallocation -----------------------------------------------
    crowd_profiles = [
        _profile('hog', min_threads=1, thread_ceiling=1,
                 cpu_benefit='none'),
        _profile('bigother', min_threads=6, thread_ceiling=8,
                 cpu_benefit='linear'),
        _profile('medfull', min_threads=3, thread_ceiling=4,
                 cpu_benefit='sublinear'),
        _profile('smallfull', min_threads=2, thread_ceiling=2,
                 cpu_benefit='sublinear'),
        _profile('newscaler', min_threads=2, thread_ceiling=8,
                 cpu_benefit='linear'),
    ]
    cmgr = _mgr(
        [big, med, small], crowd_profiles,
        instances=[_instance('big-inst', 'big'),
                   _instance('med-inst', 'med'),
                   _instance('small-inst', 'small')],
        assignments=[_assignment('hog', 'big-inst'),
                     _assignment('bigother', 'big-inst'),
                     _assignment('medfull', 'med-inst'),
                     _assignment('smallfull', 'small-inst')])
    r = assess_module_admission(cmgr, 'newscaler')
    check('crowded -> fits-with-reallocation naming the move',
          r['verdict'] == 'fits-with-reallocation'
          and r['moves'][0]['module'] == 'hog'
          and r['moves'][0]['machineTo'] == 'med')
    check('reallocation carries the net efficiency gain',
          'single-threaded' in r['netEfficiencyGain']
          and 'freeing' in r['netEfficiencyGain'])
    check('reallocation suggestion is two pol allocate commands',
          r['suggestion']['action'].count('pol allocate') == 2)

    # --- would-break --------------------------------------------------------
    wb_profiles = crowd_profiles + [
        _profile('monster', min_ram_mb=99999.0, min_threads=2)]
    wmgr = _mgr([big, med, small], wb_profiles,
                instances=[_instance('big-inst', 'big')],
                assignments=[_assignment('bigother', 'big-inst')])
    w = assess_module_admission(wmgr, 'monster')
    check('oversized -> would-break naming conflict + limiting',
          w['verdict'] == 'would-break' and 'RAM' in
          w['limitingResource'] and 'violating' in w['conflict'])
    check('would-break names what to add + changes nothing',
          'add a node' in w['needed']
          and 'nothing was changed' in w['suggestion']['action'])

    # --- honest absence -------------------------------------------------------
    blind = _machine('blind', 0, 0.0)
    blind.logical_cpus = 0
    blind.total_ram_mb = 0.0
    blind.resource_source = 'unknown'
    bmgr = _mgr([blind], [_profile('anymod')])
    b = assess_module_admission(bmgr, 'anymod')
    check('no observed nodes -> unknown verdict + observe-first knob',
          not b['ok'] and b['verdict'] == 'unknown'
          and 'system_info_url' in b['suggestion']['knob'])

    # --- set feasibility --------------------------------------------------------
    smgr = _mgr([big, med, small],
                [_profile('a', min_ram_mb=1000.0, image_mb=500.0,
                          min_threads=2),
                 _profile('b', min_ram_mb=2000.0, image_mb=1000.0,
                          min_threads=2)],
                instances=[_instance('big-inst', 'big')])
    yes = assess_set_feasibility(smgr, ['a', 'b'], 'big')
    check('set fits comfortably -> yes',
          yes['feasible'] == 'yes' and yes['totals']['minThreads'] == 4)
    no = assess_set_feasibility(smgr, ['a', 'b'], 'small')
    check('set overflows the small node -> no + limiting resource',
          no['feasible'] == 'no'
          and no['limitingResource'] in ('threads', 'ram'))
    tight_mgr = _mgr([_machine('snug', 8, 3500.0)],
                     [_profile('a', min_ram_mb=1500.0),
                      _profile('b', min_ram_mb=1500.0)],
                     instances=[])
    tight = assess_set_feasibility(tight_mgr, ['a', 'b'], 'snug')
    check('set at >80% of a budget -> tight',
          tight['feasible'] == 'tight'
          and tight['limitingResource'] == 'ram')
    part = assess_set_feasibility(smgr, ['a', 'ghostmod'], 'big')
    check('unprofiled module in the set NAMED, not guessed',
          part['unprofiled'] == ['ghostmod']
          and 'NOT counted' in part['note'])
    off = assess_set_feasibility(bmgr, ['anymod'], 'blind')
    check('unobserved node -> observe-first refusal',
          not off['ok'] and 'observe first' in off['error'])

    # --- efficiency suggestions ---------------------------------------------------
    emgr = _mgr(
        [big, small],
        [_profile('lazy', thread_ceiling=1, cpu_benefit='none'),
         _profile('worker', thread_ceiling=8, cpu_benefit='linear')],
        instances=[_instance('big-inst', 'big'),
                   _instance('small-inst', 'small')],
        assignments=[_assignment('lazy', 'big-inst'),
                     _assignment('worker', 'small-inst')])
    eff = efficiency_suggestions(emgr)
    check('single-threaded on the big node + scaler cramped -> swap',
          len(eff) == 1
          and eff[0]['kind'] == 'efficiency-swap-suggested'
          and 'lazy' in eff[0]['subject']
          and eff[0]['suggestedCommand'].count('pol allocate') == 2)
    quiet = efficiency_suggestions(_mgr([big, small], []))
    check('no profiles -> no efficiency noise', quiet == [])

    # --- cost-aware provider ranking ------------------------------------------------
    order = rank_candidates_by_fit(
        fmgr, 'singlemod', ['big-inst', 'small-inst', 'med-inst'])
    check('provider ranking: single-threaded -> smallest machine first',
          order[0] == 'small-inst')
    order2 = rank_candidates_by_fit(
        fmgr, 'scalemod', ['small-inst', 'big-inst'])
    check('provider ranking: scaler -> biggest machine first',
          order2[0] == 'big-inst')
    keep = rank_candidates_by_fit(
        fmgr, 'unprofiled-mod', ['x', 'y'])
    check('provider ranking: no profile -> order untouched',
          keep == ['x', 'y'])

    # --- allocation rollup ------------------------------------------------------------
    alloc = node_allocation(cmgr)
    check('node_allocation: floors summed + free threads derived',
          alloc['big']['allocation']['minThreads'] == 7
          and alloc['big']['allocation']['freeThreads'] == 1)

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
