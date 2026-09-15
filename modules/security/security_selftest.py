"""security_selftest — the module constructs, the three views build for every scenario, the simulation and
the comparison answer, the seed is well-formed, the pages have no raw JSON, and the facts hold:
stock docker blocks module loading / mount / ptrace / userns; stock docker ALLOWS writing the image, raw
sockets and chroot (Polari's rings remove them); a guest cannot escape; the lean profile's API is open."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))


def main():
    from security.security_basis import SECURITY_CLASSES, SecurityTopologyEdge
    from security.security_seed import SECURITY_SEED_PAIRS, SEED_SECURITY_EDGES
    from security.security_page import SEED_SECURITY_PAGE_DISPLAYS
    from security.custom.security_topology import MODES, VIEWS, build, compare, simulate
    from security.custom.security_facts import SYSTEMS, scenario_names
    check('twenty-seven row classes', len(SECURITY_CLASSES) == 27, str(len(SECURITY_CLASSES)))
    check('row class constructs', SecurityTopologyEdge(name='x').name == 'x')
    n = 0
    for scn in scenario_names():
        for v in VIEWS:
            for m in MODES:
                g = build(v, scn, m); n += 1
                assert g['edges'] and g['nodes'], (v, scn, m)
    check('every view × scenario × mode builds', n == len(scenario_names()) * 3 * 4, str(n))
    stock = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'stock')['edges'] if e['source'] == 'prf-backend'}
    check('stock docker blocks: module load, mount, ptrace, userns', all((m, 'blocked') in stock for m in ('load a kernel module', 'mount a filesystem / pivot_root', "ptrace another container's process", 'new user namespace (unshare -r), keyctl, bpf')))
    check('stock docker ALLOWS: image write, raw socket, chroot', all((m, 'allowed') in stock for m in ('write into /usr, /etc, /bin of its own image', 'open a raw socket (sniff / forge packets)', 'chroot')))
    enf = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'enforce')['edges'] if e['source'] == 'prf-backend'}
    check('enforce removes them', all((m, 'blocked') in enf for m in ('write into /usr, /etc, /bin of its own image', 'open a raw socket (sniff / forge packets)', 'chroot')))
    comp = {(e['means'], e['verdict']) for e in build('os', 'isle', 'today')['edges'] if e['source'] == 'prf-isle-backend'}
    check('today on the isle LOGS the image write (the union profile is loaded there)', ('write into /usr, /etc, /bin of its own image', 'logged') in comp)
    todl = {(e['means'], e['verdict']) for e in build('os', 'swarm-lean', 'today')['edges'] if e['source'] == 'prf-backend'}
    check('today on the swarm the image write is still ALLOWED (nothing loaded there)', ('write into /usr, /etc, /bin of its own image', 'allowed') in todl)
    check('the host-bind read is DAC\'s, not AppArmor\'s', any(e['means'].startswith("read the host's") and e['decided_by'] in ('mount-policy', 'userns') for e in build('os', 'isle', 'enforce')['edges']))
    g = build('os', 'isle', 'today')
    check('a guest cannot escape (qemu layers)', any(e['source'] == 'a guest' and e['means'] == 'escape the hypervisor' and e['verdict'] == 'blocked' for e in g['edges']))
    check('swarm folds modules into the backend', any(e['source'] == 'a module' and e['target'] == 'prf-backend' for e in build('os', 'swarm-lean')['edges']))
    lean = simulate('app', 'swarm-lean', 'visitor'); full = simulate('app', 'swarm-full', 'visitor')
    check('lean: the API is open to a visitor; full: refused without a token', 'api' in lean['reach']['allowed'] and 'api' in full['reach']['blocked'])
    check('simulate names an unknown actor honestly', simulate('os', 'dev', 'nobody')['ok'] is False)
    c = compare('network')
    check('compare has a column per scenario', all(scn in c['rows'][0] for scn in scenario_names()))
    row = [x for x in compare('os')['rows'] if x['means'].startswith('write into') and x['source'] == 'the Polari backend'][0]
    check('compare lines the backend up across routes', all(row[s] != '—' for s in ('isle', 'swarm-lean', 'swarm-full')), str(row))
    check('every system has a provenance', all(s['provenance'] in ('stock', 'qemu', 'polari') for s in SYSTEMS.values()))
    check('seed pairs: 27, all rows named', len(SECURITY_SEED_PAIRS) == 27 and all(r.get('name') for _, _, rows in SECURITY_SEED_PAIRS for r in rows))
    check('edge rows unique by name', len({r['name'] for r in SEED_SECURITY_EDGES}) == len(SEED_SECURITY_EDGES), str(len(SEED_SECURITY_EDGES)))
    check('eight pages, none with api-json-panel', len(SEED_SECURITY_PAGE_DISPLAYS) == 8 and all('api-json-panel' not in p['definition'] for p in SEED_SECURITY_PAGE_DISPLAYS))
    from security.custom.security_threats import threats, threat_rows
    th = {t['name']: t for t in threats('swarm-lean', 'stock')['threats']}
    check('stock: the image backdoor, raw sniff AND the socket (if mounted) get THROUGH — docker alone stops none', th['image-backdoor']['verdict'] == 'allowed' and th['raw-sniff']['verdict'] == 'allowed' and th['docker-socket']['verdict'] == 'allowed')
    check('today: the socket threat is blocked by the mount policy', {t['name']: t for t in threats('swarm-lean', 'today')['threats']}['docker-socket']['blocked_by'] == 'mount-policy')
    te = {t['name']: t for t in threats('swarm-lean', 'enforce')['threats']}
    check('enforce: both blocked, with the blocking policy named', te['image-backdoor']['verdict'] == 'blocked' and te['image-backdoor']['blocked_by'] and te['raw-sniff']['verdict'] == 'blocked')
    check('every threat carries a counterexample path that reaches the target', all(t['counter']['path'][-1]['node'] == t['counter']['target'] for t in te.values()))
    ti = {t['name']: t for t in threats('isle', 'today')['threats']}
    check('isle: guest escape and the unassigned device are present; the device counterexample is open on the isle', 'guest-escape' in ti and ti['unassigned-device']['counter']['verdict'] == 'allowed')
    check('swarm: the device counterexample has NO legitimate path', te['unassigned-device']['counter']['verdict'] == 'blocked')
    check('lean: the anonymous API threat is ALLOWED and says so; full: blocked by keycloak', th['anonymous-api']['verdict'] == 'allowed' and {t['name']: t for t in threats('swarm-full', 'today')['threats']}['anonymous-api']['blocked_by'] == 'keycloak')
    check('the animation path stops at the block', all(t['path'][t['stops_at']]['decision'] == 'blocked' for t in te.values() if t['stops_at'] is not None))
    ph = {e['means']: e for e in build('os', 'isle', 'today')['edges'] if e['source'] == 'physical access'}
    check('physical access: with encryption off the drive is readable; Secure Boot stops a tampered kernel but not a live USB',
          ph['pull the drive and read it in another machine']['verdict'] == 'allowed' and ph['replace the boot loader or kernel on the disk with a tampered one']['decided_by'] == 'secure-boot'
          and ph['boot a live USB and read the files']['verdict'] == 'allowed')
    phe = {e['means']: e for e in build('os', 'isle', 'enforce')['edges'] if e['source'] == 'physical access'}
    check('enforce on a desktop profile: encryption on → the drive and the live USB are blocked', phe['pull the drive and read it in another machine']['decided_by'] == 'disk-encryption')
    phs = {e['means']: e for e in build('os', 'swarm-lean', 'enforce')['edges'] if e['source'] == 'physical access'}
    check('enforce on a headless profile: encryption stays OFF (never on headless) → the drive is still readable', phs['pull the drive and read it in another machine']['verdict'] == 'allowed')
    tt = {t['name']: t for t in threats('isle', 'today')['threats']}
    check('the two physical threats exist with counterexamples', 'stolen-drive' in tt and 'tampered-boot' in tt and tt['stolen-drive']['counter']['path'][-1]['node'] == 'the disk')
    from security.security_seed import SEED_SECURITY_LEDGER, SEED_SECURITY_TRUST_CHANNELS, SEED_SECURITY_MAC_PROFILES, SEED_SECURITY_SERVICE_IDENTITIES
    check('ledger: one row per app per scenario; nothing blocked at conform', len(SEED_SECURITY_LEDGER) > 200 and not any(r['blocking'] == 'stanza_conforms' for r in SEED_SECURITY_LEDGER))
    check('ledger: the isle backend is blocked at mac_enforced (loaded in complain today)', next(r for r in SEED_SECURITY_LEDGER if r['name'] == 'isle:prf-isle-backend')['blocking'] == 'mac_enforced')
    check('trust channels: public Keycloak clients are asymmetric, the confidential one symmetric, no symmetric USER channel', any(c['name'].endswith('polari-frontend') and c['key_kind'] == 'asymmetric' for c in SEED_SECURITY_TRUST_CHANNELS) and any(c['name'].endswith('polari-backend') and c['key_kind'] == 'symmetric' for c in SEED_SECURITY_TRUST_CHANNELS) and not any(c['finding'] for c in SEED_SECURITY_TRUST_CHANNELS))
    check('mac profiles: the isle union is complain today, the swarm union only rendered', {(r['scenario'], r['mode']) for r in SEED_SECURITY_MAC_PROFILES if r['app'] == 'docker-default'} == {('isle', 'complain'), ('swarm-lean', 'rendered'), ('swarm-full', 'rendered')})
    check('service identities: expired internal certs are reported as such (days_left < 0)', any(r['issued'] and r['days_left'] < 0 for r in SEED_SECURITY_SERVICE_IDENTITIES))
    from security.custom.security_proposals import propose_from_groups
    pr = propose_from_groups('gears', {'profile': 'web-app', 'writable': ['/data'], 'network': ['isle'], 'capabilities': []}, [
        {'class': 'file', 'object': '/app/data/gears/out.csv', 'mask': 'wc', 'count': 3}, {'class': 'file', 'object': '/usr/local/lib/python3.12/__pycache__/x.pyc', 'mask': 'w', 'count': 30},
        {'class': 'file', 'object': '/etc/hosts', 'mask': 'w', 'count': 1}, {'class': 'cap', 'object': 'capability chown', 'mask': ''}, {'class': 'cap', 'object': 'capability sys_admin', 'mask': ''},
        {'class': 'seccomp', 'object': 'syscall open', 'mask': ''}, {'class': 'mount', 'object': 'mount /mnt/ tmpfs', 'mask': ''}])
    check('proposal: writable /app/data + CHOWN + open proposed; pycache ignored; /etc write, sys_admin and mount NOT expressible',
          pr['add_writable'] == ['/app/data'] and pr['add_capabilities'] == ['CHOWN'] and pr['add_syscalls'] == ['open'] and pr['pycache_writes_ignored'] == 30 and len(pr['not_expressible']) == 3)
    from security.custom.security_audit_feed import applied_from_controls, physical_from_controls
    ctl = [{'ring': 'mac', 'control': 'per-app-profiles', 'status': 'pass'}, {'ring': 'mac', 'control': 'profiles-enforcing', 'status': 'fail'}, {'ring': 'network', 'control': 'ufw', 'status': 'pass'}, {'ring': 'physical', 'control': 'secure-boot', 'status': 'fail'}]
    check('audit feed: profiles loaded + not enforcing → apparmor complain; ufw pass → live; secure boot fail → off', applied_from_controls(ctl) == {'polari-apparmor': 'complain', 'ufw': 'live'} and physical_from_controls(ctl) == {'secure_boot': False})
    from security.custom.security_notices import notices_from
    nt = notices_from(probes=[{'host': 'prf.example', 'days_left': -3, 'not_after': '2026-09-10', 'issuer': 'x'}, {'host': 'api.prf.example', 'days_left': 9, 'not_after': '', 'issuer': ''}],
                      audit_controls=[{'control': 'auto-renew', 'status': 'fail'}], identities=[{'service': 'pol-kc', 'issued': True, 'days_left': -25, 'manifest': 'ca/cert-manifest.conf'}], hosts=['prf.example', 'api.prf.example', 'hub.example'])
    codes = [n['code'] for n in nt]
    check('notices: expired → error with the renew action; expiring → warning; auto-renew absent → info; internal expired → warning; unreachable host → info',
          codes == ['cert-expired', 'cert-expiring', 'auto-renew-absent', 'internal-cert-expired', 'host-unreachable'] and nt[0]['level'] == 'error' and 'pol cert renew' in nt[0]['action'])
    from security.custom.security_ssh import ssh_row_from_inventory, inventory_row, ssh_summary
    inv = {'os': 'Ubuntu', 'kernel': 'k', 'docker': {'version': '29', 'swarm': 'active/false', 'containers': [{'name': 'isle-vlan-agent'}], 'stacks': [], 'images': [], 'volumes': 1}, 'debs': ['polari-complete|0.1.33|ok'], 'checkouts': ['/x|dev|1G'], 'units': ['isle-host-agent.service|active|running'], 'guests': ['openwrt-isle-router'], 'etc_isle_mesh': True, 'apparmor_polari': 66,
           'ssh': {'listen': ['0.0.0.0:22'], 'password_auth': 'yes', 'pubkey_auth': 'yes', 'permit_root': 'without-password', 'kbd_interactive': 'no', 'authorized_keys': [{'user': 'u', 'type': 'ssh-ed25519', 'comment_kind': 'user@host'}], 'private_keys_present': ['u|id_ed25519'], 'ssh_config_hosts': ['u|lightweight'], 'fail2ban': 'inactive', 'recent_failed_logins_24h': 0}}
    r = ssh_row_from_inventory('isle-core', inv); ir = inventory_row('isle-core', inv)
    check('ssh: passwords + root login → exposed, with the vectors named; role isle-core; formats deb + containers + guests', r['verdict'] == 'exposed' and 'passwords accepted' in r['vector'] and 'root may log in' in r['vector'] and r['role'] == 'isle-core' and 'deb' in ir['formats'] and 'KVM guests' in ir['formats'])
    inv2 = dict(inv, ssh=dict(inv['ssh'], listen=[])); check('ssh: no sshd → closed', ssh_row_from_inventory('pol-core', inv2)['verdict'] == 'closed')
    inv3 = dict(inv, ssh=dict(inv['ssh'], password_auth='no', permit_root='no')); check('ssh: keys only + no root → keys-only', ssh_row_from_inventory('x', inv3)['verdict'] == 'keys-only')
    check('ssh summary reads', ssh_summary([r, ssh_row_from_inventory('pol-core', inv2)])['exposed'] == ['isle-core'])
    # his ask 2026-09-14: permission levels + assurance (secure | dev until | unsecured)
    from security.custom.security_ssh import permission_levels, ssh_assurance, assurance_summary
    inv_u = dict(inv, ssh=dict(inv['ssh'], password_auth='no', permit_root='without-password', allow_groups='', groups=['sudo|u', 'polari-ops|dev1'],
                               sudoers=['root ALL=(ALL:ALL) ALL', '%sudo ALL=(ALL:ALL) ALL', 'u ALL=(ALL) NOPASSWD: ALL', '%polari-ops ALL=(root) /usr/bin/pol, /usr/bin/systemctl']))
    a = ssh_assurance(inv_u)
    check('assurance: root with key + no AllowGroups + blanket sudo, no posture → UNSECURED with the three reasons', a[0] == 'unsecured' and 'root may log in' in a[1] and 'AllowGroups' in a[1] and 'blanket sudo for u' in a[1], a)
    lv = {r['principal']: r for r in permission_levels('n', inv_u)}
    check('levels: u = blanket-sudo (sudoers ALL), %polari-ops = scoped-sudo with its command list, dev1 scoped via the group, root allowed in',
          lv['u']['level'] == 'blanket-sudo' and lv['%polari-ops']['level'] == 'scoped-sudo' and '/usr/bin/pol' in lv['%polari-ops']['commands'] and lv['dev1']['level'] == 'scoped-sudo' and lv['root']['allowed_over_ssh'] is True, {k: (v['level'], v['allowed_over_ssh']) for k, v in lv.items()})
    inv_d = dict(inv_u, ssh=dict(inv_u['ssh'], posture={'posture': 'dev', 'until': '2999-01-01T00:00:00Z', 'relaxations': ['ssh.root-key-from-isle']}))
    a2 = ssh_assurance(inv_d)
    check('assurance: the same device under a declared, unexpired dev posture → DEV with the expiry', a2[0] == 'dev' and '2999' in a2[1], a2)
    inv_x = dict(inv_u, ssh=dict(inv_u['ssh'], posture={'posture': 'dev', 'until': '2020-01-01T00:00:00Z'}))
    check('assurance: an EXPIRED dev posture → UNSECURED', ssh_assurance(inv_x)[0] == 'unsecured' and 'EXPIRED' in ssh_assurance(inv_x)[1])
    inv_p = dict(inv_d, ssh=dict(inv_d['ssh'], password_auth='yes'))
    check('invariant: passwords accepted is UNSECURED even in dev posture', ssh_assurance(inv_p)[0] == 'unsecured')
    inv_s = dict(inv_u, ssh=dict(inv_u['ssh'], permit_root='no', allow_groups='polari-ops', sudoers=['root ALL=(ALL:ALL) ALL', '%sudo ALL=(ALL:ALL) ALL', '%polari-ops ALL=(root) /usr/bin/pol']))
    check('assurance: keys only + no root + AllowGroups + scoped sudo → SECURE; a keyed user outside AllowGroups is not allowed in', ssh_assurance(inv_s)[0] == 'secure' and {r['principal']: r['allowed_over_ssh'] for r in permission_levels('n', inv_s)}['u'] is False)
    rows = [ssh_row_from_inventory('a', inv_s), ssh_row_from_inventory('b', inv_d), ssh_row_from_inventory('c', inv_u)]
    summ = assurance_summary(rows)
    check('assurance summary: 1 secure, 1 dev (until), 1 unsecured → not assured', summ['secure'] == ['a'] and summ['dev'] and summ['dev'][0].startswith('b (until') and summ['unsecured'] == ['c'] and summ['assured'] is False, summ)
    check('assurance summary: secure + dev only → assured', assurance_summary(rows[:2])['assured'] is True)
    from security.custom.security_notices import posture_notices
    class _M:
        pass
    class _R:
        def __init__(self, **kw): self.__dict__.update(kw)
    m = _M(); m.objectTables = {'SshCapability': {'b': _R(device='b', assurance='dev', posture_until='2999-01-01T00:00:00Z', assurance_reasons=''), 'c': _R(device='c', assurance='unsecured', posture_until='', assurance_reasons='passwords accepted')}}
    pn = posture_notices(m, env={'POLARI_POSTURE': 'dev'})
    check('dev-mode notices: the install-level DEV MODE warning names the danger of connecting to systems that are not your own; dev devices warn; unsecured devices error',
          [n['code'] for n in pn] == ['dev-mode', 'dev-posture-devices', 'ssh-unsecured'] and 'not your own' in pn[0]['text'] and 'EXTREMELY DANGEROUS' in pn[0]['text'] and pn[2]['level'] == 'error' and 'passwords accepted' in pn[2]['text'], [n['code'] for n in pn])
    check('production install, every device secure → no posture notice', posture_notices(_M(), env={}) == [])
    # ---- ISLE_HARDENING_PLAN §17: OBSERVE MODE — one switch (posture), one ledger (SecurityEvent), one contract
    import os
    import tempfile
    from moduleService import posture as P
    from security.custom import security_observe as O
    with tempfile.TemporaryDirectory() as td:
        pf = os.path.join(td, 'posture.json')
        check('posture: nothing says dev → production (source default)', P.state(env={}, path=pf) == {'posture': 'production', 'until': '', 'source': 'default', 'expired': False, 'relaxations': [], 'applied_by': ''})
        check('posture: POLARI_POSTURE=dev wins (source env)', P.state(env={'POLARI_POSTURE': 'dev', 'POLARI_POSTURE_UNTIL': ''}, path=pf)['posture'] == 'dev' and P.is_dev(env={'POLARI_POSTURE': 'dev'}, path=pf))
        open(pf, 'w').write('{"posture": "dev", "until": "2999-01-01T00:00:00Z", "relaxations": ["ssh.root-key-from-isle"], "applied_by": "posture.sh"}')
        st = P.state(env={}, path=pf)
        check('posture: the machine\'s posture.json (mounted read-only) says dev with an expiry → dev, its relaxations read', st['posture'] == 'dev' and st['source'] == 'file' and st['relaxations'] == ['ssh.root-key-from-isle'])
        open(pf, 'w').write('{"posture": "dev", "until": "2020-01-01T00:00:00Z"}')
        st = P.state(env={}, path=pf)
        check('posture: an EXPIRED dev posture is production again (the revert timer\'s promise, kept here too)', st['posture'] == 'production' and st['expired'] is True)
    m2 = _M(); m2.objectTables = {'SecurityEvent': {}}
    m2.persistTree = lambda: None
    dev = {'POLARI_POSTURE': 'dev'}; prod = {}
    check('decide: an allowed act is allowed, nothing recorded', O.decide(m2, 'authz', 'update Person', 'Person', denied=False, env=dev) == (True, 'allowed') and O.events(m2) == [])
    ok, out = O.decide(m2, 'authz', 'update Person', 'Person', denied=True, reason='no verb grant', actor='dev1', env=dev, source='test')
    check('decide: DEV posture + an observable control → the act PROCEEDS as "observed" and a SecurityEvent counts it', ok is True and out == 'observed' and len(O.events(m2)) == 1 and O.events(m2)[0]['count'] == 1 and O.events(m2)[0]['would_deny'] is True)
    O.decide(m2, 'authz', 'update Person', 'Person', denied=True, reason='no verb grant', env=dev)
    check('the same decision again counts on the same row (control|action|target)', len(O.events(m2)) == 1 and O.events(m2)[0]['count'] == 2)
    check('decide: PRODUCTION posture → denied (the caller refuses as before), recorded as denied', O.decide(m2, 'authz', 'delete Person', 'Person', denied=True, env=prod)[1] == 'denied')
    check('decide: an INVARIANT (§16) refuses even in dev; an unknown control is treated as an invariant',
          O.decide(m2, 'ssh-password', 'password login', 'sshd', denied=True, env=dev) == (False, 'denied') and O.decide(m2, 'made-up', 'x', 'y', denied=True, env=dev) == (False, 'denied'))
    check('the contract: authz, peer admission, certificates, trust channels, content, browser, tier, posture relaxations OBSERVE; the six invariants + dev-variant-on-production + headless encryption REFUSE',
          set(O.OBSERVED_CONTROLS) >= {'authz', 'peer-admission', 'certificate', 'trust-channel', 'content', 'browser', 'tier', 'posture-relaxation'}
          and set(O.INVARIANT_CONTROLS) >= {'ssh-password', 'upstream-interface', 'production-route', 'dev-variant-on-production', 'iso-headless-encryption'} and not set(O.OBSERVED_CONTROLS) & set(O.INVARIANT_CONTROLS))
    s = O.summary(m2, env=dev)
    check('summary: observe on, the observed actions counted per control, the contract stated', s['observe'] is True and s['observed_actions'] == 2 and s['per_control'] == {'authz': 2} and s['contract']['observed'])
    on = O.observe_notice(m2, env=dev)
    check('the notice bar item (dev only): OBSERVE MODE with the count of what production would deny; absent in production',
          len(on) == 1 and on[0]['code'] == 'observe-mode' and on[0]['level'] == 'warning' and '2 action(s)' in on[0]['title'] and O.observe_notice(m2, env=prod) == [])
    from security.security_api import SecurityAPI
    class _Req:
        params = {}
    class _Res:
        media = None; status = '200 OK'
    api = SecurityAPI(polServer=None, manager=None); api.manager = m2; r = _Res(); api.on_get_events(_Req(), r)
    check('/api/security/events answers with the summary, the events and the how', r.media['ok'] and r.media['summary']['observed_events'] == 1 and len(r.media['events']) >= 2 and 'observe' in r.media['how'],
          (r.media or {}).get('summary'))
    from accessControl.app_permissions_gate import crude_permission_gate
    import types as _types
    class _Hdr:
        def __init__(self): self.h = {}; self.status = ''; self.media = None
        def set_header(self, k, v): self.h[k] = v
    class _ReqU:
        context = _types.SimpleNamespace(user_info={'preferred_username': 'dev1'})
    import sys as _sys, types as _t
    fake = _t.ModuleType('polariapps.apps_permissions_basis'); fake.permission_verdict = lambda *a, **k: {'allowed': False, 'reason': 'no grant'}
    pkg = _t.ModuleType('polariapps'); pkg.apps_permissions_basis = fake
    saved = {k: _sys.modules.get(k) for k in ('polariapps', 'polariapps.apps_permissions_basis')}
    _sys.modules['polariapps'] = pkg; _sys.modules['polariapps.apps_permissions_basis'] = fake
    m3 = _M(); m3.objectTables = {'AppPermissionProfile': {}, 'SecurityEvent': {}}; m3.persistTree = lambda: None
    old_env = dict(os.environ); os.environ['POLARI_APP_PERMISSIONS'] = 'enforce'; os.environ['POLARI_POSTURE'] = 'dev'
    try:
        h = _Hdr(); g1 = crude_permission_gate(m3, _ReqU(), h, 'update', 'Person')
        os.environ['POLARI_POSTURE'] = 'production'; h2 = _Hdr(); g2 = crude_permission_gate(m3, _ReqU(), h2, 'update', 'Person')
    finally:
        os.environ.clear(); os.environ.update(old_env)
        for k, v in saved.items():
            if v is None: _sys.modules.pop(k, None)
            else: _sys.modules[k] = v
    check('the CRUDE permission gate in ENFORCE: a dev build lets the refused act through with an "observed" header + a SecurityEvent; production still 403s',
          g1 is True and 'observed Person:update' in h.h.get('X-Polari-Permission-Advisory', '') and len(O.events(m3)) == 1 and O.events(m3)[0]['actor'] == 'dev1' and g2 is False and h2.status == '403 Forbidden')
    from security.custom.security_ssh import permission_group_updates, merge_members
    pg = permission_group_updates('n', inv_u)
    check('permission groups: observed sudo + polari-ops members tied per device', pg['sudo']['members'] == 'n: u' and pg['polari-ops']['members'] == 'n: dev1')
    check('members merge per device (this device replaced, others kept)', merge_members('a: x; n: old', 'n', 'n: u') == 'a: x; n: u')
    check('the password-guess threat exists on the isle with its counterexample', 'ssh-password-guess' in {t['name'] for t in threats('isle', 'today')['threats']})
    check('threat rows seed for every scenario', len([r for n in scenario_names() for r in threat_rows(n)]) >= 40)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
