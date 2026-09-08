"""
@module gears.custom.gear_kinematics

gr-1: THE ABSTRACT SOLVE (GEARS_PLAN §4a). Walk the train graph from
the input shaft outward; every mesh edge imposes a speed ratio and a
torque ratio, every shaft node carries ONE speed (which is exactly
what makes a compound stage multiply).

What this computes, per shaft:
  - angular speed WITH DIRECTION SIGN (external meshes reverse,
    internal ones do not — the classic silent bug, asserted in the
    selftests),
  - torque after the CUMULATIVE efficiency chain,
  - cumulative ratio from the input,
  - accumulated backlash (priors until measured runs land).

And per mesh: the efficiency actually used and whether it was a
PRIOR or a measured/overridden number; the derived centre distance;
power in / lost / out.

Honesty (stated on every payload, not just here):
  - QUASI-STATIC: no inertia, no acceleration, no resonance. These
    are steady-state ratios.
  - No gear ratio invents torque: power out = power in - losses, and
    the solve CHECKS that rather than asserting it.
  - Efficiency priors are literature bands; the midpoint is used
    when nothing measured exists and the payload says so.

@consumers gears.gear_api, gears.custom.gear_motor (gr-5),
           gears.gears_selftest
"""

import math

TWO_PI_OVER_60 = 2.0 * math.pi / 60.0

VALIDITY = ('QUASI-STATIC steady state: ratios, torques and '
            'efficiencies only. Inertia, angular acceleration, '
            'resonance, shock and backlash DYNAMICS are not '
            'modeled. Efficiency values are literature PRIORS '
            'unless a mesh states a measured override.')

#: Types whose chaining law the gr-1 solver implements. Anything
#: else REFUSES by name rather than guessing a ratio — planetary and
#: cycloidal need their own member/lobe algebra (gr-6).
CHAINABLE_TYPES = ('spur', 'helical', 'internal', 'bevel-straight',
                   'worm', 'rack-pinion')


def _sig(value, digits=12):
    """Round to SIGNIFICANT FIGURES, not decimal places.

    Fixed-decimal rounding is wrong for any payload that mixes
    scales, and a drivetrain mixes scales BY DEFINITION — that is
    what a ratio does. round(x, 9) quantized a clock's 1/60 rpm
    output shaft; round(x, 12) then quantized a 4e-6 Nm motor torque
    once the gr-5 splice multiplied it through. Both were the same
    bug wearing different decimals (and mag-3 hit it a third time on
    flux density). Significant-figure rounding keeps the payload
    tidy without eating the small end."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if v == 0.0 or v != v or v in (float('inf'), float('-inf')):
        return v
    exponent = math.floor(math.log10(abs(v)))
    return round(v, int(digits - 1 - exponent))


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _for_train(manager, class_name, train_name):
    return [r for r in _rows(manager, class_name)
            if getattr(r, 'train_ref', '') == train_name]


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _mesh_efficiency(manager, mesh, gtype):
    """(value, is_prior, note). A mesh override is taken as given
    (that is where a MEASURED number belongs); otherwise the type's
    literature band midpoint is used and FLAGGED, with both ends of
    the band carried so nobody has to trust the midpoint blindly."""
    override = getattr(mesh, 'efficiency_override', None)
    if override is not None:
        return (float(override), False,
                'stated on the mesh row (measured runs belong here)')
    lo = float(getattr(gtype, 'efficiency_prior_min', 0.9))
    hi = float(getattr(gtype, 'efficiency_prior_max', 0.99))
    return ((lo + hi) / 2.0, True,
            f'PRIOR: literature band {lo}-{hi} for '
            f'"{getattr(gtype, "name", "?")}", midpoint used — a '
            f'measured run replaces it')


def _pitch_radius_mm(gear):
    """Pitch diameter = module x teeth; radius is half of it."""
    return (float(getattr(gear, 'module_mm', 1.0))
            * float(getattr(gear, 'teeth', 1))) / 2.0


def _centre_distance_mm(mesh, driving, driven):
    override = getattr(mesh, 'center_distance_mm_override', None)
    if override is not None:
        return float(override), 'stated on the mesh row'
    r1 = _pitch_radius_mm(driving)
    r2 = _pitch_radius_mm(driven)
    if getattr(mesh, 'is_internal', False):
        # Internal mesh: the pinion sits INSIDE the ring, so the
        # centres are a DIFFERENCE apart, not a sum.
        return abs(r2 - r1), 'derived |r_ring - r_pinion| (internal)'
    return r1 + r2, 'derived r1 + r2 (external)'


def solve_train(manager, train_name, input_torque_nm=None,
                input_speed_rpm=None):
    """Solve one gear train. Returns per-shaft and per-mesh results
    plus a power-conservation check.

    `input_torque_nm` / `input_speed_rpm` override the train row —
    the gr-5 motor splice drives the train point-by-point along a
    motor's torque curve through exactly this door."""
    train = _named(manager, 'GearTrainDefinition', train_name)
    if train is None:
        return _refuse(f'no GearTrainDefinition named '
                       f'"{train_name}"')
    gears = _for_train(manager, 'GearDefinition', train_name)
    meshes = _for_train(manager, 'GearMeshDefinition', train_name)
    if not gears:
        return _refuse(f'train "{train_name}" has no GearDefinition '
                       f'rows',
                       {'knob': 'GearDefinition.train_ref',
                        'action': 'add the gear bodies first'})
    if not meshes:
        return _refuse(f'train "{train_name}" has no '
                       f'GearMeshDefinition rows — bodies without '
                       f'meshes are parts, not a drivetrain')
    by_name = {getattr(g, 'name', ''): g for g in gears}

    in_shaft = getattr(train, 'input_shaft', '')
    if not in_shaft:
        return _refuse(f'train "{train_name}" names no input shaft')
    torque = (float(input_torque_nm) if input_torque_nm is not None
              else float(getattr(train, 'input_torque_nm', 0.0)))
    speed = (float(input_speed_rpm) if input_speed_rpm is not None
             else float(getattr(train, 'input_speed_rpm', 0.0)))

    # Declared shafts are documentation; undeclared ones referenced
    # by a gear are SUGGESTIONS (the mag-3 flux-node rule).
    declared = {getattr(s, 'shaft', '')
                for s in _for_train(manager, 'ShaftNodeDefinition',
                                    train_name)}
    used = {getattr(g, 'shaft_ref', '') for g in gears}
    suggestions = [
        {'evidence': f'gear rows reference shaft "{s}" with no '
                     f'ShaftNodeDefinition row',
         'knob': 'ShaftNodeDefinition',
         'action': f'declare shaft "{s}" (or fix the typo)'}
        for s in sorted(used - declared) if s]

    # Walk outward from the input shaft. Each shaft holds ONE state;
    # bodies sharing a shaft therefore share its speed for free.
    state = {in_shaft: {'speedRpm': speed, 'torqueNm': torque,
                        'ratioFromInput': 1.0,
                        'backlashMm': 0.0,
                        'efficiencyFromInput': 1.0}}
    mesh_results = []
    remaining = list(meshes)
    progressed = True
    while remaining and progressed:
        progressed = False
        for mesh in list(remaining):
            driving = by_name.get(
                getattr(mesh, 'driving_gear_ref', ''))
            driven = by_name.get(
                getattr(mesh, 'driven_gear_ref', ''))
            if driving is None or driven is None:
                return _refuse(
                    f'mesh "{getattr(mesh, "name", "?")}" '
                    f'references a gear not in this train '
                    f'("{getattr(mesh, "driving_gear_ref", "")}" / '
                    f'"{getattr(mesh, "driven_gear_ref", "")}")')
            src = getattr(driving, 'shaft_ref', '')
            dst = getattr(driven, 'shaft_ref', '')
            if src not in state:
                continue                      # not reachable yet
            gtype = _named(manager, 'GearTypeDefinition',
                           getattr(driving, 'gear_type_ref', ''))
            if gtype is None:
                return _refuse(
                    f'gear "{getattr(driving, "name", "?")}" names '
                    f'unknown type '
                    f'"{getattr(driving, "gear_type_ref", "")}"',
                    {'knob': 'GearTypeDefinition',
                     'action': 'seed the type row first'})
            tname = getattr(gtype, 'name', '')
            if tname not in CHAINABLE_TYPES:
                return _refuse(
                    f'type "{tname}" is seeded but the gr-1 solver '
                    f'does not chain it — its ratio law needs its '
                    f'own algebra, and guessing one would be worse '
                    f'than refusing',
                    {'evidence': f'ratio law: '
                                 f'{getattr(gtype, "ratio_law", "")}',
                     'knob': 'GearTrainDefinition',
                     'action': 'use a chainable type, or land gr-6 '
                               '(planetary/cycloidal algebra)'})
            n1 = float(getattr(driving, 'teeth', 1)) or 1.0
            n2 = float(getattr(driven, 'teeth', 1)) or 1.0
            ratio = n2 / n1               # >1 = reduction
            eff, eff_is_prior, eff_note = _mesh_efficiency(
                manager, mesh, gtype)
            reverses = (bool(getattr(gtype, 'reverses_direction',
                                     True))
                        and not getattr(mesh, 'is_internal', False))
            sign = -1.0 if reverses else 1.0
            up = state[src]
            new_speed = up['speedRpm'] / ratio * sign
            new_torque = up['torqueNm'] * ratio * eff
            # Backlash accumulates as ANGLE, but at the output the
            # honest unit is arc length at the driven pitch radius —
            # each mesh contributes its two flanks' play.
            play = (float(getattr(driving, 'backlash_mm_prior', 0.0))
                    + float(getattr(driven, 'backlash_mm_prior',
                                    0.0)))
            new_backlash = up['backlashMm'] / ratio + play
            existing = state.get(dst)
            if existing is not None:
                # Two paths into one shaft: only consistent if they
                # agree (a differential does NOT, which is exactly
                # why v1 refuses instead of silently picking one).
                if abs(existing['speedRpm'] - new_speed) > 1e-9:
                    return _refuse(
                        f'shaft "{dst}" is driven by two paths that '
                        f'disagree ({existing["speedRpm"]} vs '
                        f'{new_speed} rpm) — a differential needs '
                        f'its own solve, so this refuses rather '
                        f'than picking one')
            else:
                state[dst] = {
                    'speedRpm': new_speed,
                    'torqueNm': new_torque,
                    'ratioFromInput': up['ratioFromInput'] * ratio,
                    'backlashMm': new_backlash,
                    'efficiencyFromInput': (up['efficiencyFromInput']
                                            * eff)}
            cd, cd_note = _centre_distance_mm(mesh, driving, driven)
            p_in = abs(up['torqueNm'] * up['speedRpm']
                       * TWO_PI_OVER_60)
            p_out = abs(new_torque * new_speed * TWO_PI_OVER_60)
            mesh_results.append({
                'mesh': getattr(mesh, 'name', ''),
                'type': tname,
                'drivingGear': getattr(driving, 'name', ''),
                'drivenGear': getattr(driven, 'name', ''),
                'fromShaft': src, 'toShaft': dst,
                'teeth': [int(n1), int(n2)],
                'stageRatio': _sig(ratio),
                'reversesDirection': reverses,
                'efficiency': _sig(eff),
                'efficiencyIsPrior': eff_is_prior,
                'efficiencyNote': eff_note,
                'centreDistanceMm': _sig(cd),
                'centreDistanceNote': cd_note,
                'powerInW': _sig(p_in),
                'powerOutW': _sig(p_out),
                'powerLostW': _sig(p_in - p_out),
                'producesThrust': bool(getattr(gtype,
                                               'produces_thrust',
                                               False)),
            })
            remaining.remove(mesh)
            progressed = True

    if remaining:
        orphans = [getattr(m, 'name', '') for m in remaining]
        return _refuse(
            f'meshes {orphans} are not reachable from input shaft '
            f'"{in_shaft}" — the train is disconnected (or the '
            f'input shaft is wrong)',
            {'knob': 'GearMeshDefinition.driving_gear_ref',
             'action': 'check the chain from the input outward'})

    out_shaft = getattr(train, 'output_shaft', '')
    if out_shaft and out_shaft not in state:
        return _refuse(
            f'output shaft "{out_shaft}" is never reached by any '
            f'mesh from the input')

    shafts = []
    for shaft, s in sorted(state.items()):
        shafts.append({
            'shaft': shaft,
            # 12 dp, not 9: a clock's minute shaft runs at 1/60 rpm
            # and 9-decimal rounding QUANTIZES it (0.016666667 is
            # not 1/60). Same class of bug as the mag-3 flux-density
            # rounding that quantized mT values — small quantities
            # in a mixed-scale payload need the precision, and a
            # reduction train is mixed-scale by definition.
            'speedRpm': _sig(s['speedRpm']),
            'direction': ('input' if shaft == in_shaft
                          else ('same-as-input' if s['speedRpm'] *
                                (speed or 1.0) >= 0 else 'reversed')),
            'torqueNm': _sig(s['torqueNm']),
            'ratioFromInput': _sig(s['ratioFromInput']),
            'efficiencyFromInput': _sig(
                s['efficiencyFromInput']),
            'backlashMm': _sig(s['backlashMm']),
            'isInput': shaft == in_shaft,
            'isOutput': shaft == out_shaft,
        })

    p_in_total = abs(torque * speed * TWO_PI_OVER_60)
    out_state = state.get(out_shaft) if out_shaft else None
    p_out_total = (abs(out_state['torqueNm']
                       * out_state['speedRpm'] * TWO_PI_OVER_60)
                   if out_state else 0.0)
    lost = sum(m['powerLostW'] for m in mesh_results)
    # Conservation over the DRIVEN PATH (branches would each carry
    # their own; v1 trains are chains, and a branch that disagreed
    # already refused above).
    conserved = (abs(p_in_total - p_out_total - lost) <=
                 max(1e-12, 1e-6 * max(p_in_total, 1e-12)))

    return {
        'ok': True,
        'train': train_name,
        'displayName': getattr(train, 'display_name', ''),
        'toleranceTier': getattr(train, 'tolerance_tier', 'T0'),
        'inputShaft': in_shaft, 'outputShaft': out_shaft,
        'inputTorqueNm': torque, 'inputSpeedRpm': speed,
        'shafts': shafts, 'meshes': mesh_results,
        'totalRatio': (_sig(out_state['ratioFromInput'])
                       if out_state else None),
        'totalEfficiency': (_sig(out_state['efficiencyFromInput'])
                            if out_state else None),
        'outputTorqueNm': (_sig(out_state['torqueNm'])
                           if out_state else None),
        'outputSpeedRpm': (_sig(out_state['speedRpm'])
                           if out_state else None),
        'outputBacklashMm': (_sig(out_state['backlashMm'])
                             if out_state else None),
        'power': {'inW': _sig(p_in_total),
                  'outW': _sig(p_out_total),
                  'lostW': _sig(lost),
                  'conserved': conserved,
                  'note': 'no gear ratio invents torque: the speed '
                          'given up and the efficiency lost are on '
                          'this line, not hidden behind the '
                          'output torque'},
        'suggestions': suggestions,
        'validity': VALIDITY,
    }


def train_catalog(manager):
    """Every train with its shape — the picker surface."""
    out = []
    for t in _rows(manager, 'GearTrainDefinition'):
        name = getattr(t, 'name', '')
        gears = _for_train(manager, 'GearDefinition', name)
        meshes = _for_train(manager, 'GearMeshDefinition', name)
        out.append({
            'name': name,
            'displayName': getattr(t, 'display_name', ''),
            'description': getattr(t, 'description', ''),
            'inputShaft': getattr(t, 'input_shaft', ''),
            'outputShaft': getattr(t, 'output_shaft', ''),
            'gearCount': len(gears), 'meshCount': len(meshes),
            'motorDesignRef': getattr(t, 'motor_design_ref', ''),
            'toleranceTier': getattr(t, 'tolerance_tier', 'T0'),
        })
    out.sort(key=lambda r: r['name'])
    return {'ok': True, 'trains': out, 'count': len(out)}


def type_catalog(manager):
    """The taxonomy, with the geometry gate visible: a type whose
    generator is empty can be SIMULATED but not yet drawn."""
    out = []
    for t in _rows(manager, 'GearTypeDefinition'):
        gen = getattr(t, 'geometry_generator', '')
        name = getattr(t, 'name', '')
        out.append({
            'name': name,
            'displayName': getattr(t, 'display_name', ''),
            'description': getattr(t, 'description', ''),
            'axisRelation': getattr(t, 'axis_relation', ''),
            'ratioLaw': getattr(t, 'ratio_law', ''),
            'efficiencyPrior': [
                getattr(t, 'efficiency_prior_min', None),
                getattr(t, 'efficiency_prior_max', None)],
            'reversesDirection': getattr(t, 'reverses_direction',
                                         True),
            'profileFamily': getattr(t, 'profile_family', ''),
            'producesThrust': getattr(t, 'produces_thrust', False),
            'canSelfLock': getattr(t, 'can_self_lock', False),
            'makeabilityNote': getattr(t, 'makeability_note', ''),
            'toleranceTierMin': getattr(t, 'tolerance_tier_min',
                                        'T0'),
            'chainable': name in CHAINABLE_TYPES,
            'geometryGenerator': gen or None,
            'geometryNote': (f'generator "{gen}"' if gen else
                             'NOT built yet (gr-3) — this type '
                             'simulates but does not draw'),
        })
    out.sort(key=lambda r: r['name'])
    return {'ok': True, 'types': out, 'count': len(out),
            'note': 'efficiency values are LITERATURE PRIOR BANDS '
                    '(both ends stated on purpose); measured runs '
                    'replace them per mesh'}
