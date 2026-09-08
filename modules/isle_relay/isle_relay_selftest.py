"""isle_relay_selftest — the relay rows, the guest row they seed, its render through hardwareapps."""
import json, sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from isle_relay.isle_relay_basis import RelayNodeDefinition, SEED_RELAY_NODES, SEED_RELAY_HARDWARE_APPS, SEED_RELAY_CATALOG, ISLE_RELAY_CLASSES
    from hardwareapps.custom.domain_xml import render_domain
    from hardwareapps.custom.uci_profiles import render_uci
    from islemesh.islemesh_catalog import install_plan
    r = RelayNodeDefinition(**SEED_RELAY_NODES[0])
    check('two row classes', len(ISLE_RELAY_CLASSES) == 2)
    check('relay params feed the relay UCI profile', r.uci_params()['vlan'] == 30 and r.uci_params()['ssid'] == 'isle-relay')
    app = dict(SEED_RELAY_HARDWARE_APPS[0])
    _, ref = render_domain(app)
    check('unpinned image is refused by name (deploy-time pin)', ref and any('sha' in x for x in ref))
    xml, ref = render_domain(dict(app, image_sha256_raw='cd' * 32), [{'kind': 'usb', 'vendor_id': '0bda', 'product_id': '8812', 'description': 'wifi'}])
    check('pinned + a WiFi adapter renders the guest', xml and not ref and '<name>isle-relay</name>' in xml)
    uci, r2 = render_uci(app)
    check('relay UCI renders (forward ACCEPT, bearer port)', not r2 and "forward='ACCEPT'" in uci and "dest_port='4242'" in uci)
    plan = install_plan(SEED_RELAY_CATALOG[0])
    check('store plan = isle vm define/start, hardware tier', plan['ok'] and plan['requires_tier'] == 'hardware' and plan['steps'][0].startswith('isle vm define isle-relay'))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
