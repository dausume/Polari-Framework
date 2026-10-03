"""
@module hwnocode.custom.derive

THE BACKEND NODE'S ARITHMETIC (uno-temp-split, plan §4 h) — registered as the AnalysisDefinition `hwnocode-temp-derive` and run by
the engine's EXISTING AnalysisCall node (`fn(manager, **params) -> dict`, polariNoCode.analysis_calls): keep this frame's sample
and return the moving average of temp_c over the last `window` samples. The threshold decision and the write of the derived
state are the engine's own ConditionalChain / VariableAssignment / StateChangeCommit nodes — not here.

Storage is bounded: `SimRigTempSample` is a RING of `keep` slots per source row (slot = seq % keep, the oldest overwritten; no
deletes), the cursor `samples` lives on the `SimRigTempDerived` row (created on the first frame) — the orchestrator idiom of
polariNoCode.graph_compilers.advance: state persisted on a domain row between complete runs.
"""
import datetime


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values())


def _create(manager, cls, fields):
    """A new row through the typing's create path (registered in the tree), saved once."""
    from types import SimpleNamespace
    import uuid
    typing = (getattr(manager, 'objectTypingDict', None) or {}).get(cls)
    if typing is not None and hasattr(typing, 'getCreateMethod'):
        inst = typing.getCreateMethod(returnTupWithParams=True)(**fields, manager=manager)
    else:   # a manager without typing (selftests): a plain row in objectTables
        inst = SimpleNamespace(id=uuid.uuid4().hex[:10], **fields)
        manager.objectTables.setdefault(cls, {})[inst.id] = inst
    _save(manager, inst)
    return inst


def _save(manager, inst):
    """One row, one save — measured (hn-0, on the twin): a debounced whole-tree persist per burst was WORSE at 10 Hz (a
    persistTree every 3 s stalls every other commit for up to seconds), so the sample row is saved alone. The derived row's
    cursor is NOT saved here: the engine's StateChangeCommit saves that same row a moment later in the same run."""
    from polariNoCode.event_dispatcher import save_instance
    try:
        save_instance(manager, inst)
    except Exception as e:  # never break the run on a persistence hiccup — the row in memory is still right
        print('[hwnocode] could not persist %s: %s' % (getattr(inst, 'name', '?'), e), flush=True)


def temp_derive(manager, object='', uptime_ms=0, temp_c=0.0, window=5, keep=600, solution=''):
    """One frame → one sample in the ring + the moving average ending at it."""
    name = str(object or '')
    if not name:
        return {'ok': False, 'error': 'no source object (the trigger payload names the SimRigState row)'}
    window = max(1, int(window or 1))
    keep = max(window, int(keep or window))
    now = datetime.datetime.now().isoformat(timespec='milliseconds')
    derived = next((r for r in _rows(manager, 'SimRigTempDerived') if getattr(r, 'name', '') == name), None)
    if derived is None:
        derived = _create(manager, 'SimRigTempDerived', {'name': name, 'solution': solution, 'window': window, 'samples': 0})
    seq = int(getattr(derived, 'samples', 0) or 0)
    slot = seq % keep
    ring = {getattr(r, 'name', ''): r for r in _rows(manager, 'SimRigTempSample') if getattr(r, 'source_object', '') == name}
    vals = [float(temp_c or 0.0)]
    for back in range(1, window):
        if seq - back < 0:
            break
        prev = ring.get('%s#%04d' % (name, (seq - back) % keep))
        if prev is None or int(getattr(prev, 'seq', -1)) != seq - back:
            break
        vals.append(float(getattr(prev, 'temp_c', 0.0) or 0.0))
    avg = sum(vals) / len(vals)
    fields = {'source_object': name, 'seq': seq, 'slot': slot, 'uptime_ms': int(uptime_ms or 0), 'temp_c': float(temp_c or 0.0),
              'temp_avg': avg, 'window': len(vals), 'written_at': now}
    row = ring.get('%s#%04d' % (name, slot))
    if row is None:
        _create(manager, 'SimRigTempSample', dict(fields, name='%s#%04d' % (name, slot)))
    else:
        for k, v in fields.items():
            setattr(row, k, v)
        _save(manager, row)
    derived.samples = seq + 1      # persisted by the StateChangeCommit node that follows (same run, same row)
    derived.updated_at = now
    return {'ok': True, 'temp_avg': avg, 'samples': seq + 1, 'slot': slot, 'window_used': len(vals)}


def chart_rows(manager, object='', last=300):
    """The chart's long rows, oldest first: uptime_ms (s), temp_c, temp_avg — the two series of the configured graph."""
    rows = [r for r in _rows(manager, 'SimRigTempSample') if not object or getattr(r, 'source_object', '') == object]
    rows.sort(key=lambda r: int(getattr(r, 'seq', 0) or 0))
    rows = rows[-int(last or 300):]
    return [{'uptime_s': round(int(getattr(r, 'uptime_ms', 0) or 0) / 1000.0, 3), 'uptime_ms': int(getattr(r, 'uptime_ms', 0) or 0),
             'temp_c': float(getattr(r, 'temp_c', 0.0) or 0.0), 'temp_avg': round(float(getattr(r, 'temp_avg', 0.0) or 0.0), 4),
             'seq': int(getattr(r, 'seq', 0) or 0), 'source_object': getattr(r, 'source_object', '')} for r in rows]
