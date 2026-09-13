"""
@module security.custom.security_ssh

SSH as a security vector across Polari devices (his ask 2026-09-13), and the device inventory. Both come
from what a machine reports about itself — `os-security/inventory.sh` posted through
`pol deploy inventory <node> --post <core>` (→ DeviceInventory + SshCapability rows) and the audit's `ssh`
ring — never typed. The isle topology page shows the SshCapability rows so the isle's ssh surface is one
picture: which devices accept ssh, how (keys only or passwords), root or not, and who can reach whom.
"""
import json
import time


def _role_of(inv):
    d = inv.get('docker') or {}
    if inv.get('etc_isle_mesh') and inv.get('guests'):
        return 'isle-core'
    if inv.get('etc_isle_mesh'):
        return 'isle-member'
    if (d.get('swarm') or '').startswith('active/true'):
        return 'swarm-manager'
    if (d.get('swarm') or '').startswith('active'):
        return 'swarm-worker'
    return 'other'


def ssh_row_from_inventory(device, inv, observed_at=''):
    s = inv.get('ssh') or {}
    listens = bool(s.get('listen'))
    keys = s.get('authorized_keys') or []
    types = sorted({k.get('type', '') for k in keys})
    users = sorted({k.get('user', '') for k in keys})
    weak = sum(1 for k in keys if k.get('type') in ('ssh-rsa', 'ssh-dss'))
    pa = s.get('password_auth') or 'unknown'; pr = s.get('permit_root') or 'unknown'; ki = s.get('kbd_interactive') or 'unknown'
    reaches = ', '.join(h.split('|', 1)[-1] for h in (s.get('ssh_config_hosts') or []))
    vectors = []
    if not listens:
        verdict = 'closed'
        vectors.append('no sshd: nobody can ssh in (nor can pol deploy / the core)')
    else:
        if pa == 'yes' or ki == 'yes':
            vectors.append('passwords accepted: a guessable password is the vector')
        if pr not in ('no', 'unknown'):
            vectors.append(f'root may log in ({pr})')
        if weak:
            vectors.append(f'{weak} rsa/dss key(s)')
        if (s.get('fail2ban') or 'inactive') != 'active':
            vectors.append('no brute-force guard')
        if any(a.startswith(('0.0.0.0', '[::]')) for a in (s.get('listen') or [])):
            vectors.append('listens on all interfaces (the firewall ring narrows it)')
        if pa == 'unknown':
            vectors.append('auth methods unreadable without root')
        verdict = 'exposed' if (pa == 'yes' or ki == 'yes' or pr not in ('no', 'unknown')) else ('keys-only' if pa == 'no' else 'unknown')
    return {'name': device, 'device': device, 'role': _role_of(inv), 'listens': listens, 'listen_addresses': ', '.join(s.get('listen') or []),
            'password_auth': pa, 'pubkey_auth': s.get('pubkey_auth') or 'unknown', 'permit_root': pr, 'kbd_interactive': ki,
            'authorized_keys': len(keys), 'key_types': ', '.join(t for t in types if t), 'key_users': ', '.join(u for u in users if u), 'weak_keys': weak,
            'private_keys': ', '.join(s.get('private_keys_present') or []), 'reaches': reaches, 'brute_force_guard': s.get('fail2ban') or 'none',
            'failed_logins_24h': int(s.get('recent_failed_logins_24h') or 0), 'ufw': s.get('ufw') or '', 'verdict': verdict, 'vector': '; '.join(vectors),
            'observed_at': observed_at or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def inventory_row(device, inv, observed_at=''):
    d = inv.get('docker') or {}
    formats = []
    if inv.get('debs'):
        formats.append('deb')
    if d.get('containers'):
        formats.append('docker containers')
    if d.get('stacks'):
        formats.append('swarm stacks')
    if inv.get('checkouts'):
        formats.append('git checkouts')
    if inv.get('guests'):
        formats.append('KVM guests')
    if any('isle' in u or 'polari' in u or 'mesh' in u for u in inv.get('units') or []):
        formats.append('systemd units')
    rings = []
    if inv.get('apparmor_polari'):
        rings.append(f"apparmor files {inv['apparmor_polari']}")
    if inv.get('sudoers_polari'):
        rings.append(f"sudoers {inv['sudoers_polari']}")
    if inv.get('etc_isle_mesh'):
        rings.append('/etc/isle-mesh')
    if inv.get('etc_polari'):
        rings.append('/etc/polari')
    return {'name': device, 'device': device, 'role': _role_of(inv), 'os_release': inv.get('os', ''), 'kernel': inv.get('kernel', ''),
            'docker_version': d.get('version', ''), 'swarm': d.get('swarm', ''), 'kvm': bool(inv.get('kvm')), 'iommu': bool(inv.get('iommu')),
            'containers': ', '.join(c.get('name', '') for c in d.get('containers') or []), 'stacks': ', '.join(d.get('stacks') or []),
            'images': len(d.get('images') or []), 'volumes': int(d.get('volumes') or 0), 'debs': ', '.join(x.split('|')[0] + '=' + x.split('|')[1] for x in inv.get('debs') or [] if '|' in x),
            'apt_sources': ', '.join(inv.get('apt_sources') or []), 'clis': ', '.join(f'{k}={v}' for k, v in (inv.get('clis') or {}).items() if v not in ('', False)),
            'checkouts': ', '.join(inv.get('checkouts') or []), 'units': ', '.join(u for u in inv.get('units') or [] if any(k in u for k in ('isle', 'polari', 'mesh', 'libvirt', 'jenkins'))),
            'timers': ', '.join(inv.get('timers') or []), 'guests': ', '.join(inv.get('guests') or []), 'rings_present': ', '.join(rings) or 'none',
            'formats': ', '.join(formats) or 'nothing installed', 'observed_at': observed_at or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'raw_json': json.dumps(inv)[:30000]}


def ssh_rows(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return [{k: getattr(r, k, '') for k in ('device', 'role', 'listens', 'listen_addresses', 'password_auth', 'permit_root', 'authorized_keys', 'key_types', 'key_users', 'reaches', 'brute_force_guard', 'failed_logins_24h', 'verdict', 'vector', 'observed_at')}
            for r in (tables.get('SshCapability') or {}).values()]


def ssh_summary(rows):
    """The isle's ssh surface as one reading."""
    exposed = [r['device'] for r in rows if r.get('verdict') == 'exposed']
    keys_only = [r['device'] for r in rows if r.get('verdict') == 'keys-only']
    closed = [r['device'] for r in rows if r.get('verdict') == 'closed']
    edges = []
    for r in rows:
        for t in (r.get('reaches') or '').split(', '):
            if t:
                edges.append({'from': r['device'], 'to': t, 'means': 'ssh key (client config)'})
    return {'devices': len(rows), 'exposed': exposed, 'keys_only': keys_only, 'closed': closed, 'reach_edges': edges,
            'reading': f"{len(rows)} device(s): {len(exposed)} accept passwords or root login, {len(keys_only)} keys-only, {len(closed)} closed"}
