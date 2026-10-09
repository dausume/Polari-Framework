"""uno_core_demo_selftest — ucd-2 (UNO_CORE_DEMO_PLAN.md §2): the manifest names every composed part and conforms;
a hardware-app manifest with no `app.realization` is REFUSED by `moduleService.manifests.validate` (D-ucd-2); the
existing kvm hardware-app manifests (isle_relay/isle_guestnet/voron) still validate after the realization=kvm
migration; readiness() over the SEED tables (no manager) yields one row per part — `exists` true for every part
this worktree actually has seeded, false/missing honestly for one that is not (a parallel agent's own slice may not
have landed), never a crash — and a `composition` row whose status is the weakest of the six.

    PYTHONPATH=.:modules python3 -m uno_core_demo.uno_core_demo_selftest      # from polari-framework/
"""
passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def manifest_names_every_part():
    from moduleService.manifests import load
    from uno_core_demo.custom.readiness import PARTS_ORDER
    m = load('uno_core_demo')
    check('polari-app.json loads', m is not None)
    parts = (m or {}).get('parts') or {}
    check('the manifest\'s `parts` names every one of the six composed parts', set(PARTS_ORDER) <= set(parts),
          [p for p in PARTS_ORDER if p not in parts])
    check('firmware names FirmwareSolution uno-button-clock', parts.get('firmware') == {'class': 'FirmwareSolution', 'name': 'uno-button-clock'})
    check('bridge names the button-clock HardwareBridgeDefinition + its two wire classes',
          parts.get('bridge', {}).get('name') == 'button-clock' and parts.get('bridge', {}).get('state_class') == 'ButtonClockState'
          and parts.get('bridge', {}).get('event_class') == 'ButtonClockEvent')
    check('polari_app names the solution + the display', parts.get('polari_app') == {'solution': 'button-clock-ledger', 'display': 'uno-core-demo'})
    check('cross_domain/circuit/purpose each name a class + a name',
          all(parts.get(p, {}).get('class') and parts.get(p, {}).get('name') for p in ('cross_domain', 'circuit', 'purpose')))


def conforms():
    from moduleService.manifests import conform
    r = conform('uno_core_demo')
    check('pol modules conform uno_core_demo is clean', r['ok'], r['findings'])
    check('conform reports kind hardware-app', r.get('kind') == 'hardware-app')


def realization_is_refused_without_it():
    from moduleService.manifests import validate, REALIZATIONS
    base = {'schema': 'polari-app/1', 'id': 'x', 'package': 'x', 'title': 'X', 'app': {'kind': 'hardware-app', 'agentTier': 'hardware'},
            'requires': {'modules': []}, 'files': {}, 'classes': []}
    problems = validate(base)
    check('a hardware-app manifest with NO app.realization is refused, naming D-ucd-2',
          any('realization' in p and 'D-ucd-2' in p for p in problems), problems)
    for realization in REALIZATIONS:
        tier = 'hardware' if realization == 'kvm' else 'member'
        ok_manifest = dict(base, app=dict(base['app'], realization=realization, agentTier=tier))
        check('realization=%s with agentTier=%s validates clean' % (realization, tier), validate(ok_manifest) == [], validate(ok_manifest))
    bridge_wrong_tier = dict(base, app=dict(base['app'], realization='bridge', agentTier='hardware'))
    check('realization=bridge is fine with agentTier=hardware too (member OR hardware — never REQUIRES libvirt)',
          validate(bridge_wrong_tier) == [])
    kvm_wrong_tier = dict(base, app=dict(base['app'], realization='kvm', agentTier='member'))
    check('realization=kvm with agentTier=member is refused (kvm needs the hardware tier)',
          any('kvm' in p and 'hardware' in p for p in validate(kvm_wrong_tier)), validate(kvm_wrong_tier))


def existing_kvm_apps_still_conform():
    from moduleService.manifests import conform, load
    for pkg in ('isle_relay', 'isle_guestnet', 'voron'):
        m = load(pkg)
        check('%s migrated to realization=kvm' % pkg, (m or {}).get('app', {}).get('realization') == 'kvm')
        r = conform(pkg)
        check('%s still conforms after the migration' % pkg, r['ok'], r['findings'])


def tier_derivation():
    from moduleService.tier_reach import tiers_for, hardware_app_min_tier, bridge_requirement, install_allowed
    kvm_app = {'kind': 'hardware-app', 'realization': 'kvm'}
    bridge_app = {'kind': 'hardware-app', 'realization': 'bridge'}
    check('kvm realization needs the hardware tier', hardware_app_min_tier(kvm_app) == 'hardware'
          and tiers_for('hardware-app', kvm_app) == ['hardware', 'core'])
    check('bridge realization needs only member ("host") — never hardware/libvirt', hardware_app_min_tier(bridge_app) == 'member'
          and tiers_for('hardware-app', bridge_app) == ['member', 'hardware', 'core'])
    check('a bridge hardware-app installs on a plain member (never needs libvirt)', install_allowed(bridge_app, 'member') is True)
    check('a kvm hardware-app does NOT install on a plain member', install_allowed(kvm_app, 'member') is False)
    req = bridge_requirement(bridge_app)
    check('bridge_requirement names the proof class + the plain-words need', req is not None and req['proof_class'] == 'BridgingCapability'
          and 'BridgingCapability' in req['needs'] or 'proven' in req['needs'])
    check('bridge_requirement is None for a kvm realization', bridge_requirement(kvm_app) is None)


def readiness_over_seed_tables():
    from uno_core_demo.custom import readiness as RD
    from moduleService.manifests import load
    parts = (load('uno_core_demo') or {}).get('parts') or RD.DEFAULT_PARTS
    rows = RD.readiness(manager=None, parts=parts)
    names = [r['part'] for r in rows]
    check('one row per part + the composition, in order', names == list(RD.PARTS_ORDER) + ['composition'], names)
    check('every row names a plain-words why, never empty', all(r['why'] for r in rows))
    check('every row carries exists as a real bool', all(isinstance(r['exists'], bool) for r in rows))
    by_part = {r['part']: r for r in rows}
    check('circuit (seeded in electrodevice) exists', by_part['circuit']['exists'] is True, by_part['circuit'])
    check('purpose (seeded in cmod) exists', by_part['purpose']['exists'] is True, by_part['purpose'])
    check('cross_domain (seeded in hwnocode, ucd-1) exists', by_part['cross_domain']['exists'] is True, by_part['cross_domain'])
    check('polari_app (button-clock-ledger + /display/uno-core-demo, ucd-1) exists', by_part['polari_app']['exists'] is True, by_part['polari_app'])
    comp = by_part['composition']
    missing_parts = [p for p, r in by_part.items() if p != 'composition' and not r['exists']]
    if missing_parts:
        check('composition is "incomplete" when any part is missing (named: %s)' % ', '.join(missing_parts),
              comp['status'] == 'incomplete', comp)
    else:
        check('composition carries the weakest part\'s own status when every part exists',
              comp['status'] in {r['status'] for p, r in by_part.items() if p != 'composition'}, comp)
    # never a crash when a part is absent (e.g. a worktree with no FirmwareSolution row yet)
    no_firmware_parts = dict(parts, firmware={'class': 'FirmwareSolution', 'name': 'definitely-not-a-real-row'})
    rows2 = RD.readiness(manager=None, parts=no_firmware_parts)
    fw = next(r for r in rows2 if r['part'] == 'firmware')
    check('a named-but-absent part reads exists=False, status=missing — never a crash', fw['exists'] is False and fw['status'] == 'missing', fw)
    comp2 = next(r for r in rows2 if r['part'] == 'composition')
    check('composition is "incomplete" when the firmware part is absent', comp2['status'] == 'incomplete', comp2)


if __name__ == '__main__':
    manifest_names_every_part()
    conforms()
    realization_is_refused_without_it()
    existing_kvm_apps_still_conform()
    tier_derivation()
    readiness_over_seed_tables()
    print('%d/%d checks passed' % (passed, total))
    import sys
    sys.exit(0 if passed == total else 1)
