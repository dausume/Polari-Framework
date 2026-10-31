"""
@module pcb.custom.temperature_inputs

tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md; the user's words 2026-10-31: "A number of parts have temperature tolerances and their drive and
signal data may vary with temperature"): WHAT A PERSON GIVES about a part's temperature behaviour - its rated operating range and, for an R / C / L,
its temperature coefficients (PartTemperatureBehaviour). The deck (pcb.custom.kicad_spice.build_deck `coefficients`) writes the coefficients as
ngspice's tc1 / tc2; the range is checked against every temperature a part is simulated at (pcb.custom.spice_temperature).

  parts(manager, board, rows=None)                  one row per part of the deck: what it is, its rated range, its coefficients, where they came from
  quantities(manager, board, ref)                   LONG FORM, one row per number a person can give (the page edits `value`; every row is signed)
  set_quantity(manager, board, ref, quantity, value) -> (status, body)   PUT; clear_quantity(...) -> (status, body)   DELETE (back to not given)
  behaviour(manager, board, ref, symbol=None)       {t_min_c, t_max_c, tc1_ppm_k, tc2_ppm_k2, given: set, name, words} or None
  coefficients(manager, board, rows=None)           {ref: (tc1 1/K, tc2 1/K2, origin)} for the R, C, L parts with a given coefficient
With no manager (selftests) the rows live in this process only.
"""
import math

CLS = 'PartTemperatureBehaviour'
_MEM = {CLS: {}}
PASSIVES = ('R', 'C', 'L')

#: quantity -> (unit, meaning)
QUANTITIES = {
    't_min_c': ('C', 'the datasheet\'s lowest operating temperature'),
    't_max_c': ('C', 'the datasheet\'s highest operating temperature'),
    'tc1_ppm_k': ('ppm/K', 'first-order temperature coefficient - a resistor\'s TCR, a capacitor\'s ppm/K (R, C, L only: ngspice\'s tc1 = this x 1e-6)'),
    'tc2_ppm_k2': ('ppm/K2', 'second-order temperature coefficient (R, C, L only: ngspice\'s tc2 = this x 1e-6)'),
}


def _objs(manager):
    if manager is None:
        return list(_MEM[CLS].values())
    return list(((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).values())


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _find(manager, name):
    return next((o for o in _objs(manager) if _get(o, 'name') == name), None)


def _save(manager, name, fields):
    o = _find(manager, name)
    if manager is None:
        _MEM[CLS][name] = dict(o or {}, name=name, **fields)
        return _MEM[CLS][name]
    if o is None:
        from pcb.objects.pcb.PartTemperatureBehaviour import PartTemperatureBehaviour as C
        o = C(manager=manager, name=name, **fields)
    else:
        for k, v in fields.items():
            setattr(o, k, v)
    try:
        manager.db.saveInstanceInDB(o)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return o


def _given(o):
    return {g for g in (_get(o, 'given', '') or '').split(',') if g}


def behaviour(manager, board, ref, symbol=None):
    """The behaviour that applies to one part: '<board>:<ref>' first, else a board-free row whose part_key is the symbol's value or lib_id."""
    o = _find(manager, '%s:%s' % (board, ref))
    if o is None or not _given(o):   # an own row with everything cleared gives way to a shared one
        keys = {k for k in ((symbol or {}).get('value'), (symbol or {}).get('lib_id')) if k}
        o = next((m for m in _objs(manager) if not _get(m, 'board') and _get(m, 'part_key') in keys), None)
    if o is None or not _given(o):
        return None
    words = (', '.join(x for x in (_get(o, 'document'), _get(o, 'page_table')) if x)
             or 'no document named: %s' % (_get(o, 'origin', '') or 'given by a person'))
    return {'name': _get(o, 'name'), 'given': _given(o), 'words': words,
            **{q: float(_get(o, q, 0.0) or 0.0) for q in QUANTITIES}}


def _symbols(rows):
    return {s['ref']: s for s in rows.get('SchematicSymbol') or [] if s.get('power') != 'yes'}


def coefficients(manager, board, rows=None):
    from pcb.custom.thermal import _rows_of
    rows = rows if rows is not None else _rows_of(manager, board, ('SchematicSymbol',))
    out = {}
    for ref, s in _symbols(rows).items():
        b = behaviour(manager, board, ref, s)
        if b and ref[:1].upper() in PASSIVES and b['given'] & {'tc1_ppm_k', 'tc2_ppm_k2'}:
            out[ref] = (b['tc1_ppm_k'] * 1e-6, b['tc2_ppm_k2'] * 1e-6, b['words'])
    return out


def parts(manager, board, rows=None):
    from pcb.custom.thermal import _rows_of
    rows = rows if rows is not None else _rows_of(manager, board, ('SchematicSymbol',))
    out = []
    for ref, s in sorted(_symbols(rows).items()):
        b = behaviour(manager, board, ref, s) or {'given': set(), 'words': ''}
        g = b['given']
        out.append({'board': board, 'ref': ref, 'value': s.get('value', ''), 'lib_id': s.get('lib_id', ''),
                    'rated_range': ('%g .. %g C' % (b['t_min_c'], b['t_max_c'])) if {'t_min_c', 't_max_c'} <= g else
                                   ('from %g C' % b['t_min_c']) if 't_min_c' in g else ('up to %g C' % b['t_max_c']) if 't_max_c' in g else 'not given',
                    'tc1_ppm_k': b['tc1_ppm_k'] if 'tc1_ppm_k' in g else '', 'tc2_ppm_k2': b['tc2_ppm_k2'] if 'tc2_ppm_k2' in g else '',
                    'source': b['words'] if g else '',
                    'coefficient_use': ('written into the deck as tc1 / tc2' if g & {'tc1_ppm_k', 'tc2_ppm_k2'} else 'none given - an ideal value, '
                                        'unchanged by temperature') if ref[:1].upper() in PASSIVES else
                                       'its SPICE model carries its temperature behaviour (coefficients apply to R, C, L only)'})
    return out


def quantities(manager, board, ref):
    o = _find(manager, '%s:%s' % (board, ref))
    g = _given(o) if o is not None else set()
    return [{'board': board, 'ref': ref, 'quantity': q, 'value': float(_get(o, q, 0.0) or 0.0) if q in g else '', 'unit': unit, 'meaning': meaning,
             'given': q in g, 'signed': True, 'origin': _get(o, 'origin', '') if q in g else ''} for q, (unit, meaning) in QUANTITIES.items()]


def set_quantity(manager, board, ref, quantity, value):
    if quantity not in QUANTITIES:
        return 400, {'ok': False, 'error': 'no quantity %r - %s' % (quantity, ', '.join(QUANTITIES))}
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': '%s needs a number, got %r' % (quantity, value)}
    if not math.isfinite(v):
        return 400, {'ok': False, 'error': '%s needs a finite number, got %r' % (quantity, value)}
    if quantity in ('t_min_c', 't_max_c') and v < -273.15:
        return 400, {'ok': False, 'error': '%s is below absolute zero (-273.15 C): %g' % (quantity, v)}
    name = '%s:%s' % (board, ref)
    o = _find(manager, name)
    g = _given(o) if o is not None else set()
    lo = v if quantity == 't_min_c' else float(_get(o, 't_min_c', 0.0)) if 't_min_c' in g else None
    hi = v if quantity == 't_max_c' else float(_get(o, 't_max_c', 0.0)) if 't_max_c' in g else None
    if lo is not None and hi is not None and lo >= hi:
        return 400, {'ok': False, 'error': 'the rated range needs t_min_c < t_max_c (would be %g .. %g C)' % (lo, hi)}
    _save(manager, name, {'board': board, 'ref': ref, quantity: v, 'given': ','.join(sorted(g | {quantity}))})
    return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'value': v, 'rows': quantities(manager, board, ref)}


def clear_quantity(manager, board, ref, quantity):
    if quantity not in QUANTITIES:
        return 400, {'ok': False, 'error': 'no quantity %r - %s' % (quantity, ', '.join(QUANTITIES))}
    name = '%s:%s' % (board, ref)
    o = _find(manager, name)
    if o is None or quantity not in _given(o):
        return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'cleared': False, 'rows': quantities(manager, board, ref)}
    _save(manager, name, {quantity: 0.0, 'given': ','.join(sorted(_given(o) - {quantity}))})
    return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'cleared': True, 'rows': quantities(manager, board, ref)}


def put_behaviour(manager, board, ref, part_key, body):
    """A whole behaviour WITH its citation (POST): any of the four quantities + document, page_table, url, origin. -> (status, body)"""
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'body must be an object'}
    vals = {}
    for q in QUANTITIES:
        if q in body:
            try:
                vals[q] = float(body[q])
            except (TypeError, ValueError):
                return 400, {'ok': False, 'error': '%s needs a number, got %r' % (q, body[q])}
            if not math.isfinite(vals[q]):
                return 400, {'ok': False, 'error': '%s needs a finite number' % q}
    if not vals:
        return 400, {'ok': False, 'error': 'give at least one of %s' % ', '.join(QUANTITIES)}
    if 't_min_c' in vals and 't_max_c' in vals and vals['t_min_c'] >= vals['t_max_c']:
        return 400, {'ok': False, 'error': 'the rated range needs t_min_c < t_max_c'}
    if any(vals.get(q, 0.0) < -273.15 for q in ('t_min_c', 't_max_c')):
        return 400, {'ok': False, 'error': 'a rated temperature below absolute zero'}
    name = '%s:%s' % (board, ref) if board else part_key
    fields = dict(vals, board=board, ref=ref, part_key=part_key, given=','.join(sorted(vals)),
                  **{k: str(body.get(k, '')) for k in ('document', 'page_table', 'url')},
                  origin=str(body.get('origin') or ('cited' if body.get('document') else 'given without a document')))
    _save(manager, name, fields)
    return 201, {'ok': True, 'name': name, 'given': sorted(vals)}
