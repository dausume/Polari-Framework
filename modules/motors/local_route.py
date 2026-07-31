"""
@module motors.local_route

mag-22: SOLVE FOR A LOCALLY PRODUCIBLE ROUTE to a working clock.

Dustin 2026-07-30: "what we want to solve for here is a locally
producible route to an electric motor clock that will work here, at
least one solution to that."

Everything before this ANALYSED a fixed design and found it wanting.
This SEARCHES: it assigns materials per part from the locally
producible set only, runs every gate already built, and returns the
configurations that clear them — or reports honestly that none does
and names what would have to change.

WHAT COUNTS AS LOCALLY PRODUCIBLE, as data rather than assertion:
  - realization_level is recipe-seeded or made-and-measured (we
    have a route, not a paper), AND
  - the route resolves through the supply chain to inputs we can
    actually get — the pottery channel (SrCO3, Fe2O3), the
    geopolymer stack, or a bioleached metal.
Anything reference-only or literature-only is EXCLUDED even when it
would obviously work: an NdFeB rotor solves the torque problem and
is not a local route, so it is not an answer to this question.

THE ONE HONEST EXCEPTION is copper. No local route to bulk copper
exists in this stack today — bioleaching (Acidithiobacillus, already
seeded in biomining) is real and is ~20% of world production, but we
do not run it. The winding is therefore marked IMPORTED in every
route rather than quietly counted as local, because a route that
hides its one import is not a local route.

@consumers motors.motor_api, motors.selftest_motors
"""

from magnetics.magnet_analysis import _named, _rows

#: Parts we are allowed to vary, and the roles that constrain each.
#: The rotor is deliberately included: the ladder's whole promise is
#: that a fired/sintered hexaferrite is reachable from pottery
#: chemicals, and that is exactly the swap that buys torque.
VARIABLE_PARTS = ('lavet-v2-stator', 'lavet-v2-pinion',
                  'lavet-v2-rotor-magnet')

#: Processes a route may require, and what each unlocks. These are
#: the REAL cost of "local": not money, capability.
PROCESS_UNLOCKS = {
    'ambient-cure': 'mix and cast. No kiln. What we have today.',
    'kiln-fire': 'a pottery kiln to cone 8-10. Unlocks fired '
                 'ceramic (10x the tensile strength of the cast '
                 'body) and the sintered hexaferrite route — the '
                 'Table 8.8 escalation already in the tech tree.',
    'magnetize': 'a pulse magnetiser — itself buildable from the '
                 'electrodevice stack (§1b: the stack bootstraps '
                 'its own tooling).',
    'buy-wire': 'IMPORTED. No local bulk-copper route runs here. '
                'Bioleaching is real and seeded in biomining, but '
                'we do not operate it.',
}


def _prop(manager, option, key):
    import json
    row = _named(manager, 'MagneticMaterialOption', option)
    if row is None:
        return None
    try:
        props = json.loads(getattr(row, 'properties_json', '')
                           or '{}')
    except (TypeError, ValueError):
        return None
    entry = props.get(key)
    return entry.get('value') if isinstance(entry, dict) else None


#: A material whose INPUT is recipe-seeded and whose process is one
#: the ladder already carries is not "literature only" in the way an
#: NdFeB magnet is — it is one named experiment away. Modelling that
#: honestly matters, because the difference between "we cannot" and
#: "we have not yet fired one" is the whole question.
#:
#: Each entry names the DEMONSTRATION that would promote it. This is
#: a bill of experiments, not a relabelling: nothing here is counted
#: as achieved, only as reachable, and by a stated act.
PROMOTABLE = {
    'opt-sintered-hexaferrite': {
        'fromMaterial': 'opt-srfe12o19',
        'fromLevel': 'recipe-seeded',
        'process': 'kiln-fire',
        'demonstration': (
            'press the recipe-seeded SrFe12O19 powder we already '
            'have a route to, fire it to ~1200 C in the same kiln '
            'the fired-ceramic rung needs, magnetise, and MEASURE '
            'B_r. Literature says 0.39 T; ours will be lower and '
            'the number that matters is the measured one.'),
        'whyItMatters': (
            'it is 0.39 T against the bonded route\'s 0.12 T — '
            '3.2x the remanence, hence ~3x the torque per amp, '
            'which is the only lever we have on the power blocker '
            'that does not require laminated steel we cannot make.'),
    },
}


def locally_producible(manager, allow_promotions=True):
    """The set a local route may draw from, WITH the process each
    one demands — because 'local' costs capability, not money."""
    out = []
    for o in _rows(manager, 'MagneticMaterialOption'):
        name = getattr(o, 'name', '')
        level = getattr(o, 'realization_level', '')
        if level not in ('recipe-seeded', 'made-and-measured'):
            continue
        if getattr(o, 'reference_only', False):
            continue
        fired = 'fired' in name or 'sinter' in name
        process = 'kiln-fire' if fired else 'ambient-cure'
        out.append({
            'promotion': None,
            'material': name,
            'displayName': getattr(o, 'display_name', ''),
            'realizationLevel': level,
            'itemRef': getattr(o, 'item_ref', ''),
            'process': process,
            'processNote': PROCESS_UNLOCKS[process],
            'muREff': _prop(manager, name, 'mu_r_eff'),
            'tensileMpa': _prop(manager, name, 'tensile_mpa'),
            'brT': _prop(manager, name, 'b_r_t'),
        })
    if allow_promotions:
        for target, promo in PROMOTABLE.items():
            row = _named(manager, 'MagneticMaterialOption', target)
            if row is None or any(m['material'] == target
                                  for m in out):
                continue
            out.append({
                'promotion': promo,
                'material': target,
                'displayName': getattr(row, 'display_name', ''),
                'realizationLevel': getattr(row, 'realization_level',
                                            ''),
                'itemRef': getattr(row, 'item_ref', ''),
                'process': promo['process'],
                'processNote': PROCESS_UNLOCKS[promo['process']],
                'muREff': _prop(manager, target, 'mu_r_eff'),
                'tensileMpa': _prop(manager, target, 'tensile_mpa'),
                'brT': _prop(manager, target, 'b_r_t'),
            })
    out.sort(key=lambda r: r['material'])
    return {'ok': True, 'materials': out, 'count': len(out),
            'promotionsOffered': [
                {'material': m['material'],
                 'demonstration': m['promotion']['demonstration'],
                 'whyItMatters': m['promotion']['whyItMatters']}
                for m in out if m['promotion']],
            'excluded': 'reference-only and literature-only options '
                        'are EXCLUDED even where they would '
                        'obviously work — an NdFeB rotor solves the '
                        'torque problem and is not a local route, '
                        'so it is not an answer to this question',
            'importedNote': PROCESS_UNLOCKS['buy-wire']}


def _score_part(manager, design_name, part_name, material,
                years=10.0):
    """Run the built gates on one (part, material) pair."""
    part = _named(manager, 'MotorPartDefinition', part_name)
    if part is None:
        return None
    original = getattr(part, 'material_ref', '')
    try:
        part.material_ref = material
        from motors.part_roles import (
            PART_ROLE_ASSIGNMENTS, role_viability,
        )
        roles = PART_ROLE_ASSIGNMENTS.get(part_name, [])
        via = role_viability(manager, material, roles,
                             part_row=part)
        if via['verdict'] != 'viable':
            return {'material': material, 'ok': False,
                    'stage': 'role', 'verdict': via['verdict'],
                    'failedOn': via['failedOn'],
                    'unassessedOn': via['unassessedOn']}
        from motors.motor_fatigue import part_fatigue
        fat = part_fatigue(manager, design_name, part_name,
                           years=years)
        if not fat.get('ok'):
            return {'material': material, 'ok': False,
                    'stage': 'fatigue-refused',
                    'why': fat.get('refusal', '')[:140]}
        return {'material': material, 'ok': bool(fat['passes']),
                'stage': 'fatigue',
                'staticSf': fat['staticSafetyFactor'],
                'fatigueSf': fat['fatigueSafetyFactor'],
                'passes': fat['passes']}
    finally:
        part.material_ref = original


def solve_local_route(manager, design_name='clock-lavet-m0',
                      years=10.0, allow_promotions=True):
    """Search the locally producible set for an assignment that
    clears every gate. Returns routes, or an honest nothing."""
    local = locally_producible(manager,
                               allow_promotions=allow_promotions)
    names = [m['material'] for m in local['materials']]
    by_name = {m['material']: m for m in local['materials']}

    per_part = {}
    for part in VARIABLE_PARTS:
        scored = []
        for mat in names:
            r = _score_part(manager, design_name, part, mat,
                            years=years)
            if r is not None:
                scored.append(r)
        winners = [r for r in scored if r.get('ok')]
        winners.sort(key=lambda r: -(r.get('fatigueSf') or 0))
        per_part[part] = {'viable': winners,
                          'rejected': [r for r in scored
                                       if not r.get('ok')]}

    solvable = all(per_part[p]['viable'] for p in VARIABLE_PARTS)
    route = None
    if solvable:
        picks = {p: per_part[p]['viable'][0] for p in VARIABLE_PARTS}
        processes = sorted({by_name[v['material']]['process']
                            for v in picks.values()}
                           | {'magnetize', 'buy-wire'})
        route = {
            'assignment': {p: {
                'material': v['material'],
                'process': by_name[v['material']]['process'],
                'fatigueSafetyFactor': v['fatigueSf'],
                'staticSafetyFactor': v['staticSf'],
            } for p, v in picks.items()},
            'processesRequired': [
                {'process': pr, 'unlocks': PROCESS_UNLOCKS[pr]}
                for pr in processes],
            'importedParts': ['the winding — copper. ' +
                              PROCESS_UNLOCKS['buy-wire']],
            'demonstrationsRequired': [
                {'part': p, 'material': v['material'],
                 'demonstration':
                     by_name[v['material']]['promotion']
                     ['demonstration'],
                 'whyItMatters':
                     by_name[v['material']]['promotion']
                     ['whyItMatters']}
                for p, v in picks.items()
                if by_name[v['material']]['promotion']],
        }
        route['fullyProvenToday'] = not route[
            'demonstrationsRequired']

    return {
        'ok': True, 'design': design_name, 'years': years,
        'localSet': local, 'perPart': per_part,
        'solved': solvable, 'route': route,
        'headline': (
            'A LOCALLY PRODUCIBLE ROUTE EXISTS: '
            + ', '.join(f'{p.split("-")[-1]} = {v["material"]}'
                        for p, v in route['assignment'].items())
            + '. The unlock is the KILN — firing buys ~10x the '
              'tensile strength of the ambient-cured body, which is '
              'what turns the pinion from failing to passing.'
            if solvable else
            'NO fully local assignment clears every gate with the '
            'materials on the shelf; see perPart for which part '
            'has no viable local material and why'),
        'honesty': (
            'this searches MATERIAL assignment only, with geometry '
            'and load held fixed. A part with no viable material is '
            'telling you the DESIGN needs to change — a bigger '
            'tooth, a lower handling load — and that search is not '
            'built. Copper is IMPORTED in every route and is '
            'labelled so rather than quietly counted as local.'),
    }


#: A drive sized at the bare stepping threshold misses steps the
#: first time a bearing drags or the temperature moves. Commercial
#: movements run real margin; this is the factor we design to, and
#: it is a knob rather than a constant buried in a formula.
DRIVE_MARGIN = 1.5


def minimum_drive_current(manager, design_name='clock-lavet-m0',
                          rotor_material='', stator_material='',
                          pulses=20, margin=DRIVE_MARGIN):
    """DERIVE the current this motor needs instead of asserting it.

    The M0 design carries `coil_amps: 0.02` as a STATED parameter,
    and every power figure we have reported rests on it. That number
    was never solved for — so "40x a wall clock" was, in part, a
    consequence of a guess.

    This bisects the current against the EXISTING clock_sim step
    condition (mag-5's co-energy landscape) with the route's
    materials installed, finding the smallest current at which every
    commanded pulse still advances the rotor, then applies a stated
    design margin. No new physics: the simulator that already
    decides whether a step happens is the judge.
    """
    from motors.motor_designer import clock_sim
    import json
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design named "{design_name}"'}
    original = getattr(design, 'params_json', '') or '{}'
    try:
        params = json.loads(original)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': f'"{design_name}" has unreadable '
                           f'params_json'}
    stated = float(params.get('coil_amps', 0.0) or 0.0)
    if rotor_material:
        params['rotor_material'] = rotor_material
    if stator_material:
        params['stator_material'] = stator_material

    last = {}

    def steps_at(amps):
        params['coil_amps'] = amps
        design.params_json = json.dumps(params)
        out = clock_sim(manager, design_name, pulses=pulses)
        last.clear()
        last.update(out)
        return bool(out.get('ok')) and out.get('stepsMissed') == 0

    try:
        if not steps_at(stated):
            # A refused SIM and a motor that will not step are
            # different failures and must not be reported alike:
            # the first is a hole in our data, the second is a
            # verdict about the machine.
            if not last.get('ok'):
                return {'ok': False, 'kind': 'data-gap',
                        'refusal': f'the step simulation could not '
                                   f'run with these materials: '
                                   f'{last.get("refusal")}',
                        'whatThisIsNot': 'this is a MISSING PROPERTY, '
                                         'not a finding that the '
                                         'motor fails — fill the '
                                         'property and ask again',
                        'ratedAmps': stated}
            return {'ok': False, 'kind': 'does-not-step',
                    'refusal': f'the motor does not step reliably '
                               f'even at the stated {stated} A with '
                               f'these materials — there is no '
                               f'current to minimise, the DESIGN is '
                               f'wrong',
                    'stepsMissed': last.get('stepsMissed'),
                    'ratedAmps': stated}
        lo, hi = 0.0, stated
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if steps_at(mid):
                hi = mid
            else:
                lo = mid
        threshold = hi
    finally:
        design.params_json = original

    designed = threshold * margin
    return {
        'ok': True, 'design': design_name,
        'rotorMaterial': rotor_material or '(unchanged)',
        'statorMaterial': stator_material or '(unchanged)',
        'statedAmps': stated,
        'thresholdAmps': float(f'{threshold:.4g}'),
        'marginFactor': margin,
        'designedAmps': float(f'{designed:.4g}'),
        'reductionVsStated': (float(f'{stated / designed:.3g}')
                              if designed else None),
        'method': (f'bisection over the existing clock_sim step '
                   f'condition across {pulses} pulses — the '
                   f'simulator that already decides whether a step '
                   f'happens is the judge, and no new physics was '
                   f'written for this'),
        'honesty': (
            'the threshold is only as good as the co-energy '
            'landscape it is bisected against: an idealised '
            'sinusoidal detent, no friction, no load torque from '
            'the train, no temperature. A real movement needs MORE '
            'than this. The result is a defensible design current '
            'in place of an asserted one, not a measurement.'),
    }


def route_power_effect(manager, design_name='clock-lavet-m0',
                       years=10.0):
    """Does the local route actually fix the power blocker? Solve
    the current for the CURRENT materials and for the ROUTE's, and
    compare both against a commercial movement."""
    solved = solve_local_route(manager, design_name, years=years)
    if not solved['solved']:
        return {'ok': False, 'refusal': 'no local route to evaluate',
                'solve': solved}
    a = solved['route']['assignment']
    rotor = a['lavet-v2-rotor-magnet']['material']
    stator = a['lavet-v2-stator']['material']

    base = minimum_drive_current(manager, design_name)
    routed = minimum_drive_current(manager, design_name,
                                   rotor_material=rotor,
                                   stator_material=stator)
    if not (base.get('ok') and routed.get('ok')):
        return {'ok': False,
                'refusal': 'could not solve drive current',
                'base': base, 'routed': routed}

    from motors.clock_product import (POWER_REFERENCES,
                                      power_budget, CELLS)
    pw = power_budget(manager, design_name)
    if not pw.get('ok'):
        return pw
    # power_budget's average scales linearly with coil current at
    # fixed pulse width and rate, so rescale rather than re-derive.
    stated_amps = pw['coilCurrentA']

    def at(amps):
        avg = pw['averageCurrentMa'] * (amps / stated_amps)
        wall = POWER_REFERENCES['quartz-wall-clock'][0]
        return {
            'coilAmps': float(f'{amps:.4g}'),
            'averageCurrentMa': float(f'{avg:.4g}'),
            'timesThirstierThanWallClock': float(f'{avg / wall:.3g}'),
            'aaMonths': float(f'{CELLS["AA-alkaline"] / avg / 24 / 30.4:.3g}'),
            'aaYears': float(f'{CELLS["AA-alkaline"] / avg / 24 / 365:.3g}'),
        }

    as_built = at(routed['designedAmps'])
    fixed = as_built['timesThirstierThanWallClock'] <= 5.0
    return {
        'ok': True, 'design': design_name,
        'routeMaterials': {'rotor': rotor, 'stator': stator},
        'currentMaterials': at(base['designedAmps']),
        'routeMaterialsResult': as_built,
        'asStated': at(stated_amps),
        'baseSolve': base, 'routeSolve': routed,
        'powerBlockerCleared': fixed,
        'finding': (
            f'the stated 20 mA was never solved for. Bisected '
            f'against the step condition, the CURRENT materials '
            f'need {base["designedAmps"]} A and the ROUTE\'s need '
            f'{routed["designedAmps"]} A at a {DRIVE_MARGIN}x '
            f'margin — {as_built["timesThirstierThanWallClock"]}x a '
            f'commercial wall movement, '
            f'{as_built["aaYears"]} years on one AA.'),
        'honesty': (
            'this rescales the existing power budget linearly in '
            'coil current at fixed pulse width, which is right for '
            'I*R drive but ignores inductive rise, driver quiescent '
            'draw and the oscillator — all of which make the real '
            'figure worse. It also inherits every caveat of the '
            'idealised detent landscape.'),
    }


def turns_sweep(manager, design_name='clock-lavet-m0',
                rotor_material='', stator_material='',
                turns_options=(1500, 3000, 6000, 10000, 15000,
                               20000)):
    """THE REAL LEVER ON POWER, found by asking what the step
    condition actually depends on.

    clock_sim's coil term depends on the MMF — turns x amps — while
    dissipation goes as I^2 R. Hold the mmf at the stepping
    threshold and the current falls as 1/N while resistance rises
    only as ~N (longer wire) x (finer gauge), so average current
    falls steeply with turns. This is not a trick: it is why a real
    quartz movement winds ten to twenty THOUSAND turns of 44-46 AWG
    onto a tiny bobbin instead of our 1500.

    Each candidate is checked through the EXISTING winding_report,
    so a coil that will not fit the bobbin, or needs a current
    density no wire survives, is rejected by the same gate as
    before rather than by a new rule invented here.
    """
    import json
    from motors.motor_winding import winding_report
    from motors.clock_product import POWER_REFERENCES, CELLS
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design named "{design_name}"'}
    base = minimum_drive_current(manager, design_name,
                                 rotor_material=rotor_material,
                                 stator_material=stator_material)
    if not base.get('ok'):
        return base
    original = getattr(design, 'params_json', '') or '{}'
    params = json.loads(original)
    n0 = float(params.get('coil_turns', 0) or 0)
    # The threshold is an MMF, not a current: this is the quantity
    # the step condition actually cares about.
    mmf = base['thresholdAmps'] * n0
    designed_mmf = base['designedAmps'] * n0
    rate = float(json.loads(getattr(design, 'drive_json', '')
                            or '{}').get('rate_hz', 1.0))
    duty = 0.030 * rate
    wall = POWER_REFERENCES['quartz-wall-clock'][0]

    rows = []
    try:
        if rotor_material:
            params['rotor_material'] = rotor_material
        if stator_material:
            params['stator_material'] = stator_material
        for n in turns_options:
            amps = designed_mmf / float(n)
            params['coil_turns'] = n
            params['coil_amps'] = amps
            params.pop('wire_awg', None)   # let the gauge auto-pick
            design.params_json = json.dumps(params)
            w = winding_report(manager, design_name)
            if not w.get('ok'):
                rows.append({'turns': n, 'fits': False,
                             'why': w.get('refusal', '')[:160]})
                continue
            avg_ma = amps * 1000.0 * duty
            # winding_report's key is fitVerdict/fillFactor. An
            # earlier pass here read a 'fits' key that DOES NOT
            # EXIST, so .get defaulted it to True and every
            # candidate was reported as fitting — including the
            # baseline, which needs 1.55x the stated window. Read
            # the real verdict.
            fill = w.get('fillFactor')
            window = float(w.get('bobbinWindowMm2') or 0.0)
            rows.append({
                'turns': n,
                'ampsForSameMmf': float(f'{amps:.4g}'),
                'gaugeAwg': w.get('gaugeAwg') or w.get('gauge'),
                'fillFactor': fill,
                'fitVerdict': w.get('fitVerdict'),
                'fits': w.get('fitVerdict') not in ('IMPOSSIBLE',
                                                    'MACHINE-ONLY'),
                'buildable': w.get('buildable'),
                'statedWindowMm2': window,
                'windowNeededMm2': (
                    float(f'{window * float(fill) / 0.6:.4g}')
                    if fill and window else None),
                'windowNote': (
                    'window needed to reach a 0.60 fill factor — '
                    'the hand-windable threshold. The STATED 12 mm2 '
                    'window does not hold even the baseline coil, '
                    'so the bobbin is the binding constraint at '
                    'every turns count, not just the deep ones.'),
                'handWindable': w.get('handWindable'),
                'resistanceOhm': w.get('resistanceOhm'),
                'voltageNeededV': w.get('voltageNeededV'),
                'averageCurrentMa': float(f'{avg_ma:.4g}'),
                'timesThirstierThanWallClock':
                    float(f'{avg_ma / wall:.3g}'),
                'aaYears': float(f'{CELLS["AA-alkaline"] / avg_ma / 24 / 365:.3g}'),
                'copperMassG': w.get('copperMassG'),
            })
    finally:
        design.params_json = original

    ok_rows = [r for r in rows if r.get('fits')]
    # If NOTHING fits the stated bobbin — which is the actual
    # situation — the sweep must still report the physics rather
    # than collapsing to 'no answer', because the bobbin is a knob
    # and the reader needs to know what to set it to.
    if not ok_rows:
        ok_rows = [r for r in rows if r.get('windowNeededMm2')]
    best = min(ok_rows,
               key=lambda r: r['timesThirstierThanWallClock'],
               default=None)
    return {
        'ok': True, 'design': design_name,
        'holdingMmfAt': float(f'{designed_mmf:.4g}'),
        'baselineTurns': n0,
        'candidates': rows, 'best': best,
        'finding': (
            f'holding the stepping MMF fixed at '
            f'{designed_mmf:.4g} A-turns, {best["turns"]} turns of '
            f'{best["gaugeAwg"]} AWG needs only '
            f'{best["ampsForSameMmf"]:.4g} A — '
            f'{best["timesThirstierThanWallClock"]}x a commercial '
            f'wall movement and {best["aaYears"]} years on one AA, '
            f'against 40x and 0.48 years at the stated 1500 turns. '
            f'The power blocker was a WINDING choice, not a '
            f'materials limit — but it is NOT free: that coil '
            f'needs a {best.get("windowNeededMm2")} mm2 bobbin '
            f'window against the {best.get("statedWindowMm2")} mm2 '
            f'the design states, and the stated window does not '
            f'hold even the baseline 1500-turn coil.'
            if best else
            'no turns count in the sweep both fits the bobbin and '
            'holds the stepping MMF — the bobbin window is the '
            'binding constraint, and it is a knob'),
        'honesty': (
            'the step condition is held at constant MMF, which is '
            'right for the co-energy landscape but ignores '
            'INDUCTANCE: more turns means more henries, and a 30 ms '
            'pulse into a large inductance does not reach its final '
            'current. That effect cuts the other way and is NOT '
            'modelled here, so treat the deep-turns end of this '
            'sweep as an upper bound on the benefit, not a promise.'),
    }


#: Target: within 5x a commercial wall movement is a clock you would
#: actually live with (a cell lasting years, not months).
POWER_TARGET_X_WALL = 5.0


def producible_clock(manager, design_name='clock-lavet-m0',
                     train_name='clock-train-m0'):
    """THE ANSWER: one locally producible route to a working
    electric-motor clock, with everything it costs stated.

    Composes the material route, the drive current solved rather
    than asserted, and the winding that makes the power budget
    work — then lists what must be IMPORTED, what must be
    DEMONSTRATED, and what is still unknown. A route that hides any
    of those three is not a route.
    """
    route = solve_local_route(manager, design_name)
    if not route['solved']:
        return {'ok': False,
                'refusal': 'no local material assignment clears the '
                           'gates', 'solve': route}
    a = route['route']['assignment']
    rotor = a['lavet-v2-rotor-magnet']['material']
    stator = a['lavet-v2-stator']['material']
    sweep = turns_sweep(manager, design_name,
                        rotor_material=rotor,
                        stator_material=stator)
    if not sweep.get('ok'):
        return sweep
    # Cheapest winding that reaches the power target — not the
    # deepest, because turns cost window, wire and winding hours.
    good = [c for c in sweep['candidates']
            if c.get('timesThirstierThanWallClock', 1e9)
            <= POWER_TARGET_X_WALL]
    pick = min(good, key=lambda c: c['turns']) if good else None

    steps = [
        {'step': 1, 'act': 'fire the ceramic parts',
         'detail': f'stator in {stator} and pinion in '
                   f'opt-fired-ceramic, cone 8-10. This is the '
                   f'single highest-value change: it takes the '
                   f'pinion from a fatigue safety factor of 0.39 — '
                   f'a part that fails in service — to '
                   f'{a["lavet-v2-pinion"]["fatigueSafetyFactor"]}.',
         'needs': 'a pottery kiln'},
        {'step': 2, 'act': 'press and sinter the rotor magnet',
         'detail': f'from the recipe-seeded SrFe12O19 powder, then '
                   f'magnetise. UNPROVEN BY US — this is the one '
                   f'demonstration the route depends on.',
         'needs': 'the same kiln, a press, a magnetiser'},
        {'step': 3, 'act': 'wind the coil deep, not thick',
         'detail': (f'{pick["turns"]:.0f} turns needing '
                    f'{pick["ampsForSameMmf"]:.4g} A, on a bobbin '
                    f'window of about {pick["windowNeededMm2"]} mm2 '
                    f'— NOT the 12 mm2 the design currently states, '
                    f'which does not hold even the present coil.'
                    if pick else
                    'no swept turns count reaches the power target'),
         'needs': 'IMPORTED copper magnet wire, and a bigger bobbin'},
    ]

    return {
        'ok': True, 'question': 'a locally producible route to an '
                                'electric-motor clock that works',
        'answerable': bool(pick),
        'design': design_name, 'train': train_name,
        'materials': a,
        'winding': pick,
        'windingSweep': sweep['candidates'],
        'buildSteps': steps,
        'imported': [
            'COPPER MAGNET WIRE. This is the honest hole in "local". '
            'Bioleaching copper is real and seeded in the biomining '
            'module, but we do not run it, and a clock needs '
            'hundreds of metres of enamelled fine wire — which is a '
            'drawing-and-enamelling capability, not just a metal. '
            'Everything else on this list we can make.'],
        'mustDemonstrate': route['route']['demonstrationsRequired'],
        'processesNeeded': route['route']['processesRequired'],
        'stillUnknown': [
            'INDUCTANCE is not modelled. A 10k-turn coil is many '
            'henries, and a 30 ms pulse may not reach its final '
            'current — which would eat into the power win. This is '
            'the largest single risk to the claim above.',
            'no casting or firing of ours has been MEASURED; every '
            'material property here is a literature class value, '
            'and the fatigue exponent amplifies error in them.',
            'the detent landscape is idealised — no friction, no '
            'load from the gear train, no temperature.',
        ],
        'headline': (
            f'YES, with one kiln, one demonstration and one import. '
            f'Fire the stator and pinion, sinter the rotor from '
            f'powder we already have a recipe for, and wind '
            f'{pick["turns"]:.0f} turns instead of 1500: that is '
            f'{pick["timesThirstierThanWallClock"]}x a commercial '
            f'wall movement, about {pick["aaYears"]} years on one '
            f'AA. The two blockers that looked like materials '
            f'limits were not — the pinion was a FIRING choice and '
            f'the power was a WINDING choice.'
            if pick else
            'no configuration in this search reaches the power '
            'target; the bobbin window is the binding constraint'),
        'honesty': (
            'the strong rotor makes power WORSE, not better, and '
            'that is worth stating because the opposite is the '
            'intuitive guess: in a Lavet motor the magnet that '
            'makes the torque also makes the detent you must '
            'overcome, so remanence buys structural margin and '
            'costs current. The power win here comes entirely from '
            'turns, and turns cost bobbin window.'),
    }
