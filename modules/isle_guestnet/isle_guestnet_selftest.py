"""isle_guestnet_selftest — the guest-network rows, the guest they seed, the render, the exposure ledger discipline."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from isle_guestnet.isle_guestnet_basis import (GuestNetworkDefinition, GuestNetworkExposure, SEED_GUEST_NETWORKS, SEED_GUEST_EXPOSURES,
                                                   SEED_GUESTNET_HARDWARE_APPS, SEED_GUESTNET_CATALOG, ISLE_GUESTNET_CLASSES)
    from hardwareapps.custom.uci_profiles import render_uci
    from hardwareapps.custom.domain_xml import render_domain
    from islemesh.islemesh_catalog import install_plan
    import json
    check('three row classes', len(ISLE_GUESTNET_CLASSES) == 3)
    check('no exposures by default (guests reach nothing on the isle)', SEED_GUEST_EXPOSURES == [])
    n = GuestNetworkDefinition(**SEED_GUEST_NETWORKS[0])
    uci, r = render_uci(dict(SEED_GUESTNET_HARDWARE_APPS[0]))
    check('guestnet UCI: REJECT into the isle, client isolation, wan only', not r and "forward='REJECT'" in uci and "isolate='1'" in uci and "dest='wan'" in uci and 'guest-allow' not in uci)
    e = GuestNetworkExposure(name='guest-1:polari', network='guest-1', isle_host='10.10.0.2', app_name='polari', allowed_by='dustin', reason='demo')
    app = dict(SEED_GUESTNET_HARDWARE_APPS[0], uci_params_json=json.dumps(n.uci_params(allow_hosts=[e.isle_host])))
    uci2, r2 = render_uci(app)
    check('an exposure row becomes exactly one allow rule', not r2 and uci2.count("name='guest-allow-") == 1 and "dest_ip='10.10.0.2'" in uci2)
    xml, ref = render_domain(dict(app, image_sha256_raw='ef' * 32))
    check('pinned image renders the guest (384 MB, 1 vcpu)', xml and not ref and "<memory unit='MiB'>384</memory>" in xml)
    plan = install_plan(SEED_GUESTNET_CATALOG[0])
    check('store plan = isle vm define/start on the hardware tier', plan['ok'] and plan['requires_tier'] == 'hardware')
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
