"""
@module motors.simple_first

mag-25: THE SIMPLEST CASE FIRST, with the road to the advanced ones.

Dustin 2026-07-31: "the point of the m0 exercise was actually to try
and solve for a simple magnetic engine that does not use complex
processes, so we should be aiming for an AWG that does not require
more complex processing... account for the road to advanced cases
while starting with the simplest case for learning and testing. We
want to maximize performance while staying at a level managable by
local means."

That is a correction and it is right. mag-22 optimised for POWER,
landed on 15000 turns of 46 AWG, and thereby dragged the whole
project into ultrafine drawing, diamond dies and an HPHT press —
none of which the M0 was ever for. Optimising the wrong objective
does not announce itself; it just quietly moves the requirements.

THE CONSTRAINT WAS ALWAYS THERE AND WE MISSED IT. Coil voltage
depends ONLY on the bare copper cross-section:
    V = MMF * rho * MTL / A_copper
Turns do not appear. So gauge alone decides whether the movement can
run off a cell — and at 46 AWG the answer is NO: it needs 4.14 V,
which means a step-up converter, with a quiescent draw that was
never in the power budget. A commercial quartz movement runs
directly off one cell precisely to avoid that.

So the fine-wire design was not merely harder to make. It was
carrying a hidden component.

WHAT DECIDES WHAT, stated once because it makes the whole trade
obvious:
    GAUGE  -> voltage (coarser wire = lower voltage = simpler drive)
    TURNS  -> battery life (charge per pulse is MMF*t/N)
    WINDOW -> turns, at a given gauge
Gauge and turns are therefore INDEPENDENT levers, and the only cost
of coarse wire is a bigger bobbin. On a wall clock, volume is the
cheapest thing we have.

@consumers motors.motor_api, motors.selftest_motors
"""

import math

PROV = 'mag-25'

RHO_CU = 1.724e-8
ENAMEL_MM = 0.025
FILL = 0.60

#: Bare copper diameters, mm.
AWG_MM = {24: 0.5106, 26: 0.4049, 28: 0.3211, 30: 0.2546,
          32: 0.2019, 34: 0.1601, 36: 0.1270, 38: 0.1007,
          40: 0.0799, 42: 0.0635, 44: 0.0503, 46: 0.0399}

#: What a cell actually delivers. The drive must fit inside this or
#: it needs a converter — which is a PART, with its own draw.
SUPPLY_OPTIONS = {
    'one-alkaline-cell': {'volts': 1.5, 'capacityMah': 2500,
                          'note': 'AA. What a commercial movement '
                                  'runs on, directly.'},
    'two-alkaline-cells': {'volts': 3.0, 'capacityMah': 2500,
                           'note': 'doubles the voltage headroom and '
                                   'the cost, not the capacity'},
    'coin-cell': {'volts': 3.0, 'capacityMah': 225,
                  'note': 'CR2032 — voltage is easy, capacity is not'},
}

#: Which drawing rung each gauge sits in (techtree.wire_ladder).
#: This is the whole point: the design must name the CAPABILITY it
#: assumes, not just the number.
def rung_for(awg):
    d = AWG_MM[awg]
    if d >= 0.5:
        return 'W1'
    if d >= 0.1:
        return 'W2'
    return 'W3'


RUNG_DIFFICULTY = {
    'W1': 'carbide dies, batch anneal — ordinary metalworking',
    'W2': 'carbide dies with careful bore finish — the honest edge '
          'of a home shop',
    'W3': 'diamond or fine-grit PCD dies, profiled bore — a serious '
          'project (see techtree.wire_ladder PCD_ROUTE)',
}


def coil_voltage(mmf, awg, mean_turn_mm=14.0):
    """V = MMF * rho * MTL / A_copper. Turns cancel — which is why
    gauge alone decides whether a cell can drive this."""
    a_cu = math.pi * (AWG_MM[awg] / 2000.0) ** 2
    return mmf * RHO_CU * (mean_turn_mm / 1000.0) / a_cu


def turns_in_window(awg, window_mm2, fill=FILL):
    a_wound = math.pi * ((AWG_MM[awg] + ENAMEL_MM) / 2.0) ** 2
    return fill * window_mm2 / a_wound


def design_at_gauge(mmf, awg, window_mm2, supply='one-alkaline-cell',
                    pulse_ms=30.0, rate_hz=1.0, mean_turn_mm=14.0):
    """One candidate movement, judged against a real cell."""
    sup = SUPPLY_OPTIONS.get(supply)
    if sup is None:
        return {'ok': False,
                'refusal': f'unknown supply "{supply}" — one of '
                           f'{sorted(SUPPLY_OPTIONS)}'}
    turns = turns_in_window(awg, window_mm2)
    if turns < 1:
        return {'ok': False,
                'refusal': f'a {window_mm2} mm2 window holds no '
                           f'complete turn of {awg} AWG'}
    volts = coil_voltage(mmf, awg, mean_turn_mm)
    amps = mmf / turns
    duty = (pulse_ms / 1000.0) * rate_hz
    avg_ma = amps * 1000.0 * duty
    fits = volts <= sup['volts']
    side = math.sqrt(window_mm2)
    return {
        'ok': True, 'awg': awg, 'rung': rung_for(awg),
        'rungDifficulty': RUNG_DIFFICULTY[rung_for(awg)],
        'windowMm2': round(window_mm2, 1),
        'windowSquareSideMm': round(side, 1),
        'turns': round(turns),
        'coilCurrentMa': round(amps * 1000.0, 4),
        'coilVoltageV': round(volts, 3),
        'supply': supply, 'supplyVoltsV': sup['volts'],
        'runsDirectlyOffSupply': fits,
        'needsConverter': not fits,
        'converterPenalty': (
            None if fits else
            'a step-up converter is a PART: extra cost, extra '
            'failure mode, and a quiescent current that is not in '
            'this budget and would eat into the battery life below'),
        'averageCurrentMa': round(avg_ma, 5),
        'timesThirstierThanWallClock': round(avg_ma / 0.015, 2),
        'aaYears': round(sup['capacityMah'] / avg_ma / 24 / 365, 2)
        if avg_ma else None,
    }


def manufacturable_ladder(manager=None, mmf=21.45,
                          supply='one-alkaline-cell',
                          target_years=4.0, max_window_mm2=900.0):
    """THE ROAD, as a ladder: what each DRAWING capability rung buys.

    For every gauge, grow the bobbin until the target battery life is
    met (or the size cap bites), then report what capability that
    design assumes. The simplest rung that clears the target is the
    one to build first — and the finer rungs are kept, because the
    question was how to reach the advanced cases, not how to avoid
    them.
    """
    rows = []
    for awg in sorted(AWG_MM):
        volts = coil_voltage(mmf, awg)
        # Turns needed for the target life, then the window to hold
        # them. Battery life is linear in turns.
        probe = design_at_gauge(mmf, awg, 100.0, supply=supply)
        if not probe.get('ok'):
            continue
        need = probe['turns'] * (target_years / probe['aaYears']) \
            if probe['aaYears'] else None
        a_wound = math.pi * ((AWG_MM[awg] + ENAMEL_MM) / 2.0) ** 2
        window = (need * a_wound / FILL) if need else None
        capped = bool(window and window > max_window_mm2)
        design = design_at_gauge(
            mmf, awg, min(window, max_window_mm2) if window else 100.0,
            supply=supply)
        design['windowCappedAt'] = max_window_mm2 if capped else None
        # A 1% tolerance, because the window is sized FROM the
        # target and then rounded — without it, 3.99 years reads as
        # a failure and 4.01 as a pass, which is a rounding artefact
        # masquerading as an engineering distinction.
        design['meetsTargetYears'] = bool(
            (design.get('aaYears') or 0) >= target_years * 0.99)
        design['coilVoltageV'] = round(volts, 3)
        rows.append(design)

    viable = [r for r in rows
              if r['runsDirectlyOffSupply'] and r['meetsTargetYears']]
    # SIMPLEST means easiest to MAKE: coarsest rung first, then
    # coarsest gauge within it. Stated explicitly because the
    # opposite sort gives the smallest coil, and which of those two
    # you call "best" is the whole argument of this module.
    order = {'W1': 0, 'W2': 1, 'W3': 2}
    viable.sort(key=lambda r: (order[r['rung']], -AWG_MM[r['awg']]))
    simplest = viable[0] if viable else None
    smallest = min(viable, key=lambda r: r['windowMm2']) \
        if viable else None
    finest = max(rows, key=lambda r: r['awg'])

    return {
        'ok': True, 'mmfATurns': mmf, 'supply': supply,
        'targetYears': target_years,
        'maxWindowMm2': max_window_mm2,
        'candidates': rows, 'viable': viable, 'simplest': simplest,
        'smallestViable': smallest,
        'selectionCriterion': (
            '"simplest" = easiest to MAKE (coarsest drawable gauge '
            'that still clears the target on one cell), NOT smallest. '
            'smallestViable is carried alongside so the trade is '
            'visible rather than decided silently.'),
        'finding': (
            f'the simplest movement that clears {target_years} years '
            f'on one cell is {simplest["awg"]} AWG at rung '
            f'{simplest["rung"]} — {simplest["turns"]} turns in a '
            f'{simplest["windowMm2"]} mm2 window (about '
            f'{simplest["windowSquareSideMm"]} mm square), drawing '
            f'{simplest["coilVoltageV"]} V, which one cell supplies '
            f'DIRECTLY. Capability needed: '
            f'{simplest["rungDifficulty"]}'
            if simplest else
            'no gauge clears the target within the window cap and '
            'the supply voltage — relax one of the three'),
        'theHiddenComponent': (
            f'{finest["awg"]} AWG — the gauge mag-22 chose — needs '
            f'{finest["coilVoltageV"]} V. A cell gives 1.5 V, so '
            f'that design silently assumed a STEP-UP CONVERTER with '
            f'a quiescent draw nobody costed. The fine-wire route '
            f'was not just harder to make, it was carrying an '
            f'uncounted part.'),
        'whyGaugeIsFree': (
            'coil voltage is MMF*rho*MTL/A_copper — TURNS CANCEL. So '
            'gauge sets the voltage and turns set the battery life, '
            'independently, and the only price of coarse wire is a '
            'bigger bobbin. On a wall clock, volume is the cheapest '
            'resource we have.'),
        'provenance': PROV,
    }


def road_to_advanced(manager=None, mmf=21.45):
    """What the harder rungs actually BUY, so the ladder is a road
    rather than a dismissal of everything above the first step."""
    ladder = manufacturable_ladder(manager, mmf=mmf)
    by_rung = {}
    for r in ladder['candidates']:
        by_rung.setdefault(r['rung'], []).append(r)
    stages = []
    for rung in ('W1', 'W2', 'W3'):
        here = by_rung.get(rung, [])
        if not here:
            continue
        best = min(here, key=lambda r: r['windowMm2'])
        stages.append({
            'rung': rung, 'capability': RUNG_DIFFICULTY[rung],
            'finestGauge': max(r['awg'] for r in here),
            'smallestWindowMm2': best['windowMm2'],
            'smallestSideMm': best['windowSquareSideMm'],
            'buys': (
                f'the same timekeeping in a '
                f'{best["windowSquareSideMm"]} mm square coil '
                f'instead of a larger one'),
            'directDrive': any(r['runsDirectlyOffSupply']
                               for r in here),
        })
    return {
        'ok': True, 'stages': stages,
        'whatFinerWireBuys': (
            'SIZE, and nothing else that matters here. Finer wire '
            'packs more turns into less window, so the movement '
            'shrinks. It does NOT buy battery life at equal turns, '
            'and past ~40 AWG it actively COSTS you the ability to '
            'run off a single cell.'),
        'theRealCeiling': (
            'there is a hard stop that has nothing to do with '
            'drawing skill: below ~40 AWG the coil needs more than '
            '1.5 V. Getting finer than that is not a capability '
            'upgrade for this product, it is a different product '
            'with a converter in it. The advanced rungs are worth '
            'building for OTHER consumers — sieve mesh, strain '
            'gauges, instrument coils — not for this clock.'),
        'learningOrder': [
            {'stage': 1, 'act': 'build the W2 movement and MEASURE it',
             'why': 'it runs off one cell, needs only carbide dies, '
                    'and every number we have is currently a '
                    'literature estimate. A measured coil resolves '
                    'the 4.6x reluctance-model disagreement '
                    '(mag-23) at the same time.'},
            {'stage': 2, 'act': 'shrink it by one gauge step',
             'why': 'proves the drawing capability incrementally, '
                    'against a working reference, where a failure '
                    'costs one coil rather than a project'},
            {'stage': 3, 'act': 'take W3 on for the OTHER consumers',
             'why': 'sieve mesh and strain gauges genuinely need it '
                    'and the clock does not — so W3 gets justified '
                    'by the tech tree, not by this movement'},
        ],
        'provenance': PROV,
    }
