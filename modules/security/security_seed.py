"""
@module security.security_seed

Seed rows (upserted by name). The taxonomy (domains, areas), the scenarios, the controls per scenario with
provenance and state, and the three views' nodes and edges for every scenario at today's mode — all DERIVED
from security_facts + security_topology, never hand-typed. SECURITY_SEED_PAIRS is what admission applies.
"""
import json

from security.security_basis import (SecurityEvent, PermissionObservation, ObservationSession, UsageObservation, RolePrototype, AppSecurityRecord, AuthzRule, BrowserPolicy, ContentPolicy, ContentPolicyViolation, DacPolicy,
                                     FirewallRuleSet, HardwareTrial, MacProfile, PermissionGroup, ProxyConfig, ProxySnippet,
                                     SecurityArea, SecurityAuditRun, SecurityControl, SecurityDomain, SecurityProposal, SecurityScenario,
                                     SecurityThreat, SecurityTopologyEdge, SecurityTopologyNode, ServiceIdentity, SshCapability, DeviceInventory, SshPermissionLevel, TrustChannel)
from security.custom.security_os_rows import dac_policy_rows, mac_profile_rows, permission_group_rows
from security.custom.security_network_rows import firewall_rule_rows, proxy_config_rows, proxy_snippet_rows, service_identity_rows
from security.custom.security_app_rows import authz_rule_rows, browser_policy_rows, trust_channel_rows
from security.custom.security_ledger import app_security_records
from security.custom.security_facts import APPLIED_TODAY, SYSTEMS, load_scenario, scenario_names
from security.custom.security_topology import VIEWS, build
from security.custom.security_threats import threat_rows

SEED_SECURITY_DOMAINS = [
    {'name': 'app', 'title': 'App', 'order': 1, 'view_route': '/display/security-app',
     'description': 'How an app proves who it is, who may call what, what a request may contain — and who gets access through which means.'},
    {'name': 'network', 'title': 'Network', 'order': 2, 'view_route': '/display/security-network',
     'description': 'How bytes get in, between and out, and who can forge them.'},
    {'name': 'os', 'title': 'OS', 'order': 3, 'view_route': '/display/security-os',
     'description': 'What a process can touch on the machine: DAC (who runs as whom) and MAC (what it may touch regardless).'},
]

SEED_SECURITY_AREAS = [
    {'name': 'encryption', 'domain': 'app', 'title': 'Encryption', 'generated': False, 'docs_page': 'app-security', 'description': 'Key material: asymmetric for users, symmetric between servers.'},
    {'name': 'authentication', 'domain': 'app', 'title': 'Authentication', 'generated': False, 'docs_page': 'app-security', 'description': 'Keycloak (full profile), ssh keys, isle groups; none on the lean profile (D2).'},
    {'name': 'authorization', 'domain': 'app', 'title': 'Authorization', 'generated': True, 'docs_page': 'app-security', 'description': 'accessControl rules (the authority), sudoers drop-ins, the docker group, polkit.'},
    {'name': 'channels', 'domain': 'app', 'title': 'Channels', 'generated': False, 'docs_page': 'app-security', 'description': 'user↔app and app↔app trust channels (sec-i-2).'},
    {'name': 'content-policy', 'domain': 'app', 'title': 'Content policy', 'generated': True, 'docs_page': 'app-security', 'description': 'Payload schemas and limits derived from the data model (sec-i-3).'},
    {'name': 'tls', 'domain': 'network', 'title': 'TLS', 'generated': True, 'docs_page': 'network-security', 'description': 'Service identities, the suite and isle CAs, encrypted overlays.'},
    {'name': 'proxy', 'domain': 'network', 'title': 'Proxy', 'generated': True, 'docs_page': 'proxy-security', 'description': 'The edge proxy and the agent: hardened templates, per-app snippets.'},
    {'name': 'firewall', 'domain': 'network', 'title': 'Firewall', 'generated': True, 'docs_page': 'firewall-security', 'description': 'ufw, DOCKER-USER, docker network isolation, the router VM zones.'},
    {'name': 'exposure', 'domain': 'network', 'title': 'Exposure', 'generated': False, 'docs_page': 'network-security', 'description': 'Doors and rungs: what is deliberately reachable from outside.'},
    {'name': 'dac', 'domain': 'os', 'title': 'DAC', 'generated': True, 'docs_page': 'os-security', 'description': 'uid/gid, capabilities, read-only root, user-namespace remap, what is mounted, device allow-lists, groups.'},
    {'name': 'mac', 'domain': 'os', 'title': 'MAC', 'generated': True, 'docs_page': 'os-security', 'description': 'AppArmor (docker-default, per app, the node-wide union), seccomp, sVirt, docker\'s masked paths.'},
    {'name': 'hardware', 'domain': 'os', 'title': 'Hardware', 'generated': False, 'docs_page': 'os-security', 'description': 'VFIO passthrough from the hardware map; hardware trials (sec-i-5).'},
    {'name': 'boot', 'domain': 'os', 'title': 'Boot', 'generated': False, 'docs_page': 'os-security', 'description': 'Secure Boot: the firmware runs only a signed boot chain (Ubuntu\'s shim + kernel); off only deliberately at ISO build with a written reason.'},
    {'name': 'at-rest', 'domain': 'os', 'title': 'At rest', 'generated': False, 'docs_page': 'os-security', 'description': 'Disk encryption (LUKS): the one protection against someone who takes the drive or the machine; an option, off by default, never on headless.'},
    {'name': 'groups', 'domain': 'os', 'title': 'Groups', 'generated': True, 'docs_page': 'os-security', 'description': 'polari-remote, polari-app and the hardware groups.'},
]


def _scenario_rows():
    out = []
    for n in scenario_names():
        sc = load_scenario(n)
        if sc:
            out.append({'name': n, 'route': sc['route'], 'title': sc['title'], 'rings': sc['rings'], 'mode': 'today',
                        'mac_attach': sc['mac_attach'], 'apps_run': sc['apps_run'], 'fixed_pieces': ', '.join(f['name'] for f in sc['fixed']),
                        'guests': bool(sc.get('guests')), 'hardware': bool(sc.get('hardware')), 'description': sc['description']})
    return out


def _control_rows():
    out = []
    for n in scenario_names():
        sc = load_scenario(n)
        if not sc:
            continue
        applied = APPLIED_TODAY.get(n, {})
        for sid, s in SYSTEMS.items():
            if s['provenance'] == 'qemu' and not sc.get('guests'):
                continue
            if sid in ('agent-door', 'router-zone') and sc['route'] != 'isle':
                continue
            if sid == 'overlay-ipsec' and sc['route'] != 'swarm':
                continue
            state = applied.get(sid) or ('stock' if s['provenance'] == 'stock' else 'rendered')
            out.append({'name': f'{n}:{sid}', 'system': sid, 'scenario': n, 'domain': s['domain'], 'area': s['area'], 'title': s['title'],
                        'provenance': s['provenance'], 'state': state, 'protects': '', 'evidence': s['note'], 'notes': ''})
    return out


def _view_rows():
    nodes, edges = [], []
    for n in scenario_names():
        for v in VIEWS:
            try:
                g = build(v, n, 'today')
            except ValueError:
                continue
            for nd in g['nodes']:
                nodes.append({'name': f"{v}:{n}:{nd['node']}", 'view': v, 'scenario': n, 'node': nd['node'], 'kind': nd['kind'], 'layer': nd['layer'],
                              'title': nd['title'], 'description': nd.get('description', ''), 'system': nd.get('system', '')})
            for e in g['edges']:
                edges.append({'name': f"{v}:{n}:{e['source']}→{e['target']}:{e['means']}"[:200], 'view': v, 'scenario': n, 'mode': 'today',
                              'source': e['source'], 'target': e['target'], 'means': e['means'],
                              'chain': ' → '.join(f"{s['system']}:{s['decision']}" for s in e['chain'] if s['decision'] != 'n/a'),
                              'decided_by': e['decided_by'], 'provenance': e['provenance'], 'verdict': e['verdict'], 'why': e['why']})
    return nodes, edges


SEED_SECURITY_SCENARIOS = _scenario_rows()
SEED_SECURITY_CONTROLS = _control_rows()
SEED_SECURITY_NODES, SEED_SECURITY_EDGES = _view_rows()
SEED_SECURITY_THREATS = [r for n in scenario_names() for r in threat_rows(n, 'today')]
SEED_SECURITY_MAC_PROFILES = mac_profile_rows(APPLIED_TODAY)
SEED_SECURITY_DAC_POLICIES = dac_policy_rows()
SEED_SECURITY_PERMISSION_GROUPS = permission_group_rows()
SEED_SECURITY_PROXY_CONFIGS = proxy_config_rows()
SEED_SECURITY_PROXY_SNIPPETS = proxy_snippet_rows()
SEED_SECURITY_SERVICE_IDENTITIES = service_identity_rows()
SEED_SECURITY_FIREWALL_RULES = firewall_rule_rows(APPLIED_TODAY)
SEED_SECURITY_TRUST_CHANNELS = trust_channel_rows()
SEED_SECURITY_AUTHZ_RULES = authz_rule_rows()
SEED_SECURITY_BROWSER_POLICIES = browser_policy_rows()
SEED_SECURITY_LEDGER = app_security_records(APPLIED_TODAY, channels=SEED_SECURITY_TRUST_CHANNELS)

SECURITY_SEED_PAIRS = [
    ('SecurityDomain', SecurityDomain, SEED_SECURITY_DOMAINS),
    ('SecurityArea', SecurityArea, SEED_SECURITY_AREAS),
    ('SecurityScenario', SecurityScenario, SEED_SECURITY_SCENARIOS),
    ('SecurityControl', SecurityControl, SEED_SECURITY_CONTROLS),
    ('SecurityTopologyNode', SecurityTopologyNode, SEED_SECURITY_NODES),
    ('SecurityTopologyEdge', SecurityTopologyEdge, SEED_SECURITY_EDGES),
    ('SecurityThreat', SecurityThreat, SEED_SECURITY_THREATS),
    # the domains' rows (derived from the tree; the live columns fill from audit runs / the manager at refresh)
    ('MacProfile', MacProfile, SEED_SECURITY_MAC_PROFILES),
    ('DacPolicy', DacPolicy, SEED_SECURITY_DAC_POLICIES),
    ('PermissionGroup', PermissionGroup, SEED_SECURITY_PERMISSION_GROUPS),
    ('HardwareTrial', HardwareTrial, []),
    ('ProxyConfig', ProxyConfig, SEED_SECURITY_PROXY_CONFIGS),
    ('ProxySnippet', ProxySnippet, SEED_SECURITY_PROXY_SNIPPETS),
    ('ServiceIdentity', ServiceIdentity, SEED_SECURITY_SERVICE_IDENTITIES),
    ('FirewallRuleSet', FirewallRuleSet, SEED_SECURITY_FIREWALL_RULES),
    ('TrustChannel', TrustChannel, SEED_SECURITY_TRUST_CHANNELS),
    ('AuthzRule', AuthzRule, SEED_SECURITY_AUTHZ_RULES),
    ('ContentPolicy', ContentPolicy, []),
    ('ContentPolicyViolation', ContentPolicyViolation, []),
    ('BrowserPolicy', BrowserPolicy, SEED_SECURITY_BROWSER_POLICIES),
    ('AppSecurityRecord', AppSecurityRecord, SEED_SECURITY_LEDGER),
    ('SecurityAuditRun', SecurityAuditRun, []),
    ('SecurityProposal', SecurityProposal, []),
    ('SshCapability', SshCapability, []),
    ('DeviceInventory', DeviceInventory, []),
    ('SshPermissionLevel', SshPermissionLevel, []),
    ('SecurityEvent', SecurityEvent, []),      # observe mode (§17): filled by decisions at runtime, never seeded
    ('PermissionObservation', PermissionObservation, []),   # dev mode: who did what (roles × class × verb) — profiles derived from it
    ('ObservationSession', ObservationSession, []),         # role-play windows
    ('UsageObservation', UsageObservation, []),             # what a role USES: apps, pages, components, actions, endpoints
    ('RolePrototype', RolePrototype, []),                   # roles that exist to be role-played (prototype → concreted → enforced)
]

if __name__ == '__main__':
    print(json.dumps({k: len(v) for k, _, v in [(a, b, c) for a, b, c in SECURITY_SEED_PAIRS]}, indent=1))
