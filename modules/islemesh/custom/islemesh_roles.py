"""Reported Polari component roles and built-in agent diagnostics.

Registration is deployment evidence, not a live endpoint health check.
Frontend and backend providers may reside on different devices. Neither role
alone establishes the minimum Polari deployment for an Isle.
"""
import json
import re


def value(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def modes_of(row):
    modes = value(row, 'modes', None)
    if modes is None:
        try:
            modes = json.loads(value(row, 'modes_json', '[]') or '[]')
        except (ValueError, TypeError):
            modes = []
    return modes if isinstance(modes, list) else []


def services_of(row, services):
    return [s for s in services if value(s, 'app_name') == value(row, 'name')
            and value(s, 'device_name') == value(row, 'device_name')
            and not value(s, 'is_mock', False)]


def is_agent_health(row, services):
    if 'agent-diagnostic:health' in modes_of(row):
        return True
    # Legacy built-in registry entry; never classify a separately hosted app
    # just because its name contains 'health'.
    return (value(row, 'name') == 'health' and value(row, 'domain') == 'health.local'
            and not any(value(s, 'container') for s in services_of(row, services)))


def component_roles(row, services):
    roles = {m.split(':', 1)[1] for m in modes_of(row)
             if m in ('polari-role:frontend', 'polari-role:backend')}
    for service in services_of(row, services):
        match = re.fullmatch(r'prf-[a-z0-9-]+-(frontend|backend)', value(service, 'container'))
        if match:
            roles.add(match.group(1))
    return sorted(roles)


def polari_inventory(apps, services, devices=()):
    providers = []
    device_map = {value(d, 'name'): d for d in devices}
    for app in apps:
        if value(app, 'is_mock', False):
            continue
        for role in component_roles(app, services):
            device = value(app, 'device_name')
            deployment = next((m.split(':', 1)[1] for m in modes_of(app) if isinstance(m, str) and m.startswith('polari-deployment:')), value(app, 'name').removesuffix('-api'))
            providers.append({'deployment': deployment, 'app': value(app, 'name'), 'device': device,
                              'domain': value(app, 'domain'), 'component_role': role,
                              'role': role, 'subdomains': [],
                              'modules': [name for m in modes_of(app) if isinstance(m, str) and m.startswith('modules:') for name in m[8:].split(',') if name] if role == 'backend' else [],
                              'reported_at': value(device_map.get(device, {}), 'last_seen'),
                              'evidence': 'registry role or Polari service container',
                              'health': 'not verified by registration'})
    # Older installers stored backend module configuration on the paired
    # frontend registration. Only transfer it when service containers prove
    # the same deployment on the same device; never infer from DNS alone.
    for provider in providers:
        if provider['component_role'] != 'backend' or provider['modules']:
            continue
        app = next(a for a in apps if value(a, 'name') == provider['app'] and value(a, 'device_name') == provider['device'])
        paired = {value(s, 'container').removesuffix('-backend') + '-frontend' for s in services_of(app, services) if value(s, 'container').endswith('-backend')}
        for candidate in apps:
            if value(candidate, 'is_mock', False) or value(candidate, 'device_name') != provider['device']:
                continue
            if any(value(s, 'container') in paired for s in services_of(candidate, services)):
                provider['modules'] = [name for m in modes_of(candidate) if isinstance(m, str) and m.startswith('modules:') for name in m[8:].split(',') if name]
                provider['deployment'] = value(candidate, 'name')
                provider['module_evidence'] = 'legacy paired frontend registration'
                break
    frontends = [p for p in providers if p['component_role'] == 'frontend']
    backends = [p for p in providers if p['component_role'] == 'backend']
    missing = [role for role, entries in [('frontend', frontends), ('backend', backends)] if not entries]
    return {'instances': providers, 'frontend_count': len(frontends), 'backend_count': len(backends),
            'minimum_deployment_present': not missing, 'missing_roles': missing,
            'health_verified': False,
            'message': ('Minimum Polari deployment reported: at least one frontend and one backend across the Isle. Endpoint health and frontend/backend connectivity still require verification.' if not missing else 'Minimum Polari deployment incomplete: missing ' + ' and '.join(missing) + '.'),
            'recommended_shape': 'Usually one frontend and multiple backends; additional frontends are supported.'}
