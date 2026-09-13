"""
@module security.custom.security_threats

Threat analysis simulations ON the topology (his ask 2026-09-12): a named threat is one reach attempt taken
from a view (an actor, a means, a target), played hop by hop through the chain of systems until one blocks
it — the policy that blocked it is named — and beside it the COUNTEREXAMPLE: the legitimate actor, group or
permission that reaches the same target through the intended means, and the chain that lets it. Every threat
resolves against a scenario and a mode (stock | today | complain | enforce), so the same threat can be
watched getting through on stock docker, logged under complain, and blocked under enforce. The path is what
the animation walks: [actor] → boundary … → [target], with `stops_at` the index of the block.
"""
from security.custom.security_facts import SYSTEMS, load_scenario
from security.custom.security_topology import MODES, ROLE_OF, build

# actor roles → the node name in a scenario
BACKEND = {'isle': 'prf-isle-backend', 'swarm-lean': 'prf-backend', 'swarm-full': 'prf-backend', 'dev': None}
GATEWAY = {'isle': 'isle-gateway', 'swarm-lean': 'pol-proxy', 'swarm-full': 'pol-proxy', 'dev': None}

THREATS = [
    {'name': 'image-backdoor', 'view': 'os', 'title': 'A compromised app writes a backdoor into its own image',
     'actor': 'backend', 'means': 'write into /usr, /etc, /bin of its own image', 'target': 'image',
     'story': 'Code running inside the container tries to replace its own entrypoint so the backdoor survives a restart.',
     'counter': {'actor': 'owner', 'group': 'the owner or a polari-remote member', 'means': 'rebuild the image and redeploy (pol build, pol prod apply)', 'target': 'image',
                 'chain': [('ssh-keys', 'allowed', 'key login'), ('sudoers', 'allowed', 'the remote verbs')],
                 'story': 'What runs is changed by a build and a deploy, by a person with the remote role — never by the running app.'}},
    {'name': 'docker-socket', 'view': 'os', 'title': 'A compromised app takes the docker socket (root on the host)',
     'actor': 'backend', 'means': 'connect /var/run/docker.sock', 'target': 'docker-socket',
     'story': 'With the socket, a process can start a privileged container and own the machine.',
     'counter': {'actor': 'owner', 'group': 'the docker group (the operator only)', 'means': 'docker on the host', 'target': 'docker-socket',
                 'chain': [('ssh-keys', 'allowed', ''), ('docker-group', 'allowed', 'membership is root-equivalent — kept to the operator')],
                 'story': 'The socket is for the operator on the host; Polari never mounts it into a container and never adds a service user to the group.'}},
    {'name': 'host-shadow', 'view': 'os', 'title': "A compromised app reads the host's password hashes through a bind mount",
     'actor': 'backend', 'means': "read the host's /etc/shadow through a bind mount", 'target': 'host-files',
     'story': 'If a host directory were bound in, uid 0 inside is uid 0 outside and owns the file.',
     'counter': {'actor': 'owner', 'group': 'sudo', 'means': 'sudo cat /etc/shadow', 'target': 'host-files',
                 'chain': [('ssh-keys', 'allowed', ''), ('sudoers', 'allowed', 'the owner\'s own sudo')],
                 'story': 'Host files belong to the host\'s people. The app\'s protections here are DAC: nothing bound in, and the user-namespace remap (D1).'}},
    {'name': 'ptrace-neighbour', 'view': 'os', 'title': "A compromised app attaches to another container's process",
     'actor': 'backend', 'means': "ptrace another container's process", 'target': 'other-container',
     'story': 'Reading another service\'s memory would expose its secrets and tokens.',
     'counter': {'actor': 'owner', 'group': 'the docker group', 'means': 'docker exec into the container', 'target': 'other-container',
                 'chain': [('ssh-keys', 'allowed', ''), ('docker-group', 'allowed', 'exec enters the container under its own profile')],
                 'story': 'An operator inspects a container through docker, which puts the shell under that container\'s own confinement.'}},
    {'name': 'kernel-module', 'view': 'os', 'title': 'A compromised app loads a kernel module',
     'actor': 'backend', 'means': 'load a kernel module', 'target': 'kernel',
     'story': 'A rootkit in the kernel would be invisible to everything above it.',
     'counter': {'actor': 'owner', 'group': 'sudo', 'means': 'modprobe on the host', 'target': 'kernel',
                 'chain': [('ssh-keys', 'allowed', ''), ('sudoers', 'allowed', '')],
                 'story': 'Kernel changes are the owner\'s, on the host, in a maintenance window.'}},
    {'name': 'raw-sniff', 'view': 'os', 'title': 'A compromised app opens a raw socket to sniff or forge packets',
     'actor': 'backend', 'means': 'open a raw socket (sniff / forge packets)', 'target': 'kernel',
     'story': 'Stock docker keeps CAP_NET_RAW; a backend has no business with it.',
     'counter': {'actor': 'gateway', 'group': 'the gateway kind (declares NET_RAW / NET_ADMIN)', 'means': 'raw sockets for tunnels and DHCP', 'target': 'kernel',
                 'chain': [('polari-surface', 'allowed', 'cap_add from the manifest stanza'), ('polari-apparmor', 'allowed', 'network raw allowed for gateway kinds')],
                 'story': 'Only a gateway kind declares it, in its manifest, and gets exactly that.'}},
    {'name': 'unassigned-device', 'view': 'os', 'title': 'A plain app opens a hardware device it was never assigned',
     'actor': 'backend', 'means': 'open /dev/ttyUSB0, /dev/video0, /dev/kvm', 'target': 'devices',
     'story': 'A printer port, a camera or the KVM device in the wrong hands.',
     'counter': {'actor': 'a hardware extension', 'group': 'kind hardware-extension with a hardware-map assignment (isle only)', 'means': 'the assigned device through VFIO / --device', 'target': 'devices',
                 'chain': [('device-acl', 'allowed', 'exactly the assigned device'), ('vfio', 'allowed', 'the hardware map is the authority')],
                 'story': 'Hardware reaches an app only on the isle route, through an assignment: on a swarm there is no legitimate path at all.', 'isle_only': True}},
    {'name': 'guest-escape', 'view': 'os', 'title': 'A hardware app inside its guest tries to reach the host',
     'actor': 'a guest', 'means': 'escape the hypervisor', 'target': 'kernel', 'isle_only': True,
     'story': 'The guest kernel is the app\'s; the host kernel is not.',
     'counter': {'actor': 'owner', 'group': 'libvirt / sudo', 'means': 'virsh and the isle CLI', 'target': 'guests',
                 'chain': [('polkit', 'allowed', ''), ('sudoers', 'allowed', '')],
                 'story': 'Guests are managed from the host by the owner; a guest never manages the host.'}},
    {'name': 'stolen-drive', 'view': 'os', 'title': 'The machine is stolen and its drive is read in another computer',
     'actor': 'physical access', 'means': 'pull the drive and read it in another machine', 'target': 'the disk',
     'story': 'No container ring applies to someone holding the hardware; only what is on the disk itself decides.',
     'counter': {'actor': 'owner', 'group': 'the owner who knows the passphrase', 'means': 'type the passphrase at start-up', 'target': 'the disk',
                 'chain': [('disk-encryption', 'allowed', 'the passphrase unlocks it; lost passphrase = data gone, disk reinstallable')],
                 'story': 'Disk encryption is a build-time option (off by default, never on headless): with it on, the drive is unreadable to anyone but the person with the passphrase.'}},
    {'name': 'tampered-boot', 'view': 'os', 'title': 'Someone with the machine installs a tampered boot loader or kernel',
     'actor': 'physical access', 'means': 'replace the boot loader or kernel on the disk with a tampered one', 'target': 'kernel',
     'story': 'A kernel that lies to everything above it, planted before the OS starts.',
     'counter': {'actor': 'owner', 'group': "Ubuntu's signed boot chain (Canonical's shim + kernel)", 'means': 'a kernel update from the apt pool, signed', 'target': 'kernel',
                 'chain': [('secure-boot', 'allowed', 'signed by the key the firmware trusts')],
                 'story': 'Legitimate kernels arrive signed through apt; Secure Boot is on by default and turned off only deliberately at ISO build, with the reason written down.'}},
    {'name': 'ssh-from-internet', 'view': 'network', 'title': 'Someone on the internet reaches sshd',
     'actor': 'internet', 'means': 'ssh', 'target': 'sshd',
     'story': 'Password guessing and key theft start with a reachable port.',
     'counter': {'actor': 'owner', 'group': 'the admin / isle LAN with a key', 'means': 'ssh from the admin LAN', 'target': 'sshd',
                 'chain': [('ufw', 'allowed', '22 from the admin LAN only (rendered)'), ('ssh-keys', 'allowed', 'public-key login')],
                 'story': 'The firewall ring narrows 22 to the operator\'s network; the key is the identity.'}},
    {'name': 'swarm-ports-from-internet', 'view': 'network', 'title': 'Someone on the internet reaches the swarm management ports',
     'actor': 'internet', 'means': 'swarm management / gossip / VXLAN', 'target': 'swarm-ports',
     'story': 'The swarm control plane must only hear its own peers.',
     'counter': {'actor': 'other-node', 'group': 'a swarm peer (its address in the peers set)', 'means': '2377/7946/4789 from a peer', 'target': 'swarm-ports',
                 'chain': [('ufw', 'allowed', 'peers only'), ('overlay-ipsec', 'allowed', 'and the traffic is encrypted')],
                 'story': 'Peers are named; everyone else is denied by the firewall ring.', 'swarm_only': True}},
    {'name': 'container-to-host-ssh', 'view': 'network', 'title': 'A compromised container connects to the host\'s sshd',
     'actor': 'backend', 'means': 'connect to a host service', 'target': 'sshd',
     'story': 'Stock docker lets containers reach the host\'s services at the bridge gateway.',
     'counter': {'actor': 'owner', 'group': 'the admin LAN', 'means': 'ssh from the LAN', 'target': 'sshd',
                 'chain': [('ufw', 'allowed', ''), ('ssh-keys', 'allowed', '')],
                 'story': 'DOCKER-USER lets containers reach only DNS (and the agent on the isle); people reach sshd from the LAN.'}},
    {'name': 'anonymous-api', 'view': 'app', 'title': 'A visitor calls the API without logging in',
     'actor': 'visitor', 'means': None, 'target': 'api',
     'story': 'Every class has CRUDE endpoints; without a login boundary anyone may read and write.',
     'counter': {'actor': 'user', 'group': 'a Keycloak role (full profile)', 'means': 'HTTPS with a signed OIDC token, then the accessControl rules', 'target': 'api',
                 'chain': [('keycloak', 'allowed', 'a signed token — asymmetric, no shared secret in the browser'), ('access-control', 'allowed', 'CRUDE per class and role')],
                 'story': 'On the full profile identity comes from Keycloak and permission from the accessControl rules. On the lean profile there is NO login by decision D2: the threat is simply allowed, and the counterexample is the same visitor — acceptable only for a distribution point with no private data.'}},
    {'name': 'remote-escalation', 'view': 'app', 'title': 'A polari-remote member tries to become full root',
     'actor': 'remote-member', 'means': 'the polari-remote verbs only (install, swarm, AI setup)', 'target': 'host',
     'story': 'The remote role exists so setup over ssh needs no full sudo.',
     'counter': {'actor': 'owner', 'group': 'the owner (sudo)', 'means': 'sudo', 'target': 'host',
                 'chain': [('ssh-keys', 'allowed', ''), ('sudoers', 'allowed', 'the owner\'s own membership')],
                 'story': 'The drop-in lists the verbs; anything else is the owner\'s. (Today the drop-ins are installed on no machine, so the owner\'s sudo stands in for both.)'}},
    {'name': 'docker-group-root', 'view': 'app', 'title': 'A docker-group member becomes root on the host',
     'actor': 'docker-member', 'means': 'docker run --privileged, or mount /', 'target': 'host',
     'story': 'This one is ALLOWED by design of docker itself: the socket is root.',
     'counter': {'actor': 'owner', 'group': 'the docker group = the operator, nobody else', 'means': 'the same socket', 'target': 'host',
                 'chain': [('docker-group', 'allowed', 'membership is the control')],
                 'story': 'There is no policy that narrows the socket: the only control is who is in the group. Polari never adds a service user to it, and the audit counts its members.'}},
]


def _resolve_actor(role, scn):
    if role == 'backend':
        return BACKEND.get(scn)
    if role == 'gateway':
        return GATEWAY.get(scn)
    return role


def _path(actor, chain, target):
    path = [{'node': actor, 'kind': 'actor', 'decision': ''}]
    for st in chain:
        if st['decision'] == 'n/a':
            continue
        path.append({'node': st['system'], 'kind': 'boundary', 'title': SYSTEMS[st['system']]['title'], 'provenance': st['provenance'],
                     'decision': st['decision'], 'note': st.get('note', '')})
    path.append({'node': target, 'kind': 'target', 'decision': ''})
    stops = next((i for i, p in enumerate(path) if p.get('decision') == 'blocked'), None)
    return path, stops


def threats(scenario, mode='today'):
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES}')
    sc = load_scenario(scenario)
    if sc is None:
        raise ValueError(f'unknown scenario {scenario!r}')
    graphs = {v: build(v, scenario, mode) for v in ('os', 'network', 'app')}
    out = []
    for t in THREATS:
        if t.get('isle_only') and sc['route'] != 'isle':
            continue
        if t.get('swarm_only') and sc['route'] != 'swarm':
            continue
        actor = _resolve_actor(t['actor'], scenario)
        if actor is None:
            continue
        edges = graphs[t['view']]['edges']
        e = next((x for x in edges if x['source'] == actor and x['target'] == t['target'] and (t['means'] is None or x['means'] == t['means'])), None)
        if e is None:
            continue
        path, stops = _path(actor, e['chain'], t['target'])
        blocked_by = e['decided_by'] if e['verdict'] == 'blocked' else ''
        policy = next((st.get('note') or SYSTEMS[st['system']]['note'] for st in e['chain'] if st['system'] == blocked_by), '') if blocked_by else ''
        c = t['counter']
        c_actor = _resolve_actor(c['actor'], scenario) or c['actor']
        c_isle_only = c.get('isle_only') and sc['route'] != 'isle'
        if c_isle_only:
            c_chain = [{'system': 'vfio', 'provenance': 'qemu', 'decision': 'blocked', 'note': 'no hardware on this route: nothing can be assigned'}]
        else:
            c_chain = [{'system': s, 'provenance': SYSTEMS[s]['provenance'], 'decision': d, 'note': n} for s, d, n in c['chain']]
        c_path, c_stops = _path(c_actor, c_chain, c['target'])
        out.append({
            'name': t['name'], 'view': t['view'], 'scenario': scenario, 'mode': mode, 'title': t['title'], 'story': t['story'],
            'actor': actor, 'means': e['means'], 'target': t['target'], 'verdict': e['verdict'], 'blocked_by': blocked_by,
            'policy': policy, 'why': e['why'], 'path': path, 'stops_at': stops,
            'counter': {'actor': c_actor, 'group': c['group'], 'means': c['means'], 'target': c['target'], 'story': c['story'],
                        'verdict': 'blocked' if c_stops is not None else 'allowed', 'path': c_path, 'stops_at': c_stops,
                        'note': 'no legitimate path on this route' if c_isle_only else ''},
        })
    counts = {'allowed': sum(1 for x in out if x['verdict'] == 'allowed'), 'logged': sum(1 for x in out if x['verdict'] == 'logged'), 'blocked': sum(1 for x in out if x['verdict'] == 'blocked')}
    return {'scenario': scenario, 'route': sc['route'], 'mode': mode, 'modes': list(MODES), 'counts': counts, 'threats': out,
            'reading': f"{scenario} ({mode}): of {len(out)} threats, {counts['blocked']} blocked, {counts['logged']} logged only, {counts['allowed']} get through"}


def threat_rows(scenario, mode='today'):
    """Flat rows for the table / the seed."""
    rows = []
    for t in threats(scenario, mode)['threats']:
        rows.append({'name': f"{scenario}:{t['name']}", 'threat': t['name'], 'view': t['view'], 'scenario': scenario, 'mode': mode, 'title': t['title'],
                     'actor': t['actor'], 'means': t['means'], 'target': t['target'], 'verdict': t['verdict'], 'blocked_by': t['blocked_by'],
                     'policy': (t['policy'] or '')[:200], 'counter_actor': t['counter']['actor'], 'counter_group': t['counter']['group'],
                     'counter_means': t['counter']['means'], 'counter_verdict': t['counter']['verdict'], 'story': t['story']})
    return rows
