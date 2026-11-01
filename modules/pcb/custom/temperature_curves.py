"""
@module pcb.custom.temperature_curves

tmp-5 (AI-Notes/plans/TEMPERATURE_PLAN.md): PARTS WITH NO SPICE MODEL, AT A TEMPERATURE - their datasheets' numbers against temperature
(PartTemperatureCurve), read at the temperatures the circuit is simulated at, and put into the deck where the part IS a deck element (a resistor's
value, a capacitor's corner). The same "derive or cite" rule as the Foster stages: only what the document gives in NUMBERS; a curve printed only
as a graph is not read off the graph (its row would have to be typed from it, and say so).

  CITED                                   the code-owned catalogue (each row cited below); seeded as board-free PartTemperatureCurve rows
  value_at(curve, t_c) -> {value, low, high, inside, words}   points: straight line between two table rows; linear: the stated value + slope;
                                          band: nominal 1 with its low / high corner (a ratio); outside the stated range: inside False, value -1
  catalogue(manager)                      the board-free curves
  bound(manager, board, rows=None)        {ref: [curve, ...]} - the part's own ('<board>:<ref>:<quantity>') and catalogue rows matching its value / lib_id
  bind(manager, board, ref, from_name) / unbind(manager, board, ref, quantity) -> (status, body)
  at_temperatures(manager, board, temps, rows=None)   long form: each bound curve at each temperature, and what the deck does with it
  deck_values(manager, board, temp_c, corner='nominal', rows=None) -> ({ref: (new value text, words)}, notes)
      R with an ohm curve -> the curve's value; R / C / L with a band -> nominal x the corner's ratio (low | high); anything else is listed, not used
  run_at(manager, board, temp_c, corner='nominal', runner=None, rows=None) -> result   the board at temp_c with those values in its deck (kept)

The catalogue (2026-11-01, read from the documents):
  sq2310es-rds-on   Vishay SQ2310ES, S21-1074 Rev. C, 15-Nov-2021, Specifications p. 2: R_DS(on) MAX at V_GS 4.5 V - 0.030 ohm (I_D 4 A, the
                    table's T_C 25 C), 0.045 ohm (I_D 4 A, T_J 125 C), 0.054 ohm (I_D 5 A, T_J 175 C); pulse test <= 300 us, <= 2 % duty
  tlcy5200-vf       Vishay TLCY5200, Document 81354 Rev. 1.6, 09-May-2022, Optical and Electrical Characteristics p. 2: V_F 2.1 V typ at I_F
                    50 mA, T_amb 25 C, and its temperature coefficient -3.5 mV/K typ at 50 mA; operating range -40 .. +100 C (Absolute Maximum
                    Ratings p. 1). ONE typical coefficient: the straight line across the range is ours, said on every row
  x7r / x5r / c0g   EIA-198 dielectric classes as KEMET states them: X7R +-15 % over -55 .. +125 C (C1002_X7R, 2026-09-01, p. 1); X5R +-15 % over
                    -55 .. +85 C (C1006_X5R, 2026-09-07, p. 1); C0G +-30 ppm/C over -55 .. +125 C (C1003_C0G, 2025-02-20, p. 1, p. 4) - BOUNDS
                    (the class says the capacitance stays inside them), not a curve: the low and high corners
With no manager (selftests) the rows live in this process only.
"""
import json

CLS = 'PartTemperatureCurve'
_MEM = {CLS: {}}
_SQ = ('Vishay SQ2310ES Automotive N-Channel 20 V (D-S) 175 C MOSFET, S21-1074', 'Rev. C, 15-Nov-2021', 'https://www.vishay.com/docs/67036/sq2310es.pdf')
_TL = ('Vishay TLCY5200 High Intensity LED, 5 mm Clear, Document Number 81354', 'Rev. 1.6, 09-May-2022', 'https://www.vishay.com/docs/81354/tlcy5200.pdf')
CITED = [
    {'name': 'sq2310es-rds-on', 'part_key': 'SQ2310ES', 'quantity': 'rds_on_max', 'unit': 'ohm', 'kind': 'points',
     'points_json': json.dumps([[25.0, 0.030], [125.0, 0.045], [175.0, 0.054]]), 't_min_c': 25.0, 't_max_c': 175.0,
     'conditions': 'V_GS 4.5 V; I_D 4 A at 25 and 125 C, 5 A at 175 C (as printed); 25 C is the table\'s T_C, 125 / 175 C are T_J; pulse test <= 300 us, '
                   '<= 2 % duty; MAXIMUM values (no typical is given hot)',
     'document': _SQ[0], 'revision': _SQ[1], 'page_table': 'Specifications, Drain-source on-state resistance, p. 2', 'url': _SQ[2], 'origin': 'cited'},
    {'name': 'tlcy5200-vf', 'part_key': 'TLCY5200', 'quantity': 'vf_typ', 'unit': 'V', 'kind': 'linear', 't_ref_c': 25.0, 'value_ref': 2.1,
     'slope_per_k': -0.0035, 't_min_c': -40.0, 't_max_c': 100.0,
     'conditions': 'I_F 50 mA; V_F 2.1 V typ at T_amb 25 C; TC_VF -3.5 mV/K typ; the operating range -40 .. +100 C. One typical coefficient - the '
                   'straight line across the range is ours',
     'document': _TL[0], 'revision': _TL[1], 'page_table': 'Optical and Electrical Characteristics, p. 2; Absolute Maximum Ratings, p. 1', 'url': _TL[2],
     'origin': 'cited'},
    {'name': 'x7r', 'part_key': 'X7R', 'quantity': 'capacitance', 'unit': 'ratio', 'kind': 'band', 'band_pct': 15.0, 't_ref_c': 25.0,
     't_min_c': -55.0, 't_max_c': 125.0, 'conditions': 'EIA-198 class X7R: +-15 % capacitance change over -55 .. +125 C (a bound)',
     'document': 'KEMET Surface Mount Multilayer Ceramic Chip Capacitors, X7R Dielectric, C1002_X7R', 'revision': '2026-09-01', 'page_table': 'p. 1',
     'url': 'https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf', 'origin': 'cited'},
    {'name': 'x5r', 'part_key': 'X5R', 'quantity': 'capacitance', 'unit': 'ratio', 'kind': 'band', 'band_pct': 15.0, 't_ref_c': 25.0,
     't_min_c': -55.0, 't_max_c': 85.0, 'conditions': 'EIA-198 class X5R: +-15 % capacitance change over -55 .. +85 C (a bound)',
     'document': 'KEMET Surface Mount Multilayer Ceramic Chip Capacitors, X5R Dielectric, C1006_X5R', 'revision': '2026-09-07', 'page_table': 'p. 1, p. 3',
     'url': 'https://content.kemet.com/datasheets/KEM_C1006_X5R_SMD.pdf', 'origin': 'cited'},
    {'name': 'c0g', 'part_key': 'C0G', 'quantity': 'capacitance', 'unit': 'ratio', 'kind': 'band', 'band_ppm_k': 30.0, 't_ref_c': 25.0,
     't_min_c': -55.0, 't_max_c': 125.0, 'conditions': 'EIA-198 class C0G: +-30 ppm/C over -55 .. +125 C, aging 0 % (a bound, growing with |T - 25 C|)',
     'document': 'KEMET Surface Mount Multilayer Ceramic Chip Capacitors, C0G Dielectric, C1003_C0G', 'revision': '2025-02-20', 'page_table': 'p. 1, p. 4',
     'url': 'https://content.kemet.com/datasheets/KEM_C1003_C0G_SMD.pdf', 'origin': 'cited'},
]
_FIELDS = ('part_key', 'from_curve', 'quantity', 'unit', 'kind', 'points_json', 't_ref_c', 'value_ref', 'slope_per_k', 'band_pct', 'band_ppm_k',
           't_min_c', 't_max_c', 'conditions', 'document', 'revision', 'page_table', 'url', 'origin', 'notes')


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _objs(manager):
    if manager is None:
        return list(_MEM[CLS].values())
    return list(((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).values())


def catalogue(manager):
    rows = [c for c in _objs(manager) if not _get(c, 'board')]
    have = {_get(c, 'name') for c in rows}
    return rows + [c for c in CITED if c['name'] not in have]   # the code-owned rows stand in until seeded (selftests, a fresh instance)


def _cite(c):
    return ', '.join(x for x in (_get(c, 'document'), _get(c, 'revision'), _get(c, 'page_table')) if x) or 'no document named: %s' % (_get(c, 'origin') or 'given')


def value_at(c, t_c):
    kind, lo_t, hi_t = _get(c, 'kind'), float(_get(c, 't_min_c', 0) or 0), float(_get(c, 't_max_c', 0) or 0)
    if kind == 'points':
        pts = sorted(json.loads(_get(c, 'points_json') or '[]'))
        if len(pts) < 1:
            return {'value': -1.0, 'low': -1.0, 'high': -1.0, 'inside': False, 'words': 'no points given'}
        lo_t, hi_t = pts[0][0], pts[-1][0]
    out = {'value': -1.0, 'low': -1.0, 'high': -1.0, 'inside': lo_t <= t_c <= hi_t}
    if not out['inside']:
        return dict(out, words='%g C is outside the %g .. %g C the document gives - not extrapolated' % (t_c, lo_t, hi_t))
    if kind == 'points':
        for (t0, v0), (t1, v1) in zip(pts, pts[1:] + [pts[-1]]):
            if t0 <= t_c <= t1:
                v = v0 if t1 == t0 else v0 + (v1 - v0) * (t_c - t0) / (t1 - t0)
                exact = t_c in (t0, t1)
                return dict(out, value=v, low=v, high=v, words=('the table\'s own row at %g C' % t_c) if exact else
                            'a straight line between the table\'s rows at %g C and %g C' % (t0, t1))
    if kind == 'linear':
        t_ref, v_ref, k = float(_get(c, 't_ref_c')), float(_get(c, 'value_ref')), float(_get(c, 'slope_per_k'))
        v = v_ref + k * (t_c - t_ref)
        return dict(out, value=v, low=v, high=v, words='%g at %g C %+g per K x %+g K (one stated coefficient, applied as a straight line)'
                                                        % (v_ref, t_ref, k, t_c - t_ref))
    if kind == 'band':
        pct, ppm = float(_get(c, 'band_pct', 0) or 0), float(_get(c, 'band_ppm_k', 0) or 0)
        b = pct / 100.0 if pct else ppm * 1e-6 * abs(t_c - float(_get(c, 't_ref_c', 25) or 25))
        return dict(out, value=1.0, low=1.0 - b, high=1.0 + b, words=('a bound: within +-%g %% of nominal anywhere in the range' % pct) if pct else
                    'a bound: within +-%g ppm/K x %g K = +-%.4g %% of nominal' % (ppm, abs(t_c - float(_get(c, 't_ref_c', 25) or 25)), b * 100))
    return dict(out, inside=False, words='unknown curve kind %r' % kind)


def _symbols(rows):
    return {s['ref']: s for s in rows.get('SchematicSymbol') or [] if s.get('power') != 'yes'}


def bound(manager, board, rows=None):
    from pcb.custom.spice_temperature import _rows
    rows = _rows(manager, board, rows)
    own = [c for c in _objs(manager) if _get(c, 'board') == board]
    cat = catalogue(manager)
    out = {}
    for ref, s in sorted(_symbols(rows).items()):
        mine = [c for c in own if _get(c, 'ref') == ref]
        q = {_get(c, 'quantity') for c in mine}
        keys = {k for k in (s.get('value'), s.get('lib_id')) if k}
        mine += [c for c in cat if _get(c, 'part_key') in keys and _get(c, 'quantity') not in q]
        if mine:
            out[ref] = mine
    return out


def _save(manager, name, fields):
    if manager is None:
        _MEM[CLS][name] = dict(_MEM[CLS].get(name) or {}, name=name, **fields)
        return _MEM[CLS][name]
    o = next((x for x in _objs(manager) if _get(x, 'name') == name), None)
    if o is None:
        from pcb.objects.pcb.PartTemperatureCurve import PartTemperatureCurve
        o = PartTemperatureCurve(manager=manager, name=name, **fields)
    else:
        for k, v in fields.items():
            setattr(o, k, v)
    try:
        manager.db.saveInstanceInDB(o)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return o


def bind(manager, board, ref, from_name):
    c = next((x for x in catalogue(manager) if _get(x, 'name') == from_name), None)
    if c is None:
        return 404, {'ok': False, 'error': 'no catalogue curve %r - %s' % (from_name, ', '.join(_get(x, 'name') for x in catalogue(manager)))}
    fields = {k: _get(c, k) for k in _FIELDS if _get(c, k) is not None}
    fields.update(board=board, ref=ref, from_curve=from_name)
    name = '%s:%s:%s' % (board, ref, fields['quantity'])
    _save(manager, name, fields)
    return 200, {'ok': True, 'board': board, 'ref': ref, 'curve': name, 'from': from_name}


def unbind(manager, board, ref, quantity):
    name = '%s:%s:%s' % (board, ref, quantity)
    if manager is None:
        gone = _MEM[CLS].pop(name, None)
    else:
        gone = next((x for x in _objs(manager) if _get(x, 'name') == name), None)
        if gone is not None:
            try:
                manager.db.deleteInstanceFromDB(gone)
            except Exception:  # noqa: BLE001
                pass
            ((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).pop(getattr(gone, 'id', None), None)
    return (200, {'ok': True, 'removed': name}) if gone is not None else (404, {'ok': False, 'error': 'no curve %r' % name})


def _deck_use(kind, c):
    """What the deck does with this curve on this element kind, or why not."""
    unit, ck = _get(c, 'unit'), _get(c, 'kind')
    if kind == 'R' and unit == 'ohm' and ck != 'band':
        return 'the resistor\'s value'
    if kind in ('R', 'C', 'L') and ck == 'band':
        return 'nominal x the corner (low / high)'
    return ''


def at_temperatures(manager, board, temps, rows=None):
    from pcb.custom import kicad_spice as P
    from pcb.custom.spice_temperature import _rows
    rows = _rows(manager, board, rows)
    kinds = {e.get('ref', n): e['kind'] for n, e in P.build_deck(rows)['elements'].items()}
    out = []
    for ref, curves in bound(manager, board, rows).items():
        for c in curves:
            use = _deck_use(kinds.get(ref, ''), c)
            for t in temps:
                v = value_at(c, float(t))
                out.append({'board': board, 'ref': ref, 'curve': _get(c, 'name'), 'quantity': _get(c, 'quantity'), 'unit': _get(c, 'unit'),
                            'kind': _get(c, 'kind'), 'temp_c': float(t), 'value': v['value'], 'low': v['low'], 'high': v['high'],
                            'inside': 'yes' if v['inside'] else 'no', 'how': v['words'],
                            'in_deck': use or ('not in the deck: %s' % ('no deck element' if ref not in kinds else 'a %s element takes no %s curve'
                                                                        % (kinds[ref], _get(c, 'quantity')))),
                            'conditions': _get(c, 'conditions') or '', 'source': _cite(c)})
    return out


def deck_values(manager, board, temp_c, corner='nominal', rows=None):
    from pcb.custom import kicad_spice as P
    from pcb.custom.spice_temperature import _rows
    from pcb.custom.thermal import spice_number
    rows = _rows(manager, board, rows)
    elements = {e.get('ref', n): e for n, e in P.build_deck(rows)['elements'].items()}
    vals, notes = {}, []
    for ref, curves in bound(manager, board, rows).items():
        e = elements.get(ref)
        for c in curves:
            use = _deck_use(e['kind'] if e else '', c)
            if not use:
                notes.append('%s %s: not in the deck' % (ref, _get(c, 'quantity')))
                continue
            v = value_at(c, float(temp_c))
            if not v['inside']:
                notes.append('%s %s: %s - left at its value' % (ref, _get(c, 'quantity'), v['words']))
                continue
            if _get(c, 'kind') == 'band':
                nominal = spice_number(e['value'].split()[0])
                ratio = {'low': v['low'], 'high': v['high']}.get(corner, 1.0)
                if not nominal:
                    notes.append('%s: no number in %r to scale' % (ref, e['value']))
                    continue
                vals[ref] = ('%.6g' % (nominal * ratio), '%s corner of %s at %g C: x %.6g (%s)' % (corner, _get(c, 'name'), temp_c, ratio, v['words']))
            else:
                vals[ref] = ('%.6g' % v['value'], '%s at %g C: %.6g %s (%s)' % (_get(c, 'name'), temp_c, v['value'], _get(c, 'unit'), v['words']))
    return vals, notes


def run_at(manager, board, temp_c, corner='nominal', runner=None, rows=None):
    from pcb.custom import spice_temperature as ST
    if corner not in ('nominal', 'low', 'high'):
        return {'ok': False, 'error': 'corner must be nominal, low or high, got %r' % corner, 'status': 400}
    vals, notes = deck_values(manager, board, temp_c, corner, rows)
    return ST.run_at(manager, board, temp_c, runner=runner, rows=rows, values=vals,
                     extra={'corner': corner, 'curve_values': {r: w for r, (_v, w) in vals.items()}, 'curve_notes': notes})
