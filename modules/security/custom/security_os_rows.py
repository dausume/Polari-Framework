"""
@module security.custom.security_os_rows

The OS domain's rows, DERIVED: MacProfile from the os-security render manifests (per scenario) and the
latest audit run; DacPolicy from the stanza / fixed piece (declared) beside the container facts an audit
run reports (live); PermissionGroup from the sudoers drop-ins in polari-cli/shells/groups. Nothing typed.
"""
import glob
import hashlib
import json
import os
import re

from security.custom.security_facts import SUITE, load_scenario, scenario_names

OUT = os.path.join(SUITE, 'os-security', 'out')
GROUPS = os.path.join(SUITE, 'polari-cli', 'shells', 'groups')
MODULES = os.path.join(SUITE, 'polari-rf-node', 'polari-framework', 'modules')


def _stanza_hash(stanza):
    return hashlib.sha256(json.dumps(stanza or {}, sort_keys=True).encode()).hexdigest()[:12]


def _manifests():
    out = {}
    for p in glob.glob(os.path.join(MODULES, '*', 'polari-app.json')):
        try:
            m = json.load(open(p, encoding='utf-8'))
            out[m['id']] = m
        except Exception:
            pass
    return out


def render_manifest(scenario):
    p = os.path.join(OUT, scenario, 'manifest.json')
    return json.load(open(p, encoding='utf-8')) if os.path.isfile(p) else None


def mac_profile_rows(applied=None):
    """One row per rendered profile per scenario (+ the node profile), with the mode the latest audit says."""
    applied = applied or {}
    rows = []
    manifests = _manifests()
    for scn in scenario_names():
        rm = render_manifest(scn)
        sc = load_scenario(scn)
        if not rm or not sc:
            continue
        loaded_mode = (applied.get(scn) or {}).get('polari-apparmor', '')
        entries = [dict(x, group='apps') for x in rm.get('apps', [])] + [dict(x, group='fixed') for x in rm.get('fixed', [])]
        if rm.get('node'):
            entries.append(dict(rm['node'], group='node'))
        for e in entries:
            app = e['name']
            stanza = (manifests.get(app) or {}).get('security') or next((f for f in sc['fixed'] if f['name'] == app), {})
            rows.append({'name': f"{scn}:{e['profile']}", 'app': app, 'scenario': scn, 'kind': 'apparmor', 'profile': e['profile'],
                         'mode': loaded_mode or 'rendered', 'loaded': bool(loaded_mode), 'attach': rm.get('mac_attach', 'security_opt') if e['group'] != 'node' else 'node-wide',
                         'denials_24h': 0, 'stanza_hash': _stanza_hash(stanza), 'artifact': os.path.join('os-security/out', scn, 'apparmor', e['profile']),
                         'state': loaded_mode or 'rendered'})
        for kind in rm.get('kinds', []):
            rows.append({'name': f'{scn}:seccomp:{kind}', 'app': f'kind {kind}', 'scenario': scn, 'kind': 'seccomp', 'profile': f'{kind}.json',
                         'mode': (applied.get(scn) or {}).get('polari-seccomp', 'rendered'), 'loaded': False, 'attach': 'security_opt' if rm.get('mac_attach') == 'security_opt' else 'daemon seccomp-profile',
                         'denials_24h': 0, 'stanza_hash': '', 'artifact': os.path.join('os-security/out', scn, 'seccomp', kind + '.json'), 'state': 'rendered (inert until attached)'})
        if sc.get('guests'):
            rows.append({'name': f'{scn}:svirt', 'app': 'every guest', 'scenario': scn, 'kind': 'svirt', 'profile': 'libvirt-<uuid>', 'mode': 'enforce', 'loaded': True,
                         'attach': 'libvirt per VM', 'denials_24h': 0, 'stanza_hash': '', 'artifact': '', 'state': 'stock (libvirt default, enforcing)'})
    return rows


def dac_policy_rows(containers_by_scenario=None):
    """Declared DAC per app per scenario; live columns filled from an audit run's container facts when present."""
    containers_by_scenario = containers_by_scenario or {}
    rows = []
    manifests = _manifests()
    for scn in scenario_names():
        sc = load_scenario(scn)
        if not sc:
            continue
        pieces = list(sc['fixed'])
        if sc['apps_run'] == 'containers':
            pieces += [{'name': mid, **(m.get('security') or {})} for mid, m in manifests.items() if m.get('security')]
        live = {c.get('name'): c for c in containers_by_scenario.get(scn, [])}
        for p in pieces:
            caps = ','.join(p.get('capabilities') or [])
            lv = live.get(p['name']) or {}
            drift = ''
            if lv:
                if lv.get('read_only') is False:
                    drift += 'writable rootfs; '
                if lv.get('user') in ('', None, 'root', '0'):
                    drift += 'runs as root; '
                if lv.get('caps') and set(lv['caps']) - set(p.get('capabilities') or []):
                    drift += 'extra caps; '
            rows.append({'name': f"{scn}:{p['name']}", 'app': p['name'], 'scenario': scn, 'kind': p.get('profile', 'web-app'), 'read_only': True,
                         'caps_add': caps, 'writable': ','.join(p.get('writable') or []), 'pids_limit': 512, 'tmpfs': '/tmp,/run', 'no_new_privileges': True,
                         'userns': (sc.get('docker') or {}).get('userns_remap', '') if isinstance(sc.get('docker'), dict) else '',
                         'live_read_only': '' if not lv else str(lv.get('read_only')), 'live_caps': ','.join(lv.get('caps') or []) if lv else '',
                         'live_user': lv.get('user', '') if lv else '', 'drift': drift.strip('; ') or ('not reported' if not lv else 'none')})
    return rows


def permission_group_rows(installed=None):
    """The sudoers groups from their drop-ins (verbs = the Cmnd_Alias lines), plus the groups docker/libvirt rely on."""
    installed = installed or {}
    rows = []
    for f in sorted(glob.glob(os.path.join(GROUPS, '*.sudoers'))):
        group = os.path.basename(f)[:-8]
        txt = open(f, encoding='utf-8').read()
        aliases = re.findall(r'Cmnd_Alias\s+(\w+)\s*=\s*(.+)', txt)
        verbs = '; '.join(f"{a}: {', '.join(x.strip() for x in cmds.split(',')[:6])}{' …' if cmds.count(',') > 5 else ''}" for a, cmds in aliases)
        purpose = {'polari-remote': 'remote setup over ssh: docker, the isle CLI, the platform debs, virtualization, reading isle state',
                   'polari-app': "the store's doors: isle core-install/onboard/app/url/status/uninstall and the app debs"}.get(group, '')
        rows.append({'name': group, 'purpose': purpose, 'verbs': verbs[:900], 'sudoers_file': f'/etc/sudoers.d/{group}', 'granted_by': 'pol deploy grant <node> --group / install-groups.sh',
                     'members': installed.get(group, {}).get('members', ''), 'apps_needing': '', 'installed': installed.get(group, {}).get('installed', 'unknown')})
    for g, purpose, apps in (('docker', 'root-equivalent on the host (the socket): the operator only, never a service user', ''),
                             ('libvirt', 'manage guests: the owner and the hardware tier', 'hardware apps'),
                             ('kvm', '/dev/kvm: the hardware tier', 'hardware apps'),
                             ('dialout', 'serial ports (/dev/ttyUSB*, ttyACM*): printers, boards', 'voron, printcam, hardware extensions'),
                             ('video', 'cameras (/dev/video*)', 'printcam'), ('plugdev', 'USB devices (/dev/bus/usb)', 'hardware extensions'),
                             ('gpio', 'GPIO chips', 'hardware extensions'), ('i2c', 'I2C buses', 'hardware extensions'), ('render', 'GPU compute', 'hardware extensions'), ('input', 'input devices', '')):
        rows.append({'name': g, 'purpose': purpose, 'verbs': '', 'sudoers_file': '', 'granted_by': 'the hardware map / a hardware trial (sec-i-5)',
                     'members': installed.get(g, {}).get('members', ''), 'apps_needing': apps, 'installed': installed.get(g, {}).get('installed', 'unknown')})
    return rows
