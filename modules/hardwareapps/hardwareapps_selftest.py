"""hardwareapps_selftest — the renderers are pure and honest: a complete
definition renders the router-shaped domain + a UCI script; every gap is a
named refusal; an extension app renders no guest."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from hardwareapps.custom.domain_xml import render_domain
    from hardwareapps.custom.uci_profiles import render_uci
    from hardwareapps.hardwareapps_basis import HardwareAppDefinition, HARDWAREAPPS_CLASSES
    check('two row classes', len(HARDWAREAPPS_CLASSES) == 2)
    good = {'name': 'isle-relay', 'kind': 'hardware-app', 'role': 'relay', 'guest_kind': 'openwrt', 'vm_image_ref': 'openwrt-isle-router.qcow2',
            'image_sha256_raw': 'ab' * 32, 'memory_mb': 512, 'vcpus': 2, 'bridges_json': '["br-mgmt", "isle-br-0"]',
            'uci_profile': 'relay', 'uci_params_json': '{"uci": "relay", "vlan": 30, "cidr": "10.30.0.0/24", "ssid": "isle-relay"}'}
    xml, ref = render_domain(good, [{'kind': 'usb', 'vendor_id': '0bda', 'product_id': '8812', 'description': 'alfa'}, {'kind': 'nic', 'interface': 'enp3s0'}])
    check('complete definition renders a domain with no refusals', xml and not ref, str(ref))
    check('router shape: q35, host-passthrough, 8 pcie ports, virtio disk under /var/lib/libvirt/images',
          "machine='pc-q35-6.2'" in xml and "mode='host-passthrough'" in xml and xml.count("model='pcie-root-port'") == 8 and '/var/lib/libvirt/images/isle-relay.qcow2' in xml)
    check('bridges in NIC order + usb hostdev + macvtap', xml.index("bridge='br-mgmt'") < xml.index("bridge='isle-br-0'") and "<vendor id='0x0bda'/>" in xml and "dev='enp3s0'" in xml)
    _, ref2 = render_domain(dict(good, image_sha256_raw='', memory_mb=64, bridges_json='[]'))
    check('gaps are named refusals (sha, memory, bridges)', len(ref2) == 3 and any('sha' in r for r in ref2))
    _, ref3 = render_domain(dict(good, kind='hardware-extension-app'))
    check('an extension app renders no guest of its own', ref3 and 'extension' in ref3[0])
    uci, r = render_uci(good)
    check('relay UCI: forwards to lan, opens the reticulum bearer, AP with a deploy-time PSK', not r and "forward='ACCEPT'" in uci and "dest_port='4242'" in uci and '.psk' in uci and "isolate" not in uci)
    guest = dict(good, name='isle-guestnet', uci_profile='guestnet', uci_params_json='{"uci": "guest", "vlan": 20, "cidr": "10.20.0.0/24", "ssid": "isle-guest", "allow_hosts": ["10.10.0.2"]}')
    uci_g, r = render_uci(guest)
    check('guestnet UCI: forward=REJECT, wan only, allow-list rule, client isolation', not r and "forward='REJECT'" in uci_g and "dest='wan'" in uci_g and "dest_ip='10.10.0.2'" in uci_g and "isolate='1'" in uci_g)
    _, r = render_uci(dict(good, uci_params_json='{"uci": "relay", "vlan": 1, "cidr": "10.30.0.1/24"}'))
    check('bad vlan + non-network cidr refused by name', len(r) == 2)
    row = HardwareAppDefinition(**{k: v for k, v in good.items()})
    check('the row constructs with the same fields', row.role == 'relay' and row.requires_tier == 'hardware')
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
