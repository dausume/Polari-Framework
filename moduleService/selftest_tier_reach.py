"""selftest_tier_reach — member tiers (access / host / hardware) and what each may install: access-only installs
shells only; hosted kinds need host; KVM kinds need hardware; the notice is a sentence, never a refusal."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


def main():
    from moduleService.tier_reach import tiers_for, runs_on, tier_notice, access_form, TIERS, MIN_TIER
    from moduleService.manifests import APP_KINDS
    check('three tiers in order', TIERS == ('access', 'host', 'hardware'))
    check('every manifest kind has a lowest tier', all(k in MIN_TIER for k in APP_KINDS), [k for k in APP_KINDS if k not in MIN_TIER])
    check('access-app runs on every tier (it hosts nothing)', tiers_for('access-app') == ['access', 'host', 'hardware'])
    check('polari-app / isle-app / library need host or above', tiers_for('polari-app') == ['host', 'hardware'] and tiers_for('isle-app') == ['host', 'hardware'] and tiers_for('library') == ['host', 'hardware'])
    check('hardware kinds need the hardware tier', tiers_for('hardware-app') == ['hardware'] and tiers_for('hardware-extension-app') == ['hardware'])
    check('unknown kind is treated as a hosted app', tiers_for('') == ['host', 'hardware'])
    check('access-only device: a polari-app gets the ACCESS ONLY notice naming the shell', 'ACCESS ONLY' in tier_notice('polari-app', 'access') and 'shell' in tier_notice('polari-app', 'access'))
    check('access-only device: an access-app has no notice', tier_notice('access-app', 'access') == '')
    check('host device: a hardware-app gets the hardware-tier notice; a polari-app none', 'HARDWARE tier' in tier_notice('hardware-app', 'host') and tier_notice('polari-app', 'host') == '')
    check('runs_on agrees', runs_on('polari-app', 'host') and not runs_on('polari-app', 'access') and runs_on('access-app', 'access'))
    f = access_form('gears', 'Gears')
    check('the access form of an app is its launcher package, kind access-app', f['kind'] == 'access-app' and f['package'] == 'polari-launcher-gears' and 'hosts nothing' in f['reading'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
