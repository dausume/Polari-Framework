"""
@cross-cutting
@module casting.custom.sprue_geometry
@tags @xc:bindings

cast-4: AUTOMATED sprue + vent generation. Reuses the two proven
instruments instead of inventing new ones:

  - geometry lands as bounded cone-quadric `-eq` rows via
    mathshapes.custom.shape_modify.build_quadric_eq_row — the pot-hole
    idiom, so every channel is a real matrix equation;
  - placement comes from the cast-2 OccupancyGrid: the LOCAL part
    section at the attachment is a measured slice (cells × cell
    area, not a guess), and vents go where the connectivity says
    air pockets would form — the cavity's high regions.

Removability, made numeric (plan §4, named priors): per sprue,
ratio = neck area ÷ local section, gated by part-material class
(brittle ≤ 0.25 snap / ductile ≤ 0.40 cut), access recorded with
its basis, worst-wins across the set.

Both parity artifacts are emitted: `--body-sprued` (channels
SUBTRACTED from the mold body — negative parity) and
`--master-sprued` (solids UNIONED onto the part — positive parity);
cast-3's derived parity picks which one gets printed.

Grid-path (imported) molds refuse for now: their body has no CSG to
carve — sprues on grids land with the cast-5 fill sim (named).

Duck-typed manager, stdlib.
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-4)
"""

import json
import math

from casting.custom.mold_geometry import _converge_shape_rows, _mold_named
from casting.sprue_basis import NECK_RATIO_LIMITS
from casting.custom.voxel_grid import OccupancyGrid
from casting.custom.wax_feasibility import _row_named
from mathshapes.custom.shape_modify import build_quadric_eq_row

#: Placement grid — fine enough to slice local sections, cheap
#: enough to run at seed time.
GRID_RES = 24
#: Vents are thin escape channels, floored so they stay printable-
#: ish; the vent-vs-bead-width check is cast-5's (named in results).
MIN_VENT_RADIUS_CM = 0.08


def _strategy(manager, name):
    return _row_named(manager, 'SprueStrategyDefinition', name)


def _cavity_name(mold):
    return (getattr(mold, 'scaled_part_shape_name', '')
            or getattr(mold, 'part_shape_ref', ''))


def _slice_cells(grid, k):
    return [c for c in grid.inside if c[2] == k]


def _slice_area_and_centroid(grid, cells):
    area = len(cells) * grid.dx * grid.dy
    if not cells:
        return 0.0, (0.0, 0.0)
    cx = sum(grid.cell_center(c)[0] for c in cells) / len(cells)
    cy = sum(grid.cell_center(c)[1] for c in cells) / len(cells)
    return area, (cx, cy)


def _components_2d(grid, cells):
    """Face-connected components within one z-slice (reuses the 3D
    BFS on the subset — z-neighbours simply don't exist in it)."""
    return grid.connected_components(cells)


def apply_sprue_strategy(manager, mold_name, strategy_name,
                         part_brittleness='brittle', persist=True):
    """Generate gate + vents for a mold from a strategy; emit the
    equation rows, both parity artifacts, and the removability
    verdict. Re-application reconverges derived rows (cast-1 rule)."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    strat = _strategy(manager, strategy_name)
    if strat is None:
        return {'ok': False,
                'error': f"no SprueStrategyDefinition named "
                         f"'{strategy_name}'"}
    if not getattr(mold, 'body_shape_name', ''):
        if getattr(mold, 'derivation_json', ''):
            return {'ok': False, 'refusal': 'grid-path mold',
                    'error': f"mold '{mold_name}' is grid-derived "
                             f'(imported part) — its body has no CSG '
                             f'to carve channels from; sprues on '
                             f'grids land with the cast-5 fill sim '
                             f'(named absence)'}
        return {'ok': False,
                'error': f"mold '{mold_name}' is underived — run "
                         f'derive_mold first'}
    if part_brittleness not in NECK_RATIO_LIMITS:
        return {'ok': False,
                'error': f"part_brittleness '{part_brittleness}' — "
                         f'know: {sorted(NECK_RATIO_LIMITS)}'}
    cavity = _cavity_name(mold)
    grid = OccupancyGrid.from_shape(manager, cavity,
                                    resolution=GRID_RES)
    if not isinstance(grid, OccupancyGrid):
        return grid
    if not grid.inside:
        return {'ok': False,
                'error': f"cavity '{cavity}' voxelizes empty at "
                         f'resolution {GRID_RES}'}
    try:
        margin = float(getattr(mold, 'stock_margin_cm', 1.0) or 1.0)
    except (TypeError, ValueError):
        margin = 1.0
    b = grid.bounds
    stock_top_z = b[2][1] + margin
    style = getattr(strat, 'gate_style', 'top-gate')
    ratio = float(getattr(strat, 'neck_area_ratio', 0.2) or 0.2)
    taper = math.tan(math.radians(
        float(getattr(strat, 'sprue_taper_deg', 2.0) or 0.0)))
    mode = getattr(strat, 'removal_mode', 'snap')

    k_top = max(c[2] for c in grid.inside)
    top_cells = _slice_cells(grid, k_top)
    top_z = b[2][0] + (k_top + 0.5) * grid.dz

    rows, sprues, placements = [], [], []
    gate_xy = None

    def _channel(idx, base_r, top_r, length, axis, center, why,
                 local_section):
        # equation of record (quadric matrix) + the BOUNDED primitive
        # solid the CSG composes — a bare quadric is INFINITE under
        # the field evaluator (bounds_json only scopes grid scans),
        # so unioning it would leak a phantom column across the
        # stock. The pot idiom: -eq row + solid row, pair.
        eq_name = f'{mold_name}--sprue-{idx}-eq'
        solid_name = f'{mold_name}--sprue-{idx}'
        row, _q = build_quadric_eq_row(
            eq_name, f'{mold_name} sprue {idx} (equation)',
            base_r, top_r, length, axis, center,
            f'cast-4 {style} channel — {why}',
            max(base_r, top_r) * 3.0 + 0.5)
        rows.append({f: getattr(row, f) for f in
                     ('name', 'display_name', 'family',
                      'primitive_kind', 'csg_json', 'parameters_json',
                      'quadric_matrix_json', 'bounds_json', 'notes',
                      'provenance_id')})
        rows.append({
            'name': solid_name,
            'display_name': f'{mold_name} sprue {idx}',
            'family': 'primitive', 'primitive_kind': 'frustum',
            'quadric_matrix_json': '', 'csg_json': '',
            'bounds_json': '', 'provenance_id': 'cast-4',
            'notes': f'bounded solid of {eq_name}',
            'parameters_json': json.dumps({
                'base_radius': round(base_r, 5),
                'top_radius': round(top_r, 5),
                'height': round(length, 5), 'axis': axis,
                'center': center, 'cap_base': True,
                'cap_top': True})})
        sprues.append({'name': eq_name, 'solidName': solid_name,
                       'neckRadiusCm': base_r,
                       'farRadiusCm': top_r, 'lengthCm': length,
                       'axis': axis, 'center': center,
                       'localSectionCm2': local_section})
        placements.append({'feature': eq_name, 'why': why})

    if style == 'top-gate':
        area, (cx, cy) = _slice_area_and_centroid(grid, top_cells)
        neck_r = math.sqrt(max(1e-9, ratio * area) / math.pi)
        length = stock_top_z - top_z
        _channel(0, neck_r, neck_r + taper * length, length, 'z',
                 [round(cx, 4), round(cy, 4),
                  round((top_z + stock_top_z) / 2.0, 4)],
                 f'vertical gate at the cavity-top centroid; local '
                 f'section {area:.3f}cm² measured from the top '
                 f'slice ({len(top_cells)} cells)', area)
        gate_xy = (cx, cy)
    elif style == 'side-gate':
        k_mid = int(sum(c[2] for c in grid.inside) / len(grid.inside))
        mid_cells = _slice_cells(grid, k_mid)
        area, (cx, cy) = _slice_area_and_centroid(grid, mid_cells)
        mid_z = b[2][0] + (k_mid + 0.5) * grid.dz
        x_face = b[0][1] + margin
        length = x_face - cx
        neck_r = math.sqrt(max(1e-9, ratio * area) / math.pi)
        _channel(0, neck_r, neck_r + taper * length, length, 'x',
                 [round((cx + x_face) / 2.0, 4), round(cy, 4),
                  round(mid_z, 4)],
                 f'horizontal gate at mid-height into the slice '
                 f'centroid; local section {area:.3f}cm² '
                 f'({len(mid_cells)} cells)', area)
    elif style == 'bottom-gate-riser':
        k_bot = min(c[2] for c in grid.inside)
        bot_cells = _slice_cells(grid, k_bot)
        area, (cx, cy) = _slice_area_and_centroid(grid, bot_cells)
        bot_z = b[2][0] + (k_bot + 0.5) * grid.dz
        neck_r = math.sqrt(max(1e-9, ratio * area) / math.pi)
        sprue_x = b[0][1] + margin / 2.0
        length = stock_top_z - bot_z
        _channel(0, neck_r, neck_r + taper * length, length, 'z',
                 [round(sprue_x, 4), round(cy, 4),
                  round((bot_z + stock_top_z) / 2.0, 4)],
                 f'down-sprue in the mold wall (riser doubles as '
                 f'feed head); local section {area:.3f}cm² from the '
                 f'bottom slice', area)
        run_len = sprue_x - cx
        _channel(1, neck_r, neck_r, run_len, 'x',
                 [round((cx + sprue_x) / 2.0, 4), round(cy, 4),
                  round(bot_z, 4)],
                 'runner joining the down-sprue to the cavity floor '
                 '(fills from the bottom — less air entrainment)',
                 area)
    else:
        return {'ok': False,
                'error': f"gate style '{style}' not implemented"}

    # -- vents at the cavity's high regions (cast-2 connectivity) --
    vents, vent_rows = [], []
    n_vents = int(getattr(strat, 'n_vents', 0) or 0)
    vent_reason = ''
    if getattr(strat, 'vent_placement', 'high-points') == 'high-points':
        comps = _components_2d(grid, top_cells)
        open_comps = []
        for comp in comps:
            if gate_xy is not None:
                _, (ccx, ccy) = _slice_area_and_centroid(grid,
                                                         list(comp))
                if (abs(ccx - gate_xy[0]) < grid.dx * 2
                        and abs(ccy - gate_xy[1]) < grid.dy * 2):
                    continue        # the gate already owns this high
                    # region — a vent there is redundant
            open_comps.append(comp)
        if not open_comps:
            vent_reason = ('0 vents: the gate occupies the single '
                           'high region of the cavity — air escapes '
                           'through it')
        neck_ref = sprues[0]['neckRadiusCm'] if sprues else 0.3
        for vi, comp in enumerate(open_comps[:max(0, n_vents)]):
            _, (vx, vy) = _slice_area_and_centroid(grid, list(comp))
            vr = max(MIN_VENT_RADIUS_CM, neck_ref / 3.0)
            length = stock_top_z - top_z
            eq_name = f'{mold_name}--vent-{vi}-eq'
            solid_name = f'{mold_name}--vent-{vi}'
            v_center = [round(vx, 4), round(vy, 4),
                        round((top_z + stock_top_z) / 2.0, 4)]
            row, _q = build_quadric_eq_row(
                eq_name, f'{mold_name} vent {vi} (equation)',
                vr, vr, length, 'z', v_center,
                f'cast-4 vent at a cavity high region the gate does '
                f'not cover (air rises here — the trapped-pocket '
                f'site cast-5 would find)', vr * 3.0 + 0.5)
            vent_rows.append({f: getattr(row, f) for f in
                              ('name', 'display_name', 'family',
                               'primitive_kind', 'csg_json',
                               'parameters_json',
                               'quadric_matrix_json', 'bounds_json',
                               'notes', 'provenance_id')})
            vent_rows.append({
                'name': solid_name,
                'display_name': f'{mold_name} vent {vi}',
                'family': 'primitive', 'primitive_kind': 'cylinder',
                'quadric_matrix_json': '', 'csg_json': '',
                'bounds_json': '', 'provenance_id': 'cast-4',
                'notes': f'bounded solid of {eq_name}',
                'parameters_json': json.dumps({
                    'radius': round(vr, 5),
                    'height': round(length, 5), 'axis': 'z',
                    'center': v_center, 'cap_base': True,
                    'cap_top': True})})
            vents.append({'name': eq_name, 'solidName': solid_name,
                          'radiusCm': vr})
            placements.append({'feature': eq_name,
                               'why': f'high region {vi + 1} of '
                                      f'{len(open_comps)} uncovered '
                                      f'by the gate'})

    # -- both parity artifacts (composed from the BOUNDED solids) --
    channel_names = ([s['solidName'] for s in sprues]
                     + [v['solidName'] for v in vents])
    stock_name = getattr(mold, 'stock_shape_name', '')
    body_sprued = f'{mold_name}--body-sprued'
    rows_all = rows + vent_rows
    rows_all.append({
        'name': body_sprued,
        'display_name': f'{mold_name} mold body with channels',
        'family': 'csg', 'primitive_kind': '',
        'quadric_matrix_json': '',
        'csg_json': json.dumps({'op': 'difference',
                                'shapes': [stock_name, cavity]
                                + channel_names}),
        'parameters_json': '{}', 'bounds_json': '',
        'provenance_id': 'cast-4',
        'notes': 'DERIVED: mold body minus gate/vent channels — the '
                 'NEGATIVE-parity print artifact'})
    master_sprued = f'{mold_name}--master-sprued'
    rows_all.append({
        'name': master_sprued,
        'display_name': f'{mold_name} master with sprues attached',
        'family': 'csg', 'primitive_kind': '',
        'quadric_matrix_json': '',
        'csg_json': json.dumps({'op': 'union',
                                'shapes': [cavity] + channel_names}),
        'parameters_json': '{}', 'bounds_json': '',
        'provenance_id': 'cast-4',
        'notes': 'DERIVED: part plus sprue/vent solids — the '
                 'POSITIVE-parity print artifact (invested masters '
                 'carry their own wax sprues)'})

    # -- removability: worst-wins, evidence carried --
    limit = NECK_RATIO_LIMITS[part_brittleness]
    blockers, per_sprue = [], []
    worst = 1.0
    for s in sprues:
        r_ratio = (math.pi * s['neckRadiusCm'] ** 2
                   / s['localSectionCm2']) if s['localSectionCm2'] \
            else 1.0
        ok = r_ratio <= limit
        if not ok:
            blockers.append(
                f"sprue {s['name']}: neck ratio {r_ratio:.2f} "
                f'exceeds the {part_brittleness} limit {limit} — '
                f'removal would damage the part (lower '
                f'neck_area_ratio)')
        if mode == 'snap' and part_brittleness == 'ductile':
            blockers.append(
                f"sprue {s['name']}: snap removal on a DUCTILE part "
                f'tears instead of breaking — use cut')
        score = max(0.0, 1.0 - r_ratio / limit)
        worst = min(worst, score)
        per_sprue.append({'sprue': s['name'],
                          'neckRatio': round(r_ratio, 4),
                          'limit': limit, 'mode': mode,
                          'access': 'terminates at a stock face by '
                                    'construction',
                          'score': round(score, 4), 'ok': ok})
    removability = {'partBrittleness': part_brittleness,
                    'perSprue': per_sprue,
                    'worstWinsScore': round(worst, 4),
                    'limits': NECK_RATIO_LIMITS,
                    'limitsClaim': 'plan §4 named priors — '
                                   'confirmable knobs'}

    if not persist:
        return {'ok': True, 'dryRun': True,
                'rows': [r['name'] for r in rows_all]}
    converge = _converge_shape_rows(manager, rows_all)

    # the instance row (derived — reconverges on re-application)
    inst_name = f'{mold_name}--{strategy_name}'
    table = manager.objectTables.setdefault('SprueSetInstance', {})
    existing = None
    for r in table.values():
        if getattr(r, 'name', '') == inst_name:
            existing = r
            break
    inst_fields = {
        'name': inst_name, 'mold_ref': mold_name,
        'strategy_ref': strategy_name,
        'sprue_shape_names_json': json.dumps(
            [s['name'] for s in sprues]),
        'vent_shape_names_json': json.dumps(
            [v['name'] for v in vents]),
        'placements_json': json.dumps(placements),
        'removability_score': removability['worstWinsScore'],
        'removability_json': json.dumps(removability),
        'sprued_body_shape_name': body_sprued,
        'sprued_master_shape_name': master_sprued,
        'provenance_id': 'cast-4'}
    if existing is not None:
        for k, v in inst_fields.items():
            setattr(existing, k, v)
    else:
        made = None
        try:
            from casting.sprue_basis import SprueSetInstance
            made = SprueSetInstance(**inst_fields, manager=manager)
        except Exception:
            made = None
        if made is None or inst_name not in {
                getattr(r, 'name', None) for r in table.values()}:
            class _Row:
                pass
            r = _Row()
            for k, v in inst_fields.items():
                setattr(r, k, v)
            table[inst_name] = r

    result = {'ok': True, 'mold': mold_name,
              'strategy': strategy_name, 'style': style,
              'instance': inst_name,
              'sprues': sprues, 'vents': vents,
              'ventReason': vent_reason,
              'placements': placements,
              'spruedBodyShape': body_sprued,
              'spruedMasterShape': master_sprued,
              'removability': removability,
              'blockers': blockers,
              'verdict': 'blocked' if blockers else 'feasible',
              'inserted': converge['inserted'],
              'reconverged': converge['reconverged'],
              'gaps': ['vent diameter vs printable bead width — '
                       'checked when cast-5 binds print routes to '
                       'channels',
                       'runner/gate fluid sizing (fill rate, freeze '
                       'time in the channel) — cast-5',
                       'wall weakening around channel openings — '
                       'interacts with the pour-loading plate model '
                       '(gap str-wall-plate-model)'],
              'note': 'both parity artifacts emitted; cast-3 parity '
                      'decides which is printed. Local sections are '
                      'MEASURED grid slices, not guesses.'}
    return result
