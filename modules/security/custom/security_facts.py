"""
@module security.custom.security_facts

What already protects a process BEFORE Polari adds anything (stock docker, the
kernel, qemu/libvirt), the systems Polari adds, and the scenarios. Every
system has a provenance so a view can say "docker gives you this already" vs
"Polari renders this" vs "qemu gives every guest this". Facts are cited to the
docker/moby and libvirt defaults as they ship on Ubuntu 24.04 (docker 27–29).
"""
import glob
import os

SUITE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
SCENARIO_DIR = os.path.join(SUITE, 'os-security', 'scenarios')

# ---- the systems (a boundary a reach attempt passes through) -----------------------------------
# provenance: stock = docker/the kernel, for every container, no Polari action needed
#             qemu  = libvirt/qemu, for every guest
#             polari = rendered by os-security / the proxy / the isle agent / Keycloak wiring
SYSTEMS = {
    'linux-dac':      {'title': 'Linux DAC (uid/gid, file modes)', 'provenance': 'stock', 'domain': 'os', 'area': 'dac',
                       'note': 'root inside a container is root on the host unless user namespaces remap it'},
    'docker-caps':    {'title': 'docker default capabilities', 'provenance': 'stock', 'domain': 'os', 'area': 'dac',
                       'note': '14 caps kept (CHOWN DAC_OVERRIDE FSETID FOWNER MKNOD NET_RAW SETGID SETUID SETFCAP SETPCAP NET_BIND_SERVICE SYS_CHROOT KILL AUDIT_WRITE); no SYS_ADMIN, SYS_MODULE, SYS_PTRACE, SYS_RAWIO, NET_ADMIN'},
    'docker-masks':   {'title': 'docker masked and read-only paths', 'provenance': 'stock', 'domain': 'os', 'area': 'mac',
                       'note': '/proc/kcore, /proc/keys, /proc/sysrq-trigger, /proc/sys, /sys/firmware, /sys/devices/virtual/powercap masked or read-only in every container'},
    'docker-seccomp': {'title': 'docker builtin seccomp profile', 'provenance': 'stock', 'domain': 'os', 'area': 'mac',
                       'note': 'blocks mount, umount2, pivot_root, ptrace (without CAP_SYS_PTRACE), keyctl, add_key, bpf, perf_event_open, *_module, kexec, reboot, swapon, setns/unshare of a user namespace, open_by_handle_at, userfaultfd, iopl/ioperm, settimeofday, acct …'},
    'docker-apparmor': {'title': 'docker-default AppArmor profile', 'provenance': 'stock', 'domain': 'os', 'area': 'mac',
                        'note': 'file, network and capabilities allowed; explicit denies on /proc and /sys writes, mount, sysrq, kcore, firmware, powercap, kernel/security'},
    'device-acl':     {'title': 'cgroup device allow-list', 'provenance': 'stock', 'domain': 'os', 'area': 'dac',
                       'note': 'a container opens only /dev/null, zero, random, urandom, tty, console, ptmx and what --device adds'},
    'docker-bridge':  {'title': 'docker network isolation', 'provenance': 'stock', 'domain': 'network', 'area': 'firewall',
                       'note': 'containers on the same network reach each other (icc); other networks are isolated; the host is reachable at the gateway; DOCKER-USER starts empty'},
    'docker-group':   {'title': 'the docker group / socket', 'provenance': 'stock', 'domain': 'app', 'area': 'authorization',
                       'note': 'membership of the docker group is root-equivalent on the host'},
    'userns':         {'title': 'user-namespace remap', 'provenance': 'polari', 'domain': 'os', 'area': 'dac',
                       'note': 'container uid 0 becomes an unprivileged host uid; rendered into daemon.json and diffed only (decision D1)'},
    'polari-surface': {'title': 'the app surface ring (cap_drop ALL, declared cap_add, read-only root, tmpfs, pid limit)', 'provenance': 'polari', 'domain': 'os', 'area': 'dac',
                       'note': 'rendered as a compose fragment (isle: applied by the agent at install; swarm: the stack overlay) — applied nowhere yet'},
    'polari-apparmor': {'title': 'Polari AppArmor profile (per app, or the node-wide union on swarm)', 'provenance': 'polari', 'domain': 'os', 'area': 'mac',
                        'note': 'an allow-list; complain keeps docker\'s stock denies and logs the rest; enforce adds Polari\'s denies'},
    'polari-seccomp': {'title': 'Polari seccomp list (per kind)', 'provenance': 'polari', 'domain': 'os', 'area': 'mac',
                       'note': 'complain = SCMP_ACT_LOG (permit + log); enforce = ERRNO; attaches per container (isle) or daemon-wide (swarm)'},
    'mount-policy':   {'title': 'what is mounted into the container', 'provenance': 'polari', 'domain': 'os', 'area': 'dac',
                       'note': 'no docker.sock, no libvirt socket, no host /etc in any Polari stack or isle app (the audit checks)'},
    'docker-user':    {'title': 'DOCKER-USER chain', 'provenance': 'polari', 'domain': 'network', 'area': 'firewall',
                       'note': 'containers may reach the host only for DNS (and the agent on the isle); 22, docker, libvirt, swarm ports denied — rendered, printed unless --enforce'},
    'ufw':            {'title': 'ufw host firewall', 'provenance': 'polari', 'domain': 'network', 'area': 'firewall',
                       'note': 'default deny incoming; 22 from the admin/isle LAN; 80/443 to anyone (server) or the isle side; swarm ports from peers — rendered, printed unless --enforce'},
    'overlay-ipsec':  {'title': 'encrypted swarm overlays', 'provenance': 'polari', 'domain': 'network', 'area': 'tls',
                       'note': 'every stack overlay carries encrypted=true (IPsec between nodes) — live'},
    'proxy-tls':      {'title': 'the edge proxy (TLS, headers, rate limits)', 'provenance': 'polari', 'domain': 'network', 'area': 'proxy',
                       'note': 'nginx templates hardened; Let\'s Encrypt or the suite CA; HSTS once public — live on the server route'},
    'agent-door':     {'title': 'isle agent ingress and doors', 'provenance': 'polari', 'domain': 'network', 'area': 'exposure',
                       'note': 'apps reached only through the agent by .isle name (isle CA leaf); an exposed door speaks plain HTTP with basic auth on its outside leg (reported)'},
    'router-zone':    {'title': 'the router VM\'s firewall zones (OpenWrt)', 'provenance': 'polari', 'domain': 'network', 'area': 'firewall',
                       'note': 'the isle VLAN, the home LAN and the internet are zones on the router guest; isle-core\'s half'},
    'svirt':          {'title': 'sVirt (libvirt AppArmor per guest)', 'provenance': 'qemu', 'domain': 'os', 'area': 'mac',
                       'note': 'every qemu process runs under libvirt-<uuid>: only its own disk, its own devices, no other guest\'s'},
    'qemu-user':      {'title': 'qemu as an unprivileged user', 'provenance': 'qemu', 'domain': 'os', 'area': 'dac',
                       'note': 'libvirt runs qemu as libvirt-qemu; a guest escape lands as that user, not root'},
    'hypervisor':     {'title': 'the KVM/qemu boundary', 'provenance': 'qemu', 'domain': 'os', 'area': 'mac',
                       'note': 'a guest kernel is not the host kernel; devices are virtio, passthrough only through VFIO for what the hardware map assigns'},
    'vfio':           {'title': 'VFIO passthrough', 'provenance': 'qemu', 'domain': 'os', 'area': 'hardware',
                       'note': 'the one way a guest touches real hardware: the device the hardware map assigned, nothing else'},
    'keycloak':       {'title': 'Keycloak (OIDC)', 'provenance': 'polari', 'domain': 'app', 'area': 'authentication',
                       'note': 'the full profile: users log in, the API checks bearer tokens; the lean profile has NO logins (D2) — the API is open'},
    'access-control': {'title': 'accessControl rules (the authority for who may call what)', 'provenance': 'polari', 'domain': 'app', 'area': 'authorization',
                       'note': 'CRUDE verbs per class and role; the security module only views them'},
    'sudoers':        {'title': 'sudoers drop-ins (polari-remote, polari-app)', 'provenance': 'polari', 'domain': 'app', 'area': 'authorization',
                       'note': 'two narrow groups: remote setup over ssh; the store\'s doors — installed by pol deploy grant; today on no machine'},
    'polkit':         {'title': 'polkit / pkexec', 'provenance': 'stock', 'domain': 'app', 'area': 'authorization',
                       'note': 'the desktop consent dialog the manager app uses for trust and hardware trials'},
    'secure-boot':    {'title': 'Secure Boot (the firmware runs only a signed boot chain)', 'provenance': 'stock', 'domain': 'os', 'area': 'boot',
                       'note': 'Ubuntu\'s shim + kernel are signed with the key every PC trusts; a tampered boot loader or kernel on the disk does not start. ON by default; turned off only deliberately at ISO build with a written reason (POLARI_ISO_PLAN D6). Protects the boot path only.'},
    'disk-encryption': {'title': 'disk encryption at rest (LUKS)', 'provenance': 'polari', 'domain': 'os', 'area': 'at-rest',
                        'note': 'the disk is unreadable without the passphrase typed at start-up — the one protection against someone who takes the drive or the machine. An OPTION, off by default; never on headless (ISO plan D8).'},
    'ssh-keys':       {'title': 'ssh public-key login', 'provenance': 'stock', 'domain': 'app', 'area': 'authentication',
                       'note': 'passwordless between the home machines; sshd listens on all interfaces (finding)'},
}

# ---- the scenarios (fallback when os-security/scenarios/*.yml is not beside the checkout) -----
FIXED = {
    'isle': [
        {'name': 'isle-agent', 'profile': 'gateway', 'network': ['isle'], 'capabilities': ['NET_BIND_SERVICE'], 'ports': [80, 443], 'writable': ['/etc/nginx/configs', '/var/log/nginx']},
        {'name': 'isle-gateway', 'profile': 'gateway', 'network': ['isle', 'internet'], 'capabilities': ['NET_BIND_SERVICE'], 'ports': [80], 'writable': []},
        {'name': 'prf-isle-backend', 'profile': 'web-app', 'network': ['isle'], 'capabilities': [], 'ports': [3000, 3001], 'writable': ['/data', '/app/data']},
        {'name': 'prf-isle-frontend', 'profile': 'web-app', 'network': ['isle'], 'capabilities': [], 'ports': [4200], 'writable': []},
        {'name': 'isle-apt', 'profile': 'web-app', 'network': ['isle'], 'capabilities': [], 'ports': [80], 'writable': []},
        {'name': 'isle-remote-agent', 'profile': 'gateway', 'network': ['isle'], 'capabilities': ['NET_BIND_SERVICE', 'NET_ADMIN'], 'ports': [80, 443], 'writable': ['/etc/nginx/configs', '/var/log/nginx']},
    ],
    'swarm-lean': [
        {'name': 'pol-proxy', 'profile': 'gateway', 'network': ['isle', 'internet'], 'capabilities': ['NET_BIND_SERVICE', 'CHOWN', 'SETUID', 'SETGID'], 'ports': [80, 443], 'writable': ['/var/cache/nginx', '/var/run']},
        {'name': 'pol-hub', 'profile': 'web-app', 'network': ['isle'], 'capabilities': ['CHOWN', 'SETUID', 'SETGID'], 'ports': [4200], 'writable': ['/var/cache/nginx', '/var/run']},
        {'name': 'prf-frontend', 'profile': 'web-app', 'network': ['isle'], 'capabilities': ['CHOWN', 'SETUID', 'SETGID'], 'ports': [4200], 'writable': ['/var/cache/nginx', '/var/run']},
        {'name': 'prf-backend', 'profile': 'worker', 'network': ['isle', 'internet'], 'capabilities': [], 'ports': [3000, 3001], 'writable': ['/app/data', '/tmp']},
    ],
    'dev': [],
}
FIXED['swarm-full'] = FIXED['swarm-lean'] + [
    {'name': 'psc-frontend', 'profile': 'web-app', 'network': ['isle'], 'capabilities': ['CHOWN', 'SETUID', 'SETGID'], 'ports': [4200], 'writable': ['/var/cache/nginx', '/var/run']},
    {'name': 'psc-backend', 'profile': 'worker', 'network': ['isle'], 'capabilities': [], 'ports': [8080], 'writable': ['/tmp']},
    {'name': 'pol-keycloak', 'profile': 'worker', 'network': ['isle'], 'capabilities': [], 'ports': [8080, 8443], 'writable': ['/opt/keycloak/data', '/tmp']},
    {'name': 'pol-mariadb', 'profile': 'worker', 'network': ['isle'], 'capabilities': ['CHOWN', 'SETUID', 'SETGID', 'DAC_READ_SEARCH'], 'ports': [3306], 'writable': ['/var/lib/mysql', '/run/mysqld', '/tmp']},
    {'name': 'pol-file-store', 'profile': 'worker', 'network': ['isle'], 'capabilities': [], 'ports': [9000, 9001], 'writable': ['/data', '/tmp']},
    {'name': 'psc-redis', 'profile': 'worker', 'network': ['isle'], 'capabilities': [], 'ports': [6379], 'writable': ['/data']},
]

SCENARIOS = {
    'isle':       {'route': 'isle', 'ssh': {'password_auth': True, 'permit_root': 'without-password'}, 'physical': {'secure_boot': True, 'disk_encryption': False, 'headless': False}, 'title': 'An isle (the app route: debs, KVM guests, hardware)', 'rings': 'surface,dac,mac,network,host',
                   'mac_attach': 'security_opt', 'apps_run': 'containers', 'guests': True, 'hardware': True, 'auth': 'isle-groups',
                   'description': 'Every app is its own plain container started by the agent; hardware apps run in KVM guests under sVirt with VFIO passthrough of what the hardware map assigns; ingress only through the agent by .isle name.'},
    'swarm-lean': {'route': 'swarm', 'physical': {'secure_boot': True, 'disk_encryption': False, 'headless': True}, 'title': 'The lean server (swarm, no logins)', 'rings': 'dac,mac,network,host',
                   'mac_attach': 'docker-default', 'apps_run': 'in-core', 'guests': False, 'hardware': False, 'auth': 'none',
                   'description': 'Four services; modules run inside the backend; no per-service profile (the node-wide union instead); no guests, no devices; the API has no logins (D2).'},
    'swarm-full': {'route': 'swarm', 'physical': {'secure_boot': True, 'disk_encryption': False, 'headless': True}, 'title': 'The full server (swarm, Keycloak logins)', 'rings': 'dac,mac,network,host',
                   'mac_attach': 'docker-default', 'apps_run': 'in-core', 'guests': False, 'hardware': False, 'auth': 'keycloak',
                   'description': 'Ten services incl. Keycloak, MariaDB, MinIO, the scorecard; same swarm limits; users log in and the API checks tokens.'},
    'dev':        {'route': 'dev', 'physical': {'secure_boot': True, 'disk_encryption': False, 'headless': False}, 'title': "A developer's machine", 'rings': 'mac,host',
                   'mac_attach': 'security_opt', 'apps_run': 'containers', 'guests': False, 'hardware': False, 'auth': 'none',
                   'description': 'Compose on a laptop; profiles render in complain; nothing enforced that would get in the way; the audit still reports.'},
}

# what is APPLIED today, per scenario, beyond stock (the honest state; refreshed by hand from the ledger until the
# audit feeds it): system → mode
APPLIED_TODAY = {
    'isle': {'polari-apparmor': 'complain', 'svirt': 'enforce', 'agent-door': 'live', 'proxy-tls': 'live'},
    'swarm-lean': {'overlay-ipsec': 'live', 'proxy-tls': 'live'},
    'swarm-full': {'overlay-ipsec': 'live', 'proxy-tls': 'live', 'keycloak': 'live'},
    'dev': {},
}


def load_scenario(name):
    """The scenario's fixed pieces + keys, from os-security/scenarios/<name>.yml when the suite tree is
    beside the checkout, else the embedded mirror above."""
    base = dict(SCENARIOS.get(name) or {})
    if not base:
        return None
    base['name'] = name
    base['fixed'] = [dict(f) for f in FIXED.get(name, [])]
    path = os.path.join(SCENARIO_DIR, name + '.yml')
    if os.path.isfile(path):
        try:
            import yaml
            sc = yaml.safe_load(open(path, encoding='utf-8')) or {}
            base['fixed'] = [{'name': f['name'], 'profile': f.get('profile', 'web-app'), 'network': f.get('network', []),
                              'capabilities': f.get('capabilities', []), 'ports': f.get('ports', []), 'writable': f.get('writable', [])}
                             for f in sc.get('fixed', [])]
            base['mac_attach'] = sc.get('mac_attach', base['mac_attach'])
            base['apps_run'] = sc.get('apps_run', base['apps_run'])
            base['rings'] = ','.join(sc.get('rings', base['rings'].split(',')))
            base['source'] = path
        except Exception as exc:   # the mirror stands in
            base['source'] = f'embedded (yml unreadable: {exc})'
    else:
        base['source'] = 'embedded'
    return base


def scenario_names():
    names = list(SCENARIOS)
    for p in glob.glob(os.path.join(SCENARIO_DIR, '*.yml')):
        n = os.path.basename(p)[:-4]
        if n not in names:
            names.append(n)
    return names
