"""
@module security.custom.security_topology

The three security topology views and the reach simulation (his ask 2026-09-12:
"topology based simulations to demonstrate intuitively what is being protected
and how, via what system, and what groups and apps give you access through what
means — separating the topology logic across 3 security topology views").

  os      what a process can touch on the machine (containers, modules inside the
          core, guests → the kernel, the host's files, other containers, devices,
          the docker socket), and which system decides each hop
  network how bytes get in, between and out (internet, LANs, overlays, host
          services, listening containers, doors)
  app     who gets access to what through which means (visitors, logged-in users,
          group members, root, apps, guests → the API, the data, the host)

Every edge is a reach attempt: source → target by a means, a CHAIN of systems
consulted in order, each with its provenance (stock docker / qemu / polari) and
its decision under the MODE simulated:
  stock     only what docker, the kernel and qemu give every container/guest
  today     what is really applied on that scenario right now (security_facts.APPLIED_TODAY)
  complain  every Polari ring that can warn loaded warn-only (what a warn-only apply would log)
  enforce   every Polari ring on
The verdict is the first block, else "logged" if anything logged, else allowed.
Pure functions over security_facts; no I/O beyond reading the scenario file.
"""
from security.custom.security_facts import APPLIED_TODAY, SYSTEMS, load_scenario

VIEWS = ('os', 'network', 'app')
MODES = ('stock', 'today', 'complain', 'enforce')
LOGGABLE = ('polari-apparmor', 'polari-seccomp')


def _step(system, decision, note=''):
    s = SYSTEMS[system]
    return {'system': system, 'title': s['title'], 'provenance': s['provenance'], 'decision': decision, 'note': note}


def _verdict(chain):
    for st in chain:
        if st['decision'] == 'blocked':
            return 'blocked', st['system'], st['provenance']
    for st in chain:
        if st['decision'] == 'logged':
            return 'logged', st['system'], st['provenance']
    last = next((st for st in reversed(chain) if st['decision'] == 'allowed'), None)
    return 'allowed', (last['system'] if last else ''), (last['provenance'] if last else '')


def _polari(mode, applied, system, enforce_blocks=True):
    """Decision of a Polari ring under the simulated mode. stock: absent. complain: the rings that can warn
    (AppArmor, seccomp) log; the rest are printed, not applied. enforce: on. today: whatever APPLIED_TODAY
    says is really loaded on that scenario (complain → logs; enforce/live → decides)."""
    if mode == 'stock':
        return 'n/a'
    if mode == 'enforce':
        return 'blocked' if enforce_blocks else 'allowed'
    if mode == 'complain':
        return 'logged' if system in LOGGABLE else 'n/a'
    live = applied.get(system)
    if live in ('enforce', 'live'):
        return 'blocked' if enforce_blocks else 'allowed'
    if live == 'complain':
        return 'logged'
    return 'n/a'


# ------------------------------------------------------------------ the OS view
OS_TARGETS = [
    ('kernel', 'target', 'the host kernel'), ('host-files', 'target', "the host's files (a bind of /etc, /home)"),
    ('image', 'target', "the container's own image (/usr, /etc inside)"), ('other-container', 'target', 'another container'),
    ('docker-socket', 'target', 'the docker socket (root-equivalent)'), ('devices', 'target', 'host devices (/dev/tty*, video, usb, kvm)'),
    ('proc-sys', 'target', '/proc/sys, sysrq, kcore'),
]


def _os_process_edges(p, sc, mode, applied):
    """Reach attempts from one container process. p = a fixed piece or app dict; sc = scenario."""
    kind = p.get('profile', 'web-app'); caps = set(p.get('capabilities') or [])
    surface_on = (mode == 'enforce')
    E = []

    def edge(target, means, chain, why):
        v, by, prov = _verdict(chain)
        E.append({'source': p['name'], 'target': target, 'means': means, 'chain': chain, 'verdict': v, 'decided_by': by, 'provenance': prov, 'why': why})

    edge('kernel', 'load a kernel module', [
        _step('docker-caps', 'blocked', 'CAP_SYS_MODULE is not in the default set'),
        _step('docker-seccomp', 'blocked', 'init_module/finit_module are not in the builtin profile'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'deny capability sys_module (enforce)')],
        'stock docker already stops this twice; Polari adds a third layer')
    edge('kernel', 'mount a filesystem / pivot_root', [
        _step('docker-caps', 'blocked', 'no CAP_SYS_ADMIN'), _step('docker-seccomp', 'blocked', 'mount is not in the builtin profile'),
        _step('docker-apparmor', 'blocked', 'docker-default: deny mount'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'the same deny, kept in complain too')],
        'three stock layers; Polari keeps docker\'s deny')
    edge('proc-sys', 'write /proc/sys/kernel/* or /proc/sysrq-trigger', [
        _step('docker-masks', 'blocked', 'read-only and masked paths'), _step('docker-apparmor', 'blocked', 'deny /proc writes'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'))], 'masked by docker in every container')
    edge('other-container', 'ptrace another container\'s process', [
        _step('docker-caps', 'blocked', 'no CAP_SYS_PTRACE'), _step('docker-seccomp', 'blocked', 'ptrace without the capability'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'ptrace peer = the app itself only')],
        'stock; Polari narrows ptrace to the app\'s own profile')
    edge('kernel', 'new user namespace (unshare -r), keyctl, bpf', [
        _step('docker-seccomp', 'blocked', 'the builtin profile blocks all three'),
        _step('polari-seccomp', _polari(mode, applied, 'polari-seccomp'), 'absent from every kind\'s list')],
        'seccomp\'s job, stock already; Polari\'s list keeps them out')
    edge('image', 'write into /usr, /etc, /bin of its own image', [
        _step('linux-dac', 'allowed', 'uid 0 inside owns the image files'),
        _step('docker-apparmor', 'allowed', 'docker-default allows all files'),
        _step('polari-surface', 'blocked' if surface_on else 'n/a', 'read_only: true — rendered, applied nowhere yet'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'the image is read-only in the allow-list; enforce also denies /usr /etc … w')],
        'ALLOWED by stock docker: a rooted app can overwrite its own entrypoints; Polari\'s surface ring or profile stops it')
    edge('host-files', "read the host's /etc/shadow through a bind mount", [
        _step('mount-policy', 'blocked' if mode != 'stock' else 'allowed', 'no Polari stack or isle app binds host /etc (audit: no such mounts); stock = if someone did'),
        _step('linux-dac', 'allowed', 'uid 0 in the container is uid 0 on the host: owner of the file'),
        _step('userns', 'blocked' if mode == 'enforce' else 'n/a', 'with the remap uid 0 is an unprivileged host uid (D1) — rendered, not applied'),
        _step('polari-apparmor', 'allowed', 'a path-based profile cannot tell a bind from the image (measured 2026-09-12)')],
        'the one thing AppArmor cannot do: DAC (user-namespace remap) is the ring for this')
    edge('docker-socket', 'connect /var/run/docker.sock', [
        _step('mount-policy', 'blocked' if mode != 'stock' else 'allowed', 'not mounted into any Polari container; stock = if mounted'),
        _step('linux-dac', 'allowed', 'root:docker 0660 — uid 0 may'),
        _step('userns', 'blocked' if mode == 'enforce' else 'n/a', 'remapped uid 0 is not root, not in docker'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'the socket\'s path is "disconnected" and denied under enforce')],
        'never mount the socket: that is the control; the audit checks it')
    edge('devices', 'open /dev/ttyUSB0, /dev/video0, /dev/kvm', [
        _step('device-acl', 'allowed' if kind == 'hardware-extension' else 'blocked', 'only --device entries; hardware extensions get what the hardware map assigns'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'deny /dev/{tty,video,bus,…}* unless hardware-extension')],
        'a plain container sees no devices; a hardware extension sees exactly its assigned ones (isle route only)')
    raw_stock = 'allowed' if 'NET_RAW' in caps or kind in ('gateway', 'vpn-gateway') or mode == 'stock' else 'allowed'
    edge('kernel', 'open a raw socket (sniff / forge packets)', [
        _step('docker-caps', raw_stock, 'CAP_NET_RAW is in docker\'s default set'),
        _step('polari-surface', ('allowed' if kind in ('gateway', 'vpn-gateway') else 'blocked') if surface_on else 'n/a', 'cap_drop ALL; gateways add it back'),
        _step('polari-apparmor', ('allowed' if kind in ('gateway', 'vpn-gateway') else _polari(mode, applied, 'polari-apparmor')), 'deny network raw for non-gateway kinds (enforce)')],
        'ALLOWED by stock docker for every container; Polari removes it except for gateways')
    edge('kernel', 'chroot', [
        _step('docker-caps', 'allowed', 'CAP_SYS_CHROOT is in the default set'),
        _step('polari-surface', 'blocked' if surface_on else 'n/a', 'cap_drop ALL'),
        _step('polari-apparmor', _polari(mode, applied, 'polari-apparmor'), 'capability sys_chroot is not in the allow-list')],
        'stock allows; Polari\'s rings remove the capability')
    return E


def os_view(sc, mode, applied):
    nodes = [{'node': p['name'], 'kind': 'process', 'layer': 0, 'title': p['name'], 'description': f"{p['profile']} container; caps {','.join(p.get('capabilities') or []) or 'none'}; writable {', '.join(p.get('writable') or []) or 'none'}"}
             for p in sc['fixed']]
    procs = list(sc['fixed'])
    if sc['apps_run'] == 'in-core':
        core = next((p for p in sc['fixed'] if p['name'] == 'prf-backend'), None)
        nodes.append({'node': 'a module', 'kind': 'process', 'layer': 0, 'title': 'a module (inside prf-backend)',
                      'description': 'modules are not containers on the swarm: same process, same profile, same rings as the backend'})
    else:
        nodes.append({'node': 'an app', 'kind': 'process', 'layer': 0, 'title': 'an app (its own container)',
                      'description': 'started by the agent from its manifest; its own profile and seccomp list through the compose fragment'})
        procs.append({'name': 'an app', 'profile': 'web-app', 'capabilities': [], 'writable': ['/data']})
        if sc.get('hardware'):
            nodes.append({'node': 'a hardware extension', 'kind': 'process', 'layer': 0, 'title': 'a hardware extension container', 'description': 'kind hardware-extension: sees exactly the devices the hardware map assigned'})
            procs.append({'name': 'a hardware extension', 'profile': 'hardware-extension', 'capabilities': [], 'writable': ['/data']})
    if sc.get('guests'):
        nodes.append({'node': 'a guest', 'kind': 'guest', 'layer': 0, 'title': 'a KVM guest (a hardware app, the router)', 'description': 'its own kernel under qemu; sVirt profile per VM; VFIO for assigned hardware'})
    for n, k, t in OS_TARGETS:
        nodes.append({'node': n, 'kind': k, 'layer': 2, 'title': t, 'description': ''})
    for s in ('linux-dac', 'docker-caps', 'docker-masks', 'docker-seccomp', 'docker-apparmor', 'device-acl', 'mount-policy', 'userns', 'polari-surface', 'polari-apparmor', 'polari-seccomp') + (('hypervisor', 'svirt', 'qemu-user', 'vfio') if sc.get('guests') else ()):
        nodes.append({'node': s, 'kind': 'boundary', 'layer': 1, 'title': SYSTEMS[s]['title'], 'description': SYSTEMS[s]['note'], 'system': s})
    edges = []
    for p in procs:
        if sc['apps_run'] == 'in-core' and p['name'] == 'prf-backend':
            pass
        edges += _os_process_edges(p, sc, mode, applied)
    if sc['apps_run'] == 'in-core':
        edges.append({'source': 'a module', 'target': 'prf-backend', 'means': 'runs inside', 'chain': [_step('polari-apparmor', 'allowed', 'the module\'s stanza folds into the backend\'s profile')],
                      'verdict': 'allowed', 'decided_by': 'polari-apparmor', 'provenance': 'polari', 'why': 'on the swarm a module IS the backend process: whatever the backend may touch, the module may'})
    # someone with the machine in their hands (his ask 2026-09-13): a thief, a repair shop, a curious visitor —
    # the one actor no container ring touches; Secure Boot and disk encryption exist for them
    phys = sc.get('physical') or {}
    sb_on = bool(phys.get('secure_boot', True)); enc_on = bool(phys.get('disk_encryption', False)) or (mode == 'enforce' and not phys.get('headless'))
    nodes.append({'node': 'physical access', 'kind': 'actor', 'layer': 0, 'title': 'someone with the machine in their hands',
                  'description': 'a thief, a repair shop, anyone who can boot it or pull the drive; no container ring applies to them'})
    nodes.append({'node': 'the disk', 'kind': 'target', 'layer': 2, 'title': "the disk's contents (data at rest)", 'description': ''})
    for s_ in ('secure-boot', 'disk-encryption'):
        nodes.append({'node': s_, 'kind': 'boundary', 'layer': 1, 'title': SYSTEMS[s_]['title'], 'description': SYSTEMS[s_]['note'], 'system': s_})
    for target, means, chain, why in (
        ('the disk', 'pull the drive and read it in another machine', [
            _step('disk-encryption', 'blocked' if enc_on else 'allowed', 'LUKS: unreadable without the passphrase' if enc_on else 'not enabled on this profile: every file is readable')],
         'the ONLY thing that protects data on a drive that leaves the machine; it is a build-time option (headless boxes cannot have it — nobody types the passphrase)'),
        ('the disk', 'boot a live USB and read the files', [
            _step('secure-boot', 'allowed', 'a signed live USB boots fine — Secure Boot is not what stops this'),
            _step('disk-encryption', 'blocked' if enc_on else 'allowed', 'the encrypted disk is unreadable from the USB too' if enc_on else 'every file readable')],
         'Secure Boot does not protect the data; only encryption does'),
        ('kernel', 'replace the boot loader or kernel on the disk with a tampered one', [
            _step('secure-boot', 'blocked' if sb_on else 'allowed', 'the firmware refuses an unsigned boot chain' if sb_on else 'turned off for this profile (a written reason exists): a tampered kernel would start'),
            _step('disk-encryption', 'blocked' if enc_on else 'allowed', 'the disk cannot be modified without the passphrase either' if enc_on else '')],
         'the boot path is Secure Boot\'s job; encryption guards it a second time'),
    ):
        v, by, prov = _verdict(chain)
        edges.append({'source': 'physical access', 'target': target, 'means': means, 'chain': chain, 'verdict': v, 'decided_by': by, 'provenance': prov, 'why': why})
    if sc.get('guests'):
        for target, means, chain, why in (
            ('kernel', 'escape the hypervisor', [_step('hypervisor', 'blocked', 'a guest kernel is not the host kernel'), _step('qemu-user', 'blocked', 'qemu runs unprivileged'), _step('svirt', 'blocked', 'libvirt-<uuid> profile per guest — libvirt\'s default on Ubuntu, enforcing on the isle')], 'three qemu/libvirt layers; Polari only requires sVirt to be on'),
            ('devices', 'use real hardware', [_step('vfio', 'allowed', 'only the device the hardware map assigned'), _step('svirt', 'blocked', 'nothing else')], 'the isle\'s way to hardware: one assigned device through VFIO'),
            ('other-container', 'reach an isle app', [_step('router-zone', 'allowed', 'through the router VM\'s zones and the agent'), _step('agent-door', 'allowed', 'by .isle name through the agent')], 'a guest talks to apps like any isle member: through the network, never the host'),
        ):
            v, by, prov = _verdict(chain)
            edges.append({'source': 'a guest', 'target': target, 'means': means, 'chain': chain, 'verdict': v, 'decided_by': by, 'provenance': prov, 'why': why})
    return nodes, edges


# ------------------------------------------------------------------ the network view
def network_view(sc, mode, applied):
    route = sc['route']
    nets = [('internet', 'the internet'), ('home-lan', 'the home / admin LAN')]
    if route == 'isle':
        nets += [('isle-vlan', 'the isle VLAN (router VM)'), ('isle-agent-net', 'isle-agent-net (containers behind the agent)')]
    else:
        nets += [('overlay', 'the swarm overlay (encrypted)'), ('other-node', 'another swarm node')]
    nodes = [{'node': n, 'kind': 'network', 'layer': 0, 'title': t, 'description': ''} for n, t in nets]
    services = [('sshd', 'sshd :22 (all interfaces)'), ('docker-api', 'docker API (unix socket only)'), ('libvirtd', 'libvirtd :16509'), ('swarm-ports', 'swarm 2377/7946/4789')]
    if route != 'isle':
        services.append(('jenkins', 'Jenkins :8080 (127.0.0.1)'))
    nodes += [{'node': n, 'kind': 'service', 'layer': 2, 'title': t, 'description': 'a host service'} for n, t in services]
    for p in sc['fixed']:
        nodes.append({'node': p['name'], 'kind': 'process', 'layer': 2, 'title': f"{p['name']} :{','.join(map(str, p.get('ports') or []))}", 'description': 'a listening container'})
    for s in ('docker-bridge', 'docker-user', 'ufw', 'overlay-ipsec', 'proxy-tls') + (('agent-door', 'router-zone') if route == 'isle' else ()):
        nodes.append({'node': s, 'kind': 'boundary', 'layer': 1, 'title': SYSTEMS[s]['title'], 'description': SYSTEMS[s]['note'], 'system': s})
    E = []

    def edge(src, target, means, chain, why):
        v, by, prov = _verdict(chain)
        E.append({'source': src, 'target': target, 'means': means, 'chain': chain, 'verdict': v, 'decided_by': by, 'provenance': prov, 'why': why})

    ufw = lambda ok, note: _step('ufw', ('allowed' if ok else 'blocked') if (mode == 'enforce') else 'n/a', note + (' — rendered, not applied' if mode != 'enforce' else ''))  # noqa: E731
    du = lambda ok, note: _step('docker-user', ('allowed' if ok else 'blocked') if (mode == 'enforce') else 'n/a', note + (' — rendered, not applied' if mode != 'enforce' else ''))  # noqa: E731
    edge_name = 'isle-agent' if route == 'isle' else 'pol-proxy'
    if route == 'isle':
        edge('home-lan', edge_name, 'HTTPS by .isle name', [_step('router-zone', 'allowed', 'the isle side'), ufw(True, '80/443 from the isle side'), _step('agent-door', 'allowed', 'TLS with the isle CA leaf')], 'the only way into an isle app')
        edge('internet', edge_name, 'an exposed door (isle url expose)', [_step('router-zone', 'allowed', 'a published port'), _step('agent-door', 'allowed', 'basic auth over PLAIN HTTP on the outside leg (reported to isle-core)')], 'works, but the credential travels unencrypted: use only across a VPN until the door terminates TLS')
    else:
        edge('internet', edge_name, 'HTTPS 443 (and 80 for ACME + redirect)', [ufw(True, '80/443 to anyone'), _step('proxy-tls', 'allowed', 'TLS 1.2+, hardened headers, rate limits; Let\'s Encrypt when public')], 'the edge; live on the server route')
    edge('internet', 'sshd', 'ssh', [_step('ssh-keys', 'allowed', 'key login; sshd on all interfaces'), ufw(False, 'only from the admin/isle LAN under the rendered rules')], 'today reachable from anywhere a route exists (finding); the firewall ring closes it')
    edge('internet', 'sshd', 'guess a password over ssh', [_step('ssh-keys', 'allowed' if (sc.get('ssh') or {}).get('password_auth', True) else 'blocked', 'PasswordAuthentication yes on the isle core (inventory 2026-09-13); keys-only closes this' if (sc.get('ssh') or {}).get('password_auth', True) else 'keys only'), ufw(False, 'and only from the admin LAN')],
         'passwords are the guessable vector: PasswordAuthentication no + keys only is the fix; fail2ban / ufw limit slows the guessing meanwhile')
    edge('internet', 'swarm-ports', 'swarm management / gossip / VXLAN', [ufw(False, 'peers only under the rendered rules')], 'today open on pol-core (finding); the firewall ring closes it to peers' if route == 'swarm' else 'not a swarm node role here')
    edge('internet', 'docker-api', 'docker TCP API', [_step('docker-bridge', 'blocked', 'no TCP socket; unix socket only (audit pass)')], 'not exposed')
    if route != 'isle':
        edge('internet', 'jenkins', 'HTTP 8080', [_step('docker-bridge', 'blocked', 'published on 127.0.0.1 only')], 'local only')
    for p in sc['fixed']:
        for svc, note in (('sshd', 'no reason for a container to reach ssh'), ('docker-api', 'the socket is not TCP; the unix socket is not mounted'), ('libvirtd', 'guests are the host\'s business, never a container\'s'), ('swarm-ports', 'containers do not manage the swarm')):
            edge(p['name'], svc, 'connect to a host service', [_step('docker-bridge', 'allowed' if svc != 'docker-api' else 'blocked', 'the host is reachable at the bridge gateway' if svc != 'docker-api' else 'no TCP socket'), du(False, note)], 'ALLOWED by stock docker: containers reach the host\'s services; DOCKER-USER denies all but DNS' if svc != 'docker-api' else 'not reachable')
        if route == 'isle':
            edge(p['name'], 'isle-agent', 'reach the agent (DNS, ingress)', [du(True, 'DNS + the agent\'s 80/443 are the allowed exceptions')], 'the agent is how apps find and reach each other')
    others = [q['name'] for q in sc['fixed']]
    if len(others) > 1:
        edge(others[-1], others[0], 'talk directly to another container on the same network', [_step('docker-bridge', 'allowed', 'icc on the shared network'), _step('proxy-tls' if route != 'isle' else 'agent-door', 'allowed', 'the intended path is through the proxy/agent')], 'stock docker lets containers on one network talk; the scenario renders icc=false so only the proxy/agent path stays (daemon.json, diffed only)')
    if route != 'isle':
        edge('other-node', 'overlay', 'service traffic between nodes', [_step('overlay-ipsec', 'allowed', 'encrypted=true on every stack overlay (audit pass)')], 'protected in transit; live today')
    return nodes, E


# ------------------------------------------------------------------ the app (access) view
def app_view(sc, mode, applied):
    auth = sc.get('auth')
    actors = [('visitor', 'an anonymous visitor (a browser)'), ('user', 'a logged-in user (Keycloak role)'), ('owner', 'the owner (sudo on the host)'),
              ('remote-member', 'a polari-remote member (ssh)'), ('app-member', 'a polari-app member (the store\'s doors)'), ('docker-member', 'a docker-group member'),
              ('an-app', 'an app\'s own process'), ('another-app', 'another app')]
    if sc.get('guests'):
        actors.append(('a-guest', 'a guest (a hardware app)'))
    means = [('browser-https', 'HTTPS + (full) OIDC bearer token'), ('ssh', 'ssh key login'), ('sudo', 'sudo / a sudoers drop-in'), ('docker-socket', 'the docker socket'), ('pkexec', 'pkexec consent'), ('isle-cli', 'the isle CLI')]
    resources = [('api', 'the Polari API (CRUDE on every class)'), ('data', 'the data (sqlite / MariaDB / MinIO)'), ('downloads', 'the download / apps pages'), ('host', 'the host OS'), ('containers', 'the containers'), ('guests', 'the guests / hardware')]
    nodes = [{'node': n, 'kind': 'actor', 'layer': 0, 'title': t, 'description': ''} for n, t in actors]
    nodes += [{'node': n, 'kind': 'means', 'layer': 1, 'title': t, 'description': ''} for n, t in means]
    nodes += [{'node': n, 'kind': 'resource', 'layer': 3, 'title': t, 'description': ''} for n, t in resources]
    for s in ('keycloak', 'access-control', 'sudoers', 'docker-group', 'polkit', 'ssh-keys') + (('agent-door',) if sc['route'] == 'isle' else ()):
        nodes.append({'node': s, 'kind': 'boundary', 'layer': 2, 'title': SYSTEMS[s]['title'], 'description': SYSTEMS[s]['note'], 'system': s})
    E = []

    def edge(src, target, means_, chain, why):
        v, by, prov = _verdict(chain)
        E.append({'source': src, 'target': target, 'means': means_, 'chain': chain, 'verdict': v, 'decided_by': by, 'provenance': prov, 'why': why})

    if auth == 'keycloak':
        edge('visitor', 'api', 'call the API without a token', [_step('keycloak', 'blocked', 'the API requires a bearer token')], 'logins on: anonymous calls are refused')
        edge('user', 'api', 'call the API with a token, per role', [_step('keycloak', 'allowed', 'a signed OIDC token — asymmetric, no shared secret in the browser'), _step('access-control', 'allowed', 'CRUDE per class and role — the authority')], 'what a user may do is the accessControl rules\' answer')
    elif auth == 'none':
        edge('visitor', 'api', 'call the API (no logins on this profile)', [_step('keycloak', 'allowed', 'absent by decision D2 (lean: a distribution point) / dev'), _step('access-control', 'allowed', 'no identity to rule on')], 'OPEN: on the lean profile every visitor may call the API; acceptable only for a demonstration/distribution point with no private data')
    else:
        edge('visitor', 'api', 'call the API by .isle name', [_step('agent-door', 'allowed', 'reachable only from the isle side or a door'), _step('access-control', 'allowed', 'isle groups')], 'the isle\'s network IS the login boundary today')
    edge('visitor', 'downloads', 'read the download pages', [_step('proxy-tls' if sc['route'] != 'isle' else 'agent-door', 'allowed', 'public by design')], 'public')
    edge('user', 'data', 'read/write rows through the API', [_step('access-control', 'allowed', 'per class, per role')], 'never the database directly')
    edge('owner', 'host', 'sudo', [_step('ssh-keys', 'allowed', 'key login'), _step('sudoers', 'allowed', 'the owner\'s own sudo membership')], 'the owner is root when they choose')
    edge('remote-member', 'host', 'the polari-remote verbs only (install, swarm, AI setup)', [_step('ssh-keys', 'allowed'), _step('sudoers', 'allowed' if mode == 'enforce' else 'blocked', 'polari-remote drop-in — installed on no machine yet (pol deploy grant)')], 'a narrow, listed set of commands; today the owner\'s sudo stands in')
    edge('app-member', 'host', 'the store\'s doors (pkexec)', [_step('polkit', 'allowed', 'a desktop consent dialog'), _step('sudoers', 'allowed' if mode == 'enforce' else 'blocked', 'polari-app drop-in — not installed yet')], 'the manager app asks for consent per action')
    edge('docker-member', 'host', 'docker run --privileged, or mount /', [_step('docker-group', 'allowed', 'the socket is root-equivalent (stock docker)')], 'ALLOWED and unavoidable: keep the docker group to the operator; Polari never adds a service user to it')
    edge('an-app', 'api', 'call another app\'s API', [_step('proxy-tls' if sc['route'] != 'isle' else 'agent-door', 'allowed', 'through the proxy/agent by name'), _step('keycloak', 'allowed' if auth == 'keycloak' else 'n/a', 'app↔app channels use symmetric material (shared secret / mTLS session) — TrustChannel rows, sec-i-2')], 'apps talk through the front door, never container-to-container')
    edge('an-app', 'host', 'become root on the host', [_step('docker-caps', 'blocked', 'no SYS_ADMIN'), _step('mount-policy', 'blocked' if mode != 'stock' else 'allowed', 'no socket mounted'), _step('userns', 'blocked' if mode == 'enforce' else 'n/a', 'D1')], 'the os view\'s question, seen from access: the app has no means')
    if sc.get('guests'):
        edge('a-guest', 'guests', 'use its assigned hardware', [_step('vfio', 'allowed', 'the assigned device only')], 'the app route\'s hardware path')
        edge('a-guest', 'host', 'reach the host', [_step('hypervisor', 'blocked'), _step('svirt', 'blocked')], 'no means')
    edge('owner', 'guests', 'virsh / the isle CLI', [_step('polkit', 'allowed', 'libvirt group or sudo'), _step('sudoers', 'allowed')], 'the owner manages guests; apps never do')
    return nodes, E


BUILDERS = {'os': os_view, 'network': network_view, 'app': app_view}


def build(view, scenario, mode='today'):
    if view not in VIEWS:
        raise ValueError(f'view must be one of {VIEWS}')
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES}')
    sc = load_scenario(scenario)
    if sc is None:
        raise ValueError(f'unknown scenario {scenario!r}')
    applied = APPLIED_TODAY.get(scenario, {}) if mode == 'today' else {}
    nodes, edges = BUILDERS[view](sc, mode, applied)
    counts = {'allowed': 0, 'logged': 0, 'blocked': 0}
    for e in edges:
        counts[e['verdict']] += 1
    layers = sorted({n['layer'] for n in nodes})
    legend = {'stock': 'docker / the kernel give this to every container', 'qemu': 'libvirt / qemu give this to every guest', 'polari': 'Polari renders or configures this'}
    return {'view': view, 'scenario': scenario, 'route': sc['route'], 'mode': mode, 'title': sc['title'], 'description': sc['description'],
            'mac_attach': sc['mac_attach'], 'apps_run': sc['apps_run'], 'scenario_source': sc.get('source', ''),
            'counts': counts, 'layers': layers, 'nodes': nodes, 'edges': edges, 'legend': legend,
            'summary': [{'source': e['source'], 'means': e['means'], 'target': e['target'], 'verdict': e['verdict'],
                         'decided_by': e['decided_by'], 'provenance': e['provenance'], 'why': e['why']} for e in edges]}


def simulate(view, scenario, actor, mode='today'):
    """Everything one actor can reach in a view, hop by hop, with the deciding system named."""
    g = build(view, scenario, mode)
    steps = []
    for e in g['edges']:
        if e['source'] != actor:
            continue
        steps.append({'target': e['target'], 'means': e['means'], 'verdict': e['verdict'], 'decided_by': e['decided_by'], 'provenance': e['provenance'],
                      'chain': ' → '.join(f"{s['system']}:{s['decision']}" for s in e['chain'] if s['decision'] != 'n/a'), 'why': e['why']})
    actors = sorted({e['source'] for e in g['edges']})
    if actor not in actors:
        return {'ok': False, 'view': view, 'scenario': scenario, 'mode': mode, 'actor': actor, 'error': f'no such actor in this view; one of {actors}', 'actors': actors}
    reach = {'allowed': [s['target'] for s in steps if s['verdict'] == 'allowed'], 'logged': [s['target'] for s in steps if s['verdict'] == 'logged'], 'blocked': [s['target'] for s in steps if s['verdict'] == 'blocked']}
    return {'ok': True, 'view': view, 'scenario': scenario, 'mode': mode, 'actor': actor, 'actors': actors, 'reach': reach, 'steps': steps,
            'reading': f"{actor} on {scenario} ({mode}): {len(reach['allowed'])} reach(es) allowed, {len(reach['logged'])} logged (would be denied under enforce), {len(reach['blocked'])} blocked"}


ROLE_OF = {'prf-backend': 'the Polari backend', 'prf-isle-backend': 'the Polari backend', 'psc-backend': 'a backend', 'pol-proxy': 'the edge proxy',
           'isle-agent': 'the isle agent', 'isle-gateway': 'the isle gateway', 'isle-remote-agent': 'the remote agent', 'pol-hub': 'a static frontend',
           'prf-frontend': 'a static frontend', 'prf-isle-frontend': 'a static frontend', 'psc-frontend': 'a static frontend', 'isle-apt': 'a static frontend',
           'pol-keycloak': 'a service', 'pol-mariadb': 'a service', 'pol-file-store': 'a service', 'psc-redis': 'a service'}


def compare(view, mode='today'):
    """The same view across every scenario: one row per (source role, means, target) with each scenario's
    verdict(s). Sources are compared by ROLE (the Polari backend is prf-backend on the swarm and
    prf-isle-backend on the isle) so a row lines up across routes."""
    from security.custom.security_facts import scenario_names
    rows = {}
    names = scenario_names()
    for scn in names:
        try:
            g = build(view, scn, mode)
        except ValueError:
            continue
        for e in g['edges']:
            role = ROLE_OF.get(e['source'], e['source'])
            key = (role, e['means'], e['target'])
            row = rows.setdefault(key, {'source': role, 'means': e['means'], 'target': e['target']})
            cell = f"{e['verdict']} ({e['decided_by']})"
            row[scn] = cell if not row.get(scn) or row[scn] == cell else row[scn] + ' / ' + cell
    for r in rows.values():
        for scn in names:
            r.setdefault(scn, '—')
    return {'view': view, 'mode': mode, 'scenarios': names, 'rows': list(rows.values())}
