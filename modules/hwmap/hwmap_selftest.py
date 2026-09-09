"""hwmap_selftest — the mapping rules on a REAL captured snapshot (this box, custom/fixture_pol_core.json)
and on synthetic snapshots for the branches the box cannot show (IOMMU present, owned ports)."""
import json, os, sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from hwmap.custom.mapping import build, port_role
    from hwmap.hwmap_basis import HWMAP_CLASSES, HardwarePort
    snap = json.load(open(os.path.join(os.path.dirname(__file__), 'custom', 'fixture_pol_core.json')))
    check('four row classes', len(HWMAP_CLASSES) == 4)
    needs = {'voron-printer': [{'kind': 'serial'}], 'isle-relay': [{'kind': 'usb', 'role': 'wifi'}]}
    r = build(snap, {}, needs)
    by = {c['port']: c for c in r['candidates']}
    serial = [c for c in r['candidates'] if ':serial:' in c['port']]
    check('the two CP210x bridges are serial-usb-hostdev candidates satisfying the printer', len(serial) == 2 and all(c['mapping'] == 'serial-usb-hostdev' and 'voron-printer' in c['satisfies_json'] for c in serial))
    wifi = [c for c in r['candidates'] if '0e8d:7610' in c['port']]
    check('the MediaTek WiFi dongle satisfies the relay (role wifi from its driver)', wifi and wifi[0]['mappable'] and 'isle-relay' in wifi[0]['satisfies_json'])
    pci = [c for c in r['candidates'] if ':pci:' in c['port']]
    check('no IOMMU on this box → every PCI function refused by name', pci and all(not c['mappable'] and 'IOMMU' in c['reasons_json'] for c in pci))
    nic = by.get('%s:nic:eno1' % snap['device_name'])
    check('the only wired uplink is refused (would cut the host off)', nic and not nic['mappable'] and 'uplink' in nic['reasons_json'])
    check('root hubs/hubs are slots, not ports', r['snapshot']['slots'] >= 3 and not any(c['port'].endswith('1d6b:0002@001-0') for c in r['candidates']))
    check('duplicate serial adapters are told to identify by usb path', all('usb path' in c['reasons_json'] for c in serial))
    check('hardware tier readiness is measured, not assumed', r['snapshot']['hardware_tier_ready'] is False and r['snapshot']['cpu_virt'] is False)
    # synthetic: IOMMU present, one NIC in its own group → pci-vfio; a GPU shared group → refused; an owned port → refused
    syn = {'device_name': 'big', 'observed_at': 'now', 'virt': {'cpu_virt': True, 'kvm_device': True, 'libvirt': True, 'iommu_enabled': True}, 'iommu_groups': 3,
           'usb': [{'bus': '001', 'dev': '005', 'vendor_id': '0bda', 'product_id': '8812', 'description': 'alfa', 'path': '001-3', 'class': 'Vendor Specific Class', 'driver': 'rtl8812au', 'speed_mbps': 480}],
           'usb_slots': [{'kind': 'usb-controller', 'slot_id': '001-0', 'driver': 'xhci_hcd', 'ports_total': 4, 'speed_mbps': 480, 'parent': ''}],
           'pci': [{'address': '0000:03:00.0', 'class_name': 'Ethernet controller', 'class_code': '0200', 'description': 'I210', 'vendor_id': '8086', 'product_id': '1533', 'driver': 'igb', 'iommu_group': 7},
                   {'address': '0000:01:00.0', 'class_name': 'VGA', 'class_code': '0300', 'description': 'GPU', 'vendor_id': '10de', 'product_id': '1c82', 'driver': 'nouveau', 'iommu_group': 1},
                   {'address': '0000:01:00.1', 'class_name': 'Audio', 'class_code': '0403', 'description': 'GPU audio', 'vendor_id': '10de', 'product_id': '0fb9', 'driver': 'snd_hda_intel', 'iommu_group': 1}],
           'nics': [{'iface': 'enp2s0', 'state': 'UP', 'mac': 'aa', 'physical': True, 'wireless': False}, {'iface': 'enp3s0', 'state': 'DOWN', 'mac': 'bb', 'physical': True, 'wireless': False}], 'serial': []}
    r2 = build(syn, {'0bda:8812': 'isle-relay'}, {'isle-relay': [{'kind': 'usb', 'role': 'wifi'}]})
    c = {x['port']: x for x in r2['candidates']}
    check('a NIC in its own IOMMU group is pci-vfio with the bind instruction', c['big:pci:0000:03:00.0']['mapping'] == 'pci-vfio' and 'vfio-pci' in c['big:pci:0000:03:00.0']['reasons_json'])
    check('a GPU sharing its group with its audio function is refused (group moves together)', not c['big:pci:0000:01:00.0']['mappable'] and 'shared' in c['big:pci:0000:01:00.0']['reasons_json'])
    check('a second wired NIC is macvtap-mappable while the uplink is not', c['big:nic:enp3s0']['mappable'] and not c['big:nic:enp2s0']['mappable'])
    check('a port owned by a guest is refused (exclusive)', not c['big:usb:0bda:8812@001-3']['mappable'] and 'owned by guest' in c['big:usb:0bda:8812@001-3']['reasons_json'])
    check('readiness true on the synthetic hardware-tier box', r2['snapshot']['hardware_tier_ready'] is True)
    check('port roles from drivers', port_role('mt76x0u') == 'wifi' and port_role('cp210x') == 'serial' and port_role('usbhid') == 'hid')
    row = HardwarePort(**r['ports'][0])
    check('port rows construct from the built dicts', row.name.startswith(snap['device_name']))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
