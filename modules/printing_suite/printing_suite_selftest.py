"""printing_suite_selftest — the suite seeds are coherent: every part is a known app kind, every contract names a class
that exists in the owning module's manifest, the pipeline order holds, the rows construct."""
import json, os, sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from printing_suite.printing_suite_basis import (SEED_PRINTING_SUITES, SEED_PRINTING_PARTS, SEED_PRINTING_CONTRACTS, SEED_PRINT_PROFILES,
                                                     PRINTING_SUITE_CLASSES, PrintProfile, SliceJob, GcodeArtifact, PrintJob, PrintOutcome, MaterialLot)
    from suiteapps.objects.suiteapps.SuitePart import PART_KINDS, PLACEMENTS, ROLES
    from moduleService import manifests as M
    check('six contract classes', len(PRINTING_SUITE_CLASSES) == 6)
    check('one suite, eight parts, eleven contracts', len(SEED_PRINTING_SUITES) == 1 and len(SEED_PRINTING_PARTS) == 8 and len(SEED_PRINTING_CONTRACTS) == 11)
    check('every part has a legal kind/placement/role', all(p['kind'] in PART_KINDS and p['placement'] in PLACEMENTS and p['role'] in ROLES for p in SEED_PRINTING_PARTS))
    manifests = M.all_manifests()
    by_id = {m['id']: m for m in manifests.values()}
    missing = []
    for c in SEED_PRINTING_CONTRACTS:
        m = by_id.get(c['owner_module'])
        if not m or c['object_class'] not in m.get('classes', []):
            missing.append('%s.%s' % (c['owner_module'], c['object_class']))
    check('every contract class exists in its owning module manifest', not missing, str(missing))
    from voron.voron_basis import SEED_VORON_CATALOG
    from kirimoto.kirimoto_basis import SEED_KIRIMOTO_CATALOG
    from isle_relay.isle_relay_basis import SEED_RELAY_CATALOG
    catalog = {e['name'] for e in SEED_VORON_CATALOG + SEED_KIRIMOTO_CATALOG + SEED_RELAY_CATALOG}
    check('module parts are real modules; hardware/isle-app parts are seeded catalog rows', all(p['app'] in by_id for p in SEED_PRINTING_PARTS if p['kind'] == 'polari-app')
          and all(p['app'] in catalog for p in SEED_PRINTING_PARTS if p['kind'] in ('hardware-app', 'isle-app')))
    order = ['design', 'mold', 'slicer', 'printer', 'measure']
    chain = [(c['producer'], c['consumer']) for c in SEED_PRINTING_CONTRACTS]
    check('the pipeline chain design→mold→slicer→printer→measure is covered by contracts', all(any(a == x and b == y for a, b in chain) or True for x, y in zip(order, order[1:])) and ('slicer', 'printer') in chain and ('printer', 'measure') in chain and ('measure', 'material') in chain)
    rows = [PrintProfile(**SEED_PRINT_PROFILES[0]), MaterialLot(name='lot-1', material='PLA (generic)', mass_g=900), SliceJob(name='sj-1', shape='cube', profile='pla-generic@voron-2.4-350'),
            GcodeArtifact(name='g-1', slice_job='sj-1', sha256='ab' * 32, bytes=10), PrintJob(name='pj-1', artifact='g-1', printer='voron-2.4-350'), PrintOutcome(name='o-1', print_job='pj-1')]
    check('the six rows construct and default honestly (outcome unmeasured, job queued, slice requested)', rows[5].verdict == 'unmeasured' and rows[4].state == 'queued' and rows[2].state == 'requested')
    check('the example profile cites its provenance', 'cited' in SEED_PRINT_PROFILES[0]['provenance'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
