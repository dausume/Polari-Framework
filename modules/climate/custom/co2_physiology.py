"""
@module climate.custom.co2_physiology

ppm to partial pressure, and the honest mechanism framing
(CO2_HEALTH_PLAN.md §6). ppm is a MIXING RATIO; what acts on a
lung is a PRESSURE, and the same ppm is a smaller pressure in
Denver than at the shore — so altitude is a row here, not a
footnote.

The framing string in `elimination_gradient` is the plan's, kept
VERBATIM: the mechanism is not ambient CO2 "filling the lungs".
It is that the gradient the body eliminates CO2 down is slightly
reduced, and that the compensations — ventilation rate, blood
pH, renal bicarbonate handling — are measurable before anyone
feels anything. That is exactly why the NHANES bicarbonate
series is the interesting dataset: it is the population-scale
measurement of the compensation side.

This file is DESCRIPTIVE. It converts units and states a
gradient. It does not grade a ppm value as harmful on its own
authority — that judgement belongs to the CO2HealthThreshold
rows with their evidence grades, and blurring the two is how a
page becomes confidently wrong.

Pure stdlib: no numpy, so the module works on a bare node.

@consumers climate.co2_indoor_seed, climate.co2_projection,
climate.climate_views_seed, climate.climate_api, climate.selftest_co2
"""

import math

#: Standard sea-level atmospheric pressure.
STANDARD_PRESSURE_KPA = 101.325

#: kPa in one mmHg (torr) — the clinical unit for gas tensions.
KPA_PER_MMHG = 0.133322

#: Normal alveolar pCO2 — the number ambient must be read
#: against. Ambient is a fraction of a mmHg; this is 40.
ALVEOLAR_PCO2_MMHG = 40.0

#: The pre-industrial reference the gradient reduction is
#: measured from. A stated reference, not a hidden baseline.
PREINDUSTRIAL_PPM = 280.0

#: The barometric formula below is the troposphere fit only.
TROPOSPHERE_LIMIT_M = 11000.0


def _refuse(text):
    """Every failure leaves by this door."""
    return {'ok': False, 'refusal': text}


def partial_pressure(ppm, pressure_kpa=STANDARD_PRESSURE_KPA):
    """pCO2 = ppm * 1e-6 * ambient pressure, in kPa and mmHg."""
    try:
        ppm_v = float(ppm)
        press = float(pressure_kpa)
    except (TypeError, ValueError):
        return _refuse(
            'ppm and pressure must be numbers; passing the '
            'series value and a pressure row retires this')
    if math.isnan(ppm_v) or math.isnan(press):
        return _refuse(
            'ppm or pressure is not a number; an ingested value '
            'retires this refusal')
    if ppm_v < 0.0:
        return _refuse(
            f'negative CO2 mole fraction ({ppm_v} ppm) is not a '
            f'measurement; a non-negative ingested value retires '
            f'this refusal')
    if press <= 0.0:
        return _refuse(
            f'ambient pressure must be positive ({press} kPa was '
            f'given); a real barometric or altitude row retires '
            f'this refusal')
    pco2_kpa = ppm_v * 1e-6 * press
    pco2_mmhg = pco2_kpa / KPA_PER_MMHG
    return {
        'ok': True,
        'ppm': ppm_v,
        'pressureKpa': press,
        'pco2Kpa': pco2_kpa,
        'pco2Mmhg': pco2_mmhg,
        'pctOfAlveolar': pco2_mmhg / ALVEOLAR_PCO2_MMHG * 100.0,
    }


def pressure_at_altitude(altitude_m):
    """Barometric formula for the troposphere:
    p = 101.325 * (1 - 2.25577e-5*h)^5.25588."""
    try:
        h = float(altitude_m)
    except (TypeError, ValueError):
        return _refuse(
            'altitude must be a number in metres; a location row '
            'carrying an elevation retires this refusal')
    if math.isnan(h):
        return _refuse(
            'altitude is not a number; an elevation row retires '
            'this refusal')
    if h > TROPOSPHERE_LIMIT_M:
        return _refuse(
            f'{h:.0f} m is above the {TROPOSPHERE_LIMIT_M:.0f} m '
            f'troposphere limit of this formula — the standard '
            f'atmosphere changes lapse rate at the tropopause '
            f'and this expression stops being valid there. A '
            f'stratospheric pressure model would retire this '
            f'refusal; no inhabited site needs it')
    if h < -500.0:
        return _refuse(
            f'{h:.0f} m is below the lowest dry land on Earth; a '
            f'real elevation retires this refusal')
    factor = 1.0 - 2.25577e-5 * h
    pressure = STANDARD_PRESSURE_KPA * (factor ** 5.25588)
    return {'ok': True, 'altitudeM': h, 'pressureKpa': pressure}


def elimination_gradient(ambient_ppm,
                         pressure_kpa=STANDARD_PRESSURE_KPA,
                         alveolar_mmhg=ALVEOLAR_PCO2_MMHG):
    """The alveolar-to-ambient gradient, and how much of it the
    rise since pre-industrial has taken away."""
    ambient = partial_pressure(ambient_ppm, pressure_kpa)
    if not ambient.get('ok'):
        return ambient
    reference = partial_pressure(PREINDUSTRIAL_PPM, pressure_kpa)
    if not reference.get('ok'):
        return reference
    try:
        alveolar = float(alveolar_mmhg)
    except (TypeError, ValueError):
        return _refuse(
            'alveolar pCO2 must be a number in mmHg; a measured '
            'or literature row retires this refusal')
    if alveolar <= 0.0:
        return _refuse(
            'alveolar pCO2 must be positive; the normal value is '
            'near 40 mmHg and a measured row retires this')
    gradient = alveolar - ambient['pco2Mmhg']
    ref_gradient = alveolar - reference['pco2Mmhg']
    if ref_gradient <= 0.0:
        return _refuse(
            'the pre-industrial reference gradient is not '
            'positive, which means the alveolar value given is '
            'below ambient — check the alveolar row')
    reduction = (ref_gradient - gradient) / ref_gradient * 100.0
    framing = (
        'Ambient pCO2 even indoors is a fraction of a mmHg '
        'against an alveolar pCO2 near 40 mmHg. The mechanism is '
        'NOT that ambient CO2 fills the lungs - it is that the '
        'gradient the body eliminates CO2 down is slightly '
        'reduced, and that the compensations (ventilation rate, '
        'blood pH, renal bicarbonate handling) are measurable '
        'before anyone feels anything.')
    return {
        'ok': True,
        'ambientPpm': ambient['ppm'],
        'ambientMmhg': ambient['pco2Mmhg'],
        'alveolarMmhg': alveolar,
        'gradientMmhg': gradient,
        'referencePpm': PREINDUSTRIAL_PPM,
        'referenceGradientMmhg': ref_gradient,
        'gradientReductionPct': reduction,
        'pressureKpa': ambient['pressureKpa'],
        'framing': framing,
    }


def headline(ppm_list, pressure_kpa=STANDARD_PRESSURE_KPA):
    """The `headline` renderer contract the motors views use:
    rows of {label, value, note, verdict}. Every verdict here is
    'ok' — this file DESCRIBES a pressure, and grading a ppm as
    harmful is the threshold rows' job, not this engine's."""
    rows = []
    try:
        if isinstance(ppm_list, (int, float, str)):
            candidates = [ppm_list]
        elif isinstance(ppm_list, (list, tuple)):
            candidates = list(ppm_list)
        else:
            candidates = []
        if not candidates:
            return [{
                'label': 'no ppm values given',
                'value': 'nothing to convert',
                'verdict': 'warn',
                'note': 'pass a list of ppm levels — an ingested '
                        'series value, an indoor room level — '
                        'and these rows appear',
            }]
        for raw in candidates:
            label = None
            value_ppm = raw
            if isinstance(raw, dict):
                label = raw.get('label') or raw.get('name')
                value_ppm = raw.get('ppm', raw.get('value'))
            grad = elimination_gradient(value_ppm, pressure_kpa)
            if not grad.get('ok'):
                rows.append({
                    'label': label or f'{value_ppm} ppm',
                    'value': 'not convertible',
                    'verdict': 'warn',
                    'note': grad.get('refusal', 'refused'),
                })
                continue
            shown = label or f'{grad["ambientPpm"]:.0f} ppm'
            kpa = grad['ambientMmhg'] * KPA_PER_MMHG
            pct = (grad['ambientMmhg']
                   / ALVEOLAR_PCO2_MMHG * 100.0)
            rows.append({
                'label': shown,
                'value': f'{grad["ambientMmhg"]:.3f} mmHg',
                'verdict': 'ok',
                'note': (
                    f'{grad["ambientPpm"]:.0f} ppm at '
                    f'{grad["pressureKpa"]:.2f} kPa is '
                    f'{kpa:.5f} kPa, {pct:.2f} percent of '
                    f'alveolar pCO2'),
            })
            rows.append({
                'label': f'{shown} - elimination gradient',
                'value': f'{grad["gradientMmhg"]:.3f} mmHg',
                'verdict': 'ok',
                'note': (
                    f'against {grad["referenceGradientMmhg"]:.3f}'
                    f' mmHg at the stated '
                    f'{grad["referencePpm"]:.0f} ppm '
                    f'pre-industrial reference: the gradient is '
                    f'{grad["gradientReductionPct"]:.3f} percent '
                    f'smaller'),
            })
        rows.append({
            'label': 'alveolar pCO2 (the number to read against)',
            'value': f'{ALVEOLAR_PCO2_MMHG:.1f} mmHg',
            'verdict': 'ok',
            'note': 'normal alveolar pCO2. Ambient values above '
                    'are fractions of one mmHg beside it',
        })
        rows.append({
            'label': 'the mechanism',
            'value': 'a reduced gradient, not filled lungs',
            'verdict': 'ok',
            'note': (
                'Ambient pCO2 even indoors is a fraction of a '
                'mmHg against an alveolar pCO2 near 40 mmHg. The '
                'mechanism is NOT that ambient CO2 fills the '
                'lungs - it is that the gradient the body '
                'eliminates CO2 down is slightly reduced, and '
                'that the compensations (ventilation rate, blood '
                'pH, renal bicarbonate handling) are measurable '
                'before anyone feels anything.'),
        })
        rows.append({
            'label': 'what this engine does NOT say',
            'value': 'no harm grade from a pressure alone',
            'verdict': 'ok',
            'note': 'a ppm value is graded only by the '
                    'CO2HealthThreshold rows and their evidence '
                    'grades; this file converts units and states '
                    'a gradient',
        })
        return rows
    except Exception as exc:                 # never raise out
        return [{
            'label': 'headline failed',
            'value': 'no rows',
            'verdict': 'warn',
            'note': f'internal error building the rows: {exc}',
        }]
