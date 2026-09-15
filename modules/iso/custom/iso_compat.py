"""
@module iso.custom.iso_compat

Ubuntu compatibility DERIVED, never a hand-typed list (ISO plan §P): every PCI/USB id a probe reports is matched
against the target kernel's `modules.alias` table (the same glob matching the kernel itself uses), and against the
`linux-firmware` file list; a short curated TRAP list covers what ids cannot tell (T2 Macs, RAID mode, BitLocker,
Fast Startup, 32-bit UEFI, Secure Boot + NVIDIA). Apple silicon gets the plain-words message (his ruling: blunt,
inside the line — sourceable facts, labelled opinion, no claims about motives).

@consumers
  - iso.iso_api (the verdict on a posted probe), iso.custom.iso_builder (the plan's notes), iso.iso_selftest
"""
import fnmatch
import hashlib
import json
import re

APPLE_SILICON_MESSAGE = (
    'This is an Apple silicon Mac. Apple publishes no hardware documentation and no drivers for these chips, and dropped '
    'Boot Camp when it introduced them, so no open-source operating system supports them. The one Linux that runs here exists '
    'because volunteers spent years reverse-engineering the hardware, and it is still incomplete. Ubuntu does not run on this '
    'computer, and Polari cannot be installed on it. Nearly every other computer sold today runs Ubuntu out of the box. In our '
    'view, a computer that will not let you run free software is one you rent, not one you own. To run Polari, use one built '
    'on open documentation: any PC, or an Intel Mac.')

#: drivers Ubuntu cannot ship in the kernel: the id family → what the installer adds (third-party, from the restricted pool)
THIRD_PARTY = {
    'pci:v000010DE*': ('nvidia', 'NVIDIA graphics: the open kernel module or the proprietary driver is added by the installer; with Secure Boot on it must be signed (the installer enrols a key)'),
    'pci:v000014E4d000043*': ('bcmwl', 'Broadcom WiFi: the bcmwl driver is added by the installer (common in older Macs and laptops)'),
    'pci:v000014E4d00004*': ('bcmwl', 'Broadcom WiFi: the bcmwl driver is added by the installer'),
}

#: curated traps: (id, applies(report) → text or '') — what ids cannot say
def _traps(report):
    out = []
    model = (report.get('model') or '').lower(); maker = (report.get('manufacturer') or '').lower()
    if 'apple' in maker and report.get('t2', False):
        out.append(('t2-mac', 'An Intel Mac with the T2 chip: Ubuntu installs, but the T2 must be set to allow booting from external media (Startup Security Utility), and the keyboard, audio and WiFi need the t2linux kernel packages the installer adds.'))
    if (report.get('raid_mode') or '').lower() in ('raid', 'rst', 'intel rst', 'raid on'):
        out.append(('raid-mode', 'The storage controller is in RAID (Intel RST) mode: Ubuntu will not see the disk. Switch it to AHCI in the firmware before installing (Windows keeps booting if Safe Mode is used once after the switch).'))
    if (report.get('disk_encryption') or '').lower() in ('bitlocker', 'on', 'enabled', 'filevault'):
        out.append(('disk-encrypted', 'The disk is encrypted by the current OS (BitLocker / FileVault). Decrypt or turn it off first, or the installer cannot resize or replace the partitions.'))
    if report.get('fast_startup'):
        out.append(('fast-startup', 'Windows Fast Startup is on: it leaves the disk in a hibernated state that blocks dual boot. Turn it off in Power Options before installing alongside Windows.'))
    if (report.get('firmware') or '').lower() in ('uefi32', 'ia32 uefi', 'uefi-32'):
        out.append(('uefi32', 'A 32-bit UEFI firmware on a 64-bit CPU (some tablets): the standard ISO does not boot; a 32-bit EFI loader must be added to the stick.'))
    if (report.get('secure_boot') or '').lower() == 'on' and any(fnmatch.fnmatch(i, 'pci:v000010DE*') for i in normalize_ids(report)):
        out.append(('secure-boot-nvidia', 'Secure Boot is on and there is an NVIDIA GPU: the driver module must be signed; the installer enrols a machine-owner key and asks for one reboot with a password prompt.'))
    if (report.get('firmware') or '').lower() in ('bios', 'legacy', 'csm'):
        out.append(('legacy-bios', 'The firmware boots in legacy BIOS mode: Ubuntu installs, but Secure Boot and TPM-bound unlock are not available; switch to UEFI in the firmware if the machine allows it.'))
    return out


def hw_hash(report):
    """The device key: DMI UUID + board serial + first disk serial, hashed — the same machine probed twice is one row."""
    basis = '|'.join(str(report.get(k) or '') for k in ('dmi_uuid', 'board_serial', 'disk_serial', 'cpu', 'memory_gb'))
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def normalize_ids(report):
    """Every device id as a kernel modalias prefix: Windows PnP ids (PCI\\VEN_8086&DEV_1533&SUBSYS_...&REV_..,
    USB\\VID_0BDA&PID_8153), macOS vendor/device pairs, Linux modalias strings — → 'pci:v00008086d00001533' /
    'usb:v0BDAp8153' (the vendor:device part; the kernel table is matched with the rest wildcarded)."""
    out = []
    for raw in report.get('device_ids') or []:
        s = str(raw).strip()
        m = re.match(r'(?i)^PCI\\VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})', s)
        if m:
            out.append(f'pci:v0000{m.group(1).upper()}d0000{m.group(2).upper()}'); continue
        m = re.match(r'(?i)^USB\\VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', s)
        if m:
            out.append(f'usb:v{m.group(1).upper()}p{m.group(2).upper()}'); continue
        m = re.match(r'(?i)^(pci|usb):(.+)$', s)
        if m:
            out.append(s if s.startswith(('pci:', 'usb:')) else s.lower()); continue
        m = re.match(r'(?i)^(pci|usb)\s+([0-9a-f]{4}):([0-9a-f]{4})$', s)   # "pci 8086:1533" (macOS / hwmap shorthand)
        if m:
            kind, v, d = m.group(1).lower(), m.group(2).upper(), m.group(3).upper()
            out.append(f'pci:v0000{v}d0000{d}' if kind == 'pci' else f'usb:v{v}p{d}'); continue
    return sorted(set(out))


def load_alias_table(path):
    """modules.alias → [(pattern, module)]; the kernel's own file ('alias pci:v0000...* e1000e')."""
    rows = []
    try:
        with open(path, encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 3 and parts[0] == 'alias' and parts[1].startswith(('pci:', 'usb:')):
                    rows.append((parts[1], parts[2]))
    except OSError:
        pass
    return rows


_VD_RE = re.compile(r'^(pci|usb):v([0-9A-Fa-f*]+?)(?=d|p)[dp]([0-9A-Fa-f*]+?)(?=[a-z]|$|\*)')


def _vendor_device(modalias):
    """('pci', vendor, device) from a modalias or pattern — '*' when the pattern leaves it open."""
    m = re.match(r'^(pci):v([0-9A-Fa-f]{8}|\*)d([0-9A-Fa-f]{8}|\*)', modalias) or re.match(r'^(usb):v([0-9A-Fa-f]{4}|\*)p([0-9A-Fa-f]{4}|\*)', modalias)
    return (m.group(1), m.group(2).upper(), m.group(3).upper()) if m else None


def is_full_modalias(dev_id):
    return bool(re.match(r'^pci:v[0-9A-Fa-f]{8}d[0-9A-Fa-f]{8}sv', dev_id) or re.match(r'^usb:v[0-9A-Fa-f]{4}p[0-9A-Fa-f]{4}d', dev_id))


def match_id(dev_id, alias_rows):
    """The kernel modules that claim this id. A FULL modalias (what the Linux probe reports) matches a driver's pattern
    exactly as the kernel does (glob). A PARTIAL id (vendor:device only — Windows and macOS reports) matches only
    patterns whose vendor and device are LITERAL and equal; class-only patterns (ahci, snd_hda_intel …) say nothing
    about a device whose class we do not know, so they never claim it."""
    hits = set()
    if is_full_modalias(dev_id):
        for pattern, module in alias_rows:
            if fnmatch.fnmatchcase(dev_id, pattern):
                hits.add(module)
        return sorted(hits)
    ours = _vendor_device(dev_id)
    if not ours:
        return []
    for pattern, module in alias_rows:
        theirs = _vendor_device(pattern)
        if theirs and theirs[0] == ours[0] and theirs[1] == ours[1] and theirs[2] == ours[2] and '*' not in (theirs[1] + theirs[2]):
            hits.add(module)
    return sorted(hits)


def verdict(report, alias_rows=None, base_name='', firmware_files=None):
    """{verdict, text, per_id: [...], counts, traps, apple_silicon} — compatible / compatible-with-notes /
    not-compatible / unchecked (no kernel table cached yet)."""
    if report.get('apple_silicon') or ((report.get('manufacturer') or '').lower().startswith('apple') and (report.get('arch') or '').lower() in ('arm64', 'aarch64')):
        return {'verdict': 'not-compatible', 'text': APPLE_SILICON_MESSAGE, 'per_id': [], 'counts': {}, 'traps': [], 'apple_silicon': True, 'base': base_name}
    ids = normalize_ids(report)
    traps = _traps(report)
    if not alias_rows:
        return {'verdict': 'unchecked', 'text': f'Hardware recorded ({len(ids)} device ids). The kernel table for {base_name or "the base"} is not cached on this instance yet, so the driver check waits; the traps below apply regardless.',
                'per_id': [{'id': i, 'status': 'unchecked', 'modules': []} for i in ids], 'counts': {}, 'traps': [{'id': t, 'text': x} for t, x in traps], 'apple_silicon': False, 'base': base_name}
    per = []; counts = {'in_kernel': 0, 'firmware': 0, 'third_party': 0, 'missing': 0}
    for i in ids:
        mods = match_id(i, alias_rows)
        tp = next((v for k, v in THIRD_PARTY.items() if fnmatch.fnmatchcase(i, k)), None)
        if mods:
            status = 'in-kernel'; counts['in_kernel'] += 1
            if firmware_files and any(m in f for m in mods for f in firmware_files):
                status = 'firmware'; counts['firmware'] += 1; counts['in_kernel'] -= 1
        elif tp:
            status = 'third-party'; counts['third_party'] += 1
        else:
            status = 'no-driver'; counts['missing'] += 1
        per.append({'id': i, 'status': status, 'modules': mods, 'note': tp[1] if tp and status == 'third-party' else ''})
    important_missing = [p for p in per if p['status'] == 'no-driver' and p['id'].startswith('pci:')]
    if important_missing and len(important_missing) >= max(2, len(per) // 3):
        v = 'not-compatible'
        text = f'Ubuntu is unlikely to run well here: {len(important_missing)} PCI device(s) have no driver in this kernel.'
    elif counts['third_party'] or counts['missing'] or traps:
        v = 'compatible-with-notes'
        bits = []
        if counts['third_party']:
            bits.append(f"{counts['third_party']} device(s) need a driver the installer adds")
        if counts['missing']:
            bits.append(f"{counts['missing']} device(s) have no driver (usually unimportant ones; see the list)")
        if traps:
            bits.append(f'{len(traps)} thing(s) to do before installing')
        text = 'Ubuntu will run on this computer. ' + '; '.join(bits) + '.'
    else:
        v = 'compatible'
        text = f'Ubuntu will run on this computer: every device has a driver in the kernel ({counts["in_kernel"]} checked).'
    return {'verdict': v, 'text': text, 'per_id': per, 'counts': counts, 'traps': [{'id': t, 'text': x} for t, x in traps], 'apple_silicon': False, 'base': base_name}


def suggest_role(report):
    """A knob with its evidence (his rule): always-on + memory → core; KVM + IOMMU → hardware; a laptop → access; else member."""
    mem = float(report.get('memory_gb') or 0); virt = bool(report.get('virtualization')); laptop = bool(report.get('battery'))
    iommu = bool(report.get('iommu'))
    if laptop:
        return 'access', 'a laptop (battery present): best as an access-only or plain member — it sleeps and moves'
    if virt and iommu:
        return 'hardware', f'virtualization and IOMMU present, {mem:g} GB memory: can host KVM guests with passthrough'
    if virt and mem >= 16:
        return 'core', f'virtualization present and {mem:g} GB memory on a machine without a battery: a good always-on core'
    return 'member', f'{mem:g} GB memory, no IOMMU: a hosting member for web apps and containers'


def summarize(report):
    """The DeviceProbe row's flat fields from a probe report."""
    disks = report.get('disks') or []
    return {
        'hw_hash': report.get('hw_hash') or hw_hash(report), 'label': report.get('label') or report.get('hostname') or report.get('model') or '',
        'os_name': report.get('os_name') or '', 'os_version': report.get('os_version') or '', 'cpu': report.get('cpu') or '', 'arch': report.get('arch') or '',
        'virtualization': bool(report.get('virtualization')), 'memory_gb': float(report.get('memory_gb') or 0),
        'disks': ', '.join(f"{d.get('name', '?')} {d.get('size_gb', 0):g} GB" for d in disks) if isinstance(disks, list) else str(disks),
        'free_gb': float(report.get('free_gb') or 0), 'firmware': report.get('firmware') or '', 'secure_boot': report.get('secure_boot') or '',
        'tpm': report.get('tpm') or '', 'disk_encryption': report.get('disk_encryption') or '', 'raid_mode': report.get('raid_mode') or '',
        'gpu': report.get('gpu') or '', 'wifi': report.get('wifi') or '', 'nics': int(report.get('nics') or 0),
        'device_ids': ', '.join(normalize_ids(report)), 'apple_silicon': bool(report.get('apple_silicon')),
        'probed_at': report.get('probed_at') or '', 'raw_json': json.dumps(report)[:30000],
    }
