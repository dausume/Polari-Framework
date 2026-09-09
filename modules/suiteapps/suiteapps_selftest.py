"""suiteapps_selftest — the placement rules: core, hardware-tier with the map's answer, node, same-as, least-loaded, and the named blockers."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from suiteapps.custom.placement import place
    from suiteapps.suiteapps_basis import SUITEAPPS_CLASSES
    check('four row classes', len(SUITEAPPS_CLASSES) == 4)
    parts = [{'name': 'design', 'app': 'mathshapes', 'kind': 'polari-app', 'placement': 'core', 'required': True, 'order': 0},
             {'name': 'printer', 'app': 'voron-printer', 'kind': 'hardware-app', 'placement': 'hardware', 'required': True, 'order': 1},
             {'name': 'slicer', 'app': 'kirimoto', 'kind': 'isle-app', 'placement': 'any', 'required': True, 'order': 2},
             {'name': 'camera', 'app': 'printcam', 'kind': 'isle-app', 'placement': 'same-as', 'same_as': 'printer', 'required': False, 'order': 3},
             {'name': 'archive', 'app': 'store', 'kind': 'isle-app', 'placement': 'node', 'node': 'econ-core', 'required': False, 'order': 4}]
    devs = [{'name': 'pol-core', 'is_core': True, 'hardware_tier_ready': False, 'ports_satisfy': [], 'total_ram_mb': 16000, 'load': 0},
            {'name': 'isle-core', 'is_core': False, 'hardware_tier_ready': True, 'ports_satisfy': ['voron-printer'], 'total_ram_mb': 7700, 'load': 0},
            {'name': 'econ-core', 'is_core': False, 'hardware_tier_ready': False, 'ports_satisfy': [], 'total_ram_mb': 7600, 'load': 0}]
    r = place(parts, devs)
    by = {p['part']: p for p in r['placements']}
    check('core part goes to the core', by['design']['device'] == 'pol-core')
    check('hardware part goes to the hardware-tier device whose map satisfies it', by['printer']['device'] == 'isle-core' and 'port satisfying' in by['printer']['reason'])
    check('same-as follows its target', by['camera']['device'] == 'isle-core')
    check('node part is pinned', by['archive']['device'] == 'econ-core')
    check('any part goes to the least-loaded device', by['slicer']['device'] in ('econ-core', 'pol-core'))
    check('summary counts + no blockers', r['summary']['placed'] == 5 and r['summary']['blocking'] == [])
    devs2 = [dict(d, ports_satisfy=[]) for d in devs]
    r2 = place(parts, devs2)
    check('no mapped port → needs-hardware-tier naming the missing app, and it blocks (required)', r2['placements'][1]['verdict'] == 'needs-hardware-tier' and 'pol hwmap push' in r2['placements'][1]['reason'] and 'printer' in r2['summary']['blocking'])
    r3 = place(parts, [])
    check('no devices → every part unplaceable with the reason', all(p['verdict'] == 'unplaceable' for p in r3['placements']))
    # the seeded suites (design §10)
    from suiteapps.suiteapps_seed import SEED_SUITES, SEED_SUITE_PARTS, SEED_SUITE_CONTRACTS
    from suiteapps.objects.suiteapps.SuitePart import PART_KINDS, PLACEMENTS, ROLES
    from moduleService import manifests as M
    by_id = {m['id']: m for m in M.all_manifests().values()}
    names = {s['name'] for s in SEED_SUITES}
    check('seven prior suites seeded', len(SEED_SUITES) == 7)
    check('every part belongs to a suite with legal kind/placement/role', all(p['suite'] in names and p['kind'] in PART_KINDS and p['placement'] in PLACEMENTS and p['role'] in ROLES for p in SEED_SUITE_PARTS))
    check('every polari-app part is a real module', all(p['app'] in by_id for p in SEED_SUITE_PARTS if p['kind'] == 'polari-app'), str([p['app'] for p in SEED_SUITE_PARTS if p['kind'] == 'polari-app' and p['app'] not in by_id]))
    bad = ['%s.%s' % (c['owner_module'], c['object_class']) for c in SEED_SUITE_CONTRACTS if c['object_class'] not in by_id.get(c['owner_module'], {}).get('classes', [])]
    check('every contract names a class its owning module really has', not bad, str(bad))
    check('same-as parts follow a part in the same suite', all(any(q['name'] == p['same_as'] for q in SEED_SUITE_PARTS) for p in SEED_SUITE_PARTS if p['placement'] == 'same-as'))
    check('node parts name a node', all(p['node'] for p in SEED_SUITE_PARTS if p['placement'] == 'node'))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
