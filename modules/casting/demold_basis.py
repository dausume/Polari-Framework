"""
@cross-cutting
@module casting.demold_basis
@tags @xc:bindings

cast-7: getting the part OUT without damage. Three routes, all
computed:

  MECHANICAL   directional voxel sweeps. One-piece extraction along
               ±x/±y/±z needs every cavity column CLEAR to the stock
               boundary (a fully-enclosed cavity — the sphere —
               demolds NOWHERE in one piece, correctly). Failing
               that, a TWO-PART parting plane is searched along each
               axis: a half can pull away iff, in every column, its
               cavity cells form a contiguous run TOUCHING the
               parting plane (the voxel statement of "no undercut
               relative to the pull"). The sphere parts at its
               equator; the frustum pot caps at its top.
  MELT-OUT /   sacrificial exit, thermally gated: the master's
  BURN-OUT     removal temperature must sit BELOW the cast
               material's damage ceiling (the same _thermal_profile
               ladder the chain gate uses); burn-out carries the
               residue/ventilation notes from the feedstock row.
  BREAK-OUT    the disposable-mold route (Dustin: geopolymer is
               disposable) — always geometrically possible,
               reported with the crush-to-aggregate end-of-life.

Release requirement DERIVED, not remembered: like-on-like
geopolymer BONDS (the supplychain.custom.mold_analysis rule) — a
geopolymer pour into a geopolymer mold demands a release coat
(jojoba is waxsupply's named release), surfaced as a blocker until
a coating is declared.

Ejection damage v1: a BRITTLE part with undercut columns under
mechanical extraction is a break — blocked; adhesion coefficients
are a named absence.

@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-7)
"""

import json

from casting.custom.chain_analysis import _thermal_profile
from casting.fill_sim_basis import _sprue_instance_for
from casting.custom.mold_geometry import _mold_named
from casting.custom.voxel_grid import OccupancyGrid
from casting.custom.wax_feasibility import _row_named
from mathshapes.custom.shape_analysis import _named
from objectTreeDecorators import treeObject, treeObjectInit

DEMOLD_METHODS = ('mechanical', 'melt-out', 'burn-out', 'break-out')
_AXES = {'x': 0, 'y': 1, 'z': 2}


class DemoldPlanDefinition(treeObject):
    """A derived demold verdict for one mold — method, parting
    result, gates. Re-planning reconverges (derived-row rule)."""

    @treeObjectInit
    def __init__(self, name: str = '', mold_ref: str = '',
                 method: str = 'mechanical',
                 parting_json: str = '{}', gates_json: str = '[]',
                 release_coating_required: bool = False,
                 verdict: str = '', is_prior: bool = True,
                 notes: str = '', provenance_id: str = '',
                 manager=None):
        self.name = name
        self.mold_ref = mold_ref
        self.method = (method if method in DEMOLD_METHODS
                       else 'mechanical')
        self.parting_json = parting_json
        self.gates_json = gates_json
        self.release_coating_required = release_coating_required
        self.verdict = verdict
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id


def _column_key(cell, axis_i):
    return tuple(v for i, v in enumerate(cell) if i != axis_i)


def _one_piece_sweep(cavity, clear, axis, sign):
    """Columns whose cavity cells can slide to the boundary along
    (axis, sign) through clear cells. Returns (blocked, total)."""
    ai = _AXES[axis]
    n = cavity.n
    cols = {}
    for c in cavity.inside:
        cols.setdefault(_column_key(c, ai), []).append(c[ai])
    blocked = 0
    for key, ks in cols.items():
        edge = max(ks) if sign > 0 else min(ks)
        path = range(edge + 1, n) if sign > 0 else range(edge - 1,
                                                        -1, -1)
        ok = True
        for k in path:
            cell = list(key)
            cell.insert(ai, k)
            if tuple(cell) not in clear:
                ok = False
                break
        if not ok:
            blocked += 1
    return blocked, len(cols)


def _two_part_plane(cavity, axis):
    """Smallest-undercut parting plane along `axis`: at plane k_p the
    upper half pulls +axis iff every column's cavity cells in
    [k_p, n) are contiguous from k_p; mirrored below. Returns the
    first feasible k_p (searching from the cavity's widest slice
    outward) or None."""
    ai = _AXES[axis]
    ks = sorted({c[ai] for c in cavity.inside})
    if not ks:
        return None

    def _half_ok(k_p, upper):
        cols = {}
        for c in cavity.inside:
            if (c[ai] >= k_p) if upper else (c[ai] < k_p):
                cols.setdefault(_column_key(c, ai), []).append(c[ai])
        for key, kk in cols.items():
            kk = sorted(kk)
            contiguous = kk[-1] - kk[0] + 1 == len(kk)
            touches = (kk[0] == k_p) if upper else (kk[-1] == k_p - 1)
            if not (contiguous and touches):
                return False
        return True

    # widest slice first — the physically-natural parting line.
    by_width = sorted(ks, key=lambda k: -sum(
        1 for c in cavity.inside if c[ai] == k))
    for k in by_width:
        for k_p in (k, k + 1):
            if _half_ok(k_p, True) and _half_ok(k_p, False):
                return k_p
    return None


def demold_plan(manager, mold_name, method='mechanical',
                cast_material='geopolymer-slurry',
                part_brittleness='brittle', resolution=24,
                coating_declared=''):
    """Plan the extraction; verdict + gates, nothing assumed."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    if method not in DEMOLD_METHODS:
        return {'ok': False,
                'error': f"unknown method '{method}' — know: "
                         f'{DEMOLD_METHODS}'}
    cavity_shape = (getattr(mold, 'scaled_part_shape_name', '')
                    or getattr(mold, 'part_shape_ref', ''))
    stock = _named(manager, getattr(mold, 'stock_shape_name', ''))
    try:
        params = json.loads(getattr(stock, 'parameters_json', '{}'))
        size, center = params['size'], params['center']
        bounds = [[center[i] - size[i] / 2.0,
                   center[i] + size[i] / 2.0] for i in range(3)]
    except (AttributeError, KeyError, TypeError, ValueError):
        return {'ok': False, 'error': 'stock bounds unreadable'}
    cavity = OccupancyGrid.from_shape(manager, cavity_shape,
                                      resolution=resolution,
                                      bounds=bounds)
    if not isinstance(cavity, OccupancyGrid):
        return cavity
    clear = set(cavity.inside)
    inst = _sprue_instance_for(manager, mold_name)
    if inst is not None:
        dom_shape = getattr(inst, 'sprued_master_shape_name', '')
        dom = OccupancyGrid.from_shape(manager, dom_shape,
                                       resolution=resolution,
                                       bounds=bounds)
        if isinstance(dom, OccupancyGrid):
            clear = dom.inside

    blockers, findings, gaps, gates = [], [], [], []

    # -- mold material + release rule (derived, not remembered) --
    feed_ref = getattr(mold, 'mold_material_ref', '') or ''
    mold_material = feed_ref or 'carnauba-pellet'
    release_required = False
    if ('geopolymer' in cast_material
            and 'geopolymer' in mold_material):
        release_required = True
        if not coating_declared:
            blockers.append(
                'fresh geopolymer BONDS to cured geopolymer '
                '(mold_analysis rule) — a release coat is REQUIRED '
                'and none is declared; jojoba (waxsupply\'s named '
                'release) or a wax wash satisfies it (cast-8 makes '
                'coatings rows)')

    parting = {}
    if method == 'mechanical':
        one_piece = {}
        any_open = False
        for axis in _AXES:
            for sign, label in ((1, f'+{axis}'), (-1, f'-{axis}')):
                blocked, total = _one_piece_sweep(cavity, clear,
                                                 axis, sign)
                one_piece[label] = {'blockedColumns': blocked,
                                    'totalColumns': total}
                if blocked == 0 and total:
                    any_open = True
        parting['onePiece'] = one_piece
        if not any_open:
            planes = {}
            for axis in _AXES:
                k_p = _two_part_plane(cavity, axis)
                if k_p is not None:
                    coord = cavity.bounds[_AXES[axis]][0] \
                        + k_p * (cavity.dx, cavity.dy,
                                 cavity.dz)[_AXES[axis]]
                    planes[axis] = {'planeIndex': k_p,
                                    'planeCoordCm': round(coord, 3)}
            parting['twoPart'] = planes
            if planes:
                findings.append(
                    f'fully-enclosed cavity: one-piece extraction '
                    f'impossible in all 6 directions — a TWO-PART '
                    f'mold parts cleanly at '
                    f'{sorted(planes)} (plane coords in twoPart)')
            else:
                blockers.append(
                    'no single parting plane frees both halves — '
                    'undercuts interlock; use a sacrificial route '
                    '(melt-out / break-out) or redesign')
        if part_brittleness == 'brittle' and not any_open \
                and not parting.get('twoPart'):
            blockers.append('mechanical extraction of a BRITTLE '
                            'part against undercuts is a break')
        gaps.append('ejection adhesion coefficients unmeasured — '
                    'the sweep is geometric only (named absence)')
    elif method in ('melt-out', 'burn-out'):
        feed = _row_named(manager, 'MasterFeedstockDefinition',
                          mold_material)
        if feed is None:
            return {'ok': False,
                    'error': f"mold material '{mold_material}' is "
                             f'not a MasterFeedstockDefinition — '
                             f'{method} applies to sacrificial '
                             f'masters'}
        removal_t = float(getattr(feed, 'removal_temp_c', 0.0)
                          or 0.0)
        cast_ceiling = _thermal_profile(
            manager, 'geopolymer' if 'geopolymer' in cast_material
            else cast_material)
        if cast_ceiling is None:
            blockers.append(f"no thermal ceiling for the cast "
                            f"'{cast_material}' — cannot gate the "
                            f'{method}')
        else:
            ok = removal_t < cast_ceiling['ceilingC']
            gates.append({'gate': f'{method} at {removal_t:.0f}°C '
                                  f'vs the cast part ceiling '
                                  f"{cast_ceiling['ceilingC']:.0f}°C",
                          'ok': ok,
                          'evidence': cast_ceiling['basis']})
            if not ok:
                blockers.append(
                    f'{method} at {removal_t:.0f}°C would damage '
                    f'the part (ceiling '
                    f"{cast_ceiling['ceilingC']:.0f}°C) — the "
                    f'offending pair, named')
        notes = getattr(feed, 'removal_notes', '')
        if method == 'burn-out':
            findings.append(f'burn-out residue/ventilation: {notes} '
                            f'— vent the kiln')
        else:
            findings.append(f'melt-out: {notes}')
    elif method == 'break-out':
        findings.append(
            'disposable-mold route: geometrically unconditional; '
            'end-of-life = crush to aggregate (mold_analysis '
            'credit), the geopolymer loop Dustin approved')

    verdict = 'blocked' if blockers else 'feasible'
    plan_name = f'{mold_name}--demold-{method}'
    table = manager.objectTables.setdefault('DemoldPlanDefinition',
                                            {})
    fields = {'name': plan_name, 'mold_ref': mold_name,
              'method': method,
              'parting_json': json.dumps(parting),
              'gates_json': json.dumps(gates),
              'release_coating_required': release_required,
              'verdict': verdict, 'provenance_id': 'cast-7'}
    existing = next((r for r in table.values()
                     if getattr(r, 'name', '') == plan_name), None)
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        made = None
        try:
            made = DemoldPlanDefinition(**fields, manager=manager)
        except Exception:
            made = None
        if made is None or plan_name not in {
                getattr(r, 'name', None) for r in table.values()}:
            class _Row:
                pass
            r = _Row()
            for k, v in fields.items():
                setattr(r, k, v)
            table[plan_name] = r

    return {'ok': True, 'mold': mold_name, 'method': method,
            'plan': plan_name, 'parting': parting, 'gates': gates,
            'releaseCoatingRequired': release_required,
            'blockers': blockers, 'findings': findings, 'gaps': gaps,
            'verdict': verdict,
            'note': 'the sweep is the voxel statement of "no '
                    'undercut relative to the pull"; sacrificial '
                    'routes gate on the SAME thermal ladder the '
                    'chain uses.'}
