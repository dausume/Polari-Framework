"""
@module pcb.custom.thermal

bob-3c / kxc-3d (BENCH_BOARDS_PLAN bob-3, his words 2026-10-30: the single-Board view goes into "how it handles thermal behaviors"): A FIRST-ORDER THERMAL
VIEW of a PCB, from a kept simulation run - every number derived from the run and the board's own rows, or a labelled knob.

  dissipation(manager, board, run=None, rows=None) -> (rows, why)   per part, from the run's vectors and the deck's elements (pcb.custom.kicad_spice):
      R   P(t) = (Va - Vb)^2 / R  (Ohm's law on the node voltages; R from its SPICE value)
      V   P(t) = -(Vp - Vn) * I   the power the source DELIVERS (ngspice's branch current flows into the + node through the source)
      C L ideal reactive elements: 0 W on average by definition (they store and return energy)
      D X Q M ... undetermined: the deck saves node voltages and source branch currents only - their current is not in the run
    average over the stored points by the trapezoid rule (a thinned reference run is said), and the peak.
  estimate(manager, board, run=None, rows=None, pcb=None, h=H_FREE_AIR) -> (row, why)   the board's mean temperature rise in still air:
      unaccounted = what the sources deliver - what the counted parts take (energy conservation): the power in the undetermined parts, in total
      dT = P / (h * 2A) - Newton's law of cooling for a plate losing heat from both faces at one uniform temperature; A from the PcbBoard outline
      (width x height); P = the determined dissipation; h a KNOB (free convection in air, below). Radiation and conduction into the mounting are left
      out (said): the number is a first-order mean, not a hot-spot map.

H_FREE_AIR: Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, Table 1.1 "Typical values of the convection heat transfer coefficient": free
convection, gases, 2-25 W/(m2 K). 10 is a knob inside that range, never a measured value.
"""
import json
import re

H_FREE_AIR = 10.0
H_RANGE = (2.0, 25.0)
H_CITE = 'Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, Table 1.1: free convection in gases 2-25 W/(m2 K)'
_SUFFIX = [('meg', 1e6), ('f', 1e-15), ('p', 1e-12), ('n', 1e-9), ('u', 1e-6), ('m', 1e-3), ('k', 1e3), ('g', 1e9), ('t', 1e12)]


def spice_number(text):
    """'4.7k' -> 4700.0, '1Meg' -> 1e6, '100n' -> 1e-7 (SPICE: m = milli, meg = mega; trailing unit letters ignored). None when it is not a number."""
    m = re.match(r'^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([a-zA-Z]*)', str(text or ''))
    if not m:
        return None
    v, suf = float(m.group(1)), m.group(2).lower()
    for s, k in _SUFFIX:
        if suf.startswith(s):
            return v * k
    return v


def _rows_of(manager, board):
    import inspect
    from pcb.pcb_basis import PCB_CLASSES
    tables = (getattr(manager, 'objectTables', None) or {}) if manager is not None else {}
    out = {}
    for cls in PCB_CLASSES:
        if cls.__name__ in ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact', 'PcbBoard'):
            keys = [k for k in inspect.signature(cls.__init__).parameters if k not in ('self', 'manager')]
            out[cls.__name__] = [{k: getattr(o, k, None) for k in keys} for o in (tables.get(cls.__name__) or {}).values()
                                 if getattr(o, 'board', getattr(o, 'name', '')) == board or getattr(o, 'name', '') == board]
    return out


def _trapz_mean(xs, ys):
    if len(xs) < 2 or xs[-1] == xs[0]:
        return sum(ys) / len(ys) if ys else 0.0
    area = sum((xs[i + 1] - xs[i]) * (ys[i + 1] + ys[i]) / 2 for i in range(len(xs) - 1))
    return area / (xs[-1] - xs[0])


def dissipation(manager, board, run=None, rows=None):
    from pcb.custom import kicad_spice as P
    from pcb.custom import spice_runs as SR
    r = next((x for x in SR.runs(manager, board) if x['name'] == run), None) if run else SR._latest_ok(manager, board)
    if r is None:
        return [], 'no finished run kept for %s - simulate it first (the thermal view reads a run)' % board
    if not r['plot'].startswith('tran'):
        return [], 'run %s is a %s: dissipation needs a transient (an AC sweep is small-signal, it carries no power)' % (r['name'], r['analysis'])
    vs = {v['vector'].lower(): v for v in SR._table(manager, 'SpiceVector') if v['run'] == r['name']}
    xs = json.loads(next(v for v in vs.values() if v['role'] == 'scale')['values_json'])
    deck = P.build_deck(rows if rows is not None else _rows_of(manager, board))

    def volts(node):
        if node == 'GND':
            return [0.0] * len(xs)
        v = vs.get(node.lower())
        return json.loads(v['values_json']) if v else None

    out = []
    for name, e in sorted(deck['elements'].items()):
        base = {'ref': name, 'kind': e['kind'], 'value': e['value'], 'nodes': ' '.join(e['nodes']), 'avg_w': -1.0, 'peak_w': -1.0, 'run': r['name'], 'basis': ''}
        if e['kind'] == 'R':
            ohm, va, vb = spice_number(e['value']), volts(e['nodes'][0]), volts(e['nodes'][1])
            if not ohm or va is None or vb is None:
                out.append(dict(base, basis='undetermined: %s' % ('no resistance in %r' % e['value'] if not ohm else 'a node voltage is not in the run')))
                continue
            p = [(a - b) ** 2 / ohm for a, b in zip(va, vb)]
            out.append(dict(base, avg_w=_trapz_mean(xs, p), peak_w=max(p), basis='(Va - Vb)^2 / R with R = %g ohm, over %d stored points' % (ohm, len(p))))
        elif e['kind'] == 'V':
            i, vp, vn = vs.get('%s#branch' % name.lower()), volts(e['nodes'][0]), volts(e['nodes'][1])
            if i is None or vp is None or vn is None:
                out.append(dict(base, basis='undetermined: its branch current or a node voltage is not in the run'))
                continue
            p = [-(a - b) * c for a, b, c in zip(vp, vn, json.loads(i['values_json']))]
            out.append(dict(base, avg_w=_trapz_mean(xs, p), peak_w=max(p), basis='delivered -(Vp - Vn) * I (ngspice branch current), over %d stored points' % len(p)))
        elif e['kind'] in ('C', 'L'):
            out.append(dict(base, avg_w=0.0, peak_w=-1.0, basis='an ideal %s stores and returns energy: 0 W on average by definition' % ('capacitor' if e['kind'] == 'C' else 'inductor')))
        else:
            out.append(dict(base, basis='undetermined: the run holds node voltages and source branch currents only - a %s\'s current is not in it' % e['kind']))
    note = '' if r['points'] > 1000 else ' (the run keeps %d points: averages are over those points only)' % r['points']
    for row in out:
        row['basis'] += note if row['avg_w'] not in (-1.0, 0.0) else ''
    return out, ''


def estimate(manager, board, run=None, rows=None, pcb=None, h=H_FREE_AIR):
    parts, why = dissipation(manager, board, run, rows)
    if why:
        return None, why
    heat = [p for p in parts if p['kind'] not in ('V',) and p['avg_w'] >= 0]
    undetermined = [p['ref'] for p in parts if p['avg_w'] == -1.0]
    total = sum(p['avg_w'] for p in heat)
    delivered = [p['avg_w'] for p in parts if p['kind'] == 'V' and p['avg_w'] != -1.0]
    # energy conservation: what the sources deliver on average is what the parts take - the remainder is the parts whose current the run does not hold
    unaccounted = (sum(delivered) - total) if delivered and len(delivered) == sum(1 for p in parts if p['kind'] == 'V') else -1.0
    pcb = pcb if pcb is not None else next(iter((rows if rows is not None else _rows_of(manager, board)).get('PcbBoard') or []), None)
    w, ht = (float(pcb.get('width_mm') or 0), float(pcb.get('height_mm') or 0)) if pcb else (0.0, 0.0)
    row = {'board': board, 'run': parts[0]['run'] if parts else '', 'dissipated_w': total, 'parts_counted': len(heat), 'parts_undetermined': ', '.join(undetermined),
           'delivered_w': sum(delivered) if delivered else -1.0, 'unaccounted_w': unaccounted,
           'area_mm2': w * ht if w > 0 and ht > 0 else -1.0, 'h_w_m2k': h, 'delta_t_c': -1.0,
           'basis': 'h = %g W/(m2 K), a knob (%s)' % (h, H_CITE)}
    if row['area_mm2'] <= 0:
        row['basis'] = 'undetermined: no PCB outline for %s (a schematic-only project has no board area) - the parts\' dissipation is still listed' % board
        return row, ''
    row['delta_t_c'] = total / (h * 2 * row['area_mm2'] * 1e-6)
    row['basis'] = ('dT = P / (h x 2A): Newton\'s law of cooling, a plate at one temperature losing heat from both faces; A = %g x %g mm (PcbBoard); %s; '
                    'radiation and conduction into the mounting left out - a first-order mean rise, not a hot-spot map%s'
                    % (w, ht, row['basis'], ('; NOT counted (no current in the run): %s' % ', '.join(undetermined)) if undetermined else ''))
    return row, ''
