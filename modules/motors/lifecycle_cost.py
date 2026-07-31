"""
@module motors.lifecycle_cost

mag-19: THE TRUE PRICE — cost per sensible lifespan unit.

Dustin 2026-07-30: "figure out which configuration is cheapest, not
based on instantaneous cost, but based off of the lifetime of the
product and cost per sensible lifespan unit. So first for a product
we need to determine the most sensible lifespan unit for it. Then
per one of those lifespan units we assess the cost ... upfront may
be more important on a low budget and in urgent times of use. But
lifetime usage is the 'true price' while the prior is only useful
for special cases."

Both numbers are computed and both are kept. They answer different
questions and neither replaces the other:

  UPFRONT      what it costs to have one at all. Decisive on a low
               budget, or when you need it now.
  PER-UNIT     what it costs to actually GET the service. The true
               price, and the one that reorders the options.

STEP ONE IS CHOOSING THE UNIT, and it is a real choice, not a
formality. A clock's product is TIME KEPT, so its unit is a
year-of-timekeeping — not hours of runtime (it never stops) and not
kilograms (it does not consume). A pump's unit is litres moved. A
mould's unit is casts. Pick the wrong denominator and every
comparison downstream is answering a question nobody asked, so the
unit is stated WITH ITS REASONING on every report.

STEP TWO IS LIFE, and this is where the work already done pays off.
The lifespan is not asserted: it comes from whichever failure mode
bites FIRST — fatigue (mag-16) or wear (mag-18) — and for brittle
parts the fatigue life INVERTS the crack-growth law rather than
just passing or failing a threshold:
    allowable(N) = strength * N^(-1/n)   =>   N_fail = (S/s)^n
That exponent is unforgiving: a part at half its derated strength
survives 2^n cycles, and at 1.4x it survives a few hundred. Small
changes in margin move life by orders of magnitude, which is
exactly why 'it passed the static check' told us so little.

STEP THREE IS COST OVER A HORIZON: upfront, plus the replacements
the life implies, plus maintenance. A configuration that cannot
complete one unit has an INFINITE cost per unit, and the report says
so rather than printing a large number that invites comparison.

@consumers motors.motor_api, motors.selftest_motors
"""

import math

from magnetics.magnet_analysis import _named, _rows
from motors.motor_stress import _prop, failure_criterion

#: product kind -> (unit, why this unit, units per calendar year).
#: The reasoning is part of the data because picking the
#: denominator IS the modelling decision.
LIFESPAN_UNITS = {
    'timekeeper': (
        'year-of-timekeeping',
        'a clock produces TIME KEPT. Not runtime hours (it never '
        'stops, so hours are calendar time wearing a different '
        'name) and not mass (it consumes nothing). What a buyer '
        'actually purchases is years during which it tells the '
        'time.', 1.0),
    'rotating-machine': (
        'million-revolutions',
        'a motor produces SHAFT REVOLUTIONS; wear and fatigue both '
        'scale with them, so revolutions are the unit that makes '
        'two differently-driven machines comparable.', None),
    'gear-train': (
        'million-tooth-engagements',
        'a gear is consumed by MESH CYCLES, not by time — a train '
        'idle in a drawer ages very little.', None),
    'mould': (
        'cast',
        'a mould produces CASTS; the mold-1 fleet analysis already '
        'counts casts-at-retirement, so the unit is already the '
        'one the rows record.', None),
    'vessel': (
        'growing-season',
        'a planter produces SEASONS of growing; freeze-thaw and '
        'leaching both track seasons rather than hours.', None),
}


#: Beyond this, a crack-growth extrapolation stops being an
#: estimate. 1e12 cycles is ~32,000 years at 1 Hz — past it the
#: honest statement is "not fatigue-limited", not a bigger number.
EXTRAPOLATION_CAP_CYCLES = 1.0e12


def lifespan_unit_for(kind):
    entry = LIFESPAN_UNITS.get(kind)
    if entry is None:
        return {'ok': False,
                'refusal': f'no lifespan unit defined for kind '
                           f'"{kind}" — choosing the denominator is '
                           f'the modelling decision and this '
                           f'refuses to guess it',
                'suggestion': {'knob': 'LIFESPAN_UNITS',
                               'action': f'define the unit for '
                                         f'"{kind}" with its '
                                         f'reasoning'}}
    unit, why, per_year = entry
    return {'ok': True, 'kind': kind, 'unit': unit, 'why': why,
            'unitsPerYear': per_year}


def fatigue_life_cycles(manager, material, applied_mpa,
                        survival=0.99):
    """INVERT the fatigue law to get cycles-to-failure, instead of
    only passing/failing a fixed horizon."""
    crit = failure_criterion(manager, material)
    if not crit.get('ok'):
        return crit
    strength = crit.get('tensileMpa')
    if not strength or not applied_mpa:
        return {'ok': False,
                'refusal': 'need both a strength and an applied '
                           'stress to invert the fatigue law'}
    fclass, _ = _prop(manager, material, 'fatigue_class')
    if fclass == 'brittle-scg':
        n, _ = _prop(manager, material, 'scg_exponent_n')
        m, _ = _prop(manager, material, 'weibull_modulus')
        if not n:
            return {'ok': False,
                    'refusal': f'"{material}" has no '
                               f'scg_exponent_n'}
        # Weibull first: the strength a 99%-survival design may use.
        derated = float(strength)
        if m:
            derated *= (-math.log(survival)) ** (1.0 / float(m))
        ratio = derated / float(applied_mpa)
        if ratio <= 1.0:
            return {'ok': True, 'material': material,
                    'model': 'brittle-scg', 'cyclesToFailure': 0.0,
                    'ratio': ratio,
                    'why': f'the applied {applied_mpa} MPa already '
                           f'exceeds the Weibull-derated strength '
                           f'{round(derated, 3)} MPa — it does not '
                           f'have a fatigue life, it has an '
                           f'immediate-failure problem'}
        cycles = ratio ** float(n)
        # A crack-growth law extrapolated far beyond any data is
        # arithmetic, not knowledge: n=45 on a 6x margin predicts
        # 1e85 cycles, which is not a lifespan, it is a number. Cap
        # it and SAY the cap is what is being reported.
        extrapolated = cycles > EXTRAPOLATION_CAP_CYCLES
        if extrapolated:
            cycles = EXTRAPOLATION_CAP_CYCLES
        return {'ok': True, 'material': material,
                'model': 'brittle-scg', 'cyclesToFailure': cycles,
                'extrapolationCapped': extrapolated,
                'capNote': ('life exceeded the defensible '
                            'extrapolation range and is REPORTED AT '
                            'THE CAP — the honest reading is "not '
                            'fatigue-limited at this stress; some '
                            'other mode governs", not the raw '
                            'number'
                            if extrapolated else ''),
                'ratio': round(ratio, 4),
                'deratedStrengthMpa': round(derated, 4),
                'scgExponent': n, 'weibullModulus': m,
                'why': f'N_fail = (S/s)^n = {round(ratio, 3)}^{n}. '
                       f'The exponent is unforgiving: margin moves '
                       f'life by ORDERS, which is why a static pass '
                       f'says so little.'}
    if fclass == 'ductile-endurance-limit':
        ratio_e, _ = _prop(manager, material,
                           'endurance_limit_ratio')
        limit = float(strength) * float(ratio_e or 0.45)
        infinite = float(applied_mpa) <= limit
        return {'ok': True, 'material': material,
                'model': 'ductile-endurance-limit',
                'cyclesToFailure': (float('inf') if infinite
                                    else 1e7),
                'enduranceLimitMpa': round(limit, 3),
                'why': ('below the endurance limit: life is '
                        'effectively unlimited by fatigue, so '
                        'another mode (wear) will govern'
                        if infinite else
                        'above the endurance limit — finite life; '
                        '1e7 used as a coarse stand-in because no '
                        'S-N curve is on record')}
    # no endurance limit
    return {'ok': True, 'material': material,
            'model': 'ductile-no-endurance-limit',
            'cyclesToFailure': 1e8,
            'why': 'no endurance limit exists for this class, so a '
                   'high-cycle stand-in of 1e8 is used and is a '
                   'PRIOR, not a measurement'}


def cost_per_lifespan_unit(manager, design_name, part_name,
                           kind='timekeeper', horizon_years=10.0,
                           part_cost_usd=None,
                           maintenance_usd_per_year=0.0,
                           **stress_kw):
    """The true price: upfront AND cost per lifespan unit, with the
    governing failure mode named."""
    unit = lifespan_unit_for(kind)
    if not unit.get('ok'):
        return unit
    from motors.motor_stress import part_stress
    st = part_stress(manager, design_name, part_name, **stress_kw)
    if not st.get('ok'):
        return st
    material = st['material']
    applied = st['stress']['judgedPa'] / 1e6
    life = fatigue_life_cycles(manager, material, applied)
    if not life.get('ok'):
        return life

    # Cycles the product performs per lifespan unit.
    design = _named(manager, 'MotorDesignDefinition', design_name)
    import json
    try:
        drive = json.loads(getattr(design, 'drive_json', '') or '{}')
    except (TypeError, ValueError):
        drive = {}
    rate = float(drive.get('rate_hz', 1.0) or 1.0)
    cycles_per_unit = rate * 365.25 * 24 * 3600   # per year

    cycles = life['cyclesToFailure']
    units_per_part = (cycles / cycles_per_unit
                      if cycles_per_unit else 0.0)

    # Upfront: the part's own material cost if not supplied.
    if part_cost_usd is None:
        part_cost_usd = 0.01        # placeholder, flagged below
        cost_flagged = True
    else:
        cost_flagged = False

    if units_per_part <= 0:
        return {
            'ok': True, 'design': design_name, 'part': part_name,
            'material': material, 'lifespanUnit': unit,
            'upfrontUsd': part_cost_usd,
            'unitsPerPart': 0.0,
            'costPerUnitUsd': None,
            'governingMode': 'immediate failure',
            'verdict': (
                f'this configuration cannot complete even ONE '
                f'{unit["unit"]}: {life["why"]} There is no cost '
                f'per unit to quote — an infinite number is not a '
                f'price, it is a disqualification.'),
            'life': life, 'appliedMpa': round(applied, 5),
            'costFlagged': cost_flagged,
        }

    replacements = max(math.ceil(horizon_years / units_per_part) - 1,
                       0) if units_per_part < horizon_years else 0
    total = (part_cost_usd * (1 + replacements)
             + maintenance_usd_per_year * horizon_years)
    per_unit = total / horizon_years
    return {
        'ok': True, 'design': design_name, 'part': part_name,
        'material': material, 'lifespanUnit': unit,
        'appliedMpa': round(applied, 5), 'life': life,
        'cyclesPerUnit': cycles_per_unit,
        'unitsPerPart': (round(units_per_part, 4)
                         if units_per_part != float('inf')
                         else 'unlimited-by-fatigue'),
        'horizonYears': horizon_years,
        'replacementsOverHorizon': replacements,
        'upfrontUsd': round(part_cost_usd, 6),
        'maintenanceUsdPerYear': maintenance_usd_per_year,
        'totalOverHorizonUsd': round(total, 6),
        'costPerUnitUsd': round(per_unit, 6),
        'governingMode': ('fatigue' if units_per_part
                          != float('inf') else 'not fatigue'),
        'verdict': (
            f'{part_cost_usd:.4g} USD upfront; over {horizon_years:g} '
            f'{unit["unit"]}s it needs {replacements} replacement(s), '
            f'so the TRUE price is {per_unit:.4g} USD per '
            f'{unit["unit"]}'),
        'bothNumbersNote': (
            'UPFRONT decides on a low budget or in urgent use; '
            'PER-UNIT is the true price and is what reorders the '
            'options. Neither replaces the other, so both are kept.'),
        'costFlagged': cost_flagged,
        'honesty': (
            'the lifespan is derived from literature-est material '
            'properties and an idealised stress — every uncertainty '
            'in those is baked into this price, and the exponent in '
            'the crack-growth law AMPLIFIES them. Treat the '
            'ORDERING of configurations as the result, not the '
            'absolute number.'),
    }


def cheapest_configuration(manager, design_name, part_name,
                           kind='timekeeper', horizon_years=10.0,
                           costs_usd=None, **stress_kw):
    """Rank every ROLE-VIABLE material by TRUE price, and show the
    upfront ordering beside it so the two can be compared."""
    from motors.part_roles import screen_candidates
    screen = screen_candidates(manager, part_name)
    if not screen.get('ok'):
        return screen
    part = _named(manager, 'MotorPartDefinition', part_name)
    original = getattr(part, 'material_ref', '')
    costs = costs_usd or {}
    rows = []
    for name in screen['viable']:
        try:
            part.material_ref = name
            r = cost_per_lifespan_unit(
                manager, design_name, part_name, kind=kind,
                horizon_years=horizon_years,
                part_cost_usd=costs.get(name), **stress_kw)
        finally:
            part.material_ref = original
        if not r.get('ok'):
            continue
        rows.append({
            'material': name,
            'upfrontUsd': r['upfrontUsd'],
            'costPerUnitUsd': r['costPerUnitUsd'],
            'unitsPerPart': r['unitsPerPart'],
            'governingMode': r['governingMode'],
            'lifeIsCapped': bool(r.get('life', {})
                                 .get('extrapolationCapped')),
            'lifeIsPrior': r.get('life', {}).get('model')
            != 'brittle-scg',
            'completesOneUnit': r['costPerUnitUsd'] is not None,
        })
    priced = [r for r in rows if r['completesOneUnit']]
    by_true = sorted(priced, key=lambda r: r['costPerUnitUsd'])
    by_upfront = sorted(rows, key=lambda r: r['upfrontUsd'])
    return {
        'ok': True, 'part': part_name, 'lifespanUnit':
            lifespan_unit_for(kind), 'candidates': rows,
        'roleViableOnly': screen['viable'],
        'cheapestTruePrice': (by_true[0] if by_true else None),
        'cheapestUpfront': (by_upfront[0] if by_upfront else None),
        'ordersDisagree': bool(
            by_true and by_upfront
            and by_true[0]['material'] != by_upfront[0]['material']),
        'note': 'candidates are ROLE-SCREENED first (mag-17): a '
                'material that cannot do the job is not made a '
                'bargain by being cheap. When the two orderings '
                'DISAGREE, that disagreement is the finding — the '
                'cheap option is buying you less service.',
    }
