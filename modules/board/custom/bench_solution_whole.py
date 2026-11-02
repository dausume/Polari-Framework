"""
@module board.custom.bench_solution_whole

bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5, "Whole"): IS A BENCH SOLUTION WHOLE? It is, only when its Hardware, Firmware and Thermal
Solutions all exist, are complete, and each names the System its Bench System composes, and its conditions sit inside the Thermal System's range.
Derived on read from the rows, never stored; what is missing is said in words.

    whole(manager, name) -> {'ok', 'name', 'whole': bool, 'missing': [words], 'legs': {system|hardware|firmware|thermal|conditions: {'ref', 'ok', 'why'}}}
    listing(manager)     -> [{'name', 'title', 'whole', 'missing': n}]

Rows of other modules (cmod FirmwareSolution) are read by attribute from the manager's tables; nothing is imported from cmod.
"""
FIRMWARE_COMPLETE = ('built', 'run')


class NotFound(Exception):
    pass


def _table(manager, cls):
    return (getattr(manager, 'objectTables', None) or {}).get(cls, {}) or {}


def _row(manager, cls, name):
    return next((r for r in _table(manager, cls).values() if getattr(r, 'name', '') == name), None) if name else None


def _leg(ref, ok, why=''):
    return {'ref': ref, 'ok': bool(ok), 'why': '' if ok else why}


def _csv(text):
    return [x.strip() for x in str(text or '').split(',') if x.strip()]


def _hardware(manager, bs, system):
    ref = getattr(bs, 'hardware_solution', '')
    if not ref:
        return _leg(ref, False, 'no Hardware Solution named')
    row = _row(manager, 'HardwareSolution', ref)
    if row is None:
        return _leg(ref, False, "Hardware Solution %r does not exist" % ref)
    want = getattr(system, 'hardware_system', '') if system else ''
    have = getattr(row, 'system', '')
    if want and have and have != want:
        return _leg(ref, False, "Hardware Solution %r is of Hardware System %r; the Bench System composes %r" % (ref, have, want))
    undetermined = getattr(row, 'undetermined', '')
    if undetermined:
        return _leg(ref, False, "Hardware Solution %r is not complete: %s" % (ref, undetermined))
    return _leg(ref, True)


def _firmware(manager, bs, system):
    ref = getattr(bs, 'firmware_solution', '')
    if not ref:
        return _leg(ref, False, 'no Firmware Solution named')
    row = _row(manager, 'FirmwareSolution', ref)
    if row is None:
        return _leg(ref, False, "Firmware Solution %r does not exist" % ref)
    want = getattr(system, 'firmware_system', '') if system else ''
    have = getattr(row, 'graph', '')
    if want and have != want:
        return _leg(ref, False, "Firmware Solution %r is built on graph %r; the Bench System composes %r" % (ref, have, want))
    status = getattr(row, 'status', '')
    if status not in FIRMWARE_COMPLETE:
        return _leg(ref, False, "Firmware Solution %r is %s, not built" % (ref, status or 'unknown'))
    return _leg(ref, True)


def _thermal(manager, bs, system):
    ref = getattr(bs, 'thermal_solution', '')
    if not ref:
        return _leg(ref, False, 'no Thermal Solution named (open air with nothing added is still a Thermal Solution: make one and name it)')
    row = _row(manager, 'ThermalSolution', ref)
    if row is None:
        return _leg(ref, False, "Thermal Solution %r does not exist" % ref)
    want = getattr(system, 'thermal_system', '') if system else ''
    have = getattr(row, 'system', '')
    if want and have != want:
        return _leg(ref, False, "Thermal Solution %r follows Thermal System %r; the Bench System composes %r" % (ref, have, want))
    tsys = _row(manager, 'ThermalSystem', have)
    if tsys is None:
        return _leg(ref, False, "Thermal System %r does not exist" % have)
    allowed = _csv(getattr(tsys, 'mitigations_allowed', ''))
    for mname in _csv(getattr(row, 'mitigations', '')):
        m = _row(manager, 'ThermalMitigation', mname)
        if m is None:
            return _leg(ref, False, "Thermal Mitigation %r does not exist" % mname)
        if getattr(m, 'kind', '') not in allowed:
            return _leg(ref, False, "mitigation %r is a %s; Thermal System %r allows %s" % (mname, getattr(m, 'kind', ''), have, ', '.join(allowed) or 'nothing'))
    return _leg(ref, True)


def _conditions(manager, bs, system):
    ref = getattr(bs, 'conditions', '')
    if not ref:
        return _leg(ref, False, 'no Bench Conditions named')
    row = _row(manager, 'BenchConditions', ref)
    if row is None:
        return _leg(ref, False, "Bench Conditions %r do not exist" % ref)
    tsys = _row(manager, 'ThermalSystem', getattr(system, 'thermal_system', '')) if system else None
    if tsys is None:
        return _leg(ref, True)
    if getattr(row, 'air', 'open') != getattr(tsys, 'air', 'open'):
        return _leg(ref, False, "conditions %r are %s air; Thermal System %r is %s air" % (ref, getattr(row, 'air', ''), tsys.name, getattr(tsys, 'air', '')))
    lo, hi = float(getattr(row, 'ambient_min_c', 0)), float(getattr(row, 'ambient_max_c', 0))
    tlo, thi = float(getattr(tsys, 'ambient_min_c', 0)), float(getattr(tsys, 'ambient_max_c', 0))
    if lo < tlo or hi > thi:
        return _leg(ref, False, "conditions %r span %g..%g C; Thermal System %r is meant for %g..%g C" % (ref, lo, hi, tsys.name, tlo, thi))
    return _leg(ref, True)


def whole(manager, name):
    bs = _row(manager, 'BenchSolution', name)
    if bs is None:
        raise NotFound("no Bench Solution %r" % name)
    sref = getattr(bs, 'system', '')
    system = _row(manager, 'BenchSystem', sref)
    legs = {'system': _leg(sref, system is not None, 'no Bench System named' if not sref else "Bench System %r does not exist" % sref)}
    legs['hardware'] = _hardware(manager, bs, system)
    legs['firmware'] = _firmware(manager, bs, system)
    legs['thermal'] = _thermal(manager, bs, system)
    legs['conditions'] = _conditions(manager, bs, system)
    missing = [legs[k]['why'] for k in ('system', 'hardware', 'firmware', 'thermal', 'conditions') if not legs[k]['ok']]
    return {'ok': True, 'name': name, 'title': getattr(bs, 'title', ''), 'whole': not missing, 'missing': missing, 'legs': legs}


def legs(manager, name):
    """The whole check as rows, one per leg: {leg, ref, ok, why} (the Bench Solutions page's table)."""
    w = whole(manager, name)
    return [dict(leg=k, **w['legs'][k]) for k in ('system', 'hardware', 'firmware', 'thermal', 'conditions')]


def listing(manager):
    out = []
    for r in _table(manager, 'BenchSolution').values():
        if getattr(r, 'name', ''):
            w = whole(manager, r.name)
            out.append({'name': r.name, 'title': w['title'], 'whole': w['whole'], 'missing': len(w['missing'])})
    return sorted(out, key=lambda x: x['name'])
