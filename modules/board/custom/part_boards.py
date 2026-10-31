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
  suggestions(nets, manager) / budgets(nets, manager)   board.custom.part_fixes (re-exported here): the fixes, judged, and whole-part budgets

"""
import json
import math

from board.custom import bench as B
from board.custom.part_seed import SEED  # noqa: F401 - the cited catalogue lives in its own file

CLS = 'PartBoard'
_MEM = {CLS: {}}
UNKNOWN = -1.0
NO_TEMP = -300.0
ROLE_DIRECTION = {'in': 'in', 'out': 'out', 'supply': 'supply', 'ground': 'supply', 'common': 'passive', 'nc': 'passive', 'regulated': 'supply'}
_NUMS = ('on_volts', 'draw_ma', 'in_max_v', 'out_sink_ma', 'out_source_ma', 'out_max_v', 'supply_min_v', 'supply_max_v', 'total_ma', 'esd_hbm_v',
         'esd_cdm_v', 'out_volts')
REGULATORS = ('ldo', 'buck', 'boost')
PIN_OVERRIDES = ('on_volts', 'draw_ma', 'max_volts', 'source_ma', 'sink_ma', 'logic_volts')


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
    if r.get('kind') in REGULATORS:
        return ('out: %s at up to %s; in: %s .. %s; needs %s'
                % (n('out_volts', 'V'), n('out_source_ma', 'mA'), n('supply_min_v', 'V'), n('supply_max_v', 'V'), r.get('needs') or 'nothing else'))
    return ('in: on from %s, draws %s, max %s; out: sinks %s, sources %s, high at %s, max %s; total %s%s'
            % (n('on_volts', 'V'), n('draw_ma', 'mA'), n('in_max_v', 'V'), n('out_sink_ma', 'mA'), n('out_source_ma', 'mA'), n('out_volts', 'V'),
               n('out_max_v', 'V'), n('total_ma', 'mA'), ('; needs %s' % r['needs']) if r.get('needs') else ''))


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
                     logic_volts=float(r.get('out_volts', UNKNOWN) if r.get('out_volts') is not None else UNKNOWN),
                     drive_basis='output of channel %s: %s (%s)' % (p.get('channel', '?'), contract_words(r), cite))
        elif role == 'regulated':
            f.update(rail_volts=float(r.get('out_volts', UNKNOWN)), source_ma=float(r.get('out_source_ma', UNKNOWN)),
                     drive_basis='regulated output: %s (%s)' % (contract_words(r), cite))
        elif role == 'ground':
            f.update(rail_volts=0.0, drive_basis='the part\'s ground / common emitter: 0 V by use (%s)' % cite)
        elif role == 'supply':
            f['drive_basis'] = 'supply %s .. %s V (%s)' % (r.get('supply_min_v'), r.get('supply_max_v'), cite)
            f['undetermined'] = 'the supply voltage is whatever the bench applies'
        over = {k: float(p[k]) for k in PIN_OVERRIDES if k in p}
        if over:   # drv-2: this pin's own numbers (a TLC5916's SDO; a regulator's input minimum)
            f.update(over)
            f['drive_basis'] += '; pin %s\'s own: %s' % (num, ', '.join('%s %g' % kv for kv in sorted(over.items())))
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
        pin = {'number': p['number'], 'name': str(p.get('name', num)), 'role': p['role'], 'channel': p.get('channel', 0), 'x_mm': x, 'y_mm': y}
        for k in PIN_OVERRIDES:
            if k in p:
                try:
                    pin[k] = float(p[k])
                except (TypeError, ValueError):
                    return 400, {'ok': False, 'error': 'pin %s: %s needs a number' % (num, k)}
        clean.append(pin)
    row = {k: body.get(k, '') for k in ('kind', 'part_number', 'package', 'position_basis', 'contract_basis', 'document', 'page_table', 'url', 'notes',
                                        'needs')}
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


from board.custom.part_fixes import budgets, suggestions  # noqa: E402,F401 - re-exported (callers use part_boards.suggestions)
