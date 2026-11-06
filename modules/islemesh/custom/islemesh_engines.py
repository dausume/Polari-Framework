"""
@module islemesh.custom.islemesh_engines

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

fix 11 (COHERENT_ISLE_WORK_SPLIT.md, econ Claude 2026-11-06), the CONSUMER half: a backend
binds every engine the isle announces WITHOUT a hand ingest. `sync_from_registry` pulls the isle
core's registry (GET $ISLE_CORE_API/api/islemesh/engines, the existing door, TLS verified) at
boot (topology.topology_self.after_boot calls it before describing links) and on an explicit
refresh (POST /api/islemesh/engines/sync), binds each real entry through the SAME `bind_engine`
the ingest door uses, records the same IsleEngine row (`record_engine`), and retires
registry-sourced rows the registry no longer lists. Mock entries never bind. A missing `device`
(the installed core80 backend omits it) stays 'unknown' - never a guessed host. Failures are
words in the result, retryable, and never a claim of compile/simulation readiness.

@consumers
  - islemesh.islemesh_api (ingest/engine, engines/sync)
  - topology.topology_self (after_boot -> sync_from_registry)
  - islemesh.islemesh_selftest
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
        # A live server whose binding table is still EMPTY has no
        # objectTables key for it yet; the class is REGISTERED
        # (objectTyping), and the first engine on a fresh instance
        # must bind, never refuse. Without either, refuse honestly.
        tables = getattr(manager, 'objectTables', None) or {}
        registered = 'EngineProviderBinding' in tables or any(
            getattr(t, 'className', '') == 'EngineProviderBinding'
            for t in (getattr(manager, 'objectTyping', None) or []))
        if not registered:
            return None
        existing = None
        for row in (tables.get('EngineProviderBinding') or {}).values():
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


def _bind_reasoning(manager, app_name, url, save):
    """ai-3: reasoning → the managed reasoning config (the
    _bind_odoo shape, but the consumer is CONFIG, not a row):
    deploying an OpenAI-compatible server anywhere on the isle
    (LocalAI) sets this instance's active provider to
    openai_compatible with the app's /v1 base_url — the assistant
    follows the engine with no redeploy. Refuses (returns None)
    when reasoning_config is unavailable (host tool context)."""
    try:
        from polariApiServer import reasoning_config
    except ImportError:
        return None
    base_url = url.rstrip('/') + '/v1'
    reasoning_config.set_active('openai_compatible',
                                {'base_url': base_url})
    return 'reasoning_config:openai_compatible'


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
    # ti-3a: the hardware engine workers (board = the avr family)
    'board': ('topology', _bind_engine_row('board')),
    'esp': ('topology', _bind_engine_row('esp')),
    'formal': ('topology', _bind_engine_row('formal')),
    'pcb': ('topology', _bind_engine_row('pcb')),
    'bridge': ('topology', _bind_engine_row('bridge')),
    # osc-5: the oscilloscope emulator worker (instruments.custom.scope_engines reads the row)
    'scope': ('topology', _bind_engine_row('scope')),
    # ai-3: the consumer is the managed reasoning config itself.
    'reasoning': ('reasoning_config', _bind_reasoning),
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


# ---- fix 11, the consumer half: pull the isle's engine registry ----------------
REGISTRY_KNOB = 'ISLE_CORE_API'          # e.g. https://api.polari.isle ; unset = no isle (compose stacks keep working)
REGISTRY_PATH = '/api/islemesh/engines'  # the EXISTING registry door on the isle core (Codex's contract 2026-11-06)
REGISTRY_MARK = '[isle registry] '       # notes prefix on IsleEngine rows this pull wrote (so only those can be retired)


def registry_origin(env=None):
    env = os.environ if env is None else env
    return (env.get(REGISTRY_KNOB) or '').strip().rstrip('/')


def fetch_registry(origin, timeout=10):
    """GET <origin>/api/islemesh/engines through the outbound seam. TLS is verified by the
    interpreter's default context: no -k, no env override (a backend whose trust store lacks
    the isle root fails here in words - item 8 - and is never bypassed).
    Returns (entries, '') or (None, words)."""
    from polariApiServer import outbound
    url = origin + REGISTRY_PATH
    try:
        with outbound.http_request('peer', 'isle-core-registry', 'GET', url,
                                   means='rest', timeout=timeout, lib='urllib') as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001 - every transport failure becomes words, never a crash
        words = '%s: %s' % (type(exc).__name__, exc)
        if 'CERTIFICATE_VERIFY_FAILED' in words:
            words += " (this backend's trust store lacks the isle root - item 8 - not bypassed)"
        return None, 'registry unreachable at %s: %s' % (url, words)
    if not isinstance(body, dict) or body.get('ok') is not True \
            or not isinstance(body.get('engines'), list):
        return None, 'registry at %s answered without ok/engines' % url
    return body['engines'], ''


def _engine_rows(manager):
    return list(((getattr(manager, 'objectTables', None) or {}).get('IsleEngine') or {}).values())


def record_engine(manager, save, app_name, provides, url, device_name,
                  bound, bound_to, note, is_mock=False):
    """Upsert the IsleEngine row keyed '<app>@<kind>' - the ONE record the ingest door and
    the registry pull both write, so GET /api/islemesh/engines on this backend tells the same
    story whichever way the engine arrived."""
    from islemesh.objects.islemesh.IsleEngine import IsleEngine
    key = '%s@%s' % (app_name, provides)
    row = next((r for r in _engine_rows(manager) if getattr(r, 'name', '') == key), None)
    if row is None:
        row = IsleEngine(name=key, manager=manager)
    row.app_name = app_name
    row.device_name = device_name
    row.provides = provides
    row.url = url
    row.bound = bool(bound)
    row.bound_to = bound_to or ''
    row.is_mock = bool(is_mock)
    row.notes = note or ''
    save(row)
    return row


def retire_binding(manager, kind, url, delete=None):
    """Drop the EngineProviderBinding for `kind` ONLY when it still points at `url` (a
    binding someone set by hand to another url is never clobbered). Returns True if removed."""
    table = (getattr(manager, 'objectTables', None) or {}).get('EngineProviderBinding') or {}
    # a row sits in the table under its id AND (via save) under its name: drop every reference
    hits = [(key, row) for key, row in table.items()
            if getattr(row, 'name', '') == kind and getattr(row, 'url', '') == url]
    if not hits:
        return False
    seen = set()
    for key, row in hits:
        table.pop(key, None)
        if delete is not None and id(row) not in seen:
            seen.add(id(row))
            try:
                delete(row)
            except Exception:  # noqa: BLE001 - reported by the caller's words, never raised
                pass
    return True


def _default_save(manager):
    def save(row):
        try:
            manager.db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001 - same discipline as IsleMeshAPI._save
            pass
    return save


def _default_delete(manager):
    def delete(row):
        db = getattr(manager, 'db', None)
        row_id = getattr(row, 'id', None)
        if db is not None and hasattr(db, 'deleteRowsWhere') and row_id:
            db.deleteRowsWhere(type(row).__name__, 'id', row_id)
    return delete


def sync_from_registry(manager, source='boot', save=None, delete=None, fetch=None,
                       env=None, notify=False):
    """Pull the isle core's engine registry and bind what it lists (fix 11, consumer half).

    Returns {ok, source, origin, seen, bound[], unbound[], skipped_mock[], retired[], words}
    and never raises on transport or data problems. ok=False only when the registry could not
    be read (nothing changed then). `notify=True` (runtime paths) calls
    topology.topology_self.on_binding_changed afterwards; the boot path leaves that to
    after_boot, which describes links right after this returns."""
    out = {'ok': True, 'source': source, 'origin': '', 'seen': 0, 'bound': [], 'unbound': [],
           'skipped_mock': [], 'retired': [], 'words': ''}
    origin = registry_origin(env)
    if not origin:
        out['words'] = 'no isle registry configured (%s unset)' % REGISTRY_KNOB
        return out
    out['origin'] = origin
    save = save or _default_save(manager)
    delete = delete or _default_delete(manager)
    entries, words = (fetch or fetch_registry)(origin)
    if entries is None:
        out['ok'] = False
        out['words'] = words
        return out
    out['seen'] = len(entries)
    listed = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        app = str(entry.get('app') or '').strip()
        provides = str(entry.get('provides') or '').strip()
        url = str(entry.get('url') or '').strip()
        key = '%s@%s' % (app, provides)
        if not (app and provides and url):
            out['unbound'].append({'engine': str(entry.get('name') or key),
                                   'note': 'registry entry lacks app/provides/url; not bound'})
            continue
        if entry.get('is_mock'):
            out['skipped_mock'].append(key)   # mock entries never enter real placement
            continue
        listed.add(key)
        device = str(entry.get('device') or '').strip() or 'unknown'  # core80's installed backend omits it
        bound, bound_to, note = bind_engine(manager, app, provides, url, save)
        record_engine(manager, save, app, provides, url, device, bound, bound_to,
                      REGISTRY_MARK + note)
        if bound:
            out['bound'].append({'engine': key, 'bound_to': bound_to, 'url': url, 'device': device})
        else:
            out['unbound'].append({'engine': key, 'note': note, 'device': device})
    # retire what THIS pull once recorded and the registry no longer lists (never a direct ingest)
    for row in _engine_rows(manager):
        notes = getattr(row, 'notes', '') or ''
        if not notes.startswith(REGISTRY_MARK) or getattr(row, 'name', '') in listed:
            continue
        if not getattr(row, 'bound', False) and 'retired:' in notes:
            continue   # already retired on an earlier pull
        retire_binding(manager, getattr(row, 'provides', ''), getattr(row, 'url', ''), delete)
        row.bound = False
        row.bound_to = ''
        row.notes = REGISTRY_MARK + 'retired: no longer listed by the isle registry'
        save(row)
        out['retired'].append(getattr(row, 'name', ''))
    out['words'] = '%d listed, %d bound, %d unbound, %d mock skipped, %d retired (%s)' % (
        out['seen'], len(out['bound']), len(out['unbound']), len(out['skipped_mock']),
        len(out['retired']), origin)
    if notify and (out['bound'] or out['retired']):
        try:
            from topology.topology_self import on_binding_changed
            out['topology'] = on_binding_changed(manager, source='engine registry (%s)' % source)
        except ImportError:
            out['topology'] = {'ok': False, 'words': 'topology module absent'}
    return out
