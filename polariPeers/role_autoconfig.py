"""
@cross-cutting
@module polariPeers.role_autoconfig
@tags @xc:bindings

Role auto-config — the first-boot mesh logic (/MESH_CONVERGENCE_PLAN.md
§3, §7.3): detect the mesh → claim this node's .isle name → discover
existing Polari instances → decide parent|child → as child, send the
join request (polariPeers.join_flow) and, once approved, the
coordination module can be pulled via the existing modules API.

Knobs-and-suggestions compliant:
  * POLARI_NODE_ROLE = auto | parent | child   (the role knob; auto default)
  * POLARI_PARENT_URL                          (explicit parent — strongest
                                                child evidence)
  * POLARI_DISCOVERY_URLS                      (comma-separated probe list —
                                                the twin's stand-in for mesh
                                                discovery)
  * POLARI_PUBLIC_BASE_URL                     (how peers reach THIS node)
Every auto decision is returned (and printed) WITH its evidence lines —
detection suggests, the knobs decide.

Idempotent by design: re-running is safe (an approved outbound agreement
short-circuits to a plain re-register; an unmeshed node with no evidence
just reports 'standalone' and changes nothing).

@consumers
  - polariServer (first-boot hook, POLARI_MESH_AUTOCONFIG-guarded)
  - polariPeers.peers_api (POST /api/peers/autoconfig drives it on demand)
@see /MESH_CONVERGENCE_PLAN.md §3, §7
"""

import os
from typing import Any, Dict, List

from polariPeers.mesh_facts import claim_name, get_mesh_facts
from polariPeers.peers_api import _http_get_json, instance_identity


def _discovery_urls() -> List[str]:
    urls = (os.environ.get('POLARI_DISCOVERY_URLS') or '').strip()
    return [u.strip().rstrip('/') for u in urls.split(',') if u.strip()]


def _probe_polari(base_url: str) -> Dict[str, Any]:
    """Is there a live Polari at base_url? Its ping identity or
    {'_error': ...}."""
    ping = _http_get_json(f'{base_url}/api/peers/ping')
    if '_error' in ping:
        return ping
    data = ping.get('data') or {}
    if data.get('framework') != 'polari':
        return {'_error': 'not a polari instance'}
    return data


def discover_existing(facts: Dict[str, Any],
                      parent_url: str = '') -> List[Dict[str, Any]]:
    """Find live Polari instances: the explicit parent (param or knob)
    first, then the discovery list, then mesh-facts polari-* claims."""
    candidates: List[str] = []
    parent_url = (parent_url
                  or os.environ.get('POLARI_PARENT_URL')
                  or '').strip().rstrip('/')
    if parent_url:
        candidates.append(parent_url)
    candidates += _discovery_urls()
    for claim, owner in (facts.get('claims') or {}).items():
        if str(claim).startswith('polari-') and owner:
            candidates.append(f'http://{claim}')
    found = []
    my_name = instance_identity()['instanceName']
    seen = set()
    for url in candidates:
        if not url or url in seen:
            continue
        seen.add(url)
        ident = _probe_polari(url)
        if '_error' not in ident and ident.get('instanceName') != my_name:
            found.append({'baseUrl': url, 'identity': ident})
    return found


def auto_configure(manager, my_base_url: str = '',
                   parent_url: str = '') -> Dict[str, Any]:
    """The detect→claim→discover→role pipeline. Returns the full report
    (role, evidence, actions taken)."""
    evidence: List[str] = []
    ident = instance_identity()
    my_base_url = (my_base_url
                   or (os.environ.get('POLARI_PUBLIC_BASE_URL') or '').strip()
                   ).rstrip('/')

    # 1. Detect.
    facts = get_mesh_facts()
    evidence.append(
        f'mesh facts: meshed={facts["meshed"]} '
        f'(source {facts.get("source", "?")})'
        + (f', isle "{facts["isleName"]}"' if facts.get('isleName') else ''))

    # 2. Claim this node's .isle name (only meaningful on a mesh).
    if facts['meshed']:
        isle_claim = f'{ident["instanceName"]}.isle'
        claim = claim_name(isle_claim)
        evidence.append(
            f'claim "{isle_claim}": claimed={claim.get("claimed")} '
            f'(available={claim.get("available")})')

    # 3. Discover.
    existing = discover_existing(facts, parent_url=parent_url)
    evidence.append(
        f'discovery: {len(existing)} live Polari instance(s) found'
        + (': ' + ', '.join(
            f'{e["identity"].get("instanceName", "?")}@{e["baseUrl"]}'
            for e in existing) if existing else ''))

    # 4. Role: the knob decides; auto follows the evidence.
    role_knob = (os.environ.get('POLARI_NODE_ROLE') or 'auto').strip().lower()
    if role_knob in ('parent', 'child'):
        role = role_knob
        evidence.append(f'role knob POLARI_NODE_ROLE={role_knob} — '
                        f'overriding auto detection')
    else:
        role = 'child' if existing else 'parent'
        evidence.append(
            f'auto role: {role} ({"existing Polari found" if existing else "none found — this node leads"})')

    report: Dict[str, Any] = {
        'instance': ident['instanceName'], 'role': role,
        'meshed': facts['meshed'], 'evidence': evidence,
    }

    # 5. Act. Parent: nothing to do (children come to us via join
    # requests). Child: send the join request to the best parent.
    if role == 'child':
        if not existing:
            evidence.append('child role but no reachable parent — will '
                            'retry on the next auto-configure run')
            report['joined'] = False
        elif not my_base_url:
            evidence.append('cannot join: POLARI_PUBLIC_BASE_URL is not set '
                            '(the parent must be able to reach this node)')
            report['joined'] = False
        else:
            from polariPeers.join_flow import join_parent
            join = join_parent(manager, existing[0]['baseUrl'], my_base_url)
            evidence.extend(join.get('evidence') or [])
            report['joined'] = join.get('joined', False)
            report['join'] = join

    for line in evidence:
        print(f'[RoleAutoConfig] {line}', flush=True)
    print(f'[RoleAutoConfig] DECISION: {ident["instanceName"]} -> {role}',
          flush=True)
    return report
