"""
@module electrodevice.custom.board_models

D-bob-3 (BENCH_BOARDS_PLAN, 2026-10-30): ONE BOARD MODEL, READ WHOLE. A BoardModel holds identity only; the facts only some boards have are their own rows
naming the model (BreadboardLayout, BoardOutline, BoardRating). `composed()` joins them into one flat dict per model for the code that reads a board as a
whole (the board family, the bench's selection list, the footholds) - a READ view, never stored. Live rows win over the code seeds, row by row.

  composed(manager=None) -> {model name: dict}   identity + layout (size, rows, holes_per_side, rails, rail_holes, pitch_mm, tie_points, layout_basis)
                                                 + outline (width_mm, height_mm, drawable, outline_basis) + rating (rail_voltage_max_v, rail_current_max_a, rating_basis)
  canonical(name)                                an older board.BreadboardModel name (half-400, full-830) -> the merged model's name
  derived_ties(row)                              rows x holes_per_side x 2 + rails x rail_holes

Outline: a vendor-STATED outline is a BoardOutline row; otherwise a laid-out breadboard's outline is DERIVED from its layout (board.custom.pv_shapes.
breadboard_geometry, the pin view's own drawing) and is drawable. Rating: a rail-less layout says n/a; anything else without a BoardRating row says no
rating is cited (-1, never a typical value).
"""
from electrodevice.objects.layout import _board_seeds as SEEDS

TABLES = ('BoardModel', 'BreadboardLayout', 'BoardOutline', 'BoardRating')
_MODEL = ('name', 'title', 'kind', 'vendor', 'part_number', 'status', 'board_definition', 'description', 'notes')
_LAYOUT = ('size', 'rows', 'holes_per_side', 'rails', 'rail_holes', 'pitch_mm', 'tie_points')
#: what a board with no layout reads as: a devboard / reserved kind has no strips (0); a breadboard with no layout row is undetermined (-1)
_NO_LAYOUT = {'size': '', 'rows': 0, 'holes_per_side': 0, 'rails': 0, 'rail_holes': 0, 'pitch_mm': SEEDS.PITCH_MM, 'tie_points': 0}
_UNKNOWN_LAYOUT = {'size': 'unverified', 'rows': -1, 'holes_per_side': 5, 'rails': -1, 'rail_holes': -1, 'pitch_mm': SEEDS.PITCH_MM, 'tie_points': -1}


def canonical(name):
    return SEEDS.MODEL_ALIASES.get(name, name)


def _live(manager, cls):
    t = ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}) if manager is not None else {}
    return [{k: v for k, v in vars(o).items() if not k.startswith('_')} if not isinstance(o, dict) else dict(o) for o in (t.values() if isinstance(t, dict) else t)]


def _by(seeds, live, key):
    out = {r[key]: dict(r) for r in seeds}
    out.update({r.get(key, ''): r for r in live})
    return out


def derived_ties(row):
    return int(row['rows']) * int(row['holes_per_side']) * 2 + int(row['rails']) * int(row['rail_holes'])


def _derived_outline(layout):
    try:
        from board.custom import pv_shapes as PV
        g = PV.breadboard_geometry(layout['rows'], layout['rail_holes'], layout['pitch_mm'])
        return float(g['w']), float(g['h']), 'derived: pv_shapes.breadboard_geometry(rows=%d, rail_holes=%d) at the %g mm pitch' % (layout['rows'], layout['rail_holes'], layout['pitch_mm'])
    except Exception:  # noqa: BLE001 - the drawing helper is the board module's; without it the outline is undetermined, said so
        return -1.0, -1.0, 'undetermined: the drawing helper (board.custom.pv_shapes) is not loaded; the hole layout itself is known'


def composed(manager=None):
    models = _by(SEEDS.SEED_BOARD_MODELS, _live(manager, 'BoardModel'), 'name')
    layouts = _by(SEEDS.SEED_BREADBOARD_LAYOUTS, _live(manager, 'BreadboardLayout'), 'board_model')
    outlines = _by(SEEDS.SEED_BOARD_OUTLINES, _live(manager, 'BoardOutline'), 'board_model')
    ratings = _by(SEEDS.SEED_BOARD_RATINGS, _live(manager, 'BoardRating'), 'board_model')
    out = {}
    for name, m in models.items():
        row = {k: m.get(k, '') for k in _MODEL}
        lay = layouts.get(name)
        base = _UNKNOWN_LAYOUT if row['kind'] == 'breadboard' else _NO_LAYOUT
        row.update({k: (lay or base).get(k, base[k]) for k in _LAYOUT})
        row['layout_basis'] = (lay or {}).get('basis', '') or ('no BreadboardLayout row: the layout is undetermined' if row['kind'] == 'breadboard' else '')
        laid = row['kind'] == 'breadboard' and int(row['rows']) > 0 and int(row['rail_holes']) >= 0
        o = outlines.get(name)
        if o:
            row.update(width_mm=float(o['width_mm']), height_mm=float(o['height_mm']), drawable=bool(o['drawable']), outline_basis=o.get('basis', ''))
        elif laid:
            w, h, why = _derived_outline(row)
            row.update(width_mm=w, height_mm=h, drawable=True, outline_basis=why)
        else:
            row.update(width_mm=-1.0, height_mm=-1.0, drawable=False, outline_basis='no layout and no stated outline' if row['kind'] == 'breadboard' else '')
        r = ratings.get(name)
        if r:
            row.update(rail_voltage_max_v=float(r['rail_voltage_max_v']), rail_current_max_a=float(r['rail_current_max_a']), rating_basis=r.get('basis', ''))
        else:
            why = '' if row['kind'] != 'breadboard' else ('n/a: this model has no power rails (rails 0)' if int(row['rails']) == 0 else
                                                          'unverified: no rail rating cited for this model')
            row.update(rail_voltage_max_v=-1.0, rail_current_max_a=-1.0, rating_basis=why)
        out[name] = row
    return out
