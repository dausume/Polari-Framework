"""
@module board.custom.footholds

bob-0 (AI-Notes/plans/BENCH_BOARDS_PLAN.md section 3): THE BENCH CONTRACT. Every Board on the Bench - a dev board, a breadboard, a PCB - is reached
through its FOOTHOLDS (BoardFoothold rows): where something can land, which footholds the board joins inside (`node`), and the abstracted drive and
signal data. How a board is DEFINED is its own level (his ruling 2026-10-30); one adapter per definition kind turns the definition's rows into
footholds, and nothing is typed twice:

  datasheet(tables, board)   a dev board known from its vendor documents: one foothold per ConnectorPin (header pin), its BoardPin / net / cited limits
  geometry(model)            a breadboard known from its counts and pitch: one foothold per tie point and rail hole, a strip half or a rail = one node
  layers                     a PCB known from its copper (pcb.custom.kicad_footholds, stored by the KiCad ingest - the parse lives with the reader)
  for_definition(kind, definition, tables)  the dispatcher the door uses

Unknown stays unknown: -1 for a number nobody cited, the reason in `undetermined`.
"""
import json

from board.custom import pv_families as F
from board.custom import pv_shapes as S

UNKNOWN = -1.0
KINDS = ('datasheet', 'geometry', 'layers')
POSITION_KNOB = {'arduino-uno-r3': 'drawing knob: the header rows\' x offsets are not dimensioned (pv_shapes.HEADERS); the 2.54 mm pitch is cited (UNO datasheet p.12)',
                 'esp32-c3': 'derived: J1-J3 22.86 mm and the 2.54 mm pitch cited (DevKitM-1 dimensions drawing); the rows\' inset and offset are drawing knobs (pv_shapes.C3_HEADERS)'}
#: header labels that are inputs to the board, not supplies or chip pins (the vendors' header tables)
INPUT_LABELS = {'RESET': 'the reset input (UNO header)', 'RST': 'CHIP_PU, the chip enable / reset input (DevKitM-1 Header Block)',
                'AREF': 'the analog reference input (UNO header)'}


def _name(kind, definition, foothold):
    return '%s:%s:%s' % (kind, definition, foothold)


def _j(raw, default):
    try:
        return json.loads(raw) if raw else default
    except (TypeError, ValueError):
        return default


def _soc_of(tables, board):
    hw = next((h for h in tables.get('BoardHardware', []) if h['board'] == board), None)
    mcu = next((c for c in _j(hw and hw.get('components_json'), []) if c.get('role') == 'mcu'), {})
    return mcu.get('soc', ''), _j(hw and hw.get('power_rails_json'), [])


def _families(tables, soc, board_pin):
    fams = []
    for f in tables.get('PinFunction', []):
        if f['soc'] == soc and f['soc_pin'] == '%s:%s' % (soc, board_pin['soc_pin']):
            fams += [x for x in F.families_of_function(f['function']) if x not in fams]
    role = F.role_family(board_pin.get('function', ''))
    if role and role not in fams:
        fams.append(role)
    return fams


def _header_positions(tables, board):
    """{(connector, number): (x, y)} from the pin view's own board shape (the one geometry the drawing uses)."""
    p = S.params(S.board_row(board, tables))
    out = {}
    for h in p.get('headers', []):
        for pin in S.header(h):
            out[(h['connector'], pin['number'])] = (round(pin['x'], 4), round(pin['y'], 4))
    return out


def datasheet(tables, board):
    """BoardFoothold rows of a datasheet-defined dev board: one per header pin (ConnectorPin)."""
    from board.custom import electrical_check as EC
    soc, rails = _soc_of(tables, board)
    rail = {r['net']: r for r in rails}
    nets = {n['net']: n for n in tables.get('BoardNet', []) if n['board'] == board}
    pins = {p['canonical']: p for p in tables.get('BoardPin', []) if p['board'] == board}
    logic, logic_why = EC._board_logic_level(board)
    where = _header_positions(tables, board)
    rows = []
    for cp in sorted((c for c in tables.get('ConnectorPin', []) if c['board'] == board), key=lambda c: (c['connector'], c['number'])):
        fid = '%s:%d' % (cp['connector'], cp['number'])
        x, y = where.get((cp['connector'], cp['number']), (UNKNOWN, UNKNOWN))
        r = {'name': _name('datasheet', board, fid), 'definition_kind': 'datasheet', 'definition': board, 'foothold': fid, 'kind': 'header-pin',
             'label': cp['label'], 'x_mm': x, 'y_mm': y, 'position_basis': POSITION_KNOB.get(board, 'drawing knob') if (cp['connector'], cp['number']) in where else '',
             'side': 'top', 'node': 'net:%s' % cp['net'] if cp['net'] else 'pin:%s' % fid, 'net': cp['net'], 'rail_volts': UNKNOWN, 'logic_volts': UNKNOWN,
             'source_ma': UNKNOWN, 'sink_ma': UNKNOWN, 'drive_basis': '', 'families_json': '[]', 'chip_pin': '', 'direction': 'undetermined',
             'signal_basis': 'ConnectorPin %s:%s (%s)' % (board, fid, cp.get('fact', '')), 'undetermined': '', 'notes': cp.get('notes', '')}
        bp = pins.get(cp['board_pin'])
        net = nets.get(cp['net'], {})
        if bp:   # a chip pin brought out to the header
            el = _j(bp.get('electrical_json'), {})
            r.update(chip_pin=bp['soc_pin'], direction='inout', families_json=json.dumps(_families(tables, soc, bp)),
                     signal_basis='BoardPin %s -> %s %s (PinFunction rows)' % (bp['name'], soc, bp['soc_pin']))
            if logic is not None:
                r.update(logic_volts=float(logic))
            if 'max_ma' in el:
                typical = 'typical' in el.get('kind', '')
                r.update(source_ma=float(el['max_ma']), sink_ma=UNKNOWN if typical else float(el['max_ma']))
                r['drive_basis'] = '%s %s mA (%s)%s; logic %s' % ('typical source' if typical else 'per-pin limit', el['max_ma'], el.get('fact', ''),
                                                                '; sink not cited' if typical else ' (source and sink)', logic_why)
            else:
                r['drive_basis'] = 'logic %s' % logic_why
                r['undetermined'] = 'no current limit on BoardPin %s (%s)' % (bp['name'], ', '.join('%s %s' % kv for kv in sorted(el.items())) or 'no electrical data')
        elif net.get('net_class') in ('power', 'ground'):
            fam = net['net_class']
            r.update(direction='supply', families_json=json.dumps([fam]), signal_basis='BoardNet %s:%s class %s' % (board, cp['net'], fam))
            rr = rail.get(cp['net'], {})
            v = rr.get('volts')
            if fam == 'ground':
                r.update(rail_volts=0.0, drive_basis='ground (BoardNet %s)' % cp['net'])
            elif isinstance(v, (int, float)):
                r.update(rail_volts=float(v), drive_basis='BoardHardware.power_rails_json %s = %s V%s' % (cp['net'], v, (', %s' % rr['fact']) if rr.get('fact') else ''))
            elif not rr and float(net.get('volts') or 0) > 0 and net.get('fact'):   # the C3: its rails are cited on the BoardNet rows (the Header Block's words)
                r.update(rail_volts=float(net['volts']), drive_basis='BoardNet %s:%s = %s V (%s)' % (board, cp['net'], net['volts'], net['fact']))
            else:
                r['undetermined'] = 'rail voltage of %s: %s' % (cp['net'], ('a range %s V (%s)' % (v, rr.get('fact', ''))) if v else 'not in the cited power rails')
            if rr.get('max_ma'):
                r.update(source_ma=float(rr['max_ma']), drive_basis=r['drive_basis'] + '; max %s mA (%s)' % (rr['max_ma'], rr.get('fact', '')))
        elif cp['label'] in INPUT_LABELS:
            r.update(direction='in', families_json=json.dumps(['reset-programming'] if cp['label'] != 'AREF' else ['analog']), signal_basis=INPUT_LABELS[cp['label']])
            r['undetermined'] = 'thresholds of %s not cited here' % cp['label']
        elif cp['label'] == 'NC':
            r.update(direction='passive', node='pin:%s' % fid, net='', signal_basis='printed NC: not connected (the vendor header table)')
        else:
            r['undetermined'] = 'header pin %s (%s) is neither a chip pin nor a cited rail' % (fid, cp['label'])
        rows.append(r)
    return rows


def geometry(model):
    """BoardFoothold rows of a breadboard (a BoardModel or BreadboardModel row dict: rows, rail_holes, holes_per_side?, pitch_mm?): the layout view's hole grammar
    r<N><a-j> and rail:<top|bottom>:<+|->:<N>. Strip N holes a-e are one node, f-j another (the centre trench); each rail is one node. A tie point is passive: it
    carries what is driven into it; the board's own limit is its rail rating when one is cited (BreadboardModel.rail_*_max), else undetermined."""
    name, rows_n, rail_n = model['name'], int(model.get('rows', -1)), int(model.get('rail_holes', -1))
    if rows_n <= 0 or rail_n < 0:
        return []
    side = int(model.get('holes_per_side', 5) or 5)
    geo = S.breadboard_geometry(rows_n, rail_n, float(model.get('pitch_mm', 2.54) or 2.54))
    drawable = model.get('geometry_known', True) is not False   # BreadboardModel says False when a stated outline disagrees with the generated one
    rv, ra = float(model.get('rail_voltage_max_v', UNKNOWN)), float(model.get('rail_current_max_a', UNKNOWN))
    limit_why = model.get('power_basis') or 'no rail rating cited for this model'
    basis = 'derived: %d strips x %d+%d holes, %d-hole rails, 2.54 mm pitch (pv_shapes.breadboard_geometry; %s)' % (rows_n, side, side, rail_n, model.get('source') or model.get('basis') or 'the model row')
    out = []

    def add(fid, kind, node, x, y, label=''):
        out.append({'name': _name('geometry', name, fid), 'definition_kind': 'geometry', 'definition': name, 'foothold': fid, 'kind': kind, 'label': label,
                    'x_mm': round(x, 4) if drawable else UNKNOWN, 'y_mm': round(y, 4) if drawable else UNKNOWN,
                    'position_basis': basis if drawable else 'not drawable: %s' % (model.get('basis') or 'the model says geometry_known False'), 'side': 'top', 'node': node, 'net': '', 'rail_volts': UNKNOWN,
                    'logic_volts': UNKNOWN, 'source_ma': ra * 1000 if ra > 0 else UNKNOWN, 'sink_ma': ra * 1000 if ra > 0 else UNKNOWN,
                    'drive_basis': ('rail contact rating %s V / %s A (%s)' % (rv, ra, limit_why)) if ra > 0 else '', 'families_json': '[]', 'chip_pin': '',
                    'direction': 'passive', 'signal_basis': 'a tie point carries what is driven into it', 'undetermined': '' if ra > 0 else 'contact rating: %s' % limit_why,
                    'notes': ''})
    cols = S.BB_COLS[:2 * side]
    for n in range(1, rows_n + 1):
        for i, c in enumerate(cols):
            x, y = S.hole_xy(geo, 'r%d%s' % (n, c))
            add('r%d%s' % (n, c), 'tie-point', 'strip:%d:%s' % (n, cols[0] + '-' + cols[side - 1] if i < side else cols[side] + '-' + cols[-1]), x, y)
    for rail in sorted(geo['rail_y']):
        where, pol = rail[:-1], rail[-1]
        for k in range(1, rail_n + 1):
            fid = 'rail:%s:%s:%d' % (where, pol, k)
            x, y = S.hole_xy(geo, fid)
            add(fid, 'rail-hole', 'rail:%s:%s' % (where, pol), x, y, label=pol)
    return out


def for_definition(kind, definition, tables=None, manager=None):
    """The dispatcher: (rows, why) - why is '' when rows came back, else the reason none did."""
    if kind not in KINDS:
        return [], 'no definition kind %r - %s' % (kind, ' | '.join(KINDS))
    if kind == 'datasheet':
        if tables is None:
            from board.custom import hardware_system as HS
            tables = HS.default_tables(manager)
        if not any(b['board'] == definition for b in tables.get('BoardPin', [])):
            return [], 'no datasheet board %r (no BoardPin rows)' % definition
        return datasheet(tables, definition), ''
    if kind == 'geometry':
        model = _breadboard_model(definition, manager)
        if model is None:
            return [], 'no breadboard model %r (BoardModel kind breadboard or BreadboardModel)' % definition
        rows = geometry(model)
        return rows, '' if rows else 'model %r has no drawable geometry (%s)' % (definition, model.get('basis') or 'rows / rail holes unknown')
    stored = [_as_dict(o) for o in _table(manager, 'BoardFoothold') if getattr(o, 'definition_kind', '') == 'layers' and getattr(o, 'definition', '') == definition]
    return sorted(stored, key=lambda r: r['name']), '' if stored else 'no stored footholds for PCB %r - ingest it (pol pcb ingest)' % definition


def _table(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _as_dict(o):
    import inspect
    from board.objects.board.BoardFoothold import BoardFoothold
    return {k: getattr(o, k, None) for k in inspect.signature(BoardFoothold.__init__).parameters if k not in ('self', 'manager')}


def _breadboard_model(name, manager=None):
    """BoardModel kind breadboard (electrodevice) first, then BreadboardModel (board): the live rows when a manager is given, else the code seeds."""
    for cls in ('BoardModel', 'BreadboardModel'):
        for o in _table(manager, cls):
            if getattr(o, 'name', '') == name and getattr(o, 'kind', 'breadboard') != 'devboard':
                return {k: v for k, v in vars(o).items() if not k.startswith('_')}
    try:
        from electrodevice.objects.layout._shared import SEED_BOARD_MODELS
    except ImportError:
        SEED_BOARD_MODELS = []
    from board.custom.bench_seed import SEED_BREADBOARD_MODELS
    return next((dict(m) for m in list(SEED_BOARD_MODELS) + list(SEED_BREADBOARD_MODELS) if m['name'] == name and m.get('kind') != 'devboard'), None)
