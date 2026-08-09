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


def assess_topology(devices, apps):
    """Joined view + evidence-bearing assessments.

    devices: [{name, agent_present, last_seen, is_mock}, ...]
    apps:    [{name, device_name, domain, is_mock}, ...]

    Returns {'devices': [...], 'polari': {...},
             'assessments': [{level, code, message}, ...]}.
    Assessments SUGGEST (knobs-and-suggestions) — nothing here acts.
    """
    real_devices = [d for d in devices if not d.get('is_mock')]
    real_apps = [a for a in apps if not a.get('is_mock')]
    by_device = {}
    for a in real_apps:
        by_device.setdefault(a.get('device_name', ''), []).append(a)

    polari_instances = instances_of(real_apps, 'polari')
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
            'app_count': len(d_apps),
            'apps': sorted(a.get('name', '') for a in d_apps),
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

    return {
        'devices': out_devices,
        'polari': {
            'instances': polari_instances,
            'devices': sorted(polari_devices),
            'candidates': candidates,
        },
        'assessments': assessments,
    }
