"""
@module board.custom.esd_areas

esd-0 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): FLAGGING PIECES OF A BOARD AS ESD PROTECTION AREAS (EsdProtectionArea), on the Board's definition (any kind,
D-esd-3). The events themselves run in pcb.custom.esd_events (a PCB's deck).

  areas(manager, kind, definition)                 the flagged areas, one row each, with the test and the criterion in words
  flag(manager, kind, definition, body) -> (status, body)    {scope, target, inject_net?, protection_refs?, model?, level_v?, abs_max_v?, recover_*?,
                                                   document?, page_table?} - checked whole, refused in words; flagging the same piece again updates it
  unflag(manager, name) -> (status, body)
  set_quantity(manager, name, quantity, value) -> (status, body)   the page's edit box: level_v, abs_max_v, recover_pct, recover_mv, recover_us
With no manager (selftests) the rows live in this process only.
"""
import math

CLS = 'EsdProtectionArea'
_MEM = {CLS: {}}
QUANTITIES = {'level_v': (0.0, 30000.0), 'abs_max_v': (-1.0, 1e5), 'recover_pct': (0.0, 100.0), 'recover_mv': (0.0, 1e5), 'recover_us': (0.0, 1e6)}


def _fields():
    import inspect
    from board.objects.board.EsdProtectionArea import EsdProtectionArea
    return [k for k in inspect.signature(EsdProtectionArea.__init__).parameters if k not in ('self', 'manager')]


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _objs(manager):
    if manager is None:
        return list(_MEM[CLS].values())
    return list(((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).values())


def _find(manager, name):
    return next((o for o in _objs(manager) if _get(o, 'name') == name), None)


def _save(manager, name, fields):
    o = _find(manager, name)
    if manager is None:
        _MEM[CLS][name] = dict(o or {}, name=name, **fields)
        return _MEM[CLS][name]
    if o is None:
        from board.objects.board.EsdProtectionArea import EsdProtectionArea
        o = EsdProtectionArea(manager=manager, name=name, **fields)
    else:
        for k, v in fields.items():
            setattr(o, k, v)
    try:
        manager.db.saveInstanceInDB(o)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return o


def criterion_words(a):
    return ('peak against %s; back within max(%g %% of the no-event run, %g mV) by %g us after the event'
            % (('abs max %g V' % float(a['abs_max_v'])) if float(a['abs_max_v']) >= 0 else 'no absolute maximum given (break check undetermined)',
               float(a['recover_pct']), float(a['recover_mv']), float(a['recover_us'])))


def areas(manager, kind, definition):
    from pcb.custom.esd_events import MODELS
    out = []
    for o in sorted(_objs(manager), key=lambda o: _get(o, 'name')):
        if _get(o, 'definition_kind') != kind or _get(o, 'definition') != definition:
            continue
        a = {k: _get(o, k) for k in _fields()}
        m = MODELS.get(a['model'], {})
        out.append(dict(a, board=definition, test='%s at %g V (%s)' % (a['model'], float(a['level_v']), m.get('standard', 'unknown model')),
                        criterion=criterion_words(a), signed=False))
    return out


def flag(manager, kind, definition, body):
    from board.custom.footholds import KINDS
    from board.objects.board.EsdProtectionArea import EsdProtectionArea
    from pcb.custom.esd_events import MODELS
    if kind not in KINDS:
        return 400, {'ok': False, 'error': 'no definition kind %r - %s' % (kind, ' | '.join(KINDS))}
    body = body if isinstance(body, dict) else {}
    scope, target = body.get('scope', 'net'), str(body.get('target', '')).strip()
    if scope not in EsdProtectionArea.SCOPES:
        return 400, {'ok': False, 'error': 'scope must be one of %s' % ', '.join(EsdProtectionArea.SCOPES)}
    if not target:
        return 400, {'ok': False, 'error': 'target needs the %s to protect' % scope}
    model = body.get('model', 'hbm')
    if model not in MODELS:
        return 400, {'ok': False, 'error': 'model must be one of %s' % ', '.join(MODELS)}
    fields = {'definition_kind': kind, 'definition': definition, 'scope': scope, 'target': target, 'model': model,
              'inject_net': str(body.get('inject_net', '')), 'protection_refs': str(body.get('protection_refs', '')),
              'document': str(body.get('document', '')), 'page_table': str(body.get('page_table', '')), 'notes': str(body.get('notes', '')),
              'origin': 'cited' if body.get('document') else 'flagged on the page'}
    for q, (lo, hi) in QUANTITIES.items():
        if q in body:
            try:
                v = float(body[q])
            except (TypeError, ValueError):
                return 400, {'ok': False, 'error': '%s needs a number' % q}
            if not math.isfinite(v) or not lo <= v <= hi:
                return 400, {'ok': False, 'error': '%s must be within %g .. %g, got %r' % (q, lo, hi, body[q])}
            fields[q] = v
    name = '%s:%s:%s:%s' % (kind, definition, scope, target)
    if _find(manager, name) is None:   # a new area: the class defaults (D-esd-2's criterion), the model's second-highest level
        for k, v in (('level_v', float(MODELS[model]['levels'][-2])), ('abs_max_v', -1.0), ('recover_pct', 5.0), ('recover_mv', 50.0),
                     ('recover_us', 10.0)):
            fields.setdefault(k, v)
    _save(manager, name, fields)
    return 201, {'ok': True, 'name': name, 'rows': areas(manager, kind, definition)}


def unflag(manager, name):
    o = _find(manager, name)
    if o is None:
        return 404, {'ok': False, 'error': 'no ESD area %r' % name}
    if manager is None:
        _MEM[CLS].pop(name, None)
    else:
        table = (manager.objectTables or {}).get(CLS) or {}
        for k, v in list(table.items()):
            if v is o:
                table.pop(k)
        try:
            manager.db.deleteInstanceInDB(o)
        except Exception:  # noqa: BLE001 - an in-memory manager has no db
            pass
    return 200, {'ok': True, 'removed': name}


def set_quantity(manager, name, quantity, value):
    o = _find(manager, name)
    if o is None:
        return 404, {'ok': False, 'error': 'no ESD area %r' % name}
    if quantity not in QUANTITIES:
        return 400, {'ok': False, 'error': 'no quantity %r - %s' % (quantity, ', '.join(QUANTITIES))}
    lo, hi = QUANTITIES[quantity]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': '%s needs a number' % quantity}
    if not math.isfinite(v) or not lo <= v <= hi:
        return 400, {'ok': False, 'error': '%s must be within %g .. %g' % (quantity, lo, hi)}
    _save(manager, name, {quantity: v})
    return 200, {'ok': True, 'name': name, quantity: v}


UNITS = {'level_v': ('V', 'the test level'), 'abs_max_v': ('V', 'the protected pins\' absolute maximum, from their datasheet (-1 = not given)'),
         'recover_pct': ('%', 'recovered = back within this % of the no-event run ...'), 'recover_mv': ('mV', '... or within this many mV, whichever is larger ...'),
         'recover_us': ('us', '... by this long after the event')}


def toggle(manager, kind, definition, body):
    """Click-toggle (the page's row button): flag the piece, or unflag it when it is already flagged."""
    body = body if isinstance(body, dict) else {}
    name = '%s:%s:%s:%s' % (kind, definition, body.get('scope', 'net'), str(body.get('target', '')).strip())
    if _find(manager, name) is not None:
        return unflag(manager, name)
    return flag(manager, kind, definition, body)


def quantities(manager, name):
    o = _find(manager, name)
    if o is None:
        return []
    return [{'area': name, 'quantity': q, 'value': float(_get(o, q, -1.0)), 'unit': UNITS[q][0], 'meaning': UNITS[q][1], 'signed': q == 'abs_max_v'}
            for q in QUANTITIES]
