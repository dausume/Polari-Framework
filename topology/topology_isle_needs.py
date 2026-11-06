"""
@cross-cutting
@module topology.topology_isle_needs

tpl-4 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md, "Needs an isle"): which topology features need an isle, whether THIS backend
has one, and the fallback when it does not, so a page never shows a blank or stale panel where isle data would be.

The isle counts as present on evidence only (never assumed):
    configured   ISLE_CORE_API is set (the isle instance generator writes it for backend roles)
    reported     the isle has posted devices here (IsleDevice rows, from /api/islemesh/ingest/device)
Either is enough to say "present"; the words name which. A compose stack started from its own files has neither, and every
Polari-only feature still works.

    isle_presence(manager) -> {present, configured, devices, words}
    isle_needs(manager)    -> {ok, isle, features: [{key, title, layer, requiresIsle, available, words, fallback}]}
"""
import os

#: The Polari-only features (the separation map's "Fully Polari"): available with or without an isle.
POLARI_FEATURES = (
    ('placement', 'Module placement (which modules each instance runs)'),
    ('dependencies', 'Module dependencies and their providers'),
    ('ownership', 'Object ownership (class -> module -> instance -> database)'),
    ('apps', 'Polari Apps (module compositions)'),
    ('engine-ladder', 'Engine resolution (knob -> local -> binding row -> topology provider)'),
    ('connections', 'Service connections and their generated artifacts'),
    ('drift', 'Drift and reallocation suggestions'),
    ('testing', 'Testing over the topology'),
)


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def isle_presence(manager):
    origin = (os.environ.get('ISLE_CORE_API') or '').strip()
    devices = sorted({getattr(r, 'name', '') or getattr(r, 'device_name', '') for r in _rows(manager, 'IsleDevice')} - {''})
    present = bool(origin or devices)
    parts = []
    if origin:
        parts.append('configured: ISLE_CORE_API = %s' % origin)
    if devices:
        parts.append('reported: %d device%s (%s)' % (len(devices), '' if len(devices) == 1 else 's', ', '.join(devices)))
    return {'present': present, 'configured': origin, 'devices': devices,
            'words': '; '.join(parts) if parts else 'no isle: ISLE_CORE_API is unset and no isle has reported devices here'}


def isle_needs(manager):
    isle = isle_presence(manager)
    present, origin, devices = isle['present'], isle['configured'], isle['devices']
    registry_bound = [r for r in _rows(manager, 'IsleEngine')
                      if getattr(r, 'bound', False) and (getattr(r, 'notes', '') or '').startswith('[isle registry]')]
    observed = [m for m in _rows(manager, 'PolariNodeMachine')
                if getattr(m, 'resource_source', '') not in ('', 'unknown') and getattr(m, 'total_ram_mb', 0)]
    needs = [
        ('discovery', 'Finding other devices and their Polari instances', bool(devices),
         ('the isle reports %d device%s' % (len(devices), '' if len(devices) == 1 else 's')) if devices
         else ('configured, but no device has reported here yet' if origin else 'needs an isle: devices are discovered by the isle agents'),
         'list peers by hand (tpl-2), or `pol topology report` over ssh'),
        ('engine-auto-routing', 'Routing to an engine on another device with no URL knob', bool(origin),
         ('the isle engine registry at %s (%d engine%s bound from it)' % (origin, len(registry_bound), '' if len(registry_bound) == 1 else 's'))
         if origin else 'needs an isle: the engine registry lives on the isle core',
         'set the engine URL knob (e.g. BOARD_ENGINES_URL)'),
        ('trusted-names', 'Trusted HTTPS names (<name>.isle) for cross-device calls', present,
         'isle names and certificates from the isle CA' if present else 'needs an isle: the .isle names and their CA are the isle\'s',
         'your own TLS, or plain dev URLs'),
        ('device-resources', 'Device resources observed by the isle agents', bool(observed) or bool(devices),
         ('%d machine%s with observed resources' % (len(observed), '' if len(observed) == 1 else 's')) if observed
         else ('devices reported; resources not observed yet' if devices else 'needs an isle: the agents observe device resources'),
         '`pol topology observe` over ssh, or "capacity unknown"'),
        ('run-placement', 'Running a placement change (moving a module or instance)', present,
         'from the Isle App, through `pkexec isle ...` (web pages stay show-only)' if present
         else 'needs an isle: changes run through the Isle App with pkexec',
         'the suggestions plus `pol allocate` by hand'),
        ('network-view', 'The Isle Topology tab (devices, addresses, routes)', present,
         'the isle mirror in this backend (/api/islemesh/graph) and the Isle App' if present
         else 'needs an isle: there is no network layer to show',
         'hidden; the Polari topology still works'),
    ]
    features = [{'key': k, 'title': t, 'layer': 'polari', 'requiresIsle': False, 'available': True,
                 'words': 'Polari-only: works with or without an isle', 'fallback': ''} for k, t in POLARI_FEATURES]
    features += [{'key': k, 'title': t, 'layer': 'isle', 'requiresIsle': True, 'available': bool(a), 'words': w,
                  'fallback': '' if a else f} for k, t, a, w, f in needs]
    return {'ok': True, 'isle': isle, 'features': features}
