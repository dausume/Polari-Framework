"""
@cross-cutting
@module casting.fill_sim
@tags @xc:bindings

cast-5 core: SIMULATE THE FILL — does the poured material reach
everywhere, and where does air get trapped? Quasi-static gravity
model on the cast-2 OccupancyGrid, with the cast-4 channels as the
plumbing:

  DOMAIN     the `--master-sprued` shape (cavity + channels as ONE
             solid) voxelized on the STOCK lattice — channel exits
             land exactly on the grid boundary, so "outside" is
             well-defined.
  FEED       fluid enters at the SPRUE mouths (boundary cells inside
             the sprue shapes — vents are air exits, not feeds) and
             fills level-by-level from the bottom; channels are
             always traversable (fluid falls through them).
  UNFED      cavity regions with NO path from the gate at all — the
             gate feeds the wrong chamber (a real two-chamber
             failure this sim catches).
  AIR        at every level, air must escape to a boundary through
             air cells OR through channels (counterflow up a filled
             gate is allowed WITH a finding — bubble defects); an
             air region that loses every escape path is TRAPPED at
             that level and never fills.
  FREEZE     fill time (cavity volume ÷ pour rate, Torricelli rate
             from the gate neck by default — claim named) against
             the material's pot life; ratio > 1 blocks.

Verdicts are knobs-and-suggestions: a trapped pocket names its top
cell — exactly where cast-4 would put the next vent — and never
auto-applies anything.

MoldFillSimState rows (one per domain cell per recorded level, the
WaxPrintSimState idiom) make runs 3D-viewable; the SimSpace scene
binding lands with the cast-9 page pass (named).

Named unmodelled v1: turbulence, surface tension/menisci, viscosity-
limited channel flow, gas back-pressure magnitude, thermal front
during fill (metals refuse — their freeze window is not seeded).

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-5)
"""

import json
import math

from casting.mold_geometry import _mold_named, _rows
from casting.voxel_grid import OccupancyGrid
from casting.wax_feasibility import _row_named
from mathshapes.shape_analysis import _named, evaluate_point
from objectTreeDecorators import treeObject, treeObjectInit

_G = 9.80665

#: Pourable materials + pot life (how long the mix stays fluid).
#: Metals refuse v1: their freeze-during-fill window is genuinely
#: unmodelled (gap thm-*), not defaulted.
FILL_MATERIAL_PRIORS = {
    'geopolymer-slurry': {
        'pot_life_s': 1800.0,
        'claim': 'literature-approximate ~30 min workable time — '
                 'mix-dependent, measure the real batch'},
    'water-test': {'pot_life_s': None,
                   'claim': 'water does not set — bench-test medium'},
}


class MoldFillSimState(treeObject):
    """One rendered voxel of one fill run at one recorded level —
    the WaxPrintSimState idiom (rows are 3D-viewable; the scene
    binding lands with cast-9)."""

    simulation_definition_name = 'mold-fill'

    @treeObjectInit
    def __init__(self, name: str = '', simulation_run_ref: str = '',
                 mold_ref: str = '', step: int = 0, time: float = 0.0,
                 pos_x: float = 0.0, pos_y: float = 0.0,
                 pos_z: float = 0.0,
                 # 0 empty · 1 filled · 2 channel · 3 trapped ·
                 # 4 unfed
                 render_state: int = 0,
                 manager=None):
        self.name = name
        self.simulation_run_ref = simulation_run_ref
        self.mold_ref = mold_ref
        self.step = step
        self.time = time
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.render_state = render_state


def _sprue_instance_for(manager, mold_name):
    for r in _rows(manager, 'SprueSetInstance'):
        if getattr(r, 'mold_ref', '') == mold_name:
            return r
    return None


def _boundary_cells(grid, cells):
    n = grid.n
    return {c for c in cells
            if 0 in c or (n - 1) in c}


def _cells_in_shapes(manager, grid, cells, shape_names):
    """Which of `cells` sit inside any of the named shapes — used to
    tell sprue mouths from vent mouths on the boundary (few cells,
    exact field evaluation)."""
    hits = set()
    for c in cells:
        x, y, z = grid.cell_center(c)
        for nm in shape_names:
            r = evaluate_point(manager, nm, x, y, z)
            if r.get('inside'):
                hits.add(c)
                break
    return hits


def simulate_fill(manager, mold_name, cast_material='geopolymer-slurry',
                  resolution=24, pour_rate_cm3_s=None,
                  record_levels=4):
    """Run the gravity fill. Returns fill fraction, trapped pockets
    (with the vent-here suggestion), unfed regions, counterflow
    findings, fill-time vs pot-life, and per-level cell states."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    prior = FILL_MATERIAL_PRIORS.get(cast_material)
    if prior is None:
        if cast_material == 'plastic-clay':
            return {'ok': False,
                    'refusal': 'pressed material',
                    'error': 'plastic clay is PRESSED, not poured — '
                             'a fill simulation does not apply '
                             '(placement, not flow)'}
        return {'ok': False,
                'error': f"no fill data for '{cast_material}' — "
                         f'metals refuse until their freeze-during-'
                         f'fill window is measured (named gap); '
                         f'know: {sorted(FILL_MATERIAL_PRIORS)}',
                'knownMaterials': sorted(FILL_MATERIAL_PRIORS)}
    inst = _sprue_instance_for(manager, mold_name)
    if inst is None:
        return {'ok': False,
                'error': f"mold '{mold_name}' has no SprueSetInstance "
                         f'— a fill needs a gate; run '
                         f'apply_sprue_strategy first'}
    domain_shape = getattr(inst, 'sprued_master_shape_name', '')
    cavity_shape = (getattr(mold, 'scaled_part_shape_name', '')
                    or getattr(mold, 'part_shape_ref', ''))
    stock = _named(manager, getattr(mold, 'stock_shape_name', ''))
    try:
        params = json.loads(getattr(stock, 'parameters_json', '{}'))
        size, center = params['size'], params['center']
        stock_bounds = [[center[i] - size[i] / 2.0,
                         center[i] + size[i] / 2.0] for i in range(3)]
    except (AttributeError, KeyError, TypeError, ValueError):
        return {'ok': False, 'error': 'stock bounds unreadable'}

    domain = OccupancyGrid.from_shape(manager, domain_shape,
                                      resolution=resolution,
                                      bounds=stock_bounds)
    cavity = OccupancyGrid.from_shape(manager, cavity_shape,
                                      resolution=resolution,
                                      bounds=stock_bounds)
    if not isinstance(domain, OccupancyGrid) \
            or not isinstance(cavity, OccupancyGrid):
        return {'ok': False, 'error': 'domain/cavity voxelization '
                                      'failed'}
    channels = domain.inside - cavity.inside
    boundary = _boundary_cells(domain, domain.inside)
    sprue_names = json.loads(getattr(inst, 'sprue_shape_names_json',
                                     '[]') or '[]')
    # the instance records the -eq equation rows; the BOUNDED solids
    # share the name minus the suffix (the cast-4 pair convention).
    sprue_solids = [n[:-3] if n.endswith('-eq') else n
                    for n in sprue_names]
    feed_mouths = _cells_in_shapes(manager, domain, boundary,
                                   sprue_solids)
    if not feed_mouths:
        return {'ok': False,
                'error': 'no sprue mouth reaches the stock boundary '
                         '— the gate does not connect to the outside'}

    findings, gaps, blockers = [], [], []
    reachable = domain.flood_fill(feed_mouths)
    unfed_cells = cavity.inside - reachable
    unfed_regions = domain.connected_components(unfed_cells) \
        if unfed_cells else []
    for reg in unfed_regions:
        top = max(reg, key=lambda c: c[2])
        blockers.append(
            f'UNFED region of {len(reg)} cells (top cell {top}) — '
            f'no path from the gate reaches it; add a gate/runner '
            f'into this chamber')

    # ---- level-by-level fill with air-escape bookkeeping ----
    filled, trapped = set(), set()
    counterflow_used = False
    levels = sorted({c[2] for c in reachable})
    recorded = []
    record_at = {levels[int(i * (len(levels) - 1)
                            / max(1, record_levels - 1))]
                 for i in range(record_levels)} if levels else set()
    for lv in levels:
        traversable = {c for c in reachable
                       if c[2] <= lv or c in channels}
        filled = domain.flood_fill(feed_mouths, traversable) - trapped
        air = reachable - filled - trapped
        # air escapes through air cells; counterflow through
        # channels is allowed but NOTED (bubbles up the gate).
        air_escape_domain = air | channels
        air_mouths = _boundary_cells(domain, air_escape_domain)
        escaped = domain.flood_fill(air_mouths, air_escape_domain)
        newly_trapped = air - escaped
        pure_air_escape = domain.flood_fill(
            _boundary_cells(domain, air), air)
        if (air - pure_air_escape) - newly_trapped:
            counterflow_used = True
        trapped |= newly_trapped
        if lv in record_at:
            recorded.append({'level': lv,
                             'filled': set(filled),
                             'trapped': set(trapped)})
    trapped_pockets = domain.connected_components(trapped) \
        if trapped else []
    suggestions = []
    for pk in trapped_pockets:
        top = max(pk, key=lambda c: c[2])
        x, y, z = domain.cell_center(top)
        suggestions.append(
            {'kind': 'vent',
             'atCell': list(top),
             'atPointCm': [round(x, 3), round(y, 3), round(z, 3)],
             'evidence': f'trapped air pocket of {len(pk)} cells '
                         f'peaks here — a vent at this high point '
                         f'gives it an escape path (cast-4 '
                         f'high-points placement would choose it)'})
        blockers.append(
            f'TRAPPED air pocket ({len(pk)} cells, top {top}) — '
            f'void in the cast part; see the vent suggestion')
    if counterflow_used:
        findings.append(
            'air escaped by COUNTERFLOW up a feed channel — works, '
            'but slows the pour and risks bubble defects; a '
            'dedicated vent is cleaner')

    # ---- fill time vs pot life ----
    cavity_vol = len(cavity.inside & reachable) * domain.cell_volume
    rate = pour_rate_cm3_s
    rate_basis = 'caller-declared pour rate'
    if rate is None and sprue_names:
        # Torricelli through the gate: v = √(2·g·head), head taken
        # from the stock top to mid-height; the mouth area is
        # MEASURED off the grid (feed cells × cell face area).
        head_m = (stock_bounds[2][1]
                  - (stock_bounds[2][0] + stock_bounds[2][1]) / 2.0) \
            / 100.0
        neck_area_cm2 = max(1, len(feed_mouths)) \
            * domain.dx * domain.dy
        v_cm_s = math.sqrt(2.0 * _G * max(0.01, head_m)) * 100.0
        rate = neck_area_cm2 * v_cm_s
        rate_basis = (f'Torricelli through the measured gate mouth '
                      f'({neck_area_cm2:.3f}cm² × '
                      f'√(2g·{head_m * 100:.0f}cm)) — an upper '
                      f'bound; viscosity-limited flow is unmodelled '
                      f'(named)')
    fill_time_s = cavity_vol / rate if rate else None
    pot_life = prior.get('pot_life_s')
    freeze = {'fillTimeS': round(fill_time_s, 2)
              if fill_time_s else None,
              'rateBasis': rate_basis,
              'potLifeS': pot_life,
              'claim': prior.get('claim')}
    if fill_time_s and pot_life:
        ratio = fill_time_s / pot_life
        freeze['ratio'] = round(ratio, 4)
        if ratio >= 1.0:
            blockers.append(
                f'fill time {fill_time_s:.0f}s exceeds the '
                f'{cast_material} pot life {pot_life:.0f}s — the '
                f'mix sets mid-fill')
        elif ratio > 0.5:
            findings.append(f'fill uses {ratio:.0%} of the pot life '
                            f'— thin margin')

    gaps.extend([
        'turbulence / surface tension / menisci unmodelled '
        '(quasi-static levels)',
        'channel flow is not viscosity-limited (Torricelli upper '
        'bound named in the rate basis)',
        'gas back-pressure magnitude unmodelled — trapped pockets '
        'are detected topologically, their compression is not',
        'metals refuse until a freeze-during-fill window is '
        'measured',
        'SimSpace scene binding for these rows lands with the '
        'cast-9 page pass'])

    fill_fraction = (len(filled & cavity.inside)
                     / len(cavity.inside)) if cavity.inside else 0.0
    return {'ok': True, 'mold': mold_name,
            'castMaterial': cast_material,
            'domainCells': len(domain.inside),
            'cavityCells': len(cavity.inside),
            'channelCells': len(channels),
            'fillFraction': round(fill_fraction, 4),
            'unfedRegions': [len(r) for r in unfed_regions],
            'trappedPockets': [len(p) for p in trapped_pockets],
            'suggestions': suggestions,
            'freeze': freeze,
            'blockers': blockers, 'findings': findings, 'gaps': gaps,
            'verdict': 'blocked' if blockers else 'feasible',
            'recordedLevels': recorded,
            'grids': {'domain': domain, 'cavity': cavity,
                      'channels': channels, 'filled': filled,
                      'trapped': trapped, 'unfed': unfed_cells},
            'note': 'suggestions are evidence-bearing and never '
                    'auto-applied; a trapped pocket names the exact '
                    'high point the next vent should occupy.'}


def compute_fill_rows(manager, mold_name, run_name,
                      cast_material='geopolymer-slurry',
                      resolution=24, record_levels=3):
    """MoldFillSimState row dicts for a run — display-capped
    resolution, one row per domain cell per recorded level."""
    res = simulate_fill(manager, mold_name,
                        cast_material=cast_material,
                        resolution=resolution,
                        record_levels=record_levels)
    if not res.get('ok'):
        return res
    g = res['grids']
    domain, cavity = g['domain'], g['cavity']
    channels, unfed = g['channels'], g['unfed']
    rows = []
    for step, snap in enumerate(res['recordedLevels']):
        for c in domain.inside:
            x, y, z = domain.cell_center(c)
            if c in snap['trapped']:
                state = 3
            elif c in unfed:
                state = 4
            elif c in channels:
                state = 2       # channels render distinctly even
                # while carrying fluid — they fill from step 0
            elif c in snap['filled']:
                state = 1
            else:
                state = 0
            rows.append({'name': f'{run_name}-{step}-'
                                 f'{c[0]}-{c[1]}-{c[2]}',
                         'simulation_run_ref': run_name,
                         'mold_ref': mold_name, 'step': step,
                         'time': float(snap['level']),
                         'pos_x': round(x, 4), 'pos_y': round(y, 4),
                         'pos_z': round(z, 4),
                         'render_state': state})
    return {'ok': True, 'rows': rows,
            'verdict': res['verdict'],
            'summary': {k: res[k] for k in
                        ('fillFraction', 'trappedPockets',
                         'unfedRegions')}}
