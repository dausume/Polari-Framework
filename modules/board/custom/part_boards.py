"""
@module board.custom.part_boards

drv-0 / drv-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; the user's words 2026-10-31: drivers "as a type of component we can put into place to fix issues
with drive" ... "that way we can define custom drivers like mini boards and enable placing boards with footprints onto other boards"): PARTS AS BOARDS.
A PartBoard row (a driver, a load, a module) is the definition kind `part` of a Board on the Bench; this module is its adapter and its catalogue.

  catalogue(manager)                   every PartBoard: the cited seed (SEED) + rows people defined, one row each with its contract in words
  part(name, manager)                  one as a dict, or None
  footholds(row)                       BoardFoothold rows of a part: one per pin, direction from its role, drive numbers from its contract
  define(manager, body) -> (status, body)   a custom part (a person's mini board): checked whole, refused in words
  add_part(manager, bench, body) -> (status, body)   a part onto a bench (a BenchBoard of kind part)
  suggestions(nets, manager)           for each over-voltage / under-voltage / drive-shortfall finding, the catalogue parts whose contract fixes it

SEED - ULN2003A in PDIP-16, every number from TI SLRS027T (ULN200x / ULQ200x, December 1976 - revised March 2025):
  pins (Table 4-1): 1B..7B = 1..7 channel inputs, E = 8 common emitter ("typically tied to ground"), COM = 9 common cathode of the clamp diodes,
  7C..1C = 10..16 open-collector outputs; positions from the N (R-PDIP-T16) mechanical drawing 4040049/E: pin pitch 0.100 in (2.54 mm), rows
  0.300 in (7.62 mm) apart (the drawing's 0.300 (7,62) minimum lead spread, the JEDEC MS-001 300-mil row)
  §5.1 absolute maximum: collector-emitter 50 V; input 30 V; peak collector current 500 mA; total emitter-terminal current -2.5 A; operating
  free-air -40 .. 70 C (ULN200xA); §5.6 at 25 C: V_I(on) 2.4 V max at I_C 200 mA (V_CE 2 V); input current 1.35 mA max at V_I 3.85 V;
  §5.2 ESD: HBM +-2000 V (ANSI/ESDA/JEDEC JS-001), CDM +-500 V (JESD22-C101)
"""
import json
import math

from board.custom import bench as B

CLS = 'PartBoard'
_MEM = {CLS: {}}
UNKNOWN = -1.0
NO_TEMP = -300.0
ROLE_DIRECTION = {'in': 'in', 'out': 'out', 'supply': 'supply', 'ground': 'supply', 'common': 'passive', 'nc': 'passive'}
ULN_DOC = 'TI SLRS027T, ULN200x / ULQ200x High-Voltage, High-Current Darlington Transistor Arrays (rev. March 2025)'


def _uln_pins():
    pins = [{'number': k, 'name': '%dB' % k, 'role': 'in', 'channel': k, 'x_mm': round((k - 1) * 2.54, 3), 'y_mm': 7.62} for k in range(1, 8)]
    pins.append({'number': 8, 'name': 'E', 'role': 'ground', 'channel': 0, 'x_mm': round(7 * 2.54, 3), 'y_mm': 7.62})
    pins.append({'number': 9, 'name': 'COM', 'role': 'common', 'channel': 0, 'x_mm': round(7 * 2.54, 3), 'y_mm': 0.0})
    pins += [{'number': k, 'name': '%dC' % (17 - k), 'role': 'out', 'channel': 17 - k, 'x_mm': round((16 - k) * 2.54, 3), 'y_mm': 0.0} for k in range(10, 17)]
    return pins


SEED = [{
    'name': 'uln2003a-n', 'kind': 'darlington-array', 'part_number': 'ULN2003AN', 'package': 'PDIP-16 (TI N, R-PDIP-T16)', 'channels': 7,
    'pins_json': json.dumps(_uln_pins()), 'on_volts': 2.4, 'draw_ma': 1.35, 'in_max_v': 30.0, 'out_sink_ma': 500.0, 'out_source_ma': 0.0,
    'out_max_v': 50.0, 'supply_min_v': UNKNOWN, 'supply_max_v': UNKNOWN, 'total_ma': 2500.0, 't_min_c': -40.0, 't_max_c': 70.0, 'esd_hbm_v': 2000.0,
    'esd_cdm_v': 500.0,
    'position_basis': 'N (R-PDIP-T16) drawing 4040049/E: pitch 0.100 in (2.54 mm), rows 0.300 in (7.62 mm) apart (JEDEC MS-001); top view, pin 1 '
                      'bottom left, pin 16 opposite it',
    'contract_basis': ('on_volts = V_I(on) max at I_C 200 mA, V_CE 2 V (§5.6; 2.7 V at 250 mA, 3 V at 300 mA); draw_ma = I_I max at V_I 3.85 V (§5.6); '
                       'in_max_v = V_I (§5.1); out_sink_ma = peak collector current (§5.1, an absolute maximum - the continuous figure falls with duty '
                       'cycle and channels on, Figures 5-4 / 5-5); out_source_ma 0 = an open collector sources nothing (Table 4-1); out_max_v = V_CC '
                       'collector-emitter (§5.1); total_ma = total emitter-terminal current (§5.1)'),
    'document': ULN_DOC, 'page_table': '§3, Table 4-1, §5.1, §5.2, §5.6; N package drawing', 'url': 'https://www.ti.com/lit/ds/symlink/uln2003a.pdf',
    'origin': 'cited', 'notes': 'COM goes to the load supply for inductive loads (the clamp diodes); E to ground'}]

_NUMS = ('on_volts', 'draw_ma', 'in_max_v', 'out_sink_ma', 'out_source_ma', 'out_max_v', 'supply_min_v', 'supply_max_v', 'total_ma', 'esd_hbm_v',
         'esd_cdm_v')


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _fields():
    import inspect
    from board.objects.board.PartBoard import PartBoard
    return [k for k in inspect.signature(PartBoard.__init__).parameters if k not in ('self', 'manager')]


def _as_dict(o):
    return {k: _get(o, k) for k in _fields()}


def _live(manager):
    if manager is None:
        return list(_MEM[CLS].values())
    return [_as_dict(o) for o in ((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).values()]


def catalogue(manager=None):
    """Every part: live rows over the seed (a live row of the same name wins), each with its contract in words."""
    by = {r['name']: dict(r) for r in SEED}
    by.update({r['name']: r for r in _live(manager)})
    return [dict(r, pins=len(json.loads(r['pins_json'] or '[]')), contract=contract_words(r), definition='part/%s' % r['name'])
            for r in sorted(by.values(), key=lambda r: r['name'])]


def part(name, manager=None):
    return next((r for r in catalogue(manager) if r['name'] == name), None)


def contract_words(r):
    def n(k, unit):
        v = float(r.get(k, UNKNOWN) if r.get(k) is not None else UNKNOWN)
        return '%g %s' % (v, unit) if v >= 0 else 'not given'
    return ('in: on from %s, draws %s, max %s; out: sinks %s, sources %s, max %s; total %s'
            % (n('on_volts', 'V'), n('draw_ma', 'mA'), n('in_max_v', 'V'), n('out_sink_ma', 'mA'), n('out_source_ma', 'mA'), n('out_max_v', 'V'),
               n('total_ma', 'mA')))


def footholds(r):
    cite = r.get('document') or ('custom: %s' % (r.get('notes') or 'defined by a person'))
    out = []
    for p in json.loads(r['pins_json'] or '[]'):
        role, num = p['role'], str(p['number'])
        f = {'name': 'part:%s:%s' % (r['name'], num), 'definition_kind': 'part', 'definition': r['name'], 'foothold': num, 'kind': 'pin',
             'label': p.get('name', num), 'x_mm': float(p.get('x_mm', 0.0)), 'y_mm': float(p.get('y_mm', 0.0)), 'position_basis': r.get('position_basis', ''),
             'side': 'top', 'node': 'pin:%s' % num, 'net': '', 'rail_volts': UNKNOWN, 'logic_volts': UNKNOWN, 'source_ma': UNKNOWN, 'sink_ma': UNKNOWN,
             'draw_ma': UNKNOWN, 'on_volts': UNKNOWN, 'max_volts': UNKNOWN, 'drive_basis': '', 'families_json': '[]', 'chip_pin': '',
             'direction': ROLE_DIRECTION.get(role, 'undetermined'), 'signal_basis': 'pin role %s (%s)' % (role, cite), 'undetermined': '', 'notes': ''}
        if role == 'in':
            f.update(draw_ma=float(r.get('draw_ma', UNKNOWN)), on_volts=float(r.get('on_volts', UNKNOWN)), max_volts=float(r.get('in_max_v', UNKNOWN)),
                     drive_basis='input of channel %s: %s (%s)' % (p.get('channel', '?'), contract_words(r), cite))
        elif role == 'out':
            f.update(source_ma=float(r.get('out_source_ma', UNKNOWN)), sink_ma=float(r.get('out_sink_ma', UNKNOWN)), max_volts=float(r.get('out_max_v', UNKNOWN)),
                     drive_basis='output of channel %s: %s (%s)' % (p.get('channel', '?'), contract_words(r), cite))
        elif role == 'ground':
            f.update(rail_volts=0.0, drive_basis='the part\'s ground / common emitter: 0 V by use (%s)' % cite)
        elif role == 'supply':
            f['drive_basis'] = 'supply %s .. %s V (%s)' % (r.get('supply_min_v'), r.get('supply_max_v'), cite)
            f['undetermined'] = 'the supply voltage is whatever the bench applies'
        out.append(f)
    return out


def define(manager, body):
    """A custom part (a person's mini board): {name, kind, pins: [{number, name, role, channel?, x_mm, y_mm}], contract numbers?, document?, ...}."""
    from board.objects.board.PartBoard import PartBoard
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'body must be an object'}
    name = str(body.get('name', '')).strip()
    if not name or not all(c.isalnum() or c in '-_.' for c in name):
        return 400, {'ok': False, 'error': 'name needs letters, digits, - _ . only, got %r' % name}
    if any(s['name'] == name for s in SEED):
        return 409, {'ok': False, 'error': '%r is a cited catalogue part - give yours its own name' % name}
    if body.get('kind') not in PartBoard.KINDS:
        return 400, {'ok': False, 'error': 'kind must be one of %s' % ', '.join(PartBoard.KINDS)}
    pins = body.get('pins')
    if not isinstance(pins, list) or not pins:
        return 400, {'ok': False, 'error': 'pins must be a list of {number, name, role, x_mm, y_mm}'}
    seen, clean = set(), []
    for p in pins:
        try:
            num, x, y = str(p['number']), float(p['x_mm']), float(p['y_mm'])
        except (KeyError, TypeError, ValueError):
            return 400, {'ok': False, 'error': 'each pin needs number, x_mm and y_mm (numbers): %r' % (p,)}
        if p.get('role') not in PartBoard.ROLES:
            return 400, {'ok': False, 'error': 'pin %s: role must be one of %s' % (num, ', '.join(PartBoard.ROLES))}
        if num in seen:
            return 400, {'ok': False, 'error': 'pin %s is given twice' % num}
        seen.add(num)
        clean.append({'number': p['number'], 'name': str(p.get('name', num)), 'role': p['role'], 'channel': p.get('channel', 0), 'x_mm': x, 'y_mm': y})
    row = {k: body.get(k, '') for k in ('kind', 'part_number', 'package', 'position_basis', 'contract_basis', 'document', 'page_table', 'url', 'notes')}
    for k in _NUMS:
        try:
            v = float(body.get(k, UNKNOWN))
        except (TypeError, ValueError):
            return 400, {'ok': False, 'error': '%s needs a number' % k}
        if not math.isfinite(v) or (v < 0 and v != UNKNOWN):
            return 400, {'ok': False, 'error': '%s must be >= 0 or -1 (not given), got %r' % (k, body.get(k))}
        row[k] = v
    row.update(name=name, channels=int(body.get('channels') or len({p['channel'] for p in clean if p['role'] in ('in', 'out')})),
               pins_json=json.dumps(clean), t_min_c=float(body.get('t_min_c', NO_TEMP)), t_max_c=float(body.get('t_max_c', NO_TEMP)),
               origin='cited' if body.get('document') else 'custom')
    if manager is None:
        _MEM[CLS][name] = row
    else:
        o = PartBoard(manager=manager, **row)
        try:
            manager.db.saveInstanceInDB(o)
        except Exception:  # noqa: BLE001 - an in-memory manager has no db
            pass
    return 201, {'ok': True, 'name': name, 'definition': 'part/%s' % name, 'footholds': len(clean), 'origin': row['origin']}


def add_part(manager, bench_name, body):
    """(status, body): a part onto a bench as a BenchBoard of kind part (it then has footholds, mounts and wires like any Board)."""
    from board.custom import bench_boards as BB
    if B.bench(bench_name, manager) is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    name = str((body or {}).get('part', '')).strip()
    if part(name, manager) is None:
        return 404, {'ok': False, 'error': 'no part named %r' % name, 'known': [r['name'] for r in catalogue(manager)]}
    if manager is None:
        return 503, {'ok': False, 'error': 'no object manager: a Board on the Bench is a stored row'}
    from electrodevice.objects.layout.BenchBoard import BenchBoard
    mine = [o for o in BB._rows(manager, 'BenchBoard') if getattr(o, 'bench', '') == bench_name and getattr(o, 'definition', '') == name
            and getattr(o, 'definition_kind', '') == 'part']
    row_name = '%s:part:%s#%d' % (bench_name, name, len(mine) + 1)
    BenchBoard(manager=manager, name=row_name, model_name='part', label=str(body.get('label') or '%s #%d' % (name, len(mine) + 1)), owner='',
               notes=str(body.get('note') or ''), bench=bench_name, definition_kind='part', definition=name)
    return 201, {'ok': True, 'bench': bench_name, 'added': row_name, 'rows': BB.boards_on_bench(bench_name, manager)}


def _fixes(finding, members, cat):
    """Catalogue parts whose cited contract fixes one finding, each with the evidence in words."""
    out = []
    kind = finding['kind']
    if kind == 'drive-shortfall':
        need, level = finding['need_ma'], finding.get('source_volts', UNKNOWN)
        for r in cat:
            sink, src = float(r['out_sink_ma']), float(r['out_source_ma'])
            if r['kind'] == 'load' or max(sink, src) < need:
                continue
            ok_level = level < 0 or 0 <= float(r['on_volts']) <= level
            out.append({'part': r['name'], 'kind': r['kind'], 'why': ('its outputs %s up to %g mA (need %g mA); its input turns on from %s and draws %s - %s'
                                                                       % ('sink' if sink >= src else 'source', max(sink, src), need,
                                                                          ('%g V' % float(r['on_volts'])) if float(r['on_volts']) >= 0 else 'an uncited level',
                                                                          ('%g mA' % float(r['draw_ma'])) if float(r['draw_ma']) >= 0 else 'an uncited current',
                                                                          'the driving pin\'s %g V reaches it' % level if ok_level and level >= 0 else
                                                                          'check the driving level' if ok_level else
                                                                          'NOT reached by the driving pin\'s %g V' % level)),
                        'fits': ok_level, 'source': r['document'] or r['origin']})
    elif kind in ('over-voltage', 'under-voltage'):
        for r in cat:
            if r['kind'] in ('level-shifter', 'buffer'):
                out.append({'part': r['name'], 'kind': r['kind'], 'why': 'a %s puts each side on its own supply: %s' % (r['kind'], contract_words(r)),
                            'fits': True, 'source': r['document'] or r['origin']})
        if not out:
            out.append({'part': '', 'kind': 'level-shifter', 'why': 'no level shifter or buffer in the catalogue yet - define one (POST /api/board/parts) '
                                                                    'from its datasheet', 'fits': False, 'source': ''})
    return out


def suggestions(nets, manager=None):
    cat = catalogue(manager)
    rows = []
    for n in nets:
        for f in n['findings']:
            if f['kind'] not in ('drive-shortfall', 'over-voltage', 'under-voltage'):
                continue
            for s in _fixes(f, n['members'], cat) or [{'part': '', 'kind': '', 'why': 'no catalogue part fixes this yet', 'fits': False, 'source': ''}]:
                rows.append(dict(s, net=n['net'], finding=f['kind'], problem=f['words']))
    return rows
