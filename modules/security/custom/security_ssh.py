"""
@module security.custom.security_ssh

SSH as a security vector across Polari devices (his ask 2026-09-13), and the device inventory. Both come
from what a machine reports about itself — `os-security/inventory.sh` posted through
`pol deploy inventory <node> --post <core>` (→ DeviceInventory + SshCapability rows) and the audit's `ssh`
ring — never typed. The isle topology page shows the SshCapability rows so the isle's ssh surface is one
picture: which devices accept ssh, how (keys only or passwords), root or not, and who can reach whom.
"""
import json
import re
import time

_SUDO_RE = re.compile(r'^(%?)([\w.@+-]+)\s+\S+\s*=\s*(\([^)]*\))?\s*(.*)$')
LEVEL_ORDER = {'root': 4, 'blanket-sudo': 3, 'scoped-sudo': 2, 'shell': 1, 'none': 0}


def sudo_grants(lines):
    """sudoers lines → {principal: {'kind': user|group, 'commands': str, 'blanket': bool}} (tags stripped, never a secret)."""
    grants = {}
    for line in lines or []:
        m = _SUDO_RE.match(line.strip())
        if not m:
            continue
        pct, who, _runas, cmds = m.groups()
        cmds = re.sub(r'\b(NOPASSWD|PASSWD|NOEXEC|SETENV|LOG_INPUT|LOG_OUTPUT):\s*', '', cmds or '').strip()
        g = grants.setdefault(who, {'kind': 'group' if pct else 'user', 'commands': '', 'blanket': False})
        g['commands'] = (g['commands'] + '; ' + cmds).strip('; ') if g['commands'] else cmds
        g['blanket'] = g['blanket'] or cmds == 'ALL'
    return grants


def posture_state(inv, now=None):
    """(posture, until, relaxations, expired) from /etc/polari/posture.json as the device reported it."""
    p = (inv.get('ssh') or {}).get('posture') or inv.get('posture') or {}
    if not isinstance(p, dict) or p.get('posture') != 'dev':
        return 'secure', '', [], False
    until = p.get('until') or ''
    expired = False
    if until:
        try:
            expired = time.strptime(until[:19], '%Y-%m-%dT%H:%M:%S') < time.gmtime(now)
        except ValueError:
            expired = False
    return 'dev', until, list(p.get('relaxations') or []), expired


def permission_levels(device, inv, observed_at=''):
    """One row per principal: may it log in over ssh, and at what level once in."""
    s = inv.get('ssh') or {}
    allow = (s.get('allow_groups') or '').split()
    groups = {}
    for line in s.get('groups') or []:
        name, _, members = line.partition('|')
        groups[name] = [m for m in members.split(',') if m]
    grants = sudo_grants(s.get('sudoers') or [])
    keyed = {}
    for k in s.get('authorized_keys') or []:
        keyed[k.get('user', '')] = keyed.get(k.get('user', ''), 0) + 1
    posture, until, _rlx, expired = posture_state(inv)
    active_dev = posture == 'dev' and not expired
    ts = observed_at or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rows = {}

    def user_level(u):
        if u == 'root':
            return 'root', 'root account'
        g = grants.get(u)
        if g and g['blanket']:
            return 'blanket-sudo', 'sudoers: ALL'
        if g:
            return 'scoped-sudo', 'sudoers: ' + g['commands'][:80]
        for gname, members in groups.items():
            gg = grants.get(gname)
            if u in members and gg:
                return ('blanket-sudo' if gg['blanket'] else 'scoped-sudo'), f'member of {gname}'
        return 'shell', 'a shell, no sudo'

    def allowed(u):
        if u == 'root':
            return s.get('permit_root', 'unknown') not in ('no', 'unknown', '')
        if allow:
            return any(u in groups.get(g, []) for g in allow)
        return u in keyed
    for u in sorted(set(keyed) | {m for g in groups.values() for m in g} | {w for w, g in grants.items() if g['kind'] == 'user'}):
        if not u:
            continue
        lvl, via = user_level(u)
        rows[f'{device}:{u}'] = {'name': f'{device}:{u}', 'device': device, 'principal': u, 'kind': 'user', 'allowed_over_ssh': bool(allowed(u)),
                                 'level': lvl, 'via': via + (f'; {keyed[u]} key(s)' if u in keyed else '; no authorized key'),
                                 'commands': (grants.get(u) or {}).get('commands', ''), 'members': '',
                                 'posture': 'dev' if active_dev and lvl in ('root', 'blanket-sudo') else 'secure', 'expires': until if active_dev else '', 'observed_at': ts}
    for gname, members in sorted(groups.items()):
        g = grants.get(gname)
        lvl = 'blanket-sudo' if (g and g['blanket']) else ('scoped-sudo' if g else 'shell')
        rows[f'{device}:%{gname}'] = {'name': f'{device}:%{gname}', 'device': device, 'principal': '%' + gname, 'kind': 'group',
                                      'allowed_over_ssh': (gname in allow) if allow else bool(members), 'level': lvl,
                                      'via': ('AllowGroups' if gname in allow else 'not in AllowGroups' if allow else 'no AllowGroups (any keyed member)'),
                                      'commands': (g or {}).get('commands', ''), 'members': ', '.join(members),
                                      'posture': 'dev' if active_dev and lvl == 'blanket-sudo' else 'secure', 'expires': until if active_dev else '', 'observed_at': ts}
    return list(rows.values())


def ssh_assurance(inv, levels=None):
    """secure | dev (until) | unsecured | closed | unknown, with the reasons. Secure = keys only, no root, AllowGroups
    names who may log in, nobody beyond root/admin/sudo holds a blanket ALL. Dev = a declared, unexpired dev posture
    covering exactly what breaks 'secure' — and even dev never accepts passwords (the invariant). Anything else is
    unsecured, and says why."""
    s = inv.get('ssh') or {}
    if not s.get('listen'):
        return 'closed', 'no sshd listens', 'secure', ''
    pa = s.get('password_auth') or 'unknown'; pr = s.get('permit_root') or 'unknown'; ki = s.get('kbd_interactive') or 'unknown'
    if pa == 'unknown':
        return 'unknown', 'auth methods unreadable without root', 'secure', ''
    posture, until, relaxations, expired = posture_state(inv)
    invariant_breaks = []
    if pa == 'yes' or ki == 'yes':
        invariant_breaks.append('passwords accepted (no posture allows that)')
    if pr == 'yes':
        invariant_breaks.append('root with a password (no posture allows that)')
    breaks = []
    if pr not in ('no', 'yes'):
        breaks.append(f'root may log in with a key ({pr})')
    if not (s.get('allow_groups') or '').strip():
        breaks.append('no AllowGroups: any account with a key may log in')
    blanket = [w for w, g in sudo_grants(s.get('sudoers') or []).items() if g['blanket'] and w not in ('root', 'admin', 'sudo')]
    if blanket:
        breaks.append('blanket sudo for ' + ', '.join(blanket))
    if invariant_breaks:
        return 'unsecured', '; '.join(invariant_breaks + breaks), posture, until
    if not breaks:
        return 'secure', 'keys only, no root, AllowGroups set, sudo scoped', posture, until
    if posture == 'dev' and not expired:
        return 'dev', f"dev posture until {until or 'unset'}: " + '; '.join(breaks), posture, until
    if posture == 'dev' and expired:
        return 'unsecured', f'dev posture EXPIRED at {until}: ' + '; '.join(breaks), posture, until
    return 'unsecured', '; '.join(breaks) + ' — declare a dev posture or fix', posture, until


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
    assurance, reasons, posture, until = ssh_assurance(inv)
    lv = permission_levels(device, inv, observed_at)
    levels = ', '.join(f"{r['principal']}={r['level']}" for r in lv if r['allowed_over_ssh'])
    return {'name': device, 'device': device, 'role': _role_of(inv), 'listens': listens, 'listen_addresses': ', '.join(s.get('listen') or []),
            'allow_groups': s.get('allow_groups') or '', 'posture': posture, 'posture_until': until, 'assurance': assurance, 'assurance_reasons': reasons, 'levels': levels,
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
    return [{k: getattr(r, k, '') for k in ('device', 'role', 'listens', 'listen_addresses', 'password_auth', 'permit_root', 'authorized_keys', 'key_types', 'key_users', 'reaches', 'brute_force_guard', 'failed_logins_24h', 'verdict', 'vector', 'assurance', 'assurance_reasons', 'posture', 'posture_until', 'allow_groups', 'levels', 'observed_at')}
            for r in (tables.get('SshCapability') or {}).values()]


def level_rows(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return [{k: getattr(r, k, '') for k in ('device', 'principal', 'kind', 'allowed_over_ssh', 'level', 'via', 'commands', 'members', 'posture', 'expires', 'observed_at')}
            for r in (tables.get('SshPermissionLevel') or {}).values()]


def assurance_summary(rows):
    by = {}
    for r in rows:
        by.setdefault(r.get('assurance') or 'unknown', []).append(r['device'] + (f" (until {r['posture_until']})" if r.get('assurance') == 'dev' and r.get('posture_until') else ''))
    n = len(rows)
    return {'secure': by.get('secure', []) + by.get('closed', []), 'dev': by.get('dev', []), 'unsecured': by.get('unsecured', []), 'unknown': by.get('unknown', []),
            'assured': not by.get('unsecured') and not by.get('unknown') and n > 0,
            'reading': (f"{n} device(s): {len(by.get('secure', []) + by.get('closed', []))} secure, {len(by.get('dev', []))} in a declared dev posture, "
                        f"{len(by.get('unsecured', []))} UNSECURED, {len(by.get('unknown', []))} unknown" if n else 'no device has posted an inventory yet')}


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


TRACKED_GROUPS = ('sudo', 'admin', 'wheel', 'docker', 'libvirt', 'kvm', 'dialout', 'plugdev')


def permission_group_updates(device, inv):
    """The tie between what a device REPORTS (its /etc/group) and the PermissionGroup rows the security module
    designs (polari-* sudoers groups, docker/libvirt/kvm …): {group: {'members': 'device: a, b', 'installed': ...}}
    — merged per device into the row by the API, so a group's members are visible across the isle."""
    s = inv.get('ssh') or {}
    out = {}
    for line in s.get('groups') or []:
        name, _, members = line.partition('|')
        if name.startswith('polari-') or name in TRACKED_GROUPS:
            out[name] = {'members': f"{device}: {', '.join(m for m in members.split(',') if m) or '(nobody)'}", 'installed': 'yes'}
    return out


def merge_members(existing, device, entry):
    """'a: x, y; b: z' merged with this device's entry — one segment per device, this device's replaced."""
    segs = [seg.strip() for seg in (existing or '').split(';') if seg.strip() and not seg.strip().startswith(device + ':')]
    segs.append(entry)
    return '; '.join(segs)
