"""
@module cmod.custom.purpose_derived

The two things about a Purpose that are WORKED OUT every time they are asked and never stored on the Purpose
(FIRMWARE_GENERATION_MODULE_PLAN.md §7.8.2, §8.3): `resolution` ("can it run here?", from the real HardwareBindings) and
`observed_summary` ("on each device", from the PurposeObservation rows, the weakest device). Pure over rows already produced
elsewhere (`cmod.custom.binding`, `cmod.custom.firmware`); a manager only to read live rows. Plus `record_observation`, the
backend's one writer of a PurposeObservation (the HTTP door calls it too, after refusing anyone who is not the backend).
"""
import datetime
import json

FULFILLMENTS = ('unknown', 'satisfied', 'at-risk', 'violated')
HEALTHS = ('unknown', 'healthy', 'degraded', 'failed')


def _graphs_of(cap):
    """The graphs the Purpose's c-device tasks come from (its own graph first)."""
    seen = [cap.get('graph', '')] if cap.get('graph') else []
    try:
        tasks = json.loads(cap.get('tasks_by_runtime_json') or '{}')
    except Exception:  # noqa: BLE001
        tasks = {}
    for ref in tasks.get('c-device') or []:
        g = ref.partition(':')[0]
        if g and g not in seen:
            seen.append(g)
    return seen


def resolution(cap, manager=None):
    """{state, why, bindings} — DERIVED from the actual HardwareBindings, never stored.
    resolved   a valid HardwareBinding lays a firmware solution over the Purpose's graph (and every task it names exists)
    unresolved there is nothing to bind: no tasks, or no firmware solution over its graph
    blocked    a binding exists but none is valid, or a named task does not exist — `why` is the validator's own reason."""
    from cmod.custom import binding as BIND
    from cmod.custom import capabilities as CAP
    from cmod.custom import firmware as FW
    try:
        tasks = json.loads(cap.get('tasks_by_runtime_json') or '{}')
    except Exception:  # noqa: BLE001
        tasks = {}
    if not any(tasks.get(r) for r in CAP.RUNTIMES):
        return {'state': 'unresolved', 'why': 'it names no tasks yet, so there is nothing to put on a board', 'bindings': []}
    ok, why = CAP.validate(cap, manager=manager)
    if not ok:
        return {'state': 'blocked', 'why': why, 'bindings': []}
    solutions = [s for s in (FW.solution_for_graph(g, manager=manager) for g in _graphs_of(cap)) if s]
    if not solutions:
        return {'state': 'unresolved', 'why': 'no firmware solution lays out graph %s, so no binding can exist' % (cap.get('graph') or '?'),
                'bindings': []}
    found = []
    for sol in solutions:
        for b in BIND.bindings_for_solution(sol['name'], manager=manager):
            found.append({'name': b['name'], 'status': b['status'], 'why': b.get('why') or ''})
    good = [b for b in found if b['status'] == 'valid']
    if good:
        return {'state': 'resolved', 'why': 'bound: %s (valid)' % ', '.join(b['name'] for b in good), 'bindings': found}
    if not found:
        return {'state': 'unresolved', 'why': 'firmware solution %s has no binding to any board' % solutions[0]['name'], 'bindings': []}
    reason = '; '.join('%s is %s%s' % (b['name'], b['status'], (': ' + b['why']) if b['why'] else '') for b in found)
    return {'state': 'blocked', 'why': reason, 'bindings': found}


def _observations(purpose, manager):
    if manager is None:
        return []
    return [r for r in ((getattr(manager, 'objectTables', None) or {}).get('PurposeObservation', {}) or {}).values()
            if getattr(r, 'purpose', '') == purpose]


def observed_summary(cap, manager=None):
    """{summary, weakest, devices[]} — DERIVED from the per-device PurposeObservation rows: the WEAKEST device decides
    (fulfillment violated < at-risk < unknown < satisfied; health failed < degraded < unknown < healthy). No rows = nothing
    deployed has reported ("unknown"), said plainly."""
    rows = _observations(cap.get('name', ''), manager)
    devices = [{'board_instance': r.board_instance, 'fulfillment': r.fulfillment, 'health': r.health, 'why': r.why,
                'observed_at': r.observed_at, 'evidence': r.evidence} for r in rows]
    if not devices:
        return {'summary': 'unknown: no deployed board has reported on this yet', 'weakest': None, 'devices': []}
    f_rank = {'violated': 0, 'at-risk': 1, 'unknown': 2, 'satisfied': 3}
    h_rank = {'failed': 0, 'degraded': 1, 'unknown': 2, 'healthy': 3}
    weakest = min(devices, key=lambda d: (f_rank.get(d['fulfillment'], 2), h_rank.get(d['health'], 2), d['board_instance']))
    return {'summary': '%s: %s, %s%s' % (weakest['board_instance'], weakest['fulfillment'], weakest['health'],
                                          (' (%s)' % weakest['why']) if weakest['why'] else ''),
            'weakest': weakest, 'devices': sorted(devices, key=lambda d: d['board_instance'])}


def record_observation(manager, purpose, board_instance, fulfillment, health, why='', evidence='', observed_at=''):
    """(ok, why, row-dict) — the backend's writer: upserts the PurposeObservation '<purpose>@<board_instance>'. Refuses by name
    an unknown purpose, a missing board instance, or a word outside the two scales."""
    purposes = {getattr(r, 'name', '') for r in ((getattr(manager, 'objectTables', None) or {}).get('CapabilityDefinition', {}) or {}).values()}
    if purpose not in purposes:
        return False, 'no Purpose named %r' % purpose, None
    if not board_instance:
        return False, "'board_instance' is required: an observation is about one deployed board", None
    if fulfillment not in FULFILLMENTS:
        return False, "'fulfillment' must be one of %s" % ', '.join(FULFILLMENTS), None
    if health not in HEALTHS:
        return False, "'health' must be one of %s" % ', '.join(HEALTHS), None
    from cmod.objects.cmod.PurposeObservation import PurposeObservation
    row = {'name': '%s@%s' % (purpose, board_instance), 'purpose': purpose, 'board_instance': board_instance,
           'fulfillment': fulfillment, 'health': health, 'why': why or '', 'evidence': evidence or '',
           'observed_at': observed_at or datetime.datetime.now().isoformat(timespec='seconds')}
    table = manager.objectTables.setdefault('PurposeObservation', {})
    existing = next((r for r in table.values() if r.name == row['name']), None)
    if existing is not None:
        for k, v in row.items():
            setattr(existing, k, v)
        obj = existing
    else:
        obj = PurposeObservation(manager=manager, **row)
        table[obj.id] = obj
    db = getattr(manager, 'db', None)
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(obj)
    return True, 'recorded', row
