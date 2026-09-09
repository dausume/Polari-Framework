"""
@module hwmap.custom.scanner

The on-device scan → one JSON snapshot. Runs on the DEVICE (host, not a
container): lsusb / lsusb -t / lspci -nnk / /sys/kernel/iommu_groups /
ip -br link / /dev/serial/by-id / /proc/cpuinfo / /dev/kvm / virsh. Pure
collection, no judgement (the mapping rules run in Polari). Stdlib only.

    python3 -m hwmap.custom.scanner            # JSON on stdout
    pol hwmap scan [--push <api>]              # the CLI wrapper
"""
import json
import os
import re
import subprocess
import time

SCANNER_VERSION = '1'


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return ''


def usb_devices():
    out = []
    for line in _run(['lsusb']).splitlines():
        m = re.match(r'Bus (\d+) Device (\d+): ID ([0-9a-f]{4}):([0-9a-f]{4}) ?(.*)', line)
        if m:
            out.append({'bus': m.group(1), 'dev': m.group(2), 'vendor_id': m.group(3), 'product_id': m.group(4), 'description': m.group(5).strip()})
    return out


def usb_tree():
    """Controllers/hubs (slots) + per-device path/class/driver/speed from lsusb -t."""
    slots, paths = [], {}
    bus = ''
    stack = []
    for line in _run(['lsusb', '-t']).splitlines():
        m = re.match(r'^(\s*)(?:/:\s+)?(?:\|__ )?(Bus (\d+)\.)?Port (\d+): Dev (\d+), (?:If \d+, )?Class=([^,]+), Driver=([^,]+?)(?:/(\d+)p)?, (\d+)M', line)
        if not m:
            continue
        indent, _, b, port, dev, cls, driver, nports, speed = m.groups()
        depth = len(indent) // 4
        if b:
            bus = b.zfill(3); depth = 0
        stack = stack[:depth] + [port]
        path = bus + '-' + '.'.join(stack[1:]) if len(stack) > 1 else bus + '-0'
        entry = {'bus': bus, 'dev': dev.zfill(3), 'path': path, 'class': cls, 'driver': driver, 'speed_mbps': int(speed)}
        if nports:
            slots.append({'kind': 'usb-controller' if cls == 'root_hub' else 'usb-hub', 'slot_id': path, 'driver': driver,
                          'ports_total': int(nports), 'speed_mbps': int(speed), 'parent': (bus + '-' + '.'.join(stack[1:-1])) if len(stack) > 2 else (bus + '-0' if len(stack) == 2 else '')})
        paths[(bus, dev.zfill(3))] = entry
    return slots, paths


def pci_devices():
    out = []
    cur = None
    for line in _run(['lspci', '-nnk']).splitlines():
        m = re.match(r'^([0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]) (.+?) \[([0-9a-f]{4})\]: (.+?) \[([0-9a-f]{4}):([0-9a-f]{4})\]', line)
        if m:
            cur = {'address': '0000:' + m.group(1), 'class_name': m.group(2), 'class_code': m.group(3), 'description': m.group(4),
                   'vendor_id': m.group(5), 'product_id': m.group(6), 'driver': '', 'iommu_group': -1}
            out.append(cur)
        elif cur and 'Kernel driver in use:' in line:
            cur['driver'] = line.split(':', 1)[1].strip()
    groups = {}
    base = '/sys/kernel/iommu_groups'
    if os.path.isdir(base):
        for g in os.listdir(base):
            for dev in os.listdir(os.path.join(base, g, 'devices')) if os.path.isdir(os.path.join(base, g, 'devices')) else []:
                groups[dev] = int(g)
    for d in out:
        d['iommu_group'] = groups.get(d['address'], -1)
    return out, len(set(groups.values()))


def nics():
    out = []
    for line in _run(['ip', '-br', 'link']).splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] != 'lo':
            name = parts[0].split('@')[0]
            physical = os.path.exists('/sys/class/net/%s/device' % name)
            out.append({'iface': name, 'state': parts[1], 'mac': parts[2], 'physical': physical,
                        'wireless': os.path.isdir('/sys/class/net/%s/wireless' % name)})
    return out


def serial_ports():
    base = '/dev/serial/by-id'
    out = []
    if os.path.isdir(base):
        for n in sorted(os.listdir(base)):
            try:
                target = os.path.realpath(os.path.join(base, n))
            except OSError:
                target = ''
            out.append({'by_id_path': os.path.join(base, n), 'device': target})
    return out


def virt_facts():
    cpu = ''
    try:
        cpu = open('/proc/cpuinfo').read()
    except OSError:
        pass
    return {'cpu_virt': bool(re.search(r'\b(vmx|svm)\b', cpu)), 'kvm_device': os.path.exists('/dev/kvm'),
            'libvirt': bool(_run(['sh', '-c', 'command -v virsh'])), 'iommu_enabled': os.path.isdir('/sys/kernel/iommu_groups') and bool(os.listdir('/sys/kernel/iommu_groups'))}


def scan(device_name=None):
    slots, paths = usb_tree()
    usb = []
    for d in usb_devices():
        t = paths.get((d['bus'], d['dev']), {})
        usb.append({**d, 'path': t.get('path', d['bus'] + '-?'), 'class': t.get('class', ''), 'driver': t.get('driver', ''), 'speed_mbps': t.get('speed_mbps', 0)})
    pci, ngroups = pci_devices()
    return {'scanner_version': SCANNER_VERSION, 'device_name': device_name or os.uname().nodename,
            'observed_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'virt': virt_facts(), 'iommu_groups': ngroups,
            'usb': usb, 'usb_slots': slots, 'pci': pci, 'nics': nics(), 'serial': serial_ports()}


if __name__ == '__main__':
    print(json.dumps(scan(), indent=1))
