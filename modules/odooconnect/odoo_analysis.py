"""
@module odooconnect.odoo_analysis

Duck-typed status/catalog over OdooInstanceConfig rows — stdlib only,
takes any manager exposing .objectTables (selftests pass a
SimpleNamespace). Probing goes through an injectable handle factory so
selftests point it at a stub server.

@consumers odooconnect.odoo_api, odooconnect.selftest_odoo
"""

from odooconnect.odoo_client import OdooHandle


def _rows(manager, class_name):
    table = getattr(manager, 'objectTables', {}).get(class_name, {})
    return list(table.values())


def odoo_configs(manager):
    """Catalog of config rows — knob states visible, secrets never."""
    rows = []
    for cfg in _rows(manager, 'OdooInstanceConfig'):
        rows.append({
            'name': getattr(cfg, 'name', ''),
            'displayName': getattr(cfg, 'display_name', ''),
            'baseUrl': getattr(cfg, 'base_url', ''),
            'db': getattr(cfg, 'db', ''),
            'mode': getattr(cfg, 'mode', ''),
            'urlEnv': getattr(cfg, 'url_env', ''),
            'authLogin': getattr(cfg, 'auth_login', ''),
            'authPasswordEnv': getattr(cfg, 'auth_password_env', ''),
            'pushEnabled': bool(getattr(cfg, 'push_enabled', False)),
            'readOnly': bool(getattr(cfg, 'read_only', False)),
            'notes': getattr(cfg, 'notes', ''),
        })
    return {'ok': True, 'configs': sorted(rows, key=lambda r: r['name'])}


def odoo_status(manager, handle_factory=OdooHandle, timeout=5):
    """Per-config live probe: reachable + server version via the
    unauthenticated common.version call (the db manager is disabled on
    the server, so no db listing — the row SAYS which db it is for).
    Refusals ride along per row; the endpoint itself always answers."""
    catalog = odoo_configs(manager)
    statuses = []
    for cfg in _rows(manager, 'OdooInstanceConfig'):
        handle = handle_factory(cfg, timeout=timeout)
        probe = handle.version()
        row = {
            'name': getattr(cfg, 'name', ''),
            'db': getattr(cfg, 'db', ''),
            'mode': getattr(cfg, 'mode', ''),
            'baseUrl': handle.base_url(),
            'pushEnabled': bool(getattr(cfg, 'push_enabled', False)),
            'readOnly': bool(getattr(cfg, 'read_only', False)),
            'reachable': bool(probe.get('ok')),
        }
        if probe.get('ok'):
            info = probe.get('result') or {}
            row['serverVersion'] = info.get('server_version', '')
        else:
            row['refusal'] = probe.get('refusal', '')
            if probe.get('suggestion'):
                row['suggestion'] = probe['suggestion']
        statuses.append(row)
    return {'ok': True,
            'configCount': len(catalog.get('configs', [])),
            'statuses': sorted(statuses, key=lambda r: r['name'])}
