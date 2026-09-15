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
    check('four tiers in order', TIERS == ('access', 'member', 'hardware', 'core'))
    check('every manifest kind has a lowest tier', all(k in MIN_TIER for k in APP_KINDS), [k for k in APP_KINDS if k not in MIN_TIER])
    check('access-app runs on every tier (it hosts nothing)', tiers_for('access-app') == ['access', 'member', 'hardware', 'core'])
    check('polari-app / isle-app / library need a member or above', tiers_for('polari-app') == ['member', 'hardware', 'core'] and tiers_for('isle-app') == ['member', 'hardware', 'core'] and tiers_for('library') == ['member', 'hardware', 'core'])
    check('hardware kinds need the hardware tier or the core', tiers_for('hardware-app') == ['hardware', 'core'] and tiers_for('hardware-extension-app') == ['hardware', 'core'])
    check('unknown kind is treated as a hosted app', tiers_for('') == ['member', 'hardware', 'core'])
    check('access-only device: a polari-app gets the ACCESS ONLY notice naming the shell', 'ACCESS ONLY' in tier_notice('polari-app', 'access') and 'shell' in tier_notice('polari-app', 'access'))
    check('access-only device: an access-app has no notice', tier_notice('access-app', 'access') == '')
    check('member: a hardware-app gets the hardware-tier notice; a polari-app none; host is an alias of member', 'HARDWARE tier' in tier_notice('hardware-app', 'host') and tier_notice('polari-app', 'member') == '')
    check('runs_on agrees', runs_on('polari-app', 'host') and not runs_on('polari-app', 'access') and runs_on('access-app', 'access'))
    from moduleService.tier_reach import install_allowed
    hw = {'kind': 'hardware-app', 'agentTier': 'hardware'}; core = {'kind': 'polari-app', 'agentTier': 'core'}; web = {'kind': 'polari-app', 'agentTier': 'member'}
    check('his rules: access → no installs; member → web yes, hardware no, core no; hardware → web + hardware, core no; core → everything',
          not install_allowed(web, 'access') and install_allowed(web, 'member') and not install_allowed(hw, 'member') and not install_allowed(core, 'member')
          and install_allowed(hw, 'hardware') and not install_allowed(core, 'hardware') and install_allowed(core, 'core') and install_allowed(hw, 'core'))
    check('core-exclusive apps are hosted by the core only', tiers_for('polari-app', core) == ['core'])
    f = access_form('gears', 'Gears')
    check('the access form of an app is its launcher package, kind access-app', f['kind'] == 'access-app' and f['package'] == 'polari-launcher-gears' and 'hosts nothing' in f['reading'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
