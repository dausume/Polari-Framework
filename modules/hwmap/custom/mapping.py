"""
@module hwmap.custom.mapping

The rules: snapshot → ports, slots, and a PassthroughCandidate per port —
"what can be mapped to a potential KVM", with reasons. Pure.

  usb      → usb-hostdev by vendor:product (a serial adapter → serial-usb-hostdev,
             identity = its by-id path); root hubs and hubs are slots, never mapped;
             the device is not mappable while another guest owns it
  pci      → pci-vfio ONLY when an IOMMU exists, the function sits in an IOMMU
             group of its own (or shares it only with PCI bridges), and it is not
             the host's own disk / display / USB controller that the host needs
  nic      → nic-macvtap for a physical NIC that is not the host's only uplink
             (a wireless NIC is better passed through as its USB device)
  and every verdict says which hardware-app needs it satisfies.
"""
import json

HOST_CRITICAL_PCI = {'0100', '0101', '0106', '0300', '0302', '0380', '0c03', '0601', '0604', '0500', '0580'}
#   SCSI/IDE/SATA, VGA/3D/display, USB controller, ISA/PCI bridge, memory


WIFI_DRIVERS = ('mt76', 'rtl8', 'rtw', 'ath9k', 'ath10k', 'ath11k', 'r8188', 'r8192', 'brcmfmac', 'mt7601', 'rt2800', 'iwl')
SERIAL_DRIVERS = ('cp210x', 'ftdi_sio', 'ch341', 'cdc_acm', 'pl2303', 'usbserial')


def port_role(driver, usb_class=''):
    """The human role of a port from its driver/class — what a need matches on."""
    d = (driver or '').lower()
    if d.startswith(WIFI_DRIVERS):
        return 'wifi'
    if d.startswith(SERIAL_DRIVERS):
        return 'serial'
    if d in ('usb-storage', 'uas'):
        return 'storage'
    if d == 'usbhid' or 'Human Interface' in (usb_class or ''):
        return 'hid'
    if d in ('uvcvideo',):
        return 'camera'
    if d in ('snd-usb-audio',):
        return 'audio'
    return 'other'


def _usb_port(d, dev, owned, slot_lookup):
    pid = '%s:%s@%s' % (d['vendor_id'], d['product_id'], d.get('path', ''))
    role = port_role(d.get('driver'), d.get('class'))
    kind = 'serial' if role == 'serial' else 'usb'
    return {'name': '%s:%s:%s' % (dev, kind, pid), 'device_name': dev, 'kind': kind, 'port_id': pid,
            'vendor_id': d['vendor_id'], 'product_id': d['product_id'], 'description': d.get('description', ''),
            'driver': d.get('driver', ''), 'usb_bus': d.get('bus', ''), 'usb_path': d.get('path', ''), 'usb_class': d.get('class', ''),
            'speed_mbps': d.get('speed_mbps', 0), 'slot': slot_lookup(d.get('path', '')),
            'owner': owned.get(pid) or owned.get('%s:%s' % (d['vendor_id'], d['product_id'])) or 'host', 'role': role}


def build(snapshot, owners=None, needs=None):
    """owners: {port_id: guest name} (from DeviceLink.owner / prior candidates);
    needs: {hardware_app: [{'kind': 'usb'|'serial'|'nic'|'pci', 'vendor_id'?, 'product_id'?, 'driver'?, 'iface'?}]}
    Returns {'snapshot': {...}, 'ports': [...], 'slots': [...], 'candidates': [...]}."""
    owned = owners or {}
    needs = needs or {}
    dev = snapshot.get('device_name', '')
    at = snapshot.get('observed_at', '')
    v = snapshot.get('virt', {})
    slots = []
    for s in snapshot.get('usb_slots', []):
        slots.append({'name': '%s:%s:%s' % (dev, s['kind'], s['slot_id']), 'device_name': dev, 'kind': s['kind'], 'slot_id': s['slot_id'],
                      'driver': s.get('driver', ''), 'ports_total': s.get('ports_total', 0), 'ports_used': 0, 'speed_mbps': s.get('speed_mbps', 0),
                      'parent': s.get('parent', ''), 'observed_at': at})
    def slot_of(path):
        parent = path.rsplit('.', 1)[0] if '.' in path else path.split('-')[0] + '-0'
        for s in slots:
            if s['slot_id'] == parent:
                s['ports_used'] += 1
                return s['name']
        return ''
    ports = []
    for d in snapshot.get('usb', []):
        if d.get('class') in ('root_hub', 'Hub') or d.get('driver') in ('hub',) or d['vendor_id'] == '1d6b':
            continue
        ports.append({**_usb_port(d, dev, owned, slot_of), 'observed_at': at})
    for p in snapshot.get('pci', []):
        if p['class_code'] in ('0604', '0601'):
            slots.append({'name': '%s:pci-bridge:%s' % (dev, p['address']), 'device_name': dev, 'kind': 'pci-bridge', 'slot_id': p['address'],
                          'driver': p.get('driver', ''), 'ports_total': 0, 'ports_used': 0, 'speed_mbps': 0, 'parent': '', 'pci_address': p['address'], 'observed_at': at})
            continue
        ports.append({'name': '%s:pci:%s' % (dev, p['address']), 'device_name': dev, 'kind': 'pci', 'port_id': p['address'], 'role': 'pci-' + p['class_code'],
                      'vendor_id': p['vendor_id'], 'product_id': p['product_id'], 'description': p.get('description', ''), 'driver': p.get('driver', ''),
                      'pci_address': p['address'], 'pci_class': p['class_code'], 'iommu_group': p.get('iommu_group', -1),
                      'owner': owned.get(p['address'], 'host'), 'observed_at': at})
    phys = [n for n in snapshot.get('nics', []) if n.get('physical')]
    for n in phys:
        ports.append({'name': '%s:nic:%s' % (dev, n['iface']), 'device_name': dev, 'kind': 'nic', 'port_id': n['iface'], 'iface': n['iface'],
                      'mac': n.get('mac', ''), 'description': 'wireless' if n.get('wireless') else 'ethernet', 'driver': '', 'role': 'wifi' if n.get('wireless') else 'ethernet',
                      'owner': owned.get(n['iface'], 'host'), 'observed_at': at})
    # by-id paths identify serial adapters across replugs — but identical
    # adapters (same serial '0001') collapse into ONE by-id entry, so the
    # mapping is unambiguous only when by-id entries and serial ports match 1:1
    by_id = [s['by_id_path'] for s in snapshot.get('serial', [])]
    serial_ports_here = [p for p in ports if p['kind'] == 'serial']
    for i, p in enumerate(serial_ports_here):
        p['by_id_path'] = by_id[i] if len(by_id) == len(serial_ports_here) else ''
    # groups shared with host-critical functions
    group_members = {}
    for p in snapshot.get('pci', []):
        group_members.setdefault(p.get('iommu_group', -1), []).append(p)
    candidates = []
    for p in ports:
        reasons, mapping, ok = [], 'not-mappable', False
        if p.get('owner', 'host') not in ('', 'host'):
            reasons.append('owned by guest %r (passthrough is exclusive)' % p['owner'])
        elif p['kind'] in ('usb', 'serial'):
            mapping = 'serial-usb-hostdev' if p['kind'] == 'serial' else 'usb-hostdev'
            ok = True
            reasons.append('usb hostdev by vendor:product %s:%s' % (p['vendor_id'], p['product_id']))
            if p['kind'] == 'serial' and not p.get('by_id_path'):
                reasons.append('more than one identical adapter: identify by usb path %s, not by-id' % p['usb_path'])
        elif p['kind'] == 'pci':
            if not v.get('iommu_enabled'):
                reasons.append('no IOMMU enabled (intel_iommu=on / amd_iommu=on + VT-d/AMD-Vi in firmware) — pci vfio impossible')
            elif p['iommu_group'] < 0:
                reasons.append('function has no IOMMU group')
            else:
                others = [m for m in group_members.get(p['iommu_group'], []) if m['address'] != p['pci_address'] and m['class_code'] not in ('0604', '0601')]
                if others:
                    reasons.append('IOMMU group %d shared with %s — the whole group moves together' % (p['iommu_group'], ', '.join(o['address'] for o in others)))
                elif p['pci_class'] in HOST_CRITICAL_PCI:
                    reasons.append('host-critical class %s (%s) — the host needs it' % (p['pci_class'], p['description']))
                else:
                    mapping, ok = 'pci-vfio', True
                    reasons.append('IOMMU group %d of its own; unbind %s and bind vfio-pci' % (p['iommu_group'], p['driver'] or 'no driver'))
        elif p['kind'] == 'nic':
            uplinks = [n for n in phys if n.get('state') == 'UP' and not n.get('wireless')]
            if p['description'] == 'wireless':
                reasons.append('wireless NIC: pass the USB adapter itself (usb-hostdev) so the guest owns the radio; macvtap cannot carry an AP')
            elif len(uplinks) == 1 and uplinks[0]['iface'] == p['iface']:
                reasons.append('the host\'s only wired uplink — macvtap would cut the host off')
            else:
                mapping, ok = 'nic-macvtap', True
                reasons.append('macvtap bridge mode on %s' % p['iface'])
        satisfies = []
        for app, reqs in needs.items():
            for r in reqs:
                if r.get('kind') == p['kind'] and all(str(p.get(k, '')) == str(val) for k, val in r.items() if k != 'kind'):
                    satisfies.append(app)
        frag = ''
        if ok and mapping in ('usb-hostdev', 'serial-usb-hostdev'):
            frag = "<hostdev mode='subsystem' type='usb' managed='yes'><source><vendor id='0x%s'/><product id='0x%s'/></source></hostdev>" % (p['vendor_id'], p['product_id'])
        elif ok and mapping == 'pci-vfio':
            b, rest = p['pci_address'].split(':')[1], p['pci_address'].split(':')[2]
            frag = "<hostdev mode='subsystem' type='pci' managed='yes'><source><address domain='0x0000' bus='0x%s' slot='0x%s' function='0x%s'/></source></hostdev>" % (b, rest.split('.')[0], rest.split('.')[1])
        elif ok and mapping == 'nic-macvtap':
            frag = "<interface type='direct'><source dev='%s' mode='bridge'/><model type='virtio'/></interface>" % p['iface']
        candidates.append({'name': 'map:' + p['name'], 'device_name': dev, 'port': p['name'], 'mapping': mapping, 'mappable': ok,
                           'reasons_json': json.dumps(reasons), 'satisfies_json': json.dumps(sorted(set(satisfies))), 'fragment': frag, 'observed_at': at})
    snap = {'name': dev, 'device_name': dev, 'cpu_virt': bool(v.get('cpu_virt')), 'kvm_device': bool(v.get('kvm_device')), 'libvirt': bool(v.get('libvirt')),
            'iommu_groups': int(snapshot.get('iommu_groups', 0) or 0),
            'hardware_tier_ready': bool(v.get('cpu_virt') and v.get('kvm_device') and v.get('libvirt')),
            'usb_ports': sum(1 for p in ports if p['kind'] in ('usb', 'serial')), 'pci_ports': sum(1 for p in ports if p['kind'] == 'pci'),
            'nics': sum(1 for p in ports if p['kind'] == 'nic'), 'serial_ports': sum(1 for p in ports if p['kind'] == 'serial'),
            'slots': len(slots), 'observed_at': at, 'scanner_version': snapshot.get('scanner_version', '')}
    return {'snapshot': snap, 'ports': ports, 'slots': slots, 'candidates': candidates}
