"""
@cross-cutting
@module topology.topology_isle_needs

tpl-4 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md, "Needs an isle"): which topology features need an isle, what this backend
has OBSERVED about each, and the fallback, so a page never shows a blank or stale panel where isle data would be.

Codex's review (2026-11-06): configuration is not readiness. Each isle feature carries a STATE from existing, timestamped
observations only (no network probe per GET), never a bare "available":

    not-configured     nothing here points at an isle (ISLE_CORE_API unset, nothing reported)
    configured         ISLE_CORE_API is set; nothing has been observed for this feature yet ("not yet evaluated")
    last-reported      an observation exists; `observedAt` is its newest timestamp and `ageSeconds` its age
    stale              the newest observation is older than POLARI_ISLE_EVIDENCE_MAX_AGE_S (knob; default 86400 s)

A configured origin never claims trusted HTTPS, routable engines or a runnable placement; `last-reported` means "the isle
said so at <time>", not "verified working now". The fallback is shown for every state except a fresh `last-reported`.

Placement changes are ONE shared operation (the isle CLI); its authorization depends on where it runs (sudo over SSH, or
pkexec from the Isle App bridge). This backend only names the supported command; it never claims it is executable here.

    isle_presence(manager) -> {configured, reported: {devices, lastSeen}, words}
    isle_needs(manager, now=None) -> {ok, evaluatedAt, maxAgeS, isle, features: [{key, title, layer, requiresIsle, state,
                                       observedAt, ageSeconds, evidence: [{source, observedAt, words}], words, fallback}]}
"""
import os
from datetime import datetime, timezone

#: The Polari-only features (the separation map's "Fully Polari"): state 'supported' with or without an isle.
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
STATES = ('not-configured', 'configured', 'last-reported', 'stale')
MAX_AGE_KNOB = 'POLARI_ISLE_EVIDENCE_MAX_AGE_S'
DEFAULT_MAX_AGE_S = 86400


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def _ts(value):
    """An ISO timestamp -> aware datetime, else None (an unparseable stamp is no evidence)."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _max_age():
    try:
        return max(1, int(os.environ.get(MAX_AGE_KNOB) or DEFAULT_MAX_AGE_S))
    except ValueError:
        return DEFAULT_MAX_AGE_S


def isle_presence(manager):
    origin = (os.environ.get('ISLE_CORE_API') or '').strip()
    devices = [r for r in _rows(manager, 'IsleDevice') if getattr(r, 'name', '') and not getattr(r, 'is_mock', False)]
    seen = [s for s in (_ts(getattr(d, 'last_seen', '')) for d in devices) if s]
    last = max(seen).isoformat() if seen else ''
    parts = ['configured: ISLE_CORE_API = %s' % origin] if origin else []
    if devices:
        parts.append('reported: %d device%s (%s), newest report %s' % (
            len(devices), '' if len(devices) == 1 else 's', ', '.join(sorted(d.name for d in devices)), last or 'with no timestamp'))
    return {'configured': origin, 'reported': {'devices': sorted(d.name for d in devices), 'lastSeen': last},
            'words': '; '.join(parts) if parts else 'no isle: ISLE_CORE_API is unset and no isle has reported devices here'}


def _feature(key, title, origin, evidence, now, max_age, words_none, words_configured, fallback):
    stamps = [_ts(e['observedAt']) for e in evidence if _ts(e['observedAt'])]
    newest = max(stamps) if stamps else None
    if newest is not None:
        age = int((now - newest).total_seconds())
        state = 'stale' if age > max_age else 'last-reported'
        words = '; '.join(e['words'] for e in evidence)
        if state == 'stale':
            words = 'STALE (%d s old, over %s=%d): %s' % (age, MAX_AGE_KNOB, max_age, words)
    else:
        age, state = None, ('configured' if origin else 'not-configured')
        words = words_configured if origin else words_none
    return {'key': key, 'title': title, 'layer': 'isle', 'requiresIsle': True, 'state': state,
            'observedAt': newest.isoformat() if newest else '', 'ageSeconds': age, 'evidence': evidence, 'words': words,
            'fallback': '' if state == 'last-reported' else fallback}


def isle_needs(manager, now=None):
    now = now or datetime.now(timezone.utc)
    max_age = _max_age()
    isle = isle_presence(manager)
    origin = isle['configured']
    devices = [r for r in _rows(manager, 'IsleDevice') if getattr(r, 'name', '') and not getattr(r, 'is_mock', False)]
    dev_ev = [{'source': 'IsleDevice:%s' % d.name, 'observedAt': getattr(d, 'last_seen', '') or '',
               'words': 'the isle reported %s' % d.name} for d in devices]
    bindings = {getattr(b, 'name', ''): b for b in _rows(manager, 'EngineProviderBinding')}
    eng_ev = []
    for e in _rows(manager, 'IsleEngine'):
        if not getattr(e, 'bound', False) or not (getattr(e, 'notes', '') or '').startswith('[isle registry]'):
            continue
        b = bindings.get(getattr(e, 'provides', ''))
        eng_ev.append({'source': 'EngineProviderBinding:%s' % getattr(e, 'provides', ''),
                       'observedAt': getattr(b, 'bound_at', '') if b is not None else '',
                       'words': '%s bound from the isle registry -> %s' % (getattr(e, 'name', ''), getattr(e, 'url', ''))})
    res_ev = [{'source': 'PolariNodeMachine:%s' % getattr(m, 'name', ''), 'observedAt': getattr(m, 'resource_observed_at', '') or '',
               'words': '%s resources observed (%s)' % (getattr(m, 'name', ''), getattr(m, 'resource_source', ''))}
              for m in _rows(manager, 'PolariNodeMachine')
              if getattr(m, 'resource_source', '') not in ('', 'unknown') and getattr(m, 'resource_observed_at', '')]
    not_evaluated = 'configured; not yet evaluated (no observation recorded here)'
    features = [{'key': k, 'title': t, 'layer': 'polari', 'requiresIsle': False, 'state': 'supported', 'observedAt': '',
                 'ageSeconds': None, 'evidence': [], 'words': 'Polari-only: works with or without an isle', 'fallback': ''}
                for k, t in POLARI_FEATURES]
    features += [
        _feature('discovery', 'Finding other devices and their Polari instances', origin, dev_ev, now, max_age,
                 'needs an isle: devices are discovered by the isle agents', 'configured; no device has reported here yet',
                 'list peers by hand (tpl-2), or `pol topology report` over ssh'),
        _feature('engine-auto-routing', 'Routing to an engine on another device with no URL knob', origin,
                 [e for e in eng_ev if e['observedAt']] or [], now, max_age,
                 'needs an isle: the engine registry lives on the isle core',
                 'configured; no engine bound from the isle registry yet (see `pol engines list`)' if not eng_ev
                 else 'configured; engines bound from the registry carry no timestamp yet',
                 'set the engine URL knob (e.g. BOARD_ENGINES_URL)'),
        # No TLS observation is recorded by this backend: configuration never claims trust.
        _feature('trusted-names', 'Trusted HTTPS names (<name>.isle) for cross-device calls', origin, [], now, max_age,
                 'needs an isle: the .isle names and their CA are the isle\'s', not_evaluated + '; configured is not trusted',
                 'your own TLS, or plain dev URLs'),
        _feature('device-resources', 'Device resources observed by the isle agents', origin, res_ev, now, max_age,
                 'needs an isle: the agents observe device resources',
                 'configured; devices reported but no resources observed yet' if devices else not_evaluated,
                 '`pol topology observe` over ssh, or "capacity unknown"'),
        # One shared operation; this backend names it and never claims it can run it.
        _feature('run-placement', 'Running a placement change (moving a module or instance)', origin, [], now, max_age,
                 'needs an isle: the shared isle operation places instances on devices',
                 'supported operation: `isle polari module move <m> --from A --to B` / `isle polari instance deploy` (the shared '
                 'CLI; authorized by sudo over SSH, or pkexec from the Isle App); not evaluated as executable from here',
                 'the suggestions plus `pol allocate` by hand'),
        _feature('network-view', 'The Isle Topology tab (devices, addresses, routes)', origin, dev_ev, now, max_age,
                 'needs an isle: there is no network layer to show', 'configured; no device has reported here yet',
                 'hidden; the Polari topology still works'),
    ]
    return {'ok': True, 'evaluatedAt': now.isoformat(), 'maxAgeS': max_age, 'isle': isle, 'features': features}
