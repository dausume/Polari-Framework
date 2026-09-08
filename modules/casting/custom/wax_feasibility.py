"""
@cross-cutting
@module casting.custom.wax_feasibility
@tags @xc:bindings

cast-1b (Dustin 2026-08-05): the wax master must be REAL, not just
algebra — before a mold is declared usable we check that

  1. the wax can hold up its own weight (self-support: column stress
     ρ·g·h at the base vs a compressive-strength floor, with the
     softening margin to the wax's melt point named),
  2. the wax mold is reasonably MAKABLE (a mold-ranked wax exists in
     waxsupply; the thinnest printed wall spans enough beads at the
     printer's nozzle), and
  3. if printed, HOW LONG it would take (kinematic deposition rate
     bead_width × layer_height × speed from a real waxprint
     PrintConditionDefinition/assembly, times a NAMED travel/retract
     overhead prior — no toolpath is simulated yet).

Verdict vocabulary follows motors.scale_goals_basis.goal_feasibility:
`blockers` decide, `gaps` are honest I-don't-knows with the
measurement named. Strength values are conservative literature FLOORS
carried as code priors (the MOLD_STRATEGY_PRIORS precedent) with
their claim status attached — a measured row replaces a prior, never
the other way round.

Parity note: in a 1-stage chain the wax IS the mold, so what gets
printed (and weighed, and timed) is the MOLD BODY. Deeper chains
print the positive instead — cast-3 picks the shape by parity; this
module times whatever shape it is handed.

Duck-typed manager, stdlib. @see /WAX_MOLD_NESTING_PLAN.md (cast-1)
"""

import json

from casting.custom.mold_geometry import _mold_named, derive_mold
from mathshapes.custom.shape_analysis import _named, shape_properties

_G = 9.80665

#: Conservative literature FLOORS for wax compressive strength at
#: room temperature, keyed by waxsupply source name. Claim status
#: travels with every use; a measured value should replace these
#: (knobs-and-suggestions: overridable per call via `overrides`).
WAX_STRUCTURAL_PRIORS = {
    'carnauba':      {'compressive_strength_mpa': 2.0,
                      'density_kg_m3': 990.0},
    'candelilla':    {'compressive_strength_mpa': 1.2,
                      'density_kg_m3': 980.0},
    'rice-bran-wax': {'compressive_strength_mpa': 1.0,
                      'density_kg_m3': 970.0},
    'sunflower-wax': {'compressive_strength_mpa': 1.0,
                      'density_kg_m3': 960.0},
    'beeswax':       {'compressive_strength_mpa': 0.5,
                      'density_kg_m3': 960.0},
}
_PRIOR_CLAIM = ('literature-approximate CONSERVATIVE FLOOR at room '
                'temperature — measure a real puck to replace')
#: Travel/retract/first-layer overhead on the kinematic print time —
#: a NAMED prior, not a toolpath simulation.
PRINT_OVERHEAD_FACTOR = 1.35
#: Softening margin: within this many °C of the melt point the
#: room-temperature strength floor is no longer credible.
SOFTENING_MARGIN_C = 15.0
#: A printed wall must span at least this many beads to be a wall.
MIN_BEADS_ACROSS_WALL = 2.0


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _row_named(manager, class_name, name):
    for r in _rows(manager, class_name):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _pick_wax(manager, wax_source_name):
    """The named wax, or waxsupply's own mold ranking's recommendation
    — never a silent default."""
    if wax_source_name:
        row = _row_named(manager, 'WaxSourceDefinition', wax_source_name)
        if row is None:
            return None, {'ok': False,
                          'error': f"no WaxSourceDefinition named "
                                   f"'{wax_source_name}'"}
        return row, None
    try:
        from waxsupply.custom.wax_analysis import wax_for_use
    except ImportError:
        return None, {'ok': False,
                      'error': 'waxsupply module unavailable — cannot '
                               'rank waxes for use mold; name a '
                               'wax_source_name explicitly'}
    ranked = wax_for_use(manager, 'mold')
    if not ranked.get('ok') or not ranked.get('recommended'):
        return None, {'ok': False,
                      'error': 'no wax source ranked for use '
                               "'mold' — seed waxsupply or name one"}
    row = _row_named(manager, 'WaxSourceDefinition',
                     ranked['recommended'])
    return row, None


def _density_for(manager, wax_name, prior):
    """Feedstock row density when one is bound to this wax source
    (real data wins), else the named prior."""
    for f in _rows(manager, 'WaxFeedstockDefinition'):
        if getattr(f, 'wax_source_ref', '') == wax_name:
            d = getattr(f, 'density_kg_m3', None)
            if d:
                return float(d), (f'WaxFeedstockDefinition '
                                  f"'{getattr(f, 'name', '')}'")
    return float(prior['density_kg_m3']), 'literature-approximate prior'


def wax_self_support(manager, mold_name, wax_source_name=None,
                     ambient_c=25.0, overrides=None):
    """Can the printed wax body hold its own weight? Column crush at
    the base (σ = ρ·g·h) against the strength floor, plus the melt
    margin. Creep, slender-feature bending and overhang support are
    NAMED unmodelled — this is the coarse gate, not the fine one."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    wax, err = _pick_wax(manager, wax_source_name)
    if err:
        return err
    wax_name = getattr(wax, 'name', '')
    prior = dict(WAX_STRUCTURAL_PRIORS.get(wax_name) or {})
    prior.update(overrides or {})
    melt_c = float(getattr(wax, 'melt_point_c', 0.0) or 0.0)
    findings, blockers = [], []
    # The melt gate FIRST: a wax that is liquid at ambient needs no
    # strength number to be refused — the master will not exist.
    if ambient_c >= melt_c - 5.0:
        blockers.append(
            f'ambient {ambient_c:.0f}°C is at/above {wax_name} melt '
            f'{melt_c:.0f}°C (−5°C guard) — the master will not exist')
        return {'ok': False, 'mold': mold_name, 'wax': wax_name,
                'meltPointC': melt_c, 'ambientC': ambient_c,
                'blockers': blockers, 'findings': findings}
    if not prior.get('compressive_strength_mpa'):
        return {'ok': False,
                'error': f"no strength prior for wax '{wax_name}' — "
                         f'absent data is absent; pass overrides='
                         f"{{'compressive_strength_mpa': ...}} or "
                         f'measure one',
                'knownPriors': sorted(WAX_STRUCTURAL_PRIORS)}
    if melt_c - ambient_c < SOFTENING_MARGIN_C:
        findings.append(
            f'only {melt_c - ambient_c:.0f}°C below {wax_name} melt — '
            f'the room-temperature strength floor is not credible '
            f'this close to softening')

    # printed height = the stock's z extent (the wax body IS the mold
    # body at chain depth 1 — see the parity note in the header).
    stock = _named(manager,
                   getattr(mold, 'stock_shape_name', '') or '')
    if stock is None:
        return {'ok': False,
                'error': f"mold '{mold_name}' has no derived stock — "
                         f'run derive_mold first'}
    try:
        size = json.loads(getattr(stock, 'parameters_json', '{}')
                          ).get('size') or []
        height_cm = float(size[2])
    except (TypeError, ValueError, IndexError):
        return {'ok': False,
                'error': 'derived stock has no readable z size'}

    density, density_source = _density_for(manager, wax_name, prior)
    sigma_kpa = density * _G * (height_cm / 100.0) / 1000.0
    strength_kpa = float(prior['compressive_strength_mpa']) * 1000.0
    utilization = sigma_kpa / strength_kpa if strength_kpa else 1.0
    if utilization >= 1.0:
        blockers.append(
            f'self-weight base stress {sigma_kpa:.1f} kPa exceeds the '
            f'{wax_name} strength floor {strength_kpa:.0f} kPa')
    return {'ok': not blockers, 'mold': mold_name, 'wax': wax_name,
            'heightCm': round(height_cm, 3),
            'densityKgM3': density, 'densitySource': density_source,
            'baseStressKpa': round(sigma_kpa, 4),
            'strengthFloorKpa': strength_kpa,
            'strengthClaim': _PRIOR_CLAIM,
            'utilization': round(utilization, 6),
            'meltPointC': melt_c, 'ambientC': ambient_c,
            'blockers': blockers, 'findings': findings,
            'unmodelled': ['creep (wax flows under sustained load)',
                           'slender-feature bending', 'overhang '
                           'support', 'strength drop vs temperature '
                           '(only the margin is checked)']}


def print_time_estimate(manager, shape_name, condition_name,
                        assembly_name='', overhead_factor=None):
    """Kinematic print time for a shape row: resolve its volume, then
    time it. Grid-derived molds (imported parts) have no body shape
    row — use print_time_for_volume with the grid's volume instead."""
    props = shape_properties(manager, shape_name)
    if not props.get('ok'):
        return props
    return print_time_for_volume(
        manager, float(props.get('volumeCm3') or 0.0), condition_name,
        assembly_name, overhead_factor, shape_label=shape_name)


def print_time_for_volume(manager, volume_cm3, condition_name,
                          assembly_name='', overhead_factor=None,
                          shape_label=''):
    """Kinematic print time for a known volume: volume ÷ (bead_width ×
    layer_height × speed), times the NAMED overhead prior. Nozzle
    comes from the condition when it declares one (>0), else the
    assembly — waxprint's own convention."""
    cond = _row_named(manager, 'PrintConditionDefinition',
                      condition_name)
    if cond is None:
        return {'ok': False,
                'error': f"no PrintConditionDefinition named "
                         f"'{condition_name}'"}
    nozzle = float(getattr(cond, 'nozzle_diameter_mm', 0.0) or 0.0)
    if nozzle <= 0.0 and assembly_name:
        asm = _row_named(manager, 'PrinterAssemblyDefinition',
                         assembly_name)
        if asm is not None:
            nozzle = float(getattr(asm, 'nozzle_diameter_mm', 0.0)
                           or 0.0)
    if nozzle <= 0.0:
        return {'ok': False,
                'error': f"condition '{condition_name}' declares no "
                         f'nozzle and no assembly supplied one'}
    speed = float(getattr(cond, 'print_speed_mm_s', 0.0) or 0.0)
    layer = float(getattr(cond, 'layer_height_mm', 0.0) or 0.0)
    if speed <= 0.0 or layer <= 0.0:
        return {'ok': False,
                'error': f"condition '{condition_name}' has no "
                         f'positive print_speed/layer_height'}
    volume_cm3 = float(volume_cm3 or 0.0)
    try:
        from waxprint.custom.voxel_resolution import bead_width_m
        bead_mm = bead_width_m(nozzle) * 1000.0
        bead_source = 'waxprint.custom.voxel_resolution.bead_width_m'
    except ImportError:
        bead_mm = nozzle * 1.1
        bead_source = ('waxprint unavailable — same 1.1× road model, '
                       'computed locally')
    overhead = (PRINT_OVERHEAD_FACTOR if overhead_factor is None
                else float(overhead_factor))
    rate_mm3_s = bead_mm * layer * speed
    rate_cm3_h = rate_mm3_s * 3600.0 / 1000.0
    hours = volume_cm3 / rate_cm3_h * overhead if rate_cm3_h else None
    return {'ok': True, 'shape': shape_label,
            'volumeCm3': round(volume_cm3, 2),
            'beadWidthMm': round(bead_mm, 4), 'beadSource': bead_source,
            'layerHeightMm': layer, 'printSpeedMmS': speed,
            'depositionRateCm3H': round(rate_cm3_h, 3),
            'overheadFactor': overhead,
            'overheadClaim': 'NAMED prior for travel/retract/first-'
                             'layer — no toolpath simulated',
            'estimatedHours': round(hours, 2) if hours else None}


def _body_volume(manager, mold):
    """The printable body's volume: the CSG body row when one exists,
    else the grid body volume from derivation_json (imported parts)."""
    body_shape = getattr(mold, 'body_shape_name', '')
    if body_shape:
        props = shape_properties(manager, body_shape)
        if props.get('ok'):
            return float(props.get('volumeCm3') or 0.0), body_shape
        return None, body_shape
    try:
        deriv = json.loads(getattr(mold, 'derivation_json', '{}')
                           or '{}')
    except (TypeError, ValueError):
        deriv = {}
    v = deriv.get('bodyVolumeCm3')
    return (float(v), '(grid body)') if v else (None, '')


def _routes_of(feed):
    try:
        routes = json.loads(getattr(feed, 'make_routes_json', '[]')
                            or '[]')
    except (TypeError, ValueError):
        routes = []
    return [r for r in routes if isinstance(r, str)]


def printable_criteria(feed, ambient_c=25.0):
    """The GENERAL 3D-printable criteria (Dustin 2026-08-05): does
    this feedstock qualify for a printer route at all? Each criterion
    reports pass/fail with its evidence — a failed list, not a silent
    drop."""
    routes = _routes_of(feed)
    print_routes = [r for r in routes
                    if r in ('auger-pellet-print', 'fdm-voron')]
    soften = float(getattr(feed, 'soften_temp_c', 0.0) or 0.0)
    checks = [
        {'criterion': 'has a printer make-route',
         'ok': bool(print_routes), 'evidence': routes or 'none'},
        {'criterion': 'positive print kinematics (nozzle/layer/speed)',
         'ok': all(float(getattr(feed, f, 0.0) or 0.0) > 0.0
                   for f in ('nozzle_diameter_mm', 'layer_height_mm',
                             'print_speed_mm_s')) or not print_routes,
         'evidence': {f: getattr(feed, f, None)
                      for f in ('nozzle_diameter_mm',
                                'layer_height_mm',
                                'print_speed_mm_s')}},
        {'criterion': f'holds shape at ambient (soften > '
                      f'{ambient_c:.0f}°C + 10)',
         'ok': soften > ambient_c + 10.0,
         'evidence': f'soften {soften:.0f}°C'},
        {'criterion': 'density + strength data present',
         'ok': float(getattr(feed, 'density_kg_m3', 0.0) or 0.0) > 0.0
         and float(getattr(feed, 'compressive_strength_mpa', 0.0)
                   or 0.0) > 0.0,
         'evidence': getattr(feed, 'claim_status', '')},
    ]
    return {'ok': all(c['ok'] for c in checks), 'checks': checks,
            'printRoutes': print_routes}


def _default_feedstock(manager):
    """The 'core' priority row — the natural locally-producible wax
    Dustin named as the focus. Never a silent commercial fallback."""
    core = [f for f in _rows(manager, 'MasterFeedstockDefinition')
            if getattr(f, 'priority', '') == 'core']
    return core[0] if core else None


def master_report(manager, mold_name, feedstock_name=None, route=None,
                  ambient_c=25.0, condition_name='room-baseline',
                  assembly_name='demo-auger-extruder'):
    """The generalized cast-1b gate: ANY MasterFeedstockDefinition
    (natural wax core, machinable wax, Voron wax filament, PLA) ×
    its make route. Blockers decide; gaps are named absences."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    if (not getattr(mold, 'body_shape_name', '')
            and not getattr(mold, 'derivation_json', '')):
        derived = derive_mold(manager, mold_name)
        if not derived.get('ok'):
            return {'ok': False, 'verdict': 'unassessed',
                    'error': f'derivation failed: '
                             f"{derived.get('error', '')}"}
    if feedstock_name:
        feed = _row_named(manager, 'MasterFeedstockDefinition',
                          feedstock_name)
        if feed is None:
            return {'ok': False,
                    'error': f'no MasterFeedstockDefinition named '
                             f"'{feedstock_name}'"}
    else:
        feed = _default_feedstock(manager)
        if feed is None:
            return {'ok': False,
                    'error': "no 'core' MasterFeedstockDefinition "
                             'seeded — name a feedstock explicitly'}
    feed_name = getattr(feed, 'name', '')
    routes = _routes_of(feed)
    if route is None:
        route = routes[0] if routes else ''
    blockers, gaps, findings = [], [], []
    if route not in routes:
        blockers.append(f"route '{route}' is not a make-route of "
                        f"'{feed_name}' (has: {routes})")

    # -- self-support + softening, straight off the feedstock row --
    density = float(getattr(feed, 'density_kg_m3', 0.0) or 0.0)
    strength_mpa = float(getattr(feed, 'compressive_strength_mpa',
                                 0.0) or 0.0)
    soften = float(getattr(feed, 'soften_temp_c', 0.0) or 0.0)
    if soften and ambient_c >= soften - 5.0:
        blockers.append(
            f'ambient {ambient_c:.0f}°C is at/above {feed_name} '
            f'softening {soften:.0f}°C (−5°C guard)')
    elif soften and soften - ambient_c < SOFTENING_MARGIN_C:
        findings.append(f'only {soften - ambient_c:.0f}°C below '
                        f'{feed_name} softening — strength floor not '
                        f'credible this close')
    support = None
    if density > 0.0 and strength_mpa > 0.0:
        stock = _named(manager,
                       getattr(mold, 'stock_shape_name', '') or '')
        try:
            size = json.loads(getattr(stock, 'parameters_json', '{}')
                              ).get('size') or []
            height_cm = float(size[2])
        except (AttributeError, TypeError, ValueError, IndexError):
            height_cm = 0.0
        if height_cm > 0.0:
            sigma_kpa = density * _G * (height_cm / 100.0) / 1000.0
            utilization = sigma_kpa / (strength_mpa * 1000.0)
            support = {'heightCm': round(height_cm, 3),
                       'baseStressKpa': round(sigma_kpa, 4),
                       'strengthFloorKpa': strength_mpa * 1000.0,
                       'claim': getattr(feed, 'claim_status', ''),
                       'utilization': round(utilization, 6)}
            if utilization >= 1.0:
                blockers.append(
                    f'self-weight {sigma_kpa:.1f} kPa exceeds the '
                    f'{feed_name} strength floor')
    else:
        blockers.append(f"'{feed_name}' carries no density/strength "
                        f'— absent data is absent')

    # -- criteria + timing per route --
    criteria = printable_criteria(feed, ambient_c=ambient_c)
    volume, body_label = _body_volume(manager, mold)
    timing = {'ok': False, 'error': 'no body volume'}
    wall_beads = None
    if volume is not None:
        if route == 'auger-pellet-print':
            timing = print_time_for_volume(
                manager, volume, condition_name, assembly_name,
                shape_label=body_label)
        elif route == 'fdm-voron':
            for c in criteria['checks']:
                if not c['ok']:
                    blockers.append(
                        f"general 3D-printable criterion failed: "
                        f"{c['criterion']} ({c['evidence']})")
            nozzle = float(getattr(feed, 'nozzle_diameter_mm', 0.0)
                           or 0.0)
            layer = float(getattr(feed, 'layer_height_mm', 0.0)
                          or 0.0)
            speed = float(getattr(feed, 'print_speed_mm_s', 0.0)
                          or 0.0)
            if nozzle > 0 and layer > 0 and speed > 0:
                bead_mm = nozzle * 1.1
                rate_cm3_h = bead_mm * layer * speed * 3.6
                timing = {'ok': True, 'shape': body_label,
                          'volumeCm3': round(volume, 2),
                          'beadWidthMm': round(bead_mm, 4),
                          'layerHeightMm': layer,
                          'printSpeedMmS': speed,
                          'depositionRateCm3H': round(rate_cm3_h, 3),
                          'overheadFactor': PRINT_OVERHEAD_FACTOR,
                          'overheadClaim': 'NAMED prior — no '
                                           'toolpath simulated',
                          'machine': 'standard Voron/cartesian FDM',
                          'estimatedHours': round(
                              volume / rate_cm3_h
                              * PRINT_OVERHEAD_FACTOR, 2)}
        elif route == 'cnc':
            timing = {'ok': False, 'gap': True,
                      'error': 'no CNC feeds/speeds model v1 — time '
                               'unassessed, not zero'}
            gaps.append('CNC machining time: no feeds/speeds model '
                        'v1 (named absence)')
            gaps.append('CNC wall/cutter-access check: no cutter '
                        'geometry data v1 (named absence)')
    # thinnest-wall bead check applies to print routes only.
    if timing.get('ok') and timing.get('beadWidthMm'):
        try:
            margin_mm = float(getattr(mold, 'stock_margin_cm', 0.0)
                              or 0.0) * 10.0
        except (TypeError, ValueError):
            margin_mm = 0.0
        if margin_mm > 0.0:
            wall_beads = margin_mm / timing['beadWidthMm']
            if wall_beads < MIN_BEADS_ACROSS_WALL:
                blockers.append(
                    f'thinnest mold wall {margin_mm:.1f}mm spans only '
                    f'{wall_beads:.1f} beads (need ≥ '
                    f'{MIN_BEADS_ACROSS_WALL:.0f})')

    gaps.append('printer/machine build envelope not checked — no '
                'envelope data (measure/declare one)')
    removal = {'route': getattr(feed, 'removal_route', ''),
               'tempC': getattr(feed, 'removal_temp_c', 0.0),
               'notes': getattr(feed, 'removal_notes', ''),
               'gate': 'checked against the mold material by the '
                       'cast-3 thermal gate, not here'}
    verdict = 'blocked' if blockers else 'feasible'
    return {'ok': True, 'mold': mold_name, 'verdict': verdict,
            'feedstock': feed_name,
            'materialKind': getattr(feed, 'material_kind', ''),
            'priority': getattr(feed, 'priority', ''),
            'renewable': bool(getattr(feed, 'renewable', False)),
            'route': route, 'routes': routes,
            'blockers': blockers, 'gaps': gaps, 'findings': findings,
            'printableCriteria': criteria, 'selfSupport': support,
            'printTime': timing, 'removal': removal,
            'wallBeads': round(wall_beads, 2) if wall_beads else None,
            'note': 'blockers decide; gaps are named absences. The '
                    'core focus stays the natural local wax — '
                    'commercial feedstocks are supported, reported '
                    'with their sourcing tier, never silently '
                    'promoted.'}


def wax_master_report(manager, mold_name, wax_source_name=None,
                      condition_name='room-baseline',
                      assembly_name='demo-auger-extruder',
                      ambient_c=None, overrides=None):
    """The cast-1b gate in one report: wax choice (waxsupply's own
    mold ranking unless named), self-support, thinnest-wall
    printability, and print time. Verdict vocabulary: blockers
    decide; gaps are the honest I-don't-knows."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    if (not getattr(mold, 'body_shape_name', '')
            and not getattr(mold, 'derivation_json', '')):
        derived = derive_mold(manager, mold_name)
        if not derived.get('ok'):
            return {'ok': False, 'verdict': 'unassessed',
                    'error': f'derivation failed: '
                             f"{derived.get('error', '')}"}
    cond = _row_named(manager, 'PrintConditionDefinition',
                      condition_name)
    if ambient_c is None:
        ambient_c = float(getattr(cond, 'ambient_temp_c', 25.0)
                          or 25.0) if cond is not None else 25.0

    support = wax_self_support(manager, mold_name, wax_source_name,
                               ambient_c=ambient_c,
                               overrides=overrides)
    if not support.get('ok') and 'error' in support:
        return support
    body_shape = getattr(mold, 'body_shape_name', '')
    if body_shape:
        timing = print_time_estimate(manager, body_shape,
                                     condition_name, assembly_name)
    else:
        # grid-derived (imported part): the body volume lives in
        # derivation_json — same timing, different volume source.
        try:
            deriv = json.loads(getattr(mold, 'derivation_json', '{}')
                               or '{}')
        except (TypeError, ValueError):
            deriv = {}
        body_vol = deriv.get('bodyVolumeCm3')
        if body_vol:
            timing = print_time_for_volume(
                manager, body_vol, condition_name, assembly_name,
                shape_label=f'{mold_name} (grid body)')
        else:
            timing = {'ok': False,
                      'error': 'no body shape row and no grid body '
                               'volume in derivation_json'}

    blockers = list(support.get('blockers', []))
    gaps = [f"strength floor is a {support.get('strengthClaim', '')}"]
    findings = list(support.get('findings', []))

    # Thinnest printed wall: the stock margin IS the mold body's wall
    # at its closest approach to the cavity.
    wall_beads = None
    try:
        margin_mm = float(getattr(mold, 'stock_margin_cm', 0.0)
                          or 0.0) * 10.0
    except (TypeError, ValueError):
        margin_mm = 0.0
    if timing.get('ok') and margin_mm > 0.0:
        wall_beads = margin_mm / timing['beadWidthMm']
        if wall_beads < MIN_BEADS_ACROSS_WALL:
            blockers.append(
                f'thinnest mold wall {margin_mm:.1f}mm spans only '
                f'{wall_beads:.1f} beads at bead width '
                f"{timing['beadWidthMm']:.2f}mm (need ≥ "
                f'{MIN_BEADS_ACROSS_WALL:.0f})')
    if not timing.get('ok'):
        gaps.append(f'print time unavailable: '
                    f"{timing.get('error', '')}")
    gaps.append('printer build envelope not checked — no build-volume '
                'data on PrinterAssemblyDefinition (measure/declare '
                'one)')
    gaps.append('CNC-wax route not assessed v1 — no machine envelope '
                'data')

    verdict = 'blocked' if blockers else 'feasible'
    return {'ok': True, 'mold': mold_name, 'verdict': verdict,
            'wax': support.get('wax'),
            'blockers': blockers, 'gaps': gaps, 'findings': findings,
            'selfSupport': support, 'printTime': timing,
            'wallBeads': round(wall_beads, 2) if wall_beads else None,
            'note': 'blockers decide; gaps are named absences. The '
                    'timed/weighed shape is the MOLD BODY (chain '
                    'depth 1: the wax is the mold) — cast-3 hands '
                    'deeper chains the positive instead.'}
