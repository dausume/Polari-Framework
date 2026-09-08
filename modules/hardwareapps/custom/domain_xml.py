"""
@module hardwareapps.custom.domain_xml

Render a libvirt domain XML for a HardwareAppDefinition — the isle's own
router template (Isle-Mesh/openwrt-router/templates/libvirt/base-vm.xml)
generalised: q35, host-passthrough CPU, eight spare PCIe root ports, one
virtio disk, one virtio NIC per bridge in NIC order, then one `hostdev`
(USB, by vendor:product) or one macvtap `interface type='direct'` per
passthrough entry, pty console, VNC on loopback. Pure: strings in,
string out; the isle stages the disk under /var/lib/libvirt/images/ (the
AppArmor rule) and `virsh define`s the result.
"""
import json
import os
import re

_PCIE_PORTS = 8


def _esc(v):
    return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;')


def _valid_name(name):
    return bool(re.match(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$', name or ''))


def render_domain(defn, passthrough=None, image_dir='/var/lib/libvirt/images'):
    """defn: a HardwareAppDefinition row or dict. passthrough: list of dicts
    {kind:'usb', vendor_id, product_id, description} or {kind:'nic', interface}
    (resolved by the caller from DeviceLink rows / host NIC names).
    Returns (xml, refusals): refusals is a list of named reasons — an
    empty list means the XML is complete."""
    g = (lambda k, d=None: defn.get(k, d)) if isinstance(defn, dict) else (lambda k, d=None: getattr(defn, k, d))
    name = g('name', '')
    refusals = []
    if not _valid_name(name):
        refusals.append('name %r is not a valid libvirt domain name' % name)
    if (g('kind') or 'hardware-app') != 'hardware-app':
        refusals.append('only kind hardware-app renders a domain (an extension app has no guest of its own)')
    try:
        bridges = json.loads(g('bridges_json', '[]') or '[]')
    except ValueError:
        bridges, _ = [], refusals.append('bridges_json is not JSON')
    if not bridges:
        refusals.append('no bridges — a guest needs at least one NIC')
    mem, vcpus = int(g('memory_mb', 0) or 0), int(g('vcpus', 0) or 0)
    if mem < 128 or vcpus < 1:
        refusals.append('memory_mb >= 128 and vcpus >= 1 required (got %s / %s)' % (mem, vcpus))
    image = g('vm_image_ref', '') or ''
    if not image.endswith('.qcow2'):
        refusals.append('vm_image_ref must be a .qcow2 (got %r)' % image)
    if not g('image_sha256_raw', ''):
        refusals.append('image_sha256_raw is empty — pin the image by RAW sha like the router (router-image.manifest)')
    if refusals:
        return '', refusals
    disk = os.path.join(image_dir, '%s.qcow2' % name)
    out = ["<domain type='kvm'>", "  <name>%s</name>" % _esc(name),
           "  <metadata><description>%s</description></metadata>" % _esc('Polari hardware app %s (role %s, guest %s) — rendered from HardwareAppDefinition' % (name, g('role', 'custom'), g('guest_kind', 'openwrt'))),
           "  <memory unit='MiB'>%d</memory>" % mem, "  <currentMemory unit='MiB'>%d</currentMemory>" % mem,
           "  <vcpu placement='static'>%d</vcpu>" % vcpus,
           "  <os><type arch='x86_64' machine='pc-q35-6.2'>hvm</type><boot dev='hd'/></os>",
           "  <features><acpi/><apic/></features>", "  <cpu mode='host-passthrough' check='none'/>",
           "  <clock offset='utc'><timer name='rtc' tickpolicy='catchup'/><timer name='pit' tickpolicy='delay'/><timer name='hpet' present='no'/></clock>",
           "  <on_poweroff>destroy</on_poweroff><on_reboot>restart</on_reboot><on_crash>restart</on_crash>",
           "  <devices>", "    <emulator>/usr/bin/qemu-system-x86_64</emulator>",
           "    <disk type='file' device='disk'><driver name='qemu' type='qcow2'/><source file='%s'/><target dev='vda' bus='virtio'/></disk>" % _esc(disk),
           "    <controller type='pci' index='0' model='pcie-root'/>"]
    for i in range(1, _PCIE_PORTS + 1):
        out.append("    <controller type='pci' index='%d' model='pcie-root-port'><model name='pcie-root-port'/><target chassis='%d' port='0x%x'/><address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x%x'%s/></controller>"
                   % (i, i, 0x10 + i - 1, i - 1, " multifunction='on'" if i == 1 else ''))
    for n, br in enumerate(bridges):
        out.append("    <!-- eth%d: bridge %s -->" % (n, _esc(br)))
        out.append("    <interface type='bridge'><source bridge='%s'/><model type='virtio'/></interface>" % _esc(br))
    for p in passthrough or []:
        if p.get('kind') == 'usb':
            out.append("    <!-- USB passthrough: %s (exclusive owner: %s) -->" % (_esc(p.get('description', '')), _esc(name)))
            out.append("    <hostdev mode='subsystem' type='usb' managed='yes'><source><vendor id='0x%s'/><product id='0x%s'/></source></hostdev>"
                       % (_esc(p['vendor_id']).replace('0x', ''), _esc(p['product_id']).replace('0x', '')))
        elif p.get('kind') == 'nic':
            out.append("    <!-- NIC passthrough (macvtap): %s -->" % _esc(p['interface']))
            out.append("    <interface type='direct'><source dev='%s' mode='bridge'/><model type='virtio'/></interface>" % _esc(p['interface']))
        else:
            refusals.append('passthrough entry of unknown kind %r' % p.get('kind'))
    out += ["    <serial type='pty'><target type='isa-serial' port='0'><model name='isa-serial'/></target></serial>",
            "    <console type='pty'><target type='serial' port='0'/></console>",
            "    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'><listen type='address' address='127.0.0.1'/></graphics>",
            "    <video><model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/></video>",
            "  </devices>", "</domain>", ""]
    return ('\n'.join(out) if not refusals else ''), refusals
