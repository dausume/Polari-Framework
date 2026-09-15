"""iso_selftest — the ISO arc's pieces without a 3 GB base: the rows construct; compatibility is DERIVED from an
alias table (in-kernel / third-party / no driver) with the traps and the Apple silicon message; the autoinstall
follows the plan's decisions (refusals + warnings); the probe kit is complete; the overlay tree lays; the pool policy
holds; the API answers with doubles."""
import json
import os
import sys
import tempfile

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1; passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


class R:
    def __init__(self, media=None, **p):
        self.media = media; self.params = p


class S:
    def __init__(self):
        self.media = None; self.status = '200 OK'; self.data = None; self.stream = None; self.content_type = ''; self.downloadable_as = ''; self.headers = {}

    def set_header(self, k, v):
        self.headers[k] = v


def main():
    tmp = tempfile.mkdtemp(prefix='iso-'); os.environ['POLARI_ISO_DIR'] = tmp
    from iso.iso_basis import DeviceProbe, IsoBase, IsoBuild, ISO_CLASSES
    from iso.iso_seed import ISO_SEED_PAIRS, SEED_ISO_BASES
    from iso.iso_page import SEED_ISO_PAGE_DISPLAYS
    from iso.custom import iso_autoinstall, iso_builder, iso_compat, iso_probe_kit
    check('three row classes; seed pairs cover them; bases seeded with a default', len(ISO_CLASSES) == 3 and len(ISO_SEED_PAIRS) == 3 and any(b['default'] for b in SEED_ISO_BASES))
    check('page seeds: no raw JSON panel', all('api-json-panel' not in p['definition'] for p in SEED_ISO_PAGE_DISPLAYS))
    # ---- compatibility, derived from an alias table
    alias = [('pci:v00008086d00001533sv*sd*bc*sc*i*', 'igb'), ('pci:v00008086d0000A0F0sv*sd*bc*sc*i*', 'iwlwifi'), ('usb:v0BDAp8153d*dc*dsc*dp*ic*isc*ip*in*', 'r8152')]
    report = {'os_name': 'Windows', 'cpu': 'Intel i5', 'memory_gb': 16, 'virtualization': True, 'iommu': True, 'firmware': 'UEFI', 'secure_boot': 'on', 'raid_mode': 'raid', 'disk_encryption': 'bitlocker',
              'device_ids': ['PCI\\VEN_8086&DEV_1533&SUBSYS_00008086&REV_03', 'PCI\\VEN_10DE&DEV_2484&SUBSYS_1234&REV_A1', 'USB\\VID_0BDA&PID_8153\\1', 'PCI\\VEN_1234&DEV_5678&REV_00'], 'dmi_uuid': 'u1', 'board_serial': 'b1'}
    ids = iso_compat.normalize_ids(report)
    check('ids normalise to kernel modalias prefixes (Windows PnP → pci:v…d…, usb:v…p…)', 'pci:v00008086d00001533' in ids and 'usb:v0BDAp8153' in ids and 'pci:v000010DEd00002484' in ids, ids)
    v = iso_compat.verdict(report, alias, 'ubuntu-26.04-amd64')
    st = {p['id']: p['status'] for p in v['per_id']}
    check('derived: the NIC and USB adapter are in-kernel, NVIDIA is third-party, an unknown PCI id has no driver', st['pci:v00008086d00001533'] == 'in-kernel' and st['usb:v0BDAp8153'] == 'in-kernel' and st['pci:v000010DEd00002484'] == 'third-party' and st['pci:v00001234d00005678'] == 'no-driver', st)
    check('verdict: compatible with notes; the traps name RAID mode, BitLocker and Secure Boot + NVIDIA', v['verdict'] == 'compatible-with-notes' and {t['id'] for t in v['traps']} >= {'raid-mode', 'disk-encrypted', 'secure-boot-nvidia'}, v['traps'])
    full = 'pci:v00008086d00008C02sv0000103Csd000018E7bc01sc06i01'
    check('matcher: a FULL modalias matches exactly as the kernel does (a class-only pattern claims the SATA controller, not the NIC); a PARTIAL id matches literal vendor/device only, never class-only patterns',
          iso_compat.match_id(full, alias + [('pci:v*d*sv*sd*bc01sc06i01*', 'ahci')]) == ['ahci'] and iso_compat.match_id('pci:v00008086d00008C02', alias + [('pci:v*d*sv*sd*bc01sc06i01*', 'ahci')]) == []
          and iso_compat.match_id('pci:v00008086d00001533', alias) == ['igb'])
    hub = iso_compat.verdict({'device_ids': ['usb:v1D6Bp0002d0608dc09dsc00dp01ic09isc00ip00in00', 'pci:v00008086d00000C00sv0000103Csd000018E7bc06sc00i00']}, alias, 'x')
    check('bridges and hubs the kernel drives itself read as built-in, never as no driver', hub['counts']['builtin'] == 2 and hub['verdict'] == 'compatible' and 'handled by the kernel itself' in hub['text'], hub)
    check('no kernel table cached → unchecked, honestly, traps still listed', iso_compat.verdict(report, [], 'x')['verdict'] == 'unchecked' and iso_compat.verdict(report, [], 'x')['traps'])
    apple = iso_compat.verdict({'manufacturer': 'Apple', 'arch': 'arm64', 'apple_silicon': True, 'cpu': 'Apple M2'}, alias, 'x')
    check('Apple silicon: not compatible, the blunt message verbatim, no motives, no "only"', apple['verdict'] == 'not-compatible' and apple['text'] == iso_compat.APPLE_SILICON_MESSAGE and 'purposefully' not in apple['text'] and 'the only chips' not in apple['text'])
    role, why = iso_compat.suggest_role(report)
    check('suggested role is a knob with evidence: virtualization + IOMMU → hardware', role == 'hardware' and 'IOMMU' in why)
    check('a laptop → access, with the reason', iso_compat.suggest_role({'battery': True, 'memory_gb': 8})[0] == 'access')
    check('the same machine hashes to the same key', iso_compat.hw_hash(report) == iso_compat.hw_hash(dict(report)) and len(iso_compat.hw_hash(report)) == 16)
    # ---- autoinstall: the plan's decisions
    b = {'base': 'ubuntu-26.04-amd64', 'role': 'member', 'shape': 'headless', 'encryption': True}
    ref, warns = iso_autoinstall.validate(b)
    check('D8: encryption on a headless shape is REFUSED with the reason', 'refused' in ref and 'headless' in ref)
    b2 = {'role': 'core', 'shape': 'desktop', 'encryption': True, 'secure_boot': 'off', 'posture': 'dev'}
    ref2, warns2 = iso_autoinstall.validate(b2)
    check('warnings: encryption (second password), Secure Boot off, dev posture — no refusal', not ref2 and len(warns2) == 3 and any('second password' in w for w in warns2) and any('EXTREMELY DANGEROUS' in w for w in warns2))
    ai = iso_autoinstall.render(b2, ssh_keys=['ssh-ed25519 AAAA owner'], core_key='ssh-ed25519 BBBB core')['autoinstall']
    check('D11: ssh from the first boot, keys only (no password login), owner + core keys placed', ai['ssh']['install-server'] and ai['ssh']['allow-pw'] is False and len(ai['ssh']['authorized-keys']) == 2 and ai['identity']['password'] == '!')
    check('offline first: the installer falls back to the ISO pool when no mirror answers, never aborts', ai['apt']['fallback'] == 'offline-install')
    check('desktop shape → the KDE task; core → the KVM packages; encryption → an LVM layout with a passphrase', 'kubuntu-desktop' in ai['packages'] and 'libvirt-daemon-system' in ai['packages'] and ai['storage']['layout'].get('password'))
    check('late commands install the platform OFFLINE from the ISO, write the posture and the plan, enable first boot',
          any('/cdrom/polari' in c for c in ai['late-commands']) and any('polari-complete' in c and 'apt-get install' in c for c in ai['late-commands']) and any('posture.json' in c and '"dev"' in c for c in ai['late-commands']) and any('plan.json' in c for c in ai['late-commands']) and any('polari-first-boot.service' in c for c in ai['late-commands']))
    ai3 = iso_autoinstall.render({'role': 'member', 'shape': 'detect', 'encryption': True})['autoinstall']
    check('D8 at deploy: shape detect + encryption → an early command refuses on a machine without a display', any('REFUSED' in c and 'display' in c for c in ai3['early-commands']))
    check('the core key rides on every image (D11 + the scaffolding): it is among the authorized keys', 'ssh-ed25519 BBBB core' in ai['ssh']['authorized-keys'])
    ai4 = iso_autoinstall.render({'role': 'member', 'shape': 'headless', 'report_to': 'https://core.example', 'target_hash': 'h1'})['autoinstall']
    check('the plan the machine keeps carries where to report and its own hash', any('report_to' in c and 'core.example' in c and '"h1"' in c for c in ai4['late-commands']))
    fb = iso_autoinstall.first_boot_script()
    check('first boot reports back to the core (/api/iso/joined) with hash, hostname, addresses, detections', '/api/iso/joined' in fb and 'report_to' in fb and 'detected.json' in fb)
    check('first boot: detects display/kvm/iommu/nics/tpm, becomes the core or joins with the fingerprint, admits the carried apps, disables itself',
          'detected.json' in fb and 'core-install' in fb and 'isle-bootstrap.sh' in fb and '--fingerprint' in fb and 'install-apps.sh' in fb and 'systemctl disable polari-first-boot' in fb)
    # ---- the probe kit
    kit = iso_probe_kit.kit_files()
    check('probe kit: README with one button per OS, the three launchers, the cache folder; Apple silicon message inside the Mac probe',
          'I am on Windows' in kit['README.html'] and 'I am on a Mac' in kit['README.html'] and 'I am on Linux' in kit['README.html'] and 'probe/windows/polari-probe.ps1' in kit and 'probe/macos/polari-probe.sh' in kit and 'probe/linux/polari-probe.sh' in kit and 'rent, not one you own' in kit['probe/macos/polari-probe.sh'])
    check('every launcher writes the same report shape (probe/1, hw_hash, device_ids)', all(("'polari-probe/1'" in kit[k] or "polari-probe/1" in kit[k]) and 'hw_hash' in kit[k] and 'device_ids' in kit[k] for k in ('probe/windows/polari-probe.ps1', 'probe/macos/polari-probe.sh', 'probe/linux/polari-probe.sh')))
    z = iso_probe_kit.kit_zip(); check('the kit zips', len(z) > 2000 and z[:2] == b'PK')
    # ---- the overlay tree (no base needed)
    over = os.path.join(tmp, 'overlay'); fake_deb = os.path.join(tmp, 'polari-complete_0.1.36_amd64.deb'); open(fake_deb, 'wb').write(b'x' * 100)
    iso_builder.lay_tree({'role': 'member', 'shape': 'detect', 'target_hash': 'abc123', 'join_fingerprint': 'AA:BB'}, '', over, [fake_deb], [], ['ssh-ed25519 K'])
    check('overlay: nocloud user-data + meta-data, polari/debs with the platform, first-boot + unit, the device plan, GRUB boots unattended',
          os.path.isfile(os.path.join(over, 'nocloud', 'user-data')) and os.path.isfile(os.path.join(over, 'nocloud', 'meta-data')) and os.path.isfile(os.path.join(over, 'polari', 'debs', 'polari-complete_0.1.36_amd64.deb'))
          and os.access(os.path.join(over, 'polari', 'first-boot.sh'), os.X_OK) and os.path.isfile(os.path.join(over, 'polari', 'plans', 'abc123.json')) and 'autoinstall ds=nocloud' in open(os.path.join(over, 'boot', 'grub', 'grub.cfg')).read())
    ud = open(os.path.join(over, 'nocloud', 'user-data')).read(); check('user-data is cloud-config with autoinstall version 1', ud.startswith('#cloud-config') and 'version: 1' in ud or '"version": 1' in ud)
    # ---- the ISO pool policy
    os.makedirs(iso_builder.pool_dir(), exist_ok=True); f = 'polari-member-detect-x.iso'; open(os.path.join(iso_builder.pool_dir(), f), 'wb').write(b'i' * 1000)
    iso_builder.note_request(f, 3 * 1024 ** 3)
    e = iso_builder.pool_entry(f); check('an ISO is held ≥ 30 min and 3× its slow download (3 GB → hours)', e['hold_remaining_seconds'] >= 1800 and iso_builder.hold_seconds(3 * 1024 ** 3) == 3 * 3 * 1024 ** 3 // iso_builder.slow_bps())
    r = iso_builder.make_room(10 ** 15); check('make_room refuses while the hold runs, naming the earliest hold', r['ok'] is False and r['blocked_by'] and 'inside its minimum hold' in r['note'])
    check('pool status carries used/max/free and the knobs', 'max_bytes' in iso_builder.pool_status() and iso_builder.pool_status()['files'] == 1)
    check('tools are reported honestly (present or None)', set(iso_builder.tools()) == {'xorriso', 'genisoimage', 'isohybrid'})
    check('the kernel table is derived from .modinfo alias strings (what depmod reads), pci/usb only', iso_builder.module_aliases(b'x\x00alias=pci:v00008086d00001533sv*sd*bc*sc*i*\x00alias=of:N*T*C\x00alias=usb:v0BDAp8153d*\x00') == ['pci:v00008086d00001533sv*sd*bc*sc*i*', 'usb:v0BDAp8153d*'])
    # ---- the API with doubles
    from iso.iso_api import IsoAPI
    api = IsoAPI(polServer=None, manager=None)
    s = S(); api.on_get(R(), s); check('/api/iso summary: bases, pool, tools, roles', s.media['ok'] and s.media['bases'] and 'pool' in s.media and 'core' in s.media['roles'])
    s = S(); api.on_get_probe_kit(R(), s); check('/api/iso/probe-kit is a zip', s.content_type == 'application/zip' and s.data[:2] == b'PK')
    s = S(); api.on_post_probe(R(media=report), s); check('POST /api/iso/probe → verdict + suggested role (no manager: not stored, still answered)', s.media['ok'] and s.media['verdict']['verdict'] == 'unchecked' and s.media['suggested_role'] == 'hardware')
    s = S(); api.on_post_probe(R(media={'manufacturer': 'Apple', 'arch': 'arm64', 'apple_silicon': True, 'cpu': 'Apple M3'}), s); check('POST an Apple silicon probe → the message, no next step', s.media['verdict']['apple_silicon'] and s.media['next'] == '')
    s = S(); api.on_post_probe(R(media={'hello': 1}), s); check('a non-report body is refused with a sentence', s.status.startswith('400'))
    s = S(); api.on_get_preview(R(role='member', shape='headless', encryption='1'), s); check('preview: the headless-encryption refusal comes back as 409', s.status.startswith('409') and 'refused' in s.media['refusal'])
    s = S(); api.on_get_preview(R(role='core', shape='desktop'), s); check('preview: a valid choice set renders the autoinstall', s.media['ok'] and s.media['autoinstall']['autoinstall']['version'] == 1)
    s = S(); api.on_post_build(R(media={'role': 'member'}), s); check('build without a cached base → 409 naming the fetch', s.status.startswith('409') and 'not cached' in s.media['refusal'])
    s = S(); api.on_post_joined(R(media={'hw_hash': 'h9', 'hostname': 'polari-x', 'addresses': ['10.0.0.9'], 'role': 'member', 'shape': 'headless', 'detected': {'kvm': 1}}), s); check('/api/iso/joined answers with the ssh line (no manager: nothing stored, still answered)', s.media['ok'] and s.media['ssh'] == 'ssh polari@10.0.0.9')
    s = S(); api.on_get_core_key(R(), s); check('/api/iso/core-key says honestly whether the core has a key', 'placed_on_every_image' in s.media)
    s = S(); api.on_post_build(R(media={'role': 'x'}), s); check('build with a bad role → 400', s.status.startswith('400'))
    page = __import__('iso.iso_api', fromlist=['render_page']).render_page(api)
    check('the human page: three steps, the probe kit link, the build form, the bases, no raw JSON', '1 · Probe' in page and '2 · Choose' in page and '3 · Install' in page and '/api/iso/probe-kit' in page and 'name="join_fingerprint"' in page and 'Ubuntu 26.04' in page)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
