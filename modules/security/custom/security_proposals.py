"""
@module security.custom.security_proposals

The write-back pass (his question 2026-09-13: "did we confirm the capability to do automation passes for
creating security profiles for different pieces of functionality?"): a harvest of what an app ACTUALLY did
under a warn-only profile (os-security/allowed.py groups: files it wrote, capabilities it used, sockets it
opened, syscalls outside its seccomp list) becomes a PROPOSED stanza change for that app — writable paths
(at directory level), capabilities from the allow-list, a network kind, seccomp list additions — and the
AppArmor lines that would allow each. Nothing is applied: a SecurityProposal row waits for an operator to
accept (`pol security os propose --accept`, which writes the stanza into the manifest, re-runs conform and
re-renders), or to refuse with a reason. Accesses the stanza vocabulary cannot express (a device from a
non-hardware kind, a capability outside the allow-list, mounting) are listed as 'needs a guest / not
expressible' so they are never silently widened into.
"""
import json
import os
import re

CAPS = ('NET_ADMIN', 'NET_BIND_SERVICE', 'CHOWN', 'SETUID', 'SETGID', 'DAC_READ_SEARCH')
NEVER_WRITABLE = ('/', '/etc', '/usr', '/bin', '/sbin', '/lib', '/lib64', '/boot', '/root', '/home', '/proc', '/sys', '/dev')
PYCACHE = re.compile(r'/__pycache__/')


def _dir_of(path):
    d = path.rsplit('/', 1)[0] or '/'
    # collapse deep paths to their first two components under a known root (/app/data/x/y → /app/data)
    parts = [p for p in d.split('/') if p]
    if len(parts) >= 2:
        return '/' + '/'.join(parts[:2])
    return d


def propose_from_groups(app, stanza, groups):
    """groups = allowed.py's reduced groups for ONE profile. Returns the proposal dict."""
    stanza = dict(stanza or {})
    writable = list(stanza.get('writable') or [])
    caps = list(stanza.get('capabilities') or [])
    network = list(stanza.get('network') or ['isle'])
    add_writable, add_caps, add_syscalls, not_expressible, apparmor_lines, pycache = [], [], [], [], [], 0
    for g in groups:
        c, obj, mask = g.get('class'), g.get('object', ''), g.get('mask', '')
        if c == 'file' and any(ch in mask for ch in 'wcdk'):
            if PYCACHE.search(obj):
                pycache += g.get('count', 1)
                continue
            d = _dir_of(obj)
            if d in NEVER_WRITABLE or any(d == root or d.startswith(root + '/') for root in ('/etc', '/usr', '/bin', '/sbin', '/lib', '/lib64', '/boot', '/root', '/home', '/proc', '/sys')):
                not_expressible.append(f"writes {obj} — inside the image / the host; a read-only root or a data path move, not a wider profile")
            elif d not in writable and d not in add_writable:
                add_writable.append(d)
                apparmor_lines.append(f'{d}/** rwk,')
        elif obj.startswith('capability '):
            cap = obj.split()[1].upper()
            if cap in CAPS and cap not in caps and cap not in add_caps:
                add_caps.append(cap); apparmor_lines.append(f'capability {cap.lower()},')
            elif cap not in CAPS:
                not_expressible.append(f'capability {cap} is not in the allow-list (SYS_ADMIN and friends are never grantable): a guest, or a smaller app')
        elif obj.startswith('network ') and 'raw' in obj:
            if 'internet' not in network and stanza.get('profile') not in ('gateway', 'vpn-gateway'):
                not_expressible.append('raw sockets: only gateway kinds get them — is this app a gateway?')
        elif obj.startswith('network inet') and 'internet' not in network:
            pass   # inet is allowed for isle+internet alike; the DOCKER-USER ring decides reach, not the profile
        elif c == 'seccomp':
            name = obj.split()[-1]
            if name not in add_syscalls:
                add_syscalls.append(name)
        elif c == 'mount' or obj.startswith(('mount', 'umount', 'pivotroot')):
            not_expressible.append(f'{obj}: mounting is never allowed to an app')
    proposed = dict(stanza)
    if add_writable:
        proposed['writable'] = writable + add_writable
    if add_caps:
        proposed['capabilities'] = caps + add_caps
    return {'app': app, 'observed': len(groups), 'pycache_writes_ignored': pycache, 'add_writable': add_writable, 'add_capabilities': add_caps,
            'add_syscalls': add_syscalls, 'not_expressible': not_expressible, 'apparmor_lines': apparmor_lines,
            'proposed_stanza': proposed, 'changes': bool(add_writable or add_caps or add_syscalls),
            'reading': (f"{app}: {len(add_writable)} writable path(s), {len(add_caps)} capability(ies), {len(add_syscalls)} syscall(s) proposed; "
                        f"{len(not_expressible)} access(es) the stanza cannot express; {pycache} bytecode-cache writes ignored (read-only root is the fix)")}


def proposal_row(proposal, harvest_source='', status='proposed'):
    return {'name': f"{proposal['app']}:{harvest_source or 'harvest'}", 'app': proposal['app'], 'source': harvest_source, 'status': status,
            'observed': proposal['observed'], 'add_writable': ','.join(proposal['add_writable']), 'add_capabilities': ','.join(proposal['add_capabilities']),
            'add_syscalls': ','.join(proposal['add_syscalls']), 'not_expressible': ' | '.join(proposal['not_expressible'])[:1500],
            'apparmor_lines': '\n'.join(proposal['apparmor_lines'])[:1500], 'proposed_stanza': json.dumps(proposal['proposed_stanza']),
            'reading': proposal['reading'], 'accepted_by': '', 'notes': ''}


def accept_into_manifest(manifest_path, proposed_stanza):
    """Write the accepted stanza into the app's polari-app.json (conform re-runs afterwards)."""
    m = json.load(open(manifest_path, encoding='utf-8'))
    m['security'] = proposed_stanza
    json.dump(m, open(manifest_path, 'w', encoding='utf-8'), indent=1)
    return manifest_path
