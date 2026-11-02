"""board_bench_solution_selftest - bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): Systems are templates, Solutions are bound specifics, and a Bench
Solution is WHOLE only when its three Solutions exist, are complete and name the Systems its Bench System composes, with conditions inside the Thermal
System's range. The plan's proof: the UNO light bench whole; remove the Thermal Solution -> "not whole" in words; every other leg's words; the doors; the
manifest.

    PYTHONPATH=.:modules python3 -m board.board_bench_solution_selftest      # from polari-framework/
"""
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _foreign(m, cls, **fields):
    """A row of another module (cmod FirmwareSolution, the Hardware Solution) as the engine reads it: by attribute from the manager's tables."""
    row = types.SimpleNamespace(**fields)
    m.objectTables.setdefault(cls, {})[fields['name']] = row
    return row


def _seed(m):
    from board.objects.board import BenchConditions, BenchSolution, BenchSystem, ThermalMitigation, ThermalSolution, ThermalSystem
    ThermalSystem(manager=m, name='open-air-desk', title='Open air on a desk', ambient_min_c=15.0, ambient_max_c=35.0, mitigations_allowed='none,sink')
    ThermalMitigation(manager=m, name='toy-sink', kind='sink', part='TOY-SINK', value=20.0, unit='K/W', source='toy')
    ThermalMitigation(manager=m, name='toy-fan', kind='fan', part='TOY-FAN', value=10.0, unit='m3/h', source='toy')
    ThermalSolution(manager=m, name='uno-light-bare', title='open air, nothing added', system='open-air-desk', mitigations='')
    BenchSystem(manager=m, name='uno-light-bench', title='UNO light bench', hardware_system='uno-class-led', firmware_system='uno-light-graph',
                thermal_system='open-air-desk')
    BenchConditions(manager=m, name='room', ambient_min_c=18.0, ambient_max_c=30.0)
    BenchConditions(manager=m, name='garage', ambient_min_c=-5.0, ambient_max_c=30.0)
    _foreign(m, 'HardwareSolution', name='uno-light-assembly', system='uno-class-led', undetermined='')
    _foreign(m, 'FirmwareSolution', name='uno-light', graph='uno-light-graph', status='built')
    _foreign(m, 'FirmwareSolution', name='uno-light-seeded', graph='uno-light-graph', status='seeded')
    BenchSolution(manager=m, name='uno-light-on-desk', title='UNO light on the desk', bench='home-bench', system='uno-light-bench',
                  hardware_solution='uno-light-assembly', firmware_solution='uno-light', thermal_solution='uno-light-bare', conditions='room')


def main():
    from board.custom import bench_solution_whole as W
    m = _manager()
    _seed(m)
    bs = m.objectTables['BenchSolution']
    row = next(iter(bs.values()))
    w = W.whole(m, 'uno-light-on-desk')
    check('PROOF: the UNO light bench is WHOLE: Bench System named, Hardware / Firmware / Thermal Solutions exist, complete, each of the composed System, '
          'conditions inside the Thermal System range', w['whole'] and w['missing'] == [] and all(l['ok'] for l in w['legs'].values()), w)
    row.thermal_solution = ''
    w = W.whole(m, 'uno-light-on-desk')
    check('PROOF: remove the Thermal Solution -> not whole, in words (and "nothing added" is still a Thermal Solution)',
          not w['whole'] and w['missing'] == ['no Thermal Solution named (open air with nothing added is still a Thermal Solution: make one and name it)'],
          w['missing'])
    row.thermal_solution = 'uno-light-bare'
    ts = next(iter(m.objectTables['ThermalSolution'].values()))
    ts.mitigations = 'toy-fan'
    w = W.whole(m, 'uno-light-on-desk')
    check('A mitigation of a kind the Thermal System does not allow is said', w['missing'] == ["mitigation 'toy-fan' is a fan; Thermal System 'open-air-desk' allows none, sink"],
          w['missing'])
    ts.mitigations = 'toy-sink'
    check('An allowed mitigation (the clip-on sink) makes it whole again', W.whole(m, 'uno-light-on-desk')['whole'])
    row.conditions = 'garage'
    w = W.whole(m, 'uno-light-on-desk')
    check('Conditions outside the Thermal System range are said with both ranges',
          w['missing'] == ["conditions 'garage' span -5..30 C; Thermal System 'open-air-desk' is meant for 15..35 C"], w['missing'])
    row.conditions = 'room'
    row.firmware_solution = 'uno-light-seeded'
    w = W.whole(m, 'uno-light-on-desk')
    check('A Firmware Solution that is only seeded is not complete, in words', w['missing'] == ["Firmware Solution 'uno-light-seeded' is seeded, not built"], w['missing'])
    row.firmware_solution = 'uno-light'
    m.objectTables['HardwareSolution']['uno-light-assembly'].system = 'other-family'
    w = W.whole(m, 'uno-light-on-desk')
    check('A Hardware Solution of another Hardware System than the Bench System composes is said',
          w['missing'] == ["Hardware Solution 'uno-light-assembly' is of Hardware System 'other-family'; the Bench System composes 'uno-class-led'"], w['missing'])
    m.objectTables['HardwareSolution']['uno-light-assembly'].system = 'uno-class-led'
    row.system = ''
    w = W.whole(m, 'uno-light-on-desk')
    check('No Bench System named -> said; the other legs still judged on their own', w['missing'] == ['no Bench System named'] and w['legs']['firmware']['ok'], w['missing'])
    row.system = 'uno-light-bench'
    check('NO OVERLAP: the Bench System holds no parts or values, the Thermal Solution no temperatures, the Bench Solution only references',
          not ({'ambient_min_c', 'mitigations', 'boards'} & set(vars(next(iter(m.objectTables['BenchSystem'].values())))))
          and not ({'ambient_min_c', 'ambient_max_c', 'air'} & set(vars(ts))) and 'mitigations_allowed' not in vars(ts))
    try:
        W.whole(m, 'nope')
        nf = ''
    except W.NotFound as e:
        nf = str(e)
    check('An unknown Bench Solution is refused in words', nf == "no Bench Solution 'nope'", nf)
    from board.bench_solution_api import BenchSolutionAPI
    api = BenchSolutionAPI(polServer=None, manager=m)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_listing(None, resp)
    one = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get(None, one, 'uno-light-on-desk')
    bad = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get(None, bad, 'nope')
    check('DOORS: GET bench-solutions lists the row as whole; GET one -> the legs; unknown -> 404',
          resp.media['rows'] == [{'name': 'uno-light-on-desk', 'title': 'UNO light on the desk', 'whole': True, 'missing': 0}]
          and one.media['whole'] and set(one.media['legs']) == {'system', 'hardware', 'firmware', 'thermal', 'conditions'} and bad.status.startswith('404'),
          (resp.media, bad.status))
    from moduleService.manifests import conform
    r = conform('board')
    check('MANIFEST: pol modules conform board is clean with the new rows and files listed', r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
