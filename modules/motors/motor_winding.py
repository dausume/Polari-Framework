"""
@module motors.motor_winding

mag-9: THE WINDING REALITY CHECK — the honesty gap under every
torque number we have published.

Until now `coil_turns` and `coil_amps` were ASSERTED. The designer
multiplies them into an MMF and reports a torque, and nothing ever
asked the three questions that decide whether those amps exist:

  1. DOES THE COPPER FIT?  turns x enamelled wire area vs the
     bobbin window. Above ~0.75 fill nobody hand-winds it; above
     1.0 it is geometrically impossible and the torque curve above
     it is fiction.
  2. WHAT VOLTAGE DOES IT NEED?  R = rho x length / area, and
     V = I x R. A coil that needs 400 V from a 12 V shield does not
     carry the current the report assumed.
  3. WHAT DOES IT DISSIPATE?  P = I^2 R, in a cast composite with
     no thermal model. We report the watts and the surface density
     and REFUSE to translate them into a temperature.

Everything derives from physics rather than a copied table: wire
area from the AWG bare diameter, resistance from copper resistivity
(1.724e-8 ohm*m, IACS annealed at 20 C — the value that reproduces
the published AWG ohms/metre to four figures), and the temperature
coefficient applied explicitly so a hot coil's higher resistance is
visible instead of assumed away.

THE COUPLING IS THE POINT: when a winding does not fit or cannot be
driven, this report says WHICH published number it invalidates, by
name. A design whose torque curve assumes unreachable current has
not been discovered to be wrong by anyone reading the torque curve.

@consumers motors.motor_api, motors.selftest_motors
"""

import json
import math

from magnetics.magnet_analysis import _named, _rows

#: Copper resistivity, IACS annealed, 20 C. Reproduces the standard
#: AWG ohms/metre table to four significant figures, which is the
#: check that this constant is the right one.
RHO_CU_20C = 1.724e-8
#: Copper temperature coefficient (per K). A 100 C coil carries
#: ~1.3x the resistance of a 20 C one — the difference between
#: "needs 9 V" and "needs 12 V", so it is never folded away.
ALPHA_CU = 0.00393

#: Bare conductor diameter (mm) by AWG. Everything else — area,
#: resistance per metre, mass per metre — is COMPUTED from this,
#: so there is one number per gauge to get wrong instead of four.
AWG_DIAMETER_MM = {
    18: 1.0237, 20: 0.8118, 22: 0.6438, 24: 0.5106, 26: 0.4049,
    28: 0.3211, 30: 0.2546, 32: 0.2019, 34: 0.1601, 36: 0.1270,
    # Fine gauges matter: a real quartz-clock coil is tens of
    # thousands of turns of 44-46 AWG, and without these the M0
    # rung has no gauge that can express it.
    38: 0.1007, 40: 0.0799, 42: 0.0635, 44: 0.0503, 46: 0.0399,
}

#: Enamel build adds to the wound diameter without adding copper.
#: Single-build grade-1 magnet wire, fine gauges: ~0.02-0.03 mm on
#: diameter. A knob, because grade-2 is roughly double.
ENAMEL_BUILD_MM = 0.025

#: Copper density (kg/m3) — turns wire length into mass, and mass
#: into COST through the mag-1 cited spools.
RHO_CU_MASS = 8960.0

#: Fill factor thresholds. Hand random-winding realistically
#: reaches 0.5-0.6; machine orthocyclic winding reaches ~0.9;
#: above 1.0 the copper does not fit the hole, full stop.
FILL_HAND_WINDABLE = 0.60
FILL_MACHINE_ONLY = 0.75

VALIDITY = (
    'DC/steady-state winding physics only: geometric fill, DC '
    'resistance at a stated temperature, ohmic voltage and I^2R '
    'dissipation. NOT modelled: back-EMF (a rotating machine needs '
    'MORE voltage than this at speed), inductive transients, skin/'
    'proximity effect, and TEMPERATURE ITSELF — we report watts and '
    'watts per cm2, never a predicted temperature, because no '
    'thermal model of a cast composite exists here.')


def _wire_props(awg, temp_c=20.0, enamel_mm=ENAMEL_BUILD_MM):
    """Everything about one gauge, computed from its diameter."""
    d_mm = AWG_DIAMETER_MM[awg]
    d_m = d_mm / 1000.0
    area_m2 = math.pi * (d_m / 2.0) ** 2
    r_per_m_20 = RHO_CU_20C / area_m2
    r_per_m = r_per_m_20 * (1.0 + ALPHA_CU * (temp_c - 20.0))
    d_wound_mm = d_mm + enamel_mm
    return {
        'awg': awg,
        'bareDiameterMm': round(d_mm, 4),
        'woundDiameterMm': round(d_wound_mm, 4),
        'copperAreaM2': area_m2,
        'woundAreaMm2': math.pi * (d_wound_mm / 2.0) ** 2,
        'ohmPerM20C': round(r_per_m_20, 6),
        'ohmPerM': round(r_per_m, 6),
        'kgPerM': area_m2 * RHO_CU_MASS,
    }


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except (TypeError, ValueError):
        return default


def _refuse(refusal, suggestion=None):
    out = {'ok': False, 'refusal': refusal}
    if suggestion:
        out['suggestion'] = suggestion
    return out


def _wire_cost_usd_per_kg(manager):
    """Cheapest CITED magnet wire (mag-1), so a winding costs real
    money rather than a guess. Returns (usd_per_kg, citation) or
    (None, None) — and a missing citation is reported, not faked."""
    best = None
    for c in _rows(manager, 'PriceCitation'):
        if getattr(c, 'item_ref', '') != 'magnet-wire-copper':
            continue
        if (getattr(c, 'currency', 'USD') or 'USD') != 'USD':
            continue          # the mag-1 currency guard, unchanged
        unit = (getattr(c, 'amount_unit', '') or '').lower()
        amount = float(getattr(c, 'amount', 0.0) or 0.0)
        price = float(getattr(c, 'price', 0.0) or 0.0)
        if amount <= 0 or price <= 0:
            continue
        if unit in ('lb', 'lbs'):
            kg = amount * 0.45359237
        elif unit == 'kg':
            kg = amount
        elif unit == 'oz':
            kg = amount * 0.0283495
        else:
            continue
        per_kg = price / kg
        if best is None or per_kg < best[0]:
            best = (per_kg, getattr(c, 'name', ''),
                    bool(getattr(c, 'is_estimate', False)))
    if best is None:
        return None, None
    return best[0], {'citation': best[1], 'isEstimate': best[2]}


def winding_report(manager, design_name, awg=None, temp_c=20.0,
                   supply_voltage_v=None, enamel_mm=None):
    """Can this design's coil actually be wound and driven?

    Geometry comes from the design's params_json where stated, and
    from EXPLICITLY FLAGGED defaults where not — a design seeded
    before mag-9 still gets an answer, with every assumed number
    labelled as assumed."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return _refuse(f'no MotorDesignDefinition named '
                       f'"{design_name}"')
    params = _loads(design, 'params_json', {})
    turns = float(params.get('coil_turns', 0) or 0)
    amps = float(params.get('coil_amps', 0) or 0)
    if turns <= 0:
        return _refuse(
            f'design "{design_name}" states no coil_turns — there '
            f'is no winding to check')

    assumed = []
    gauge = awg if awg is not None else params.get('wire_awg')
    if gauge is None:
        # Pick the FINEST gauge that still carries the stated
        # current at a hand-wound ~4 A/mm2 — finest first, because
        # the thinnest adequate wire is what fits a bobbin. (An
        # earlier pass iterated thickest-first and handed a clock
        # coil 18 AWG, which is lamp cord.)
        gauge = min(AWG_DIAMETER_MM)
        for g in sorted(AWG_DIAMETER_MM, reverse=True):
            area_mm2 = math.pi * (AWG_DIAMETER_MM[g] / 2.0) ** 2
            if amps <= 0 or amps / area_mm2 <= 4.0:
                gauge = g
                break
        assumed.append(
            f'wire gauge not stated on the design — assumed {gauge} '
            f'AWG (finest gauge holding the stated {amps} A at a '
            f'hand-wound 4 A/mm2 current density)')
    gauge = int(gauge)
    if gauge not in AWG_DIAMETER_MM:
        return _refuse(
            f'{gauge} AWG is not in the gauge table',
            {'knob': 'awg', 'action': f'use one of '
                                      f'{sorted(AWG_DIAMETER_MM)}'})
    # Insulation build is a PARAMETER, not a module constant. It was
    # only a default argument, which meant a caller exploring
    # alternative insulations (mag-24) could patch the module global
    # and change nothing — defaults bind at definition time, so every
    # candidate silently returned the commercial figure. Same family
    # of trap as a flipped seed default not reaching a live row.
    wire = _wire_props(gauge, temp_c=temp_c,
                       enamel_mm=(ENAMEL_BUILD_MM if enamel_mm is None
                                  else float(enamel_mm)))

    # --- bobbin window + mean turn length -----------------------
    window_mm2 = params.get('bobbin_window_mm2')
    #: Whether the geometry is the DESIGN's or OURS. It decides
    #: whether this report may condemn anything: our own crude
    #: stand-in must never invalidate somebody's published torque
    #: number — it can only say "state the bobbin and ask again".
    window_stated = window_mm2 is not None
    if window_mm2 is None:
        # Fall back to something the design DOES state: a coil
        # wrapped on a limb of the stated overlap area, one third
        # of its span deep. Crude, and labelled crude.
        area_m2 = float(params.get('overlap_area_m2', 0) or 0)
        if area_m2 > 0:
            side_mm = math.sqrt(area_m2) * 1000.0
            window_mm2 = side_mm * side_mm / 3.0
        else:
            tooth = float(params.get('tooth_area_m2', 0) or 0)
            side_mm = (math.sqrt(tooth) * 1000.0) if tooth else 6.0
            window_mm2 = side_mm * side_mm / 3.0
        assumed.append(
            f'bobbin window not stated — assumed {window_mm2:.1f} '
            f'mm2 from the design\'s pole/tooth area (a CRUDE '
            f'stand-in; measure the real bobbin and state it)')
    window_mm2 = float(window_mm2)

    mtl_mm = params.get('mean_turn_length_mm')
    if mtl_mm is None:
        side_mm = math.sqrt(max(window_mm2, 1.0) * 3.0)
        mtl_mm = 4.0 * side_mm
        assumed.append(
            f'mean turn length not stated — assumed {mtl_mm:.1f} '
            f'mm (perimeter of a square former of the assumed '
            f'window)')
    mtl_mm = float(mtl_mm)

    # --- the three questions ------------------------------------
    fill = (turns * wire['woundAreaMm2']) / window_mm2
    length_m = turns * mtl_mm / 1000.0
    resistance = length_m * wire['ohmPerM']
    voltage = amps * resistance
    power = amps * amps * resistance
    mass_kg = length_m * wire['kgPerM']

    if fill > 1.0 and not window_stated:
        # OUR assumption, not their geometry: report it as
        # unjudgeable and ask, rather than pronouncing a design
        # impossible on the strength of a stand-in number.
        fit = 'window-unknown'
        fit_note = (f'{turns:.0f} turns of {gauge} AWG would need '
                    f'{fill:.2f}x the ASSUMED window — but that '
                    f'window is our crude stand-in, not this '
                    f'design\'s bobbin, so this says nothing about '
                    f'the design. State bobbin_window_mm2 and ask '
                    f'again.')
    elif fill > 1.0:
        fit = 'IMPOSSIBLE'
        fit_note = (f'{turns:.0f} turns of {gauge} AWG need '
                    f'{fill:.2f}x the window area — the copper does '
                    f'not fit the hole')
    elif fill > FILL_MACHINE_ONLY:
        fit = 'machine-wound-only'
        fit_note = (f'fill {fill:.2f} exceeds {FILL_MACHINE_ONLY} — '
                    f'only orthocyclic machine winding reaches this; '
                    f'not hand-windable')
    elif fill > FILL_HAND_WINDABLE:
        fit = 'tight-hand-wind'
        fit_note = (f'fill {fill:.2f} is above the comfortable '
                    f'hand-wound {FILL_HAND_WINDABLE} — doable with '
                    f'care and a neat former')
    else:
        fit = 'hand-windable'
        fit_note = f'fill {fill:.2f} — comfortable to hand-wind'

    supply = supply_voltage_v
    supply_source = 'caller-supplied'
    if supply is None:
        profiles = _rows(manager, 'MotorControllerProfile')
        if profiles:
            supply = float(getattr(profiles[0],
                                   'supply_voltage_v', 12.0))
            supply_source = (f'MotorControllerProfile '
                             f'"{getattr(profiles[0], "name", "")}"')
    drive_ok = None
    drive_note = ('no supply voltage available — state one, or seed '
                  'a MotorControllerProfile (mag-6)')
    if supply:
        drive_ok = voltage <= float(supply)
        headroom = float(supply) - voltage
        drive_note = (
            f'needs {voltage:.2f} V to push {amps} A through '
            f'{resistance:.2f} ohm; supply {supply} V '
            + (f'leaves {headroom:.2f} V headroom (before back-EMF, '
               f'which is NOT modelled and only grows with speed)'
               if drive_ok else
               f'is SHORT by {-headroom:.2f} V — the design does '
               f'NOT carry its stated current, so its torque '
               f'numbers are unreachable as specified'))

    # What this invalidates, said by name rather than left to the
    # reader to infer.
    invalidates = []
    if fit == 'IMPOSSIBLE' or drive_ok is False:
        # Only a STATED bobbin (or a real supply shortfall) may
        # condemn a published number — see window_stated above.
        target = ('clock-sim' if getattr(design, 'topology', '')
                  == 'lavet-clock-stepper' else 'torque curve')
        invalidates.append(
            f'the {target} for "{design_name}" assumes {amps} A '
            f'through {turns:.0f} turns; this winding cannot '
            f'deliver that, so those numbers are UNREACHABLE as '
            f'specified — change the gauge, the turns, the bobbin '
            f'or the supply, then re-read them')

    usd_per_kg, cite = _wire_cost_usd_per_kg(manager)
    cost = None
    if usd_per_kg:
        cost = {'usdPerKg': round(usd_per_kg, 4),
                'wireMassKg': round(mass_kg, 6),
                'wireCostUsd': round(mass_kg * usd_per_kg, 4),
                'citation': cite['citation'],
                'isEstimate': cite['isEstimate'],
                'note': 'cheapest CITED magnet wire (mag-1); gauge '
                        'is not matched to the citation — spools '
                        'are priced by mass, and thicker gauges '
                        'cost less per kg'}

    return {
        'ok': True, 'design': design_name,
        'ladderRung': getattr(design, 'ladder_rung', ''),
        'enamelBuildMm': (ENAMEL_BUILD_MM if enamel_mm is None
                          else float(enamel_mm)),
        'turns': turns, 'amps': amps,
        'mmfAt': round(turns * amps, 4),
        'wire': wire, 'temperatureC': temp_c,
        'bobbinWindowMm2': round(window_mm2, 3),
        'meanTurnLengthMm': round(mtl_mm, 3),
        'wireLengthM': round(length_m, 4),
        'fillFactor': round(fill, 4),
        'fitVerdict': fit, 'fitNote': fit_note,
        'resistanceOhm': round(resistance, 4),
        'voltageNeededV': round(voltage, 4),
        'supplyVoltageV': supply, 'supplySource': supply_source,
        'driveAchievable': drive_ok, 'driveNote': drive_note,
        'powerDissipatedW': round(power, 5),
        'powerPerCm2W': round(
            power / max(window_mm2 / 100.0, 1e-9), 4),
        'thermalNote': 'watts and watts/cm2 ONLY — no temperature '
                       'is predicted, because no thermal model of a '
                       'cast composite exists here. Compare against '
                       'the wire\'s enamel class (155 C for the '
                       'mag-1 cited spool) by measurement, not by '
                       'this report.',
        'cost': cost,
        'assumptions': assumed,
        'invalidates': invalidates,
        'windowStated': window_stated,
        'buildable': (fit not in ('IMPOSSIBLE', 'window-unknown')
                      and drive_ok is not False),
        'judgeable': window_stated,
        'validity': VALIDITY,
    }


def gauge_sweep(manager, design_name, temp_c=20.0,
                supply_voltage_v=None):
    """The same design across every gauge — the pick-your-wire
    table. Thicker wire means lower resistance and less voltage,
    but it stops fitting; the crossover is the design decision, and
    it is a table, not an opinion."""
    rows, best = [], None
    for g in sorted(AWG_DIAMETER_MM):
        rep = winding_report(manager, design_name, awg=g,
                             temp_c=temp_c,
                             supply_voltage_v=supply_voltage_v)
        if not rep.get('ok'):
            return rep
        entry = {
            'awg': g, 'fillFactor': rep['fillFactor'],
            'fitVerdict': rep['fitVerdict'],
            'resistanceOhm': rep['resistanceOhm'],
            'voltageNeededV': rep['voltageNeededV'],
            'powerDissipatedW': rep['powerDissipatedW'],
            'driveAchievable': rep['driveAchievable'],
            'buildable': rep['buildable'],
            'wireCostUsd': (rep['cost'] or {}).get('wireCostUsd'),
        }
        rows.append(entry)
        if entry['buildable'] and entry['fitVerdict'] in (
                'hand-windable', 'tight-hand-wind'):
            if best is None or (entry['voltageNeededV']
                                < best['voltageNeededV']):
                best = entry
    return {
        'ok': True, 'design': design_name, 'gauges': rows,
        'recommended': best,
        'recommendationBasis': (
            'thickest hand-windable gauge that still fits — lowest '
            'resistance, therefore least voltage and least heat, '
            'while staying buildable by hand'
            if best else
            'NONE buildable by hand at these turns/current: change '
            'the turns, the bobbin, or accept machine winding'),
        'note': 'a SUGGESTION over a full table, never an '
                'auto-applied choice — the design row keeps whatever '
                'a human puts in it',
        'validity': VALIDITY,
    }
