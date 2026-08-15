"""
@module islemesh.islemesh_engines

The engine BINDER (handoff §20.4): turn an isle app's engine
declaration into a live polari provider wiring. An installed isle
app that `provides` a capability becomes an ENGINE polari modules
resolve — automatically, the moment it is deployed.

Design: one KIND -> consumer map. Each consumer is a small function
that upserts THAT module's own config row (odoo → OdooInstanceConfig
.base_url; the generic ladder → a ServiceConnection-style knob).
The consuming module may be ABSENT on this instance — then the
engine is recorded available-but-unbound (honest, never silently
dropped), and the SAME declaration binds later when the module
lands. No import-time dependency on any consumer module: every
binder imports lazily and refuses cleanly if its module is gated
off.

@consumers
  - islemesh.islemesh_api (ingest/engine)
  - islemesh.selftest_islemesh
"""


def _bind_odoo(manager, app_name, url, save):
    """business-ops → odoo: upsert an OdooInstanceConfig whose
    base_url points at the isle app. Refuses (returns None) if the
    odooconnect module is not present on this instance."""
    try:
        from odooconnect.odoo_basis import OdooInstanceConfig
    except ImportError:
        return None
    tables = getattr(manager, 'objectTables', None) or {}
    existing = None
    for row in tables.get('OdooInstanceConfig', {}).values():
        if getattr(row, 'name', '') == app_name:
            existing = row
            break
    if existing is None:
        existing = OdooInstanceConfig(
            name=app_name, display_name=app_name, base_url=url,
            db=app_name, mode='simulation', is_prior=False,
            notes='bound from isle app deploy --engine',
            manager=manager)
    else:
        existing.base_url = url
    save(existing)
    return 'OdooInstanceConfig:%s' % app_name


def _bind_engine_row(engine):
    """sep-4: the generic binder for ladder-resolved engines (msci /
    cad) — upsert the EngineProviderBinding row, the ROW FORM of the
    *_ENGINES_URL knob. The consumers' resolution ladders read it
    between the env knob and the topology resolve, so an
    isle-deployed engine wires without a redeploy. Refuses when the
    topology classes are absent (host tool context)."""
    def bind(manager, app_name, url, save):
        try:
            from topology.topology_modules import (
                EngineProviderBinding)
        except ImportError:
            return None
        tables = getattr(manager, 'objectTables', None) or {}
        if 'EngineProviderBinding' not in tables:
            return None
        existing = None
        for row in tables['EngineProviderBinding'].values():
            if getattr(row, 'name', '') == engine:
                existing = row
                break
        import datetime
        now = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        if existing is None:
            existing = EngineProviderBinding(
                name=engine, url=url, bound_from=app_name,
                bound_at=now, is_prior=False,
                notes='bound from isle app deploy --engine',
                manager=manager)
        else:
            existing.url = url
            existing.bound_from = app_name
            existing.bound_at = now
        save(existing)
        return 'EngineProviderBinding:%s' % engine
    return bind


#: kind -> (consumer label, binder). The label is what an unbound
#: engine WOULD wire, so the honest "available but <module> absent"
#: message can name it.
_BINDERS = {
    'business-ops': ('odooconnect', _bind_odoo),
    'odoo': ('odooconnect', _bind_odoo),
    # sep-4: ladder-resolved engines — the binding row IS the wiring
    # (any instance's remote seam reads it), so the consumer label
    # names the row class, not a module that must be present.
    'msci': ('topology', _bind_engine_row('msci')),
    'cad': ('topology', _bind_engine_row('cad')),
}


def bind_engine(manager, app_name, provides, url, save):
    """Wire one engine declaration. Returns
    (bound: bool, bound_to: str, note: str) — bound_to names the
    polari row written (or the consumer that was absent)."""
    entry = _BINDERS.get(provides)
    if entry is None:
        return (False, '',
                'no polari consumer for engine kind %r yet '
                '(recorded; add a binder to wire it)' % provides)
    consumer, binder = entry
    result = binder(manager, app_name, url, save)
    if result is None:
        return (False, consumer,
                'engine available; %s module not present on this '
                'instance — binds when it lands' % consumer)
    return (True, result, 'wired %s -> %s' % (result, url))
