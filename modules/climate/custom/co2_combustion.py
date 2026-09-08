"""
@module climate.custom.co2_combustion

WHAT A WOOD FIRE DID TO INDOOR CO2 — computed three ways, because
one way was not enough to trust.

Dustin: "a wood fire does produce carbon dioxide however, that is
provably true. So let's assess how that would have likely
impacted carbon dioxide levels historically as well".

He is right, and the previous commit's reasoning was too quick. It
argued that a draughty dwelling ventilates fast enough to keep CO2
near outdoor - true as far as it goes, and asserted rather than
computed. A fire is a far larger CO2 source than the people around
it, and the arithmetic has to be done rather than waved at.

🔑 AND THE STRONGEST FORM OF HIS OBJECTION IS THE ONE THAT LANDS:
the measured PM2.5 in these dwellings PROVES combustion products
entered the room. Smoke in the room means CO2 in the room, because
they come out of the same fire. Citing the smoke as evidence the
past was worse, while claiming the CO2 stayed outside, was having
it both ways.

THREE ROUTES, and the disagreement between them is the result:

A. DIRECT BURN, from first principles. Dry wood is about half
   carbon; each carbon atom leaves as CO2 at 44/12 its mass. A
   0.5 kg/h fire in a 40 m3 room adds +2292 ppm at 5 ACH and
   +382 ppm at 30 ACH. So yes: unambiguously a large source,
   far larger than the occupants.

B. PM2.5 AS TRACER. Measured room PM2.5, divided by the smoke's
   PM/CO2 emission ratio, gives the CO2 that arrived WITH it.

C. CO AS TRACER. Measured room CO, times the modified combustion
   efficiency ratio, gives the same quantity a second way.

WHY B AND C BEAT A. The direct burn assumes every combustion
product enters the room, which depends entirely on the flue - and
the flue is the one thing nobody measured in a dwelling that no
longer exists. The tracers measure WHAT IS ACTUALLY IN THE ROOM,
so they sidestep the flue question completely. The gap between A
and the tracers IS the flue efficiency, and reporting that gap is
more honest than picking a draught coefficient.

⚠ AND THE TWO TRACERS DISAGREE, roughly fivefold. Against the Puno
24-hour medians the PM route gives about +5 to +22 ppm and the CO
route about +52 to +110 ppm. The measured CO:PM mass ratio in
those homes is near 51, where wood-smoke emission factors predict
4 to 15 - so either the instruments were not co-located, or PM
settled out, or CO had another source. That disagreement is not
smoothed over: it is the honest width of the answer.

@consumers climate.co2_settings_seed, climate.climate_views_seed,
climate.climate_api, climate.climate_selftest
"""

#: Dry wood is close to 50 percent carbon by mass - the standard
#: figure across fuel-chemistry references and stable across
#: species to within a few percent.
WOOD_CARBON_FRACTION = 0.50

#: Every carbon atom that burns completely leaves as CO2 at the
#: mass ratio of their molar masses.
CO2_PER_CARBON = 44.0 / 12.0

#: Fraction of fuel carbon reaching full CO2 in an open fire. The
#: rest leaves as CO, methane, soot and unburnt volatiles - which
#: is exactly why these fires are dangerous, and why a naive
#: complete-combustion figure OVERSTATES the CO2.
OPEN_FIRE_CO2_YIELD = 0.90

#: g CO2 per kg dry wood, allowing for incomplete combustion.
EF_CO2_G_PER_KG = 1500.0

#: g PM2.5 per kg fuel for traditional wood stoves and open fires.
#: A very wide range in the literature - a factor of four across
#: this band alone, which is most of the uncertainty in route B.
EF_PM25_G_PER_KG_LOW = 5.0
EF_PM25_G_PER_KG_HIGH = 20.0

#: Modified combustion efficiency, CO2 / (CO2 + CO) as moles.
#: Open cooking fires sit around 0.90-0.95; higher means cleaner.
MCE_LOW = 0.90
MCE_HIGH = 0.95

#: 1 ppm CO is about this many mg/m3 at 25 C and 101 kPa.
CO_MG_PER_M3_PER_PPM = 1.145
#: 1 ppm CO2 is about this many mg/m3 at the same conditions.
#: (Imported constant elsewhere; restated only in the comment to
#: avoid a second source of truth.)


def _co2_mg_per_m3_per_ppm():
    from aquaponics.custom.atmosphere_analysis import CO2_MG_PER_M3_PER_PPM
    return CO2_MG_PER_M3_PER_PPM


def wood_fire_co2_mg_per_day(kg_per_hour, hours_per_day=24.0,
                             carbon_fraction=WOOD_CARBON_FRACTION,
                             co2_yield=OPEN_FIRE_CO2_YIELD):
    """ROUTE A, the source term: how much CO2 a fire makes.

    This is the provable part of Dustin's objection and it is not
    in doubt - only how much of it reached the room.
    """
    try:
        kg_h = float(kg_per_hour)
        hours = float(hours_per_day)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'kg_per_hour and hours_per_day must be '
                           'numbers'}
    if kg_h <= 0 or hours <= 0:
        return {'ok': False,
                'refusal': 'a fire that is not burning is not a '
                           'source'}
    kg_fuel = kg_h * hours
    kg_co2 = kg_fuel * carbon_fraction * CO2_PER_CARBON * co2_yield
    return {'ok': True, 'kgFuelPerDay': kg_fuel,
            'kgCo2PerDay': kg_co2,
            'mgPerDay': kg_co2 * 1e6,
            'note': ('assumes every combustion product enters the '
                     'room - an upper bound, and the flue is what '
                     'makes it one')}


def direct_burn_offset_ppm(kg_per_hour, volume_m3,
                           air_changes_per_hour,
                           hours_per_day=24.0):
    """ROUTE A applied: the steady-state offset if ALL the fire's
    CO2 stays indoors. Reuses the one shared mass balance."""
    from climate.co2_indoor_seed import steady_state_ppm
    source = wood_fire_co2_mg_per_day(kg_per_hour, hours_per_day)
    if not source.get('ok'):
        return source
    solved = steady_state_ppm(0.0, source['mgPerDay'], volume_m3,
                              air_changes_per_hour)
    if not solved.get('ok'):
        return solved
    return {'ok': True, 'route': 'direct-burn',
            'kgFuelPerDay': source['kgFuelPerDay'],
            'offsetPpm': solved['offsetPpm'],
            'volumeM3': float(volume_m3),
            'airChangesPerHour': float(air_changes_per_hour),
            'note': ('UPPER BOUND. Assumes no flue. A hearth with '
                     'a working chimney draws its own combustion '
                     'air and sends most products up the stack - '
                     'which is what a chimney is for, and why the '
                     'tracer routes are the better estimator')}


def pm_tracer_offset_ppm(pm25_ug_m3,
                         ef_pm_g_per_kg=EF_PM25_G_PER_KG_LOW,
                         ef_co2_g_per_kg=EF_CO2_G_PER_KG):
    """ROUTE B: measured room PM2.5 -> the CO2 that arrived with
    it. Answers "how much combustion product is in this room"
    without needing to know the flue."""
    try:
        pm = float(pm25_ug_m3)
        ef_pm = float(ef_pm_g_per_kg)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'pm25_ug_m3 and the emission factor '
                           'must be numbers'}
    if pm <= 0 or ef_pm <= 0:
        return {'ok': False,
                'refusal': 'a room with no measured PM2.5 gives '
                           'this route nothing to work from'}
    ratio = ef_co2_g_per_kg / ef_pm
    co2_mg_m3 = pm * ratio / 1000.0
    return {'ok': True, 'route': 'pm-tracer',
            'pm25UgM3': pm, 'co2PerPmMassRatio': ratio,
            'co2MgPerM3': co2_mg_m3,
            'offsetPpm': co2_mg_m3 / _co2_mg_per_m3_per_ppm(),
            'note': ('the PM2.5 emission factor spans 5-20 g/kg in '
                     'the literature, a factor of four, and that '
                     'is most of this route\'s uncertainty')}


def co_tracer_offset_ppm(co_ppm, mce=MCE_LOW):
    """ROUTE C: measured room CO -> the CO2 emitted alongside it,
    via the modified combustion efficiency."""
    try:
        co = float(co_ppm)
        eff = float(mce)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'co_ppm and mce must be numbers'}
    if co <= 0:
        return {'ok': False,
                'refusal': 'no measured CO leaves this route with '
                           'nothing to scale'}
    if not 0.0 < eff < 1.0:
        return {'ok': False,
                'refusal': ('modified combustion efficiency must '
                            'be between 0 and 1 exclusive; 1 '
                            'would mean no CO at all, and then '
                            'CO cannot be a tracer')}
    molar_ratio = eff / (1.0 - eff)
    return {'ok': True, 'route': 'co-tracer', 'coPpm': co,
            'mce': eff, 'co2PerCoMolarRatio': molar_ratio,
            'offsetPpm': co * molar_ratio,
            'note': ('CO and CO2 are both gases, so the molar '
                     'ratio is also the ppm ratio - no density '
                     'conversion is needed and none is done')}


def combustion_offset_band(pm25_ug_m3=None, co_ppm=None):
    """BOTH TRACERS, and their disagreement reported rather than
    averaged.

    Averaging two estimates that differ fivefold produces a number
    with the precision of neither. The band is the answer.
    """
    estimates = []
    if pm25_ug_m3:
        for ef in (EF_PM25_G_PER_KG_HIGH, EF_PM25_G_PER_KG_LOW):
            got = pm_tracer_offset_ppm(pm25_ug_m3,
                                       ef_pm_g_per_kg=ef)
            if got.get('ok'):
                estimates.append(('pm-tracer', ef, got['offsetPpm']))
    if co_ppm:
        for eff in (MCE_LOW, MCE_HIGH):
            got = co_tracer_offset_ppm(co_ppm, mce=eff)
            if got.get('ok'):
                estimates.append(('co-tracer', eff,
                                  got['offsetPpm']))
    if not estimates:
        return {'ok': False,
                'refusal': ('give a measured PM2.5 or CO to work '
                            'from - with neither, the only route '
                            'left is the direct burn, which needs '
                            'a flue assumption nobody can check')}
    values = [v for _, _, v in estimates]
    by_route = {}
    for route, param, value in estimates:
        by_route.setdefault(route, []).append(value)
    spread = None
    if len(by_route) == 2:
        pm_mid = sum(by_route['pm-tracer']) / len(
            by_route['pm-tracer'])
        co_mid = sum(by_route['co-tracer']) / len(
            by_route['co-tracer'])
        if min(pm_mid, co_mid) > 0:
            spread = max(pm_mid, co_mid) / min(pm_mid, co_mid)
    return {
        'ok': True, 'lowPpm': min(values), 'highPpm': max(values),
        'estimates': [{'route': r, 'parameter': p,
                       'offsetPpm': v} for r, p, v in estimates],
        'routesAgreeWithinFactor': spread,
        'tracersAgree': bool(spread and spread <= 2.0),
        'note': ('the two tracers are NOT averaged. Where they '
                 'disagree, the disagreement is the honest width '
                 'of the answer, and averaging would manufacture '
                 'a precision neither route has'),
        'disagreementNote': (
            'against the Puno 24-hour medians these routes differ '
            'by roughly fivefold. The measured CO:PM mass ratio '
            'there is near 51 where wood-smoke emission factors '
            'predict 4-15, so either the instruments were not '
            'co-located, or PM settled out, or the CO had a '
            'second source. Any of those is a reason to widen the '
            'band, not to pick a favourite.'),
    }


def hearth_dwelling_estimate(background_ppm=280.0,
                             pm25_ug_m3=130.0, co_ppm=5.8,
                             respiration_offset_ppm=60.0):
    """THE REVISED ANSWER: what a pre-industrial hearth-heated
    dwelling plausibly sat at, built from the measurements that
    DO exist rather than from a draughtiness assumption.

    Defaults are the Puno 24-hour rural medians, which are the
    closest living analogue to a pre-industrial hearth that anyone
    has actually instrumented.
    """
    band = combustion_offset_band(pm25_ug_m3, co_ppm)
    if not band.get('ok'):
        return band
    low = (background_ppm + respiration_offset_ppm
           + band['lowPpm'])
    high = (background_ppm + respiration_offset_ppm
            + band['highPpm'])
    return {
        'ok': True,
        'backgroundPpm': background_ppm,
        'respirationOffsetPpm': respiration_offset_ppm,
        'combustionOffsetLowPpm': band['lowPpm'],
        'combustionOffsetHighPpm': band['highPpm'],
        'dwellingLowPpm': low, 'dwellingHighPpm': high,
        'tracers': band,
        'verdict': (
            f'a hearth-heated dwelling at a {background_ppm:.0f} '
            f'ppm background plausibly sat between {low:.0f} and '
            f'{high:.0f} ppm as a DAILY AVERAGE - comparable to '
            f'today\'s urban outdoor air, and below a modern '
            f'sealed bedroom. During active cooking, when PM and '
            f'CO peak several times their daily median, the room '
            f'would have run correspondingly higher.'),
        'whatThisChanges': (
            'It narrows the gap the previous commit claimed. A '
            'fire IS a large CO2 source - the direct-burn '
            'arithmetic is not in doubt - and the smoke in those '
            'rooms proves combustion products reached the '
            'occupants. What the tracers bound is how much: tens '
            'to low hundreds of ppm on a daily average, not the '
            'thousands the unflued direct calculation would give.'),
        'peakCaveat': (
            'THE DAILY AVERAGE IS NOT THE EXPOSURE THAT MATTERS '
            'MOST. Cooking is episodic and the person tending the '
            'fire is closest to it. A cooking-period peak '
            'plausibly reached or exceeded a modern sealed '
            'bedroom - which means the indoor PEAK is probably '
            'NOT novel. What is novel is that today\'s elevation '
            'is continuous and cannot be left.'),
        'headline': [
            {'label': 'Fire as a CO2 source',
             'value': 'large, and provable',
             'note': 'a 0.5 kg/h fire fully retained would add '
                     'hundreds to thousands of ppm',
             'verdict': 'warn'},
            {'label': 'What the tracers say reached the room',
             'value': f'+{band["lowPpm"]:.0f} to '
                      f'+{band["highPpm"]:.0f} ppm',
             'note': 'from measured PM2.5 and CO, so no flue '
                     'assumption is needed',
             'verdict': 'ok'},
            {'label': 'Hearth dwelling, daily average',
             'value': f'{low:.0f}-{high:.0f} ppm',
             'note': 'at a 280 ppm pre-industrial background',
             'verdict': 'ok'},
            {'label': 'Do the two tracers agree?',
             'value': ('no - about fivefold apart'
                       if not band['tracersAgree'] else 'yes'),
             'note': 'reported, not averaged away',
             'verdict': 'warn'},
        ],
    }
