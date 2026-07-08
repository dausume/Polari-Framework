"""
@cross-cutting
@module aquaponics.atmosphere_analysis
@tags @xc:bindings

Atmospheric conditions + plant↔air gas exchange (aqp-5) — pure
functions over AtmosphereDefinition, coupled to the aqp-4 plant
budget.

  atmosphere_state    — VPD (the transpiration driver) from T + RH,
                        CO2 mass density, light-hours, with findings
                        when VPD/light sit outside healthy bands.
  environment_gas_exchange — couples the plant's net CO2 draw to THIS
                        atmosphere: open air = effectively unlimited;
                        a controlled volume depletes (days-to-floor if
                        sealed) or holds a steady CO2 ppm under
                        ventilation. The enclosure question answered by
                        analysis, not assumption.

Every derived number is labeled and every simplification flagged (no
diurnal cycle here — daily rates; the dynamic sim refines).

@consumers
  - aquaponics.atmosphere_api / aquaponics.selftest_atmosphere / aqp-6
@see /AQUAPONICS_MODULE_PLAN.md
"""

import math

from aquaponics.plant_analysis import plant_gas_nutrient_budget

#: 1 ppm CO2 ~ 1.8 mg/m^3 at ~25 C, 101 kPa.
CO2_MG_PER_M3_PER_PPM = 1.8
#: C3 photosynthesis stalls approaching this CO2 floor.
PHOTOSYNTHESIS_FLOOR_PPM = 200.0
#: Healthy vapour-pressure-deficit band for most crops (kPa).
IDEAL_VPD_MIN, IDEAL_VPD_MAX = 0.8, 1.2
#: Rough light adequacy floor for leafy crops (umol/m^2/s).
LOW_LIGHT_PPFD = 150.0


def _by_name(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    rows = table.values() if isinstance(table, dict) else table
    return {getattr(r, 'name', ''): r for r in rows}


def _f(row, attr, default=0.0):
    try:
        return float(getattr(row, attr, default))
    except (TypeError, ValueError):
        return default


def saturation_vapour_pressure_kpa(temp_c):
    """Tetens equation — saturation vapour pressure over water (kPa)."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def atmosphere_state(manager, atmosphere_name):
    """VPD, CO2 density, light standing for one atmosphere."""
    atms = _by_name(manager, 'AtmosphereDefinition')
    atm = atms.get(atmosphere_name)
    if atm is None:
        return {'ok': False,
                'error': f"no AtmosphereDefinition named "
                         f"'{atmosphere_name}'",
                'knownAtmospheres': sorted(atms)}
    temp = _f(atm, 'temperature_c')
    rh = _f(atm, 'relative_humidity_pct')
    es = saturation_vapour_pressure_kpa(temp)
    ea = es * rh / 100.0
    vpd = es - ea
    co2_ppm = _f(atm, 'co2_ppm')
    ppfd = _f(atm, 'light_ppfd_umol_m2_s')
    findings = []
    if vpd < IDEAL_VPD_MIN:
        findings.append({
            'kind': 'vpd-low',
            'evidence': f'VPD {vpd:.2f} kPa < {IDEAL_VPD_MIN} — humid '
                        'air slows transpiration and nutrient pull; '
                        'fungal risk',
            'suggestion': {'knob': 'relative_humidity_pct / '
                                   'temperature_c',
                           'action': 'lower humidity or raise temp'}})
    elif vpd > IDEAL_VPD_MAX:
        findings.append({
            'kind': 'vpd-high',
            'evidence': f'VPD {vpd:.2f} kPa > {IDEAL_VPD_MAX} — dry '
                        'air over-transpires, stomata close, growth '
                        'stalls',
            'suggestion': {'knob': 'relative_humidity_pct',
                           'action': 'raise humidity'}})
    if ppfd < LOW_LIGHT_PPFD:
        findings.append({
            'kind': 'light-low',
            'evidence': f'PPFD {ppfd:.0f} umol/m2/s < {LOW_LIGHT_PPFD} '
                        '— below the leafy-crop light floor; CO2 '
                        'fixation will run under its light-saturated '
                        'max', 'suggestion': {
                            'knob': 'light_ppfd_umol_m2_s',
                            'action': 'add light'}})
    return {
        'ok': True,
        'atmosphere': atmosphere_name,
        'displayName': getattr(atm, 'display_name', '')
        or atmosphere_name,
        'controlled': bool(getattr(atm, 'controlled', False)),
        'temperatureC': temp,
        'relativeHumidityPct': rh,
        'saturationVapourPressureKpa': round(es, 4),
        'vapourPressureDeficitKpa': round(vpd, 4),
        'co2Ppm': co2_ppm,
        'co2MassDensityMgM3': round(
            co2_ppm * CO2_MG_PER_M3_PER_PPM, 2),
        'o2Pct': _f(atm, 'o2_pct'),
        'lightPpfd': ppfd,
        'photoperiodHours': _f(atm, 'photoperiod_hours'),
        'dailyLightIntegralNote': 'DLI approx = PPFD * photoperiod * '
                                  '3600 / 1e6 mol/m2/day',
        'findings': findings,
        'note': 'VPD by Tetens; the transpiration + CO2-fixation '
                'drivers the plant couples to. No diurnal cycle here '
                '— the dynamic sim adds it.',
    }


def environment_gas_exchange(manager, plant_name, atmosphere_name):
    """Couple the plant's net CO2 draw to this atmosphere: open air =
    unlimited; a controlled volume depletes (sealed) or settles to a
    steady CO2 under ventilation."""
    atms = _by_name(manager, 'AtmosphereDefinition')
    atm = atms.get(atmosphere_name)
    if atm is None:
        return {'ok': False,
                'error': f"no AtmosphereDefinition named "
                         f"'{atmosphere_name}'"}
    budget = plant_gas_nutrient_budget(manager, plant_name)
    if not budget.get('ok'):
        return {'ok': False,
                'error': f"plant budget unavailable: "
                         f"{budget.get('error')}"}
    net_co2_day = budget.get('netCo2FixedMgDay') or 0.0
    net_o2_day = budget.get('netO2ReleasedMgDay') or 0.0

    controlled = bool(getattr(atm, 'controlled', False))
    volume = _f(atm, 'volume_m3')
    ach = _f(atm, 'air_exchange_per_hour')
    co2_ppm = _f(atm, 'co2_ppm')
    outside_ppm = _f(atm, 'outside_co2_ppm')

    result = {
        'ok': True,
        'plant': plant_name,
        'atmosphere': atmosphere_name,
        'netCo2FixedMgDay': net_co2_day,
        'netO2ReleasedMgDay': net_o2_day,
        'controlled': controlled,
    }
    if not controlled or volume <= 0:
        result.update({
            'verdict': 'open-air-unlimited',
            'evidence': 'open air (or no enclosed volume) — CO2 is '
                        'effectively unlimited; the plant does not '
                        'measurably shift ambient composition',
            'note': 'O2 release and CO2 draw disperse into open air; '
                    'meaningful gas coupling needs a controlled '
                    'volume'})
        return result

    co2_mass_mg = co2_ppm * CO2_MG_PER_M3_PER_PPM * volume
    usable_mass_mg = max(
        0.0, (co2_ppm - PHOTOSYNTHESIS_FLOOR_PPM)
        * CO2_MG_PER_M3_PER_PPM * volume)
    # Ventilation capacity toward ambient (mg/day per ppm gap).
    vent_mg_per_ppm_day = ach * volume * 24.0 * CO2_MG_PER_M3_PER_PPM
    result['co2MassInVolumeMg'] = round(co2_mass_mg, 2)
    result['usableAboveFloorMg'] = round(usable_mass_mg, 2)

    if ach <= 0:
        days = (usable_mass_mg / net_co2_day) if net_co2_day > 0 \
            else None
        result.update({
            'verdict': 'sealed-depleting' if net_co2_day > 0
            else 'sealed-stable',
            'daysToPhotosynthesisFloor': round(days, 3)
            if days is not None else None,
            'evidence': f'sealed {volume:.1f} m3: '
                        f'{usable_mass_mg:.0f} mg CO2 usable above the '
                        f'{PHOTOSYNTHESIS_FLOOR_PPM:.0f} ppm floor, '
                        f'plant draws {net_co2_day:.0f} mg/day'
            if net_co2_day > 0 else 'sealed but the plant is net O2-'
                                    'consuming (dark) — CO2 rises',
            'suggestion': {'knob': 'air_exchange_per_hour',
                           'action': 'ventilate, or dose CO2, before '
                                     'the floor'}})
        return result

    # Ventilated: steady CO2 where demand == ventilation supply.
    steady_ppm = outside_ppm - (net_co2_day / vent_mg_per_ppm_day) \
        if vent_mg_per_ppm_day > 0 else None
    sustains = steady_ppm is not None \
        and steady_ppm >= PHOTOSYNTHESIS_FLOOR_PPM
    result.update({
        'verdict': 'ventilation-sustains' if sustains
        else 'depleting-despite-ventilation',
        'steadyStateCo2Ppm': round(steady_ppm, 1)
        if steady_ppm is not None else None,
        'ventilationCapacityMgPerPpmDay': round(vent_mg_per_ppm_day, 2),
        'evidence': f'{ach:.1f} ACH over {volume:.1f} m3 settles CO2 '
                    f'to ~{steady_ppm:.0f} ppm against a '
                    f'{net_co2_day:.0f} mg/day draw'
        if steady_ppm is not None else 'no ventilation capacity',
        'suggestion': None if sustains else {
            'knob': 'air_exchange_per_hour / outside_co2_ppm',
            'action': 'raise ventilation or supplement CO2 — the '
                      'steady state falls below the photosynthesis '
                      'floor'},
        'note': 'steady-state CO2 = outside_ppm - demand/ventilation '
                'capacity (a daily-mean balance; no diurnal cycle)',
    })
    return result
