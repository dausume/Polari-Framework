"""
@module islemesh.islemesh_coherence

The JOINED topology view: the isle topology (devices/agents/apps —
where packets go) and the polari topology (instances of polari —
what runs where) assessed TOGETHER. Pure functions over plain rows
so the selftest runs framework-free.

Dustin's rule (mac plan decision 3): what runs where is polari's,
where packets go is isle's — this module makes the seam VISIBLE and
assessable: every polari instance is an isle app instance on a
device; manipulation rides the same store/deploy machinery.

@consumers
  - islemesh.islemesh_api (/api/islemesh/coherence)
  - islemesh.selftest_islemesh (function-level)
"""

from islemesh.islemesh_catalog import instances_of
from islemesh.islemesh_netledger import assess_resources

#: Polari's COMPONENT scaling shape (Dustin): one frontend, one sql,
#: one cache per instance-group — but backends are the replicable
#: part. Whole-stack duplication (polari-2) is the coarse form;
#: component-level scaling is the real one (needs the shared-db
#: profile + upstream LB — the recorded next arc).
POLARI_COMPONENTS = {
    'frontend': 'singleton',
    'sql': 'singleton',
    'cache': 'singleton',
    'blob': 'singleton',
    'auth': 'singleton',
    'backend': 'replicable',
}


def assess_topology(devices, apps, services=None):
    """Joined view + evidence-bearing assessments.

    devices:  [{name, agent_present, last_seen, is_mock}, ...]
    apps:     [{name, device_name, domain, is_mock}, ...]
    services: [{app_name, subdomain, device_name, is_mock}, ...]
              (optional — the api/auth/... SUB-DOMAINS under each
              app; polari-style apps are unreadable without them)

    Returns {'devices': [...], 'polari': {...},
             'assessments': [{level, code, message}, ...]}.
    Assessments SUGGEST (knobs-and-suggestions) — nothing here acts.
    """
    real_devices = [d for d in devices if not d.get('is_mock')]
    real_apps = [a for a in apps if not a.get('is_mock')]
    subs_by_app = {}
    for s in (services or []):
        if s.get('is_mock'):
            continue
        sub = s.get('subdomain', '')
        if sub:
            subs_by_app.setdefault(
                (s.get('app_name', ''),
                 s.get('device_name', '')), []).append(sub)
    # SUB-DOMAIN folding: the registry models api.polari.isle as a
    # SIBLING app ('polari-api'); coherently, any app whose domain is
    # '<sub>.X.isle' on the same device IS a subdomain of the app
    # owning 'X.isle' — fold it under its parent (api/auth/... must
    # be visible UNDER the app, not beside it).
    owner_by_domain = {}
    for a in real_apps:
        dom = a.get('domain', '')
        if dom:
            owner_by_domain[(a.get('device_name', ''), dom)] = a
    folded = set()
    for a in real_apps:
        dom = a.get('domain', '')
        dev = a.get('device_name', '')
        parts = dom.split('.', 1)
        if len(parts) == 2 and (dev, parts[1]) in owner_by_domain \
                and parts[1] != dom:
            parent = owner_by_domain[(dev, parts[1])]
            subs_by_app.setdefault(
                (parent.get('name', ''), dev), []).append(dom)
            folded.add((a.get('name', ''), dev))
    real_apps = [a for a in real_apps
                 if (a.get('name', ''), a.get('device_name', ''))
                 not in folded]

    by_device = {}
    for a in real_apps:
        by_device.setdefault(a.get('device_name', ''), []).append(a)

    polari_instances = instances_of(real_apps, 'polari')
    for i in polari_instances:
        # THE CORE polari is self-evident from the isle side: the
        # instance serving polari.isle — the isle's own polari, the
        # ingest/self-feed target (we are combining the two systems).
        i['role'] = ('core' if i.get('domain') == 'polari.isle'
                     else 'additional')
        i['subdomains'] = sorted(subs_by_app.get(
            (i['app'], i['device']), []))
    polari_devices = {i['device'] for i in polari_instances}

    out_devices = []
    assessments = []
    for d in real_devices:
        name = d.get('name', '')
        agent = bool(d.get('agent_present'))
        d_apps = by_device.get(name, [])
        out_devices.append({
            'name': name,
            'agent_present': agent,
            'is_entrypoint': bool(d.get('is_entrypoint')),
            'exposures': d.get('exposures') or [],
            'pools': d.get('pools') or [],
            'ports': d.get('ports') or [],
            'app_count': len(d_apps),
            # each app with its SUB-DOMAINS (api/auth/... — where
            # the pieces of polari-style apps actually live)
            'apps': sorted(
                ({'name': a.get('name', ''),
                  'domain': a.get('domain', ''),
                  'subdomains': sorted(subs_by_app.get(
                      (a.get('name', ''), name), []))}
                 for a in d_apps),
                key=lambda x: x['name']),
            'polari_instances': sorted(
                i['app'] for i in polari_instances
                if i['device'] == name),
        })
        if d_apps and not agent:
            assessments.append({
                'level': 'warn', 'code': 'apps-without-agent',
                'message': '%s reports %d app(s) but no agent — '
                           'nothing serves them (join or isle '
                           'agent ensure)' % (name, len(d_apps))})
        if agent and not d_apps:
            assessments.append({
                'level': 'info', 'code': 'member-no-apps',
                'message': '%s is a member (agent up) with no '
                           'reported apps — a candidate for '
                           'placement' % name})

    # polari-specific: the scaling view (type vs instances)
    candidates = sorted(
        d['name'] for d in out_devices
        if d['agent_present'] and d['name'] not in polari_devices)
    if not polari_instances:
        assessments.append({
            'level': 'warn', 'code': 'no-polari',
            'message': 'no polari instance runs on the isle — the '
                       'store/topology pages have no backend'})
    if candidates:
        assessments.append({
            'level': 'info', 'code': 'polari-scale-candidates',
            'message': 'polari could also run on: %s (isle polari '
                       'instance deploy — a mesh-app install)'
                       % ', '.join(candidates)})

    # network resource conflicts (pools/ports) — the scale guard
    assessments.extend(assess_resources(real_devices))

    core = [i for i in polari_instances if i['role'] == 'core']
    if polari_instances and not core:
        assessments.append({
            'level': 'warn', 'code': 'no-core-polari',
            'message': 'no polari instance serves polari.isle — '
                       'the isle has no CORE polari (ingests and '
                       'the store have no home)'})

    return {
        'devices': out_devices,
        'polari': {
            'instances': polari_instances,
            'core': (core[0] if core else None),
            'devices': sorted(polari_devices),
            'candidates': candidates,
            # the component scaling shape: polari installs as
            # SUBSECTIONS of itself — singletons vs the replicable
            # backend (component installs are the recorded next arc)
            'components': POLARI_COMPONENTS,
        },
        'assessments': assessments,
    }
